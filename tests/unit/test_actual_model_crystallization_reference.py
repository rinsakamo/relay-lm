from pathlib import Path

from relaylm.actual_model_crystallization import (
    ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION,
)


_REFERENCE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reference"
    / "actual-model-crystallization-evidence.md"
)


def test_crystallization_reference_matches_current_evidence_schema() -> None:
    reference = _REFERENCE.read_text(encoding="utf-8")

    assert (
        "The current crystallization evidence format is version "
        f"`{ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION}`."
    ) in reference

    raw_section = reference.split(
        "## Raw output and deterministic decisions", maxsplit=1
    )[1].split("## Product-quality review", maxsplit=1)[0]
    assert "`memory_units`" in raw_section
    assert "`memory_markdown`" not in raw_section
