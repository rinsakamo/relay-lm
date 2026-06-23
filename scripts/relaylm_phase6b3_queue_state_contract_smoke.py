"""Check the B3 document and current integration sequence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def main() -> None:
    require(
        read("docs/architecture/phase6b3_relayslp_queue_state_helpers.md"),
        "Phase 6-B3 is implemented",
        "relaymem.slp_queue_transition_request.v0",
        "relaymem.slp_queue_state_transition.v0",
    )
    require(
        read("docs/architecture/relaymem_slp_current_target.md"),
        "Phase 6-B3 performs default-off, dry-run-first",
        "one-job claim/rehydrate/execute adapter",
    )
    require(
        read("docs/architecture/pipeline_implementation_plan.md"),
        "B3 queue lifecycle helpers: complete",
        "Phase 6-C1-0 through C1-5 are complete",
    )
    require(
        read("docs/PROJECT_STATUS.md"),
        "B3 fenced claim, renew, retry release, stale recovery, and terminal commit",
        "B3 claim -> C1-5 rehydrate -> C1-2 execute",
    )
    require(read("relaylm/relaymem_slp_queue_state.py"), "relaymem.slp_queue_transition_request.v0")
    print("Phase 6-B3 queue state contract smoke: ok")


if __name__ == "__main__":
    main()
