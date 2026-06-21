"""RelayMEM M3e atomic Primary MEM page writer implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_page_writer_contract import parse_relaymem_primary_writer_handoff
from ._relaymem_primary_page_writer_io import (
    empty_primary_page_write_state,
    write_or_inspect_primary_page,
)

_RESULT_SCHEMA = "relaymem.primary_page_write_apply.v0"
_RECEIPT_SCHEMA = "relaymem.primary_page_write_receipt.v0"
_PROJECTION_SCHEMA = "relaymem.primary_page_write_projection.v0"


def apply_relaymem_primary_page_write(
    *,
    writer_handoff_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Validate and optionally atomically publish one Primary MEM page."""

    parsed = parse_relaymem_primary_writer_handoff(writer_handoff_artifact)
    reasons: list[str] = []
    if type(enabled) is not bool:
        reasons.append("primary_page_writer_enabled_invalid")
        enabled = False
    if type(dry_run_only) is not bool:
        reasons.append("primary_page_writer_dry_run_only_invalid")
        dry_run_only = True
    if type(apply_enabled) is not bool:
        reasons.append("primary_page_writer_apply_enabled_invalid")
        apply_enabled = False
    if not enabled:
        reasons.append("primary_page_writer_disabled")
    if parsed.get("valid") is not True:
        reasons.extend(_strings(parsed.get("blocked_reasons")))

    state = empty_primary_page_write_state()
    receipt: dict[str, Any] | None = None
    if not reasons:
        handoff = parsed["handoff"]
        state = write_or_inspect_primary_page(
            root_path=root_path,
            handoff=handoff,
            apply_requested=bool(apply_enabled and not dry_run_only),
        )
        reasons.extend(state["blocked_reasons"])
        if state["receipt_status"]:
            receipt = _build_receipt(handoff=handoff, state=state)

    reasons = _dedupe(reasons)
    status = _result_status(
        enabled=enabled,
        parsed_valid=parsed.get("valid") is True,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        state=state,
        reasons=reasons,
    )
    projection = _build_projection(
        status=status,
        handoff=parsed.get("handoff") if parsed.get("valid") is True else None,
        state=state,
        blocked_reasons=reasons,
    )
    return {
        "schema_version": _RESULT_SCHEMA,
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "write_apply_supported": True,
        "apply_requested": bool(enabled and apply_enabled and not dry_run_only),
        "handoff_valid": parsed.get("valid") is True,
        "status": status,
        "writes_memory": state["writes_memory"],
        "page_applied": state["page_applied"],
        "idempotent_noop": state["idempotent_noop"],
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "receipt": receipt,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _build_receipt(*, handoff: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _RECEIPT_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": handoff["candidate_id"],
        "namespace": handoff["namespace"],
        "source_event_kind": handoff["source_event_kind"],
        "memory_layer": "primary",
        "memory_kind": handoff["memory_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": handoff["target_category"],
        "target_relative_path": handoff["target_relative_path"],
        "lineage_fingerprint": handoff["lineage_fingerprint"],
        "idempotency_key": handoff["idempotency_key"],
        "page_bytes": handoff["page_bytes"],
        "page_digest": handoff["page_digest"],
        "status": state["receipt_status"],
        "writes_memory": state["writes_memory"],
        "page_applied": state["page_applied"],
        "idempotent_noop": state["idempotent_noop"],
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "updates_index": False,
        "updates_log": False,
    }


def _build_projection(
    *,
    status: str,
    handoff: Mapping[str, Any] | None,
    state: Mapping[str, Any],
    blocked_reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "candidate_id_included": False,
        "namespace_included": False,
        "target_path_included": False,
        "lineage_fingerprint_included": False,
        "idempotency_key_included": False,
        "page_markdown_included": False,
        "page_digest_included": False,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "status": status,
        "handoff_valid": handoff is not None,
        "target_category": handoff.get("target_category", "unknown") if handoff else "unknown",
        "memory_kind": handoff.get("memory_kind", "unknown") if handoff else "unknown",
        "page_bytes": handoff.get("page_bytes", 0) if handoff else 0,
        "writes_memory": state["writes_memory"],
        "page_applied": state["page_applied"],
        "idempotent_noop": state["idempotent_noop"],
        "durability_confirmed": state["durability_confirmed"],
        "cleanup_complete": state["cleanup_complete"],
        "updates_index": False,
        "updates_log": False,
        "blocked_reasons": list(blocked_reasons),
    }


def _result_status(
    *,
    enabled: bool,
    parsed_valid: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    state: Mapping[str, Any],
    reasons: Sequence[str],
) -> str:
    if not enabled:
        return "disabled"
    if not parsed_valid:
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


__all__ = ["apply_relaymem_primary_page_write"]
