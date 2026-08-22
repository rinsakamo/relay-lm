from __future__ import annotations

from pathlib import Path

from tools.repository_realization_dependencies import (
    realization_dependency_review_summary,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_transitive_realization_review_reaudit() -> None:
    summary = realization_dependency_review_summary(REPOSITORY_ROOT)
    assert not summary, "current transitive-only owner-pair clusters:\n" + "\n".join(summary)
