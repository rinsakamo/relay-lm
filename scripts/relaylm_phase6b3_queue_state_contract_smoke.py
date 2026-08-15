"""Check B3 contract ownership without coupling to status or roadmap prose."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def main() -> None:
    require(
        read("docs/contracts/slp/durable-queue.md"),
        "B3 request schema",
        "relaymem.slp_queue_transition_request.v0",
        "relaymem.slp_queue_state_transition.v0",
    )
    require(
        read("relaylm/relaymem_slp_queue_state.py"),
        "relaymem.slp_queue_transition_request.v0",
        "terminal_state_immutable",
    )
    print("Phase 6-B3 queue state contract smoke: ok")


if __name__ == "__main__":
    main()
