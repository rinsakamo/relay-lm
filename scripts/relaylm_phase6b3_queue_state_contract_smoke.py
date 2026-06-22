"""Contract integration smoke for Phase 6-B3 fenced queue state helpers."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE6 = ROOT / "docs/architecture/phase6_async_relayslp_bounded_slice.md"
B0 = ROOT / "docs/architecture/phase6b0_relayslp_durable_queue_contract.md"
B2 = ROOT / "docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md"
B3 = ROOT / "docs/architecture/phase6b3_relayslp_queue_state_helpers.md"
CURRENT_TARGET = ROOT / "docs/architecture/relaymem_slp_current_target.md"
PIPELINE_PLAN = ROOT / "docs/architecture/pipeline_implementation_plan.md"
PROJECT_STATUS = ROOT / "docs/PROJECT_STATUS.md"
ARCHITECTURE_INDEX = ROOT / "docs/architecture/README.md"
DOC_INDEX = ROOT / "docs/README.md"
HELPER = ROOT / "relaylm/relaymem_slp_queue_state.py"
RECORD_HELPER = ROOT / "relaylm/relaymem_slp_queue_record.py"
STORAGE_HELPER = ROOT / "relaylm/relaymem_slp_queue_storage.py"
FUNCTIONAL = ROOT / "scripts/relaylm_phase6b3_queue_state_smoke.py"
SECURITY = ROOT / "scripts/relaylm_phase6b3_queue_state_security_smoke.py"
WORKFLOW = ROOT / ".github/workflows/relaymem-slp-queue-state-smoke.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _require_all(text: str, values: tuple[str, ...], *, label: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, f"{label} missing required values: {missing}"


def main() -> None:
    phase6 = _read(PHASE6)
    b0 = _read(B0)
    b2 = _read(B2)
    b3 = _read(B3)
    current_target = _read(CURRENT_TARGET)
    pipeline_plan = _read(PIPELINE_PLAN)
    project_status = _read(PROJECT_STATUS)
    architecture_index = _read(ARCHITECTURE_INDEX)
    doc_index = _read(DOC_INDEX)
    helper = _read(HELPER)
    helper_sources = helper + _read(RECORD_HELPER) + _read(STORAGE_HELPER)
    functional = _read(FUNCTIONAL)
    security = _read(SECURITY)
    workflow = _read(WORKFLOW)

    _require_all(
        b3,
        (
            "relaylm_authority: phase6b3_relayslp_queue_state_helpers",
            "Phase 6-B3 is implemented",
            "claim\nrenew_lease\nretry_release\nstale_recovery\ncommit_terminal",
            "relaymem.slp_queue_transition_request.v0",
            "relaymem.slp_queue_state_transition.v0",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "enabled = true",
            "dry_run_only = false",
            "apply_enabled = true",
            "record_revision == 3",
            "attempt_count == 2",
            "claim_generation == 2",
            "B3 never generates `dead_letter`",
            "same-inode byte mutation is a conflict",
            "Phase 6-C worker execution",
        ),
        label="B3 implementation handoff",
    )
    _require_all(
        phase6,
        (
            "Phase 6-B3 claim/renew/retry/stale/terminal lifecycle: complete as direct helper",
            "Next boundary: Phase 6-C worker execution",
            "B3 does not generate `dead_letter`",
        ),
        label="Phase 6 slice alignment",
    )
    _require_all(
        b0,
        (
            "Phase 6-B3",
            "claim, lease, retry-release, stale-recovery, and terminal-state helpers",
            "Phase 6-C worker execution",
            "terminal-state immutability",
        ),
        label="B0/B3 alignment",
    )
    _require_all(
        b2,
        (
            "Phase 6-B2 is implemented",
            "atomic create-if-absent publication",
            "Phase 6-B3 is implemented",
            "Phase 6-C",
        ),
        label="B2/B3 alignment",
    )
    _require_all(
        current_target,
        (
            "Phase 6-B3",
            "fenced durable queue lifecycle helpers",
            "The next bounded RelayLM Core implementation is Phase 6-C",
        ),
        label="current-target alignment",
    )
    _require_all(
        pipeline_plan,
        (
            "B3 queue lifecycle helpers: complete as direct helper",
            "Phase 6-B3 queue lifecycle: complete",
            "The next RelayLM Core boundary is Phase 6-C worker execution",
        ),
        label="pipeline-plan alignment",
    )
    _require_all(
        project_status,
        (
            "Asynchronous RelaySLP orchestration: queue lifecycle helpers complete through Phase 6-B3",
            "Phase 6-B3 fenced queue state transitions",
            "Phase 6-C worker execution",
        ),
        label="project-status alignment",
    )
    for index in (architecture_index, doc_index):
        assert "phase6b3_relayslp_queue_state_helpers.md" in index

    _require_all(
        helper_sources,
        (
            '_REQUEST_SCHEMA = "relaymem.slp_queue_transition_request.v0"',
            '_RESULT_SCHEMA = "relaymem.slp_queue_state_transition.v0"',
            '"claim", "renew_lease", "retry_release", "stale_recovery", "commit_terminal"',
            "class RelayMEMSLPQueueTransitionRequest",
            "class RelayMEMSLPQueueStateTransitionResult",
            "exact_transition_request_required",
            "job_dispatch_identity_mismatch",
            "record_revision_mismatch",
            "record_state_mismatch",
            "claim_owner_mismatch",
            "claim_generation_mismatch",
            "lease_token_mismatch",
            "retry_not_before_pending",
            "stale_lease_not_expired",
            "terminal_state_immutable",
            "queue_record_hardlink_count_invalid",
            "queue_record_duplicate_json_key",
            "queue_record_noncanonical_json",
            "queue_lock_busy",
            "queue_record_bytes_changed",
            "os.O_EXCL",
            "os.fsync",
            "os.replace",
            'node_name="relaymem_slp_queue_state"',
            '"worker_invoked": False',
            '"invokes_slp": False',
            '"writes_memory": False',
            '"mutates_soul": False',
            '"changes_visible_response": False',
        ),
        label="B3 helper",
    )
    assert 'request.terminal_state not in {"succeeded", "failed", "cancelled"}' in helper
    assert '"state": "dead_letter"' not in helper_sources

    _require_all(
        functional,
        (
            "disabled.status == \"disabled\"",
            "dry_run.status == \"dry_run_ready\"",
            '"renew_lease"',
            '"retry_release"',
            '"stale_recovery"',
            '"commit_terminal"',
            'reclaimed["record_revision"] == 3',
            'reclaimed["attempt_count"] == 2',
            'reclaimed["claim_generation"] == 2',
            "terminal_state_immutable",
            "build_relaymem_slp_queue_state_node_result",
        ),
        label="B3 functional smoke",
    )
    _require_all(
        security,
        (
            "job_dispatch_identity_mismatch",
            "queue_record_malformed_json",
            "queue_record_duplicate_json_key",
            "queue_record_noncanonical_json",
            "durable_job_shape_mismatch",
            "queue_root_symlink_blocked",
            "queue_root_not_directory",
            "queue_record_symlink_blocked",
            "queue_record_unexpected_file_type",
            "queue_record_hardlink_count_invalid",
            "queue_record_size_exceeded",
            "record_revision_mismatch",
            "record_state_mismatch",
            "claim_owner_mismatch",
            "claim_generation_mismatch",
            "lease_token_mismatch",
            "retry_not_before",
            "lease_timestamp_overflow",
            "queue_record_bytes_changed",
            "queue_lock_busy",
            "terminal_state_immutable",
        ),
        label="B3 security smoke",
    )
    _require_all(
        workflow,
        (
            "relaylm/relaymem_slp_queue_state.py",
            "scripts/relaylm_phase6b0_durable_queue_contract_smoke.py",
            "scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py",
            "scripts/relaylm_phase6b3_queue_state_smoke.py",
            "scripts/relaylm_phase6b3_queue_state_security_smoke.py",
            "scripts/relaylm_phase6b3_queue_state_contract_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
            "relaylm_docs_link_check.py",
        ),
        label="B3 workflow",
    )

    forbidden_boundaries = (
        "worker execution or worker heartbeats",
        "RelaySLP invocation",
        "Primary or Secondary MEM apply",
        "RelaySOUL mutation",
        "visible-response dependency or mutation",
    )
    _require_all(b3, forbidden_boundaries, label="B3 non-goals")

    print("Phase 6-B3 queue state contract smoke: ok")


if __name__ == "__main__":
    main()
