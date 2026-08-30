from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


_KV_CACHE_FLAG = r"--kv-cache-memory(?:-bytes)?=(?P<bytes>[1-9][0-9]*)"
_FULLY_UTILIZE_ROLE = r"to\s+fully\s+utilize(?:\s+available)?\s+gpu\s+memory"
_KV_CACHE_FULLY_UTILIZE_SUFFIX_PATTERN = re.compile(
    rf"{_KV_CACHE_FLAG}(?:(?!--kv-cache-memory)[^\r\n])*?{_FULLY_UTILIZE_ROLE}",
    re.IGNORECASE,
)
_KV_CACHE_FULLY_UTILIZE_PREFIX_PATTERN = re.compile(
    rf"{_FULLY_UTILIZE_ROLE}(?:(?!--kv-cache-memory)[^\r\n])*?{_KV_CACHE_FLAG}",
    re.IGNORECASE,
)
_MEMORY_UTILIZATION_SCALE = 1_000_000


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityReference:
    """Stable same-launch-class memory geometry for one attested vLLM runtime."""

    non_kv_memory_bytes: int
    kv_cache_memory_bytes: int
    kv_cache_capacity_tokens: int

    def __post_init__(self) -> None:
        for name in (
            "non_kv_memory_bytes",
            "kv_cache_memory_bytes",
            "kv_cache_capacity_tokens",
        ):
            _require_int(getattr(self, name), name)
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

    @classmethod
    def from_successful_launch_envelope(
        cls,
        *,
        startup_free_bytes: int,
        kv_cache_memory_bytes: int,
        kv_cache_capacity_tokens: int,
    ) -> VLLMTokenCapacityReference:
        """Build a conservative non-KV envelope from one successful launch."""

        for name, value in (
            ("startup_free_bytes", startup_free_bytes),
            ("kv_cache_memory_bytes", kv_cache_memory_bytes),
            ("kv_cache_capacity_tokens", kv_cache_capacity_tokens),
        ):
            _require_int(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if kv_cache_memory_bytes >= startup_free_bytes:
            raise ValueError(
                "successful launch evidence must leave positive non-KV memory"
            )
        return cls(
            non_kv_memory_bytes=startup_free_bytes - kv_cache_memory_bytes,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
            kv_cache_capacity_tokens=kv_cache_capacity_tokens,
        )

    @property
    def kv_bytes_per_token_upper_bound(self) -> int:
        """Conservative byte/token slope derived from the attested KV capacity."""

        return _ceil_div(self.kv_cache_memory_bytes, self.kv_cache_capacity_tokens)

    def required_kv_cache_memory_bytes(self, *, target_model_len: int) -> int:
        """Convert one selected token window into explicit KV bytes without extrapolation."""

        _require_int(target_model_len, "target_model_len")
        if target_model_len <= 0:
            raise ValueError("target_model_len must be positive")
        if target_model_len > self.kv_cache_capacity_tokens:
            raise ValueError(
                "target_model_len exceeds the attested KV token capacity; "
                "fresh launch-capability evidence is required"
            )
        return self.kv_bytes_per_token_upper_bound * target_model_len

    def required_total_memory_bytes(self, *, target_model_len: int) -> int:
        return self.non_kv_memory_bytes + self.required_kv_cache_memory_bytes(
            target_model_len=target_model_len
        )


@dataclass(frozen=True, slots=True)
class VLLMLaunchMemoryAdmission:
    """Fresh feasibility check for a fixed, token-derived vLLM memory envelope."""

    free_bytes: int
    total_bytes: int
    required_memory_bytes: int
    target_model_len: int
    kv_cache_memory_bytes: int

    def __post_init__(self) -> None:
        for name in (
            "free_bytes",
            "total_bytes",
            "required_memory_bytes",
            "target_model_len",
            "kv_cache_memory_bytes",
        ):
            _require_int(getattr(self, name), name)
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.free_bytes > self.total_bytes:
            raise ValueError("free_bytes must not exceed total_bytes")
        if self.required_memory_bytes > self.total_bytes:
            raise ValueError("required_memory_bytes must not exceed total_bytes")
        if self.kv_cache_memory_bytes >= self.required_memory_bytes:
            raise ValueError(
                "required_memory_bytes must include positive non-KV memory"
            )
        if self.free_bytes < self.required_memory_bytes:
            raise ValueError(
                "fresh free GPU memory is below the token-derived required memory"
            )
        if self._utilization_units <= 0:
            raise ValueError(
                "required memory is too small to render a positive vLLM startup admission"
            )

    @classmethod
    def for_token_window(
        cls,
        *,
        free_bytes: int,
        total_bytes: int,
        target_model_len: int,
        reference: VLLMTokenCapacityReference,
    ) -> VLLMLaunchMemoryAdmission:
        if not isinstance(reference, VLLMTokenCapacityReference):
            raise TypeError("reference must be VLLMTokenCapacityReference")
        kv_cache_memory_bytes = reference.required_kv_cache_memory_bytes(
            target_model_len=target_model_len
        )
        return cls(
            free_bytes=free_bytes,
            total_bytes=total_bytes,
            required_memory_bytes=(
                reference.non_kv_memory_bytes + kv_cache_memory_bytes
            ),
            target_model_len=target_model_len,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
        )

    @property
    def _utilization_units(self) -> int:
        units = (
            self.required_memory_bytes * _MEMORY_UTILIZATION_SCALE
        ) // self.total_bytes
        if units >= _MEMORY_UTILIZATION_SCALE:
            return _MEMORY_UTILIZATION_SCALE
        while units > 0 and math.ceil(
            self.total_bytes * (units / _MEMORY_UTILIZATION_SCALE)
        ) > self.required_memory_bytes:
            units -= 1
        return units

    @property
    def gpu_memory_utilization(self) -> str:
        """Pinned-vLLM startup guard derived from required bytes, never free bytes."""

        units = self._utilization_units
        whole, fractional = divmod(units, _MEMORY_UTILIZATION_SCALE)
        return f"{whole}.{fractional:06d}"

    def final_memory_args(self) -> tuple[str, ...]:
        """Render the fixed target window and explicit KV budget for final runtime."""

        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--kv-cache-memory-bytes",
            str(self.kv_cache_memory_bytes),
            "--max-model-len",
            str(self.target_model_len),
        )


