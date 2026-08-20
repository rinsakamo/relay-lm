from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId


VLLM_BACKEND_ATTESTATION_SOURCES = ("/version", "/v1/models")


@dataclass(frozen=True, slots=True)
class VLLMBackendAttestation:
    """Content-free identity attested from vLLM provider-specific API surfaces.

    This record proves only the backend/version and the exact served model selected
    by RelayLM. It deliberately does not infer reasoning, structured-output, or
    decoding capability from a model name or from vLLM family identity.
    """

    version: str
    request_model: str
    served_model_id: str
    model_root: str | None
    max_model_len: int | None
    backend: OpenAICompatibleBackendId = OpenAICompatibleBackendId.VLLM
    attestation_sources: tuple[str, ...] = VLLM_BACKEND_ATTESTATION_SOURCES

    def __post_init__(self) -> None:
        if self.backend is not OpenAICompatibleBackendId.VLLM:
            raise ValueError("vLLM attestation backend must be vllm")
        _non_empty_string("version", self.version)
        _non_empty_string("request_model", self.request_model)
        _non_empty_string("served_model_id", self.served_model_id)
        if self.served_model_id != self.request_model:
            raise ValueError("served model must exactly match request_model")
        if self.model_root is not None:
            _non_empty_string("model_root", self.model_root)
        if self.max_model_len is not None:
            _positive_int("max_model_len", self.max_model_len)
        if self.attestation_sources != VLLM_BACKEND_ATTESTATION_SOURCES:
            raise ValueError("vLLM attestation sources are not canonical")

    def to_mapping(self) -> dict[str, object]:
        return {
            "backend": self.backend.value,
            "version": self.version,
            "request_model": self.request_model,
            "served_model_id": self.served_model_id,
            "model_root": self.model_root,
            "max_model_len": self.max_model_len,
            "attestation_sources": list(self.attestation_sources),
        }


def attest_vllm_backend(
    *,
    request_model: str,
    version_response: object,
    models_response: object,
) -> VLLMBackendAttestation:
    """Bind configured RelayLM backend selection to vLLM API identity responses.

    `/version` supplies the backend version. `/v1/models` must contain exactly one
    model card whose public `id` equals the configured request model. Optional root
    and maximum-model-length metadata are recorded as reported metadata only; they
    are not promoted into immutable model-artifact identity.
    """

    _non_empty_string("request_model", request_model)
    version = _parse_version_response(version_response)
    card = _matching_model_card(models_response, request_model=request_model)
    model_root = _optional_non_empty_string("model_root", card.get("root"))
    max_model_len = _optional_positive_int("max_model_len", card.get("max_model_len"))

    return VLLMBackendAttestation(
        version=version,
        request_model=request_model,
        served_model_id=request_model,
        model_root=model_root,
        max_model_len=max_model_len,
    )


def _parse_version_response(response: object) -> str:
    mapping = _mapping("version response", response)
    if "version" not in mapping:
        raise ValueError("vLLM version response must contain version")
    version = mapping["version"]
    _non_empty_string("version", version)
    return version


def _matching_model_card(response: object, *, request_model: str) -> dict[str, Any]:
    mapping = _mapping("models response", response)
    if mapping.get("object") != "list":
        raise ValueError("vLLM models response object must be list")
    data = mapping.get("data")
    if not isinstance(data, list):
        raise TypeError("vLLM models response data must be a list")

    matches: list[dict[str, Any]] = []
    for item in data:
        card = _mapping("model card", item)
        model_id = card.get("id")
        if model_id == request_model:
            matches.append(card)

    if len(matches) != 1:
        raise ValueError("vLLM models response must contain exactly one matching served model")

    card = matches[0]
    if card.get("object") != "model":
        raise ValueError("vLLM served model card object must be model")
    model_id = card.get("id")
    _non_empty_string("served model id", model_id)
    return card


def _mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"vLLM {name} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"vLLM {name} keys must be strings")
    return value


def _non_empty_string(name: str, value: object) -> None:
    if not isinstance(value, str):
        raise TypeError(f"vLLM {name} must be a string")
    if not value.strip():
        raise ValueError(f"vLLM {name} must not be empty")


def _positive_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"vLLM {name} must be an integer")
    if value <= 0:
        raise ValueError(f"vLLM {name} must be positive")


def _optional_non_empty_string(name: str, value: object) -> str | None:
    if value is None:
        return None
    _non_empty_string(name, value)
    assert isinstance(value, str)
    return value


def _optional_positive_int(name: str, value: object) -> int | None:
    if value is None:
        return None
    _positive_int(name, value)
    assert isinstance(value, int) and not isinstance(value, bool)
    return value
