from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_CHARACTER_REALIZATION = (
    _REPO_ROOT / "docs" / "reference" / "actual-model-character-realization.md"
)
_STAGE_R_COVERAGE = (
    _REPO_ROOT / "docs" / "reference" / "actual-model-stage-r-coverage.md"
)
_AUTHORITY = _REPO_ROOT / ".ai" / "authority" / "actual_model_evaluation.yaml"


def test_character_realization_contract_is_registered_and_preserves_aoi() -> None:
    contract = _CHARACTER_REALIZATION.read_text(encoding="utf-8")
    coverage = _STAGE_R_COVERAGE.read_text(encoding="utf-8")
    authority = _AUTHORITY.read_text(encoding="utf-8")

    assert "Provenance is strict. Interpretation is Character-relative." in contract
    assert "Clarification is not failure. Miscalibrated certainty can be." in contract
    assert "odd_but_character_plausible" in contract
    assert "out_of_character" in contract
    assert "system_defect" in contract
    assert "actual-model-stage-r-review-v2" in contract
    assert "Historical actual-model review format v2" in contract
    assert "Aoi" in contract
    assert "ReLM" in contract
    assert "Rin" in contract
    assert "Core 1.0 does not require a rebuilt SOUL Lab UI" in coverage
    assert "Aoi, ReLM, and Rin are separate valid Character spaces" in coverage
    assert "review format v3" in coverage
    assert "actual-model-stage-r-review-v2" in coverage
    assert "docs/reference/actual-model-character-realization.md" in authority
    assert "tests/unit/test_actual_model_character_realization_review.py" in authority


def test_character_realization_contract_does_not_make_exact_semantics_universal() -> None:
    contract = _CHARACTER_REALIZATION.read_text(encoding="utf-8")
    coverage = _STAGE_R_COVERAGE.read_text(encoding="utf-8")

    assert "not a universal\nmeasure of Character cognition" in contract
    assert "do not\nestablish one neutral interpretation" in coverage
    assert "must not drive new deterministic free-form semantic grammar" in coverage
    assert "does not silently become `fail`" in contract
