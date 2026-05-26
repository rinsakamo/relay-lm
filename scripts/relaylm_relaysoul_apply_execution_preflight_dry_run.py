#!/usr/bin/env python3
"""Validate RelaySOUL apply execution readiness (dry-run preflight)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_persistence import FORBIDDEN_PAYLOAD_KEYS

SCHEMA_VERSION = "mvp-soul-0"
APPLY_PLAN_ARTIFACT_TYPE = "relaysoul_apply_plan_dry_run"
STORAGE_ENVELOPE_ARTIFACT_TYPE = "relaysoul_storage_envelope_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_apply_execution_preflight_dry_run"
STORAGE_PATH_PLAN_ARTIFACT_TYPE = "relaysoul_storage_path_plan_dry_run"
STORAGE_INDEX_PLAN_ARTIFACT_TYPE = "relaysoul_storage_index_dry_run"
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class ApplyExecutionPreflightError(ValueError):
    """Raised when apply execution preflight inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApplyExecutionPreflightError(f"{field_name} JSON root must be an object")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplyExecutionPreflightError(f"{field} must be non-empty string")
    return value


def _require_safe_path_component(value: Any, field: str) -> str:
    component = _require_non_empty_string(value, field)
    if component in {".", ".."}:
        raise ApplyExecutionPreflightError(f"{field} must be safe single path component")
    if "/" in component or "\\" in component or "\x00" in component:
        raise ApplyExecutionPreflightError(f"{field} must be safe single path component")
    return component


def _validate_apply_plan(payload: Any) -> dict[str, Any]:
    apply_plan = _require_object(payload, "apply plan")
    if apply_plan.get("artifact_type") != APPLY_PLAN_ARTIFACT_TYPE:
        raise ApplyExecutionPreflightError(f"artifact_type must be {APPLY_PLAN_ARTIFACT_TYPE}")
    if apply_plan.get("schema_version") != SCHEMA_VERSION:
        raise ApplyExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if apply_plan.get("content_free") is not True:
        raise ApplyExecutionPreflightError("content_free must be true")

    _require_non_empty_string(apply_plan.get("apply_plan_id"), "apply_plan_id")
    _require_non_empty_string(apply_plan.get("approval_decision_id"), "approval_decision_id")
    _require_non_empty_string(apply_plan.get("approval_package_id"), "approval_package_id")
    _require_non_empty_string(apply_plan.get("revision_id"), "revision_id")

    if apply_plan.get("apply_plan_status") != "ready":
        raise ApplyExecutionPreflightError("apply_plan_status must be ready")
    if apply_plan.get("rollback_available") is not True:
        raise ApplyExecutionPreflightError("rollback_available must be true")

    changed_files = apply_plan.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise ApplyExecutionPreflightError("changed_files must be non-empty list")
    if any(not isinstance(item, str) or item not in ALLOWED_CHANGED_FILES for item in changed_files):
        raise ApplyExecutionPreflightError("changed_files must contain canonical RelaySOUL file names")

    return apply_plan


