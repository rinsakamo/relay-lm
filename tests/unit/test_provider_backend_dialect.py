from __future__ import annotations

import pytest

from relaylm.providers.backend_dialect import (
    BackendDialectId,
    canonical_backend_dialects,
    resolve_backend_dialect,
)


def test_backend_dialect_registry_has_stable_machine_ids_and_display_names() -> None:
    assert [dialect.to_mapping() for dialect in canonical_backend_dialects()] == [
        {"id": "openai_compatible", "display_name": "OpenAI-compatible"},
        {"id": "vllm", "display_name": "vLLM"},
        {"id": "lm_studio", "display_name": "LM Studio"},
    ]


def test_backend_dialect_resolution_normalizes_safe_human_spelling() -> None:
    assert resolve_backend_dialect("vllm").id is BackendDialectId.VLLM
    assert resolve_backend_dialect("vLLM").id is BackendDialectId.VLLM
    assert resolve_backend_dialect(" VLLM ").id is BackendDialectId.VLLM

    assert resolve_backend_dialect("lm_studio").id is BackendDialectId.LM_STUDIO
    assert resolve_backend_dialect("lm-studio").id is BackendDialectId.LM_STUDIO
    assert resolve_backend_dialect("LM Studio").id is BackendDialectId.LM_STUDIO

    assert (
        resolve_backend_dialect("openai_compatible").id
        is BackendDialectId.OPENAI_COMPATIBLE
    )
    assert (
        resolve_backend_dialect("OpenAI-compatible").id
        is BackendDialectId.OPENAI_COMPATIBLE
    )
    assert (
        resolve_backend_dialect("OPENAI COMPATIBLE").id
        is BackendDialectId.OPENAI_COMPATIBLE
    )


def test_backend_dialect_resolution_returns_canonical_identity() -> None:
    dialect = resolve_backend_dialect("vLLM")

    assert dialect.id.value == "vllm"
    assert dialect.display_name == "vLLM"
    assert dialect.to_mapping() == {"id": "vllm", "display_name": "vLLM"}


def test_backend_dialect_resolution_does_not_fuzzy_match_unknown_values() -> None:
    for value in ("vll", "lmstudio", "openai", "sglang", "auto"):
        with pytest.raises(ValueError, match="unsupported backend dialect"):
            resolve_backend_dialect(value)


def test_backend_dialect_resolution_rejects_invalid_input() -> None:
    with pytest.raises(TypeError, match="backend dialect must be a string"):
        resolve_backend_dialect(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="backend dialect must not be empty"):
        resolve_backend_dialect("   ")
