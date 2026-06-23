"""Validate Phase 6-B3 queue ownership without freezing an obsolete next phase."""
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
    b3_doc = read("docs/architecture/phase6b3_relayslp_queue_state_helpers.md")
    current = read("docs/architecture/relaymem_slp_current_target.md")
    plan = read("docs/architecture/pipeline_implementation_plan.md")
    status = read("docs/PROJECT_STATUS.md")
    helper = read("relaylm/relaymem_slp_queue_state.py")
    record = read("relaylm/relaymem_slp_queue_record.py")
    storage = read("relaylm/relaymem_slp_queue_storage.py")
    functional = read("scripts/relaylm_phase6b3_queue_state_smoke.py")
    security = read("scripts/relaylm_phase6b3_queue_state_security_smoke.py")

    require(
        b3_doc,
        "Phase 6-B3 is implemented",
        "claim\nrenew_lease\nretry_release\nstale_recovery\ncommit_terminal",
        "relaymem.slp_queue_transition_request.v0",
        "relaymem.slp_queue_state_transition.v0",
        "B3 never generates `dead_letter`",
        "same-inode byte mutation is a conflict",
    )
    require(
        current,
        "Phase 6-B3 performs default-off, dry-run-first",
        "It owns queue metadata only and never executes a worker",
        "one-job claim/rehydrate/execute adapter",
    )
    require(
        plan,
        "B3 queue lifecycle helpers: complete",
        "Phase 6-C1-0 through C1-5 are complete",
        "thin one-job claim/rehydrate/execute integration adapter",
    )
    require(
        status,
        "Phase 6-B3 fenced claim, renew, retry release, stale recovery, and terminal commit",
        "B3 claim -> C1-5 rehydrate -> C1-2 execute",
    )

    helper_sources = helper + record + storage
    require(
        helper_sources,
        "relaymem.slp_queue_transition_request.v0",
        "relaymem.slp_queue_state_transition.v0",
        "record_revision_mismatch",
        "claim_owner_mismatch",
        "claim_generation_mismatch",
        "lease_token_mismatch",
        "terminal_state_immutable",
        "queue_record_duplicate_json_key",
        "queue_record_noncanonical_json",
        "queue_record_bytes_changed",
    )
    require(functional, "renew_lease", "retry_release", "stale_recovery", "commit_terminal")
    require(security, "queue_root_symlink_blocked", "queue_lock_busy", "terminal_state_immutable")

    print("Phase 6-B3 queue state contract smoke: ok")


if __name__ == "__main__":
    main()
