"""Check B3 ownership without freezing one status sentence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def require_any(text: str, *values: str) -> None:
    assert any(value in text for value in values), values


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
        "C2 one-job claim/rehydrate/execute adapter",
    )
    status = read("docs/PROJECT_STATUS.md")
    require(
        status,
        "Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete",
        "B0-B3 durable enqueue and fenced lifecycle",
        "B3 lifecycle: complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
    )
    require_any(
        status,
        "B0-B3 durable enqueue and fenced lifecycle",
        "B3 lifecycle: complete",
    )
    require(read("relaylm/relaymem_slp_queue_state.py"), "relaymem.slp_queue_transition_request.v0")
    print("Phase 6-B3 queue state contract smoke: ok")


if __name__ == "__main__":
    main()
