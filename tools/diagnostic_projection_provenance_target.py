"""Canonical physical-queue adapter for RelayLM #3006 projection provenance.

The public physical runner owns environment/fresh-ref/queue admission. This
module delegates exactly once to the diagnostic execute-once wrapper and does
not interpret, retry, or repair its result.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path

TARGET_NAME = "diagnostic:3006-projection-provenance"
EXPECTED_ATTEMPT_ID = "layer0-projection-provenance-20260925-a"
EXPECTED_DESCRIPTOR_GENERATION = "provenance-measured-descriptor-20260925-b"

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


def main(argv: Sequence[str] | None = None) -> int:
    module = _load_target()
    if argv is None:
        return int(module.main())

    old_argv = sys.argv
    try:
        sys.argv = [str(_TARGET), *argv]
        return int(module.main())
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
