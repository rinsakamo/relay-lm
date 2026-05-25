#!/usr/bin/env python3
"""Build RelaySOUL apply plan artifact from approval decision (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_approval_decision_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_apply_plan_dry_run"
READY_STATUSES = {"approved", "approval_not_required"}
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class ApplyPlanError(ValueError):
    """Raised when apply plan dry-run inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplyPlanError(f"{field} must be non-empty string")
    return value


def _validate_approval_decision(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApplyPlanError("approval decision JSON root must be an object")
    if payload.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise ApplyPlanError(f"artifact_type must be {INPUT_ARTIFACT_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ApplyPlanError(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("content_free") is not True:
        raise ApplyPlanError("content_free must be true")
    if payload.get("rollback_available") is not True:
        raise ApplyPlanError("rollback_available must be true")

    _require_non_empty_string(payload.get("approval_decision_id"), "approval_decision_id")
    _require_non_empty_string(payload.get("approval_package_id"), "approval_package_id")
    _require_non_empty_string(payload.get("revision_id"), "revision_id")

    changed_files = payload.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise ApplyPlanError("changed_files must be non-empty list")
    if any(not isinstance(item, str) or item not in ALLOWED_CHANGED_FILES for item in changed_files):
        raise ApplyPlanError("changed_files must contain canonical RelaySOUL file names")

    decision_status = payload.get("decision_status")
    if not isinstance(decision_status, str) or not decision_status.strip():
        raise ApplyPlanError("decision_status must be non-empty string")
    if decision_status == "denied":
        raise ApplyPlanError("denied decisions cannot produce apply plan")
    if decision_status == "deferred":
        raise ApplyPlanError("deferred decisions cannot produce apply plan")
    if decision_status not in READY_STATUSES:
        raise ApplyPlanError(f"unknown decision_status: {decision_status}")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-decision", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    decision = _validate_approval_decision(_read_json(args.approval_decision))

    now = datetime.now(UTC)
    created_at_utc = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    revision_suffix = str(decision["revision_id"]).split("-")[-1][:12]
    apply_plan_id = f"relaysoul-apply-plan-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{revision_suffix}"

    warnings = decision.get("warnings")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "apply_plan_id": apply_plan_id,
        "approval_decision_id": decision["approval_decision_id"],
        "approval_package_id": decision["approval_package_id"],
        "revision_id": decision["revision_id"],
        "parent_revision_id": decision.get("parent_revision_id"),
        "apply_plan_status": "ready",
        "source_decision_status": decision["decision_status"],
        "changed_files": decision["changed_files"],
        "target_file_count": len(decision["changed_files"]),
        "rollback_available": True,
        "created_at_utc": created_at_utc,
        "content_free": True,
        "warnings": warning_list,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
