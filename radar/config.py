"""Load the optional, non-confidential watchlist config.

Design note: every field is optional. A missing file, an empty file, or a
missing field all resolve to "no preference" — meaning the tool reports on
everything rather than silently filtering. We never fail a run because config
is absent; the detection layer must work with zero configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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


@dataclass
class EmailConfig:
    """Settings for emailing the memo.

    Split by sensitivity: the recipient and SMTP host/port are non-secret and
    live in config.yaml (so the scheduled GitHub Actions run gets them for free);
    the SMTP username and app password are secrets and come only from the
    environment (.env locally, Actions secrets in CI) — never from committed
    files.
    """

    to: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""  # from env SMTP_USERNAME (also the From address)
    password: str = ""  # from env SMTP_APP_PASSWORD

    @property
    def from_addr(self) -> str:
        return self.username or self.to

    @property
    def is_enabled(self) -> bool:
        """A send should be attempted only when a recipient is configured."""
        return bool(self.to)

    def missing_credentials(self) -> List[str]:
        """Which required secrets are absent (for a clear error message)."""
        missing = []
        if not self.username:
            missing.append("SMTP_USERNAME")
        if not self.password:
            missing.append("SMTP_APP_PASSWORD")
        return missing


def load_email_config(path: str | Path = "config.yaml") -> EmailConfig:
    """Recipient + SMTP host/port from YAML; credentials from the environment.

    Gmail app passwords are often displayed with spaces (e.g. "abcd efgh ijkl
    mnop"); we strip whitespace so pasting either form works."""
    data = {}
    p = Path(path)
    if p.exists():
        with p.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        if isinstance(loaded, dict):
            data = loaded

    try:
        port = int(data.get("smtp_port", 587))
    except (TypeError, ValueError):
        port = 587

    password = os.environ.get("SMTP_APP_PASSWORD", "")
    return EmailConfig(
        to=str(data.get("email_to", "") or "").strip(),
        smtp_host=str(data.get("smtp_host", "smtp.gmail.com") or "smtp.gmail.com").strip(),
        smtp_port=port,
        username=os.environ.get("SMTP_USERNAME", "").strip(),
        password="".join(password.split()),  # tolerate app passwords with spaces
    )
