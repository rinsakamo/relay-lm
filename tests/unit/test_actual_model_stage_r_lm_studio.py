from __future__ import annotations

from typing import Any

import pytest

import relaylm.actual_model_stage_r as stage_r
from relaylm.actual_model_stage_r import StageRAuthorityError
from relaylm.actual_model_stage_r_lm_studio import (
    LMStudioStageRError,
    observe_compatible_lm_studio_model,
)


def _models(*, quantization: str = "Q4_K_M") -> dict[str, object]:
    return {
        "models": [
            {
                "type": "llm",
                "key": "google/gemma-4-12b",
                "display_name": "Gemma 4 12B",
                "params_string": "12B",
                "quantization": {"name": quantization},
                "size_bytes": 7_381_384_864,
                "capabilities": {
                    "reasoning": {
                        "allowed_options": ["off", "on"],
                        "default": "on",
                    }
                },
                "loaded_instances": [
                    {
                        "id": "gemma-live-1",
                        "config": {
                            "context_length": 8192,
                            "flash_attention": True,
                            "offload_kv_cache_to_gpu": True,
                        },
                    }
                ],
            }
        ]
    }


def test_observed_stage_r_accepts_gemma4_12b_q4_without_artifact_sha() -> None:
    observed = observe_compatible_lm_studio_model(
        models_response=_models(),
        request_model="google/gemma-4-12b",
    )

    assert observed.request_model == "google/gemma-4-12b"
    assert observed.loaded_instance_id == "gemma-live-1"
    assert observed.quantization == "Q4_K_M"
    assert observed.context_length == 8192
    assert observed.flash_attention is True
    assert observed.offload_kv_cache_to_gpu is True
    assert observed.reasoning_default == "on"
    assert observed.reasoning_condition == "omitted_default_on"
    mapping = observed.to_mapping()
    assert "artifact_sha256" not in mapping
    assert "artifact_repository_revision" not in mapping
    assert "target_id" not in mapping


def test_observed_stage_r_rejects_non_q4_model() -> None:
    with pytest.raises(LMStudioStageRError, match="Q4-class"):
        observe_compatible_lm_studio_model(
            models_response=_models(quantization="Q8_0"),
            request_model="google/gemma-4-12b",
        )


def test_observed_stage_r_can_disambiguate_loaded_instance() -> None:
    response = _models()
    model = response["models"][0]
    assert isinstance(model, dict)
    instances = model["loaded_instances"]
    assert isinstance(instances, list)
    instances.append(
        {
            "id": "gemma-live-2",
            "config": {"context_length": 4096},
        }
    )

    with pytest.raises(LMStudioStageRError, match="ambiguous"):
        observe_compatible_lm_studio_model(
            models_response=response,
            request_model="google/gemma-4-12b",
        )

    observed = observe_compatible_lm_studio_model(
        models_response=response,
        request_model="google/gemma-4-12b",
        loaded_instance_id="gemma-live-2",
    )
    assert observed.loaded_instance_id == "gemma-live-2"
    assert observed.context_length == 4096


def test_stage_r_dispatches_lm_studio_without_vllm_capacity_or_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[list[str]] = []
    monkeypatch.setattr(
        stage_r,
        "_lm_studio_stage_r_main",
        lambda args: delegated.append(list(args)) or 0,
    )

    result = stage_r.main(
        [
            "--backend",
            "lm_studio",
            "--operation",
            "screening",
            "--condition",
            "reference_baseline",
            "--repo-root",
            "/repo",
            "--provider-base-url",
            "http://192.168.50.26:1234/v1",
            "--request-model",
            "google/gemma-4-12b",
            "--loaded-instance-id",
            "gemma-live-1",
            "--workspace-root",
            "/tmp/workspace",
            "--artifact-root",
            "/tmp/artifacts",
        ]
    )

    assert result == 0
    assert len(delegated) == 1
    args = delegated[0]
    assert args[args.index("--request-model") + 1] == "google/gemma-4-12b"
    assert args[args.index("--loaded-instance-id") + 1] == "gemma-live-1"
    assert "--snapshot-root" not in args
    assert "--model-runner" not in args
    assert "--capacity-evidence-id" not in args
    assert "--capacity-evidence-root" not in args


def test_stage_r_lm_studio_rejects_vllm_capacity_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched = False

    def forbidden(_: list[str]) -> int:
        nonlocal touched
        touched = True
        return 0

    monkeypatch.setattr(stage_r, "_lm_studio_stage_r_main", forbidden)
    with pytest.raises(StageRAuthorityError, match="must not consume vLLM capacity"):
        stage_r.main(
            [
                "--backend",
                "lm_studio",
                "--operation",
                "screening",
                "--condition",
                "reference_baseline",
                "--repo-root",
                "/repo",
                "--provider-base-url",
                "http://192.168.50.26:1234/v1",
                "--request-model",
                "google/gemma-4-12b",
                "--workspace-root",
                "/tmp/workspace",
                "--artifact-root",
                "/tmp/artifacts",
                "--capacity-evidence-id",
                "legacy",
                "--capacity-evidence-root",
                "/tmp/capacity",
            ]
        )

    assert touched is False
