from __future__ import annotations

import pytest

from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId
from relaylm.providers.vllm_backend import attest_vllm_backend


def _version(version: object = "0.23.0") -> dict[str, object]:
    return {"version": version}


def _models(*cards: dict[str, object]) -> dict[str, object]:
    return {"object": "list", "data": list(cards)}


def _card(
    model_id: object = "served-model",
    *,
    root: object = "/models/artifact",
    max_model_len: object = 32768,
) -> dict[str, object]:
    return {
        "id": model_id,
        "object": "model",
        "created": 1,
        "owned_by": "vllm",
        "root": root,
        "max_model_len": max_model_len,
    }


def test_vllm_attestation_binds_backend_version_and_exact_served_model() -> None:
    attestation = attest_vllm_backend(
        request_model="served-model",
        version_response=_version("0.23.0"),
        models_response=_models(_card()),
    )

    assert attestation.backend is OpenAICompatibleBackendId.VLLM
    assert attestation.version == "0.23.0"
    assert attestation.request_model == "served-model"
    assert attestation.served_model_id == "served-model"
    assert attestation.model_root == "/models/artifact"
    assert attestation.max_model_len == 32768
    assert attestation.attestation_sources == ("/version", "/v1/models")
    assert attestation.to_mapping() == {
        "backend": "vllm",
        "version": "0.23.0",
        "request_model": "served-model",
        "served_model_id": "served-model",
        "model_root": "/models/artifact",
        "max_model_len": 32768,
        "attestation_sources": ["/version", "/v1/models"],
    }


def test_vllm_attestation_allows_nullable_optional_model_metadata() -> None:
    attestation = attest_vllm_backend(
        request_model="served-model",
        version_response=_version(),
        models_response=_models(_card(root=None, max_model_len=None)),
    )

    assert attestation.model_root is None
    assert attestation.max_model_len is None


def test_vllm_attestation_requires_exactly_one_matching_request_model() -> None:
    with pytest.raises(ValueError, match="exactly one matching served model"):
        attest_vllm_backend(
            request_model="served-model",
            version_response=_version(),
            models_response=_models(_card("other-model")),
        )

    with pytest.raises(ValueError, match="exactly one matching served model"):
        attest_vllm_backend(
            request_model="served-model",
            version_response=_version(),
            models_response=_models(_card(), _card()),
        )


def test_vllm_attestation_rejects_malformed_version_identity() -> None:
    for response in ({}, {"version": ""}, {"version": 23}, []):
        with pytest.raises((TypeError, ValueError), match="version"):
            attest_vllm_backend(
                request_model="served-model",
                version_response=response,
                models_response=_models(_card()),
            )


def test_vllm_attestation_rejects_malformed_model_list_or_card() -> None:
    malformed = (
        {},
        {"object": "model", "data": [_card()]},
        {"object": "list", "data": "not-a-list"},
        _models({"id": "served-model", "object": "not-model"}),
        _models(_card(root=1)),
        _models(_card(max_model_len=0)),
        _models(_card(max_model_len=True)),
    )
    for response in malformed:
        with pytest.raises((TypeError, ValueError)):
            attest_vllm_backend(
                request_model="served-model",
                version_response=_version(),
                models_response=response,
            )


def test_vllm_attestation_does_not_infer_reasoning_capability() -> None:
    attestation = attest_vllm_backend(
        request_model="served-model",
        version_response=_version(),
        models_response=_models(_card()),
    )

    assert "reasoning" not in attestation.to_mapping()
    assert "reasoning_effort" not in attestation.to_mapping()
    assert "thinking_token_budget" not in attestation.to_mapping()
