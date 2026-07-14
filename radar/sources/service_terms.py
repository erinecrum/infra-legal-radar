"""Source: AWS Service Terms page (https://aws.amazon.com/service-terms/).

This is the single terms document that governs use of AWS services. We snapshot
its full text on each run and diff it, because a quiet edit here — a changed
liability cap, a new AI/ML clause, a shifted data-handling promise — is exactly
the kind of thing an infrastructure counsel must catch.

Normalization: we extract only the main content container and render it as one
logical block per line. Line-oriented text means a single edited paragraph
shows up as a single changed line in the diff, instead of the whole document
reshuffling.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .base import FetchResult, Source

_URL = "https://aws.amazon.com/service-terms/"
# A normal browser UA; AWS serves the marketing/legal pages fine with this and
# returns a stripped/blocked response to an empty UA.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
# Preferred content container on the AWS page, with fallbacks so a template
# tweak doesn't blank the snapshot.
_CONTENT_SELECTORS = ["#aws-page-content-main", "main", "#aws-page-content"]
_TIMEOUT = 30


def _normalize(html: str) -> str:
    """Extract the terms text and render it line-oriented for clean diffing."""
    soup = BeautifulSoup(html, "html.parser")

    container = None
    for sel in _CONTENT_SELECTORS:
        container = soup.select_one(sel)
        if container is not None:
            break
    if container is None:
        container = soup  # last resort: whole document

    # Drop non-content noise that would create phantom diffs.
    for tag in container.select("script, style, noscript"):
        tag.decompose()

    # One line per logical block. get_text with a newline separator gives us
    # block boundaries; we then squeeze intra-line whitespace and drop blanks.
    raw = container.get_text("\n")
    lines = []
    for line in raw.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


class ServiceTermsSource(Source):
    source_id = "service_terms"
    name = "AWS Service Terms"
    url = _URL
    kind = "page_diff"

    def fetch(self) -> FetchResult:
        resp = requests.get(self.url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()

        text = _normalize(resp.text)
        if len(text) < 1000:
            # Sanity guard: the real terms page is hundreds of KB of text. A tiny
            # result means we were blocked or the layout changed — fail loudly
            # rather than record a near-empty snapshot that the next run would
            # read as "AWS deleted its entire terms document".
            raise RuntimeError(
                f"Service Terms content suspiciously short ({len(text)} chars); "
                "refusing to snapshot. The page layout or selectors may have changed."
            )

        # Best-effort capture of the "Last Updated" date for the memo header.
        last_updated = ""
        m = re.search(r"Last Updated:\s*([A-Za-z0-9 ,]+)", text)
        if m:
            last_updated = m.group(1).strip()

        return FetchResult(
            source_id=self.source_id,
            name=self.name,
            url=self.url,
            kind=self.kind,
            text=text,
            meta={"last_updated": last_updated, "char_count": len(text)},
        )
