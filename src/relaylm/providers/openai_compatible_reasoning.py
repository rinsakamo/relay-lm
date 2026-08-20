from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


ReasoningValue = str | int
ReasoningMapping = tuple[tuple[str, ReasoningValue], ...]


class OpenAICompatibleReasoningPreflightStatus(StrEnum):
    """Provider-owned request readiness before any backend wire is serialized."""

    OMITTED = "omitted"
    READY = "ready"
    UNSUPPORTED = "unsupported"


class OpenAICompatibleReasoningApplicationStatus(StrEnum):
    """Observable provider realization outcome after request serialization."""

    OMITTED = "omitted"
    UNSUPPORTED = "unsupported"
    APPLIED = "applied"


@dataclass(frozen=True, slots=True)
class OpenAICompatibleReasoningCapabilities:
    """Backend/model reasoning controls attested outside generic OpenAI semantics.

    ``mode_control_supported`` answers whether a per-request mode/effort-like
    control exists. ``supported_mode_values`` is the exact accepted public option
    set when it is known. ``None`` means the option set is unknown, which is not
    permission to send an explicit value. ``token_budget_supported`` is separate
    because some backends may expose an explicit reasoning-token budget without
    the same mode vocabulary.
    """

    mode_control_supported: bool = False
    supported_mode_values: tuple[str, ...] | None = None
    token_budget_supported: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode_control_supported, bool):
            raise TypeError("mode_control_supported must be bool")
        if not isinstance(self.token_budget_supported, bool):
            raise TypeError("token_budget_supported must be bool")
        if self.supported_mode_values is not None:
            if not self.mode_control_supported:
                raise ValueError(
                    "supported_mode_values require mode_control_supported"
                )
            if not isinstance(self.supported_mode_values, tuple):
                raise TypeError("supported_mode_values must be a tuple or None")
            if not self.supported_mode_values:
                raise ValueError("known supported_mode_values must not be empty")
            if not all(
                isinstance(value, str) and value.strip()
                for value in self.supported_mode_values
            ):
                raise TypeError(
                    "supported_mode_values must contain non-empty strings"
                )
            if len(set(self.supported_mode_values)) != len(
                self.supported_mode_values
            ):
                raise ValueError("supported_mode_values must not contain duplicates")
            if tuple(sorted(self.supported_mode_values)) != self.supported_mode_values:
                raise ValueError("supported_mode_values must be sorted")

    @property
    def mode_values_known(self) -> bool:
        return self.supported_mode_values is not None

    def to_mapping(self) -> dict[str, object]:
        return {
            "mode_control_supported": self.mode_control_supported,
            "supported_mode_values": list(self.supported_mode_values or ()),
            "mode_values_known": self.mode_values_known,
            "token_budget_supported": self.token_budget_supported,
        }


@dataclass(frozen=True, slots=True)
class OpenAICompatibleReasoningRequest:
    """Fully resolved reasoning request presented to provider realization.

    Values are explicit caller intent. This type chooses no default, rejects the
    upstream policy value ``auto``, and never decides which cognition pass deserves
    more reasoning.
    """

    mode: str | None = None
    token_budget: int | None = None

    def __post_init__(self) -> None:
        if self.mode is not None and (
            not isinstance(self.mode, str) or not self.mode.strip()
        ):
            raise TypeError("mode must be a non-empty string or None")
        if self.mode == "auto":
            raise ValueError("reasoning mode auto must resolve before provider realization")
        if self.token_budget is not None:
            if isinstance(self.token_budget, bool) or not isinstance(
                self.token_budget, int
            ):
                raise TypeError("token_budget must be an integer or None")
            if self.token_budget <= 0:
                raise ValueError("token_budget must be positive")

    @property
    def requested(self) -> ReasoningMapping:
        values: list[tuple[str, ReasoningValue]] = []
        if self.mode is not None:
            values.append(("mode", self.mode))
        if self.token_budget is not None:
            values.append(("token_budget", self.token_budget))
        return tuple(values)

    def to_mapping(self) -> dict[str, ReasoningValue]:
        return dict(self.requested)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleReasoningPreflight:
    """Fail-closed capability result before exact backend mapping exists."""

    status: OpenAICompatibleReasoningPreflightStatus
    requested: ReasoningMapping
    unsupported_controls: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_reasoning_mapping("requested", self.requested)
        _validate_names("unsupported_controls", self.unsupported_controls)
        if self.status is OpenAICompatibleReasoningPreflightStatus.OMITTED:
            if self.requested or self.unsupported_controls:
                raise ValueError("omitted preflight must have no requested controls")
        elif self.status is OpenAICompatibleReasoningPreflightStatus.READY:
            if not self.requested or self.unsupported_controls:
                raise ValueError(
                    "ready preflight requires requested controls and no unsupported controls"
                )
        elif self.status is OpenAICompatibleReasoningPreflightStatus.UNSUPPORTED:
            if not self.requested or not self.unsupported_controls:
                raise ValueError(
                    "unsupported preflight requires requested and unsupported controls"
                )

    def to_mapping(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "requested": dict(self.requested),
            "unsupported_controls": list(self.unsupported_controls),
        }


