from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_approval import build_relaysoul_approval_summary


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _patch(dry_run_status: str = "ok", *, cid: str = "cand-1", mode: str = "calibration", targets: list[str] | None = None):
    return {
        "dry_run_status": dry_run_status,
        "candidate": {
            "candidate_id": cid,
            "mode": mode,
            "target_files": ["OUTPUT_POLICY.md"] if targets is None else targets,
        },
    }


def _rollback(rollback_status: str = "ok", *, rid: str = "rev-1", cid: str = "cand-1", mode: str = "calibration", changed: list[str] | None = None, stable_prefix_changed: bool = False):
    return {
        "rollback_status": rollback_status,
        "stable_prefix_changed": stable_prefix_changed,
        "revision": {
            "revision_id": rid,
            "patch_candidate_id": cid,
            "mode": mode,
            "changed_files": ["OUTPUT_POLICY.md"] if changed is None else changed,
        },
    }


def main() -> int:
    ok = build_relaysoul_approval_summary(_patch(), _rollback()).to_log_dict()
    require(ok["approval_status"] == "ok", ok)
    print("ok matching artifacts approved")

    p_block = build_relaysoul_approval_summary(_patch("blocked"), _rollback()).to_log_dict()
    require("patch_dry_run_blocked" in p_block["blocking_reasons"], p_block)
    print("ok patch blocked propagates")

    r_block = build_relaysoul_approval_summary(_patch(), _rollback("blocked")).to_log_dict()
    require("rollback_summary_blocked" in r_block["blocking_reasons"], r_block)
    print("ok rollback blocked propagates")

    p_warn = build_relaysoul_approval_summary(_patch("warning"), _rollback()).to_log_dict()
    require("patch_dry_run_warning" in p_warn["warning_reasons"], p_warn)
    print("ok patch warning propagates")

    r_warn = build_relaysoul_approval_summary(_patch(), _rollback("warning")).to_log_dict()
    require("rollback_summary_warning" in r_warn["warning_reasons"], r_warn)
    print("ok rollback warning propagates")

    cid_mismatch = build_relaysoul_approval_summary(_patch(cid="cand-a"), _rollback(cid="cand-b")).to_log_dict()
    require("patch_candidate_id_mismatch" in cid_mismatch["blocking_reasons"], cid_mismatch)
    print("ok candidate id mismatch blocked")

    mode_mismatch = build_relaysoul_approval_summary(_patch(mode="calibration"), _rollback(mode="normal_chat")).to_log_dict()
    require("mode_mismatch" in mode_mismatch["blocking_reasons"], mode_mismatch)
    print("ok mode mismatch blocked")

    file_mismatch = build_relaysoul_approval_summary(
        _patch(targets=["OUTPUT_POLICY.md"]),
        _rollback(changed=["RELATIONSHIP_ANCHOR.md"]),
    ).to_log_dict()
    require("target_changed_file_mismatch" in file_mismatch["blocking_reasons"], file_mismatch)
    print("ok target/changed mismatch blocked")

    prefix_warn = build_relaysoul_approval_summary(_patch(), _rollback(stable_prefix_changed=True)).to_log_dict()
    require("stable_prefix_changed" in prefix_warn["warning_reasons"], prefix_warn)
    print("ok stable prefix change warning")

    missing_patch = build_relaysoul_approval_summary(None, _rollback()).to_log_dict()
    require("missing_patch_dry_run" in missing_patch["blocking_reasons"], missing_patch)
    missing_rollback = build_relaysoul_approval_summary(_patch(), None).to_log_dict()
    require("missing_rollback_summary" in missing_rollback["blocking_reasons"], missing_rollback)
    print("ok missing artifacts blocked")

    one_sided_changed_only = build_relaysoul_approval_summary(
        _patch(targets=[]),
        _rollback(changed=["OUTPUT_POLICY.md"]),
    ).to_log_dict()
    require("target_changed_file_mismatch" in one_sided_changed_only["blocking_reasons"], one_sided_changed_only)

    one_sided_target_only = build_relaysoul_approval_summary(
        _patch(targets=["OUTPUT_POLICY.md"]),
        _rollback(changed=[]),
    ).to_log_dict()
    require("target_changed_file_mismatch" in one_sided_target_only["blocking_reasons"], one_sided_target_only)
    print("ok one-sided file lists blocked as mismatch")

    require("patch_text" not in str(ok), ok)
    print("ok content-free artifact")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
