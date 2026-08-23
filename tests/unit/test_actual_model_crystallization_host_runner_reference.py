from pathlib import Path

from relaylm.actual_model_crystallization_host_runner import (
    ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION,
    CRYSTALLIZATION_ADAPTER_IDENTITY,
    CRYSTALLIZATION_EVALUATION_CONTRACT_VERSION,
    CRYSTALLIZATION_STRUCTURED_OUTPUT_SCHEMA_VERSION,
)


_REFERENCE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reference"
    / "actual-model-crystallization-host-runner.md"
)


def test_crystallization_host_reference_matches_current_runtime_identity() -> None:
    reference = _REFERENCE.read_text(encoding="utf-8")

    assert (
        "The current condition format is version "
        f"{ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION}"
    ) in reference
    assert f'"format_version": {ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION}' in reference
    assert f"`{CRYSTALLIZATION_ADAPTER_IDENTITY}`" in reference
    assert f"`{CRYSTALLIZATION_STRUCTURED_OUTPUT_SCHEMA_VERSION}`" in reference
    assert f"`{CRYSTALLIZATION_EVALUATION_CONTRACT_VERSION}`" in reference
