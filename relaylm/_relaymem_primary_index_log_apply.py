"""RelayMEM M3g Primary MEM index/log reconciliation apply boundary."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_index_log_apply_contract import (
    parse_m3f_reconciliation_plan,
    verify_m3g_page,
)
from ._relaymem_primary_index_log_apply_io import (
    apply_or_inspect_reconciliation,
    empty_reconciliation_apply_state,
)
from ._relaymem_primary_index_log_reconciliation_io import read_store_file
from ._relaymem_primary_page_writer_common import MAX_PAGE_BYTES

_RESULT_SCHEMA = "relaymem.primary_index_log_reconciliation_apply.v0"
_RECEIPT_SCHEMA = "relaymem.primary_index_log_reconciliation_receipt.v0"
_PROJECTION_SCHEMA = "relaymem.primary_index_log_reconciliation_apply_projection.v0"


def apply_relaymem_primary_index_log_reconciliation(
    *,
    plan_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Validate and optionally apply one exact M3f reconciliation plan."""

    reasons: list[str] = []
    gates_valid = True
    if type(enabled) is not bool:
        reasons.append("primary_reconciliation_apply_enabled_invalid")
        gates_valid = False
        enabled = False
    if type(dry_run_only) is not bool:
        reasons.append("primary_reconciliation_apply_dry_run_only_invalid")
        gates_valid = False
        dry_run_only = True
    if type(apply_enabled) is not bool:
        reasons.append("primary_reconciliation_apply_apply_enabled_invalid")
        gates_valid = False
        apply_enabled = False
    if not enabled:
        reasons.append("primary_reconciliation_apply_disabled")

    parsed = parse_m3f_reconciliation_plan(plan_artifact)
    if parsed.get("valid") is not True:
        reasons.extend(_strings(parsed.get("blocked_reasons")))

    page_verified = False
    state = empty_reconciliation_apply_state()
    receipt: dict[str, Any] | None = None
    plan = parsed.get("plan") if parsed.get("valid") is True else None
    if gates_valid and enabled and isinstance(plan, Mapping):
        page_plan = plan["page"]
        page = read_store_file(
            root_path=root_path,
            relative_path=page_plan["target_relative_path"],
            max_bytes=MAX_PAGE_BYTES,
            role="page",
        )
        if page.get("status") == "missing":
            reasons.append("primary_reconciliation_apply_page_missing")
        elif page.get("valid") is not True:
            reasons.extend(_strings(page.get("blocked_reasons")))
        else:
            page_reasons = verify_m3g_page(
                page_plan,
                page["content"],
                index_entry=parsed["index_entry"],
                log_entry=parsed["log_entry"],
            )
            if page_reasons:
                reasons.extend(page_reasons)
            else:
                page_verified = True

        if page_verified:
            state = apply_or_inspect_reconciliation(
                root_path=root_path,
                plan=plan,
                apply_requested=bool(apply_enabled and not dry_run_only),
            )
            reasons.extend(_strings(state.get("blocked_reasons")))
            if state["receipt_status"]:
                receipt = _build_receipt(plan=plan, state=state)

    reasons = _dedupe(reasons)
    status = _result_status(
        enabled=enabled,
        gates_valid=gates_valid,
        plan_valid=parsed.get("valid") is True,
        page_verified=page_verified,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        state=state,
        reasons=reasons,
    )
    apply_requested = bool(
        gates_valid and enabled and apply_enabled and not dry_run_only
    )
    projection = _build_projection(
        status=status,
        plan=plan,
        page_verified=page_verified,
        state=state,
        reasons=reasons,
        apply_requested=apply_requested,
    )
    return {
        "schema_version": _RESULT_SCHEMA,
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "apply_supported": True,
        "apply_requested": apply_requested,
        "plan_valid": parsed.get("valid") is True,
        "page_verified": page_verified,
        "status": status,
        "writes_memory": state["writes_memory"],
        "index_reconciled": state["index_reconciled"],
        "log_reconciled": state["log_reconciled"],
        "index_updated": state["index_updated"],
        "log_updated": state["log_updated"],
        "index_idempotent_noop": state["index_idempotent_noop"],
        "log_idempotent_noop": state["log_idempotent_noop"],
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "updates_index": state["index_updated"],
        "updates_log": state["log_updated"],
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "receipt": receipt,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _build_receipt(
    *, plan: Mapping[str, Any], state: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": _RECEIPT_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "reconciliation_state": plan["reconciliation_state"],
        "page_relative_path": plan["page"]["target_relative_path"],
        "page_digest": plan["page"]["page_digest"],
        "idempotency_key": plan["page"]["idempotency_key"],
        "index_entry_identity": plan["index_plan"]["entry_identity"],
        "log_entry_identity": plan["log_plan"]["entry_identity"],
        "index_expected_digest": plan["index_plan"]["expected_current_digest"],
        "index_proposed_digest": plan["index_plan"]["proposed_next_digest"],
        "log_expected_digest": plan["log_plan"]["expected_current_digest"],
        "log_proposed_digest": plan["log_plan"]["proposed_next_digest"],
        "status": state["receipt_status"],
        "writes_memory": state["writes_memory"],
        "index_reconciled": state["index_reconciled"],
        "log_reconciled": state["log_reconciled"],
        "index_updated": state["index_updated"],
        "log_updated": state["log_updated"],
        "index_idempotent_noop": state["index_idempotent_noop"],
        "log_idempotent_noop": state["log_idempotent_noop"],
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "operation_count": plan["operation_count"],
        "updates_index": state["index_updated"],
        "updates_log": state["log_updated"],
    }


def _build_projection(
    *,
    status: str,
    plan: Mapping[str, Any] | None,
    page_verified: bool,
    state: Mapping[str, Any],
    reasons: Sequence[str],
    apply_requested: bool,
) -> dict[str, Any]:
    reconciliation_state = (
        str(plan.get("reconciliation_state")) if plan is not None else "unknown"
    )
    return {
        "schema_version": _PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "target_paths_included": False,
        "namespace_included": False,
        "idempotency_key_included": False,
        "page_digest_included": False,
        "control_digests_included": False,
        "entry_identities_included": False,
        "proposed_content_included": False,
        "status": status,
        "reconciliation_state": reconciliation_state,
        "plan_valid": plan is not None,
        "page_verified": page_verified,
        "apply_requested": apply_requested,
        "writes_memory": state["writes_memory"],
        "index_reconciled": state["index_reconciled"],
        "log_reconciled": state["log_reconciled"],
        "index_updated": state["index_updated"],
        "log_updated": state["log_updated"],
        "idempotent_noop_count": int(state["index_idempotent_noop"])
        + int(state["log_idempotent_noop"]),
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "conflict_count": sum("conflict" in reason for reason in reasons),
        "blocked_reasons": list(reasons),
    }


def _result_status(
    *,
    enabled: bool,
    gates_valid: bool,
    plan_valid: bool,
    page_verified: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    state: Mapping[str, Any],
    reasons: Sequence[str],
) -> str:
    if not enabled:
        return "disabled"
    if not gates_valid or not plan_valid or not page_verified:
        return "blocked"
    if state["receipt_status"]:
        return str(state["receipt_status"])
    if reasons:
        return "blocked"
    if dry_run_only or not apply_enabled:
        return "dry_run_ready"
    return "blocked"


def _strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["apply_relaymem_primary_index_log_reconciliation"]
