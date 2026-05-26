#!/usr/bin/env python3
"""Build RelaySOUL storage index append plan from path plan artifact (dry-run)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from relaylm.relaysoul_persistence import ALLOWED_ARTIFACT_KINDS

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


def _expected_storage_paths(character_id: str, artifact_kind: str, artifact_id: str) -> tuple[str, str, str]:
    artifact_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "artifacts" / character_id / artifact_kind / f"{artifact_id}.json"
    )
    artifact_index_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "index" / character_id / "artifact_index.jsonl"
    )
    lineage_index_path = str(
        PurePosixPath(".relaylm") / "relaysoul" / "index" / character_id / "lineage_index.jsonl"
    )
    return artifact_path, artifact_index_path, lineage_index_path


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

    artifact_kind = _require_non_empty_string(artifact.get("artifact_kind"), "artifact_kind")
    if artifact_kind not in ALLOWED_ARTIFACT_KINDS:
        raise StorageIndexDryRunError("artifact_kind must be supported by ALLOWED_ARTIFACT_KINDS")

    artifact_id = _require_non_empty_string(artifact.get("artifact_id"), "artifact_id")
    character_id = _require_non_empty_string(artifact.get("character_id"), "character_id")

    parent_artifact_id = artifact.get("parent_artifact_id")
    if parent_artifact_id is not None and (not isinstance(parent_artifact_id, str) or not parent_artifact_id.strip()):
        raise StorageIndexDryRunError("parent_artifact_id must be non-empty string when present")

    artifact_path = _require_non_empty_string(artifact.get("artifact_path"), "artifact_path")
    _validate_safe_posix_path(artifact_path, "artifact_path")
    artifact_index_path = _require_non_empty_string(artifact.get("artifact_index_path"), "artifact_index_path")
    _validate_safe_posix_path(artifact_index_path, "artifact_index_path")
    lineage_index_path = _require_non_empty_string(artifact.get("lineage_index_path"), "lineage_index_path")
    _validate_safe_posix_path(lineage_index_path, "lineage_index_path")

    expected_artifact_path, expected_artifact_index_path, expected_lineage_index_path = _expected_storage_paths(
        character_id=character_id,
        artifact_kind=artifact_kind,
        artifact_id=artifact_id,
    )
    if artifact_path != expected_artifact_path:
        raise StorageIndexDryRunError("artifact_path must match character_id/artifact_kind/artifact_id identity")
    if artifact_index_path != expected_artifact_index_path:
        raise StorageIndexDryRunError("artifact_index_path must match character_id index path")
    if lineage_index_path != expected_lineage_index_path:
        raise StorageIndexDryRunError("lineage_index_path must match character_id index path")

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
        "parent_artifact_id": plan.get("parent_artifact_id"),
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
