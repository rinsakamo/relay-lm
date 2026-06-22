"""Contract integration smoke for the current Phase 6-B2 durable enqueue boundary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B0 = ROOT / "docs/architecture/phase6b0_relayslp_durable_queue_contract.md"
B1 = ROOT / "docs/architecture/phase6b1_relayslp_dispatch_preflight.md"
B2 = ROOT / "docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md"
B3 = ROOT / "docs/architecture/phase6b3_relayslp_queue_state_helpers.md"
CURRENT_TARGET = ROOT / "docs/architecture/relaymem_slp_current_target.md"
PIPELINE_PLAN = ROOT / "docs/architecture/pipeline_implementation_plan.md"
PROJECT_STATUS = ROOT / "docs/PROJECT_STATUS.md"
ARCHITECTURE_INDEX = ROOT / "docs/architecture/README.md"
HELPER = ROOT / "relaylm/relaymem_slp_durable_enqueue.py"
FUNCTIONAL = ROOT / "scripts/relaylm_phase6b2_durable_enqueue_smoke.py"
SECURITY = ROOT / "scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py"
WORKFLOW = ROOT / ".github/workflows/relaymem-slp-durable-enqueue-smoke.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _require_all(text: str, values: tuple[str, ...], *, label: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, f"{label} missing required values: {missing}"


def main() -> None:
    b0 = _read(B0)
    b1 = _read(B1)
    b2 = _read(B2)
    b3 = _read(B3)
    current_target = _read(CURRENT_TARGET)
    pipeline_plan = _read(PIPELINE_PLAN)
    project_status = _read(PROJECT_STATUS)
    architecture_index = _read(ARCHITECTURE_INDEX)
    helper = _read(HELPER)
    functional = _read(FUNCTIONAL)
    security = _read(SECURITY)
    workflow = _read(WORKFLOW)

    _require_all(
        b2,
        (
            "relaylm_authority: phase6b2_relayslp_atomic_durable_enqueue",
            "Phase 6-B2 is implemented",
            "exact runtime-private B1 result",
            "atomic create-if-absent publication",
            "enqueued_new",
            "duplicate_existing",
            "blocked_collision",
            "blocked_corrupt",
            "write_failed",
            "malformed UTF-8",
            "schema drift",
            "memory-write idempotency key is never accepted as queue identity",
            "Phase 6-B3 is implemented",
        ),
        label="B2 handoff",
    )
    _require_all(
        b0,
        (
            "Phase 6-B2",
            "atomic create-if-absent",
            "Phase 6-B3",
            "claim/lease",
        ),
        label="B0/B2 alignment",
    )
    _require_all(
        b1,
        (
            "Phase 6-B1 is implemented",
            "Phase 6-B2",
            "exact validated B1 result",
        ),
        label="B1/B2 alignment",
    )
    _require_all(
        b3,
        (
            "complete canonical Phase 6-B2 durable records",
            "deterministic dispatch-digest filename",
            "Phase 6-C worker execution",
        ),
        label="B2/B3 alignment",
    )
    _require_all(
        current_target,
        (
            "Phase 6-B2",
            "atomic durable enqueue",
            "Phase 6-B3",
            "Phase 6-C worker execution",
        ),
        label="current-target alignment",
    )
    _require_all(
        pipeline_plan,
        (
            "Phase 6-B2 atomic durable enqueue",
            "complete",
            "Phase 6-B3 queue lifecycle",
            "Phase 6-C worker execution",
        ),
        label="pipeline-plan alignment",
    )
    _require_all(
        project_status,
        (
            "Asynchronous RelaySLP orchestration",
            "Phase 6-B2",
            "Phase 6-B3",
            "Phase 6-C worker execution",
        ),
        label="project-status alignment",
    )
    assert "phase6b2_relayslp_atomic_durable_enqueue.md" in architecture_index
    assert "phase6b3_relayslp_queue_state_helpers.md" in architecture_index

    _require_all(
        helper,
        (
            '_RESULT_SCHEMA = "relaymem.slp_durable_enqueue.v0"',
            '_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"',
            '_PROJECTION_SCHEMA = "relaymem.slp_queue_status_projection.v0"',
            "exact_b1_preflight_result_required",
            "exact_b1_durable_job_candidate_required",
            "_derive_dispatch_key",
            "os.O_EXCL",
            'getattr(os, "O_NOFOLLOW", 0)',
            "os.link",
            "os.fsync",
            "queue_record_malformed_utf8",
            "queue_record_duplicate_json_key",
            "dispatch_identity_collision",
            "queue_record_unexpected_file_type",
            'node_name="relaymem_slp_durable_enqueue"',
            '"worker_invoked": False',
            '"writes_memory": False',
            '"mutates_soul": False',
            '"changes_visible_response": False',
        ),
        label="B2 helper",
    )
    _require_all(
        functional,
        (
            "dry_run_ready",
            "enqueued_new",
            "duplicate_existing",
            "operational_duplicate",
            "queue_path_included",
        ),
        label="B2 functional smoke",
    )
    _require_all(
        security,
        (
            "queue_root_symlink_blocked",
            "queue_record_symlink_blocked",
            "queue_record_unexpected_file_type",
            "queue_record_malformed_utf8",
            "queue_record_duplicate_json_key",
            "durable_job_shape_mismatch",
            "dispatch_identity_collision",
            "queue_record_noncanonical_json",
            "durable_job_timestamp_invalid",
            "queue_record_key_path_mismatch",
        ),
        label="B2 security smoke",
    )
    _require_all(
        workflow,
        (
            "relaylm/relaymem_slp_durable_enqueue.py",
            "scripts/relaylm_phase6b2_durable_enqueue_smoke.py",
            "scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py",
            "scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
        ),
        label="B2 workflow",
    )

    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
