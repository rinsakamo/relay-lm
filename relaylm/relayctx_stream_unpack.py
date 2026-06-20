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


def _ends_with_sentinel_prefix(text: str) -> bool:
    if not text:
        return False
    max_prefix_len = min(len(text), _MAX_SENTINEL_CHARS - 1)
    for marker in _INTERNAL_SENTINELS:
        upper = min(max_prefix_len, len(marker) - 1)
        for prefix_len in range(_MIN_PARTIAL_SENTINEL_PREFIX_CHARS, upper + 1):
            if text.endswith(marker[:prefix_len]):
                return True
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
