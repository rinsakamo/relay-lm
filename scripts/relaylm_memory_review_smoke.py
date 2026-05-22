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
    draft_memory_review_candidate_from_trace_response,
    read_memory_review_candidates,
)
from relaylm.trace import build_trace_record


def require(condition: bool, message: str) -> None:
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
    require(candidate.review_id == "review-trace-001-default-warm-tea", candidate)
    require(candidate.source_trace_id == "trace-001", candidate)
    require(candidate.proposed_memory_id == "default-warm-tea", candidate)
    require(candidate.character_id == "default", candidate)
    require(candidate.suggested_state == "promoted", candidate)
    require(candidate.status == "pending", candidate)
    print("ok build memory review candidate")

    log_payload = candidate.to_log_dict()
    require(log_payload["review_id"] == "review-trace-001-default-warm-tea", log_payload)
    require(log_payload["status"] == "pending", log_payload)
    require(log_payload["source"] == "trace_review", log_payload)
    print("ok memory review candidate log payload")

    draft = draft_memory_review_candidate_from_trace_response(
        trace,
        proposed_memory_id="default-trace-response",
        max_content_chars=32,
    )
    require(draft is not None, draft)
    require(draft.content == "Remember that the user likes warm", draft)
    require(draft.reason == "trace_response_review", draft)
    print("ok draft memory review candidate from trace response")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "memory_review_queue.jsonl"
        require(read_memory_review_candidates(queue_path) == [], "missing queue should read empty")
        append_memory_review_candidate(queue_path, candidate)
        append_memory_review_candidate(queue_path, draft)
        queued = read_memory_review_candidates(queue_path)
        require([item.review_id for item in queued] == [candidate.review_id, draft.review_id], queued)
        require(queued[0].suggested_state == "promoted", queued[0])
        require(queued[1].status == "pending", queued[1])
        print("ok memory review queue append read")

    empty_trace = build_trace_record(
        trace_id="trace-empty",
        character_id="default",
        route_model="relaylm-default",
        mode_applied="memory_light",
        compiler_used=True,
        messages=[],
        response_text="   ",
        created_at="2026-05-22T00:00:00+00:00",
    )
    require(
        draft_memory_review_candidate_from_trace_response(
            empty_trace,
            proposed_memory_id="empty",
        )
        is None,
        "blank response should not produce candidate",
    )
    print("ok blank trace response skipped")

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
