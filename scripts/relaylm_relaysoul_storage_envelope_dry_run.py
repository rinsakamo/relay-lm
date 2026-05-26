#!/usr/bin/env python3
"""Wrap a RelaySOUL content-free artifact in a storage envelope (dry-run)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_persistence import (
    ALLOWED_ARTIFACT_KINDS,
    build_relaysoul_artifact_persistence_dry_run,
    build_relaysoul_storage_envelope_dry_run,
)

SCHEMA_VERSION = "mvp-soul-0"
OUTPUT_ARTIFACT_TYPE = "relaysoul_storage_envelope_dry_run"


class StorageEnvelopeDryRunError(ValueError):
    """Raised when storage envelope dry-run inputs are invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StorageEnvelopeDryRunError(f"{field_name} JSON root must be an object")
    return value


def _validate_artifact_kind(artifact_kind: str) -> str:
    if artifact_kind not in ALLOWED_ARTIFACT_KINDS:
        supported = ", ".join(sorted(ALLOWED_ARTIFACT_KINDS))
        raise StorageEnvelopeDryRunError(
            f"unsupported artifact-kind: {artifact_kind}. supported: {supported}"
        )
    return artifact_kind


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--artifact-kind", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--character-id", default=None)
    parser.add_argument("--created-at", default=None)
    parser.add_argument("--source-commit-sha", default=None)
    parser.add_argument("--envelope-schema-version", default="v1")
    args = parser.parse_args()

    artifact_kind = _validate_artifact_kind(args.artifact_kind)
    artifact = _require_object(_read_json(args.artifact), "artifact")

    persistence = build_relaysoul_artifact_persistence_dry_run(artifact_kind, artifact)
    envelope = build_relaysoul_storage_envelope_dry_run(
        persistence,
        artifact,
        args.character_id,
        schema_version=args.envelope_schema_version,
        created_at=args.created_at,
        source_commit_sha=args.source_commit_sha,
    )

    if envelope.envelope_status == "blocked" and "payload_not_content_free" in envelope.blocking_reasons:
        raise StorageEnvelopeDryRunError("artifact content_free must be true for storage envelope dry-run")
    if envelope.envelope_status == "blocked" and "payload_contains_forbidden_content_keys" in envelope.blocking_reasons:
        raise StorageEnvelopeDryRunError("artifact contains forbidden content keys for storage envelope dry-run")

    output_payload = {
        "artifact_type": OUTPUT_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": artifact_kind,
        "artifact_id": persistence.artifact_id,
        "parent_artifact_id": persistence.parent_artifact_id,
        "persistence_status": persistence.persistence_status,
        "persistence_ready": persistence.persistence_ready,
        "warning_reasons": list(envelope.warning_reasons),
        "blocking_reasons": list(envelope.blocking_reasons),
        "envelope": envelope.envelope,
        "content_free": True,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except StorageEnvelopeDryRunError as exc:
        raise SystemExit(f"error: {exc}")
