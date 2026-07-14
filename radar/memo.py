"""Render translated findings into a memo — Markdown file and (via mailer) HTML.

Layout, verdict-first:

    Title
    VERDICT            ← plain-English bottom line, visually prominent
    Triage counts
    Watching … line    ← one-line run metadata
    ─────
    URGENT / REVIEW sections
    Appendix (de-emphasized): NOISE items + out-of-region events table
    Run summary (collapsed when nothing changed)
    ─────
    Disclaimer + run timestamp   ← small-print footer

The shared helpers here (verdict, watching line, triage split, appendix rows,
run summary) are also used by `mailer.render_html`, so the Markdown file and the
HTML email stay structurally identical.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DISCLAIMER = (
    "This memo is automated issue-spotting support, not legal advice. It screens "
    "and triages public AWS data; it does not conclude legal or credit "
    "eligibility. Every item requires attorney review against your actual AWS "
    "agreements, DPAs, and invoices before any action or reliance."
)


# --------------------------------------------------------------------------- #
# Shared computation (used by both the Markdown and HTML renderers)
# --------------------------------------------------------------------------- #

def _parse_date(s: Any) -> Optional[date]:
    if not s:
        return None
    s = str(s).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _fmt_date(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"  # e.g. "Aug 12"


def join_and(items: List[str]) -> str:
    items = [str(i) for i in items if str(i).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def human_watchlist(w) -> str:
    """One readable line, e.g. 'Watching EC2 and S3 in us-east-1 and us-west-2'."""
    svc = list(getattr(w, "aws_services_used", []) or [])
    reg = list(getattr(w, "regions_used", []) or [])
    if not svc and not reg:
        return "Watching all AWS services and regions"
    svc_part = join_and(svc) if svc else "all services"
    if reg:
        return f"Watching {svc_part} in {join_and(reg)}"
    return f"Watching {svc_part}"


def triage_split(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    good = [it for it in items if "memo" in it]
    failed = [it for it in items if "memo" not in it]
    by = lambda m: [it for it in good if it["memo"].get("materiality") == m]
    return {
        "urgent": by("URGENT"),
        "review": by("REVIEW"),
        "noise": by("NOISE"),
        "failed": failed,
    }


def _earliest_deadline_phrase(items: List[Dict[str, Any]]) -> Optional[str]:
    """Most pressing dated obligation across the given items, human-phrased."""
    candidates: List[Tuple[date, str]] = []
    for it in items:
        memo = it["memo"]
        screen = memo.get("sla_credit_screening")
        if screen and screen.get("potentially_credit_eligible"):
            d = _parse_date(screen.get("estimated_claim_deadline"))
            if d:
                candidates.append((d, f"SLA credit claim deadline {_fmt_date(d)}"))
        for a in memo.get("action_items", []):
            d = _parse_date(a.get("deadline"))
            if d:
                candidates.append((d, f"deadline {_fmt_date(d)}"))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]


def build_verdict(items: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Return (verdict_text, severity) where severity ∈ quiet|urgent|review.

    Examples:
      'All quiet: no items need your attention this week'
      '1 URGENT item: SLA credit claim deadline Aug 12'
      '3 items to review: deadline Sep 30'
    """
    t = triage_split(items)
    urgent, review = t["urgent"], t["review"]
    if not urgent and not review:
        return ("All quiet: no items need your attention this week", "quiet")

    if urgent:
        focus, noun_s, noun_p, severity = urgent, "URGENT item", "URGENT items", "urgent"
    else:
        focus, noun_s, noun_p, severity = review, "item to review", "items to review", "review"

    n = len(focus)
    head = f"{n} {noun_s if n == 1 else noun_p}"
    detail = _earliest_deadline_phrase(focus)
    if not detail:
        # No dated obligation — fall back to the top item's headline (trimmed).
        hl = focus[0]["memo"].get("headline", "").strip()
        detail = (hl[:70] + "…") if len(hl) > 71 else hl or None
    return (f"{head}: {detail}" if detail else head, severity)


def item_deadline(item: Dict[str, Any]) -> Optional[str]:
    """Human-phrased earliest deadline for a single item (for dashboard/JSON)."""
    if "memo" not in item:
        return None
    return _earliest_deadline_phrase([item])


