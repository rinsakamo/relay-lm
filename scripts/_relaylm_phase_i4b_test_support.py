"""Shared Phase I-4B smoke helpers."""
from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from _relaylm_phase_i3_test_support import form_primary_memory, require
from relaylm_phase6c1_primary_worker_test_support import prepare_store

CHARACTER = "phase-i4b-character"
NAMESPACE = "phase-i4b-namespace"


@contextmanager
def prepared_store() -> Iterator[tuple[Path, str]]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    prepare_store(root)
    memory_id = form_primary_memory(
        root,
        namespace=NAMESPACE,
        candidate_id="phase-i4b-primary",
        title="好きな飲み物",
        summary="好きな飲み物は紅茶です。",
    )
    try:
        yield root, memory_id
    finally:
        temporary.cleanup()


def snapshot_tree(root: Path) -> tuple[tuple[str, str, int, str], ...]:
    entries: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, "symlink", 0, str(path.readlink())))
        elif path.is_dir():
            entries.append((relative, "dir", path.stat().st_mode & 0o7777, ""))
        elif path.is_file():
            payload = path.read_bytes()
            entries.append((
                relative,
                "file",
                path.stat().st_mode & 0o7777,
                hashlib.sha256(payload).hexdigest(),
            ))
        else:
            entries.append((relative, "other", 0, ""))
    return tuple(entries)


__all__ = [
    "CHARACTER",
    "NAMESPACE",
    "prepared_store",
    "require",
    "snapshot_tree",
]
