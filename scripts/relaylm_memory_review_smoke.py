from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_review import (
    MemoryReviewCandidate,
    append_memory_review_candidate,
    build_memory_review_candidate_from_trace,
    build_memory_review_id,
    draft_memory_review_candidate_from_trace_response,
    read_memory_review_candidates,
)
from relaylm.trace import build_trace_record


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    trace = build_trace_record(
        trace_id="trace-001",
        character_id="default",
        route_model="relaylm-default",
        mode_applied="memory_light",
        compiler_used=True,
        messages=[{"role": "user", "content": "I like warm tea."}],
        response_text="Remember that the user likes warm tea during late-night work.",
        metadata={"event": "backend_response"},
        created_at="2026-05-22T00:00:00+00:00",
    )

    candidate = build_memory_review_candidate_from_trace(
        trace,
        proposed_memory_id="default-warm-tea",
        content="The user likes warm tea during late-night work.",
        suggested_state="promoted",
        reason="user_preference_detected",
    )
    require(isinstance(candidate, MemoryReviewCandidate), candidate)
    require(candidate.review_id == "review-t9:trace-001-m16:default-warm-tea", candidate)
    require(candidate.source_trace_id == "trace-001", candidate)
    require(candidate.character_id == "default", candidate)
    require(candidate.suggested_state == "promoted", candidate)
    require(candidate.status == "pending", candidate)
    print("ok build memory review candidate from explicit reviewed content")

    colliding_a = build_memory_review_id(trace_id="a-b", proposed_memory_id="c")
    colliding_b = build_memory_review_id(trace_id="a", proposed_memory_id="b-c")
    require(colliding_a != colliding_b, (colliding_a, colliding_b))
    require(colliding_a == "review-t3:a-b-m1:c", colliding_a)
    require(colliding_b == "review-t1:a-m3:b-c", colliding_b)
    print("ok memory review id unambiguous")

    draft = draft_memory_review_candidate_from_trace_response(
        trace,
        proposed_memory_id="default-trace-response",
        max_content_chars=32,
    )
    require(draft is None, draft)
    require(trace.response_text is None, trace)
    print("ok audit trace response content cannot seed a memory review draft")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "memory_review_queue.jsonl"
        require(read_memory_review_candidates(queue_path) == [], "missing queue should read empty")
        append_memory_review_candidate(queue_path, candidate)
        queued = read_memory_review_candidates(queue_path)
        require([item.review_id for item in queued] == [candidate.review_id], queued)
        require(queued[0].suggested_state == "promoted", queued[0])
        print("ok memory review queue append read")

    try:
        build_memory_review_candidate_from_trace(
            trace,
            proposed_memory_id="",
            content="Some content.",
        )
    except ValueError as exc:
        require("proposed_memory_id" in str(exc), str(exc))
        print("ok invalid memory review candidate id error")
    else:
        raise AssertionError("expected invalid proposed_memory_id error")

    try:
        build_memory_review_candidate_from_trace(
            trace,
            proposed_memory_id="bad-content",
            content="   ",
        )
    except ValueError as exc:
        require("content" in str(exc), str(exc))
        print("ok invalid memory review candidate content error")
    else:
        raise AssertionError("expected invalid content error")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
