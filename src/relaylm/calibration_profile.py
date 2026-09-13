from __future__ import annotations

from dataclasses import dataclass


def _require_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """Stable runtime semantics for one named calibration-profile selection."""

    name: str
    target_window: int
    output_allowance: int
    authority: str

    def __post_init__(self) -> None:
        _require_non_empty_string("calibration_profile.name", self.name)
        _require_positive_int(
            "calibration_profile.target_window", self.target_window
        )
        _require_positive_int(
            "calibration_profile.output_allowance", self.output_allowance
        )
        _require_non_empty_string("calibration_profile.authority", self.authority)
