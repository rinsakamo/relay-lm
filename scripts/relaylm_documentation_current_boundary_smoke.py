#!/usr/bin/env python3
"""Validate completed Phase I-1 status without pinning later product wording."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read_text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read_text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: superseded boundary remains: {present!r}"


def main() -> None:
    require(
        "docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "durably enqueued jobs",
        "pre-enqueue background-finalizer crash window",
    )
    forbid(
        "docs/PROJECT_STATUS.md",
        "C1-2 one-already-claimed-job worker execution is not yet on `main`",
        "one-job claim/rehydrate/execute adapter     next integration boundary",
    )

    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "C2 exact queued-record claim, canonical reread",
    )
    forbid(
        "docs/architecture/pipeline_implementation_plan.md",
        "The next RelayLM Core boundary is a thin one-job",
        "one-job claim/rehydrate/execute adapter           next",
        "ordinary runtime still lacks the one-job adapter",
        "remaining Phase 6 product connection is one bounded queued-record",
    )

    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "pre-enqueue background-finalizer crash window",
    )

    require(
        "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
        "exact queued B3 record",
        "canonical B3 claim",
        "C1-5 protected-source lookup / rehydrate",
        "unchanged C1-2 one-claimed worker",
        "Queue scanning/scheduling",
        "next-turn recall and scope isolation",
        "Phase I-1 is complete",
        "pre-enqueue background-finalizer crash recovery",
    )

    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
