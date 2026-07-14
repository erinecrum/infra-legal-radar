"""The pluggable source contract.

Every data source (Service Terms page, Health event feed, SLA pages, and any
v2 source added later) implements `Source.fetch()` and returns a `FetchResult`.
The rest of the pipeline — snapshot store, diff engine, translation layer —
only ever sees `FetchResult`, so new sources plug in without touching them.

Two shapes of content share one type:

* Page-diff sources (Service Terms, SLA pages) populate `text`: a normalized,
  line-oriented rendering of the page that the diff engine compares run-to-run.
* Feed/structured sources (Health events, parsed SLA thresholds) populate
  `items`: a list of identified records. The diff engine detects *new* items
  by their `id`.

A source may populate both (e.g. an SLA page has diffable text AND extracted
threshold records).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class FetchResult:
    """Normalized output of a source fetch. This is the only shape the rest of
    the pipeline understands."""

    source_id: str  # stable slug, used for snapshot paths (e.g. "service_terms")
    name: str  # human-readable name for memos
    url: str  # where it came from (for citations in the memo)
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    kind: str = "page_diff"  # "page_diff" | "event_feed" | "sla"

    # Page-diff payload: normalized text, one logical block per line.
    text: Optional[str] = None

    # Structured payload: list of records, each SHOULD carry a stable "id".
    items: List[Dict[str, Any]] = field(default_factory=list)

    # Free-form extras a source wants preserved in the snapshot (e.g. parsed
    # SLA thresholds). Not diffed as text; carried for the translation layer.
    meta: Dict[str, Any] = field(default_factory=dict)


class Source(abc.ABC):
    """Base class for all sources. Subclasses set the class attributes and
    implement `fetch()`."""

    source_id: str = ""
    name: str = ""
    url: str = ""
    kind: str = "page_diff"

    @abc.abstractmethod
    def fetch(self) -> FetchResult:
        """Retrieve current content and return it normalized. Should raise on a
        hard failure (network error, unexpected empty page) so the runner can
        report the source as failed rather than silently recording a blank
        snapshot that would look like 'everything was deleted' on the next diff."""
        raise NotImplementedError
