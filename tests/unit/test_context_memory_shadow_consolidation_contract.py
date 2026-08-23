from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_AUTHORITY = _REPO_ROOT / ".ai" / "authority" / "context_compiler.yaml"

_NEW_SURFACES = (
    "tests/unit/test_context_memory_shadow_scalar.py",
    "tests/unit/test_context_memory_shadow_boolean.py",
    "tests/unit/test_context_memory_shadow_degree.py",
)

_OBSOLETE_HISTORY_SURFACES = (
    "tests/unit/test_context_inline_scalar_negation_authority.py",
    "tests/unit/test_context_heading_scalar_negation_authority.py",
    "tests/unit/test_context_multiple_inline_boolean_authority.py",
    "tests/unit/test_context_heading_multiple_degree_mixed_authority.py",
    "tests/unit/test_context_heading_multiline_single_positive_degree_authority.py",
)


def test_context_memory_shadow_tests_are_concept_owned_not_cxx_owned() -> None:
    authority = _AUTHORITY.read_text(encoding="utf-8")

    for surface in _NEW_SURFACES:
        assert surface in authority
    for surface in _OBSOLETE_HISTORY_SURFACES:
        assert surface not in authority
