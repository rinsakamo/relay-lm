from __future__ import annotations

from dataclasses import dataclass

from relaylm.providers.openai_compatible_reasoning import ReasoningMapping


VLLM_REASONING_EFFORT_VALUES = (
    "high",
    "low",
    "max",
    "medium",
    "minimal",
    "none",
    "xhigh",
)


@dataclass(frozen=True, slots=True)
class VLLMReasoningWireControls:
    """Exact vLLM Chat Completions reasoning fields without semantic inference.

    This type mirrors only the request spelling RelayLM may intentionally emit.
    It does not claim that the configured model/runtime supports or applies these
    controls, and it does not translate RelayLM's provider-neutral ``off`` or
    ``bounded`` modes into vLLM values.
    """

    reasoning_effort: str | None = None
    thinking_token_budget: int | None = None

    def __post_init__(self) -> None:
        if self.reasoning_effort is not None:
            if not isinstance(self.reasoning_effort, str):
                raise TypeError("vLLM reasoning_effort must be a string or None")
            if not self.reasoning_effort.strip():
                raise ValueError("vLLM reasoning_effort must not be empty")
            if self.reasoning_effort not in VLLM_REASONING_EFFORT_VALUES:
                raise ValueError(
                    f"unsupported vLLM reasoning_effort: {self.reasoning_effort}"
                )
        if self.thinking_token_budget is not None:
            if isinstance(self.thinking_token_budget, bool) or not isinstance(
                self.thinking_token_budget, int
            ):
                raise TypeError("vLLM thinking_token_budget must be an integer or None")
            if self.thinking_token_budget <= 0:
                raise ValueError("vLLM thinking_token_budget must be positive")

    @property
    def wire_fields(self) -> ReasoningMapping:
        fields: list[tuple[str, str | int]] = []
        if self.reasoning_effort is not None:
            fields.append(("reasoning_effort", self.reasoning_effort))
        if self.thinking_token_budget is not None:
            fields.append(("thinking_token_budget", self.thinking_token_budget))
        return tuple(fields)

    def to_mapping(self) -> dict[str, str | int]:
        return dict(self.wire_fields)
