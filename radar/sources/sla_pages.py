"""Source: AWS Service Level Agreement pages.

Covers the SLA index plus the per-service SLA pages we track (EC2 and S3 for
v1). Each page is snapshotted and diffed like any page-diff source — a quiet
edit to an uptime commitment or a credit percentage is precisely what this tool
exists to catch, so it gets top billing in the memo (rubric B.3).

In addition, the EC2 and S3 pages are *parsed into structured data*
(`meta["sla"]`): the headline commitment, every credit tier (uptime bracket →
credit %), and the claim-window language plus its computed rule. The translation
layer needs these as data to screen operational events for credit eligibility
and to estimate claim deadlines — it can't reliably do that from prose.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from ..sla_util import parse_billing_cycle_ordinal
from .base import FetchResult, Source

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_CONTENT_SELECTORS = ["#aws-page-content-main", "main", "#aws-page-content"]
_TIMEOUT = 30

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _content(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    container = None
    for sel in _CONTENT_SELECTORS:
        container = soup.select_one(sel)
        if container is not None:
            break
    container = container or soup
    for tag in container.select("script, style, noscript"):
        tag.decompose()
    return container


def _normalize_text(container: BeautifulSoup) -> str:
    raw = container.get_text("\n")
    lines = []
    for line in raw.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _percents(s: str) -> List[float]:
    return [float(x) for x in _PCT_RE.findall(s)]


def _parse_tier_table(table) -> Optional[Dict[str, Any]]:
    """Parse one credit-tier table into {metric, applies_to, rows[]}."""
    rows = table.find_all("tr")
    if not rows:
        return None

    header = [re.sub(r"\s+", " ", c.get_text(" ")).strip()
              for c in rows[0].find_all(["td", "th"])]
    # We only care about tables whose first column is an uptime metric.
    if not header or "Uptime Percentage" not in header[0]:
        return None
    metric = header[0]

    parsed_rows: List[Dict[str, Any]] = []
    for r in rows[1:]:
        cells = [re.sub(r"\s+", " ", c.get_text(" ")).strip()
                 for c in r.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        condition, credit_cell = cells[0], cells[1]
        bounds = _percents(condition)
        credit_vals = _percents(credit_cell)
        if not bounds or not credit_vals:
            continue
        # "Less than U% but ... greater than ... L%" → upper=U, lower=L.
        # "Less than 95.0%" → upper=95.0, lower=0.0 (bottom tier).
        upper = bounds[0]
        lower = bounds[1] if len(bounds) > 1 else 0.0
        parsed_rows.append(
            {
                "condition": condition,
                "upper_percent": upper,
                "lower_percent": lower,
                "credit_percent": credit_vals[0],
            }
        )
    if not parsed_rows:
        return None

    # Name the tier group by the paragraph that introduces the table (identical
    # headers otherwise, e.g. S3 Standard vs Intelligent-Tiering).
    applies_to = ""
    prev = table.find_previous(["p", "h2", "h3", "h4"])
    if prev:
        applies_to = re.sub(r"\s+", " ", prev.get_text(" ")).strip()[:180]

    return {"metric": metric, "applies_to": applies_to, "rows": parsed_rows}


def _extract_claim_window(text: str) -> Dict[str, Any]:
    """Pull the exact claim-window sentence and its billing-cycle rule."""
    window_text = ""
    m = re.search(
        r"(?:credit request must be received|must be received by us)[^.]*\.",
        text, re.IGNORECASE,
    )
    if m:
        window_text = re.sub(r"\s+", " ", m.group(0)).strip()

    n = parse_billing_cycle_ordinal(text)
    rule = None
    if n is not None:
        rule = {
            "type": "end_of_nth_billing_cycle_after_incident",
            "billing_cycles_after_incident": n,
            "note": "Billing cycle = calendar month; deadline is end of that month.",
        }
    return {"claim_window_text": window_text, "claim_window_rule": rule}


def _extract_sla(container: BeautifulSoup, service_label: str, url: str) -> Dict[str, Any]:
    tiers: List[Dict[str, Any]] = []
    for table in container.find_all("table"):
        parsed = _parse_tier_table(table)
        if parsed:
            tiers.append(parsed)

    # Headline commitment = highest uptime bracket at which credits begin
    # (the value the service promises to meet). Taken from the first tier group.
    commitment_percent = None
    if tiers and tiers[0]["rows"]:
        commitment_percent = max(r["upper_percent"] for r in tiers[0]["rows"])

    text = _normalize_text(container)
    claim = _extract_claim_window(text)

    return {
        "service": service_label,
        "commitment_percent": commitment_percent,
        "tier_groups": tiers,
        "source_url": url,
        **claim,
    }


class SlaPageSource(Source):
    """One SLA page. Set `extract=True` to also parse structured thresholds."""

    kind = "sla"

    def __init__(
        self,
        source_id: str,
        name: str,
        url: str,
        service_label: str = "",
        extract: bool = True,
    ):
        self.source_id = source_id
        self.name = name
        self.url = url
        self.service_label = service_label
        self.extract = extract

    def fetch(self) -> FetchResult:
        resp = requests.get(self.url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()

        container = _content(resp.text)
        text = _normalize_text(container)
        if len(text) < 500:
            raise RuntimeError(
                f"{self.name}: content suspiciously short ({len(text)} chars); "
                "refusing to snapshot. Page layout/selectors may have changed."
            )

        meta: Dict[str, Any] = {"char_count": len(text)}
        if self.extract:
            sla = _extract_sla(container, self.service_label or self.name, self.url)
            meta["sla"] = sla

        return FetchResult(
            source_id=self.source_id,
            name=self.name,
            url=self.url,
            kind=self.kind,
            text=text,
            meta=meta,
        )


def ec2_sla() -> SlaPageSource:
    return SlaPageSource(
        "sla_ec2", "AWS EC2 SLA", "https://aws.amazon.com/compute/sla/",
        service_label="EC2", extract=True,
    )


def s3_sla() -> SlaPageSource:
    return SlaPageSource(
        "sla_s3", "AWS S3 SLA", "https://aws.amazon.com/s3/sla/",
        service_label="S3", extract=True,
    )


def sla_index() -> SlaPageSource:
    return SlaPageSource(
        "sla_index", "AWS SLA Index",
        "https://aws.amazon.com/legal/service-level-agreements/",
        extract=False,  # index is a link list; diff-only, no thresholds to parse
    )
