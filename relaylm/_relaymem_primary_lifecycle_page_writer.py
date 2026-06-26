"""I-4C1 hidden-page validation adapter for the existing M3e atomic I/O.

This is not a second writer: publication delegates to the same
``write_or_inspect_primary_page`` authority used by ordinary M3e pages.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from . import _relaymem_primary_page_writer_impl as _active
from ._relaymem_primary_page_writer_common import (
    KIND_TARGET,
    TARGET_DIR,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)
from ._relaymem_primary_page_writer_io import (
    empty_primary_page_write_state,
    write_or_inspect_primary_page,
)
from .relaymem_primary_lifecycle_page import (
    HIDDEN_PAGE_BODY,
    validate_hidden_primary_metadata,
)

_RESULT_FIELDS = {
    "schema_version", "diagnostics_only", "helper_only", "read_only",
    "runtime_private_handoffs", "enabled", "dry_run_only", "apply_enabled",
    "write_apply_supported", "apply_allowed", "writes_memory", "updates_index",
    "updates_log", "mutates_soul", "invokes_slp", "lab_api_exposed",
    "runtime_wired", "visible_response_changed", "store_root_configured",
    "page_candidate_valid", "handoff_count", "handoffs", "blocked_reasons",
    "projection",
}
_HANDOFF_FIELDS = {
    "schema_version", "runtime_private", "content_included",
    "raw_source_text_included", "raw_message_history_included",
    "raw_affect_estimates_included", "candidate_id", "source_event_kind",
    "memory_layer", "memory_kind", "promotion_policy", "safety_scope",
    "namespace", "target_category", "target_relative_path",
    "lineage_fingerprint", "idempotency_key", "page_markdown", "page_bytes",
    "page_digest", "preflight_status", "target_exists", "target_digest_matches",
    "idempotent_noop", "upstream_writer_handoff_eligible",
    "writer_apply_eligible", "writes_memory", "updates_index", "updates_log",
    "applied", "blocked_reasons",
}


def is_hidden_lifecycle_handoff(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    handoffs = value.get("handoffs")
    if not isinstance(handoffs, Sequence) or isinstance(handoffs, (str, bytes)):
        return False
    if len(handoffs) != 1 or not isinstance(handoffs[0], Mapping):
        return False
    markdown = handoffs[0].get("page_markdown")
    if not isinstance(markdown, str):
        return False
    parsed = parse_page_markdown(markdown)
    return (
        parsed.get("valid") is True
        and isinstance(parsed.get("metadata"), Mapping)
        and parsed["metadata"].get("lifecycle_state") == "hidden"
    )


def apply_hidden_lifecycle_page_write(
    *,
    writer_handoff_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
) -> dict[str, Any]:
    parsed = _parse(writer_handoff_artifact)
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
        reasons.extend(parsed.get("blocked_reasons", []))

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
            receipt = _active._build_receipt(handoff=handoff, state=state)

    reasons = list(dict.fromkeys(reason for reason in reasons if reason))
    status = _active._result_status(
        enabled=enabled,
        parsed_valid=parsed.get("valid") is True,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        state=state,
        reasons=reasons,
    )
    projection = _active._build_projection(
        status=status,
        handoff=parsed.get("handoff") if parsed.get("valid") is True else None,
        state=state,
        blocked_reasons=reasons,
    )
    return {
        "schema_version": "relaymem.primary_page_write_apply.v0",
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


def _parse(value: Mapping[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(value, Mapping):
        return _invalid("primary_writer_handoff_artifact_missing")
    if set(value) != _RESULT_FIELDS or value.get("schema_version") != "relaymem.primary_writer_handoff_preflight.v0":
        return _invalid("primary_writer_handoff_artifact_fields_mismatch")
    expected_result = {
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_handoffs": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "store_root_configured": True,
        "page_candidate_valid": True,
        "handoff_count": 1,
    }
    for key, expected in expected_result.items():
        if not _exact(value.get(key), expected):
            reasons.append(f"primary_writer_handoff_artifact_{key}_invalid")
    if value.get("blocked_reasons") != []:
        reasons.append("primary_writer_handoff_artifact_blocked")
    handoffs = value.get("handoffs")
    if not isinstance(handoffs, Sequence) or isinstance(handoffs, (str, bytes)) or len(handoffs) != 1 or not isinstance(handoffs[0], Mapping):
        return _invalid(*(reasons + ["primary_writer_handoff_cardinality_invalid"]))
    handoff = dict(handoffs[0])
    reasons.extend(_validate_handoff(handoff))
    return _invalid(*reasons) if reasons else {"valid": True, "handoff": handoff, "blocked_reasons": []}


def _validate_handoff(value: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if set(value) != _HANDOFF_FIELDS or value.get("schema_version") != "relaymem.primary_writer_handoff.v0":
        return ["primary_writer_handoff_fields_mismatch"]
    variant = value.get("preflight_status")
    variants = {
        "ready": (False, False, False, True),
        "already_applied": (True, True, True, False),
    }
    if variant not in variants:
        return ["primary_writer_handoff_preflight_status_invalid"]
    exists, matches, noop, eligible = variants[str(variant)]
    expected = {
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_exists": exists,
        "target_digest_matches": matches,
        "idempotent_noop": noop,
        "upstream_writer_handoff_eligible": True,
        "writer_apply_eligible": eligible,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "applied": False,
        "blocked_reasons": [],
    }
    for key, wanted in expected.items():
        if not _exact(value.get(key), wanted):
            reasons.append(f"primary_writer_handoff_{key}_invalid")
    candidate = value.get("candidate_id")
    namespace = value.get("namespace")
    event = value.get("source_event_kind")
    kind = value.get("memory_kind")
    lineage = value.get("lineage_fingerprint")
    physical = value.get("idempotency_key")
    if not _token(candidate) or not _token(namespace) or not _token(event):
        reasons.append("primary_writer_handoff_token_invalid")
    if kind not in KIND_TARGET or not is_sha256(lineage) or not is_sha256(physical):
        reasons.append("primary_writer_handoff_identity_invalid")
    if not reasons:
        expected_physical = stable_hash((
            "relaymem-primary-write-preflight-v0", str(namespace), str(event),
            str(lineage), str(candidate), str(event), "primary", str(kind),
            "free_to_update",
        ))
        if physical != expected_physical:
            reasons.append("primary_writer_handoff_idempotency_key_mismatch")
    category = KIND_TARGET.get(str(kind))
    expected_path = f"{TARGET_DIR[category]}/{physical}.md" if category and is_sha256(physical) else ""
    if value.get("target_category") != category or value.get("target_relative_path") != expected_path:
        reasons.append("primary_writer_handoff_target_path_mismatch")
    markdown = value.get("page_markdown")
    try:
        encoded = markdown.encode("utf-8") if isinstance(markdown, str) else b""
    except UnicodeEncodeError:
        encoded = b""
    if not encoded or value.get("page_bytes") != len(encoded) or value.get("page_digest") != sha256(encoded).hexdigest():
        reasons.append("primary_writer_handoff_page_digest_mismatch")
    parsed = parse_page_markdown(markdown if isinstance(markdown, str) else "")
    if (
        parsed.get("valid") is not True
        or parsed.get("body") != HIDDEN_PAGE_BODY
        or not validate_hidden_primary_metadata(
            parsed.get("metadata"),
            expected_namespace=str(namespace) if isinstance(namespace, str) else None,
            expected_memory_kind=str(kind) if isinstance(kind, str) else None,
            expected_source_event_kind=str(event) if isinstance(event, str) else None,
            expected_lineage_fingerprint=str(lineage) if isinstance(lineage, str) else None,
            expected_physical_id=str(physical) if isinstance(physical, str) else None,
        )
    ):
        reasons.append("primary_writer_handoff_hidden_page_invalid")
    return list(dict.fromkeys(reasons))


def _exact(actual: object, expected: object) -> bool:
    return type(actual) is bool and actual is expected if isinstance(expected, bool) else actual == expected


def _token(value: object) -> bool:
    return isinstance(value, str) and value == value.strip() and 0 < len(value) <= 128 and not any(char in value for char in "\r\n\t\x00")


def _invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": list(dict.fromkeys(reason for reason in reasons if reason))}


__all__ = ["apply_hidden_lifecycle_page_write", "is_hidden_lifecycle_handoff"]
