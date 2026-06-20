"""RelayCTX TTS-safe segmentation hint helper.

Phase 5.5-C0 is intentionally pure and helper-only. It derives bounded
segmentation hints from already-safe visible output, but it does not execute
TTS, control avatars, persist visible text, or wire into request-runtime SSE.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_CLOSE, RELAYCTX_UPDATE_OPEN

RelayCTXTTSHintStatus = Literal[
    "disabled",
    "dry_run_ready",
    "ready",
    "empty_input",
    "blocked",
    "invalid_input",
]
RelayCTXTTSBoundaryKind = Literal[
    "sentence_punctuation",
    "newline",
    "length_limit",
    "stream_end",
]

_INTERNAL_SENTINELS = (RELAYCTX_UPDATE_OPEN, RELAYCTX_UPDATE_CLOSE)
_MAX_SENTINEL_CHARS = max(len(marker) for marker in _INTERNAL_SENTINELS)
_MIN_PARTIAL_SENTINEL_PREFIX_CHARS = 5
_DEFAULT_MAX_SEGMENT_CHARS = 120
_DEFAULT_MIN_SEGMENT_CHARS = 8
_HARD_SENTENCE_BOUNDARY_CHARS = frozenset("。．.!！?？")
_NEWLINE_BOUNDARY_CHARS = frozenset("\r\n")


@dataclass(frozen=True)
class RelayCTXTTSHint:
    """Content-free character-range hint for downstream TTS segmentation."""

    start_char: int
    end_char: int
    char_count: int
    boundary_kind: RelayCTXTTSBoundaryKind
    recommended_flush: bool
    reason_ids: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    def to_log_dict(self) -> dict[str, object]:
        """Return a text-free hint projection."""

        return {
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "boundary_kind": self.boundary_kind,
            "recommended_flush": self.recommended_flush,
            "reason_ids": list(self.reason_ids),
            "content_free": True,
        }


@dataclass(frozen=True)
class RelayCTXTTSHintResult:
    """Runtime-private segmentation hint result.

    The original visible text is intentionally not stored. Callers that need to
    apply hints must retain the already-safe visible text separately in
    request-local runtime state.
    """

    status: RelayCTXTTSHintStatus
    hints: tuple[RelayCTXTTSHint, ...]
    chunk_count: int
    valid_chunk_count: int
    invalid_chunk_count: int
    observed_chars: int
    max_segment_chars: int
    min_segment_chars: int
    enabled: bool
    dry_run_only: bool
    internal_marker_present: bool
    terminal_partial_sentinel: bool
    candidate_hint_count: int
    emitted_hint_count: int
    tts_execution_requested: bool
    avatar_control_requested: bool
    blocked_reasons: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    @property
    def persistence_allowed(self) -> bool:
        return False

    @property
    def hints_emitted(self) -> bool:
        return self.emitted_hint_count > 0

    def to_log_dict(self) -> dict[str, object]:
        """Return content-free diagnostics; hints and visible text are omitted."""

        return {
            "schema_version": "relayctx_tts_segmentation_hints.v0",
            "status": self.status,
            "chunk_count": self.chunk_count,
            "valid_chunk_count": self.valid_chunk_count,
            "invalid_chunk_count": self.invalid_chunk_count,
            "observed_chars": self.observed_chars,
            "max_segment_chars": self.max_segment_chars,
            "min_segment_chars": self.min_segment_chars,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "internal_marker_present": self.internal_marker_present,
            "terminal_partial_sentinel": self.terminal_partial_sentinel,
            "candidate_hint_count": self.candidate_hint_count,
            "emitted_hint_count": self.emitted_hint_count,
            "hints_emitted": self.hints_emitted,
            "tts_execution_requested": False,
            "avatar_control_requested": False,
            "blocked_reasons": list(self.blocked_reasons),
            "content_free": True,
            "persistence_allowed": False,
        }


def build_tts_safe_segmentation_hints(
    chunks: Iterable[str | bytes | object],
    *,
    enabled: bool,
    dry_run_only: bool = True,
    max_segment_chars: int = _DEFAULT_MAX_SEGMENT_CHARS,
    min_segment_chars: int = _DEFAULT_MIN_SEGMENT_CHARS,
) -> RelayCTXTTSHintResult:
    """Build bounded TTS segmentation hints from safe visible chunks.

    This helper is intentionally not wired into request runtime. It accepts only
    visible string chunks and returns text-free character-range hints. Any
    RelayCTX internal sentinel material blocks hint emission.
    """

    max_segment_chars, min_segment_chars = _normalize_segment_limits(
        max_segment_chars=max_segment_chars,
        min_segment_chars=min_segment_chars,
    )

    raw_chunks = tuple(chunks)
    valid_chunks: list[str] = []
    invalid_chunk_count = 0
    reasons: list[str] = []
    for chunk in raw_chunks:
        if isinstance(chunk, str):
            valid_chunks.append(chunk)
        else:
            invalid_chunk_count += 1
            reasons.append("non_string_chunk")

    visible_text = "".join(valid_chunks)
    observed_chars = len(visible_text)
    internal_marker_present = any(marker in visible_text for marker in _INTERNAL_SENTINELS)
    terminal_partial_sentinel = _terminal_partial_prefix_index(visible_text) is not None
    if internal_marker_present:
        reasons.append("internal_sentinel_detected")
    if terminal_partial_sentinel:
        reasons.append("partial_internal_sentinel_prefix")

    if not enabled:
        status: RelayCTXTTSHintStatus = "disabled"
        candidate_hints: tuple[RelayCTXTTSHint, ...] = ()
        emitted_hints: tuple[RelayCTXTTSHint, ...] = ()
    elif invalid_chunk_count:
        status = "invalid_input"
        candidate_hints = ()
        emitted_hints = ()
    elif internal_marker_present or terminal_partial_sentinel:
        status = "blocked"
        candidate_hints = ()
        emitted_hints = ()
    elif not visible_text:
        status = "empty_input"
        candidate_hints = ()
        emitted_hints = ()
    else:
        candidate_hints = tuple(
            _segment_text_by_boundaries(
                visible_text,
                max_segment_chars=max_segment_chars,
                min_segment_chars=min_segment_chars,
            )
        )
        if dry_run_only:
            status = "dry_run_ready"
            emitted_hints = ()
        else:
            status = "ready"
            emitted_hints = candidate_hints

    return RelayCTXTTSHintResult(
        status=status,
        hints=emitted_hints,
        chunk_count=len(raw_chunks),
        valid_chunk_count=len(valid_chunks),
        invalid_chunk_count=invalid_chunk_count,
        observed_chars=observed_chars,
        max_segment_chars=max_segment_chars,
        min_segment_chars=min_segment_chars,
        enabled=enabled,
        dry_run_only=dry_run_only,
        internal_marker_present=internal_marker_present,
        terminal_partial_sentinel=terminal_partial_sentinel,
        candidate_hint_count=len(candidate_hints),
        emitted_hint_count=len(emitted_hints),
        tts_execution_requested=False,
        avatar_control_requested=False,
        blocked_reasons=tuple(_dedupe(reasons)),
    )


def build_relayctx_tts_segmentation_node_result(
    result: RelayCTXTTSHintResult,
) -> PipelineNodeResult:
    """Build a content-free node result for TTS segmentation hints."""

    status = "diagnostic_only"
    if result.status == "invalid_input":
        status = "failed"
    elif result.status == "blocked":
        status = "blocked"
    elif result.status == "ready":
        status = "applied"
    return build_pipeline_node_result(
        node_name="relayctx_tts_segmentation_hints",
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_tts_segmentation_hints",
                "schema_version": "relayctx_tts_segmentation_hints.v0",
                "present": True,
                "content_free": True,
                "hint_ranges_content_free": True,
                "visible_text_omitted": True,
                "tts_execution_requested": False,
                "avatar_control_requested": False,
                "persistence_allowed": False,
            }
        ],
    )


def _segment_text_by_boundaries(
    text: str,
    *,
    max_segment_chars: int,
    min_segment_chars: int,
) -> Iterable[RelayCTXTTSHint]:
    segment_start = 0
    index = 0
    while index < len(text):
        current_char = text[index]
        segment_len = index + 1 - segment_start
        if current_char in _NEWLINE_BOUNDARY_CHARS and segment_len >= min_segment_chars:
            yield _build_hint(
                segment_start,
                index + 1,
                boundary_kind="newline",
                recommended_flush=True,
                reason_id="newline_boundary_detected",
            )
            segment_start = index + 1
        elif (
            current_char in _HARD_SENTENCE_BOUNDARY_CHARS
            and segment_len >= min_segment_chars
        ):
            yield _build_hint(
                segment_start,
                index + 1,
                boundary_kind="sentence_punctuation",
                recommended_flush=True,
                reason_id="sentence_boundary_detected",
            )
            segment_start = index + 1
        elif segment_len >= max_segment_chars:
            yield _build_hint(
                segment_start,
                index + 1,
                boundary_kind="length_limit",
                recommended_flush=False,
                reason_id="max_segment_chars_reached",
            )
            segment_start = index + 1
        index += 1

    if segment_start < len(text):
        yield _build_hint(
            segment_start,
            len(text),
            boundary_kind="stream_end",
            recommended_flush=True,
            reason_id="stream_end_boundary",
        )


def _build_hint(
    start_char: int,
    end_char: int,
    *,
    boundary_kind: RelayCTXTTSBoundaryKind,
    recommended_flush: bool,
    reason_id: str,
) -> RelayCTXTTSHint:
    return RelayCTXTTSHint(
        start_char=start_char,
        end_char=end_char,
        char_count=end_char - start_char,
        boundary_kind=boundary_kind,
        recommended_flush=recommended_flush,
        reason_ids=(reason_id,),
    )


def _normalize_segment_limits(
    *,
    max_segment_chars: int,
    min_segment_chars: int,
) -> tuple[int, int]:
    if (
        not isinstance(max_segment_chars, int)
        or isinstance(max_segment_chars, bool)
        or max_segment_chars < 1
    ):
        max_segment_chars = _DEFAULT_MAX_SEGMENT_CHARS
    if (
        not isinstance(min_segment_chars, int)
        or isinstance(min_segment_chars, bool)
        or min_segment_chars < 1
    ):
        min_segment_chars = _DEFAULT_MIN_SEGMENT_CHARS
    if min_segment_chars > max_segment_chars:
        min_segment_chars = max(1, min(_DEFAULT_MIN_SEGMENT_CHARS, max_segment_chars))
    return max_segment_chars, min_segment_chars


def _terminal_partial_prefix_index(text: str) -> int | None:
    if not text:
        return None
    max_prefix_len = min(len(text), _MAX_SENTINEL_CHARS - 1)
    for marker in _INTERNAL_SENTINELS:
        upper = min(max_prefix_len, len(marker) - 1)
        for prefix_len in range(upper, _MIN_PARTIAL_SENTINEL_PREFIX_CHARS - 1, -1):
            if text.endswith(marker[:prefix_len]):
                return len(text) - prefix_len
    return None


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
