#!/usr/bin/env python3
"""Build RelaySOUL rollback plan artifact from apply plan (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_apply_plan_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_rollback_plan_dry_run"
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class RollbackPlanError(ValueError):
    """Raised when rollback plan dry-run inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RollbackPlanError(f"{field} must be non-empty string")
    return value


def _validate_apply_plan(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RollbackPlanError("apply plan JSON root must be an object")
    if payload.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise RollbackPlanError(f"artifact_type must be {INPUT_ARTIFACT_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise RollbackPlanError(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("content_free") is not True:
        raise RollbackPlanError("content_free must be true")

    _require_non_empty_string(payload.get("apply_plan_id"), "apply_plan_id")
    _require_non_empty_string(payload.get("approval_decision_id"), "approval_decision_id")
    _require_non_empty_string(payload.get("approval_package_id"), "approval_package_id")
    _require_non_empty_string(payload.get("revision_id"), "revision_id")

    changed_files = payload.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise RollbackPlanError("changed_files must be non-empty list")
    if any(not isinstance(item, str) or item not in ALLOWED_CHANGED_FILES for item in changed_files):
        raise RollbackPlanError("changed_files must contain canonical RelaySOUL file names")

    if payload.get("rollback_available") is not True:
        raise RollbackPlanError("rollback_available must be true")
    if payload.get("apply_plan_status") != "ready":
        raise RollbackPlanError("apply_plan_status must be ready")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    apply_plan = _validate_apply_plan(_read_json(args.apply_plan))

    now = datetime.now(UTC)
    created_at_utc = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    revision_suffix = str(apply_plan["revision_id"]).split("-")[-1][:12]
    rollback_plan_id = f"relaysoul-rollback-plan-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{revision_suffix}"

    warnings = apply_plan.get("warnings")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "rollback_plan_id": rollback_plan_id,
        "apply_plan_id": apply_plan["apply_plan_id"],
        "approval_decision_id": apply_plan["approval_decision_id"],
        "approval_package_id": apply_plan["approval_package_id"],
        "revision_id": apply_plan["revision_id"],
        "parent_revision_id": apply_plan.get("parent_revision_id"),
        "rollback_plan_status": "ready",
        "source_apply_plan_status": apply_plan["apply_plan_status"],
        "changed_files": apply_plan["changed_files"],
        "target_file_count": len(apply_plan["changed_files"]),
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
