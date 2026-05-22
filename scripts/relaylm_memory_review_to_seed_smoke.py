from __future__ import annotations

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_review import (
    approved_memory_review_candidate_to_seed,
    build_memory_review_candidate_from_trace,
)
from relaylm.memory_seed import append_memory_seed, load_memory_seed_file
from relaylm.trace import build_trace_record


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    trace = build_trace_record(
        trace_id="trace-approve-001",
        character_id="default",
        route_model="relaylm-default",
        mode_applied="memory_light",
        compiler_used=True,
        messages=[{"role": "user", "content": "I prefer concise replies."}],
        response_text="The user prefers concise replies.",
        created_at="2026-05-22T00:00:00+00:00",
    )
    pending = build_memory_review_candidate_from_trace(
        trace,
        proposed_memory_id="default-concise-replies",
        content="The user prefers concise replies.",
        suggested_state="promoted",
        reason="user_preference_detected",
    )

    try:
        approved_memory_review_candidate_to_seed(pending)
    except ValueError as exc:
        require("approved" in str(exc), str(exc))
        print("ok pending review cannot become seed")
    else:
        raise AssertionError("expected pending review conversion failure")

    approved = replace(pending, status="approved")
    seed = approved_memory_review_candidate_to_seed(
        approved,
        importance=4,
        tags=("reviewed", "preference"),
    )
    require(seed.memory_id == "default-concise-replies", seed)
    require(seed.character_id == "default", seed)
    require(seed.content == "The user prefers concise replies.", seed)
    require(seed.importance == 4, seed)
    require(seed.source == "review_queue", seed)
    require(seed.tags == ("reviewed", "preference"), seed)
    require(seed.state == "promoted", seed)
    print("ok approved review candidate to seed")

    with tempfile.TemporaryDirectory() as tmpdir:
        seed_path = Path(tmpdir) / "memories.yaml"
        append_memory_seed(seed_path, seed)
        loaded = load_memory_seed_file(seed_path)
        require(len(loaded.memories) == 1, loaded)
        require(loaded.memories[0] == seed, loaded.memories[0])
        print("ok append approved seed to new file")

        second_trace = build_trace_record(
            trace_id="trace-approve-002",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="memory_light",
            compiler_used=True,
            messages=[],
            response_text="The user likes warm tea.",
            created_at="2026-05-22T00:00:00+00:00",
        )
        second = replace(
            build_memory_review_candidate_from_trace(
                second_trace,
                proposed_memory_id="default-warm-tea-reviewed",
                content="The user likes warm tea.",
                suggested_state="active",
            ),
            status="approved",
        )
        second_seed = approved_memory_review_candidate_to_seed(second)
        append_memory_seed(seed_path, second_seed)
        loaded_again = load_memory_seed_file(seed_path)
        require(
            [memory.memory_id for memory in loaded_again.memories]
            == ["default-concise-replies", "default-warm-tea-reviewed"],
            loaded_again.memories,
        )
        print("ok append approved seed to existing file")

        try:
            append_memory_seed(seed_path, seed)
        except ValueError as exc:
            require("already exists" in str(exc), str(exc))
            print("ok duplicate memory seed append rejected")
        else:
            raise AssertionError("expected duplicate memory seed append failure")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
