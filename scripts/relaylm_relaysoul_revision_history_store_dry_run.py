#!/usr/bin/env python3
"""Store RelaySOUL temp revision compile metadata into history (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

from pathlib import Path

SCHEMA_VERSION = "mvp-soul-0"
INPUT_ARTIFACT_TYPE = "relaysoul_temp_revision_compile_dry_run"
OUTPUT_ARTIFACT_TYPE = "relaysoul_revision_history_store_dry_run"
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


class RevisionHistoryStoreError(ValueError):
    """Raised when input artifacts are invalid for dry-run history store."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RevisionHistoryStoreError(f"{label} must be an object")
    return value


def _build_revision_id(created_at_utc: datetime, stable_prefix_hash_after: str | None) -> str:
    ts = created_at_utc.strftime('%Y%m%dT%H%M%S%fZ')
    if isinstance(stable_prefix_hash_after, str) and stable_prefix_hash_after.strip():
        return f"relaysoul-rev-{ts}-{stable_prefix_hash_after[:12]}"
    return f"relaysoul-rev-{ts}"




def _parse_created_at_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _resolve_parent_revision_id(history_dir: Path) -> str | None:
    latest_key: tuple[datetime, str] | None = None
    latest_revision_id: str | None = None

    for path in history_dir.glob("*.json"):
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        revision_id = payload.get("revision_id")
        created_at_raw = payload.get("created_at_utc")
        created_at = _parse_created_at_utc(created_at_raw)
        if not isinstance(revision_id, str) or not revision_id.strip() or created_at is None:
            continue

        candidate_key = (created_at, path.name)
        if latest_key is None or candidate_key > latest_key:
            latest_key = candidate_key
            latest_revision_id = revision_id

    return latest_revision_id


def _build_unique_revision_path(history_dir: Path, base_revision_id: str) -> tuple[str, Path]:
    revision_id = base_revision_id
    revision_path = history_dir / f"{revision_id}.json"
    suffix = 2
    while revision_path.exists():
        revision_id = f"{base_revision_id}-{suffix}"
        revision_path = history_dir / f"{revision_id}.json"
        suffix += 1
    return revision_id, revision_path

def _validate_input_artifact(payload: Any) -> dict[str, Any]:
    root = _require_object(payload, "temp revision compile artifact")

    if root.get("artifact_type") != INPUT_ARTIFACT_TYPE:
        raise RevisionHistoryStoreError(
            f"artifact_type must be {INPUT_ARTIFACT_TYPE}"
        )
    if root.get("schema_version") != SCHEMA_VERSION:
        raise RevisionHistoryStoreError(f"schema_version must be {SCHEMA_VERSION}")
    if root.get("compile_dry_run_status") != "ok":
        raise RevisionHistoryStoreError("compile_dry_run_status must be 'ok'")

    candidate_count = root.get("candidate_count")
    if not isinstance(candidate_count, int) or candidate_count <= 0:
        raise RevisionHistoryStoreError("candidate_count must be > 0")

    changed_files = root.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        raise RevisionHistoryStoreError("changed_files must be a non-empty list")
    if any(not isinstance(f, str) or f not in ALLOWED_CHANGED_FILES for f in changed_files):
        raise RevisionHistoryStoreError("changed_files must contain canonical RelaySOUL file names only")

    revision_preview = root.get("revision_preview")
    _require_object(revision_preview, "revision_preview")

    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-revision-compile", required=True)
    parser.add_argument("--history-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_artifact = _validate_input_artifact(_read_json(args.temp_revision_compile))

    history_dir = Path(args.history_dir)
    history_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(UTC)
    created_at_utc = created_at.isoformat(timespec="microseconds").replace("+00:00", "Z")
    stable_prefix_hash_after = source_artifact.get("stable_prefix_hash_after")
    base_revision_id = _build_revision_id(created_at, stable_prefix_hash_after if isinstance(stable_prefix_hash_after, str) else None)
    revision_id, revision_path = _build_unique_revision_path(history_dir, base_revision_id)

    parent_revision_id = _resolve_parent_revision_id(history_dir)

    changed_files = list(source_artifact["changed_files"])
    warnings = source_artifact.get("warnings")
    warning_list = [w for w in warnings if isinstance(w, str)] if isinstance(warnings, list) else []

    revision_preview = source_artifact["revision_preview"]
    mode = revision_preview.get("mode") if isinstance(revision_preview.get("mode"), str) else "calibration"
    approval_required = (
        revision_preview.get("approval_required")
        if isinstance(revision_preview.get("approval_required"), bool)
        else True
    )

    revision_entry = {
        "revision_id": revision_id,
        "parent_revision_id": parent_revision_id,
        "created_at_utc": created_at_utc,
        "mode": mode,
        "changed_files": changed_files,
        "candidate_count": source_artifact["candidate_count"],
        "high_risk_candidate_count": source_artifact.get("high_risk_candidate_count", 0),
        "soul_patch_candidate_present": source_artifact.get("soul_patch_candidate_present", False),
        "stable_prefix_hash_before": source_artifact.get("stable_prefix_hash_before"),
        "stable_prefix_hash_after": source_artifact.get("stable_prefix_hash_after"),
        "stable_prefix_changed": source_artifact.get("stable_prefix_changed"),
        "compile_dry_run_status": source_artifact.get("compile_dry_run_status"),
        "source_artifact_type": source_artifact.get("artifact_type"),
        "source_schema_version": source_artifact.get("schema_version"),
        "rollback_available": True,
        "approval_required": approval_required,
        "warnings": warning_list,
        "content_free": True,
    }

    revision_path.write_text(json.dumps(revision_entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "history_dir": str(history_dir),
        "revision_path": str(revision_path),
        "revision_id": revision_id,
        "changed_files": changed_files,
        "warning_count": len(warning_list),
        "rollback_available": True,
        "content_free": True,
        "warnings": warning_list,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
