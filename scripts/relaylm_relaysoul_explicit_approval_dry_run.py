#!/usr/bin/env python3
"""Generate RelaySOUL explicit approval artifact (dry-run, content-free)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_persistence import FORBIDDEN_PAYLOAD_KEYS

SCHEMA_VERSION = "mvp-soul-0"
ARTIFACT_TYPE = "relaysoul_explicit_approval_artifact"
ALLOWED_SCOPE = {"apply_execution", "rollback_execution", "storage_writer", "persistence_execution"}
ALLOWED_STATUS = {"approved", "blocked"}
ALLOWED_APPROVER_KIND = {"user", "operator", "system_test"}
ALLOWED_EXEC_PREFLIGHT = {"apply", "rollback", "null"}


class ExplicitApprovalDryRunError(ValueError):
    pass


def _require_non_empty_string(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplicitApprovalDryRunError(f"{field} must be non-empty string")
    return value


def _require_safe_component(value: str | None, field: str) -> str:
    text = _require_non_empty_string(value, field)
    if text in {".", ".."} or "/" in text or "\\" in text or "\x00" in text:
        raise ExplicitApprovalDryRunError(f"{field} must be safe single path component")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-scope", required=True)
    parser.add_argument("--approval-status", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--approver-kind", required=True)
    parser.add_argument("--approved-at", required=True)
    parser.add_argument("--target-gate-artifact-type", required=True)
    parser.add_argument("--target-artifact-kind", required=True)
    parser.add_argument("--target-artifact-id", required=True)
    parser.add_argument("--parent-artifact-id")
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--execution-preflight-type", default="null")
    parser.add_argument("--referenced-preflight-id", action="append", default=[])
    parser.add_argument("--referenced-gate-id", action="append", default=[])
    parser.add_argument("--approval-reason-code", action="append", default=[])
    parser.add_argument("--blocking-reason", action="append", default=[])
    parser.add_argument("--warning", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.approval_scope not in ALLOWED_SCOPE:
        raise ExplicitApprovalDryRunError("approval_scope must be one of allowlist")
    if args.approval_status not in ALLOWED_STATUS:
        raise ExplicitApprovalDryRunError("approval_status must be one of allowlist")
    if args.approver_kind not in ALLOWED_APPROVER_KIND:
        raise ExplicitApprovalDryRunError("approver_kind must be one of allowlist")
    if args.execution_preflight_type not in ALLOWED_EXEC_PREFLIGHT:
        raise ExplicitApprovalDryRunError("execution_preflight_type must be apply, rollback, or null")

    approval_id = _require_safe_component(args.approval_id, "approval_id")
    target_artifact_id = _require_safe_component(args.target_artifact_id, "target_artifact_id")
    character_id = _require_safe_component(args.character_id, "character_id")
    target_artifact_kind = _require_safe_component(args.target_artifact_kind, "target_artifact_kind")

    parent_artifact_id = None
    if args.parent_artifact_id is not None:
        parent_artifact_id = _require_safe_component(args.parent_artifact_id, "parent_artifact_id")

    approved_at = _require_non_empty_string(args.approved_at, "approved_at")
    target_gate_artifact_type = _require_non_empty_string(args.target_gate_artifact_type, "target_gate_artifact_type")

    blocking_reasons = [b for b in args.blocking_reason if isinstance(b, str) and b.strip()]
    if args.approval_status == "approved" and blocking_reasons:
        raise ExplicitApprovalDryRunError("blocking_reasons must be empty when approval_status is approved")

    for field, values in {
        "referenced_preflight_ids": args.referenced_preflight_id,
        "referenced_gate_ids": args.referenced_gate_id,
        "approval_reason_codes": args.approval_reason_code,
        "warnings": args.warning,
        "blocking_reasons": blocking_reasons,
    }.items():
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ExplicitApprovalDryRunError(f"{field} entries must be non-empty strings")
            forbidden_key_hits = [key for key in FORBIDDEN_PAYLOAD_KEYS if key in value]
            if forbidden_key_hits:
                raise ExplicitApprovalDryRunError(f"{field} contains forbidden content key token")

    execution_preflight_type: str | None
    execution_preflight_type = None if args.execution_preflight_type == "null" else args.execution_preflight_type

    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "content_free": True,
        "approval_status": args.approval_status,
        "approval_scope": args.approval_scope,
        "approval_id": approval_id,
        "approver_kind": args.approver_kind,
        "approved_at": approved_at,
        "target_gate_artifact_type": target_gate_artifact_type,
        "target_artifact_kind": target_artifact_kind,
        "target_artifact_id": target_artifact_id,
        "parent_artifact_id": parent_artifact_id,
        "character_id": character_id,
        "execution_preflight_type": execution_preflight_type,
        "referenced_preflight_ids": list(args.referenced_preflight_id),
        "referenced_gate_ids": list(args.referenced_gate_id),
        "approval_reason_codes": list(args.approval_reason_code),
        "blocking_reasons": list(blocking_reasons),
        "warnings": [w for w in args.warning if isinstance(w, str) and w.strip()],
    }

    forbidden_hits = [key for key in FORBIDDEN_PAYLOAD_KEYS if key in artifact]
    if forbidden_hits:
        raise ExplicitApprovalDryRunError("artifact contains forbidden top-level key")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except ExplicitApprovalDryRunError as exc:
        raise SystemExit(f"error: {exc}")
