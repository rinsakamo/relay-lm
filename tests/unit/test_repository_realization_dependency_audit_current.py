from __future__ import annotations

from pathlib import Path

from tools.repository_realization_dependencies import (
    realization_dependency_errors,
    realization_dependency_review_signals,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_repository_realization_dependency_audit() -> None:
    errors = realization_dependency_errors(REPOSITORY_ROOT)
    review_signals = realization_dependency_review_signals(REPOSITORY_ROOT)

    assert not errors and not review_signals, (
        "current realization dependency audit\n"
        "unexplained errors:\n"
        + ("\n".join(errors) if errors else "<none>")
        + "\ntransitive-only review signals:\n"
        + ("\n".join(review_signals) if review_signals else "<none>")
    )
