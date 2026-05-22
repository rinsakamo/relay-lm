"""Reviewable memory lifecycle helpers for RelayLM MVP-6."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

from relaylm.memory_seed import MemorySeed, append_memory_seed
from relaylm.trace import TraceRecord


MemoryReviewStatus = Literal["pending", "approved", "rejected", "applied"]
MemoryReviewSuggestedState = Literal["active", "promoted", "demoted", "disabled"]
VALID_MEMORY_REVIEW_STATUSES: set[str] = {"pending", "approved", "rejected", "applied"}
DUPLICATE_MEMORY_SEED_ERROR_PREFIX = "memory seed entry already exists:"


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


@dataclass(frozen=True)
class MemoryReviewApplyResult:
    applied_review_ids: list[str]
    skipped_review_ids: list[str]
    rejected_review_ids: list[str]
    applied_memory_ids: list[str]

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_memory_review_id(*, trace_id: str, proposed_memory_id: str) -> str:
    """Build an opaque review ID without ambiguous string concatenation."""

    return (
        f"review-t{len(trace_id)}:{trace_id}"
        f"-m{len(proposed_memory_id)}:{proposed_memory_id}"
    )


def memory_review_candidate_from_dict(payload: dict[str, Any]) -> MemoryReviewCandidate:
    return MemoryReviewCandidate(**payload)


def append_memory_review_candidate(path: str | Path, candidate: MemoryReviewCandidate) -> None:
    queue_path = Path(path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(candidate.to_log_dict(), ensure_ascii=False, sort_keys=True) + "\n"
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(line)


def write_memory_review_candidates(
    path: str | Path,
    candidates: list[MemoryReviewCandidate],
) -> None:
    queue_path = Path(path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8") as f:
        for candidate in candidates:
            line = json.dumps(candidate.to_log_dict(), ensure_ascii=False, sort_keys=True)
            f.write(line + "\n")


def read_memory_review_candidates(path: str | Path) -> list[MemoryReviewCandidate]:
    queue_path = Path(path)
    if not queue_path.exists():
        return []
    candidates: list[MemoryReviewCandidate] = []
    with queue_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            candidates.append(memory_review_candidate_from_dict(payload))
    return candidates


def update_memory_review_candidate_status(
    candidate: MemoryReviewCandidate,
    *,
    status: MemoryReviewStatus,
) -> MemoryReviewCandidate:
    if status not in VALID_MEMORY_REVIEW_STATUSES:
        raise ValueError(f"memory review status must be one of {sorted(VALID_MEMORY_REVIEW_STATUSES)}")
    return replace(candidate, status=status)


def update_memory_review_queue_status(
    path: str | Path,
    *,
    review_id: str,
    status: MemoryReviewStatus,
) -> MemoryReviewCandidate:
    candidates = read_memory_review_candidates(path)
    updated: list[MemoryReviewCandidate] = []
    matched: MemoryReviewCandidate | None = None
    for candidate in candidates:
        if candidate.review_id == review_id:
            matched = update_memory_review_candidate_status(candidate, status=status)
            updated.append(matched)
        else:
            updated.append(candidate)
    if matched is None:
        raise ValueError(f"memory review candidate not found: {review_id}")
    write_memory_review_candidates(path, updated)
    return matched


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
        review_id=build_memory_review_id(
            trace_id=trace.trace_id,
            proposed_memory_id=proposed_memory_id,
        ),
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


def approved_memory_review_candidate_to_seed(
    candidate: MemoryReviewCandidate,
    *,
    importance: int = 1,
    tags: tuple[str, ...] = ("reviewed",),
) -> MemorySeed:
    if candidate.status != "approved":
        raise ValueError("only approved memory review candidates can become memory seeds")
    if not candidate.content.strip():
        raise ValueError("approved memory review candidate content must not be empty")
    return MemorySeed(
        memory_id=candidate.proposed_memory_id,
        character_id=candidate.character_id,
        content=candidate.content.strip(),
        importance=importance,
        source="review_queue",
        tags=tags,
        state=candidate.suggested_state,
    )


def apply_approved_memory_reviews_to_seed_file(
    *,
    review_queue_path: str | Path,
    seed_path: str | Path,
    importance: int = 1,
    tags: tuple[str, ...] = ("reviewed",),
) -> MemoryReviewApplyResult:
    candidates = read_memory_review_candidates(review_queue_path)
    updated: list[MemoryReviewCandidate] = []
    applied_review_ids: list[str] = []
    skipped_review_ids: list[str] = []
    rejected_review_ids: list[str] = []
    applied_memory_ids: list[str] = []

    for index, candidate in enumerate(candidates):
        if candidate.status != "approved":
            skipped_review_ids.append(candidate.review_id)
            updated.append(candidate)
            continue
        seed = approved_memory_review_candidate_to_seed(
            candidate,
            importance=importance,
            tags=tags,
        )
        try:
            append_memory_seed(seed_path, seed)
        except ValueError as exc:
            if not str(exc).startswith(DUPLICATE_MEMORY_SEED_ERROR_PREFIX):
                write_memory_review_candidates(
                    review_queue_path,
                    [*updated, *candidates[index:]],
                )
                raise
            rejected_review_ids.append(candidate.review_id)
            updated.append(update_memory_review_candidate_status(candidate, status="rejected"))
            continue
        applied_review_ids.append(candidate.review_id)
        applied_memory_ids.append(seed.memory_id)
        updated.append(update_memory_review_candidate_status(candidate, status="applied"))

    write_memory_review_candidates(review_queue_path, updated)
    return MemoryReviewApplyResult(
        applied_review_ids=applied_review_ids,
        skipped_review_ids=skipped_review_ids,
        rejected_review_ids=rejected_review_ids,
        applied_memory_ids=applied_memory_ids,
    )
