from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)


class OpenAICompatibleBackendId(StrEnum):
    """Canonical machine-facing backend identities under the OpenAI-compatible adapter."""

    GENERIC = "generic"
    VLLM = "vllm"
    LM_STUDIO = "lm_studio"


@dataclass(frozen=True, slots=True)
class OpenAICompatibleBackend:
    """Provider-owned backend identity with display text kept out of machine identity."""

    id: OpenAICompatibleBackendId
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, OpenAICompatibleBackendId):
            raise TypeError("backend id must be OpenAICompatibleBackendId")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise TypeError("backend display_name must be a non-empty string")

    def to_mapping(self) -> dict[str, str]:
        return {"id": self.id.value, "display_name": self.display_name}


_CANONICAL_BACKENDS: tuple[OpenAICompatibleBackend, ...] = (
    OpenAICompatibleBackend(
        id=OpenAICompatibleBackendId.GENERIC,
        display_name="Generic OpenAI-compatible",
    ),
    OpenAICompatibleBackend(
        id=OpenAICompatibleBackendId.VLLM,
        display_name="vLLM",
    ),
    OpenAICompatibleBackend(
        id=OpenAICompatibleBackendId.LM_STUDIO,
        display_name="LM Studio",
    ),
)

_BACKEND_BY_ID = {backend.id: backend for backend in _CANONICAL_BACKENDS}

# Aliases are explicit, bounded input conveniences. They do not perform fuzzy
# matching and never change the canonical machine-facing value returned below.
_BACKEND_ALIASES: dict[str, OpenAICompatibleBackendId] = {
    "generic": OpenAICompatibleBackendId.GENERIC,
    "generic openai-compatible": OpenAICompatibleBackendId.GENERIC,
    "vllm": OpenAICompatibleBackendId.VLLM,
    "lm_studio": OpenAICompatibleBackendId.LM_STUDIO,
    "lm-studio": OpenAICompatibleBackendId.LM_STUDIO,
    "lm studio": OpenAICompatibleBackendId.LM_STUDIO,
}


def canonical_openai_compatible_backends() -> tuple[OpenAICompatibleBackend, ...]:
    """Return the stable backend identity vocabulary for the adapter."""

    return _CANONICAL_BACKENDS


def resolve_openai_compatible_backend(value: str) -> OpenAICompatibleBackend:
    """Resolve safe human spelling to one canonical backend identity.

    Resolution strips surrounding whitespace and case-folds only. Punctuation or
    spacing variants are accepted solely when they appear in the explicit alias
    table above. Unknown values fail closed; there is no fuzzy matching or
    backend auto-detection here.
    """

    if not isinstance(value, str):
        raise TypeError("OpenAI-compatible backend must be a string")
    normalized = value.strip().casefold()
    if not normalized:
        raise ValueError("OpenAI-compatible backend must not be empty")
    backend_id = _BACKEND_ALIASES.get(normalized)
    if backend_id is None:
        raise ValueError(f"unsupported OpenAI-compatible backend: {value}")
    return _BACKEND_BY_ID[backend_id]


def decoding_capabilities_for_backend(
    backend_id: OpenAICompatibleBackendId,
) -> OpenAICompatibleDecodingCapabilities:
    """Return provider-owned request controls proven by the selected backend dialect.

    Generic OpenAI-compatible endpoints remain capability-unknown. The current
    explicit vLLM and LM Studio dialects both admit the standard temperature,
    top-p, and hard ``max_tokens`` Chat Completions controls represented inside
    RelayLM as ``max_output_tokens``.
    """

    if not isinstance(backend_id, OpenAICompatibleBackendId):
        raise TypeError("backend_id must be OpenAICompatibleBackendId")
    if backend_id is OpenAICompatibleBackendId.GENERIC:
        return OpenAICompatibleDecodingCapabilities()
    return OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset(
            {"temperature", "top_p", "max_output_tokens"}
        )
    )
