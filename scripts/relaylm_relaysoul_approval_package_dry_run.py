#!/usr/bin/env python3
"""Build RelaySOUL approval-ready package artifact from revision entry (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
ARTIFACT_TYPE = "relaysoul_approval_package_dry_run"
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class ApprovalPackageError(ValueError):
    """Raised when revision entry shape is invalid for approval package dry-run."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parse_aware_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ApprovalPackageError(f"{field_name} must be a non-empty timestamp string")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ApprovalPackageError(f"{field_name} is invalid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApprovalPackageError(f"{field_name} must be timezone-aware (Z or offset)")
    return parsed


def _validate_revision_entry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApprovalPackageError("revision entry JSON root must be an object")
    if payload.get("content_free") is not True:
        raise ApprovalPackageError("content_free must be true")
    if payload.get("rollback_available") is not True:
        raise ApprovalPackageError("rollback_available must be true")

    revision_id = payload.get("revision_id")
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise ApprovalPackageError("revision_id must be non-empty string")

    _parse_aware_datetime(payload.get("created_at_utc"), "created_at_utc")

    changed_files = payload.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise ApprovalPackageError("changed_files must be non-empty list")
    if any(not isinstance(f, str) or f not in ALLOWED_CHANGED_FILES for f in changed_files):
        raise ApprovalPackageError("changed_files must contain canonical file names only")

    if payload.get("compile_dry_run_status") != "ok":
        raise ApprovalPackageError("compile_dry_run_status must be ok")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision-entry", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    revision = _validate_revision_entry(_read_json(args.revision_entry))

    now = datetime.now(UTC)
    now_utc = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    revision_id = revision["revision_id"]
    suffix = revision_id.split("-")[-1][:12]
    approval_package_id = f"relaysoul-approval-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{suffix}"

    warnings = revision.get("warnings")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    stable_prefix_changed = bool(revision.get("stable_prefix_changed"))
    risk_summary = {
        "high_risk_candidate_count": revision.get("high_risk_candidate_count", 0),
        "soul_patch_candidate_present": bool(revision.get("soul_patch_candidate_present", False)),
        "stable_prefix_changed": stable_prefix_changed,
        "changed_file_count": len(revision["changed_files"]),
        "warning_count": len(warning_list),
    }

    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "approval_package_id": approval_package_id,
        "revision_id": revision_id,
        "parent_revision_id": revision.get("parent_revision_id"),
        "mode": revision.get("mode"),
        "changed_files": revision["changed_files"],
        "approval_required": bool(revision.get("approval_required", True)),
        "approval_status": "pending_user_approval",
        "risk_summary": risk_summary,
        "stable_prefix_changed": stable_prefix_changed,
        "rollback_available": True,
        "warning_count": len(warning_list),
        "warnings": warning_list,
        "created_at_utc": now_utc,
        "source_revision_created_at_utc": revision.get("created_at_utc"),
        "content_free": True,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
