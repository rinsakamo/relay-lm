from __future__ import annotations

import pytest

from relaylm.providers.lm_studio_reasoning import (
    LMStudioReasoningCapabilityError,
    attest_lm_studio_reasoning_capabilities,
    realize_lm_studio_reasoning_request,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningRequest,
)


def _models_response(
    *,
    key: str = "google/gemma-4-12b",
    loaded_instances: list[dict[str, object]] | None = None,
    reasoning: object = ...,
) -> dict[str, object]:
    if loaded_instances is None:
        loaded_instances = [{"id": key, "config": {"context_length": 8192}}]
    capabilities: dict[str, object] = {"vision": False, "trained_for_tool_use": False}
    if reasoning is ...:
        capabilities["reasoning"] = {
            "allowed_options": ["off", "low", "high"],
            "default": "off",
        }
    elif reasoning is not None:
        capabilities["reasoning"] = reasoning
    return {
        "models": [
            {
                "type": "llm",
                "key": key,
                "loaded_instances": loaded_instances,
                "capabilities": capabilities,
            }
        ]
    }


def test_attests_exact_loaded_model_reasoning_options_and_default() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(),
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
    )

    assert attestation.request_model == "google/gemma-4-12b"
    assert attestation.loaded_instance_id == "google/gemma-4-12b"
    assert attestation.allowed_options == ("high", "low", "off")
    assert attestation.default == "off"
    assert attestation.reasoning_exposed is True
    assert attestation.capabilities.mode_control_supported is True
    assert attestation.capabilities.supported_mode_values == ("high", "low", "off")
    assert attestation.capabilities.token_budget_supported is False
    assert attestation.to_mapping() == {
        "format_version": 1,
        "backend": "lm_studio",
        "request_model": "google/gemma-4-12b",
        "loaded_instance_id": "google/gemma-4-12b",
        "reasoning_exposed": True,
        "allowed_options": ["high", "low", "off"],
        "default": "off",
        "reasoning_capabilities": {
            "mode_control_supported": True,
            "supported_mode_values": ["high", "low", "off"],
            "mode_values_known": True,
            "token_budget_supported": False,
        },
    }


def test_absent_reasoning_metadata_is_unsupported_without_model_name_inference() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(key="deepseek-r1", reasoning=None),
        request_model="deepseek-r1",
        loaded_instance_id="deepseek-r1",
    )

    assert attestation.reasoning_exposed is False
    assert attestation.allowed_options == ()
    assert attestation.default is None
    assert attestation.capabilities.mode_control_supported is False
    assert attestation.capabilities.supported_mode_values is None
    assert attestation.capabilities.token_budget_supported is False


@pytest.mark.parametrize(
    ("response", "request_model", "loaded_instance_id", "match"),
    [
        (
            {"models": []},
            "google/gemma-4-12b",
            "google/gemma-4-12b",
            "exactly one matching request model",
        ),
        (
            {
                "models": [
                    _models_response()["models"][0],
                    _models_response()["models"][0],
                ]
            },
            "google/gemma-4-12b",
            "google/gemma-4-12b",
            "exactly one matching request model",
        ),
        (
            _models_response(
                loaded_instances=[
                    {"id": "instance-a"},
                    {"id": "instance-b"},
                ]
            ),
            "google/gemma-4-12b",
            "instance-a",
            "exactly one loaded instance",
        ),
        (
            _models_response(loaded_instances=[{"id": "different-instance"}]),
            "google/gemma-4-12b",
            "google/gemma-4-12b",
            "loaded instance identity",
        ),
    ],
)
def test_model_and_loaded_runtime_binding_fail_closed(
    response: dict[str, object],
    request_model: str,
    loaded_instance_id: str,
    match: str,
) -> None:
    with pytest.raises(LMStudioReasoningCapabilityError, match=match):
        attest_lm_studio_reasoning_capabilities(
            models_response=response,
            request_model=request_model,
            loaded_instance_id=loaded_instance_id,
        )


@pytest.mark.parametrize(
    ("reasoning", "match"),
    [
        ({"allowed_options": [], "default": "off"}, "allowed_options"),
        (
            {"allowed_options": ["off", "off"], "default": "off"},
            "duplicates",
        ),
        (
            {"allowed_options": ["off", "turbo"], "default": "off"},
            "unsupported public option",
        ),
        (
            {"allowed_options": ["off", "on"], "default": "medium"},
            "default must be present",
        ),
        ({"allowed_options": ["off"]}, "default"),
        ({"default": "off"}, "allowed_options"),
    ],
)
def test_malformed_or_ambiguous_reasoning_metadata_fails_closed(
    reasoning: object,
    match: str,
) -> None:
    with pytest.raises(LMStudioReasoningCapabilityError, match=match):
        attest_lm_studio_reasoning_capabilities(
            models_response=_models_response(reasoning=reasoning),
            request_model="google/gemma-4-12b",
            loaded_instance_id="google/gemma-4-12b",
        )


def test_native_reasoning_metadata_does_not_attest_token_budget_support() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(
            reasoning={"allowed_options": ["on"], "default": "on"}
        ),
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
    )

    assert attestation.capabilities.token_budget_supported is False


def test_realizes_binary_off_as_exact_chat_completions_reasoning_effort() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(
            reasoning={"allowed_options": ["off", "on"], "default": "on"}
        ),
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
    )

    application = realize_lm_studio_reasoning_request(
        request=OpenAICompatibleReasoningRequest(mode="off"),
        capability=attestation,
    )

    assert application.status is OpenAICompatibleReasoningApplicationStatus.APPLIED
    assert application.requested == (("mode", "off"),)
    assert application.wire_fields == (("reasoning_effort", "off"),)
    assert application.to_mapping()["wire_fields"] == {"reasoning_effort": "off"}


def test_realizer_rejects_mode_absent_from_exact_loaded_model_capability() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(
            reasoning={"allowed_options": ["off", "on"], "default": "on"}
        ),
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
    )

    with pytest.raises(LMStudioReasoningCapabilityError, match="not supported"):
        realize_lm_studio_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="high"),
            capability=attestation,
        )


def test_realizer_rejects_reasoning_budget_without_attested_budget_wire() -> None:
    attestation = attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(
            reasoning={"allowed_options": ["off", "on"], "default": "on"}
        ),
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
    )

    with pytest.raises(LMStudioReasoningCapabilityError, match="token budget"):
        realize_lm_studio_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="off", token_budget=16),
            capability=attestation,
        )
