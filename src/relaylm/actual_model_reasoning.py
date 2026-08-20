from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.actual_model_evaluation import ActualModelRunManifest


@dataclass(frozen=True, slots=True)
class ActualModelReasoningEnvironmentIdentity:
    """Content-free attestation of the effective host/model reasoning environment."""

    required_setting: str
    effective_setting: str
    allowed_options: tuple[str, ...]
    live_default: str
    control_source: str
    control_mode: str
    serving_attestation_identity: str
    format_version: int = 1

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(
                "unsupported actual-model reasoning environment format_version: "
                f"{self.format_version}"
            )
        for name in (
            "required_setting",
            "effective_setting",
            "live_default",
            "control_source",
            "control_mode",
            "serving_attestation_identity",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not self.allowed_options or not all(
            isinstance(item, str) and item.strip() for item in self.allowed_options
        ):
            raise ValueError("allowed_options must contain non-empty strings")
        if len(set(self.allowed_options)) != len(self.allowed_options):
            raise ValueError("allowed_options must not contain duplicates")
        canonical_options = tuple(sorted(self.allowed_options))
        object.__setattr__(self, "allowed_options", canonical_options)
        for name in ("required_setting", "effective_setting", "live_default"):
            if getattr(self, name) not in canonical_options:
                raise ValueError(f"{name} must be present in allowed_options")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "required_setting": self.required_setting,
            "effective_setting": self.effective_setting,
            "allowed_options": list(self.allowed_options),
            "live_default": self.live_default,
            "control_source": self.control_source,
            "control_mode": self.control_mode,
            "serving_attestation_identity": self.serving_attestation_identity,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ActualModelReasoningRunManifest(ActualModelRunManifest):
    """Ordinary-turn manifest extended only for reasoning-attested evidence runs."""

    reasoning_environment: ActualModelReasoningEnvironmentIdentity = field(
        kw_only=True
    )

    def __post_init__(self) -> None:
        ActualModelRunManifest.__post_init__(self)
        if not isinstance(
            self.reasoning_environment,
            ActualModelReasoningEnvironmentIdentity,
        ):
            raise TypeError(
                "reasoning_environment must be ActualModelReasoningEnvironmentIdentity"
            )

    def to_mapping(self) -> dict[str, object]:
        mapping = ActualModelRunManifest.to_mapping(self)
        mapping["reasoning_environment"] = self.reasoning_environment.to_mapping()
        return mapping