def _validate_storage_envelope(payload: Any, apply_plan: dict[str, Any]) -> dict[str, Any]:
    envelope = _require_object(payload, "storage envelope")
    if envelope.get("artifact_type") != STORAGE_ENVELOPE_ARTIFACT_TYPE:
        raise ApplyExecutionPreflightError(f"artifact_type must be {STORAGE_ENVELOPE_ARTIFACT_TYPE}")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise ApplyExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if envelope.get("content_free") is not True:
        raise ApplyExecutionPreflightError("storage envelope content_free must be true")
    if envelope.get("artifact_kind") != "apply_plan":
        raise ApplyExecutionPreflightError("storage envelope artifact_kind must be apply_plan")

    if envelope.get("artifact_id") != apply_plan["apply_plan_id"]:
        raise ApplyExecutionPreflightError("storage envelope artifact_id must match apply_plan_id")
    if envelope.get("parent_artifact_id") != apply_plan["approval_decision_id"]:
        raise ApplyExecutionPreflightError("storage envelope parent_artifact_id must match approval_decision_id")

    if envelope.get("persistence_ready") is not True:
        raise ApplyExecutionPreflightError("storage envelope is blocked: persistence_ready must be true")

    persistence_status = envelope.get("persistence_status")
    if persistence_status not in {"ok", "warning"}:
        raise ApplyExecutionPreflightError("storage envelope persistence_status must be ok or warning")

    blocking_reasons = envelope.get("blocking_reasons")
    if not isinstance(blocking_reasons, list):
        raise ApplyExecutionPreflightError("storage envelope blocking_reasons must be list")
    if blocking_reasons:
        raise ApplyExecutionPreflightError("storage envelope is blocked")

    inner = envelope.get("envelope")
    if not isinstance(inner, dict):
        raise ApplyExecutionPreflightError("storage envelope.envelope must be object")
    if inner.get("artifact_kind") != "apply_plan":
        raise ApplyExecutionPreflightError("envelope.artifact_kind must be apply_plan")
    if inner.get("artifact_id") != apply_plan["apply_plan_id"]:
        raise ApplyExecutionPreflightError("envelope.artifact_id must match apply_plan_id")
    if inner.get("parent_artifact_id") != apply_plan["approval_decision_id"]:
        raise ApplyExecutionPreflightError("envelope.parent_artifact_id must match approval_decision_id")
    if inner.get("content_free") is not True:
        raise ApplyExecutionPreflightError("envelope.content_free must be true")

    inner_persistence_status = inner.get("persistence_status")
    if inner_persistence_status not in {"ok", "warning"}:
        raise ApplyExecutionPreflightError("envelope.persistence_status must be ok or warning")
    if inner_persistence_status != envelope.get("persistence_status"):
        raise ApplyExecutionPreflightError("envelope.persistence_status must match top-level persistence_status")

    inner_blocking_reasons = inner.get("blocking_reasons")
    if not isinstance(inner_blocking_reasons, list):
        raise ApplyExecutionPreflightError("envelope.blocking_reasons must be list")
    if inner_blocking_reasons:
        raise ApplyExecutionPreflightError("envelope.blocking_reasons must be empty")

    inner_warning_reasons = inner.get("warning_reasons")
    if inner_warning_reasons is not None and not isinstance(inner_warning_reasons, list):
        raise ApplyExecutionPreflightError("envelope.warning_reasons must be list when present")

    inner_payload = inner.get("payload")
    if not isinstance(inner_payload, dict):
        raise ApplyExecutionPreflightError("envelope.payload must be object")
    if inner_payload.get("content_free") is not True:
        raise ApplyExecutionPreflightError("envelope.payload.content_free must be true")
    if inner_payload.get("apply_plan_id") != apply_plan["apply_plan_id"]:
        raise ApplyExecutionPreflightError("envelope.payload.apply_plan_id must match apply_plan_id")
    if inner_payload.get("approval_decision_id") != apply_plan["approval_decision_id"]:
        raise ApplyExecutionPreflightError("envelope.payload.approval_decision_id must match approval_decision_id")
    if inner_payload.get("approval_package_id") != apply_plan["approval_package_id"]:
        raise ApplyExecutionPreflightError("envelope.payload.approval_package_id must match approval_package_id")
    if inner_payload.get("revision_id") != apply_plan["revision_id"]:
        raise ApplyExecutionPreflightError("envelope.payload.revision_id must match revision_id")
    if inner_payload.get("apply_plan_status") != apply_plan["apply_plan_status"]:
        raise ApplyExecutionPreflightError("envelope.payload.apply_plan_status must match apply_plan_status")
    if inner_payload.get("rollback_available") != apply_plan["rollback_available"]:
        raise ApplyExecutionPreflightError("envelope.payload.rollback_available must match rollback_available")
    if inner_payload.get("changed_files") != apply_plan["changed_files"]:
        raise ApplyExecutionPreflightError("envelope.payload.changed_files must match changed_files")

    forbidden_payload_keys = sorted(key for key in FORBIDDEN_PAYLOAD_KEYS if key in inner_payload)
    if forbidden_payload_keys:
        raise ApplyExecutionPreflightError(
            "envelope.payload contains forbidden content keys: " + ", ".join(forbidden_payload_keys)
        )

    return envelope


