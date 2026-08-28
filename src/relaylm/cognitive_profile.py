from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from relaylm.cognitive import CognitiveProvider
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import ContinuityRuntime
from relaylm.two_pass_turn import CognitionExecutionRuntime


@dataclass(slots=True)
class CognitiveProfileRuntime:
    """One public Cognitive Profile bound to isolated turn authority and a provider."""

    name: str
    package: CognitivePackageDirectory
    provider: CognitiveProvider = field(repr=False)
    physical_model: str
    continuity_runtime: ContinuityRuntime | None = None
    cognition_execution_runtime: CognitionExecutionRuntime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Cognitive Profile name must be a non-empty string")
        if not isinstance(self.package, CognitivePackageDirectory):
            raise TypeError("package must be CognitivePackageDirectory")
        if not isinstance(self.physical_model, str) or not self.physical_model.strip():
            raise ValueError("physical_model must be a non-empty string")
        if self.continuity_runtime is not None and not isinstance(
            self.continuity_runtime, ContinuityRuntime
        ):
            raise TypeError("continuity_runtime must be ContinuityRuntime or None")
        if self.cognition_execution_runtime is not None and not isinstance(
            self.cognition_execution_runtime, CognitionExecutionRuntime
        ):
            raise TypeError(
                "cognition_execution_runtime must be CognitionExecutionRuntime or None"
            )


@dataclass(frozen=True, slots=True)
class CognitiveProfileRegistry:
    """Deterministic public-ID registry for one-request -> one-Profile resolution."""

    profiles: tuple[CognitiveProfileRuntime, ...]
    _by_name: Mapping[str, CognitiveProfileRuntime] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profiles, tuple) or not self.profiles:
            raise ValueError("Cognitive Profile registry must not be empty")
        by_name: dict[str, CognitiveProfileRuntime] = {}
        for profile in self.profiles:
            if not isinstance(profile, CognitiveProfileRuntime):
                raise TypeError("registry profiles must be CognitiveProfileRuntime")
            if profile.name in by_name:
                raise ValueError(f"duplicate Cognitive Profile name: {profile.name}")
            by_name[profile.name] = profile
        object.__setattr__(self, "_by_name", MappingProxyType(by_name))

    @property
    def public_ids(self) -> tuple[str, ...]:
        return tuple(profile.name for profile in self.profiles)

    def resolve(self, public_id: str) -> CognitiveProfileRuntime | None:
        if not isinstance(public_id, str):
            return None
        return self._by_name.get(public_id)
