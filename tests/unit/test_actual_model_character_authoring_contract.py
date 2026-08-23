from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_AUTHORING = _REPO_ROOT / "docs" / "reference" / "actual-model-character-authoring.md"
_AUTHORITY = _REPO_ROOT / ".ai" / "authority" / "actual_model_evaluation.yaml"


def test_character_authoring_contract_keeps_authoring_outside_runtime_authority() -> None:
    authoring = _AUTHORING.read_text(encoding="utf-8")
    authority = _AUTHORITY.read_text(encoding="utf-8")

    assert "The authoring model is a tool. It is not a persistent semantic authority" in authoring
    assert "Core 1.0 does not require a rebuilt SOUL Lab UI" in authoring
    assert "Aoi" in authoring
    assert "ReLM" in authoring
    assert "Rin" in authoring
    assert "the user is the final authority" in authoring
    assert "docs/reference/actual-model-character-authoring.md" in authority
