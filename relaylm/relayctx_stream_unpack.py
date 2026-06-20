"""RelayCTX stream Unpack dry-run sentinel observation.

Phase 5.5-A is intentionally pure and diagnostics-only. It observes streamed
visible text fragments for RelayCTX internal markers across chunk boundaries but
never mutates outgoing SSE events, emits TTS hints, or persists runtime-private
content.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_CLOSE, RELAYCTX_UPDATE_OPEN

RelayCTXStreamUnpackStatus = Literal[
    "clean",
    "sentinel_detected",
    "partial_sentinel",
    "invalid_input",
]
RelayCTXStreamSuppressionStatus = Literal[
    "disabled",
    "dry_run_clean",
    "dry_run_suppression_candidate",
    "clean",
    "suppressed",
    "partial_blocked",
    "invalid_input",
]

_INTERNAL_SENTINELS = (RELAYCTX_UPDATE_OPEN, RELAYCTX_UPDATE_CLOSE)
_MAX_SENTINEL_CHARS = max(len(marker) for marker in _INTERNAL_SENTINELS)
_MIN_PARTIAL_SENTINEL_PREFIX_CHARS = 5
_DEFAULT_MAX_BUFFER_CHARS = 256


@dataclass(frozen=True)
class RelayCTXStreamUnpackObservation:
    """Content-free stream sentinel observation."""

    status: RelayCTXStreamUnpackStatus
    chunk_count: int
    valid_chunk_count: int
    invalid_chunk_count: int
    observed_chars: int
    max_buffer_chars: int
    retained_buffer_chars: int
    marker_present: bool
    complete_sentinel_detected: bool
    split_sentinel_detected: bool
    terminal_partial_sentinel: bool
    update_candidate_present: bool
    blocked_reasons: tuple[str, ...]

    @property
    def emitted_chunks_unchanged(self) -> bool:
        return True

    @property
    def content_free(self) -> bool:
        return True

    @property
    def persistence_allowed(self) -> bool:
        return False

    @property
    def tts_hints_emitted(self) -> bool:
        return False

    def to_log_dict(self) -> dict[str, object]:
        """Return content-free diagnostics for trace/node-result surfaces."""

        return {
            "schema_version": "relayctx_stream_unpack_observation.v0",
            "status": self.status,
            "chunk_count": self.chunk_count,
            "valid_chunk_count": self.valid_chunk_count,
            "invalid_chunk_count": self.invalid_chunk_count,
            "observed_chars": self.observed_chars,
            "max_buffer_chars": self.max_buffer_chars,
            "retained_buffer_chars": self.retained_buffer_chars,
            "marker_present": self.marker_present,
            "complete_sentinel_detected": self.complete_sentinel_detected,
            "split_sentinel_detected": self.split_sentinel_detected,
            "terminal_partial_sentinel": self.terminal_partial_sentinel,
            "update_candidate_present": self.update_candidate_present,
            "blocked_reasons": list(self.blocked_reasons),
            "emitted_chunks_unchanged": True,
            "content_free": True,
            "persistence_allowed": False,
            "tts_hints_emitted": False,
        }


@dataclass(frozen=True)
class RelayCTXStreamSuppressionResult:
    """Runtime-private visible stream preservation/suppression result."""

    status: RelayCTXStreamSuppressionStatus
    output_chunks: tuple[str, ...]
    chunk_count: int
    valid_chunk_count: int
    invalid_chunk_count: int
    observed_chars: int
    emitted_chars: int
    suppressed_chars: int
    max_buffer_chars: int
    enabled: bool
    dry_run_only: bool
    marker_present: bool
    complete_sentinel_detected: bool
    split_sentinel_detected: bool
    terminal_partial_sentinel: bool
    suppression_applied: bool
    suppression_would_apply: bool
    output_mutated: bool
    blocked_reasons: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    @property
    def persistence_allowed(self) -> bool:
        return False

    @property
    def tts_hints_emitted(self) -> bool:
        return False

    def to_log_dict(self) -> dict[str, object]:
        """Return content-free diagnostics; output chunks are intentionally omitted."""

        return {
            "schema_version": "relayctx_stream_suppression.v0",
            "status": self.status,
            "chunk_count": self.chunk_count,
            "valid_chunk_count": self.valid_chunk_count,
            "invalid_chunk_count": self.invalid_chunk_count,
            "observed_chars": self.observed_chars,
            "emitted_chars": self.emitted_chars,
            "suppressed_chars": self.suppressed_chars,
            "max_buffer_chars": self.max_buffer_chars,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "marker_present": self.marker_present,
            "complete_sentinel_detected": self.complete_sentinel_detected,
            "split_sentinel_detected": self.split_sentinel_detected,
            "terminal_partial_sentinel": self.terminal_partial_sentinel,
            "suppression_applied": self.suppression_applied,
            "suppression_would_apply": self.suppression_would_apply,
            "output_mutated": self.output_mutated,
            "blocked_reasons": list(self.blocked_reasons),
            "content_free": True,
            "persistence_allowed": False,
            "tts_hints_emitted": False,
        }


def observe_stream_sentinel_buffer(
    chunks: Iterable[str | bytes | object],
    *,
    max_buffer_chars: int = _DEFAULT_MAX_BUFFER_CHARS,
) -> RelayCTXStreamUnpackObservation:
    """Observe streamed fragments for RelayCTX internal markers.

    The helper is dry-run only. It does not return or mutate visible text. The
    retained buffer exists only request-locally while the helper runs and is not
    exposed through the returned observation.
    """

    if (
        not isinstance(max_buffer_chars, int)
        or isinstance(max_buffer_chars, bool)
        or max_buffer_chars < _MAX_SENTINEL_CHARS
    ):
        max_buffer_chars = _DEFAULT_MAX_BUFFER_CHARS

    retained = ""
    chunk_count = 0
    valid_chunk_count = 0
    invalid_chunk_count = 0
    observed_chars = 0
    complete_sentinel_detected = False
    split_sentinel_detected = False
    terminal_partial_sentinel = False
    reasons: list[str] = []

    for chunk in chunks:
        chunk_count += 1
        if not isinstance(chunk, str):
            invalid_chunk_count += 1
            reasons.append("non_string_chunk")
            continue

        valid_chunk_count += 1
        observed_chars += len(chunk)
        previous_tail = retained[-(_MAX_SENTINEL_CHARS - 1) :]
        boundary_text = previous_tail + chunk

        chunk_has_complete = any(marker in chunk for marker in _INTERNAL_SENTINELS)
        boundary_has_complete = any(
            marker in boundary_text for marker in _INTERNAL_SENTINELS
        )
        if chunk_has_complete or boundary_has_complete:
            complete_sentinel_detected = True
            reasons.append("internal_sentinel_detected")
        if boundary_has_complete and not chunk_has_complete:
            split_sentinel_detected = True
            reasons.append("split_internal_sentinel_detected")

        retained = (retained + chunk)[-max_buffer_chars:]
        if _ends_with_sentinel_prefix(retained):
            terminal_partial_sentinel = True
            reasons.append("partial_internal_sentinel_prefix")
        else:
            terminal_partial_sentinel = False

    if invalid_chunk_count:
        status: RelayCTXStreamUnpackStatus = "invalid_input"
    elif complete_sentinel_detected:
        status = "sentinel_detected"
    elif terminal_partial_sentinel or split_sentinel_detected:
        status = "partial_sentinel"
    else:
        status = "clean"

    marker_present = complete_sentinel_detected or terminal_partial_sentinel
    update_candidate_present = marker_present or split_sentinel_detected

    return RelayCTXStreamUnpackObservation(
        status=status,
        chunk_count=chunk_count,
        valid_chunk_count=valid_chunk_count,
        invalid_chunk_count=invalid_chunk_count,
        observed_chars=observed_chars,
        max_buffer_chars=max_buffer_chars,
        retained_buffer_chars=len(retained),
        marker_present=marker_present,
        complete_sentinel_detected=complete_sentinel_detected,
        split_sentinel_detected=split_sentinel_detected,
        terminal_partial_sentinel=terminal_partial_sentinel,
        update_candidate_present=update_candidate_present,
        blocked_reasons=tuple(_dedupe(reasons)),
    )


def apply_stream_internal_suppression_gate(
    chunks: Iterable[str | bytes | object],
    *,
    enabled: bool,
    dry_run_only: bool = True,
    max_buffer_chars: int = _DEFAULT_MAX_BUFFER_CHARS,
) -> RelayCTXStreamSuppressionResult:
    """Preserve safe visible stream text while gating internal candidates.

    This Phase 5.5-B helper is request-runtime-ready but not wired into the
    FastAPI streaming path yet. It returns runtime-private output chunks and
    content-free diagnostics. When disabled or dry-run-only, output chunks remain
    unchanged for valid string chunks.
    """

    if (
        not isinstance(max_buffer_chars, int)
        or isinstance(max_buffer_chars, bool)
        or max_buffer_chars < _MAX_SENTINEL_CHARS
    ):
        max_buffer_chars = _DEFAULT_MAX_BUFFER_CHARS

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

    stream_text = "".join(valid_chunks)
    observed_chars = len(stream_text)
    sentinel_index = _first_sentinel_index(stream_text)
    complete_sentinel_detected = sentinel_index is not None
    split_sentinel_detected = _split_sentinel_detected(valid_chunks)
    partial_index = None if complete_sentinel_detected else _terminal_partial_prefix_index(stream_text)
    terminal_partial_sentinel = partial_index is not None
    marker_present = complete_sentinel_detected or terminal_partial_sentinel
    suppression_would_apply = marker_present or split_sentinel_detected

    if complete_sentinel_detected:
        reasons.append("internal_sentinel_detected")
    if split_sentinel_detected:
        reasons.append("split_internal_sentinel_detected")
    if terminal_partial_sentinel:
        reasons.append("partial_internal_sentinel_prefix")

    if not enabled:
        output_chunks = tuple(valid_chunks)
        status: RelayCTXStreamSuppressionStatus = "disabled"
        suppression_applied = False
        output_mutated = False
    elif invalid_chunk_count:
        output_chunks = ()
        status = "invalid_input"
        suppression_applied = False
        output_mutated = True
    elif dry_run_only:
        output_chunks = tuple(valid_chunks)
        status = "dry_run_suppression_candidate" if suppression_would_apply else "dry_run_clean"
        suppression_applied = False
        output_mutated = False
    elif complete_sentinel_detected:
        safe_text = stream_text[:sentinel_index]
        output_chunks = (safe_text,) if safe_text else ()
        status = "suppressed"
        suppression_applied = True
        output_mutated = True
    elif terminal_partial_sentinel:
        safe_text = stream_text[:partial_index]
        output_chunks = (safe_text,) if safe_text else ()
        status = "partial_blocked"
        suppression_applied = True
        output_mutated = True
    else:
        output_chunks = tuple(valid_chunks)
        status = "clean"
        suppression_applied = False
        output_mutated = False

    emitted_chars = sum(len(chunk) for chunk in output_chunks)
    suppressed_chars = max(0, observed_chars - emitted_chars)
    return RelayCTXStreamSuppressionResult(
        status=status,
        output_chunks=output_chunks,
        chunk_count=len(raw_chunks),
        valid_chunk_count=len(valid_chunks),
        invalid_chunk_count=invalid_chunk_count,
        observed_chars=observed_chars,
        emitted_chars=emitted_chars,
        suppressed_chars=suppressed_chars,
        max_buffer_chars=max_buffer_chars,
        enabled=enabled,
        dry_run_only=dry_run_only,
        marker_present=marker_present,
        complete_sentinel_detected=complete_sentinel_detected,
        split_sentinel_detected=split_sentinel_detected,
        terminal_partial_sentinel=terminal_partial_sentinel,
        suppression_applied=suppression_applied,
        suppression_would_apply=suppression_would_apply,
        output_mutated=output_mutated,
        blocked_reasons=tuple(_dedupe(reasons)),
    )


def build_relayctx_stream_unpack_node_result(
    observation: RelayCTXStreamUnpackObservation,
) -> PipelineNodeResult:
    """Build a content-free dry-run node result for stream sentinel observation."""

    status = "blocked" if observation.update_candidate_present else "diagnostic_only"
    if observation.status == "invalid_input":
        status = "failed"
    return build_pipeline_node_result(
        node_name="relayctx_stream_unpack",
        status=status,
        decision=observation.status,
        blocked_reasons=observation.blocked_reasons,
        diagnostics=observation.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_stream_unpack_observation",
                "schema_version": "relayctx_stream_unpack_observation.v0",
                "present": True,
                "content_free": True,
                "emitted_chunks_unchanged": True,
                "persistence_allowed": False,
            }
        ],
    )


def build_relayctx_stream_suppression_node_result(
    result: RelayCTXStreamSuppressionResult,
) -> PipelineNodeResult:
    """Build a content-free node result for the suppression gate helper."""

    status = "diagnostic_only"
    if result.status == "invalid_input":
        status = "failed"
    elif result.suppression_applied:
        status = "applied"
    elif result.suppression_would_apply:
        status = "blocked"
    return build_pipeline_node_result(
        node_name="relayctx_stream_suppression_gate",
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_stream_suppression",
                "schema_version": "relayctx_stream_suppression.v0",
                "present": True,
                "content_free": True,
                "output_chunks_runtime_private": True,
                "persistence_allowed": False,
            }
        ],
    )


def _ends_with_sentinel_prefix(text: str) -> bool:
    return _terminal_partial_prefix_index(text) is not None


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


def _first_sentinel_index(text: str) -> int | None:
    indexes = [text.find(marker) for marker in _INTERNAL_SENTINELS]
    found = [index for index in indexes if index >= 0]
    return min(found) if found else None


def _split_sentinel_detected(chunks: Iterable[str]) -> bool:
    retained = ""
    for chunk in chunks:
        previous_tail = retained[-(_MAX_SENTINEL_CHARS - 1) :]
        boundary_text = previous_tail + chunk
        chunk_has_complete = any(marker in chunk for marker in _INTERNAL_SENTINELS)
        boundary_has_complete = any(
            marker in boundary_text for marker in _INTERNAL_SENTINELS
        )
        if boundary_has_complete and not chunk_has_complete:
            return True
        retained = (retained + chunk)[-_DEFAULT_MAX_BUFFER_CHARS:]
    return False


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
