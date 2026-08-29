from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
    VLLMReasoningCapabilityStatus,
)

OPENAI_COMPATIBLE_COGNITION_CAPABILITY_FACTS_FORMAT_VERSION = 1
_COGNITION_PER_PASS_DECODING_CONTROLS = frozenset(
    {"temperature", "top_p", "max_output_tokens"}
)


class OpenAICompatibleCognitionCapabilitySource(Protocol):
    decoding_capabilities: OpenAICompatibleDecodingCapabilities


@dataclass(frozen=True, slots=True)
class OpenAICompatibleCognitionCapabilityFacts:
    """Provider-owned facts consumable by cognition-policy capability resolution.

    This is intentionally separate from the stable P4 provider identity so adding
    a consumer-facing capability view does not rewrite historical provider identity.
    The values describe the current canonical Chat Completions adapter; they do not
    add request behavior.
    """

    structured_output: bool
    streaming: bool
    reasoning_modes: tuple[str, ...]
    bounded_reasoning_budget: bool
    per_pass_decoding_controls: tuple[str, ...]
    format_version: int = OPENAI_COMPATIBLE_COGNITION_CAPABILITY_FACTS_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != OPENAI_COMPATIBLE_COGNITION_CAPABILITY_FACTS_FORMAT_VERSION:
            raise ValueError(
                "unsupported OpenAI-compatible cognition capability facts format_version: "
                f"{self.format_version}"
            )
        if not isinstance(self.structured_output, bool):
            raise TypeError("structured_output must be bool")
        if not isinstance(self.streaming, bool):
            raise TypeError("streaming must be bool")
        if not isinstance(self.bounded_reasoning_budget, bool):
            raise TypeError("bounded_reasoning_budget must be bool")
        for name, values in (
            ("reasoning_modes", self.reasoning_modes),
            ("per_pass_decoding_controls", self.per_pass_decoding_controls),
        ):
            if not isinstance(values, tuple):
                raise TypeError(f"{name} must be a tuple")
            if not all(isinstance(item, str) and item.strip() for item in values):
                raise TypeError(f"{name} must contain non-empty strings")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must not contain duplicates")
            if tuple(sorted(values)) != values:
                raise ValueError(f"{name} must be sorted")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "structured_output": self.structured_output,
            "streaming": self.streaming,
            "reasoning_modes": list(self.reasoning_modes),
            "bounded_reasoning_budget": self.bounded_reasoning_budget,
            "per_pass_decoding_controls": list(self.per_pass_decoding_controls),
        }


def describe_openai_compatible_cognition_capabilities(
    provider: OpenAICompatibleCognitionCapabilitySource,
) -> OpenAICompatibleCognitionCapabilityFacts:
    """Return truthful current-adapter facts without inferring unsupported controls."""

    decoding_capabilities = getattr(provider, "decoding_capabilities", None)
    if not isinstance(decoding_capabilities, OpenAICompatibleDecodingCapabilities):
        raise TypeError(
            "provider capability source must expose OpenAICompatibleDecodingCapabilities"
        )

    per_pass_controls = tuple(
        sorted(
            control
            for control in decoding_capabilities.supported_controls
            if control in _COGNITION_PER_PASS_DECODING_CONTROLS
        )
    )
    vllm_reasoning = getattr(provider, "vllm_reasoning_capability", None)
    if vllm_reasoning is not None and not isinstance(
        vllm_reasoning, VLLMReasoningCapabilityAttestation
    ):
        raise TypeError(
            "provider vLLM reasoning capability must be VLLMReasoningCapabilityAttestation"
        )
    reasoning_modes: tuple[str, ...] = ()
    bounded_reasoning_budget = False
    if vllm_reasoning is not None:
        modes: list[str] = []
        if (
            vllm_reasoning.reasoning_off.status
            is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
        ):
            modes.append("off")
        if (
            vllm_reasoning.reasoning_bounded.status
            is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
        ):
            modes.append("bounded")
            bounded_reasoning_budget = True
        reasoning_modes = tuple(sorted(modes))
    return OpenAICompatibleCognitionCapabilityFacts(
        # Canonical cognition uses ordinary message content plus RelayLM-owned IR.
        # The generic adapter has no native structured-output attestation source,
        # so absence of capability evidence must not become an affirmative fact.
        structured_output=False,
        streaming=True,
        reasoning_modes=reasoning_modes,
        bounded_reasoning_budget=bounded_reasoning_budget,
        per_pass_decoding_controls=per_pass_controls,
    )
