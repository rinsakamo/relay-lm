"""I-4D unified Correct/Forget current-state projection for ordinary retrieval.

The shared scanner remains the only parser for correction receipts, prepared
operations, hidden successors, controls, and finalized tombstones. I-4D exposes
that complete fail-closed currentness to ordinary Primary recall. M2 still owns
candidate discovery, relevance ordering, caps, and budgets.
"""
from __future__ import annotations

import stat
from pathlib import Path, PurePosixPath

from . import _relaymem_primary_current_state_impl as _impl
from ._relaymem_primary_page_writer_common import MAX_PAGE_BYTES, TARGET_DIR

_MAX_RETRIEVAL_FILES = 2_048
_MAX_CONTROL_BYTES = 65_536
_MAX_ARTIFACT_BYTES = 1_048_576


def load_primary_current_state_index(
    store_root: str | Path, *, namespace: str
) -> _impl.PrimaryCorrectionStateIndex:
    """Return one read-only Correct/Forget lifecycle index for retrieval.

    A prepared operation makes the current physical revision pending as well as
    any declared successor. Finalized Forget state keeps the hidden successor as
    canonical current state, so every prior active physical revision remains
    non-current without fallback.
    """

    combined = _impl.load_primary_current_state_index(
        store_root, namespace=namespace
    )
    if not _retrieval_files_safe(Path(store_root)):
        return _impl.empty_primary_current_state_index(invalid={"*"})

    pending_physical = set(combined.pending_physical)
    for logical in combined.pending_logical:
        current = combined.current_by_logical.get(logical, (logical, 1))
        pending_physical.add(current[0])
    return _impl.PrimaryCorrectionStateIndex(
        current_by_logical=combined.current_by_logical,
        logical_by_physical=combined.logical_by_physical,
        superseded_physical=combined.superseded_physical,
        pending_physical=frozenset(pending_physical),
        invalid_logical=combined.invalid_logical,
        receipts_by_logical=combined.receipts_by_logical,
        pending_logical=combined.pending_logical,
    )


def _retrieval_files_safe(root: Path) -> bool:
    """Bounded stable reread for every file that can affect Primary currentness."""

    checks: list[tuple[Path, int]] = [
        (root / "memory/mem/index.md", _MAX_CONTROL_BYTES),
        (root / "memory/mem/log.md", _MAX_CONTROL_BYTES),
    ]
    seen = 0
    for relative in TARGET_DIR.values():
        directory = root / PurePosixPath(relative)
        scanned = _bounded_files(directory, suffix=".md")
        if scanned is None:
            return False
        seen += len(scanned)
        checks.extend((path, MAX_PAGE_BYTES) for path in scanned)
    mutation_root = root / "memory/mem/corrections/v0"
    scanned = _bounded_files(mutation_root, suffix=None)
    if scanned is None:
        return False
    seen += len(scanned)
    checks.extend((path, _MAX_ARTIFACT_BYTES) for path in scanned)
    if seen > _MAX_RETRIEVAL_FILES:
        return False
    return all(_stable_regular_file(path, maximum) for path, maximum in checks)


def _bounded_files(directory: Path, *, suffix: str | None) -> list[Path] | None:
    if not directory.exists():
        return []
    try:
        root_stat = directory.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        return None
    output: list[Path] = []
    try:
        for path in directory.rglob("*"):
            if len(output) > _MAX_RETRIEVAL_FILES:
                return None
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                return None
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode):
                return None
            if suffix is None or path.name.endswith(suffix):
                output.append(path)
    except OSError:
        return None
    return output


def _stable_regular_file(path: Path, maximum: int) -> bool:
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum
        ):
            return False
        raw = path.read_bytes()
        after = path.lstat()
    except OSError:
        return False
    before_key = (
        before.st_dev,
        before.st_ino,
        stat.S_IFMT(before.st_mode),
        before.st_nlink,
        before.st_size,
    )
    after_key = (
        after.st_dev,
        after.st_ino,
        stat.S_IFMT(after.st_mode),
        after.st_nlink,
        after.st_size,
    )
    return before_key == after_key and len(raw) == after.st_size


__all__ = ["load_primary_current_state_index"]
