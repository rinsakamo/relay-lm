"""Contract smoke for the durable RelaySLP queue boundary through Phase 6-B3."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B0 = ROOT / "docs/architecture/phase6b0_relayslp_durable_queue_contract.md"
B1 = ROOT / "docs/architecture/phase6b1_relayslp_dispatch_preflight.md"
B2 = ROOT / "docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md"
B3 = ROOT / "docs/architecture/phase6b3_relayslp_queue_state_helpers.md"
CURRENT = ROOT / "docs/architecture/relaymem_slp_current_target.md"
PLAN = ROOT / "docs/architecture/pipeline_implementation_plan.md"
STATUS = ROOT / "docs/PROJECT_STATUS.md"
INDEX = ROOT / "docs/architecture/README.md"
A2_HELPER = ROOT / "relaylm/relaymem_slp_response_handoff.py"
B1_HELPER = ROOT / "relaylm/relaymem_slp_dispatch_preflight.py"
B3_HELPER = ROOT / "relaylm/relaymem_slp_queue_state.py"
B1_WORKFLOW = ROOT / ".github/workflows/relaymem-slp-dispatch-preflight-smoke.yml"
B3_WORKFLOW = ROOT / ".github/workflows/relaymem-slp-queue-state-smoke.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _require_all(text: str, values: tuple[str, ...], label: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, f"{label} missing: {missing}"


def _section(text: str, start: str, end: str) -> str:
    begin = text.find(start)
    assert begin >= 0, f"missing section: {start}"
    finish = text.find(end, begin + len(start))
    assert finish >= 0, f"missing section: {end}"
    return text[begin:finish]


def main() -> None:
    b0 = _read(B0)
    b1 = _read(B1)
    b2 = _read(B2)
    b3 = _read(B3)
    current = _read(CURRENT)
    plan = _read(PLAN)
    status = _read(STATUS)
    index = _read(INDEX)
    a2_helper = _read(A2_HELPER)
    b1_helper = _read(B1_HELPER)
    b3_helper = _read(B3_HELPER)
    b1_workflow = _read(B1_WORKFLOW)
    b3_workflow = _read(B3_WORKFLOW)

    _require_all(
        b0,
        (
            "relaylm_authority: phase6b0_relayslp_durable_queue",
            "Phase 6-B0 remains the authoritative durable-queue design",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "Dispatch idempotency",
            "memory-write idempotency",
            "must not be reused as a memory-write key",
            "must not be accepted as a dispatch key",
            "owned by Phase 6 / RelayRUN orchestration",
            "owned by RelayMEM persistence preflight and apply",
        ),
        "B0 identity ownership",
    )
    _require_all(
        b0,
        (
            "`PipelineNodeResult`",
            "public projection fields",
            "trace or audit records",
            "frontend metadata",
            "visible response text",
            "caller-supplied dictionaries that merely resemble a typed artifact",
            "B2 consumes the exact B1 result",
            "B3 consumes an exact runtime-private transition request",
        ),
        "protected private artifacts",
    )
    _require_all(
        b0,
        (
            "dispatch_key_version",
            "candidate_schema_version",
            "candidate_kind",
            "trigger_mode",
            "processing_stage",
            "source_event_kind",
            "run_id",
            "turn_index",
            "session_id presence marker and value",
            "namespace",
            "source_count",
            "source_lineage_fingerprint",
        ),
        "dispatch identity inputs",
    )
    exclusions = _section(
        b0,
        "The derivation must not include:",
        "Operational status fields may change",
    )
    _require_all(
        exclusions,
        (
            "wall-clock timestamps",
            "random UUIDs",
            "queue paths",
            "record revision",
            "attempt count",
            "claim or lease metadata",
            "retry class or retry outcome",
            "memory-write idempotency keys",
            "raw content",
        ),
        "dispatch identity exclusions",
    )
    _require_all(
        b0,
        (
            "retry_class = unclassified",
            "failure_class = none",
            "attempt_count = 0",
            "claim_generation = 0",
            "create -> queued",
            "queued -> claimed",
            "claimed -> queued",
            "claimed -> succeeded",
            "claimed -> failed",
            "claimed -> cancelled",
            "No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.",
            "compare-and-swap semantics",
            "terminal-state immutability",
            "B3 does not generate `dead_letter`",
        ),
        "queue state contract",
    )
    _require_all(
        b0,
        (
            "enqueued_new",
            "duplicate_existing",
            "blocked_collision",
            "blocked_corrupt",
            "write_failed",
            "Same key plus different key-input fields is not a duplicate",
            "must not be silently repaired",
            "expired claimed records are not automatically executed",
            "same-inode byte mutation is a conflict",
        ),
        "enqueue and recovery contract",
    )
    _require_all(
        b0,
        (
            "Queue persistence or transition failure must not",
            "change the HTTP success already selected",
            "rewrite or append visible text",
            "delay stream completion while waiting for persistence",
            "create a synchronous memory-write fallback",
        ),
        "visible response independence",
    )
    projection = _section(b0, "## Public status projection", "## Visible-response independence")
    _require_all(
        projection,
        (
            "content-free",
            "job and dispatch identifiers",
            "claim owner and lease token",
            "memory-write idempotency keys",
            "raw content of any kind",
        ),
        "public projection exclusions",
    )

    _require_all(
        b1,
        (
            "Phase 6-B1 is implemented",
            "relaymem.slp_dispatch_preflight.v0",
            "relaymem.slp_durable_job.v0",
            "Phase 6-B2 consumes only an exact validated B1 result",
        ),
        "B1 handoff",
    )
    _require_all(
        b2,
        (
            "Phase 6-B2 is implemented",
            "atomic create-if-absent publication",
            "enqueued_new",
            "duplicate_existing",
            "blocked_collision",
            "blocked_corrupt",
            "write_failed",
            "Phase 6-B3 is implemented",
        ),
        "B2 handoff",
    )
    _require_all(
        b3,
        (
            "Phase 6-B3 is implemented",
            "claim\nrenew_lease\nretry_release\nstale_recovery\ncommit_terminal",
            "record_revision == 3",
            "attempt_count == 2",
            "claim_generation == 2",
            "B3 never generates `dead_letter`",
            "Phase 6-C worker execution",
        ),
        "B3 handoff",
    )
    _require_all(
        current,
        (
            "Phase 6-B1 implements the first exact consumer",
            "Phase 6-B2 implements atomic durable enqueue",
            "Phase 6-B3 implements default-off, dry-run-first fenced",
            "The next bounded RelayLM Core implementation is Phase 6-C worker execution",
        ),
        "current target",
    )
    _require_all(
        plan,
        (
            "Phase 6-B1: job-record and dispatch-idempotency preflight — complete",
            "Phase 6-B2 atomic durable enqueue: complete",
            "Phase 6-B3 queue lifecycle: complete",
            "The next RelayLM Core boundary is Phase 6-C worker execution",
        ),
        "pipeline plan",
    )
    _require_all(
        status,
        (
            "Asynchronous RelaySLP orchestration: queue lifecycle helpers complete through Phase 6-B3",
            "Phase 6-B1 RelaySLP dispatch preflight",
            "Phase 6-B2 atomic durable enqueue",
            "Phase 6-B3 fenced queue state transitions",
            "Phase 6-C worker execution",
        ),
        "project status",
    )
    for name in (
        "phase6b0_relayslp_durable_queue_contract.md",
        "phase6b1_relayslp_dispatch_preflight.md",
        "phase6b2_relayslp_atomic_durable_enqueue.md",
        "phase6b3_relayslp_queue_state_helpers.md",
    ):
        assert name in index, f"architecture index missing {name}"

    _require_all(
        a2_helper,
        (
            '_CANDIDATE_SCHEMA = "relaymem.slp_enqueue_candidate.v0"',
            '"dispatch_idempotency_key": ""',
            '"memory_write_idempotency_key": ""',
            '"runtime_private": True',
        ),
        "A2 compatibility",
    )
    _require_all(
        b1_helper,
        (
            '_RESULT_SCHEMA = "relaymem.slp_dispatch_preflight.v0"',
            '_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"',
            "exact_a2_handoff_result_required",
            "_validate_source_candidate_consistency",
            '"queue_io_performed": False',
        ),
        "B1 compatibility",
    )
    _require_all(
        b3_helper,
        (
            '_REQUEST_SCHEMA = "relaymem.slp_queue_transition_request.v0"',
            '_RESULT_SCHEMA = "relaymem.slp_queue_state_transition.v0"',
            "exact_transition_request_required",
            "record_revision_mismatch",
            "claim_owner_mismatch",
            "claim_generation_mismatch",
            "lease_token_mismatch",
            "terminal_state_immutable",
            'node_name="relaymem_slp_queue_state"',
            '"worker_invoked": False',
            '"writes_memory": False',
            '"mutates_soul": False',
            '"changes_visible_response": False',
        ),
        "B3 compatibility",
    )
    _require_all(
        b1_workflow,
        (
            "relaylm/relaymem_slp_dispatch_preflight.py",
            "scripts/relaylm_phase6b1_dispatch_preflight_smoke.py",
            "scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
        ),
        "B1 workflow",
    )
    _require_all(
        b3_workflow,
        (
            "relaylm/relaymem_slp_queue_state.py",
            "scripts/relaylm_phase6b3_queue_state_smoke.py",
            "scripts/relaylm_phase6b3_queue_state_security_smoke.py",
            "scripts/relaylm_phase6b3_queue_state_contract_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
        ),
        "B3 workflow",
    )

    print("Phase 6-B durable RelaySLP queue contract smoke passed through B3")


if __name__ == "__main__":
    main()
