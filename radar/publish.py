"""Publish dashboard data as static JSON under docs/data/ for GitHub Pages.

Two files:
  docs/data/events.json — a rolling history of parsed AWS Health events. Each run
    merges the current feed in (keyed by ARN), so the site can show *recent*
    events over time, not just this run's snapshot. Pruned to a time window and
    a hard cap so the file stays small.
  docs/data/memo.json — the latest memo summary: verdict, severity, triage
    counts, and the material item headlines. Drives the banner at the top.

No secrets are ever written here — this is public, static data read by a
backend-less single-page site.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_KEEP_DAYS = 180   # drop events not seen in the last ~6 months
_MAX_EVENTS = 500  # hard cap on the published history


def _event_record(e: Dict[str, Any]) -> Dict[str, Any]:
    """The public shape for one event — only fields the dashboard needs."""
    return {
        "id": e.get("id"),
        "region_code": e.get("region_code", ""),
        "region_name": e.get("region_name", ""),
        "availability_zones": e.get("availability_zones", []) or [],
        "service_name": e.get("service_name", ""),
        "summary": e.get("summary", ""),
        "status_code": e.get("status_code", ""),
        "status_label": e.get("status_label", ""),
        "resolved": bool(e.get("resolved", False)),
        "started_at": e.get("started_at", ""),
        "last_update_at": e.get("last_update_at", ""),
        "duration_hours": e.get("duration_hours"),
        "impacted_service_count": e.get("impacted_service_count", 0),
        "impacted_services": e.get("impacted_services", []) or [],
        "url": e.get("url", ""),
    }


def _parse_dt(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def publish_dashboard(
    docs_dir: str,
    *,
    events: List[Dict[str, Any]],
    memo_json: Dict[str, Any],
    run_time: datetime,
) -> Dict[str, Any]:
    """Merge events into the rolling history and write both JSON files.
    Returns a small summary dict for the console."""
    data_dir = Path(docs_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    now_iso = run_time.astimezone(timezone.utc).isoformat()
    events_path = data_dir / "events.json"

    # Load prior history (tolerate a missing/corrupt file — never crash a run).
    existing: List[Dict[str, Any]] = []
    if events_path.exists():
        try:
            loaded = json.loads(events_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except (ValueError, OSError):
            existing = []

    by_id: Dict[str, Dict[str, Any]] = {
        r.get("id"): r for r in existing if r.get("id")
    }

    for e in events:
        rec = _event_record(e)
        if not rec["id"]:
            continue
        prior = by_id.get(rec["id"])
        rec["first_seen"] = (prior or {}).get("first_seen", now_iso)
        rec["last_seen"] = now_iso
        by_id[rec["id"]] = rec

    # Prune by how recently each event was seen (keeps long-running open events
    # that started outside the window but are still live), then cap.
    cutoff = run_time.astimezone(timezone.utc) - timedelta(days=_KEEP_DAYS)
    kept = []
    for r in by_id.values():
        seen = _parse_dt(r.get("last_seen"))
        if seen is None or seen >= cutoff:
            kept.append(r)
    kept.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    kept = kept[:_MAX_EVENTS]

    events_path.write_text(
        json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (data_dir / "memo.json").write_text(
        json.dumps(memo_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"events_published": len(kept), "path": str(data_dir)}
