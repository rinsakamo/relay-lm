from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_BOUNDARY = _REPO_ROOT / "docs" / "reference" / "context-compiler-semantic-boundary.md"
_AUTHORITY = _REPO_ROOT / ".ai" / "authority" / "context_compiler.yaml"


def test_context_compiler_semantic_expansion_stops_at_c37() -> None:
    boundary = _BOUNDARY.read_text(encoding="utf-8")
    authority = _AUTHORITY.read_text(encoding="utf-8")

    assert "C37 is the proactive deterministic semantic-grammar freeze point" in boundary
    assert "Semantic completeness is not a Context Compiler goal" in boundary
    assert "evidence-triggered only" in boundary
    assert "Existing C5-C37 behavior and tests remain regression protection" in boundary
    assert "docs/reference/context-compiler-semantic-boundary.md" in authority
    assert "tests/unit/test_context_compiler_semantic_expansion_boundary.py" in authority
