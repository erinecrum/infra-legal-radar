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


@dataclass
class Watchlist:
    """Coarse relevance hints. All fields optional; empty means 'report all'."""

    aws_services_used: List[str] = field(default_factory=list)
    regions_used: List[str] = field(default_factory=list)
    heightened_concerns: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.aws_services_used or self.regions_used or self.heightened_concerns
        )


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

    return Watchlist(
        aws_services_used=_as_str_list(data.get("aws_services_used")),
        regions_used=_as_str_list(data.get("regions_used")),
        heightened_concerns=_as_str_list(data.get("heightened_concerns")),
    )
