#!/usr/bin/env python3
"""Record RelaySOUL approval decision from approval package (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_approval_package_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_approval_decision_dry_run"
ALLOWED_DECISIONS = {"approve", "deny", "defer"}
ALLOWED_APPROVAL_STATUS = {"pending_user_approval", "approval_not_required"}
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class ApprovalDecisionError(ValueError):
    """Raised when approval decision dry-run inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApprovalDecisionError(f"{field} must be non-empty string")
    return value


def _validate_approval_package(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApprovalDecisionError("approval package JSON root must be an object")
    if payload.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise ApprovalDecisionError(f"artifact_type must be {INPUT_ARTIFACT_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ApprovalDecisionError(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("content_free") is not True:
        raise ApprovalDecisionError("content_free must be true")
    if payload.get("rollback_available") is not True:
        raise ApprovalDecisionError("rollback_available must be true")

    _require_non_empty_string(payload.get("approval_package_id"), "approval_package_id")
    _require_non_empty_string(payload.get("revision_id"), "revision_id")

    approval_status = payload.get("approval_status")
    if not isinstance(approval_status, str) or approval_status not in ALLOWED_APPROVAL_STATUS:
        raise ApprovalDecisionError("approval_status must be pending_user_approval or approval_not_required")

    changed_files = payload.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise ApprovalDecisionError("changed_files must be non-empty list")
    if any(not isinstance(item, str) or item not in ALLOWED_CHANGED_FILES for item in changed_files):
        raise ApprovalDecisionError("changed_files must contain canonical RelaySOUL file names")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-package", required=True)
    parser.add_argument("--decision", required=True, choices=sorted(ALLOWED_DECISIONS))
    parser.add_argument("--decided-by", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    package = _validate_approval_package(_read_json(args.approval_package))
    decided_by = _require_non_empty_string(args.decided_by, "decided_by")
    approval_status = package["approval_status"]

    if approval_status == "approval_not_required":
        if args.decision != "approve":
            raise ApprovalDecisionError(
                "approval_not_required accepts only decision=approve"
            )
        decision_status = "approval_not_required"
    else:
        decision_status = {
            "approve": "approved",
            "deny": "denied",
            "defer": "deferred",
        }[args.decision]

    now = datetime.now(UTC)
    created_at_utc = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    approval_package_id = package["approval_package_id"]
    suffix = str(approval_package_id).split("-")[-1][:12]
    approval_decision_id = (
        f"relaysoul-decision-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{suffix}"
    )

    warnings = package.get("warnings")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "approval_decision_id": approval_decision_id,
        "approval_package_id": approval_package_id,
        "revision_id": package["revision_id"],
        "parent_revision_id": package.get("parent_revision_id"),
        "decision": args.decision,
        "decision_status": decision_status,
        "decided_by": decided_by,
        "changed_files": package["changed_files"],
        "rollback_available": True,
        "created_at_utc": created_at_utc,
        "source_approval_status": approval_status,
        "content_free": True,
        "warnings": warning_list,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
