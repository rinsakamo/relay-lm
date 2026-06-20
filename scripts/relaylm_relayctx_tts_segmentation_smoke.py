#!/usr/bin/env python3
"""Smoke checks for Phase 5.5-C0 TTS-safe segmentation helper."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.relayctx_tts_segmentation import (
    build_relayctx_tts_segmentation_node_result,
    build_tts_safe_segmentation_hints,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN


def main() -> None:
    _assert_disabled_gate_emits_no_hints()
    _assert_dry_run_plans_hints_without_emission()
    _assert_enabled_helper_emits_content_free_offsets()
    _assert_crlf_newline_boundary_is_atomic()
    _assert_length_limit_fallback()
    _assert_internal_candidate_blocks_hints()
    _assert_terminal_partial_marker_blocks_hints()
    _assert_invalid_chunk_fails_closed()
    print("relayctx_tts_segmentation_smoke: ok")


def _assert_disabled_gate_emits_no_hints() -> None:
    result = build_tts_safe_segmentation_hints(
        ["こんにちは。今日は晴れです。"],
        enabled=False,
        dry_run_only=True,
    )
    assert result.status == "disabled"
    assert result.hints == ()
    assert result.candidate_hint_count == 0
    assert result.emitted_hint_count == 0
    assert result.tts_execution_requested is False
    assert result.avatar_control_requested is False


def _assert_dry_run_plans_hints_without_emission() -> None:
    text = "こんにちは。今日は晴れです！よろしくお願いします"
    result = build_tts_safe_segmentation_hints(
        [text],
        enabled=True,
        dry_run_only=True,
        max_segment_chars=80,
        min_segment_chars=3,
    )
    assert result.status == "dry_run_ready"
    assert result.hints == ()
    assert result.candidate_hint_count >= 2
    assert result.emitted_hint_count == 0
    log_dict = result.to_log_dict()
    _assert_absent(log_dict, text, "今日は晴れ", "こんにちは")


def _assert_enabled_helper_emits_content_free_offsets() -> None:
    text = "こんにちは。今日は晴れです！よろしくお願いします"
    result = build_tts_safe_segmentation_hints(
        ["こんにちは。", "今日は晴れです！", "よろしくお願いします"],
        enabled=True,
        dry_run_only=False,
        max_segment_chars=80,
        min_segment_chars=3,
    )
    assert result.status == "ready"
    assert result.candidate_hint_count == result.emitted_hint_count
    assert len(result.hints) >= 3
    assert result.hints[0].start_char == 0
    assert result.hints[0].end_char == len("こんにちは。")
    assert result.hints[0].boundary_kind == "sentence_punctuation"
    assert result.hints[-1].end_char == len(text)
    assert result.hints[-1].boundary_kind == "stream_end"
    assert all(hint.content_free for hint in result.hints)

    node_result = build_relayctx_tts_segmentation_node_result(result)
    assert node_result.node_name == "relayctx_tts_segmentation_hints"
    assert node_result.status == "applied"
    projected = node_result.to_log_dict()
    _assert_absent(projected, text, "今日は晴れ", "よろしくお願いします")
    assert projected["diagnostics"]["emitted_hint_count"] == len(result.hints)


def _assert_crlf_newline_boundary_is_atomic() -> None:
    newline = chr(13) + chr(10)
    text = f"前の文です{newline}次の文です"
    result = build_tts_safe_segmentation_hints(
        [text],
        enabled=True,
        dry_run_only=False,
        max_segment_chars=80,
        min_segment_chars=3,
    )
    crlf_end = text.index(newline) + len(newline)
    assert result.status == "ready"
    assert len(result.hints) >= 2
    assert result.hints[0].boundary_kind == "newline"
    assert result.hints[0].end_char == crlf_end
    assert result.hints[1].start_char == crlf_end
    assert result.hints[1].start_char != text.index(chr(10))
    assert result.hints[0].reason_ids == ("crlf_newline_boundary_detected",)
    _assert_absent(result.to_log_dict(), text, "前の文", "次の文")


def _assert_length_limit_fallback() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    result = build_tts_safe_segmentation_hints(
        [text],
        enabled=True,
        dry_run_only=False,
        max_segment_chars=8,
        min_segment_chars=3,
    )
    assert result.status == "ready"
    assert result.hints
    assert any(hint.boundary_kind == "length_limit" for hint in result.hints)
    assert result.hints[-1].end_char == len(text)


def _assert_internal_candidate_blocks_hints() -> None:
    text = f"visible text {RELAYCTX_UPDATE_OPEN} internal candidate"
    result = build_tts_safe_segmentation_hints(
        [text],
        enabled=True,
        dry_run_only=False,
    )
    assert result.status == "blocked"
    assert result.hints == ()
    assert result.internal_marker_present is True
    assert "internal_sentinel_detected" in result.blocked_reasons
    node_result = build_relayctx_tts_segmentation_node_result(result)
    assert node_result.status == "blocked"
    _assert_absent(node_result.to_log_dict(), RELAYCTX_UPDATE_OPEN, "internal candidate")


def _assert_terminal_partial_marker_blocks_hints() -> None:
    partial_marker = RELAYCTX_UPDATE_OPEN[:6]
    result = build_tts_safe_segmentation_hints(
        [f"visible text {partial_marker}"],
        enabled=True,
        dry_run_only=False,
    )
    assert result.status == "blocked"
    assert result.hints == ()
    assert result.terminal_partial_sentinel is True
    assert "partial_internal_sentinel_prefix" in result.blocked_reasons


def _assert_invalid_chunk_fails_closed() -> None:
    result = build_tts_safe_segmentation_hints(
        ["safe visible", b"not text"],
        enabled=True,
        dry_run_only=False,
    )
    assert result.status == "invalid_input"
    assert result.hints == ()
    assert result.invalid_chunk_count == 1
    node_result = build_relayctx_tts_segmentation_node_result(result)
    assert node_result.status == "failed"
    assert "non_string_chunk" in node_result.blocked_reasons


def _assert_absent(value: Any, *forbidden: str) -> None:
    rendered = _stable_render(value)
    for token in forbidden:
        assert token not in rendered, token


def _stable_render(value: Any) -> str:
    if isinstance(value, Mapping):
        return "{" + ",".join(
            f"{_stable_render(key)}:{_stable_render(value[key])}"
            for key in sorted(value, key=str)
        ) + "}"
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return "[" + ",".join(_stable_render(item) for item in value) + "]"
    return repr(value)


if __name__ == "__main__":
    main()
