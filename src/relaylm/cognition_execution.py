from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from relaylm.cognitive import CognitiveInput, CognitionExecutionMode
from relaylm.continuity import ContinuityCandidate
from relaylm.state import StateCandidate


class CognitionPolicyUnresolvedError(ValueError):
    """A profile-owned `auto` value reached a pre-generation boundary unresolved."""


class CognitionExecutionCapabilityError(ValueError):
    """Requested cognition behavior is not available in the supplied capability view."""


class CognitionReasoningMode(StrEnum):
    """Provider-neutral reasoning intent for one cognition pass."""

    AUTO = "auto"
    OFF = "off"
    BOUNDED = "bounded"


class CognitionStructuredOutputMode(StrEnum):
    """Pass 2 transport choice for RelayLM-owned structured extraction."""

    AUTO = "auto"
    NATIVE = "native"
    PLAIN = "plain"


class CognitionDecodingControl(StrEnum):
    """Provider-neutral per-pass decoding/output controls owned by COGP."""

    TEMPERATURE = "temperature"
    TOP_P = "top_p"
    MAX_OUTPUT_TOKENS = "max_output_tokens"


class CognitionOptionStatus(StrEnum):
    """Observable pre-generation capability-resolution outcome."""

    APPLIED = "applied"
    OMITTED = "omitted"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class CognitionCompletionMetadata:
    """Provider-supplied content-free completion observation for one cognition pass."""

    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.finish_reason is not None and (
            not isinstance(self.finish_reason, str) or not self.finish_reason.strip()
        ):
            raise TypeError("finish_reason must be a non-empty string or None")
        _validate_optional_nonnegative_integer("prompt_tokens", self.prompt_tokens)
        _validate_optional_nonnegative_integer(
            "completion_tokens", self.completion_tokens
        )
        _validate_optional_nonnegative_integer("total_tokens", self.total_tokens)
        _validate_optional_nonnegative_integer("reasoning_tokens", self.reasoning_tokens)


@dataclass(frozen=True, slots=True)
class CognitionConversationOutput:
    """Pass 1 semantic output plus optional content-free provider completion facts."""

    response: str
    completion: CognitionCompletionMetadata = field(
        default_factory=CognitionCompletionMetadata
    )

    def __post_init__(self) -> None:
        if not isinstance(self.response, str) or not self.response.strip():
            raise ValueError("conversation response must not be empty")
        if not isinstance(self.completion, CognitionCompletionMetadata):
            raise TypeError("completion must be CognitionCompletionMetadata")


@dataclass(frozen=True, slots=True)
class CognitionExtractionInput:
    """Pass 2 input with Pass 1 response as non-authoritative interpretive context."""

    cognitive_input: CognitiveInput
    assistant_response: str

    def __post_init__(self) -> None:
        if not isinstance(self.cognitive_input, CognitiveInput):
            raise TypeError("cognitive_input must be CognitiveInput")
        if not isinstance(self.assistant_response, str) or not self.assistant_response.strip():
            raise ValueError("assistant_response must not be empty")

    @property
    def originating_event_id(self) -> str:
        """RelayLM-owned origin identity; the model does not author this binding."""

        return self.cognitive_input.input.id


@dataclass(frozen=True, slots=True)
class CognitionExtractionOutput:
    """Pass 2 semantic proposals plus optional content-free provider completion facts."""

    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)
    continuity_candidates: tuple[ContinuityCandidate, ...] = field(default_factory=tuple)
    completion: CognitionCompletionMetadata = field(
        default_factory=CognitionCompletionMetadata
    )

    def __post_init__(self) -> None:
        if not isinstance(self.state_candidates, tuple) or not all(
            isinstance(candidate, StateCandidate) for candidate in self.state_candidates
        ):
            raise TypeError("state_candidates must contain StateCandidate values")
        if not isinstance(self.continuity_candidates, tuple) or not all(
            isinstance(candidate, ContinuityCandidate)
            for candidate in self.continuity_candidates
        ):
            raise TypeError(
                "continuity_candidates must contain ContinuityCandidate values"
            )
        if not isinstance(self.completion, CognitionCompletionMetadata):
            raise TypeError("completion must be CognitionCompletionMetadata")


