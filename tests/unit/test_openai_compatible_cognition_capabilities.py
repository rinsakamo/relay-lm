from __future__ import annotations

import asyncio

from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_cognition import (
    OpenAICompatibleCognitionCapabilityFacts,
    describe_openai_compatible_cognition_capabilities,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider


def _provider(
    provider_type: type[OpenAICompatibleProvider] = OpenAICompatibleProvider,
    *,
    supported_controls: frozenset[str] = frozenset({"temperature", "top_p", "seed"}),
) -> OpenAICompatibleProvider:
    return provider_type(
        base_url="http://127.0.0.1:1234/v1",
        model="google/gemma-4-12b",
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=0.2 if "temperature" in supported_controls else None,
            top_p=0.95 if "top_p" in supported_controls else None,
            seed=7 if "seed" in supported_controls else None,
        ),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=supported_controls
        ),
    )


def test_provider_exposes_machine_readable_cognition_capability_facts() -> None:
    provider = _provider()
    try:
        facts = describe_openai_compatible_cognition_capabilities(provider)
    finally:
        asyncio.run(provider.aclose())

    assert isinstance(facts, OpenAICompatibleCognitionCapabilityFacts)
    assert facts.structured_output is True
    assert facts.streaming is True
    assert facts.reasoning_modes == ()
    assert facts.bounded_reasoning_budget is False
    assert facts.per_pass_decoding_controls == ("temperature", "top_p")
    assert facts.to_mapping() == {
        "format_version": 1,
        "structured_output": True,
        "streaming": True,
        "reasoning_modes": [],
        "bounded_reasoning_budget": False,
        "per_pass_decoding_controls": ["temperature", "top_p"],
    }


def test_provider_cognition_facts_do_not_promote_seed_or_unsupported_controls() -> None:
    provider = _provider(supported_controls=frozenset({"temperature", "seed"}))
    try:
        facts = describe_openai_compatible_cognition_capabilities(provider)
    finally:
        asyncio.run(provider.aclose())

    assert facts.per_pass_decoding_controls == ("temperature",)
    assert "seed" not in facts.per_pass_decoding_controls
    assert "max_output_tokens" not in facts.per_pass_decoding_controls


def test_two_pass_extension_reports_same_provider_owned_capability_facts() -> None:
    provider = _provider(OpenAICompatibleTwoPassProvider)
    try:
        facts = describe_openai_compatible_cognition_capabilities(provider)
    finally:
        asyncio.run(provider.aclose())

    assert facts.reasoning_modes == ()
    assert facts.bounded_reasoning_budget is False
    assert facts.structured_output is True
    assert facts.streaming is True
    assert facts.per_pass_decoding_controls == ("temperature", "top_p")
