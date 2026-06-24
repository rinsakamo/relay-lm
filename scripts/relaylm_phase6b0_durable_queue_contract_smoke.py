"""Validate durable queue ownership without freezing an obsolete next-phase label."""
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
    b0 = read("docs/architecture/phase6b0_relayslp_durable_queue_contract.md")
    current = read("docs/architecture/relaymem_slp_current_target.md")
    plan = read("docs/architecture/pipeline_implementation_plan.md")
    status = read("docs/PROJECT_STATUS.md")
    b1 = read("relaylm/relaymem_slp_dispatch_preflight.py")
    b2 = read("relaylm/relaymem_slp_durable_enqueue.py")
    b3 = read("relaylm/relaymem_slp_queue_state.py")

    require(
        b0,
        "relaymem.slp_durable_job.v0",
        "relaymem.slp_queue_status_projection.v0",
        "Dispatch idempotency",
        "memory-write idempotency",
        "terminal-state immutability",
        "B3 does not generate `dead_letter`",
    )
    require(
        current,
        "Phase 6-B2 performs atomic durable enqueue",
        "Phase 6-B3 performs default-off, dry-run-first",
        "C2 one-job claim/rehydrate/execute adapter",
        "durably enqueued jobs",
    )
    require(
        plan,
        "B2 atomic durable enqueue: complete",
        "B3 queue lifecycle helpers: complete",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
    )
    require(
        status,
        "Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
    )
    require(b1, "relaymem.slp_dispatch_preflight.v0", "relaymem.slp_durable_job.v0")
    require(b2, "relaymem.slp_durable_enqueue.v0", "exact_b1_preflight_result_required")
    require(b3, "relaymem.slp_queue_transition_request.v0", "terminal_state_immutable")

    print("Phase 6-B durable queue contract smoke: ok")


if __name__ == "__main__":
    main()