class TwoPassCognitiveProvider(Protocol):
    """One loaded provider/model reused sequentially for Pass 1 then Pass 2."""

    async def generate_conversation(
        self, cognitive_input: CognitiveInput
    ) -> CognitionConversationOutput:
        ...

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        ...


@dataclass(frozen=True, slots=True)
class CognitionReasoningPolicy:
    """Per-pass reasoning policy before profile-owned `auto` resolution."""

    mode: CognitionReasoningMode = CognitionReasoningMode.AUTO
    budget: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CognitionReasoningMode):
            raise TypeError("reasoning mode must be CognitionReasoningMode")
        if self.budget is not None:
            _validate_positive_integer("reasoning budget", self.budget)
            if self.mode is not CognitionReasoningMode.BOUNDED:
                raise ValueError("reasoning budget requires bounded mode")


@dataclass(frozen=True, slots=True)
class CognitionPassPolicy:
    """Provider-neutral pass intent; None means profile-owned `auto` for scalar fields."""

    reasoning: CognitionReasoningPolicy = field(default_factory=CognitionReasoningPolicy)
    temperature: int | float | None = None
    top_p: int | float | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reasoning, CognitionReasoningPolicy):
            raise TypeError("reasoning must be CognitionReasoningPolicy")
        _validate_optional_finite_number("temperature", self.temperature)
        _validate_optional_finite_number("top_p", self.top_p)
        if self.max_output_tokens is not None:
            _validate_positive_integer("max_output_tokens", self.max_output_tokens)


@dataclass(frozen=True, slots=True)
class CognitionPassRequest:
    """Fully profile-resolved pass request presented to capability resolution."""

    reasoning_mode: CognitionReasoningMode | None = None
    reasoning_budget: int | None = None
    temperature: int | float | None = None
    top_p: int | float | None = None
    max_output_tokens: int | None = None
    structured_output_mode: CognitionStructuredOutputMode | None = None

    def __post_init__(self) -> None:
        if self.reasoning_mode is not None and not isinstance(
            self.reasoning_mode, CognitionReasoningMode
        ):
            raise TypeError("reasoning_mode must be CognitionReasoningMode or None")
        if self.reasoning_mode is CognitionReasoningMode.AUTO:
            raise CognitionPolicyUnresolvedError(
                "reasoning mode auto must resolve before generation"
            )
        if self.reasoning_budget is not None:
            _validate_positive_integer("reasoning budget", self.reasoning_budget)
            if self.reasoning_mode is not CognitionReasoningMode.BOUNDED:
                raise ValueError("reasoning budget requires bounded mode")
        _validate_optional_finite_number("temperature", self.temperature)
        _validate_optional_finite_number("top_p", self.top_p)
        if self.max_output_tokens is not None:
            _validate_positive_integer("max_output_tokens", self.max_output_tokens)
        if self.structured_output_mode is not None and not isinstance(
            self.structured_output_mode, CognitionStructuredOutputMode
        ):
            raise TypeError(
                "structured_output_mode must be CognitionStructuredOutputMode or None"
            )


@dataclass(frozen=True, slots=True)
class CognitionExecutionCapabilities:
    """Normalized COGP view over capability facts supplied by the provider owner."""

    structured_output: bool
    streaming: bool
    reasoning_modes: frozenset[CognitionReasoningMode] = field(default_factory=frozenset)
    bounded_reasoning_budget: bool = False
    decoding_controls: frozenset[CognitionDecodingControl] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.structured_output, bool):
            raise TypeError("structured_output must be bool")
        if not isinstance(self.streaming, bool):
            raise TypeError("streaming must be bool")
        if not isinstance(self.reasoning_modes, frozenset):
            raise TypeError("reasoning_modes must be a frozenset")
        if not all(isinstance(mode, CognitionReasoningMode) for mode in self.reasoning_modes):
            raise TypeError("reasoning_modes must contain CognitionReasoningMode values")
        if CognitionReasoningMode.AUTO in self.reasoning_modes:
            raise ValueError("auto is policy resolution, not a provider capability")
        if not isinstance(self.bounded_reasoning_budget, bool):
            raise TypeError("bounded_reasoning_budget must be bool")
        if not isinstance(self.decoding_controls, frozenset):
            raise TypeError("decoding_controls must be a frozenset")
        if not all(
            isinstance(control, CognitionDecodingControl)
            for control in self.decoding_controls
        ):
            raise TypeError(
                "decoding_controls must contain CognitionDecodingControl values"
            )


