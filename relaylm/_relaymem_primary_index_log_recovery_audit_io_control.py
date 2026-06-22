"""Index/log verification helpers for RelayMEM M3h."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from ._relaymem_primary_index_log_reconciliation_plan import (
    _parse_markers,
    _valid_existing_entry,
)


def apply_control_result(
    state: dict[str, Any], result: Mapping[str, Any], receipt: Mapping[str, Any], role: str
) -> None:
    if result.get("valid") is not True:
        state[f"{role}_state"] = "missing" if result.get("status") == "missing" else "invalid"
        state["blocked_reasons"].extend(result.get("blocked_reasons", []))
        return
    content = result["content"]
    digest = sha256(content).hexdigest()
    expected_digest = receipt[f"{role}_expected_digest"]
    proposed_digest = receipt[f"{role}_proposed_digest"]
    current_state = "proposed" if digest == proposed_digest else "expected" if digest == expected_digest else "diverged"
    state[f"{role}_state"] = current_state
    marker = f"relaymem-primary-{role}-entry-v0"
    header = "# Index" if role == "index" else "# Log"
    parsed = _parse_markers(content, marker, header)
    if parsed.get("valid") is not True or any(
        not _valid_existing_entry(marker, entry) for entry in parsed.get("entries", [])
    ):
        state[f"{role}_state"] = "invalid"
        state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_contract_invalid")
        return
    matches = [
        entry for entry in parsed["entries"]
        if entry.get("entry_id") == receipt[f"{role}_entry_identity"]
    ]
    target_expected = current_state == "proposed"
    if target_expected and len(matches) != 1:
        state[f"{role}_state"] = "invalid"
        state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_target_entry_missing")
        return
    if not target_expected and matches:
        state[f"{role}_state"] = "diverged"
        state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_target_entry_unexpected")
        return
    if current_state == "diverged":
        state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_digest_diverged")
    if matches:
        entry = matches[0]
        expected = {
            "page_relative_path": receipt["page_relative_path"],
            "memory_layer": "primary",
            "idempotency_key": receipt["idempotency_key"],
            "page_digest": receipt["page_digest"],
        }
        if role == "log":
            expected["index_entry_id"] = receipt["index_entry_identity"]
        if any(entry.get(field) != wanted for field, wanted in expected.items()):
            state[f"{role}_state"] = "invalid"
            state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_entry_binding_mismatch")
            return
        state[f"{role}_entry"] = dict(entry)


def cross_validate_entries(state: dict[str, Any]) -> None:
    page = state.get("page_metadata")
    index = state.get("index_entry")
    log = state.get("log_entry")
    if not isinstance(page, Mapping):
        return
    fields = ("memory_kind", "namespace", "source_event_kind", "promotion_policy", "safety_scope")
    for role, entry in (("index", index), ("log", log)):
        if isinstance(entry, Mapping) and any(entry.get(field) != page.get(field) for field in fields):
            state[f"{role}_state"] = "invalid"
            state["blocked_reasons"].append(f"primary_reconciliation_recovery_{role}_page_scope_mismatch")
    if isinstance(index, Mapping) and isinstance(log, Mapping):
        shared = fields + ("target_category", "page_relative_path", "page_digest")
        if any(index.get(field) != log.get(field) for field in shared):
            state["blocked_reasons"].append("primary_reconciliation_recovery_control_scope_mismatch")
            state["index_state"] = "invalid"
            state["log_state"] = "invalid"


def derive_store_state(state: Mapping[str, Any]) -> str:
    if state.get("page_state") != "verified":
        return "page_unverified"
    index_state = state.get("index_state")
    log_state = state.get("log_state")
    if index_state == "proposed" and log_state == "proposed":
        return "fully_reconciled"
    if index_state == "proposed" and log_state == "expected":
        return "index_applied_log_pending"
    if index_state == "expected" and log_state == "expected":
        return "not_applied"
    if index_state == "expected" and log_state == "proposed":
        return "log_applied_index_pending"
    if index_state in {"missing", "invalid"} or log_state in {"missing", "invalid"}:
        return "control_unverified"
    return "state_diverged"
