"""Render translated findings into a single dated Markdown memo.

Output discipline (rubric C): items are ranked URGENT → REVIEW, with NOISE
demoted to a de-emphasized appendix. Every memo carries the standing disclaimer
that this is issue-spotting support, not legal advice.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_DISCLAIMER = (
    "*This memo is automated issue-spotting support, not legal advice. It "
    "screens and triages public AWS data; it does not conclude legal or credit "
    "eligibility. Every item requires attorney review against your actual "
    "AWS agreements, DPAs, and invoices before any action or reliance.*"
)

_RANK = {"URGENT": 0, "REVIEW": 1, "NOISE": 2}


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


def render_memo(
    items: List[Dict[str, Any]],
    *,
    run_time: datetime,
    watchlist_summary: str,
    detection_notes: List[str],
) -> str:
    good = [it for it in items if "memo" in it]
    failed = [it for it in items if "memo" not in it]

    good.sort(key=lambda it: _RANK.get(it["memo"].get("materiality", "REVIEW"), 1))
    urgent = [it for it in good if it["memo"].get("materiality") == "URGENT"]
    review = [it for it in good if it["memo"].get("materiality") == "REVIEW"]
    noise = [it for it in good if it["memo"].get("materiality") == "NOISE"]

    out: List[str] = []
    out.append("# Infrastructure Legal Event Radar — Memo")
    out.append(f"**Run:** {run_time.strftime('%Y-%m-%d %H:%M UTC')}")
    out.append(f"**Watchlist:** {watchlist_summary}")
    out.append("")
    out.append(_DISCLAIMER)
    out.append("")
    out.append("---")
    out.append("")

    # At-a-glance triage line.
    out.append(
        f"**Triage:** {len(urgent)} URGENT · {len(review)} REVIEW · "
        f"{len(noise)} NOISE"
        + (f" · {len(failed)} translation error(s)" if failed else "")
    )
    out.append("")

    if not good and not failed:
        out.append(
            "_No material events or changes detected this run. Detection ran "
            "cleanly against all sources (see run notes below)._"
        )
        out.append("")

    n = 1
    if urgent:
        out.append("## 🔴 URGENT — deadline within 30 days or active exposure")
        out.append("")
        for it in urgent:
            out += _render_item(it, n)
            n += 1
    if review:
        out.append("## 🟡 REVIEW — material, no immediate deadline")
        out.append("")
        for it in review:
            out += _render_item(it, n)
            n += 1
    if failed:
        out.append("## ⚠️ Translation errors")
        out.append("")
        for it in failed:
            out += _render_error(it, n)
            n += 1

    if noise:
        out.append("---")
        out.append("")
        out.append("## Appendix — NOISE (non-material changes)")
        out.append("")
        for it in noise:
            out += _render_item(it, n)
            n += 1

    # Run notes: what detection did, for auditability.
    out.append("---")
    out.append("")
    out.append("## Run notes")
    out.append("")
    for note in detection_notes:
        out.append(f"- {note}")
    out.append("")
    return "\n".join(out)


def write_memo(text: str, run_time: datetime, out_dir: str = "output") -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"legal-radar-memo-{run_time.strftime('%Y-%m-%d')}.md"
    path.write_text(text, encoding="utf-8")
    return path