def normalize_cognition_execution_capabilities(
    *,
    structured_output: bool,
    streaming: bool,
    reasoning_modes: tuple[str, ...],
    bounded_reasoning_budget: bool,
    decoding_controls: tuple[str, ...],
) -> CognitionExecutionCapabilities:
    """Normalize primitive provider-owner facts into the closed COGP vocabulary.

    This function performs no provider discovery and knows no provider-specific
    types. Unknown values, `auto`, and duplicate facts fail closed rather than
    being silently ignored or treated as equivalent capabilities.
    """

    if not isinstance(structured_output, bool):
        raise TypeError("structured_output must be bool")
    if not isinstance(streaming, bool):
        raise TypeError("streaming must be bool")
    if not isinstance(bounded_reasoning_budget, bool):
        raise TypeError("bounded_reasoning_budget must be bool")
    _validate_capability_fact_strings("reasoning_modes", reasoning_modes)
    _validate_capability_fact_strings("decoding_controls", decoding_controls)

    normalized_reasoning: set[CognitionReasoningMode] = set()
    for value in reasoning_modes:
        try:
            mode = CognitionReasoningMode(value)
        except ValueError as exc:
            raise ValueError(f"unsupported cognition reasoning capability: {value}") from exc
        if mode is CognitionReasoningMode.AUTO:
            raise ValueError("auto is policy resolution, not a provider capability")
        normalized_reasoning.add(mode)

    normalized_decoding: set[CognitionDecodingControl] = set()
    for value in decoding_controls:
        try:
            control = CognitionDecodingControl(value)
        except ValueError as exc:
            raise ValueError(f"unsupported cognition decoding capability: {value}") from exc
        normalized_decoding.add(control)

    return CognitionExecutionCapabilities(
        structured_output=structured_output,
        streaming=streaming,
        reasoning_modes=frozenset(normalized_reasoning),
        bounded_reasoning_budget=bounded_reasoning_budget,
        decoding_controls=frozenset(normalized_decoding),
    )


@dataclass(frozen=True, slots=True)
class CognitionOptionResolution:
    """One content-free requested option and its application status."""

    status: CognitionOptionStatus
    value: str | int | float | None

    def to_mapping(self) -> dict[str, object]:
        return {"status": self.status.value, "value": self.value}


@dataclass(frozen=True, slots=True)
class CognitionPassResolution:
    """Content-free capability resolution for one fully resolved pass request."""

    reasoning_mode: CognitionOptionResolution
    reasoning_budget: CognitionOptionResolution
    temperature: CognitionOptionResolution
    top_p: CognitionOptionResolution
    max_output_tokens: CognitionOptionResolution

    @property
    def unsupported_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, option in self._items()
            if option.status is CognitionOptionStatus.UNSUPPORTED
        )

    def require_supported(self) -> None:
        unsupported = self.unsupported_fields
        if unsupported:
            raise CognitionExecutionCapabilityError(
                "unsupported cognition execution options: " + ", ".join(unsupported)
            )

    def to_mapping(self) -> dict[str, dict[str, object]]:
        return {name: option.to_mapping() for name, option in self._items()}

    def _items(self) -> tuple[tuple[str, CognitionOptionResolution], ...]:
        return (
            ("reasoning_mode", self.reasoning_mode),
            ("reasoning_budget", self.reasoning_budget),
            ("temperature", self.temperature),
            ("top_p", self.top_p),
            ("max_output_tokens", self.max_output_tokens),
        )


