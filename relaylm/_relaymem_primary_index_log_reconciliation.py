"""RelayMEM M3f read-only Primary MEM index/log reconciliation preflight."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_index_log_reconciliation_contract import (
    parse_m3e_receipt,
    verify_primary_page,
)
from ._relaymem_primary_index_log_reconciliation_io import read_store_file
from ._relaymem_primary_index_log_reconciliation_plan import (
    INDEX_PATH,
    LOG_PATH,
    MAX_INDEX_LOG_BYTES,
    build_index_plan,
    build_log_plan,
    operation,
)
from ._relaymem_primary_page_writer_common import MAX_PAGE_BYTES

_RESULT_SCHEMA = "relaymem.primary_index_log_reconciliation_preflight.v0"
_PLAN_SCHEMA = "relaymem.primary_index_log_reconciliation_plan.v0"
_PROJECTION_SCHEMA = "relaymem.primary_index_log_reconciliation_projection.v0"


def build_relaymem_primary_index_log_reconciliation_preflight(
    *,
    receipt: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
) -> dict[str, Any]:
    reasons: list[str] = []
    gates_valid = True
    if type(enabled) is not bool:
        reasons.append("primary_reconciliation_enabled_invalid")
        gates_valid = False
        enabled = False
    if type(dry_run_only) is not bool:
        reasons.append("primary_reconciliation_dry_run_only_invalid")
        gates_valid = False
        dry_run_only = True
    if not enabled:
        reasons.append("primary_reconciliation_disabled")
    if not dry_run_only:
        reasons.append("primary_reconciliation_dry_run_required")

    parsed = parse_m3e_receipt(receipt)
    if parsed.get("valid") is not True:
        reasons.extend(parsed["blocked_reasons"])

    page_verified = False
    index_required = False
    log_required = False
    index_conflicts = 0
    log_conflicts = 0
    plan: dict[str, Any] | None = None
    state = "blocked"

    if gates_valid and enabled and dry_run_only and parsed.get("valid") is True:
        receipt_value = parsed["receipt"]
        page = read_store_file(
            root_path=root_path,
            relative_path=receipt_value["target_relative_path"],
            max_bytes=MAX_PAGE_BYTES,
            role="page",
        )
        if page.get("status") == "missing":
            reasons.append("primary_reconciliation_page_missing")
            state = "page_missing"
        elif page.get("valid") is not True:
            reasons.extend(page["blocked_reasons"])
            state = "page_mismatch"
        else:
            page_reasons = verify_primary_page(receipt_value, page["content"])
            if page_reasons:
                reasons.extend(page_reasons)
                state = "page_mismatch"
            else:
                page_verified = True
                index_file = read_store_file(
                    root_path=root_path,
                    relative_path=INDEX_PATH,
                    max_bytes=MAX_INDEX_LOG_BYTES,
                    role="index",
                )
                log_file = read_store_file(
                    root_path=root_path,
                    relative_path=LOG_PATH,
                    max_bytes=MAX_INDEX_LOG_BYTES,
                    role="log",
                )
                if index_file.get("valid") is not True:
                    reasons.extend(index_file["blocked_reasons"])
                if log_file.get("valid") is not True:
                    reasons.extend(log_file["blocked_reasons"])
                if index_file.get("valid") is True and log_file.get("valid") is True:
                    index_plan = build_index_plan(receipt_value, index_file["content"])
                    log_plan = build_log_plan(
                        receipt_value,
                        log_file["content"],
                        index_plan["entry_identity"],
                    )
                    index_conflicts = int(index_plan["conflict"])
                    log_conflicts = int(log_plan["conflict"])
                    if index_plan["conflict"]:
                        reasons.append("primary_reconciliation_index_conflict")
                        state = "index_conflict"
                    elif log_plan["conflict"]:
                        reasons.append("primary_reconciliation_log_conflict")
                        state = "log_conflict"
                    else:
                        index_required = not index_plan["idempotent_noop"]
                        log_required = not log_plan["idempotent_noop"]
                        state = _reconciliation_state(index_required, log_required)
                        operations: list[dict[str, Any]] = []
                        if index_required:
                            operations.append(operation(index_plan, len(operations)))
                        if log_required:
                            operations.append(operation(log_plan, len(operations)))
                        plan = {
                            "schema_version": _PLAN_SCHEMA,
                            "runtime_private": True,
                            "read_only": True,
                            "dry_run_only": True,
                            "reconciliation_state": state,
                            "plan_ready": True,
                            "page": {
                                "target_relative_path": receipt_value[
                                    "target_relative_path"
                                ],
                                "page_bytes": receipt_value["page_bytes"],
                                "page_digest": receipt_value["page_digest"],
                                "idempotency_key": receipt_value["idempotency_key"],
                                "memory_kind": receipt_value["memory_kind"],
                                "target_category": receipt_value["target_category"],
                            },
                            "index_plan": index_plan,
                            "log_plan": log_plan,
                            "ordered_operations": operations,
                            "operation_count": len(operations),
                            "writes_memory": False,
                            "updates_index": False,
                            "updates_log": False,
                        }

    reasons = _dedupe(reasons)
    projection = _build_projection(
        status=state,
        receipt_valid=parsed.get("valid") is True,
        page_verified=page_verified,
        plan_ready=plan is not None,
        index_required=index_required,
        log_required=log_required,
        index_conflicts=index_conflicts,
        log_conflicts=log_conflicts,
        operation_count=plan["operation_count"] if plan else 0,
        memory_kind=parsed.get("receipt", {}).get("memory_kind", "unknown"),
        target_category=parsed.get("receipt", {}).get(
            "target_category", "unknown"
        ),
        reasons=reasons,
    )
    return {
        "schema_version": _RESULT_SCHEMA,
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_plan": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "receipt_valid": parsed.get("valid") is True,
        "page_verified": page_verified,
        "status": state,
        "preflight_status": "ready" if plan is not None else "blocked",
        "index_update_required": index_required,
        "log_update_required": log_required,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "plan": plan,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _reconciliation_state(index_required: bool, log_required: bool) -> str:
    if index_required and log_required:
        return "index_and_log_update_required"
    if index_required:
        return "index_update_required"
    if log_required:
        return "log_update_required"
    return "already_reconciled"


def _build_projection(
    *,
    status: str,
    receipt_valid: bool,
    page_verified: bool,
    plan_ready: bool,
    index_required: bool,
    log_required: bool,
    index_conflicts: int,
    log_conflicts: int,
    operation_count: int,
    memory_kind: str,
    target_category: str,
    reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "target_path_included": False,
        "namespace_included": False,
        "idempotency_key_included": False,
        "page_digest_included": False,
        "entry_content_included": False,
        "proposed_content_included": False,
        "reconciliation_status": status,
        "preflight_status": "ready" if plan_ready else "blocked",
        "receipt_valid": receipt_valid,
        "page_verified": page_verified,
        "plan_ready": plan_ready,
        "index_update_required": index_required,
        "log_update_required": log_required,
        "conflict_counts": {"index": index_conflicts, "log": log_conflicts},
        "operation_count": operation_count,
        "memory_kind": memory_kind,
        "target_category": target_category,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "blocked_reasons": list(reasons),
    }


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["build_relaymem_primary_index_log_reconciliation_preflight"]
