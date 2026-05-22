"""Reviewable memory lifecycle helpers for RelayLM MVP-6."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from relaylm.trace import TraceRecord


MemoryReviewStatus = Literal["pending", "approved", "rejected"]
MemoryReviewSuggestedState = Literal["active", "promoted", "demoted", "disabled"]


@dataclass(frozen=True)
class MemoryReviewCandidate:
    review_id: str
    source_trace_id: str
    proposed_memory_id: str
    content: str
    character_id: str | None = None
    suggested_state: MemoryReviewSuggestedState = "active"
    reason: str = "manual_review_required"
    status: MemoryReviewStatus = "pending"
    source: str = "trace_review"

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_memory_review_candidate_from_trace(
    trace: TraceRecord,
    *,
    proposed_memory_id: str,
    content: str,
    suggested_state: MemoryReviewSuggestedState = "active",
    reason: str = "trace_response_review",
) -> MemoryReviewCandidate:
    if not content.strip():
        raise ValueError("memory review candidate content must not be empty")
    if not proposed_memory_id.strip():
        raise ValueError("proposed_memory_id must not be empty")
    return MemoryReviewCandidate(
        review_id=f"review-{trace.trace_id}-{proposed_memory_id}",
        source_trace_id=trace.trace_id,
        proposed_memory_id=proposed_memory_id,
        content=content.strip(),
        character_id=trace.character_id,
        suggested_state=suggested_state,
        reason=reason,
        status="pending",
        source="trace_review",
    )


def draft_memory_review_candidate_from_trace_response(
    trace: TraceRecord,
    *,
    proposed_memory_id: str,
    max_content_chars: int = 500,
) -> MemoryReviewCandidate | None:
    response_text = trace.response_text
    if response_text is None or not response_text.strip():
        return None
    content = response_text.strip()
    if max_content_chars > 0 and len(content) > max_content_chars:
        content = content[:max_content_chars].rstrip()
    return build_memory_review_candidate_from_trace(
        trace,
        proposed_memory_id=proposed_memory_id,
        content=content,
        suggested_state="active",
        reason="trace_response_review",
    )
