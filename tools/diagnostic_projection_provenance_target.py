"""Canonical physical-queue adapter for RelayLM #3006 projection provenance.

The public physical runner owns environment/fresh-ref/queue admission. This
module requires the inherited canonical queue lease and delegates exactly once
to the diagnostic execute-once wrapper. It does not interpret, retry, or repair
the measured result.
"""

from __future__ import annotations

import fcntl
import importlib.util
import os
import sys
from collections.abc import Sequence
from pathlib import Path

TARGET_NAME = "diagnostic:3006-projection-provenance"
EXPECTED_ATTEMPT_ID = "layer0-projection-provenance-20260925-a"
EXPECTED_DESCRIPTOR_GENERATION = "provenance-measured-descriptor-20260925-b"
QUEUE_LEASE_FD_ENV = "RELAYLM_PHYSICAL_QUEUE_LEASE_FD"
CANONICAL_LOCK_PATH = Path(
    "/tmp/relaylm/physical/locks/a820834e5681ba28.lock"
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TARGET = (
    _REPO_ROOT
    / "diagnostics"
    / "llama-cpp"
    / "e2d2c0d6-gemma4-layer0-projection-provenance-execute-once.py"
)


class ProjectionProvenanceTargetError(RuntimeError):
    pass


def _load_target():
    if not _TARGET.is_file():
        raise ProjectionProvenanceTargetError(f"measured wrapper missing: {_TARGET}")
    spec = importlib.util.spec_from_file_location(
        "relaylm_3006_projection_provenance_execute_once", _TARGET
    )
    if spec is None or spec.loader is None:
        raise ProjectionProvenanceTargetError("cannot load measured execute-once wrapper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if getattr(module, "ATTEMPT_ID", None) != EXPECTED_ATTEMPT_ID:
        raise ProjectionProvenanceTargetError("measured attempt identity drift")
    if (
        getattr(module, "EXPECTED_DESCRIPTOR_GENERATION", None)
        != EXPECTED_DESCRIPTOR_GENERATION
    ):
        raise ProjectionProvenanceTargetError("descriptor generation identity drift")
    if not callable(getattr(module, "main", None)):
        raise ProjectionProvenanceTargetError("measured wrapper main() missing")
    return module


def _require_inherited_queue_lease_fd() -> int:
    expected = str(CANONICAL_LOCK_PATH)
    candidates: list[int] = []
    for entry in Path("/proc/self/fd").iterdir():
        if not entry.name.isdigit():
            continue
        fd = int(entry.name)
        if fd <= 2:
            continue
        try:
            target = os.readlink(entry)
        except OSError:
            continue
        if target == expected:
            candidates.append(fd)

    if len(candidates) != 1:
        raise ProjectionProvenanceTargetError(
            f"expected exactly one inherited canonical queue lease fd, got {candidates}"
        )

    fd = candidates[0]
    probe = CANONICAL_LOCK_PATH.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
            raise ProjectionProvenanceTargetError(
                "inherited canonical queue fd exists but no queue flock is held"
            )
    finally:
        probe.close()
    return fd


def main(argv: Sequence[str] | None = None) -> int:
    module = _load_target()
    lease_fd = _require_inherited_queue_lease_fd()

    old_argv = sys.argv
    old_lease = os.environ.get(QUEUE_LEASE_FD_ENV)
    try:
        os.environ[QUEUE_LEASE_FD_ENV] = str(lease_fd)
        if argv is not None:
            sys.argv = [str(_TARGET), *argv]
        return int(module.main())
    finally:
        sys.argv = old_argv
        if old_lease is None:
            os.environ.pop(QUEUE_LEASE_FD_ENV, None)
        else:
            os.environ[QUEUE_LEASE_FD_ENV] = old_lease


if __name__ == "__main__":
    raise SystemExit(main())
