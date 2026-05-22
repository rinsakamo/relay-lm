from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_review import (
    append_memory_review_candidate,
    build_memory_review_candidate_from_trace,
    read_memory_review_candidates,
    update_memory_review_candidate_status,
    update_memory_review_queue_status,
    write_memory_review_candidates,
)
from relaylm.trace import build_trace_record


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_candidate(trace_id: str, memory_id: str):
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
    return build_memory_review_candidate_from_trace(
        trace,
        proposed_memory_id=memory_id,
        content=f"Memory {memory_id}.",
    )


def main() -> int:
    first = make_candidate("trace-status-001", "memory-one")
    second = make_candidate("trace-status-002", "memory-two")

    approved = update_memory_review_candidate_status(first, status="approved")
    require(approved.review_id == first.review_id, approved)
    require(approved.status == "approved", approved)
    require(first.status == "pending", first)
    print("ok update memory review candidate status")

    try:
        update_memory_review_candidate_status(first, status="archived")  # type: ignore[arg-type]
    except ValueError as exc:
        require("status" in str(exc), str(exc))
        print("ok invalid memory review status error")
    else:
        raise AssertionError("expected invalid status error")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "memory_review_queue.jsonl"
        append_memory_review_candidate(queue_path, first)
        append_memory_review_candidate(queue_path, second)

        updated_first = update_memory_review_queue_status(
            queue_path,
            review_id=first.review_id,
            status="approved",
        )
        require(updated_first.status == "approved", updated_first)
        queued = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued] == ["approved", "pending"], queued)
        print("ok approve memory review queue item")

        updated_second = update_memory_review_queue_status(
            queue_path,
            review_id=second.review_id,
            status="rejected",
        )
        require(updated_second.status == "rejected", updated_second)
        queued_again = read_memory_review_candidates(queue_path)
        require([candidate.status for candidate in queued_again] == ["approved", "rejected"], queued_again)
        print("ok reject memory review queue item")

        try:
            update_memory_review_queue_status(
                queue_path,
                review_id="missing-review-id",
                status="approved",
            )
        except ValueError as exc:
            require("not found" in str(exc), str(exc))
            print("ok missing memory review queue item error")
        else:
            raise AssertionError("expected missing review id error")

        write_memory_review_candidates(queue_path, [second, first])
        rewritten = read_memory_review_candidates(queue_path)
        require([candidate.review_id for candidate in rewritten] == [second.review_id, first.review_id], rewritten)
        require([candidate.status for candidate in rewritten] == ["pending", "pending"], rewritten)
        print("ok rewrite memory review queue")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
