from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_persistence import (
    build_relaysoul_artifact_persistence_dry_run,
    build_relaysoul_storage_envelope_dry_run,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    patch_ok = {
        "dry_run_status": "ok",
        "content_free": True,
        "candidate": {"candidate_id": "cand-1"},
    }
    out = build_relaysoul_artifact_persistence_dry_run("patch_dry_run", patch_ok).to_log_dict()
    require(out["persistence_status"] == "ok" and out["artifact_id"] == "cand-1", out)
    print("ok patch artifact persistence")

    rollback_ok = {
        "rollback_status": "ok",
        "content_free": True,
        "revision": {"revision_id": "rev-1", "parent_revision_id": "rev-0"},
    }
    out = build_relaysoul_artifact_persistence_dry_run("rollback_summary", rollback_ok).to_log_dict()
    require(out["persistence_status"] == "ok" and out["artifact_id"] == "rev-1" and out["parent_artifact_id"] == "rev-0", out)
    print("ok rollback artifact persistence")

    approval_ok = {"approval_status": "ok", "content_free": True, "revision_id": "rev-1", "patch_candidate_id": "cand-1"}
    out = build_relaysoul_artifact_persistence_dry_run("approval_summary", approval_ok).to_log_dict()
    require(out["persistence_status"] == "ok" and out["artifact_id"] == "rev-1", out)

    approval_fallback = {"approval_status": "ok", "content_free": True, "patch_candidate_id": "cand-2"}
    out = build_relaysoul_artifact_persistence_dry_run("approval_summary", approval_fallback).to_log_dict()
    require(out["artifact_id"] == "cand-2", out)
    print("ok approval artifact id extraction")

    approval_missing_parent = {"approval_status": "ok", "content_free": True, "revision_id": "rev-1"}
    out = build_relaysoul_artifact_persistence_dry_run("approval_summary", approval_missing_parent).to_log_dict()
    require(out["persistence_status"] == "warning" and out["persistence_ready"] is True and "missing_parent_artifact_id" in out["warning_reasons"], out)

    approval_empty_parent = {"approval_status": "ok", "content_free": True, "revision_id": "rev-1", "patch_candidate_id": ""}
    out = build_relaysoul_artifact_persistence_dry_run("approval_summary", approval_empty_parent).to_log_dict()
    require(out["persistence_status"] == "warning" and out["persistence_ready"] is True and "missing_parent_artifact_id" in out["warning_reasons"], out)
    print("ok approval parent lineage warning")

    compile_ok = {
        "compile_dry_run_status": "ok",
        "content_free": True,
        "patch_candidate_id": "cand-compile-1",
    }
    out = build_relaysoul_artifact_persistence_dry_run("patch_compile_dry_run", compile_ok).to_log_dict()
    require(out["persistence_status"] == "ok", out)
    require(out["artifact_id"] == "cand-compile-1", out)
    require(out["parent_artifact_id"] == "cand-compile-1", out)
    require(out["persistence_ready"] is True, out)

    compile_warning = {
        "compile_dry_run_status": "warning",
        "content_free": True,
        "patch_candidate_id": "cand-compile-2",
    }
    out = build_relaysoul_artifact_persistence_dry_run("patch_compile_dry_run", compile_warning).to_log_dict()
    require("artifact_status_warning" in out["warning_reasons"], out)
    require(out["persistence_ready"] is True, out)

    compile_blocked = {
        "compile_dry_run_status": "blocked",
        "content_free": True,
        "patch_candidate_id": "cand-compile-3",
    }
    out = build_relaysoul_artifact_persistence_dry_run("patch_compile_dry_run", compile_blocked).to_log_dict()
    require("artifact_status_blocked" in out["warning_reasons"], out)
    require(out["persistence_ready"] is True, out)

    compile_missing_id = {
        "compile_dry_run_status": "ok",
        "content_free": True,
        "patch_candidate_id": "",
    }
    out = build_relaysoul_artifact_persistence_dry_run("patch_compile_dry_run", compile_missing_id).to_log_dict()
    require("missing_artifact_id" in out["blocking_reasons"], out)
    require("missing_parent_artifact_id" in out["warning_reasons"], out)
    require(out["persistence_status"] == "blocked", out)
    print("ok patch compile persistence linkage")

    approval_package_ok = {
        "approval_status": "pending_user_approval",
        "content_free": True,
        "approval_package_id": "apkg-1",
        "revision_id": "rev-1",
    }
    out = build_relaysoul_artifact_persistence_dry_run("approval_package", approval_package_ok).to_log_dict()
    require(out["persistence_status"] == "ok" and out["artifact_id"] == "apkg-1" and out["parent_artifact_id"] == "rev-1", out)
    print("ok approval package persistence")

    approval_package_missing_id = {
        "approval_status": "pending_user_approval",
        "content_free": True,
        "revision_id": "rev-1",
    }
    out = build_relaysoul_artifact_persistence_dry_run("approval_package", approval_package_missing_id).to_log_dict()
    require("missing_artifact_id" in out["blocking_reasons"], out)

    approval_package_missing_parent = {
        "approval_status": "pending_user_approval",
        "content_free": True,
        "approval_package_id": "apkg-2",
    }
    out = build_relaysoul_artifact_persistence_dry_run("approval_package", approval_package_missing_parent).to_log_dict()
    require(out["persistence_status"] == "warning" and "missing_parent_artifact_id" in out["warning_reasons"], out)
    print("ok approval package lineage warnings")

    out = build_relaysoul_artifact_persistence_dry_run("unknown", patch_ok).to_log_dict()
    require("unsupported_artifact_kind" in out["blocking_reasons"], out)

    out = build_relaysoul_artifact_persistence_dry_run("patch_dry_run", None).to_log_dict()
    require("missing_artifact" in out["blocking_reasons"], out)

    out = build_relaysoul_artifact_persistence_dry_run("patch_dry_run", {"dry_run_status": "ok", "candidate": {"candidate_id": "cand-1"}}).to_log_dict()
    require("artifact_not_content_free" in out["blocking_reasons"], out)

    blocked_patch = {"dry_run_status": "blocked", "content_free": True, "candidate": {"candidate_id": "cand-3"}}
    out = build_relaysoul_artifact_persistence_dry_run("patch_dry_run", blocked_patch).to_log_dict()
    require(out["persistence_status"] == "warning" and "artifact_status_blocked" in out["warning_reasons"] and out["persistence_ready"] is True, out)

    warning_approval = {"approval_status": "warning", "content_free": True, "patch_candidate_id": "cand-4"}
    out = build_relaysoul_artifact_persistence_dry_run("approval_summary", warning_approval).to_log_dict()
    require("artifact_status_warning" in out["warning_reasons"], out)

    out = build_relaysoul_artifact_persistence_dry_run("patch_dry_run", {"dry_run_status": "ok", "content_free": True, "candidate": {}}).to_log_dict()
    require("missing_artifact_id" in out["blocking_reasons"], out)

    rollback_missing_parent = {"rollback_status": "ok", "content_free": True, "revision": {"revision_id": "rev-2", "parent_revision_id": None}}
    out = build_relaysoul_artifact_persistence_dry_run("rollback_summary", rollback_missing_parent).to_log_dict()
    require(out["persistence_status"] == "warning" and "missing_parent_artifact_id" in out["warning_reasons"], out)
    rollback_empty_parent = {"rollback_status": "ok", "content_free": True, "revision": {"revision_id": "rev-1", "parent_revision_id": ""}}
    out = build_relaysoul_artifact_persistence_dry_run("rollback_summary", rollback_empty_parent).to_log_dict()
    require(out["persistence_status"] == "warning" and out["persistence_ready"] is True and "missing_parent_artifact_id" in out["warning_reasons"], out)

    print("ok warnings and blocking rules")



    envelope_ok = build_relaysoul_storage_envelope_dry_run(
        build_relaysoul_artifact_persistence_dry_run("patch_dry_run", patch_ok),
        patch_ok,
        "char-1",
        created_at="2026-05-25T00:00:00Z",
        source_commit_sha="abc123",
    ).to_log_dict()
    require(envelope_ok["envelope_status"] == "ok", envelope_ok)
    require(isinstance(envelope_ok["envelope"], dict), envelope_ok)
    require(envelope_ok["envelope"]["payload"]["content_free"] is True, envelope_ok)
    print("ok storage envelope dry-run")

    envelope_blocked_cf = build_relaysoul_storage_envelope_dry_run(
        build_relaysoul_artifact_persistence_dry_run("patch_dry_run", patch_ok),
        {"dry_run_status": "ok", "candidate": {"candidate_id": "cand-1"}},
        "char-1",
    ).to_log_dict()
    require(envelope_blocked_cf["envelope_status"] == "blocked", envelope_blocked_cf)
    require("payload_not_content_free" in envelope_blocked_cf["blocking_reasons"], envelope_blocked_cf)

    envelope_blocked_key = build_relaysoul_storage_envelope_dry_run(
        build_relaysoul_artifact_persistence_dry_run("patch_dry_run", patch_ok),
        {"dry_run_status": "ok", "content_free": True, "candidate": {"candidate_id": "cand-1"}, "patch_text": "SECRET"},
        "char-1",
    ).to_log_dict()
    require(envelope_blocked_key["envelope_status"] == "blocked", envelope_blocked_key)
    require("payload_contains_forbidden_content_keys" in envelope_blocked_key["blocking_reasons"], envelope_blocked_key)
    require(envelope_blocked_key["envelope"] is None, envelope_blocked_key)
    print("ok storage envelope fail-closed")
    require("patch_text" not in str(out), out)
    print("ok content-free artifact")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