def appendix_rows(events: List[Dict[str, Any]]) -> List[Tuple[str, str, str, str]]:
    """(region, event type, start date, status) per out-of-region event."""
    rows = []
    for e in events:
        rc = e.get("region_code", "?")
        rn = e.get("region_name", "")
        region = f"{rc} ({rn})" if rn and rn != rc else rc
        rows.append(
            (
                region,
                e.get("summary", ""),
                (e.get("started_at", "") or "")[:10],
                e.get("status_label", ""),
            )
        )
    return rows


def _health_detail(h: Dict[str, int]) -> str:
    open_ = h.get("open", 0)
    out = h.get("out_region", 0)
    ins = h.get("in_scope", 0)
    if out == open_:
        return "both out of region" if open_ == 2 else f"all {open_} out of region"
    if ins == open_:
        return "both in your regions" if open_ == 2 else f"all {open_} in your regions"
    return f"{ins} in your regions and {out} out of region"


def run_summary_lines(detection: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (collapsed, lines).

    collapsed=True → a single summary line (nothing changed).
    collapsed=False → itemized bullet lines (something changed)."""
    unchanged = detection.get("unchanged", [])
    changed = detection.get("changed_notes", [])
    failures = detection.get("failures", [])
    health = detection.get("health")

    if health is None:
        health_str = "Health events: source unavailable this run."
    elif health.get("open", 0) == 0:
        health_str = "Health events: none open."
    else:
        health_str = f"Health events: {health['open']} open, {_health_detail(health)}."

    if not changed and not failures:
        line = ""
        if unchanged:
            line = f"Sources checked, no changes: {join_and(unchanged)}. "
        return True, [f"{line}{health_str}".strip()]

    # Something changed → itemize.
    lines = list(changed)
    for f in failures:
        lines.append(f)
    if unchanged:
        lines.append(f"No change: {join_and(unchanged)}.")
    lines.append(health_str)
    return False, lines


# --------------------------------------------------------------------------- #
# Markdown rendering of a full item
# --------------------------------------------------------------------------- #

def _sep(o: List[str]) -> None:
    """Append a horizontal rule, unless the last content line is already one
    (avoids doubled '---' when a section is empty)."""
    for ln in reversed(o):
        if ln.strip() == "":
            continue
        if ln.strip() == "---":
            return
        break
    o.append("---")
    o.append("")


def _fmt_deadline(d) -> str:
    return d if d else "no fixed deadline"


def _render_item(item: Dict[str, Any], n: int) -> List[str]:
    memo = item["memo"]
    L: List[str] = []
    L.append(f"### {n}. {memo['headline']}")
    L.append("")
    L.append(
        f"**Materiality:** {memo['materiality']} · "
        f"**Confidence:** {memo['confidence']} · "
        f"**Type:** {memo['classification'].replace('_', ' ')}"
    )
    L.append(f"*Source: [{item.get('source_name', '')}]({item.get('source_url', '')})*")
    L.append("")
    L.append(f"**What happened.** {memo['what_happened']}")
    L.append("")
    L.append(f"**Why counsel cares.** {memo['why_counsel_cares']}")
    L.append("")
    if memo.get("materiality_rationale"):
        L.append(f"**Why this ranking.** {memo['materiality_rationale']}")
        L.append("")

    screen = memo.get("sla_credit_screening")
    if screen:
        flag = (
            "⚠️ POTENTIALLY CREDIT ELIGIBLE"
            if screen.get("potentially_credit_eligible")
            else "Not flagged for credit eligibility"
        )
        L.append(f"**SLA credit screening — {flag}.**")
        L.append(f"- Applicable SLA: {screen.get('applicable_sla', '—')}")
        L.append(f"- Credit tiers: {screen.get('credit_tiers', '—')}")
        L.append(
            f"- Estimated claim deadline: **{screen.get('estimated_claim_deadline', '—')}**"
        )
        L.append(f"- Basis: {screen.get('deadline_basis', '—')}")
        L.append("")

    for ch in memo.get("quoted_changes", []):
        L.append(f"**Change ({ch.get('category', 'uncategorized')}).**")
        L.append(f"> **Old:** {ch.get('old_language', '').strip() or '—'}")
        L.append(">")
        L.append(f"> **New:** {ch.get('new_language', '').strip() or '—'}")
        L.append("")
        L.append(f"{ch.get('meaning_for_customer', '')}")
        L.append("")

    actions = memo.get("action_items", [])
    if actions:
        L.append("**Action items.**")
        for a in actions:
            dl = _fmt_deadline(a.get("deadline"))
            owner = a.get("suggested_owner", "").strip()
            owner_str = f" _(owner: {owner})_" if owner else ""
            L.append(f"- [ ] {a['action']} — **{dl}**{owner_str}")
        L.append("")

    if memo.get("caveats"):
        L.append(f"**Caveats.** {memo['caveats']}")
        L.append("")
    return L


def _render_error(item: Dict[str, Any], n: int) -> List[str]:
    return [
        f"### {n}. [translation failed] {item.get('ref', '') or item.get('source_name', '')}",
        "",
        f"This finding could not be translated: `{item.get('error', 'unknown error')}`. "
        "The underlying change was still detected; review the raw snapshot diff.",
        "",
    ]


# --------------------------------------------------------------------------- #
# Markdown memo
# --------------------------------------------------------------------------- #

def render_markdown(
    items: List[Dict[str, Any]],
    *,
    run_time: datetime,
    watchlist,
    detection: Dict[str, Any],
    out_of_region_events: List[Dict[str, Any]] = None,
) -> str:
    out_of_region_events = out_of_region_events or []
    t = triage_split(items)
    urgent, review, noise, failed = t["urgent"], t["review"], t["noise"], t["failed"]
    verdict, _severity = build_verdict(items)

    o: List[str] = []
    o.append("# Infrastructure Legal Event Radar — Memo")
    o.append("")
    o.append(f"## {verdict}")
    o.append("")
    triage = (
        f"**Triage:** {len(urgent)} URGENT · {len(review)} REVIEW · {len(noise)} NOISE"
        + (f" · {len(failed)} error(s)" if failed else "")
        + (
            f" · {len(out_of_region_events)} out-of-region"
            if out_of_region_events
            else ""
        )
    )
    o.append(triage)
    o.append("")
    o.append(f"_{human_watchlist(watchlist)}_")
    o.append("")
    _sep(o)

    n = 1
    if urgent:
        o.append("## 🔴 URGENT — deadline within 30 days or active exposure")
        o.append("")
        for it in urgent:
            o += _render_item(it, n)
            n += 1
    if review:
        o.append("## 🟡 REVIEW — material, no immediate deadline")
        o.append("")
        for it in review:
            o += _render_item(it, n)
            n += 1
    if failed:
        o.append("## ⚠️ Translation errors")
        o.append("")
        for it in failed:
            o += _render_error(it, n)
            n += 1

    # Appendix — de-emphasized.
    if noise or out_of_region_events:
        _sep(o)
        o.append("## Appendix")
        o.append("")
        for it in noise:
            o += _render_item(it, n)
            n += 1
        if out_of_region_events:
            o.append("### Out-of-region operational events")
            o.append("")
            o.append(
                "_Not analyzed — these affect AWS regions outside your watchlist. "
                "Listed for awareness; confirm you have no footprint there._"
            )
            o.append("")
            o.append("| Region | Event | Started | Status |")
            o.append("| --- | --- | --- | --- |")
            for region, event, started, status in appendix_rows(out_of_region_events):
                o.append(f"| {region} | {event} | {started} | {status} |")
            o.append("")

    # Run summary.
    _sep(o)
    o.append("## Run")
    o.append("")
    collapsed, lines = run_summary_lines(detection)
    if collapsed:
        o.append(lines[0])
    else:
        for ln in lines:
            o.append(f"- {ln}")
    o.append("")

    # Footer: disclaimer + timestamp, small print.
    _sep(o)
    o.append(f"_{DISCLAIMER}_")
    o.append("")
    o.append(f"_Run: {run_time.strftime('%Y-%m-%d %H:%M UTC')}_")
    return "\n".join(o)


def write_memo(text: str, run_time: datetime, out_dir: str = "output") -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"legal-radar-memo-{run_time.strftime('%Y-%m-%d')}.md"
    path.write_text(text, encoding="utf-8")
    return path
