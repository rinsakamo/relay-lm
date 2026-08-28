from __future__ import annotations

import argparse
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


@dataclass(frozen=True, slots=True)
class VLLMLaunchMemoryAdmission:
    """One fresh GPU-memory admission shared by profiler and final vLLM launch."""

    free_bytes: int
    total_bytes: int

    def __post_init__(self) -> None:
        _require_int(self.free_bytes, "free_bytes")
        _require_int(self.total_bytes, "total_bytes")
        if self.free_bytes <= 0:
            raise ValueError("free_bytes must be positive")
        if self.total_bytes <= 0:
            raise ValueError("total_bytes must be positive")
        if self.free_bytes > self.total_bytes:
            raise ValueError("free_bytes must not exceed total_bytes")
        utilization_millis = self._utilization_millis
        if utilization_millis <= 0 or utilization_millis >= 1000:
            raise ValueError(
                "fresh GPU bytes must resolve a utilization strictly between 0.000 and 1.000"
            )

    @classmethod
    def from_fresh_bytes(
        cls,
        *,
        free_bytes: int,
        total_bytes: int,
    ) -> VLLMLaunchMemoryAdmission:
        return cls(free_bytes=free_bytes, total_bytes=total_bytes)

    @property
    def _utilization_millis(self) -> int:
        return (self.free_bytes * 1000) // self.total_bytes

    @property
    def gpu_memory_utilization(self) -> str:
        """Exact three-decimal startup admission derived by downward quantization."""

        return f"0.{self._utilization_millis:03d}"

    def profiler_memory_args(self) -> tuple[str, ...]:
        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--max-model-len",
            "auto",
        )

    def final_memory_args(self, *, kv_cache_memory_bytes: int) -> tuple[str, ...]:
        _require_int(kv_cache_memory_bytes, "kv_cache_memory_bytes")
        if kv_cache_memory_bytes <= 0:
            raise ValueError("kv_cache_memory_bytes must be positive")
        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--kv-cache-memory-bytes",
            str(kv_cache_memory_bytes),
            "--max-model-len",
            "auto",
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
            "recommendation."
        )
    )
    parser.add_argument(
        "--log",
        type=Path,
        required=True,
        help="Path to the raw pinned-vLLM profiler log.",
    )
    return parser


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
