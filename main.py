"""Infrastructure Legal Event Radar — entry point.

One command runs the whole pipeline:

  1. Detection: for each registered source, fetch → load prior snapshot → diff →
     save. Prints a console summary of what changed.
  2. Translation: each detected event/change is run through the legal materiality
     rubric (Claude API) into a structured memo item.
  3. Memo: items are ranked (URGENT / REVIEW / NOISE) and written to a dated
     Markdown file under output/.

Detection runs with no API key. Translation needs ANTHROPIC_API_KEY (from .env);
without it, the run stops after detection and tells you how to enable the memo.

Run:  python main.py            # full pipeline
      python main.py --detect-only    # detection + console summary only
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from datetime import datetime, timezone

# macOS system Python links LibreSSL, which urllib3 v2 warns about on import.
# It does not affect fetching public HTTPS pages; silence it to keep the
# console readable for a non-technical (legal) user.
warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from radar.config import load_email_config, load_watchlist
from radar.diff import diff_items, diff_text, focused_excerpt
from radar.findings import (
    change_finding,
    load_tracked_sla,
    operational_event_finding,
)
from radar.memo import render_memo, write_memo
from radar.registry import active_sources
from radar.snapshot import SnapshotStore

# Cap findings per source so a wholesale page/layout change (many diff blocks)
# can't fan out into dozens of API calls. Excess is noted, not silently dropped.
_MAX_CHANGE_FINDINGS_PER_SOURCE = 12


def _clip(s: str, n: int = 200) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + " …"


def _print_event(e) -> None:
    az = f" AZ={','.join(e['availability_zones'])}" if e.get("availability_zones") else ""
    dur = f" {e['duration_hours']}h" if e.get("duration_hours") is not None else ""
    print(
        f"    • [{e.get('status_label')}] {e.get('summary')} — "
        f"{e.get('service_name')} / {e.get('region_name')} "
        f"({e.get('region_code')}){az}"
    )
    print(
        f"      started {e.get('started_at')}{dur}; "
        f"{e.get('impacted_service_count')} service(s) impacted; "
        f"{e.get('update_count')} update(s)"
    )


def _watchlist_summary(w) -> str:
    if w.is_empty:
        return "none (reporting on everything)"
    region_part = f"regions={w.regions_used or '—'}"
    if w.regions_used:
        region_part += f" (filter: {w.region_filter_mode})"
    return (
        f"services={w.aws_services_used or '—'}; "
        f"{region_part}; "
        f"concerns={w.heightened_concerns or '—'}"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Infrastructure Legal Event Radar")
    parser.add_argument("--config", default="config.yaml", help="watchlist YAML (optional)")
    parser.add_argument("--snapshots", default="snapshots", help="snapshot store dir")
    parser.add_argument("--output", default="output", help="memo output dir")
    parser.add_argument(
        "--detect-only", action="store_true", help="skip the Claude translation/memo"
    )
    parser.add_argument(
        "--no-email", action="store_true", help="generate the memo but do not email it"
    )
    args = parser.parse_args(argv)

    load_dotenv()  # pull ANTHROPIC_API_KEY from .env if present
    run_time = datetime.now(timezone.utc)

    watchlist = load_watchlist(args.config)
    print(f"Watchlist: {_watchlist_summary(watchlist)}")

    store = SnapshotStore(args.snapshots)
    sla_data = load_tracked_sla(store)  # tracked thresholds from prior run (may be empty on very first run)

    print("\nDetection pass:")
    findings = []
    notes = []
    out_of_region_events = []  # appendix-mode events, rendered as one-liners
    failures = 0

    for source in active_sources():
        try:
            result = source.fetch()
        except Exception as exc:  # one bad source ≠ dead run
            failures += 1
            print(f"  [{source.name}] FETCH FAILED: {exc}")
            notes.append(f"{source.name}: FETCH FAILED — {exc}")
            continue

        previous = store.latest(source.source_id)
        is_sla = source.kind == "sla"

        # --- page-diff sources (Service Terms, SLA pages) ---
        if result.text is not None:
            d = diff_text(previous.text if previous else None, result.text)
            if d.is_first_run:
                print(f"  [{source.name}] baseline snapshot created (first run).")
                notes.append(f"{source.name}: baseline snapshot created (no diff this run).")
            elif not d.has_changes:
                print(f"  [{source.name}] no change since last snapshot.")
                notes.append(f"{source.name}: no change.")
            else:
                print(
                    f"  [{source.name}] CHANGED: {len(d.blocks)} block(s), "
                    f"+{d.added_lines}/-{d.removed_lines} lines."
                )
                notes.append(
                    f"{source.name}: {len(d.blocks)} changed block(s) "
                    f"(+{d.added_lines}/-{d.removed_lines} lines)."
                )
                blocks = d.blocks[:_MAX_CHANGE_FINDINGS_PER_SOURCE]
                for b in blocks:
                    o, n = focused_excerpt(b.old, b.new) if (b.old and b.new) else (b.old, b.new)
                    print(f"    ── OLD: {_clip(o)}")
                    print(f"       NEW: {_clip(n)}")
                    findings.append(
                        change_finding(
                            source_name=source.name,
                            source_url=source.url,
                            old_language=b.old,
                            new_language=b.new,
                            is_sla=is_sla,
                            sla_data=sla_data,
                            watchlist=watchlist,
                        )
                    )
                if len(d.blocks) > len(blocks):
                    extra = len(d.blocks) - len(blocks)
                    print(f"    …and {extra} more block(s) (not translated this run).")
                    notes.append(f"{source.name}: {extra} additional block(s) exceeded per-source cap.")

        # --- event-feed source (Health) ---
        if result.items:
            old_items = previous.items if previous else None
            d = diff_items(old_items, result.items, revision_key="revision")
            new_ids = {e.get("id") for e in d.new_items}
            updated_ids = {e.get("id") for e in d.updated_items}

            if d.is_first_run:
                print(f"  [{source.name}] baseline snapshot created (first run).")
            print(
                f"  [{source.name}] {len(d.new_items)} new, {len(d.updated_items)} "
                f"updated; {sum(1 for e in result.items if not e.get('resolved'))} open."
            )
            notes.append(
                f"{source.name}: {len(d.new_items)} new, {len(d.updated_items)} updated event(s); "
                f"{sum(1 for e in result.items if not e.get('resolved'))} currently open."
            )

            # Report every currently-open event (active exposure persists each
            # run), plus any newly new/updated event, deduped by id. Apply the
            # region filter here (operational events only — never terms/SLA).
            in_scope = excluded = appendixed = 0
            for e in result.items:
                if e.get("resolved"):
                    continue
                status = watchlist.region_status(
                    e.get("region_code", ""), e.get("region_name", "")
                )
                if status == "out_of_scope":
                    if watchlist.region_filter_mode == "strict":
                        excluded += 1
                        continue  # excluded entirely
                    # appendix mode: one-line NOISE-appendix entry, not translated
                    appendixed += 1
                    out_of_region_events.append(e)
                    continue

                eid = e.get("id")
                if eid in new_ids:
                    kind = "new"
                elif eid in updated_ids:
                    kind = "updated"
                else:
                    kind = "ongoing"
                in_scope += 1
                _print_event(e)
                findings.append(
                    operational_event_finding(
                        e,
                        detected_this_run=(kind in ("new", "updated")),
                        change_kind=kind,
                        sla_data=sla_data,
                        watchlist=watchlist,
                    )
                )

            if watchlist.regions_used and (excluded or appendixed):
                mode = watchlist.region_filter_mode
                print(
                    f"    region filter ({mode}): {in_scope} in-scope, "
                    + (f"{excluded} excluded" if excluded else f"{appendixed} → appendix")
                )
                notes.append(
                    f"{source.name}: region filter [{mode}] on {watchlist.regions_used} — "
                    f"{in_scope} in-scope; "
                    + (
                        f"{excluded} out-of-region event(s) excluded."
                        if mode == "strict"
                        else f"{appendixed} out-of-region event(s) demoted to appendix."
                    )
                )

        store.save(result)

    print(f"\nDetection complete: {len(findings)} finding(s) to translate.")

    if args.detect_only:
        print("(--detect-only: skipping translation/memo.)")
        return 1 if failures else 0

    # --- Translation + memo ---
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "\nNo ANTHROPIC_API_KEY found — stopping after detection.\n"
            "To generate the legal memo, create a .env file in this folder with:\n"
            "  ANTHROPIC_API_KEY=sk-ant-...\n"
            "(copy .env.example to .env and paste your key). Then re-run.\n"
            "Detection ran fine; snapshots are saved."
        )
        return 0

    import anthropic  # imported here so detection-only runs need no SDK

    from radar.translate import MODEL, translate_all

    client = anthropic.Anthropic()
    print(f"\nTranslating {len(findings)} finding(s) via {MODEL}…")
    items = translate_all(client, findings)
    errs = sum(1 for it in items if "memo" not in it)
    if errs:
        print(f"  ({errs} finding(s) failed translation — see memo's error section.)")

    memo_text = render_memo(
        items,
        run_time=run_time,
        watchlist_summary=_watchlist_summary(watchlist),
        detection_notes=notes,
        out_of_region_events=out_of_region_events,
    )
    path = write_memo(memo_text, run_time, args.output)

    # Console summary.
    urgent = sum(1 for it in items if it.get("memo", {}).get("materiality") == "URGENT")
    review = sum(1 for it in items if it.get("memo", {}).get("materiality") == "REVIEW")
    noise = sum(1 for it in items if it.get("memo", {}).get("materiality") == "NOISE")
    print(f"\nMemo written: {path}")
    print(f"  Triage: {urgent} URGENT · {review} REVIEW · {noise} NOISE")

    # --- Email delivery ---
    _maybe_send_email(args, items, memo_text, out_of_region_events, path)

    return 1 if failures else 0


def _maybe_send_email(args, items, memo_text, out_of_region_events, memo_path) -> None:
    """Send the memo by email if a recipient is configured. A send failure is
    reported but never fails the run — the memo is already written/artifacted."""
    from radar.mailer import build_subject, send_memo_email  # lazy: needs `markdown`

    email_cfg = load_email_config(args.config)

    if args.no_email:
        print("\nEmail: skipped (--no-email).")
        return
    if not email_cfg.is_enabled:
        print(
            "\nEmail: no recipient configured (set `email_to` in config.yaml to enable)."
        )
        return

    subject = build_subject(items, out_of_region_events)
    try:
        send_memo_email(
            email_cfg,
            subject=subject,
            memo_markdown=memo_text,
            attachment_name=memo_path.name,
        )
        print(f"\nEmail: sent to {email_cfg.to} — subject: \"{subject}\"")
    except Exception as exc:
        print(f"\nEmail: FAILED to send — {exc}")
        print("  (The memo was still generated and saved.)")


if __name__ == "__main__":
    sys.exit(main())
