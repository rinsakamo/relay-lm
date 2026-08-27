from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_KV_CACHE_RECOMMENDATION_PATTERN = re.compile(
    r"--kv-cache-memory(?:-bytes)?=(?P<bytes>[1-9][0-9]*)"
)


class VLLMProfilerRecommendationError(ValueError):
    """A profiler log does not contain one unambiguous KV-cache recommendation."""


def parse_vllm_kv_cache_recommendation_bytes(log_text: str) -> int:
    """Return the exact positive KV-cache byte recommendation from vLLM output."""

    if not isinstance(log_text, str):
        raise TypeError("log_text must be a string")

    recommendations = {
        int(match.group("bytes"))
        for match in _KV_CACHE_RECOMMENDATION_PATTERN.finditer(log_text)
    }
    if not recommendations:
        raise VLLMProfilerRecommendationError(
            "vLLM KV-cache recommendation not found"
        )
    if len(recommendations) != 1:
        raise VLLMProfilerRecommendationError(
            "conflicting vLLM KV-cache recommendations"
        )
    return next(iter(recommendations))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract the exact vLLM profiler KV-cache byte recommendation."
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