def resolve_pass_request(
    *,
    request: CognitionPassRequest,
    capabilities: CognitionExecutionCapabilities,
) -> CognitionPassResolution:
    """Classify requested options without silently dropping unsupported behavior."""

    if not isinstance(request, CognitionPassRequest):
        raise TypeError("request must be CognitionPassRequest")
    if not isinstance(capabilities, CognitionExecutionCapabilities):
        raise TypeError("capabilities must be CognitionExecutionCapabilities")

    reasoning_mode = _resolve_reasoning_mode(request, capabilities)
    reasoning_budget = _resolve_reasoning_budget(request, capabilities)
    temperature = _resolve_decoding_control(
        value=request.temperature,
        control=CognitionDecodingControl.TEMPERATURE,
        capabilities=capabilities,
    )
    top_p = _resolve_decoding_control(
        value=request.top_p,
        control=CognitionDecodingControl.TOP_P,
        capabilities=capabilities,
    )
    max_output_tokens = _resolve_decoding_control(
        value=request.max_output_tokens,
        control=CognitionDecodingControl.MAX_OUTPUT_TOKENS,
        capabilities=capabilities,
    )
    return CognitionPassResolution(
        reasoning_mode=reasoning_mode,
        reasoning_budget=reasoning_budget,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
    )


def require_mode_capabilities(
    *,
    mode: CognitionExecutionMode,
    capabilities: CognitionExecutionCapabilities,
    streaming: bool,
) -> None:
    """Fail closed when a resolved execution mode cannot run on supplied capabilities."""

    if not isinstance(mode, CognitionExecutionMode):
        raise TypeError("mode must be CognitionExecutionMode")
    if not isinstance(capabilities, CognitionExecutionCapabilities):
        raise TypeError("capabilities must be CognitionExecutionCapabilities")
    if not isinstance(streaming, bool):
        raise TypeError("streaming must be bool")
    if mode is CognitionExecutionMode.AUTO:
        raise CognitionPolicyUnresolvedError(
            "cognition mode auto must resolve before generation"
        )
    if streaming and not capabilities.streaming:
        raise CognitionExecutionCapabilityError(
            f"{mode.value} streaming requires streaming capability"
        )


def _resolve_reasoning_mode(
    request: CognitionPassRequest,
    capabilities: CognitionExecutionCapabilities,
) -> CognitionOptionResolution:
    mode = request.reasoning_mode
    if mode is None:
        return CognitionOptionResolution(CognitionOptionStatus.OMITTED, None)
    status = (
        CognitionOptionStatus.APPLIED
        if mode in capabilities.reasoning_modes
        else CognitionOptionStatus.UNSUPPORTED
    )
    return CognitionOptionResolution(status, mode.value)


def _resolve_reasoning_budget(
    request: CognitionPassRequest,
    capabilities: CognitionExecutionCapabilities,
) -> CognitionOptionResolution:
    budget = request.reasoning_budget
    if budget is None:
        return CognitionOptionResolution(CognitionOptionStatus.OMITTED, None)
    supported = (
        request.reasoning_mode is CognitionReasoningMode.BOUNDED
        and CognitionReasoningMode.BOUNDED in capabilities.reasoning_modes
        and capabilities.bounded_reasoning_budget
    )
    status = (
        CognitionOptionStatus.APPLIED
        if supported
        else CognitionOptionStatus.UNSUPPORTED
    )
    return CognitionOptionResolution(status, budget)


def _resolve_decoding_control(
    *,
    value: int | float | None,
    control: CognitionDecodingControl,
    capabilities: CognitionExecutionCapabilities,
) -> CognitionOptionResolution:
    if value is None:
        return CognitionOptionResolution(CognitionOptionStatus.OMITTED, None)
    status = (
        CognitionOptionStatus.APPLIED
        if control in capabilities.decoding_controls
        else CognitionOptionStatus.UNSUPPORTED
    )
    return CognitionOptionResolution(status, value)


def _validate_capability_fact_strings(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise TypeError(f"{name} must contain non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must not contain duplicates")


def _validate_optional_finite_number(name: str, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number when provided")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite when provided")


def _validate_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _validate_optional_nonnegative_integer(name: str, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer when provided")
    if value < 0:
        raise ValueError(f"{name} must be non-negative when provided")