class VLLMProfilerRecommendationError(ValueError):
    """A profiler log does not contain one unambiguous KV-cache recommendation."""


def parse_vllm_kv_cache_recommendation_bytes(log_text: str) -> int:
    """Return the pinned-vLLM fully-utilize GPU KV-cache recommendation."""

    if not isinstance(log_text, str):
        raise TypeError("log_text must be a string")

    recommendations = {
        int(match.group("bytes"))
        for pattern in (
            _KV_CACHE_FULLY_UTILIZE_SUFFIX_PATTERN,
            _KV_CACHE_FULLY_UTILIZE_PREFIX_PATTERN,
        )
        for match in pattern.finditer(log_text)
    }
    if not recommendations:
        raise VLLMProfilerRecommendationError(
            "vLLM fully-utilize KV-cache recommendation not found"
        )
    if len(recommendations) != 1:
        raise VLLMProfilerRecommendationError(
            "conflicting vLLM fully-utilize KV-cache recommendations"
        )
    return next(iter(recommendations))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the exact pinned-vLLM fully-utilize GPU KV-cache byte "
            "recommendation for launch-capability evidence."
        )
    )
    parser.add_argument(
        "--log",
        type=Path,
        required=True,
        help="Path to the raw pinned-vLLM profiler log.",
    )
    return parser


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def _require_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        log_text = args.log.read_text(encoding="utf-8")
        recommendation = parse_vllm_kv_cache_recommendation_bytes(log_text)
    except (OSError, UnicodeError, VLLMProfilerRecommendationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(recommendation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
