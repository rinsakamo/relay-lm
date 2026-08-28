from __future__ import annotations

import argparse
import re
import sys
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
