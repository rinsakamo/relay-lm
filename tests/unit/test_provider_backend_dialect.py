from __future__ import annotations

import pytest

from relaylm.providers.openai_compatible_backend import (
    OpenAICompatibleBackendId,
    canonical_openai_compatible_backends,
    resolve_openai_compatible_backend,
)


def test_openai_compatible_backend_registry_has_stable_machine_ids_and_display_names() -> None:
    assert [backend.to_mapping() for backend in canonical_openai_compatible_backends()] == [
        {"id": "generic", "display_name": "Generic OpenAI-compatible"},
        {"id": "vllm", "display_name": "vLLM"},
        {"id": "lm_studio", "display_name": "LM Studio"},
    ]


def test_openai_compatible_backend_resolution_normalizes_safe_human_spelling() -> None:
    assert resolve_openai_compatible_backend("vllm").id is OpenAICompatibleBackendId.VLLM
    assert resolve_openai_compatible_backend("vLLM").id is OpenAICompatibleBackendId.VLLM
    assert resolve_openai_compatible_backend(" VLLM ").id is OpenAICompatibleBackendId.VLLM

    assert (
        resolve_openai_compatible_backend("lm_studio").id
        is OpenAICompatibleBackendId.LM_STUDIO
    )
    assert (
        resolve_openai_compatible_backend("lm-studio").id
        is OpenAICompatibleBackendId.LM_STUDIO
    )
    assert (
        resolve_openai_compatible_backend("LM Studio").id
        is OpenAICompatibleBackendId.LM_STUDIO
    )

    assert (
        resolve_openai_compatible_backend("generic").id
        is OpenAICompatibleBackendId.GENERIC
    )
    assert (
        resolve_openai_compatible_backend("Generic OpenAI-compatible").id
        is OpenAICompatibleBackendId.GENERIC
    )


def test_openai_compatible_backend_resolution_returns_canonical_identity() -> None:
    backend = resolve_openai_compatible_backend("vLLM")

    assert backend.id.value == "vllm"
    assert backend.display_name == "vLLM"
    assert backend.to_mapping() == {"id": "vllm", "display_name": "vLLM"}


def test_adapter_name_is_not_accepted_as_a_backend_identity() -> None:
    with pytest.raises(ValueError, match="unsupported OpenAI-compatible backend"):
        resolve_openai_compatible_backend("openai_compatible")


def test_openai_compatible_backend_resolution_does_not_fuzzy_match_unknown_values() -> None:
    for value in ("vll", "lmstudio", "openai", "sglang", "auto"):
        with pytest.raises(ValueError, match="unsupported OpenAI-compatible backend"):
            resolve_openai_compatible_backend(value)


def test_openai_compatible_backend_resolution_rejects_invalid_input() -> None:
    with pytest.raises(TypeError, match="OpenAI-compatible backend must be a string"):
        resolve_openai_compatible_backend(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="OpenAI-compatible backend must not be empty"):
        resolve_openai_compatible_backend("   ")