@dataclass(frozen=True, slots=True)
class OpenAICompatibleReasoningApplication:
    """Content-free identity for what the provider actually realized.

    ``APPLIED`` is intentionally stronger than preflight ``READY``: it requires
    exact serialized backend fields. R1 creates the invariant only; later wire
    carriage must construct this record from the serializer that actually sends
    those fields.
    """

    status: OpenAICompatibleReasoningApplicationStatus
    requested: ReasoningMapping
    wire_fields: ReasoningMapping

    def __post_init__(self) -> None:
        _validate_reasoning_mapping("requested", self.requested)
        _validate_reasoning_mapping("wire_fields", self.wire_fields)
        if self.status is OpenAICompatibleReasoningApplicationStatus.OMITTED:
            if self.requested or self.wire_fields:
                raise ValueError("omitted reasoning must have no request or wire fields")
        elif self.status is OpenAICompatibleReasoningApplicationStatus.UNSUPPORTED:
            if not self.requested or self.wire_fields:
                raise ValueError(
                    "unsupported reasoning requires a request and no wire fields"
                )
        elif self.status is OpenAICompatibleReasoningApplicationStatus.APPLIED:
            if not self.requested or not self.wire_fields:
                raise ValueError(
                    "applied reasoning requires requested values and exact wire fields"
                )

    def to_mapping(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "requested": dict(self.requested),
            "wire_fields": dict(self.wire_fields),
        }


def preflight_openai_compatible_reasoning(
    *,
    request: OpenAICompatibleReasoningRequest,
    capabilities: OpenAICompatibleReasoningCapabilities,
) -> OpenAICompatibleReasoningPreflight:
    """Classify explicit reasoning intent without guessing backend support."""

    if not isinstance(request, OpenAICompatibleReasoningRequest):
        raise TypeError("request must be OpenAICompatibleReasoningRequest")
    if not isinstance(capabilities, OpenAICompatibleReasoningCapabilities):
        raise TypeError("capabilities must be OpenAICompatibleReasoningCapabilities")

    requested = request.requested
    if not requested:
        return OpenAICompatibleReasoningPreflight(
            status=OpenAICompatibleReasoningPreflightStatus.OMITTED,
            requested=(),
            unsupported_controls=(),
        )

    unsupported: list[str] = []
    if request.mode is not None:
        if (
            not capabilities.mode_control_supported
            or capabilities.supported_mode_values is None
            or request.mode not in capabilities.supported_mode_values
        ):
            unsupported.append("mode")
    if request.token_budget is not None and not capabilities.token_budget_supported:
        unsupported.append("token_budget")

    if unsupported:
        return OpenAICompatibleReasoningPreflight(
            status=OpenAICompatibleReasoningPreflightStatus.UNSUPPORTED,
            requested=requested,
            unsupported_controls=tuple(unsupported),
        )
    return OpenAICompatibleReasoningPreflight(
        status=OpenAICompatibleReasoningPreflightStatus.READY,
        requested=requested,
        unsupported_controls=(),
    )


def _validate_reasoning_mapping(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    keys: list[str] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{name} must contain key/value tuples")
        key, value = item
        if not isinstance(key, str) or not key.strip():
            raise TypeError(f"{name} keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise TypeError(f"{name} values must be strings or integers")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{name} string values must not be empty")
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise ValueError(f"{name} keys must be unique")
    if tuple(sorted(values)) != values:
        raise ValueError(f"{name} must be sorted by key")


def _validate_names(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise TypeError(f"{name} must contain non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must not contain duplicates")
    if tuple(sorted(values)) != values:
        raise ValueError(f"{name} must be sorted")
