from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    OPENAI_COMPATIBLE_ADAPTER_IDENTITY,
    OPENAI_COMPATIBLE_PROVIDER_IDENTITY_FORMAT_VERSION,
    OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME,
    OPENAI_COMPATIBLE_STRUCTURED_SEMANTIC_CHANNELS,
    describe_openai_compatible_provider,
)


def _identity(
    *,
    base_url: str = "http://lm.test/v1",
    model: str = "gemma",
    api_key: str | None = None,
    decoding_config: OpenAICompatibleDecodingConfig | None = None,
    decoding_capabilities: OpenAICompatibleDecodingCapabilities | None = None,
):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: (_ for _ in ()).throw(
                    AssertionError("identity inspection must not make a network request")
                )
            )
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url=base_url,
                model=model,
                api_key=api_key,
                decoding_config=decoding_config,
                decoding_capabilities=decoding_capabilities,
                http_client=client,
            )
            return describe_openai_compatible_provider(provider)

    return asyncio.run(run())


def test_default_identity_exposes_canonical_semantic_and_delivery_capabilities() -> None:
    identity = _identity()

    assert identity.format_version == OPENAI_COMPATIBLE_PROVIDER_IDENTITY_FORMAT_VERSION
    assert identity.adapter_identity == OPENAI_COMPATIBLE_ADAPTER_IDENTITY
    assert identity.model == "gemma"
    assert identity.structured_output_schema_name == OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME
    assert identity.capabilities.structured_semantic_channels == (
        OPENAI_COMPATIBLE_STRUCTURED_SEMANTIC_CHANNELS
    )
    assert identity.capabilities.supported_decoding_controls == ()
    assert identity.capabilities.buffered is True
    assert identity.capabilities.streaming is True
    assert identity.capabilities.seed_control_supported is False
    assert identity.effective_decoding_configuration == {}
    assert set(identity.provider_capabilities) == {
        "buffered",
        "continuity_candidates",
        "response",
        "state_candidates",
        "streaming",
    }


def test_identity_distinguishes_declared_decoding_support_from_applied_configuration() -> None:
    identity = _identity(
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0.2),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p", "seed"})
        ),
    )

    assert identity.effective_decoding_configuration == {"temperature": 0.2}
    assert identity.capabilities.supported_decoding_controls == (
        "seed",
        "temperature",
        "top_p",
    )
    assert identity.capabilities.seed_control_supported is True
    assert {"temperature", "top_p", "seed"} <= set(identity.provider_capabilities)


def test_identity_tokens_directly_cover_current_actual_model_capability_vocabulary() -> None:
    identity = _identity()

    required_by_current_foundation_and_execution = {
        "state_candidates",
        "continuity_candidates",
        "streaming",
    }
    assert required_by_current_foundation_and_execution <= set(
        identity.provider_capabilities
    )


def test_identity_is_secret_free_and_excludes_connection_location() -> None:
    identity = _identity(
        base_url="https://private-host.example/internal/v1",
        api_key="super-secret-provider-key",
        decoding_config=OpenAICompatibleDecodingConfig(seed=7),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"seed"})
        ),
    )
    serialized = json.dumps(identity.to_mapping(), sort_keys=True)

    assert "super-secret-provider-key" not in serialized
    assert "private-host.example" not in serialized
    assert "internal/v1" not in serialized
    assert "api_key" not in serialized
    assert "base_url" not in serialized
    assert identity.to_mapping()["model"] == "gemma"
    assert identity.effective_decoding_configuration == {"seed": 7}


def test_request_identity_is_stable_across_secret_and_endpoint_changes() -> None:
    config = OpenAICompatibleDecodingConfig(temperature=0.1, seed=42)
    capabilities = OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset({"temperature", "seed"})
    )

    first = _identity(
        base_url="http://first-host/v1",
        api_key="first-secret",
        decoding_config=config,
        decoding_capabilities=capabilities,
    )
    second = _identity(
        base_url="https://second-host/provider/v1",
        api_key="second-secret",
        decoding_config=config,
        decoding_capabilities=capabilities,
    )

    assert first == second


def test_identity_changes_when_request_model_or_decoding_configuration_changes() -> None:
    capabilities = OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset({"temperature"})
    )
    baseline = _identity(
        model="model-a",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0.1),
        decoding_capabilities=capabilities,
    )
    changed_model = _identity(
        model="model-b",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0.1),
        decoding_capabilities=capabilities,
    )
    changed_decoding = _identity(
        model="model-a",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0.2),
        decoding_capabilities=capabilities,
    )

    assert baseline != changed_model
    assert baseline != changed_decoding


def test_identity_mapping_is_content_free_and_json_serializable() -> None:
    identity = _identity(
        decoding_config=OpenAICompatibleDecodingConfig(top_p=0.95),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"top_p"})
        ),
    )

    mapping = identity.to_mapping()
    encoded = json.dumps(mapping, ensure_ascii=False, allow_nan=False, sort_keys=True)

    assert "top_p" in encoded
    assert mapping["capabilities"]["structured_semantic_channels"] == [
        "response",
        "state_candidates",
        "continuity_candidates",
    ]
    assert mapping["capabilities"]["buffered"] is True
    assert mapping["capabilities"]["streaming"] is True


def test_identity_source_fails_closed_when_required_provider_surface_is_missing() -> None:
    with pytest.raises(TypeError, match="model"):
        describe_openai_compatible_provider(object())  # type: ignore[arg-type]
