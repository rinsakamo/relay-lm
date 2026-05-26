#!/usr/bin/env python3
"""Validate RelaySOUL persistence execution readiness (dry-run preflight)."""

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
STORAGE_ENVELOPE_ARTIFACT_TYPE = "relaysoul_storage_envelope_dry_run"
STORAGE_PATH_PLAN_ARTIFACT_TYPE = "relaysoul_storage_path_plan_dry_run"
STORAGE_INDEX_PLAN_ARTIFACT_TYPE = "relaysoul_storage_index_dry_run"
STORAGE_WRITER_PREFLIGHT_ARTIFACT_TYPE = "relaysoul_storage_writer_preflight_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_persistence_execution_preflight_dry_run"


class PersistenceExecutionPreflightError(ValueError):
    """Raised when persistence execution preflight inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PersistenceExecutionPreflightError(f"{field_name} JSON root must be an object")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceExecutionPreflightError(f"{field} must be non-empty string")
    return value


def _require_safe_path_component(value: Any, field: str) -> str:
    component = _require_non_empty_string(value, field)
    if component in {".", ".."}:
        raise PersistenceExecutionPreflightError(f"{field} must be safe single path component")
    if "/" in component or "\\" in component or "\x00" in component:
        raise PersistenceExecutionPreflightError(f"{field} must be safe single path component")
    return component


def _validate_storage_envelope(payload: Any) -> dict[str, Any]:
    envelope = _require_object(payload, "storage envelope")
    if envelope.get("artifact_type") != STORAGE_ENVELOPE_ARTIFACT_TYPE:
        raise PersistenceExecutionPreflightError(f"artifact_type must be {STORAGE_ENVELOPE_ARTIFACT_TYPE}")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise PersistenceExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if envelope.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage envelope content_free must be true")
    if envelope.get("persistence_ready") is not True:
        raise PersistenceExecutionPreflightError("storage envelope persistence_ready must be true")
    if envelope.get("persistence_status") not in {"ok", "warning"}:
        raise PersistenceExecutionPreflightError("storage envelope persistence_status must be ok or warning")
    blocking_reasons = envelope.get("blocking_reasons")
    if not isinstance(blocking_reasons, list):
        raise PersistenceExecutionPreflightError("storage envelope blocking_reasons must be list")
    if blocking_reasons:
        raise PersistenceExecutionPreflightError("storage envelope is blocked")

    _require_safe_path_component(envelope.get("artifact_kind"), "storage envelope artifact_kind")
    _require_safe_path_component(envelope.get("artifact_id"), "storage envelope artifact_id")
    parent_artifact_id = envelope.get("parent_artifact_id")
    if parent_artifact_id is not None:
        _require_safe_path_component(parent_artifact_id, "storage envelope parent_artifact_id")

    inner = _require_object(envelope.get("envelope"), "storage envelope.envelope")
    character_id = _require_safe_path_component(inner.get("character_id"), "storage envelope.envelope.character_id")
    if inner.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage envelope.envelope.content_free must be true")
    if inner.get("artifact_kind") != envelope.get("artifact_kind"):
        raise PersistenceExecutionPreflightError("storage envelope.envelope.artifact_kind must match top-level")
    if inner.get("artifact_id") != envelope.get("artifact_id"):
        raise PersistenceExecutionPreflightError("storage envelope.envelope.artifact_id must match top-level")
    if inner.get("parent_artifact_id") != envelope.get("parent_artifact_id"):
        raise PersistenceExecutionPreflightError("storage envelope.envelope.parent_artifact_id must match top-level")

    inner_payload = _require_object(inner.get("payload"), "storage envelope.envelope.payload")
    if inner_payload.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage envelope.envelope.payload.content_free must be true")
    forbidden_payload_keys = sorted(key for key in FORBIDDEN_PAYLOAD_KEYS if key in inner_payload)
    if forbidden_payload_keys:
        raise PersistenceExecutionPreflightError(
            "storage envelope.envelope.payload contains forbidden content keys: " + ", ".join(forbidden_payload_keys)
        )

    envelope["_validated_character_id"] = character_id
    return envelope


def _validate_storage_path_plan(payload: Any, storage_envelope: dict[str, Any]) -> dict[str, Any]:
    plan = _require_object(payload, "storage path plan")
    if plan.get("artifact_type") != STORAGE_PATH_PLAN_ARTIFACT_TYPE:
        raise PersistenceExecutionPreflightError(f"artifact_type must be {STORAGE_PATH_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise PersistenceExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage path plan content_free must be true")
    if plan.get("path_plan_status") != "ready":
        raise PersistenceExecutionPreflightError("path_plan_status must be ready")

    for field in ("artifact_kind", "artifact_id", "parent_artifact_id"):
        if plan.get(field) != storage_envelope.get(field):
            raise PersistenceExecutionPreflightError(f"storage path plan {field} must match storage envelope {field}")
    if plan.get("character_id") != storage_envelope.get("_validated_character_id"):
        raise PersistenceExecutionPreflightError("storage path plan character_id must match storage envelope character_id")

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
        raise PersistenceExecutionPreflightError("storage path plan artifact_path must match identity")
    if artifact_index_path != expected_artifact_index_path:
        raise PersistenceExecutionPreflightError("storage path plan artifact_index_path must match character_id")
    if lineage_index_path != expected_lineage_index_path:
        raise PersistenceExecutionPreflightError("storage path plan lineage_index_path must match character_id")

    return plan


def _validate_storage_index_plan(payload: Any, storage_path_plan: dict[str, Any]) -> None:
    plan = _require_object(payload, "storage index plan")
    if plan.get("artifact_type") != STORAGE_INDEX_PLAN_ARTIFACT_TYPE:
        raise PersistenceExecutionPreflightError(f"artifact_type must be {STORAGE_INDEX_PLAN_ARTIFACT_TYPE}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise PersistenceExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage index plan content_free must be true")
    if plan.get("index_plan_status") != "ready":
        raise PersistenceExecutionPreflightError("index_plan_status must be ready")

    for field in ("artifact_kind", "artifact_id", "character_id", "artifact_path", "artifact_index_path", "lineage_index_path"):
        if plan.get(field) != storage_path_plan.get(field):
            raise PersistenceExecutionPreflightError(f"storage index plan {field} must match storage path plan")

    for key in FORBIDDEN_PAYLOAD_KEYS:
        if key in plan:
            raise PersistenceExecutionPreflightError(f"storage index plan contains forbidden content key: {key}")

    artifact_record = _require_object(plan.get("artifact_index_record"), "artifact_index_record")
    lineage_record = _require_object(plan.get("lineage_index_record"), "lineage_index_record")
    if artifact_record.get("record_type") != "artifact":
        raise PersistenceExecutionPreflightError("artifact_index_record.record_type must be artifact")
    if lineage_record.get("record_type") != "lineage":
        raise PersistenceExecutionPreflightError("lineage_index_record.record_type must be lineage")
    if artifact_record.get("content_free") is not True or lineage_record.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("index records content_free must be true")

    for key in FORBIDDEN_PAYLOAD_KEYS:
        if key in artifact_record:
            raise PersistenceExecutionPreflightError(f"artifact_index_record contains forbidden content key: {key}")
        if key in lineage_record:
            raise PersistenceExecutionPreflightError(f"lineage_index_record contains forbidden content key: {key}")

    for field in ("artifact_kind", "artifact_id", "character_id", "artifact_path"):
        if artifact_record.get(field) != storage_path_plan.get(field):
            raise PersistenceExecutionPreflightError(f"artifact_index_record.{field} must match storage path plan")
        if lineage_record.get(field) != storage_path_plan.get(field):
            raise PersistenceExecutionPreflightError(f"lineage_index_record.{field} must match storage path plan")
    if lineage_record.get("parent_artifact_id") != storage_path_plan.get("parent_artifact_id"):
        raise PersistenceExecutionPreflightError("lineage_index_record.parent_artifact_id must match storage path plan parent_artifact_id")


def _validate_storage_writer_preflight(payload: Any, storage_path_plan: dict[str, Any]) -> dict[str, Any]:
    writer = _require_object(payload, "storage writer preflight")
    if writer.get("artifact_type") != STORAGE_WRITER_PREFLIGHT_ARTIFACT_TYPE:
        raise PersistenceExecutionPreflightError(f"artifact_type must be {STORAGE_WRITER_PREFLIGHT_ARTIFACT_TYPE}")
    if writer.get("schema_version") != SCHEMA_VERSION:
        raise PersistenceExecutionPreflightError(f"schema_version must be {SCHEMA_VERSION}")
    if writer.get("content_free") is not True:
        raise PersistenceExecutionPreflightError("storage writer preflight content_free must be true")
    if writer.get("preflight_status") != "ready":
        raise PersistenceExecutionPreflightError("storage writer preflight preflight_status must be ready")
    if writer.get("writer_execution_allowed") is not False:
        raise PersistenceExecutionPreflightError("writer_execution_allowed must be false")
    if writer.get("execution_preflight_type") not in {"apply", "rollback"}:
        raise PersistenceExecutionPreflightError("execution_preflight_type must be apply or rollback")

    for field in ("artifact_kind", "artifact_id", "parent_artifact_id", "character_id", "artifact_path", "artifact_index_path", "lineage_index_path"):
        if writer.get(field) != storage_path_plan.get(field):
            raise PersistenceExecutionPreflightError(f"storage writer preflight {field} must match storage path plan")
    return writer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-envelope", required=True)
    parser.add_argument("--storage-path-plan", required=True)
    parser.add_argument("--storage-index-plan", required=True)
    parser.add_argument("--storage-writer-preflight", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    storage_envelope = _validate_storage_envelope(_read_json(args.storage_envelope))
    storage_path_plan = _validate_storage_path_plan(_read_json(args.storage_path_plan), storage_envelope)
    _validate_storage_index_plan(_read_json(args.storage_index_plan), storage_path_plan)
    writer_preflight = _validate_storage_writer_preflight(_read_json(args.storage_writer_preflight), storage_path_plan)

    artifact = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "preflight_status": "ready",
        "execution_preflight_type": writer_preflight["execution_preflight_type"],
        "artifact_kind": storage_path_plan["artifact_kind"],
        "artifact_id": storage_path_plan["artifact_id"],
        "parent_artifact_id": storage_path_plan.get("parent_artifact_id"),
        "character_id": storage_path_plan["character_id"],
        "artifact_path": storage_path_plan["artifact_path"],
        "artifact_index_path": storage_path_plan["artifact_index_path"],
        "lineage_index_path": storage_path_plan["lineage_index_path"],
        "checked_inputs": ["storage_envelope", "storage_path_plan", "storage_index_plan", "storage_writer_preflight"],
        "writer_execution_allowed": False,
        "persistence_execution_allowed": False,
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
    except PersistenceExecutionPreflightError as exc:
        raise SystemExit(f"error: {exc}")
