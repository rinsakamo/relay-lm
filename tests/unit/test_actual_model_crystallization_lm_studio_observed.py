from __future__ import annotations

import pytest

from relaylm.actual_model_crystallization_lm_studio_observed import (
    CASE_ID,
    CONDITION_ID,
    FIXTURE_ID,
    MAX_EVENTS,
    ObservedLMStudioCrystallizationError,
    _require_openai_api_base,
    build_observed_manifest,
    observed_reasoning_identity,
)
from relaylm.actual_model_stage_r_lm_studio import ObservedLMStudioModel


def _observed(*, reasoning_default: str | None = "on") -> ObservedLMStudioModel:
    allowed = ("off", "on") if reasoning_default is not None else ()
    return ObservedLMStudioModel(
        request_model="google/gemma-4-12b",
        loaded_instance_id="gemma-live-1",
        display_name="Gemma 4 12B",
        params_string="12B",
        quantization="Q4_K_M",
        size_bytes=7_381_384_864,
        context_length=8192,
        flash_attention=True,
        offload_kv_cache_to_gpu=True,
        reasoning_default=reasoning_default,
        reasoning_allowed_options=allowed,
    )


def test_observed_manifest_records_model_condition_without_frozen_artifact() -> None:
    observed = _observed()
    manifest = build_observed_manifest(
        relaylm_commit="a" * 40,
        fixture_revision="sha256:" + "b" * 64,
        observed=observed,
        replicate_id="0",
    )

    assert manifest.character_fixture_id == FIXTURE_ID
    assert manifest.condition_id == CONDITION_ID
    assert manifest.max_events == MAX_EVENTS
    assert manifest.model_artifact == observed.observed_identity
    assert manifest.tokenizer_identity == "lmstudio-observed:tokenizer-unreported"
    assert manifest.effective_context_window == 8192
    assert manifest.reasoning_identity.effective_setting == "on"
    assert "target_id" not in manifest.to_mapping()
    assert "artifact_sha256" not in manifest.to_mapping()


def test_observed_reasoning_identity_records_default_without_wire_override() -> None:
    identity = observed_reasoning_identity(_observed())

    assert identity.required_setting == "on"
    assert identity.effective_setting == "on"
    assert identity.live_default == "on"
    assert identity.allowed_options == ("off", "on")
    assert identity.control_source == "lmstudio_native_model_default"
    assert identity.control_mode == "omitted_default_observed"


def test_observed_reasoning_identity_can_record_unknown_metadata() -> None:
    identity = observed_reasoning_identity(_observed(reasoning_default=None))

    assert identity.required_setting == "unknown"
    assert identity.effective_setting == "unknown"
    assert identity.live_default == "unknown"
    assert identity.allowed_options == ("unknown",)
    assert identity.control_source == "lmstudio_native_metadata_unreported"
    assert identity.control_mode == "omitted_default_unknown"


def test_observed_runner_uses_canonical_quality_case() -> None:
    assert CASE_ID == "crystallization-consolidation-quality-v1"
    assert MAX_EVENTS == 7


def test_observed_runner_requires_openai_v1_api_base() -> None:
    assert _require_openai_api_base("http://192.168.50.26:1234/v1") == (
        "http://192.168.50.26:1234/v1"
    )
    with pytest.raises(ObservedLMStudioCrystallizationError, match="/v1"):
        _require_openai_api_base("http://192.168.50.26:1234")
