from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from relaylm.providers.openai_compatible_reasoning import ReasoningMapping
from relaylm.providers.vllm_backend import VLLMBackendAttestation
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls


VLLM_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION = 1
TemplateValue = str | int | bool
TemplateMapping = tuple[tuple[str, TemplateValue], ...]


class VLLMReasoningTargetIdentity(Protocol):
    """Minimal frozen target identity required by reasoning attestation."""

    target_id: str
    revision: str
    model_artifact_identity: str
    artifact_repository_revision: str


class VLLMReasoningCapabilityStatus(StrEnum):
    """Classification of one configured-runtime reasoning probe."""

    UNSUPPORTED = "unsupported"
    ACCEPTED_BUT_EFFECT_UNPROVEN = "accepted_but_effect_unproven"
    SEMANTICALLY_ATTESTED = "semantically_attested"
    MALFORMED_OR_AMBIGUOUS = "malformed_or_ambiguous"


@dataclass(frozen=True, slots=True)
class VLLMReasoningProbeEvidence:
    """Content-free facts from one exact vLLM reasoning probe.

    Protocol acceptance is recorded separately from semantic effect. Template
    kwargs are evidence about the configured model's thinking activation; they
    are not a semantic default and are not provider request serialization.
    """

    wire_controls: VLLMReasoningWireControls
    http_status: int
    accepted: bool
    effect_proven: bool
    repeatable: bool
    activation_applied: bool = False
    template_kwargs: TemplateMapping = ()
    ambiguous: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.wire_controls, VLLMReasoningWireControls):
            raise TypeError("wire_controls must be VLLMReasoningWireControls")
        if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
            raise TypeError("http_status must be an integer")
        if not 100 <= self.http_status <= 599:
            raise ValueError("http_status must be a valid HTTP status")
        for name in (
            "accepted",
            "effect_proven",
            "repeatable",
            "activation_applied",
            "ambiguous",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")
        _validate_template_mapping("template_kwargs", self.template_kwargs)

        is_success = 200 <= self.http_status < 300
        if is_success != self.accepted:
            raise ValueError(
                "HTTP success must be accepted and HTTP failure must be rejected; "
                "otherwise the probe is ambiguous"
            )
        if self.effect_proven and not self.accepted:
            raise ValueError("effect cannot be proven for a rejected probe")
        if self.activation_applied and not self.accepted:
            raise ValueError("activation cannot be applied for a rejected probe")


@dataclass(frozen=True, slots=True)
class VLLMReasoningControlAttestation:
    """Classification and exact probe inputs for one reasoning control."""

    status: VLLMReasoningCapabilityStatus
    probe_wire: ReasoningMapping
    template_kwargs: TemplateMapping
    activation_applied: bool
    http_status: int
    accepted: bool
    effect_proven: bool
    repeatable: bool
    ambiguous: bool
    fallback_wire: ReasoningMapping = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, VLLMReasoningCapabilityStatus):
            raise TypeError("status must be VLLMReasoningCapabilityStatus")
        _validate_reasoning_mapping("probe_wire", self.probe_wire)
        _validate_template_mapping("template_kwargs", self.template_kwargs)
        _validate_reasoning_mapping("fallback_wire", self.fallback_wire)
        if not isinstance(self.activation_applied, bool):
            raise TypeError("activation_applied must be bool")
        if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
            raise TypeError("http_status must be an integer")
        if not 100 <= self.http_status <= 599:
            raise ValueError("http_status must be a valid HTTP status")
        for name in (
            "accepted",
            "effect_proven",
            "repeatable",
            "ambiguous",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")
        if self.fallback_wire:
            raise ValueError("vLLM reasoning attestation must not invent fallback wire")

    def to_mapping(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "probe_wire": dict(self.probe_wire),
            "template_kwargs": dict(self.template_kwargs),
            "activation_applied": self.activation_applied,
            "probe_evidence": {
                "http_status": self.http_status,
                "accepted": self.accepted,
                "effect_proven": self.effect_proven,
                "repeatable": self.repeatable,
                "ambiguous": self.ambiguous,
            },
            "fallback_wire": dict(self.fallback_wire),
        }


@dataclass(frozen=True, slots=True)
class VLLMReasoningCapabilityAttestation:
    """Configured vLLM/model reasoning facts from explicit runtime probes.

    The supplied frozen target identity is part of this identity. The record is
    capability evidence, not an applied provider request and not a cognition
    policy default.
    """

    backend_attestation: VLLMBackendAttestation
    target_id: str
    target_revision: str
    model_artifact_identity: str
    artifact_repository_revision: str
    reasoning_parser: str | None
    template_thinking_control: str | None
    reasoning_off: VLLMReasoningControlAttestation
    reasoning_bounded: VLLMReasoningControlAttestation
    format_version: int = VLLM_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != VLLM_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION:
            raise ValueError(
                "unsupported vLLM reasoning capability attestation format_version: "
                f"{self.format_version}"
            )
        if not isinstance(self.backend_attestation, VLLMBackendAttestation):
            raise TypeError("backend_attestation must be VLLMBackendAttestation")
        for name in (
            "target_id",
            "target_revision",
            "model_artifact_identity",
            "artifact_repository_revision",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"{name} must be a non-empty string")
        for name in ("reasoning_parser", "template_thinking_control"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise TypeError(f"{name} must be a non-empty string or None")
        for name in ("reasoning_off", "reasoning_bounded"):
            if not isinstance(getattr(self, name), VLLMReasoningControlAttestation):
                raise TypeError(f"{name} must be VLLMReasoningControlAttestation")

    @property
    def backend_version(self) -> str:
        return self.backend_attestation.version

    @property
    def request_model(self) -> str:
        return self.backend_attestation.request_model

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "backend": "vllm",
            "version": self.backend_version,
            "request_model": self.request_model,
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "model_artifact_identity": self.model_artifact_identity,
            "artifact_repository_revision": self.artifact_repository_revision,
            "reasoning_parser": self.reasoning_parser,
            "template_thinking_control": self.template_thinking_control,
            "off_conflicting_template_kwargs": {
                "policy": "provider_must_reject",
                "control": self.template_thinking_control,
            },
            "reasoning_off": self.reasoning_off.to_mapping(),
            "reasoning_bounded": self.reasoning_bounded.to_mapping(),
        }


def attest_vllm_reasoning_capabilities(
    *,
    backend_attestation: VLLMBackendAttestation,
    target: VLLMReasoningTargetIdentity,
    reasoning_parser: str | None,
    template_thinking_control: str | None,
    off_probe: VLLMReasoningProbeEvidence,
    bounded_probe: VLLMReasoningProbeEvidence,
) -> VLLMReasoningCapabilityAttestation:
    """Classify OFF and positive-budget probes for one frozen vLLM target.

    The function consumes supplied evidence and performs no network I/O. A
    positive numeric budget is not semantic support unless the exact budget
    field, parser/template activation, observed effect, and repeatability are
    all present. Unsupported or ambiguous observations never get a fallback.
    """

    if not isinstance(backend_attestation, VLLMBackendAttestation):
        raise TypeError("backend_attestation must be VLLMBackendAttestation")
    for name in (
        "target_id",
        "revision",
        "model_artifact_identity",
        "artifact_repository_revision",
    ):
        value = getattr(target, name, None)
        if not isinstance(value, str) or not value.strip():
            raise TypeError(f"target.{name} must be a non-empty string")
    for name, value in (
        ("reasoning_parser", reasoning_parser),
        ("template_thinking_control", template_thinking_control),
    ):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise TypeError(f"{name} must be a non-empty string or None")
    if not isinstance(off_probe, VLLMReasoningProbeEvidence):
        raise TypeError("off_probe must be VLLMReasoningProbeEvidence")
    if not isinstance(bounded_probe, VLLMReasoningProbeEvidence):
        raise TypeError("bounded_probe must be VLLMReasoningProbeEvidence")

    off = _attest_control(
        off_probe,
        control="off",
        template_thinking_control=template_thinking_control,
        activation_context_available=template_thinking_control is not None,
    )
    bounded = _attest_control(
        bounded_probe,
        control="bounded",
        template_thinking_control=template_thinking_control,
        activation_context_available=(
            reasoning_parser is not None and template_thinking_control is not None
        ),
    )
    return VLLMReasoningCapabilityAttestation(
        backend_attestation=backend_attestation,
        target_id=target.target_id,
        target_revision=target.revision,
        model_artifact_identity=target.model_artifact_identity,
        artifact_repository_revision=target.artifact_repository_revision,
        reasoning_parser=reasoning_parser,
        template_thinking_control=template_thinking_control,
        reasoning_off=off,
        reasoning_bounded=bounded,
    )


def _attest_control(
    probe: VLLMReasoningProbeEvidence,
    *,
    control: str,
    template_thinking_control: str | None,
    activation_context_available: bool,
) -> VLLMReasoningControlAttestation:
    status = VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    if probe.ambiguous:
        status = VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    elif not probe.accepted:
        status = VLLMReasoningCapabilityStatus.UNSUPPORTED
    elif control == "off" and (
        probe.wire_controls.reasoning_effort != "none"
        or probe.wire_controls.thinking_token_budget is not None
    ):
        status = VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    elif control == "bounded" and probe.wire_controls.reasoning_effort is not None:
        status = VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    elif control == "off" and (
        probe.activation_applied
        or _template_control_is_true(probe.template_kwargs, template_thinking_control)
    ):
        status = VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    elif control == "bounded" and probe.wire_controls.thinking_token_budget is None:
        status = VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    elif (
        not probe.effect_proven
        or not probe.repeatable
        or not activation_context_available
        or (
            control == "bounded"
            and not _template_control_is_true(
                probe.template_kwargs, template_thinking_control
            )
        )
    ):
        status = VLLMReasoningCapabilityStatus.ACCEPTED_BUT_EFFECT_UNPROVEN

    return VLLMReasoningControlAttestation(
        status=status,
        probe_wire=probe.wire_controls.wire_fields,
        template_kwargs=probe.template_kwargs,
        activation_applied=probe.activation_applied,
        http_status=probe.http_status,
        accepted=probe.accepted,
        effect_proven=probe.effect_proven,
        repeatable=probe.repeatable,
        ambiguous=probe.ambiguous,
    )


def _template_control_is_true(
    values: TemplateMapping,
    control: str | None,
) -> bool:
    if control is None:
        return False
    return dict(values).get(control) is True


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
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise ValueError(f"{name} keys must be unique")
    if tuple(keys) != tuple(sorted(keys)):
        raise ValueError(f"{name} must be sorted by key")


def _validate_template_mapping(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    keys: list[str] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{name} must contain key/value tuples")
        key, value = item
        if not isinstance(key, str) or not key.strip():
            raise TypeError(f"{name} keys must be non-empty strings")
        if isinstance(value, bool):
            pass
        elif isinstance(value, str):
            if not value.strip():
                raise ValueError(f"{name} string values must not be empty")
        elif isinstance(value, int):
            if isinstance(value, bool):
                raise TypeError(f"{name} values must be strings, integers, or booleans")
        else:
            raise TypeError(f"{name} values must be strings, integers, or booleans")
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise ValueError(f"{name} keys must be unique")
    if tuple(keys) != tuple(sorted(keys)):
        raise ValueError(f"{name} must be sorted by key")
