"""RelayMEM M3h Primary MEM index/log recovery audit boundary."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_index_log_recovery_audit_contract import (
    parse_m3g_reconciliation_receipt,
)
from ._relaymem_primary_index_log_recovery_audit_io import (
    empty_recovery_store_state,
    inspect_reconciliation_recovery_store,
)

_RESULT_SCHEMA = "relaymem.primary_index_log_reconciliation_recovery_audit_result.v0"
_AUDIT_SCHEMA = "relaymem.primary_index_log_reconciliation_recovery_audit.v0"
_PROJECTION_SCHEMA = "relaymem.primary_index_log_reconciliation_recovery_projection.v0"
_UNCERTAIN_STATUSES = {
    "applied_durability_unconfirmed",
    "applied_cleanup_incomplete",
    "applied_state_uncertain",
}


def audit_relaymem_primary_index_log_reconciliation_recovery(
    *,
    receipt: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
) -> dict[str, Any]:
    """Read and classify one exact M3g receipt against current store state."""

    reasons: list[str] = []
    gates_valid = True
    if type(enabled) is not bool:
        reasons.append("primary_reconciliation_recovery_enabled_invalid")
        gates_valid = False
        enabled = False
    if type(dry_run_only) is not bool or dry_run_only is not True:
        reasons.append("primary_reconciliation_recovery_dry_run_only_invalid")
        gates_valid = False
        dry_run_only = True
    if not enabled:
        reasons.append("primary_reconciliation_recovery_disabled")

    parsed = parse_m3g_reconciliation_receipt(receipt)
    if parsed.get("valid") is not True:
        reasons.extend(_strings(parsed.get("blocked_reasons")))
    private_receipt = parsed.get("receipt") if parsed.get("valid") is True else None
    store = empty_recovery_store_state()
    if gates_valid and enabled and isinstance(private_receipt, Mapping):
        store = inspect_reconciliation_recovery_store(
            root_path=root_path, receipt=private_receipt
        )
        reasons.extend(_strings(store.get("blocked_reasons")))

    reasons = _dedupe(reasons)
    classification = _classification(private_receipt, store, reasons)
    status = (
        "blocked"
        if not gates_valid or (enabled and (private_receipt is None or reasons))
        else "disabled"
        if not enabled
        else classification
    )
    audit = (
        _build_audit(private_receipt, store, classification)
        if enabled and isinstance(private_receipt, Mapping)
        else None
    )
    projection = _build_projection(
        status=status,
        receipt_valid=private_receipt is not None,
        source_status=(str(private_receipt["status"]) if private_receipt else "unknown"),
        store=store,
        classification=classification,
        reasons=reasons,
    )
    return {
        "schema_version": _RESULT_SCHEMA,
        "helper_only": True,
        "runtime_private_audit": True,
        "enabled": bool(enabled),
        "dry_run_only": True,
        "read_only": True,
        "audit_supported": True,
        "receipt_valid": private_receipt is not None,
        "status": status,
        "source_status": str(private_receipt["status"]) if private_receipt else "unknown",
        "store_state": store["store_state"],
        "recovery_classification": classification,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "creates_journal": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "audit": audit,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _classification(
    receipt: Mapping[str, Any] | None,
    store: Mapping[str, Any],
    reasons: Sequence[str],
) -> str:
    if receipt is None or store.get("store_state") == "not_evaluated":
        return "not_evaluated"
    source_status = str(receipt["status"])
    store_state = str(store["store_state"])
    cleanup_present = store.get("cleanup_artifacts_present") is True
    if reasons:
        if source_status in _UNCERTAIN_STATUSES or source_status == "index_applied_log_pending":
            return "journaled_recovery_candidate"
        return "manual_confirmation_required"
    if cleanup_present:
        return "journaled_recovery_candidate"
    if store_state == "fully_reconciled":
        if source_status in _UNCERTAIN_STATUSES:
            return "manual_confirmation_required"
        return "recovery_not_required"
    if store_state == "index_applied_log_pending":
        return "retry_reconciliation"
    if store_state == "not_applied":
        if source_status in {"dry_run_ready", "blocked"} and receipt.get("writes_memory") is False:
            return "recovery_not_required"
        return (
            "journaled_recovery_candidate"
            if source_status in _UNCERTAIN_STATUSES
            else "manual_confirmation_required"
        )
    if store_state == "log_applied_index_pending":
        if source_status == "dry_run_ready" and receipt.get("writes_memory") is False:
            return "recovery_not_required"
        return (
            "journaled_recovery_candidate"
            if source_status in _UNCERTAIN_STATUSES
            else "manual_confirmation_required"
        )
    if source_status in _UNCERTAIN_STATUSES or source_status == "index_applied_log_pending":
        return "journaled_recovery_candidate"
    return "manual_confirmation_required"


def _build_audit(
    receipt: Mapping[str, Any], store: Mapping[str, Any], classification: str
) -> dict[str, Any]:
    return {
        "schema_version": _AUDIT_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "source_status": receipt["status"],
        "reconciliation_state": receipt["reconciliation_state"],
        "page_relative_path": receipt["page_relative_path"],
        "page_digest": receipt["page_digest"],
        "idempotency_key": receipt["idempotency_key"],
        "index_entry_identity": receipt["index_entry_identity"],
        "log_entry_identity": receipt["log_entry_identity"],
        "page_state": store["page_state"],
        "index_state": store["index_state"],
        "log_state": store["log_state"],
        "store_state": store["store_state"],
        "cleanup_artifact_count": store["cleanup_artifact_count"],
        "recovery_classification": classification,
        "retry_requires_exact_plan_or_fresh_preflight": classification
        == "retry_reconciliation",
        "journal_created": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
    }


def _build_projection(
    *,
    status: str,
    receipt_valid: bool,
    source_status: str,
    store: Mapping[str, Any],
    classification: str,
    reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "target_paths_included": False,
        "namespace_included": False,
        "idempotency_key_included": False,
        "digests_included": False,
        "entry_identities_included": False,
        "file_content_included": False,
        "os_exception_text_included": False,
        "status": status,
        "receipt_valid": receipt_valid,
        "source_status": source_status,
        "store_state": store["store_state"],
        "page_verified": store["page_state"] == "verified",
        "index_state": store["index_state"],
        "log_state": store["log_state"],
        "cleanup_artifacts_present": store["cleanup_artifacts_present"],
        "recovery_classification": classification,
        "retryable": classification == "retry_reconciliation",
        "manual_confirmation_required": classification
        == "manual_confirmation_required",
        "journaled_recovery_candidate": classification
        == "journaled_recovery_candidate",
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "blocked_reasons": list(reasons),
    }


def _strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["audit_relaymem_primary_index_log_reconciliation_recovery"]
