"""Source: AWS Health Dashboard public event feed.

SOURCE CHOICE (logged here and in the README):
AWS exposes public operational status three ways: (a) per-service/region RSS
feeds under status.aws.amazon.com/rss/<service-region>.rss, (b) an aggregate
RSS at .../rss/all.rss, and (c) a single JSON document behind the Health
Dashboard at https://health.aws.amazon.com/public/currentevents (which
status.aws.amazon.com/data.json mirrors). We use the JSON feed.

Why the JSON, not RSS:
* One request covers every service and region. The per-service RSS approach
  would require guessing and polling dozens of feed URLs, most of them empty.
* It is richer and already structured: each event carries a stable ARN, a start
  timestamp, a status code, the full timestamped update log, and the complete
  list of impacted services — the raw material the legal rubric needs (blast
  radius, duration, AZ/region scope). RSS gives us title + description prose.
* The ARN is a durable unique id, which makes run-to-run new/updated detection
  reliable.

Caveat: `currentevents` reflects currently open/recent events, not full history.
That fits v1 ("events since last run"): we snapshot each run and diff, so we see
events appear and escalate over time.

Status codes observed in the feed: "0" normal/resolved, "1" informational,
"2" degraded performance, "3" service disruption.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from .base import FetchResult, Source

_URL = "https://health.aws.amazon.com/public/currentevents"
_DASHBOARD = "https://health.aws.amazon.com/health/status"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TIMEOUT = 30

_STATUS_LABELS = {
    "0": "Operating normally / resolved",
    "1": "Informational",
    "2": "Degraded performance",
    "3": "Service disruption",
}

# Matches AWS AZ identifiers embedded in update text, e.g. "mec1-az2", "use1-az4".
_AZ_RE = re.compile(r"\b[a-z]{2,4}\d?-az\d+\b", re.IGNORECASE)


def _epoch_to_iso(value: Any) -> str:
    """Feed timestamps are unix seconds (occasionally milliseconds). Normalize."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return ""
    if v > 10_000_000_000:  # clearly milliseconds
        v //= 1000
    return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()


def _region_code_from_arn(arn: str, fallback: str) -> str:
    """ARN shape: arn:aws:health:<region>::event/... — region is field index 3."""
    parts = arn.split(":")
    if len(parts) > 3 and parts[3]:
        return parts[3]
    return fallback or "global"


def _decode(content: bytes) -> Any:
    """The endpoint serves UTF-16 (with BOM). Fall back to UTF-8 defensively."""
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(content.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError("Could not decode/parse the AWS Health feed payload.")


def _parse_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    arn = raw.get("arn", "")
    status_code = str(raw.get("status", ""))
    log = raw.get("event_log") or []

    # Timeline: start = `date`; latest update = max event_log timestamp.
    start_iso = _epoch_to_iso(raw.get("date"))
    ts = [e.get("timestamp") for e in log if e.get("timestamp") is not None]
    last_iso = _epoch_to_iso(max(ts)) if ts else start_iso
    duration_hours = None
    if ts:
        try:
            span = (int(max(ts)) - int(raw.get("date"))) / 3600.0
            duration_hours = round(span, 1)
        except (TypeError, ValueError):
            duration_hours = None

    impacted = raw.get("impacted_services") or {}
    impacted_names = sorted(
        {v.get("service_name", k) for k, v in impacted.items()}
    ) if isinstance(impacted, dict) else []

    # AZ hints across all update messages — signals a zone-scoped event, which
    # the rubric treats as a data-residency / failover trigger.
    az_hits = set()
    text_blob = " ".join(
        str(e.get("message", "")) + " " + str(e.get("summary", "")) for e in log
    )
    for m in _AZ_RE.findall(text_blob):
        az_hits.add(m.lower())

    latest_message = ""
    if log:
        latest_message = str(log[-1].get("message", "")).strip()

    return {
        "id": arn,  # stable id used by the diff engine
        "summary": raw.get("summary", ""),
        "service_name": raw.get("service_name", ""),
        "service": raw.get("service", ""),
        "region_name": raw.get("region_name", ""),
        "region_code": _region_code_from_arn(arn, raw.get("region_name", "")),
        "status_code": status_code,
        "status_label": _STATUS_LABELS.get(status_code, f"Unknown ({status_code})"),
        "resolved": status_code == "0",
        "started_at": start_iso,
        "last_update_at": last_iso,
        "duration_hours": duration_hours,
        "update_count": len(log),
        "impacted_service_count": len(impacted_names),
        "impacted_services": impacted_names,
        "availability_zones": sorted(az_hits),
        "latest_message": latest_message,
        "url": _DASHBOARD,
        # Fingerprint for update detection: changes when status escalates or a
        # new official update is posted.
        "revision": f"{status_code}:{len(log)}:{last_iso}",
    }


class HealthEventsSource(Source):
    source_id = "health_events"
    name = "AWS Health Dashboard"
    url = _URL
    kind = "event_feed"

    def fetch(self) -> FetchResult:
        resp = requests.get(self.url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()

        data = _decode(resp.content)
        if not isinstance(data, list):
            raise RuntimeError(
                f"Unexpected Health feed shape: {type(data).__name__}, expected list."
            )

        events: List[Dict[str, Any]] = []
        for raw in data:
            if isinstance(raw, dict) and raw.get("arn"):
                events.append(_parse_event(raw))

        # Newest first for readable console/memo output.
        events.sort(key=lambda e: e.get("started_at", ""), reverse=True)

        return FetchResult(
            source_id=self.source_id,
            name=self.name,
            url=self.url,
            kind=self.kind,
            items=events,
            meta={"event_count": len(events), "dashboard": _DASHBOARD},
        )
