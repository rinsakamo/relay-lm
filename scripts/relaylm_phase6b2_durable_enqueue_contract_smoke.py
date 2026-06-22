"""Contract integration smoke for B2 durable enqueue after the B3 handoff."""
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
    b2 = _read("docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md")
    b3 = _read("docs/architecture/phase6b3_relayslp_queue_state_helpers.md")
    helper = _read("relaylm/relaymem_slp_durable_enqueue.py")
    functional = _read("scripts/relaylm_phase6b2_durable_enqueue_smoke.py")
    security = _read("scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py")
    workflow = _read(".github/workflows/relaymem-slp-durable-enqueue-smoke.yml")

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
            "memory-write idempotency key is never accepted as queue identity",
            "Phase 6-B3 is implemented",
        ),
        "B2 handoff",
    )
    _require_all(b0, ("Phase 6-B2", "Phase 6-B3: implemented"), "B0/B2")
    _require_all(
        b3,
        (
            "complete canonical Phase 6-B2 durable records",
            "deterministic dispatch-digest filename",
            "Phase 6-C worker execution",
        ),
        "B2/B3 handoff",
    )
    _require_all(
        helper,
        (
            '_RESULT_SCHEMA = "relaymem.slp_durable_enqueue.v0"',
            '_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"',
            "exact_b1_preflight_result_required",
            "_derive_dispatch_key",
            "os.O_EXCL",
            "os.link",
            "os.fsync",
            "queue_record_duplicate_json_key",
            "dispatch_identity_collision",
            '"worker_invoked": False',
            '"writes_memory": False',
            '"mutates_soul": False',
            '"changes_visible_response": False',
        ),
        "B2 helper",
    )
    _require_all(functional, ("dry_run_ready", "enqueued_new", "duplicate_existing"), "B2 functional")
    _require_all(
        security,
        (
            "queue_root_symlink_blocked",
            "queue_record_symlink_blocked",
            "queue_record_malformed_utf8",
            "queue_record_duplicate_json_key",
            "dispatch_identity_collision",
            "queue_record_noncanonical_json",
        ),
        "B2 security",
    )
    _require_all(
        workflow,
        (
            "relaylm/relaymem_slp_durable_enqueue.py",
            "scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
        ),
        "B2 workflow",
    )

    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
