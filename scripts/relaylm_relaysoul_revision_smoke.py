from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_revision import RelaySOULPersonaRevision, build_relaysoul_rollback_summary


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    ok_revision = RelaySOULPersonaRevision(
        revision_id="rev-1",
        parent_revision_id="rev-0",
        mode="calibration",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=["f1"],
        patch_candidate_id="cand-1",
        patch_dry_run_status="ok",
        stable_prefix_hash_before="abc",
        stable_prefix_hash_after="abc",
        compile_dry_run_status="ok",
        applied_by="operator",
        rollback_available=True,
    )
    ok = build_relaysoul_rollback_summary(ok_revision).to_log_dict()
    require(ok["rollback_status"] == "ok", ok)
    print("ok calibration rollback summary")

    missing_parent = RelaySOULPersonaRevision(
        revision_id="rev-2",
        parent_revision_id=None,
        mode="calibration",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before="abc",
        stable_prefix_hash_after="abc",
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=True,
    )
    warn_parent = build_relaysoul_rollback_summary(missing_parent).to_log_dict()
    require("missing_parent_revision" in warn_parent["warning_reasons"], warn_parent)
    print("ok missing parent warns")

    changed_prefix = RelaySOULPersonaRevision(
        revision_id="rev-3",
        parent_revision_id="rev-2",
        mode="calibration",
        changed_files=["RELATIONSHIP_ANCHOR.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before="a",
        stable_prefix_hash_after="b",
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=True,
    )
    warn_prefix = build_relaysoul_rollback_summary(changed_prefix).to_log_dict()
    require("stable_prefix_changed" in warn_prefix["warning_reasons"], warn_prefix)
    print("ok stable prefix change warns")

    rollback_unavailable = RelaySOULPersonaRevision(
        revision_id="rev-4",
        parent_revision_id="rev-3",
        mode="calibration",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before=None,
        stable_prefix_hash_after=None,
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=False,
    )
    blocked_rb = build_relaysoul_rollback_summary(rollback_unavailable).to_log_dict()
    require("rollback_unavailable" in blocked_rb["blocking_reasons"], blocked_rb)
    print("ok rollback unavailable blocked")

    unsupported_file = RelaySOULPersonaRevision(
        revision_id="rev-5",
        parent_revision_id="rev-4",
        mode="calibration",
        changed_files=["UNKNOWN.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before=None,
        stable_prefix_hash_after=None,
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=True,
    )
    blocked_file = build_relaysoul_rollback_summary(unsupported_file).to_log_dict()
    require("unsupported_changed_file" in blocked_file["blocking_reasons"], blocked_file)
    print("ok unsupported changed file blocked")

    unsupported_mode = RelaySOULPersonaRevision(
        revision_id="rev-6",
        parent_revision_id="rev-5",
        mode="review",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before=None,
        stable_prefix_hash_after=None,
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=True,
    )
    blocked_mode = build_relaysoul_rollback_summary(unsupported_mode).to_log_dict()
    require("unsupported_mode" in blocked_mode["blocking_reasons"], blocked_mode)
    print("ok unsupported mode blocked")

    patch_blocked = RelaySOULPersonaRevision(
        revision_id="rev-7",
        parent_revision_id="rev-6",
        mode="calibration",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        patch_candidate_id="cand-7",
        patch_dry_run_status="blocked",
        stable_prefix_hash_before=None,
        stable_prefix_hash_after=None,
        compile_dry_run_status="ok",
        applied_by=None,
        rollback_available=True,
    )
    blocked_patch = build_relaysoul_rollback_summary(patch_blocked).to_log_dict()
    require("patch_dry_run_blocked" in blocked_patch["blocking_reasons"], blocked_patch)
    print("ok blocked patch status blocked")

    compile_warn = RelaySOULPersonaRevision(
        revision_id="rev-8",
        parent_revision_id="rev-7",
        mode="calibration",
        changed_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        patch_candidate_id=None,
        patch_dry_run_status="ok",
        stable_prefix_hash_before=None,
        stable_prefix_hash_after=None,
        compile_dry_run_status="warning",
        applied_by=None,
        rollback_available=True,
    )
    warn_compile = build_relaysoul_rollback_summary(compile_warn).to_log_dict()
    require("compile_dry_run_not_ok" in warn_compile["warning_reasons"], warn_compile)
    require("patch_text" not in str(warn_compile), warn_compile)
    print("ok compile status warning captured content-free")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
