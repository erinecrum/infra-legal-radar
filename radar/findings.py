"""Assemble 'findings' — the packets handed to the translation layer.

A finding bundles one detected thing (an operational event, or a changed block
of terms/SLA text) with the context the rubric needs to judge it: the tracked
SLA thresholds, a pre-computed claim deadline, and the user's watchlist. Keeping
this assembly separate from both detection and translation means the model
always sees the same well-formed packet regardless of which source produced it.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .config import Watchlist
from .sla_util import compute_claim_deadline


def load_tracked_sla(store) -> Dict[str, Any]:
    """Read the current structured SLA data (thresholds, tiers, claim window)
    for the services we track, from the latest snapshots."""
    out: Dict[str, Any] = {}
    for source_id, label in [("sla_ec2", "EC2"), ("sla_s3", "S3")]:
        snap = store.latest(source_id)
        if snap:
            sla = (snap.meta.get("meta") or {}).get("sla")
            if sla:
                out[label] = sla
    return out


def _watchlist_payload(w: Watchlist) -> Any:
    if w.is_empty:
        return "none provided — report on everything"
    return {
        "aws_services_used": w.aws_services_used,
        "regions_used": w.regions_used,
        "heightened_concerns": w.heightened_concerns,
    }


def _claim_window_basis(sla_data: Dict[str, Any]) -> str:
    for label in ("EC2", "S3"):
        sla = sla_data.get(label)
        if sla and sla.get("claim_window_text"):
            return sla["claim_window_text"]
    return ""


def operational_event_finding(
    event: Dict[str, Any],
    *,
    detected_this_run: bool,
    change_kind: str,
    sla_data: Dict[str, Any],
    watchlist: Watchlist,
) -> Dict[str, Any]:
    """One open/new/updated Health event → a finding with SLA context and a
    Python-computed estimated claim deadline (rubric A.1 date math)."""
    # Both EC2 and S3 SLAs we track use the same claim window (end of the 2nd
    # billing cycle after the incident). Compute from the event start date.
    deadline = compute_claim_deadline(event.get("started_at"), months_after=2)

    payload = {
        "finding_type": "operational_event",
        "detected_this_run": detected_this_run,
        "change_kind": change_kind,  # "new", "updated", or "ongoing"
        "event": event,
        "tracked_sla_thresholds": sla_data,
        "estimated_claim_deadline": deadline.isoformat() if deadline else None,
        "claim_window_basis": _claim_window_basis(sla_data),
        "watchlist": _watchlist_payload(watchlist),
    }
    return {
        "kind": "operational_event",
        "source_name": "AWS Health Dashboard",
        "source_url": event.get("url", ""),
        "ref": event.get("id", ""),
        "payload": payload,
    }


def change_finding(
    *,
    source_name: str,
    source_url: str,
    old_language: str,
    new_language: str,
    is_sla: bool,
    sla_data: Dict[str, Any],
    watchlist: Watchlist,
) -> Dict[str, Any]:
    """One changed block of terms/SLA text → a finding for classification."""
    payload = {
        "finding_type": "sla_change" if is_sla else "terms_change",
        "source": source_name,
        "old_language": old_language,
        "new_language": new_language,
        "watchlist": _watchlist_payload(watchlist),
    }
    if is_sla:
        payload["tracked_sla_thresholds"] = sla_data
    return {
        "kind": "sla_change" if is_sla else "terms_change",
        "source_name": source_name,
        "source_url": source_url,
        "ref": "",
        "payload": payload,
    }
