"""Validate durable queue contracts without coupling to current-status prose."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), relative
    return path.read_text(encoding="utf-8")


def require(text: str, *anchors: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in text]
    assert not missing, missing


def main() -> None:
    b0 = read("docs/contracts/slp/durable-queue.md")
    b1 = read("relaylm/relaymem_slp_dispatch_preflight.py")
    b2 = read("relaylm/relaymem_slp_durable_enqueue.py")
    b3 = read("relaylm/relaymem_slp_queue_state.py")

    require(
        b0,
        "relaymem.slp_durable_job.v0",
        "relaymem.slp_queue_status_projection.v0",
        "Dispatch idempotency",
        "memory-write idempotency",
        "Terminal records are immutable under B3.",
        "B3 does not generate `dead_letter`",
    )
    require(b1, "relaymem.slp_dispatch_preflight.v0", "relaymem.slp_durable_job.v0")
    require(b2, "relaymem.slp_durable_enqueue.v0", "exact_b1_preflight_result_required")
    require(b3, "relaymem.slp_queue_transition_request.v0", "terminal_state_immutable")

    print("Phase 6-B durable queue contract smoke: ok")


if __name__ == "__main__":
    main()
