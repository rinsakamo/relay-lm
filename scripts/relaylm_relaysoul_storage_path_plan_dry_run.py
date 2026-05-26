#!/usr/bin/env python3
"""Build RelaySOUL storage path plan from storage envelope artifact (dry-run)."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath, Path
from typing import Any

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_persistence import ALLOWED_ARTIFACT_KINDS, FORBIDDEN_PAYLOAD_KEYS

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_storage_envelope_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_storage_path_plan_dry_run"


class StoragePathPlanError(ValueError):
    """Raised when storage path planner dry-run inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StoragePathPlanError(f"{name} JSON root must be an object")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StoragePathPlanError(f"{field} must be non-empty string")
    return value


def _sanitize_component(value: str, field: str) -> str:
    if value in {".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise StoragePathPlanError(f"{field} contains invalid path component")
    return value


def _validate_storage_envelope(payload: Any) -> tuple[str, str, str, str | None]:
    artifact = _require_object(payload, "storage envelope")
    if artifact.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise StoragePathPlanError(f"artifact_type must be {INPUT_ARTIFACT_TYPE}")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise StoragePathPlanError(f"schema_version must be {SCHEMA_VERSION}")
    if artifact.get("content_free") is not True:
        raise StoragePathPlanError("content_free must be true")

    kind = _require_non_empty_string(artifact.get("artifact_kind"), "artifact_kind")
    if kind not in ALLOWED_ARTIFACT_KINDS:
        raise StoragePathPlanError("artifact_kind unsupported")

    artifact_id = _sanitize_component(_require_non_empty_string(artifact.get("artifact_id"), "artifact_id"), "artifact_id")

    if artifact.get("persistence_ready") is not True:
        raise StoragePathPlanError("persistence_ready must be true")
    status = artifact.get("persistence_status")
    if status not in {"ok", "warning"}:
        raise StoragePathPlanError("persistence_status must be ok or warning")

    blocking_reasons = artifact.get("blocking_reasons")
    if not isinstance(blocking_reasons, list):
        raise StoragePathPlanError("blocking_reasons must be list")
    if blocking_reasons:
        raise StoragePathPlanError("blocked storage envelope is not plannable")

    envelope = _require_object(artifact.get("envelope"), "envelope")
    if envelope.get("content_free") is not True:
        raise StoragePathPlanError("envelope.content_free must be true")
    if envelope.get("artifact_kind") != kind:
        raise StoragePathPlanError("envelope.artifact_kind must match artifact_kind")
    if envelope.get("artifact_id") != artifact_id:
        raise StoragePathPlanError("envelope.artifact_id must match artifact_id")

    character_id = _sanitize_component(
        _require_non_empty_string(envelope.get("character_id"), "envelope.character_id"),
        "envelope.character_id",
    )

    inner_payload = _require_object(envelope.get("payload"), "envelope.payload")
    if inner_payload.get("content_free") is not True:
        raise StoragePathPlanError("envelope.payload.content_free must be true")

    forbidden_payload_keys = sorted(key for key in FORBIDDEN_PAYLOAD_KEYS if key in inner_payload)
    if forbidden_payload_keys:
        raise StoragePathPlanError(
            "envelope.payload contains forbidden content keys: " + ", ".join(forbidden_payload_keys)
        )

    top_parent = artifact.get("parent_artifact_id")
    inner_parent = envelope.get("parent_artifact_id")
    if top_parent is not None and not isinstance(top_parent, str):
        raise StoragePathPlanError("parent_artifact_id must be string when present")
    if inner_parent is not None and not isinstance(inner_parent, str):
        raise StoragePathPlanError("envelope.parent_artifact_id must be string when present")
    if top_parent is not None and inner_parent is not None and top_parent != inner_parent:
        raise StoragePathPlanError("parent_artifact_id mismatch between top-level and envelope")

    parent_artifact_id = top_parent if top_parent is not None else inner_parent
    if parent_artifact_id is not None:
        parent_artifact_id = _sanitize_component(parent_artifact_id, "parent_artifact_id")

    return kind, artifact_id, character_id, parent_artifact_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-envelope", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    artifact_kind, artifact_id, character_id, parent_artifact_id = _validate_storage_envelope(_read_json(args.storage_envelope))

    artifact_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "artifacts" / character_id / artifact_kind / f"{artifact_id}.json"
    )
    artifact_index_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "index" / character_id / "artifact_index.jsonl"
    )
    lineage_index_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "index" / character_id / "lineage_index.jsonl"
    )

    output = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": artifact_kind,
        "artifact_id": artifact_id,
        "character_id": character_id,
        "parent_artifact_id": parent_artifact_id,
        "artifact_path": artifact_path,
        "artifact_index_path": artifact_index_path,
        "lineage_index_path": lineage_index_path,
        "path_plan_status": "ready",
        "content_free": True,
        "warnings": [],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except StoragePathPlanError as exc:
        raise SystemExit(f"error: {exc}")
