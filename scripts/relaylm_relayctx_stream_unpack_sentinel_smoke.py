from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_stream_unpack import (  # noqa: E402
    build_relayctx_stream_unpack_node_result,
    observe_stream_sentinel_buffer,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN  # noqa: E402


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _assert_plain_stream_is_unchanged_dry_run() -> None:
    chunks = ["こんにちは。", "通常の", "SSEです。"]
    observation = observe_stream_sentinel_buffer(chunks)
    require(observation.status == "clean", observation)
    require(observation.chunk_count == 3, observation)
    require(observation.valid_chunk_count == 3, observation)
    require(observation.invalid_chunk_count == 0, observation)
    require(observation.observed_chars == sum(len(chunk) for chunk in chunks), observation)
    require(observation.emitted_chunks_unchanged is True, observation)
    require(observation.update_candidate_present is False, observation)
    require(observation.tts_hints_emitted is False, observation)
    require(observation.persistence_allowed is False, observation)

    node_result = build_relayctx_stream_unpack_node_result(observation)
    require(node_result.node_name == "relayctx_stream_unpack", node_result)
    require(node_result.status == "diagnostic_only", node_result)
    encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require("こんにちは" not in encoded, node_result)
    require("通常の" not in encoded, node_result)
    print("ok stream sentinel observer preserves ordinary stream as dry-run")


def _assert_short_less_than_prefix_does_not_false_positive() -> None:
    observation = observe_stream_sentinel_buffer(["x < y and z <"])
    require(observation.status == "clean", observation)
    require(observation.update_candidate_present is False, observation)
    require(observation.terminal_partial_sentinel is False, observation)
    print("ok stream sentinel observer avoids short less-than false positive")


def _assert_complete_sentinel_in_one_chunk_is_detected() -> None:
    observation = observe_stream_sentinel_buffer(["visible", RELAYCTX_UPDATE_OPEN])
    require(observation.status == "sentinel_detected", observation)
    require(observation.complete_sentinel_detected is True, observation)
    require(observation.marker_present is True, observation)
    require(observation.update_candidate_present is True, observation)
    require("internal_sentinel_detected" in observation.blocked_reasons, observation)

    node_result = build_relayctx_stream_unpack_node_result(observation)
    require(node_result.status == "blocked", node_result)
    encoded = json.dumps(observation.to_log_dict(), ensure_ascii=False)
    require(RELAYCTX_UPDATE_OPEN not in encoded, observation)
    require("visible" not in encoded, observation)
    print("ok stream sentinel observer detects one-chunk internal marker")


def _assert_split_sentinel_across_chunks_is_detected() -> None:
    split_at = 10
    chunks = ["visible ", RELAYCTX_UPDATE_OPEN[:split_at], RELAYCTX_UPDATE_OPEN[split_at:]]
    observation = observe_stream_sentinel_buffer(chunks)
    require(observation.status == "sentinel_detected", observation)
    require(observation.complete_sentinel_detected is True, observation)
    require(observation.split_sentinel_detected is True, observation)
    require("split_internal_sentinel_detected" in observation.blocked_reasons, observation)
    require(observation.emitted_chunks_unchanged is True, observation)
    print("ok stream sentinel observer detects split internal marker")


def _assert_terminal_partial_sentinel_is_blocked() -> None:
    partial = RELAYCTX_UPDATE_OPEN[:12]
    observation = observe_stream_sentinel_buffer(["visible ", partial])
    require(observation.status == "partial_sentinel", observation)
    require(observation.complete_sentinel_detected is False, observation)
    require(observation.terminal_partial_sentinel is True, observation)
    require(observation.marker_present is True, observation)
    require(observation.update_candidate_present is True, observation)
    require("partial_internal_sentinel_prefix" in observation.blocked_reasons, observation)
    print("ok stream sentinel observer blocks terminal partial internal marker")


def _assert_invalid_chunks_are_content_free_fail_closed() -> None:
    observation = observe_stream_sentinel_buffer(["safe", b"bytes are invalid"])
    require(observation.status == "invalid_input", observation)
    require(observation.invalid_chunk_count == 1, observation)
    require("non_string_chunk" in observation.blocked_reasons, observation)
    node_result = build_relayctx_stream_unpack_node_result(observation)
    require(node_result.status == "failed", node_result)
    encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require("safe" not in encoded, node_result)
    require("bytes" not in encoded, node_result)
    print("ok stream sentinel observer rejects invalid chunks content-free")


def main() -> None:
    _assert_plain_stream_is_unchanged_dry_run()
    _assert_short_less_than_prefix_does_not_false_positive()
    _assert_complete_sentinel_in_one_chunk_is_detected()
    _assert_split_sentinel_across_chunks_is_detected()
    _assert_terminal_partial_sentinel_is_blocked()
    _assert_invalid_chunks_are_content_free_fail_closed()


if __name__ == "__main__":
    main()
