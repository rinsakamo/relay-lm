from __future__ import annotations

from pathlib import Path

from tools.repository_realization_dependencies import realization_dependency_errors


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_current_realization_dependencies_are_explained() -> None:
    assert realization_dependency_errors(REPOSITORY_ROOT) == ()
