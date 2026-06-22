"""Contract smoke for the durable RelaySLP queue boundary through Phase 6-B3."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing required file: {relative}"
    return path.read_text(encoding="utf-8")


def _require_all(text: str, values: tuple[str, ...], label: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, f"{label} missing: {missing}"


def main() -> None:
    b0 = _read("docs/architecture/phase6b0_relayslp_durable_queue_contract.md")
    b1 = _read("docs/architecture/phase6b1_relayslp_dispatch_preflight.md")
    b2 = _read("docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md")
    b3 = _read("docs/architecture/phase6b3_relayslp_queue_state_helpers.md")
    current = _read("docs/architecture/relaymem_slp_current_target.md")
    plan = _read("docs/architecture/pipeline_implementation_plan.md")
    status = _read("docs/PROJECT_STATUS.md")
    index = _read("docs/architecture/README.md")

    _require_all(
        b0,
        (
            "relaylm_authority: phase6b0_relayslp_durable_queue",
            "Phase 6-B0 remains the authoritative durable-queue design",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "Dispatch idempotency",
            "memory-write idempotency",
            "create -> queued",
            "queued -> claimed",
            "claimed -> queued",
            "claimed -> succeeded",
            "claimed -> failed",
            "claimed -> cancelled",
            "No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.",
            "compare-and-swap semantics",
            "claim_generation",
            "lease_token",
            "terminal-state immutability",
            "Phase 6-B3: implemented",
            "Phase 6-C worker execution: next",
        ),
        "B0 contract",
    )
    _require_all(b1, ("Phase 6-B1 is implemented", "relaymem.slp_durable_job.v0"), "B1")
    _require_all(b2, ("Phase 6-B2 is implemented", "atomic create-if-absent publication"), "B2")
    _require_all(
        b3,
        (
            "Phase 6-B3 is implemented",
            "claim\nrenew_lease\nretry_release\nstale_recovery\ncommit_terminal",
            "B3 never generates `dead_letter`",
        ),
        "B3",
    )
    _require_all(current, ("Phase 6-B3", "Phase 6-C"), "current target")
    _require_all(plan, ("B3 queue lifecycle helpers: complete", "Phase 6-C worker execution"), "plan")
    _require_all(status, ("complete through Phase 6-B3", "Phase 6-C worker execution"), "status")
    for name in (
        "phase6b0_relayslp_durable_queue_contract.md",
        "phase6b1_relayslp_dispatch_preflight.md",
        "phase6b2_relayslp_atomic_durable_enqueue.md",
        "phase6b3_relayslp_queue_state_helpers.md",
    ):
        assert name in index, f"architecture index missing {name}"

    print("Phase 6-B durable RelaySLP queue contract smoke passed through B3")


if __name__ == "__main__":
    main()
