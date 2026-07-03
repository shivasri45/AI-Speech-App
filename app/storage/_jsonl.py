"""Shared JSONL helpers used by every store.

We deliberately keep these tiny — append-only writes, read-all-and-filter
queries. That's fine at the scale this platform targets (low hundreds of
students per institution). When data volume grows past that, swap the
store implementations to a real DB; the protocols above stay the same.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Iterable

from app.core.logger import logger


# One lock per file path. Two writes to the same file serialize through
# this; writes to different files run in parallel.
_file_locks: dict[str, Lock] = {}


def _lock_for(path: Path) -> Lock:
    key = str(path.resolve())
    existing = _file_locks.get(key)
    if existing is None:
        existing = Lock()
        _file_locks[key] = existing
    return existing


def append_jsonl(path: Path, record: dict) -> None:
    """Append `record` as one JSON line. Creates parent dir if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with _lock_for(path):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read every line as a dict. Skips malformed rows with a warning."""
    if not path.exists():
        return []

    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Skipping malformed row in %s: %s", path, exc)
    return records


def overwrite_jsonl(path: Path, records: Iterable[dict]) -> None:
    """Rewrite the file from scratch. Use sparingly — append is preferred."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with _lock_for(path):
        with open(tmp_path, "w", encoding="utf-8") as fh:
            for record in records:
                fh.write(
                    json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                )
        tmp_path.replace(path)
