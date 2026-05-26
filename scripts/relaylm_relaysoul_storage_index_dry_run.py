#!/usr/bin/env python3
"""Build RelaySOUL storage index append plan from path plan artifact (dry-run)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_storage_path_plan_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_storage_index_dry_run"


class StorageIndexDryRunError(ValueError):
    """Raised when storage index dry-run input is invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StorageIndexDryRunError(f"{name} JSON root must be an object")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StorageIndexDryRunError(f"{field} must be non-empty string")
    return value


def _validate_safe_posix_path(path_text: str, field: str) -> str:
    _require_non_empty_string(path_text, field)
    parsed = PurePosixPath(path_text)
    if parsed.is_absolute() or ".." in parsed.parts or "\\" in path_text or "\x00" in path_text:
        raise StorageIndexDryRunError(f"{field} contains invalid path")
    return path_text


def _validate_path_plan(payload: Any) -> dict[str, Any]:
    artifact = _require_object(payload, "storage path plan")
    if artifact.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise StorageIndexDryRunError(f"artifact_type must be {INPUT_ARTIFACT_TYPE}")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise StorageIndexDryRunError(f"schema_version must be {SCHEMA_VERSION}")
    if artifact.get("content_free") is not True:
        raise StorageIndexDryRunError("content_free must be true")
    if artifact.get("path_plan_status") != "ready":
        raise StorageIndexDryRunError("path_plan_status must be ready")

    _require_non_empty_string(artifact.get("artifact_kind"), "artifact_kind")
    _require_non_empty_string(artifact.get("artifact_id"), "artifact_id")
    _require_non_empty_string(artifact.get("character_id"), "character_id")

    _validate_safe_posix_path(str(artifact.get("artifact_path", "")), "artifact_path")
    _validate_safe_posix_path(str(artifact.get("artifact_index_path", "")), "artifact_index_path")
    _validate_safe_posix_path(str(artifact.get("lineage_index_path", "")), "lineage_index_path")

    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-path-plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    plan = _validate_path_plan(_read_json(args.storage_path_plan))

    artifact_index_record = {
        "record_type": "artifact",
        "artifact_kind": plan["artifact_kind"],
        "artifact_id": plan["artifact_id"],
        "character_id": plan["character_id"],
        "artifact_path": plan["artifact_path"],
        "content_free": True,
    }
    lineage_index_record = {
        "record_type": "lineage",
        "artifact_kind": plan["artifact_kind"],
        "artifact_id": plan["artifact_id"],
        "character_id": plan["character_id"],
        "artifact_path": plan["artifact_path"],
        "parent_artifact_id": None,
        "content_free": True,
    }

    output = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": plan["artifact_kind"],
        "artifact_id": plan["artifact_id"],
        "character_id": plan["character_id"],
        "artifact_path": plan["artifact_path"],
        "artifact_index_path": plan["artifact_index_path"],
        "lineage_index_path": plan["lineage_index_path"],
        "index_plan_status": "ready",
        "artifact_index_record": artifact_index_record,
        "lineage_index_record": lineage_index_record,
        "content_free": True,
        "warnings": [],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except StorageIndexDryRunError as exc:
        raise SystemExit(f"error: {exc}")
