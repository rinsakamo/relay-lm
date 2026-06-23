"""Validate Phase 6-B2 invariants without freezing an obsolete project phase."""
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
    b2_doc = read("docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md")
    current = read("docs/architecture/relaymem_slp_current_target.md")
    plan = read("docs/architecture/pipeline_implementation_plan.md")
    status = read("docs/PROJECT_STATUS.md")
    index = read("docs/architecture/README.md")
    helper = read("relaylm/relaymem_slp_durable_enqueue.py")
    functional = read("scripts/relaylm_phase6b2_durable_enqueue_smoke.py")
    security = read("scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py")

    require(
        b2_doc,
        "Phase 6-B2 is implemented",
        "atomic create-if-absent publication",
        "enqueued_new",
        "duplicate_existing",
        "blocked_collision",
        "blocked_corrupt",
        "write_failed",
        "Phase 6-B3 is implemented",
    )
    require(
        current,
        "Phase 6-B2 performs atomic durable enqueue",
        "Phase 6-B3 performs default-off, dry-run-first",
        "one-job claim/rehydrate/execute adapter",
    )
    require(
        plan,
        "B2 atomic durable enqueue: complete",
        "B3 queue lifecycle helpers: complete",
        "Phase 6-C1-0 through C1-5 are complete",
    )
    require(
        status,
        "Phase 6-B2 atomic durable enqueue",
        "C1-5 durable protected source persistence",
        "B3 claim -> C1-5 rehydrate -> C1-2 execute",
    )
    require(index, "phase6b2_relayslp_atomic_durable_enqueue.md", "phase6c1_durable_protected_source_persistence.md")
    require(
        helper,
        "relaymem.slp_durable_enqueue.v0",
        "relaymem.slp_durable_job.v0",
        "exact_b1_preflight_result_required",
        "queue_record_duplicate_json_key",
        "dispatch_identity_collision",
    )
    require(functional, "dry_run_ready", "enqueued_new", "duplicate_existing")
    require(security, "queue_root_symlink_blocked", "queue_record_noncanonical_json")

    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
