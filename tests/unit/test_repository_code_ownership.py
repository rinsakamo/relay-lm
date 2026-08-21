from __future__ import annotations

from pathlib import Path

from tools.repository_code_ownership import production_code_coverage_errors


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_every_current_production_python_module_has_a_semantic_owner() -> None:
    assert production_code_coverage_errors(REPOSITORY_ROOT) == ()
