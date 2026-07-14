"""Load the optional, non-confidential watchlist config.

Design note: every field is optional. A missing file, an empty file, or a
missing field all resolve to "no preference" — meaning the tool reports on
everything rather than silently filtering. We never fail a run because config
is absent; the detection layer must work with zero configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


VALID_FILTER_MODES = ("strict", "appendix")


@dataclass
class Watchlist:
    """Coarse relevance hints. All fields optional; empty means 'report all'."""

    aws_services_used: List[str] = field(default_factory=list)
    regions_used: List[str] = field(default_factory=list)
    heightened_concerns: List[str] = field(default_factory=list)
    # How to handle operational events outside regions_used:
    #   "appendix" (default) — demote to one-line entries in the NOISE appendix
    #   "strict"             — exclude them entirely
    # Only takes effect when regions_used is non-empty.
    region_filter_mode: str = "appendix"

    @property
    def is_empty(self) -> bool:
        return not (
            self.aws_services_used or self.regions_used or self.heightened_concerns
        )

    def region_status(self, region_code: str = "", region_name: str = "") -> str:
        """Classify an operational event's region against the watchlist.

        Returns one of:
          "unfiltered"   — no regions configured, so no filtering applies
          "global"       — global / region-less / multi-region: ALWAYS in scope
          "in_scope"     — event region is one of regions_used
          "out_of_scope" — event region is not in regions_used

        Global and region-less events are always in scope by design: a global
        service disruption can affect workloads in any region, so it must never
        be filtered out on region grounds.
        """
        if not self.regions_used:
            return "unfiltered"
        rc = (region_code or "").strip().lower()
        rn = (region_name or "").strip().lower()
        # Global / region-less only when we truly can't pin a specific region
        # (empty or literal "global"); a blank human name alone is not enough.
        if rc in ("", "global") or rn == "global":
            return "global"
        if rc in {r.strip().lower() for r in self.regions_used}:
            return "in_scope"
        return "out_of_scope"


def _as_str_list(value) -> List[str]:
    """Coerce a YAML value into a clean list of stripped, non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def load_watchlist(path: str | Path = "config.yaml") -> Watchlist:
    """Read the watchlist YAML. Returns an empty Watchlist if the file is
    missing or blank, so callers never have to special-case 'no config'."""
    p = Path(path)
    if not p.exists():
        return Watchlist()

    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        # Malformed file — treat as no config rather than crashing a scheduled run.
        return Watchlist()

    mode = str(data.get("region_filter_mode", "appendix")).strip().lower()
    if mode not in VALID_FILTER_MODES:
        # Unknown/invalid value → safe default rather than a crashed run.
        mode = "appendix"

    return Watchlist(
        aws_services_used=_as_str_list(data.get("aws_services_used")),
        regions_used=_as_str_list(data.get("regions_used")),
        heightened_concerns=_as_str_list(data.get("heightened_concerns")),
        region_filter_mode=mode,
    )
