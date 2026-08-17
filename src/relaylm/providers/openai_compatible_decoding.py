from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


OpenAICompatibleDecodingControl = Literal["temperature", "top_p", "seed"]
OPENAI_COMPATIBLE_DECODING_CONTROLS = frozenset({"temperature", "top_p", "seed"})


class ProviderCapabilityError(ValueError):
    """Caller requested provider behavior that was not declared available."""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleDecodingConfig:
    """Explicit output-affecting request controls with no numeric defaults."""

    temperature: int | float | None = None
    top_p: int | float | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        _validate_optional_finite_number("temperature", self.temperature)
        _validate_optional_finite_number("top_p", self.top_p)
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise TypeError("seed must be an integer when provided")

    @property
    def requested_controls(self) -> frozenset[OpenAICompatibleDecodingControl]:
        controls: set[OpenAICompatibleDecodingControl] = set()
        if self.temperature is not None:
            controls.add("temperature")
        if self.top_p is not None:
            controls.add("top_p")
        if self.seed is not None:
            controls.add("seed")
        return frozenset(controls)

    def to_mapping(self) -> dict[str, int | float]:
        """Return exactly the controls that will be sent upstream."""

        mapping: dict[str, int | float] = {}
        if self.temperature is not None:
            mapping["temperature"] = self.temperature
        if self.top_p is not None:
            mapping["top_p"] = self.top_p
        if self.seed is not None:
            mapping["seed"] = self.seed
        return mapping


@dataclass(frozen=True, slots=True)
class OpenAICompatibleDecodingCapabilities:
    """Explicit provider/model support declaration for P3 decoding controls."""

    supported_controls: frozenset[OpenAICompatibleDecodingControl] = field(
        default_factory=frozenset
    )

    def __post_init__(self) -> None:
        if not isinstance(self.supported_controls, frozenset):
            raise TypeError("supported_controls must be a frozenset")
        unknown = set(self.supported_controls) - OPENAI_COMPATIBLE_DECODING_CONTROLS
        if unknown:
            raise ValueError(
                "unsupported decoding capability names: " + ", ".join(sorted(unknown))
            )

    def require(self, config: OpenAICompatibleDecodingConfig) -> None:
        if not isinstance(config, OpenAICompatibleDecodingConfig):
            raise TypeError("config must be OpenAICompatibleDecodingConfig")
        missing = config.requested_controls - self.supported_controls
        if missing:
            raise ProviderCapabilityError(
                "requested decoding controls are not declared supported: "
                + ", ".join(sorted(missing))
            )


def _validate_optional_finite_number(name: str, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number when provided")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite when provided")
