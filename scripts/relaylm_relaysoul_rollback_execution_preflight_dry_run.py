#!/usr/bin/env python3
"""Validate RelaySOUL rollback execution readiness (dry-run preflight)."""

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
ROLLBACK_PLAN_ARTIFACT_TYPE = "relaysoul_rollback_plan_dry_run"
STORAGE_ENVELOPE_ARTIFACT_TYPE = "relaysoul_storage_envelope_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_rollback_execution_preflight_dry_run"
STORAGE_PATH_PLAN_ARTIFACT_TYPE = "relaysoul_storage_path_plan_dry_run"
STORAGE_INDEX_PLAN_ARTIFACT_TYPE = "relaysoul_storage_index_dry_run"


class RollbackExecutionPreflightError(ValueError):
    """Raised when rollback execution preflight inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RollbackExecutionPreflightError(f"{field_name} JSON root must be an object")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RollbackExecutionPreflightError(f"{field} must be non-empty string")
    return value


def _require_safe_path_component(value: Any, field: str) -> str:
    component = _require_non_empty_string(value, field)
    if component in {".", ".."}:
        raise RollbackExecutionPreflightError(f"{field} must be safe single path component")
    if "/" in component or "\\" in component or "\x00" in component:
        raise RollbackExecutionPreflightError(f"{field} must be safe single path component")
    return component


def _validate_rollback_plan(payload: Any) -> dict[str, Any]:
    rollback_plan = _require_object(payload, "rollback plan")
    if rollback_plan.get("artifact_type") != ROLLBACK_PLAN_ARTIFACT_TYPE:
        raise RollbackExecutionPreflightError(f"artifact_type must be {ROLLBACK_PLAN_ARTIFACT_TYPE}")
    if rollback_plan.get("schema_version") != SCHEMA_VERSION:
        raise RollbackExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if rollback_plan.get("content_free") is not True:
        raise RollbackExecutionPreflightError("content_free must be true")

    _require_non_empty_string(rollback_plan.get("rollback_plan_id"), "rollback_plan_id")
    _require_non_empty_string(rollback_plan.get("apply_plan_id"), "apply_plan_id")
    _require_non_empty_string(rollback_plan.get("approval_decision_id"), "approval_decision_id")
    _require_non_empty_string(rollback_plan.get("approval_package_id"), "approval_package_id")
    _require_non_empty_string(rollback_plan.get("revision_id"), "revision_id")

    if rollback_plan.get("rollback_plan_status") != "ready":
        raise RollbackExecutionPreflightError("rollback_plan_status must be ready")
    return rollback_plan


def _validate_storage_envelope(payload: Any, rollback_plan: dict[str, Any]) -> dict[str, Any]:
    envelope = _require_object(payload, "storage envelope")
    if envelope.get("artifact_type") != STORAGE_ENVELOPE_ARTIFACT_TYPE:
        raise RollbackExecutionPreflightError(f"artifact_type must be {STORAGE_ENVELOPE_ARTIFACT_TYPE}")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise RollbackExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if envelope.get("content_free") is not True:
        raise RollbackExecutionPreflightError("storage envelope content_free must be true")
    if envelope.get("artifact_kind") != "rollback_plan":
        raise RollbackExecutionPreflightError("storage envelope artifact_kind must be rollback_plan")
    if envelope.get("artifact_id") != rollback_plan["rollback_plan_id"]:
        raise RollbackExecutionPreflightError("storage envelope artifact_id must match rollback_plan_id")
    if envelope.get("parent_artifact_id") != rollback_plan["apply_plan_id"]:
        raise RollbackExecutionPreflightError("storage envelope parent_artifact_id must match apply_plan_id")
    if envelope.get("persistence_ready") is not True:
        raise RollbackExecutionPreflightError("storage envelope is blocked: persistence_ready must be true")
    if envelope.get("persistence_status") not in {"ok", "warning"}:
        raise RollbackExecutionPreflightError("storage envelope persistence_status must be ok or warning")
    blocking_reasons = envelope.get("blocking_reasons")
    if not isinstance(blocking_reasons, list):
        raise RollbackExecutionPreflightError("storage envelope blocking_reasons must be list")
    if blocking_reasons:
        raise RollbackExecutionPreflightError("storage envelope is blocked")

    inner = envelope.get("envelope")
    if not isinstance(inner, dict):
        raise RollbackExecutionPreflightError("storage envelope.envelope must be object")
    if inner.get("artifact_kind") != "rollback_plan":
        raise RollbackExecutionPreflightError("envelope.artifact_kind must be rollback_plan")
    if inner.get("artifact_id") != rollback_plan["rollback_plan_id"]:
        raise RollbackExecutionPreflightError("envelope.artifact_id must match rollback_plan_id")
    if inner.get("parent_artifact_id") != rollback_plan["apply_plan_id"]:
        raise RollbackExecutionPreflightError("envelope.parent_artifact_id must match apply_plan_id")
    if inner.get("content_free") is not True:
        raise RollbackExecutionPreflightError("envelope.content_free must be true")
    if inner.get("persistence_status") not in {"ok", "warning"}:
        raise RollbackExecutionPreflightError("envelope.persistence_status must be ok or warning")
    if inner.get("persistence_status") != envelope.get("persistence_status"):
        raise RollbackExecutionPreflightError("envelope.persistence_status must match top-level persistence_status")

    inner_blocking_reasons = inner.get("blocking_reasons")
    if not isinstance(inner_blocking_reasons, list):
        raise RollbackExecutionPreflightError("envelope.blocking_reasons must be list")
    if inner_blocking_reasons:
        raise RollbackExecutionPreflightError("envelope.blocking_reasons must be empty")

    inner_payload = inner.get("payload")
    if not isinstance(inner_payload, dict):
        raise RollbackExecutionPreflightError("envelope.payload must be object")
    if inner_payload.get("content_free") is not True:
        raise RollbackExecutionPreflightError("envelope.payload.content_free must be true")
    if inner_payload.get("rollback_plan_id") != rollback_plan["rollback_plan_id"]:
        raise RollbackExecutionPreflightError("envelope.payload.rollback_plan_id must match rollback_plan_id")
    if inner_payload.get("apply_plan_id") != rollback_plan["apply_plan_id"]:
        raise RollbackExecutionPreflightError("envelope.payload.apply_plan_id must match apply_plan_id")
    if inner_payload.get("approval_decision_id") != rollback_plan["approval_decision_id"]:
        raise RollbackExecutionPreflightError("envelope.payload.approval_decision_id must match approval_decision_id")
    if inner_payload.get("approval_package_id") != rollback_plan["approval_package_id"]:
        raise RollbackExecutionPreflightError("envelope.payload.approval_package_id must match approval_package_id")
    if inner_payload.get("revision_id") != rollback_plan["revision_id"]:
        raise RollbackExecutionPreflightError("envelope.payload.revision_id must match revision_id")
    if inner_payload.get("rollback_plan_status") != rollback_plan["rollback_plan_status"]:
        raise RollbackExecutionPreflightError("envelope.payload.rollback_plan_status must match rollback_plan_status")

    forbidden_payload_keys = sorted(key for key in FORBIDDEN_PAYLOAD_KEYS if key in inner_payload)
    if forbidden_payload_keys:
        raise RollbackExecutionPreflightError(
            "envelope.payload contains forbidden content keys: " + ", ".join(forbidden_payload_keys)
        )

    return envelope


def _validate_storage_path_plan(payload: Any, storage_envelope: dict[str, Any]) -> dict[str, Any]:
    plan = _require_object(payload, "storage path plan")
    if plan.get("artifact_type") != STORAGE_PATH_PLAN_ARTIFACT_TYPE:
        raise RollbackExecutionPreflightError(f"artifact_type must be {STORAGE_PATH_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise RollbackExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise RollbackExecutionPreflightError("storage path plan content_free must be true")
    if plan.get("path_plan_status") != "ready":
        raise RollbackExecutionPreflightError("path_plan_status must be ready")

    for field in ("artifact_kind", "artifact_id", "parent_artifact_id"):
        if plan.get(field) != storage_envelope.get(field):
            raise RollbackExecutionPreflightError(f"storage path plan {field} must match storage envelope {field}")

    character_id = _require_safe_path_component(plan.get("character_id"), "storage path plan character_id")
    artifact_kind = _require_safe_path_component(plan.get("artifact_kind"), "storage path plan artifact_kind")
    artifact_id = _require_safe_path_component(plan.get("artifact_id"), "storage path plan artifact_id")
    parent_artifact_id = plan.get("parent_artifact_id")
    if parent_artifact_id is not None:
        _require_safe_path_component(parent_artifact_id, "storage path plan parent_artifact_id")
    artifact_path = _require_non_empty_string(plan.get("artifact_path"), "storage path plan artifact_path")
    artifact_index_path = _require_non_empty_string(plan.get("artifact_index_path"), "storage path plan artifact_index_path")
    lineage_index_path = _require_non_empty_string(plan.get("lineage_index_path"), "storage path plan lineage_index_path")

    expected_artifact_path = f".relaylm/relaysoul/artifacts/{character_id}/{artifact_kind}/{artifact_id}.json"
    expected_artifact_index_path = f".relaylm/relaysoul/index/{character_id}/artifact_index.jsonl"
    expected_lineage_index_path = f".relaylm/relaysoul/index/{character_id}/lineage_index.jsonl"
    if artifact_path != expected_artifact_path:
        raise RollbackExecutionPreflightError("storage path plan artifact_path must match identity")
    if artifact_index_path != expected_artifact_index_path:
        raise RollbackExecutionPreflightError("storage path plan artifact_index_path must match character_id")
    if lineage_index_path != expected_lineage_index_path:
        raise RollbackExecutionPreflightError("storage path plan lineage_index_path must match character_id")
    return plan


def _validate_storage_index_plan(payload: Any, storage_path_plan: dict[str, Any], rollback_plan: dict[str, Any]) -> None:
    plan = _require_object(payload, "storage index plan")
    if plan.get("artifact_type") != STORAGE_INDEX_PLAN_ARTIFACT_TYPE:
        raise RollbackExecutionPreflightError(f"artifact_type must be {STORAGE_INDEX_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise RollbackExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise RollbackExecutionPreflightError("storage index plan content_free must be true")
    if plan.get("index_plan_status") != "ready":
        raise RollbackExecutionPreflightError("index_plan_status must be ready")

    for field in ("artifact_kind", "artifact_id", "character_id", "artifact_path", "artifact_index_path", "lineage_index_path"):
        if plan.get(field) != storage_path_plan.get(field):
            raise RollbackExecutionPreflightError(f"storage index plan {field} must match storage path plan")

    for key in FORBIDDEN_PAYLOAD_KEYS:
        if key in plan:
            raise RollbackExecutionPreflightError(f"storage index plan contains forbidden content key: {key}")

    artifact_record = _require_object(plan.get("artifact_index_record"), "artifact_index_record")
    lineage_record = _require_object(plan.get("lineage_index_record"), "lineage_index_record")
    if artifact_record.get("record_type") != "artifact":
        raise RollbackExecutionPreflightError("artifact_index_record.record_type must be artifact")
    if lineage_record.get("record_type") != "lineage":
        raise RollbackExecutionPreflightError("lineage_index_record.record_type must be lineage")
    if artifact_record.get("content_free") is not True or lineage_record.get("content_free") is not True:
        raise RollbackExecutionPreflightError("index records content_free must be true")
    for key in FORBIDDEN_PAYLOAD_KEYS:
        if key in artifact_record:
            raise RollbackExecutionPreflightError(f"artifact_index_record contains forbidden content key: {key}")
        if key in lineage_record:
            raise RollbackExecutionPreflightError(f"lineage_index_record contains forbidden content key: {key}")
    for field in ("artifact_kind", "artifact_id", "character_id", "artifact_path"):
        if artifact_record.get(field) != storage_path_plan.get(field):
            raise RollbackExecutionPreflightError(f"artifact_index_record.{field} must match storage path plan")
        if lineage_record.get(field) != storage_path_plan.get(field):
            raise RollbackExecutionPreflightError(f"lineage_index_record.{field} must match storage path plan")
    if lineage_record.get("parent_artifact_id") != rollback_plan.get("apply_plan_id"):
        raise RollbackExecutionPreflightError("lineage_index_record.parent_artifact_id must match apply_plan_id")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollback-plan", required=True)
    parser.add_argument("--storage-envelope", required=True)
    parser.add_argument("--storage-path-plan", required=True)
    parser.add_argument("--storage-index-plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rollback_plan = _validate_rollback_plan(_read_json(args.rollback_plan))
    storage_envelope = _validate_storage_envelope(_read_json(args.storage_envelope), rollback_plan)
    storage_path_plan = _validate_storage_path_plan(_read_json(args.storage_path_plan), storage_envelope)
    _validate_storage_index_plan(_read_json(args.storage_index_plan), storage_path_plan, rollback_plan)

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "preflight_status": "ready",
        "rollback_plan_id": rollback_plan["rollback_plan_id"],
        "apply_plan_id": rollback_plan["apply_plan_id"],
        "approval_decision_id": rollback_plan["approval_decision_id"],
        "approval_package_id": rollback_plan["approval_package_id"],
        "revision_id": rollback_plan["revision_id"],
        "artifact_kind": storage_envelope["artifact_kind"],
        "artifact_id": storage_envelope["artifact_id"],
        "parent_artifact_id": storage_envelope["parent_artifact_id"],
        "character_id": storage_path_plan["character_id"],
        "artifact_path": storage_path_plan["artifact_path"],
        "artifact_index_path": storage_path_plan["artifact_index_path"],
        "lineage_index_path": storage_path_plan["lineage_index_path"],
        "checked_inputs": ["rollback_plan", "storage_envelope", "storage_path_plan", "storage_index_plan"],
        "rollback_execution_allowed": False,
        "created_at_utc": datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "content_free": True,
        "warnings": [],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except RollbackExecutionPreflightError as exc:
        raise SystemExit(f"error: {exc}")
