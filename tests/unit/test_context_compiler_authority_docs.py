from __future__ import annotations

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_CONTEXT_COMPILER_AUTHORITY = (
    _REPOSITORY_ROOT / "docs" / "architecture" / "context-compiler.md"
)


def test_context_compiler_authority_describes_realized_continuity_wiring() -> None:
    authority = _CONTEXT_COMPILER_AUTHORITY.read_text(encoding="utf-8")

    assert "does not yet supply its `ContinuityRuntime.context`" not in authority
    assert "Turn supplies the accepted pre-generation Continuity Context" in authority
    assert "Continuity lifecycle acceptance remains upstream" in authority
