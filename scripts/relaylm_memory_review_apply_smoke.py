from __future__ import annotations

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_review import (
    MemoryReviewCandidate,
    append_memory_review_candidate,
    apply_approved_memory_reviews_to_seed_file,
    build_memory_review_candidate_from_trace,
    read_memory_review_candidates,
)
from relaylm.memory_seed import load_memory_seed_file
from relaylm.trace import build_trace_record


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_candidate(trace_id: str, memory_id: str, status: str):
    trace = build_trace_record(
        trace_id=trace_id,
        character_id="default",
        route_model="relaylm-default",
        mode_applied="memory_light",
        compiler_used=True,
        messages=[],
        response_text=f"Memory {memory_id}.",
        created_at="2026-05-22T00:00:00+00:00",
    )
    candidate = build_memory_review_candidate_from_trace(
        trace,
        proposed_memory_id=memory_id,
        content=f"Memory {memory_id}.",
        suggested_state="promoted" if status == "approved" else "active",
    )
    return replace(candidate, status=status)  # type: ignore[arg-type]


def main() -> int:
    approved = make_candidate("trace-apply-001", "memory-approved", "approved")
    pending = make_candidate("trace-apply-002", "memory-pending", "pending")
    rejected = make_candidate("trace-apply-003", "memory-rejected", "rejected")
    already_applied = make_candidate("trace-apply-004", "memory-applied", "applied")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "review_queue.jsonl"
        seed_path = Path(tmpdir) / "memories.yaml"
        for candidate in [approved, pending, rejected, already_applied]:
            append_memory_review_candidate(queue_path, candidate)

        result = apply_approved_memory_reviews_to_seed_file(
            review_queue_path=queue_path,
            seed_path=seed_path,
            importance=7,
            tags=("reviewed", "applied"),
        )
        require(result.applied_review_ids == [approved.review_id], result)
        require(result.applied_memory_ids == ["memory-approved"], result)
        require(result.rejected_review_ids == [], result)
        require(result.skipped_review_ids == [
            pending.review_id,
            rejected.review_id,
            already_applied.review_id,
        ], result)
        print("ok apply approved memory reviews result")

        loaded = load_memory_seed_file(seed_path)
        require(len(loaded.memories) == 1, loaded)
        seed = loaded.memories[0]
        require(seed.memory_id == "memory-approved", seed)
        require(seed.importance == 7, seed)
        require(seed.tags == ("reviewed", "applied"), seed)
        require(seed.state == "promoted", seed)
        print("ok apply approved memory reviews to seed file")

        queued = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued] == [
            "applied",
            "pending",
            "rejected",
            "applied",
        ], queued)
        print("ok approved memory reviews marked applied")

        second_result = apply_approved_memory_reviews_to_seed_file(
            review_queue_path=queue_path,
            seed_path=seed_path,
        )
        require(second_result.applied_review_ids == [], second_result)
        require(second_result.applied_memory_ids == [], second_result)
        require(second_result.rejected_review_ids == [], second_result)
        require(len(second_result.skipped_review_ids) == 4, second_result)
        loaded_again = load_memory_seed_file(seed_path)
        require(len(loaded_again.memories) == 1, loaded_again)
        print("ok reapply approved memory reviews is idempotent")

    duplicate_first = make_candidate("trace-dup-001", "memory-duplicate", "approved")
    duplicate_second = make_candidate("trace-dup-002", "memory-duplicate", "approved")
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "review_queue.jsonl"
        seed_path = Path(tmpdir) / "memories.yaml"
        append_memory_review_candidate(queue_path, duplicate_first)
        append_memory_review_candidate(queue_path, duplicate_second)

        result = apply_approved_memory_reviews_to_seed_file(
            review_queue_path=queue_path,
            seed_path=seed_path,
        )
        require(result.applied_review_ids == [duplicate_first.review_id], result)
        require(result.rejected_review_ids == [duplicate_second.review_id], result)
        require(result.applied_memory_ids == ["memory-duplicate"], result)
        queued = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued] == ["applied", "rejected"], queued)
        loaded = load_memory_seed_file(seed_path)
        require(len(loaded.memories) == 1, loaded)
        print("ok duplicate approved memory review does not block queue")

        second_result = apply_approved_memory_reviews_to_seed_file(
            review_queue_path=queue_path,
            seed_path=seed_path,
        )
        require(second_result.applied_review_ids == [], second_result)
        require(second_result.rejected_review_ids == [], second_result)
        require(len(second_result.skipped_review_ids) == 2, second_result)
        print("ok duplicate approved memory review reapply is stable")

    good_first = make_candidate("trace-malformed-001", "memory-malformed-first", "approved")
    malformed_second = make_candidate("trace-malformed-002", "memory-malformed-second", "approved")
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "review_queue.jsonl"
        seed_path = Path(tmpdir) / "memories.yaml"
        append_memory_review_candidate(queue_path, good_first)
        append_memory_review_candidate(queue_path, malformed_second)
        try:
            apply_approved_memory_reviews_to_seed_file(
                review_queue_path=queue_path,
                seed_path=seed_path,
                tags=["bad-tags"],  # type: ignore[arg-type]
            )
        except ValueError as exc:
            require("tags must be a tuple of strings" in str(exc), str(exc))
            print("ok non-duplicate apply error fails fast")
        else:
            raise AssertionError("expected non-duplicate apply failure")
        queued = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued] == ["approved", "approved"], queued)
        print("ok non-duplicate apply error leaves queue unchanged")

    good_first = make_candidate("trace-bad-content-001", "memory-before-bad-content", "approved")
    bad_content = MemoryReviewCandidate(
        review_id="review-bad-content",
        source_trace_id="trace-bad-content-002",
        proposed_memory_id="memory-bad-content",
        content="   ",
        character_id="default",
        status="approved",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "review_queue.jsonl"
        seed_path = Path(tmpdir) / "memories.yaml"
        append_memory_review_candidate(queue_path, good_first)
        append_memory_review_candidate(queue_path, bad_content)
        try:
            apply_approved_memory_reviews_to_seed_file(
                review_queue_path=queue_path,
                seed_path=seed_path,
            )
        except ValueError as exc:
            require("content" in str(exc), str(exc))
            print("ok invalid approved review content fails fast")
        else:
            raise AssertionError("expected invalid approved review content failure")
        queued = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued] == ["applied", "approved"], queued)
        loaded = load_memory_seed_file(seed_path)
        require([memory.memory_id for memory in loaded.memories] == ["memory-before-bad-content"], loaded)
        print("ok invalid approved review content preserves prior progress")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
