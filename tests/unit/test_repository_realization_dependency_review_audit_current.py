from __future__ import annotations

from pathlib import Path

from tools.repository_realization_dependencies import (
    realization_dependency_review_signals,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_transitive_realization_review_audit() -> None:
    signals = realization_dependency_review_signals(REPOSITORY_ROOT)
    assert not signals, (
        "current transitive-only realization review signals:\n"
        + "\n".join(signals)
    )
