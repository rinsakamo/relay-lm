from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_stream_unpack import (  # noqa: E402
    apply_stream_internal_suppression_gate,
    build_relayctx_stream_suppression_node_result,
    build_relayctx_stream_unpack_node_result,
    observe_stream_sentinel_buffer,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN  # noqa: E402


VISIBLE_PREFIX = "安全な表示テキスト。"
INTERNAL_BODY = '{"ctx_working_update":"private"}'
RAW_INVALID_BYTES_TEXT = "raw-bytes-payload"


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


def _assert_suppression_gate_disabled_preserves_chunks() -> None:
    chunks = [VISIBLE_PREFIX, RELAYCTX_UPDATE_OPEN, INTERNAL_BODY]
    result = apply_stream_internal_suppression_gate(
        chunks,
        enabled=False,
        dry_run_only=False,
    )
    require(result.status == "disabled", result)
    require(result.output_chunks == tuple(chunks), result.output_chunks)
    require(result.suppression_applied is False, result)
    require(result.output_mutated is False, result)
    print("ok stream suppression gate disabled preserves chunks")


def _assert_suppression_gate_dry_run_detects_without_mutation() -> None:
    chunks = [VISIBLE_PREFIX, RELAYCTX_UPDATE_OPEN, INTERNAL_BODY]
    result = apply_stream_internal_suppression_gate(
        chunks,
        enabled=True,
        dry_run_only=True,
    )
    require(result.status == "dry_run_suppression_candidate", result)
    require(result.output_chunks == tuple(chunks), result.output_chunks)
    require(result.suppression_would_apply is True, result)
    require(result.suppression_applied is False, result)
    require(result.output_mutated is False, result)
    node_result = build_relayctx_stream_suppression_node_result(result)
    require(node_result.node_name == "relayctx_stream_suppression_gate", node_result)
    require(node_result.status == "blocked", node_result)
    encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require(VISIBLE_PREFIX not in encoded, node_result)
    require(INTERNAL_BODY not in encoded, node_result)
    require(RELAYCTX_UPDATE_OPEN not in encoded, node_result)
    print("ok stream suppression gate dry-run stays content-free and unchanged")


def _assert_suppression_gate_preserves_safe_visible_prefix() -> None:
    chunks = [VISIBLE_PREFIX, RELAYCTX_UPDATE_OPEN + INTERNAL_BODY]
    result = apply_stream_internal_suppression_gate(
        chunks,
        enabled=True,
        dry_run_only=False,
    )
    require(result.status == "suppressed", result)
    require(result.output_chunks == (VISIBLE_PREFIX,), result.output_chunks)
    require(result.suppression_applied is True, result)
    require(result.output_mutated is True, result)
    require(result.suppressed_chars == len(RELAYCTX_UPDATE_OPEN + INTERNAL_BODY), result)
    require("internal_sentinel_detected" in result.blocked_reasons, result)
    node_result = build_relayctx_stream_suppression_node_result(result)
    require(node_result.status == "applied", node_result)
    encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require(VISIBLE_PREFIX not in encoded, node_result)
    require(INTERNAL_BODY not in encoded, node_result)
    require(RELAYCTX_UPDATE_OPEN not in encoded, node_result)
    print("ok stream suppression gate preserves safe visible prefix")


def _assert_suppression_gate_detects_split_marker() -> None:
    split_at = 8
    chunks = [
        VISIBLE_PREFIX,
        RELAYCTX_UPDATE_OPEN[:split_at],
        RELAYCTX_UPDATE_OPEN[split_at:] + INTERNAL_BODY,
    ]
    result = apply_stream_internal_suppression_gate(
        chunks,
        enabled=True,
        dry_run_only=False,
    )
    require(result.status == "suppressed", result)
    require(result.split_sentinel_detected is True, result)
    require(result.output_chunks == (VISIBLE_PREFIX,), result.output_chunks)
    require("split_internal_sentinel_detected" in result.blocked_reasons, result)
    print("ok stream suppression gate suppresses split internal marker")


def _assert_suppression_gate_blocks_terminal_partial_marker() -> None:
    partial = RELAYCTX_UPDATE_OPEN[:12]
    result = apply_stream_internal_suppression_gate(
        [VISIBLE_PREFIX, partial],
        enabled=True,
        dry_run_only=False,
    )
    require(result.status == "partial_blocked", result)
    require(result.output_chunks == (VISIBLE_PREFIX,), result.output_chunks)
    require(result.terminal_partial_sentinel is True, result)
    require(result.suppression_applied is True, result)
    require("partial_internal_sentinel_prefix" in result.blocked_reasons, result)
    print("ok stream suppression gate blocks terminal partial marker")


def _assert_suppression_gate_invalid_input_fails_closed() -> None:
    result = apply_stream_internal_suppression_gate(
        [VISIBLE_PREFIX, RAW_INVALID_BYTES_TEXT.encode("utf-8")],
        enabled=True,
        dry_run_only=False,
    )
    require(result.status == "invalid_input", result)
    require(result.output_chunks == (), result.output_chunks)
    require(result.invalid_chunk_count == 1, result)
    node_result = build_relayctx_stream_suppression_node_result(result)
    require(node_result.status == "failed", node_result)
    encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require(VISIBLE_PREFIX not in encoded, node_result)
    require(RAW_INVALID_BYTES_TEXT not in encoded, node_result)
    print("ok stream suppression gate invalid input fails closed")


def main() -> None:
    _assert_plain_stream_is_unchanged_dry_run()
    _assert_short_less_than_prefix_does_not_false_positive()
    _assert_complete_sentinel_in_one_chunk_is_detected()
    _assert_split_sentinel_across_chunks_is_detected()
    _assert_terminal_partial_sentinel_is_blocked()
    _assert_invalid_chunks_are_content_free_fail_closed()
    _assert_suppression_gate_disabled_preserves_chunks()
    _assert_suppression_gate_dry_run_detects_without_mutation()
    _assert_suppression_gate_preserves_safe_visible_prefix()
    _assert_suppression_gate_detects_split_marker()
    _assert_suppression_gate_blocks_terminal_partial_marker()
    _assert_suppression_gate_invalid_input_fails_closed()


if __name__ == "__main__":
    main()