def _validate_storage_path_plan(payload: Any, storage_envelope: dict[str, Any]) -> dict[str, Any]:
    plan = _require_object(payload, "storage path plan")
    if plan.get("artifact_type") != STORAGE_PATH_PLAN_ARTIFACT_TYPE:
        raise ApplyExecutionPreflightError(f"artifact_type must be {STORAGE_PATH_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ApplyExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise ApplyExecutionPreflightError("storage path plan content_free must be true")
    if plan.get("path_plan_status") != "ready":
        raise ApplyExecutionPreflightError("path_plan_status must be ready")

    if plan.get("artifact_kind") != storage_envelope.get("artifact_kind"):
        raise ApplyExecutionPreflightError("storage path plan artifact_kind must match storage envelope artifact_kind")
    if plan.get("artifact_id") != storage_envelope.get("artifact_id"):
        raise ApplyExecutionPreflightError("storage path plan artifact_id must match storage envelope artifact_id")
    if plan.get("parent_artifact_id") != storage_envelope.get("parent_artifact_id"):
        raise ApplyExecutionPreflightError(
            "storage path plan parent_artifact_id must match storage envelope parent_artifact_id"
        )

    character_id = _require_safe_path_component(plan.get("character_id"), "storage path plan character_id")
    artifact_kind = _require_safe_path_component(plan.get("artifact_kind"), "storage path plan artifact_kind")
    artifact_id = _require_safe_path_component(plan.get("artifact_id"), "storage path plan artifact_id")
    parent_artifact_id = plan.get("parent_artifact_id")
    if parent_artifact_id is not None:
        _require_safe_path_component(parent_artifact_id, "storage path plan parent_artifact_id")
    artifact_path = _require_non_empty_string(plan.get("artifact_path"), "storage path plan artifact_path")
    artifact_index_path = _require_non_empty_string(
        plan.get("artifact_index_path"), "storage path plan artifact_index_path"
    )
    lineage_index_path = _require_non_empty_string(
        plan.get("lineage_index_path"), "storage path plan lineage_index_path"
    )

    expected_artifact_path = f".relaylm/relaysoul/artifacts/{character_id}/{artifact_kind}/{artifact_id}.json"
    expected_artifact_index_path = f".relaylm/relaysoul/index/{character_id}/artifact_index.jsonl"
    expected_lineage_index_path = f".relaylm/relaysoul/index/{character_id}/lineage_index.jsonl"
    if artifact_path != expected_artifact_path:
        raise ApplyExecutionPreflightError("storage path plan artifact_path must match identity")
    if artifact_index_path != expected_artifact_index_path:
        raise ApplyExecutionPreflightError("storage path plan artifact_index_path must match character_id")
    if lineage_index_path != expected_lineage_index_path:
        raise ApplyExecutionPreflightError("storage path plan lineage_index_path must match character_id")

    return plan


def _validate_storage_index_plan(
    payload: Any,
    storage_path_plan: dict[str, Any],
    apply_plan: dict[str, Any],
) -> dict[str, Any]:
    plan = _require_object(payload, "storage index plan")
    if plan.get("artifact_type") != STORAGE_INDEX_PLAN_ARTIFACT_TYPE:
        raise ApplyExecutionPreflightError(f"artifact_type must be {STORAGE_INDEX_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ApplyExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise ApplyExecutionPreflightError("storage index plan content_free must be true")
    if plan.get("index_plan_status") != "ready":
        raise ApplyExecutionPreflightError("index_plan_status must be ready")

    for field in (
        "artifact_kind",
        "artifact_id",
        "character_id",
        "artifact_path",
        "artifact_index_path",
        "lineage_index_path",
    ):
        if plan.get(field) != storage_path_plan.get(field):
            raise ApplyExecutionPreflightError(f"storage index plan {field} must match storage path plan")

    for key in FORBIDDEN_PAYLOAD_KEYS:
        if key in plan:
            raise ApplyExecutionPreflightError(f"storage index plan contains forbidden content key: {key}")

    artifact_record = _require_object(plan.get("artifact_index_record"), "artifact_index_record")
    lineage_record = _require_object(plan.get("lineage_index_record"), "lineage_index_record")
    if artifact_record.get("record_type") != "artifact":
        raise ApplyExecutionPreflightError("artifact_index_record.record_type must be artifact")
    if lineage_record.get("record_type") != "lineage":
        raise ApplyExecutionPreflightError("lineage_index_record.record_type must be lineage")
    if artifact_record.get("content_free") is not True or lineage_record.get("content_free") is not True:
        raise ApplyExecutionPreflightError("index records content_free must be true")
    for field in ("artifact_kind", "artifact_id", "character_id", "artifact_path"):
        if artifact_record.get(field) != storage_path_plan.get(field):
            raise ApplyExecutionPreflightError(f"artifact_index_record.{field} must match storage path plan")
        if lineage_record.get(field) != storage_path_plan.get(field):
            raise ApplyExecutionPreflightError(f"lineage_index_record.{field} must match storage path plan")
    if lineage_record.get("parent_artifact_id") != apply_plan.get("approval_decision_id"):
        raise ApplyExecutionPreflightError("lineage_index_record.parent_artifact_id must match approval_decision_id")
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-plan", required=True)
    parser.add_argument("--storage-envelope", required=True)
    parser.add_argument("--storage-path-plan", required=True)
    parser.add_argument("--storage-index-plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    apply_plan = _validate_apply_plan(_read_json(args.apply_plan))
    storage_envelope = _validate_storage_envelope(_read_json(args.storage_envelope), apply_plan)
    storage_path_plan = _validate_storage_path_plan(_read_json(args.storage_path_plan), storage_envelope)
    _validate_storage_index_plan(_read_json(args.storage_index_plan), storage_path_plan, apply_plan)

    created_at_utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    warnings = storage_envelope.get("warning_reasons")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "preflight_status": "ready",
        "apply_plan_id": apply_plan["apply_plan_id"],
        "approval_decision_id": apply_plan["approval_decision_id"],
        "approval_package_id": apply_plan["approval_package_id"],
        "revision_id": apply_plan["revision_id"],
        "artifact_kind": storage_envelope["artifact_kind"],
        "artifact_id": storage_envelope["artifact_id"],
        "parent_artifact_id": storage_envelope["parent_artifact_id"],
        "character_id": storage_path_plan["character_id"],
        "artifact_path": storage_path_plan["artifact_path"],
        "artifact_index_path": storage_path_plan["artifact_index_path"],
        "lineage_index_path": storage_path_plan["lineage_index_path"],
        "changed_files": list(apply_plan["changed_files"]),
        "target_file_count": len(apply_plan["changed_files"]),
        "storage_artifact_id": storage_envelope["artifact_id"],
        "storage_parent_artifact_id": storage_envelope["parent_artifact_id"],
        "persistence_status": storage_envelope["persistence_status"],
        "checked_inputs": [
            "apply_plan",
            "storage_envelope",
            "storage_path_plan",
            "storage_index_plan",
        ],
        "apply_execution_allowed": False,
        "rollback_available": True,
        "created_at_utc": created_at_utc,
        "content_free": True,
        "warnings": warning_list,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except ApplyExecutionPreflightError as exc:
        raise SystemExit(f"error: {exc}")
