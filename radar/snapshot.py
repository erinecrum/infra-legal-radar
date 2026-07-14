"""Snapshot store: holds prior versions so the diff engine has a baseline.

Storage choice — plain files, not SQLite. Tradeoff:

* Files win on transparency and auditability. Each snapshot is a human-readable
  .txt (the terms/page text) plus a .json (metadata + any structured records).
  A lawyer — or opposing counsel, or a court — can open a snapshot directly and
  see exactly what AWS's terms said on a given date. When GitHub Actions commits
  snapshots weekly, `git diff` becomes a legally legible change history for free.
* SQLite would win if we needed relational queries across thousands of records.
  We don't: we compare "latest vs previous" per source. The query is trivial and
  the opacity cost (a binary blob you can't eyeball or diff in git) is not worth
  paying here.

Layout:
    snapshots/<source_id>/<UTC-timestamp>.txt    # normalized text (if any)
    snapshots/<source_id>/<UTC-timestamp>.json   # FetchResult metadata + items
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .sources.base import FetchResult


class Snapshot:
    """A previously stored snapshot, loaded back from disk."""

    def __init__(self, meta: Dict[str, Any], text: Optional[str], path: Path):
        self.meta = meta
        self.text = text
        self.path = path

    @property
    def fetched_at(self) -> str:
        return self.meta.get("fetched_at", "")

    @property
    def items(self) -> List[Dict[str, Any]]:
        return self.meta.get("items", [])


class SnapshotStore:
    def __init__(self, root: str | Path = "snapshots"):
        self.root = Path(root)

    def _dir(self, source_id: str) -> Path:
        return self.root / source_id

    def _stamps(self, source_id: str) -> List[str]:
        """Sorted list of snapshot timestamps present for a source (oldest→newest)."""
        d = self._dir(source_id)
        if not d.exists():
            return []
        stamps = sorted(p.stem for p in d.glob("*.json"))
        return stamps

    def latest(self, source_id: str) -> Optional[Snapshot]:
        """The most recent stored snapshot for a source, or None on first run."""
        stamps = self._stamps(source_id)
        if not stamps:
            return None
        return self._load(source_id, stamps[-1])

    def _load(self, source_id: str, stamp: str) -> Snapshot:
        d = self._dir(source_id)
        meta = json.loads((d / f"{stamp}.json").read_text(encoding="utf-8"))
        text_path = d / f"{stamp}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else None
        return Snapshot(meta=meta, text=text, path=d / stamp)

    def save(self, result: FetchResult) -> Path:
        """Persist a FetchResult as a new snapshot. Filename is the fetch time
        (UTC, filesystem-safe) so ordering is chronological and stable."""
        d = self._dir(result.source_id)
        d.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

        # Metadata + structured records go in JSON; large page text goes in a
        # sibling .txt so it diffs cleanly in git and stays human-readable.
        meta = asdict(result)
        text = meta.pop("text", None)
        (d / f"{stamp}.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if text is not None:
            (d / f"{stamp}.txt").write_text(text, encoding="utf-8")

        return d / f"{stamp}.json"
