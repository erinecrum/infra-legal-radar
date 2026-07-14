"""Diff engine: detect what changed between the previous snapshot and now.

Two detection modes, matching the two `FetchResult` shapes:

* `diff_text` — for page-diff sources. Produces a unified diff plus the changed
  paragraphs isolated (old vs new), so the translation layer can quote short
  excerpts without being handed the entire 300 KB page.
* `diff_items` — for feed/structured sources. Detects records present now but
  not in the prior snapshot, keyed by each record's stable `id`.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChangedBlock:
    """One localized change: the old text and the new text that replaced it.
    Either side may be empty (pure addition or pure deletion)."""

    old: str
    new: str


@dataclass
class TextDiff:
    has_changes: bool
    added_lines: int = 0
    removed_lines: int = 0
    unified: str = ""  # full unified diff (for the appendix / audit trail)
    blocks: List[ChangedBlock] = field(default_factory=list)  # localized changes
    is_first_run: bool = False  # no prior snapshot existed


@dataclass
class ItemsDiff:
    has_changes: bool
    new_items: List[Dict[str, Any]] = field(default_factory=list)
    updated_items: List[Dict[str, Any]] = field(default_factory=list)
    is_first_run: bool = False


def _lines(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return text.splitlines()


def focused_excerpt(old: str, new: str, context: int = 90):
    """Return (old_excerpt, new_excerpt) windowed around the FIRST place the two
    strings actually differ.

    SLA/terms edits are often a single number or clause buried deep in a long
    paragraph. Showing the paragraph's head would render OLD and NEW as visually
    identical. This centers each excerpt on the real change so a reader — and the
    translation layer quoting excerpts — sees what moved."""
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            o = _window(old, i1, i2, context)
            n = _window(new, j1, j2, context)
            return o, n
    return old[: context * 2], new[: context * 2]


def _window(s: str, start: int, end: int, context: int) -> str:
    a = max(0, start - context)
    b = min(len(s), end + context)
    snippet = s[a:b].replace("\n", " ")
    return ("…" if a > 0 else "") + snippet + ("…" if b < len(s) else "")


def diff_text(old: Optional[str], new: str) -> TextDiff:
    """Compare two normalized page texts.

    On the very first run there is no `old`, so we report `is_first_run` and no
    changes — a baseline, not "the entire page was added". That distinction
    keeps the first memo from screaming about a change that is really just
    initialization.
    """
    if old is None:
        return TextDiff(has_changes=False, is_first_run=True)

    old_lines = _lines(old)
    new_lines = _lines(new)

    added = removed = 0
    unified = "\n".join(
        difflib.unified_diff(old_lines, new_lines, lineterm="", n=1)
    )

    # Localize changes into old/new block pairs using opcodes, so downstream
    # only sees the paragraphs that actually moved.
    blocks: List[ChangedBlock] = []
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        old_chunk = "\n".join(old_lines[i1:i2]).strip()
        new_chunk = "\n".join(new_lines[j1:j2]).strip()
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
        if old_chunk or new_chunk:
            blocks.append(ChangedBlock(old=old_chunk, new=new_chunk))

    return TextDiff(
        has_changes=bool(blocks),
        added_lines=added,
        removed_lines=removed,
        unified=unified,
        blocks=blocks,
    )


def diff_items(
    old_items: Optional[List[Dict[str, Any]]],
    new_items: List[Dict[str, Any]],
    revision_key: Optional[str] = None,
) -> ItemsDiff:
    """Detect records that changed since the prior snapshot, keyed by `id`.

    * New items = ids not present before.
    * Updated items = same id, but the value under `revision_key` changed. For
      the Health feed the revision fingerprint captures status + update count,
      so an *existing* event escalating from "degraded" to "disruption", or
      getting a new official update, is surfaced too — that escalation is often
      the legally material moment, not just the event's first appearance.
      Pass `revision_key=None` (default) to detect only brand-new items.

    First run establishes a baseline (nothing reported) for the same reason as
    `diff_text`: we don't want the first run to flag every currently open AWS
    event as if it just happened.
    """
    if old_items is None:
        return ItemsDiff(has_changes=False, is_first_run=True)

    old_by_id = {it.get("id"): it for it in old_items if it.get("id") is not None}
    seen = set(old_by_id)

    new: List[Dict[str, Any]] = []
    updated: List[Dict[str, Any]] = []
    for it in new_items:
        iid = it.get("id")
        if iid not in seen:
            new.append(it)
        elif revision_key is not None:
            if old_by_id[iid].get(revision_key) != it.get(revision_key):
                updated.append(it)

    return ItemsDiff(
        has_changes=bool(new or updated), new_items=new, updated_items=updated
    )
