"""Exact M3f plan validation for RelayMEM M3g reconciliation apply."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

from ._relaymem_primary_index_log_reconciliation_plan import (
    INDEX_PATH,
    LOG_PATH,
    MAX_INDEX_LOG_BYTES,
    _parse_markers,
    _valid_existing_entry,
)
from ._relaymem_primary_page_writer_common import (
    KIND_TARGET,
    MAX_PAGE_BYTES,
    MAX_SUMMARY,
    MAX_TITLE,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
)

PLAN_SCHEMA = "relaymem.primary_index_log_reconciliation_plan.v0"
PLAN_FIELDS = {
    "schema_version",
    "runtime_private",
    "read_only",
    "dry_run_only",
    "reconciliation_state",
    "plan_ready",
    "page",
    "index_plan",
    "log_plan",
    "ordered_operations",
    "operation_count",
    "writes_memory",
    "updates_index",
    "updates_log",
}
PAGE_FIELDS = {
    "target_relative_path",
    "page_bytes",
    "page_digest",
    "idempotency_key",
    "memory_kind",
    "target_category",
}
CONTROL_PLAN_FIELDS = {
    "operation_kind",
    "target_relative_path",
    "entry_identity",
    "expected_current_bytes",
    "expected_current_digest",
    "proposed_next_bytes",
    "proposed_next_digest",
    "proposed_next_content",
    "idempotent_noop",
    "conflict",
}
OPERATION_FIELDS = {
    "operation_index",
    "operation_kind",
    "target_relative_path",
    "entry_identity",
    "expected_current_bytes",
    "expected_current_digest",
    "proposed_next_bytes",
    "proposed_next_digest",
    "proposed_next_content",
}
STATE_FLAGS = {
    "index_and_log_update_required": (False, False),
    "index_update_required": (False, True),
    "log_update_required": (True, False),
    "already_reconciled": (True, True),
}


def parse_m3f_reconciliation_plan(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_reconciliation_apply_plan_missing")
    reasons: list[str] = []
    if set(value.keys()) != PLAN_FIELDS:
        reasons.append("primary_reconciliation_apply_plan_fields_mismatch")
    exact = {
        "schema_version": PLAN_SCHEMA,
        "runtime_private": True,
        "read_only": True,
        "dry_run_only": True,
        "plan_ready": True,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
    }
    for field, expected in exact.items():
        actual = value.get(field)
        if isinstance(expected, bool):
            if type(actual) is not bool or actual is not expected:
                reasons.append(f"primary_reconciliation_apply_plan_{field}_invalid")
        elif actual != expected:
            reasons.append(f"primary_reconciliation_apply_plan_{field}_invalid")

    state = value.get("reconciliation_state")
    if not isinstance(state, str) or state not in STATE_FLAGS:
        reasons.append("primary_reconciliation_apply_plan_state_invalid")
        state = ""

    page_result = _parse_page(value.get("page"))
    reasons.extend(page_result["blocked_reasons"])
    page = page_result.get("page")

    index_result = _parse_control_plan(
        value.get("index_plan"),
        role="index",
        page=page,
        expected_index_identity=None,
    )
    reasons.extend(index_result["blocked_reasons"])
    index_plan = index_result.get("plan")
    index_entry = index_result.get("entry")

    log_result = _parse_control_plan(
        value.get("log_plan"),
        role="log",
        page=page,
        expected_index_identity=(
            index_plan.get("entry_identity") if isinstance(index_plan, Mapping) else None
        ),
    )
    reasons.extend(log_result["blocked_reasons"])
    log_plan = log_result.get("plan")
    log_entry = log_result.get("entry")

    if isinstance(index_entry, Mapping) and isinstance(log_entry, Mapping):
        shared = (
            "page_relative_path",
            "memory_layer",
            "memory_kind",
            "target_category",
            "namespace",
            "source_event_kind",
            "promotion_policy",
            "safety_scope",
            "idempotency_key",
            "page_digest",
        )
        if any(index_entry.get(field) != log_entry.get(field) for field in shared):
            reasons.append("primary_reconciliation_apply_plan_entry_scope_mismatch")

    operation_count = value.get("operation_count")
    if type(operation_count) is not int or operation_count < 0 or operation_count > 2:
        reasons.append("primary_reconciliation_apply_plan_operation_count_invalid")
        operation_count = -1
    operations = value.get("ordered_operations")
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        reasons.append("primary_reconciliation_apply_plan_operations_invalid")
        operations = []
    else:
        operations = list(operations)

    if state in STATE_FLAGS and isinstance(index_plan, Mapping) and isinstance(log_plan, Mapping):
        expected_index_noop, expected_log_noop = STATE_FLAGS[state]
        if index_plan.get("idempotent_noop") is not expected_index_noop:
            reasons.append("primary_reconciliation_apply_plan_index_state_mismatch")
        if log_plan.get("idempotent_noop") is not expected_log_noop:
            reasons.append("primary_reconciliation_apply_plan_log_state_mismatch")
        expected_roles = []
        if not expected_index_noop:
            expected_roles.append("index")
        if not expected_log_noop:
            expected_roles.append("log")
        if operation_count != len(expected_roles) or len(operations) != len(expected_roles):
            reasons.append("primary_reconciliation_apply_plan_operation_count_mismatch")
        else:
            plans = {"index": index_plan, "log": log_plan}
            for position, role in enumerate(expected_roles):
                operation_reasons = _validate_operation(
                    operations[position], position=position, control_plan=plans[role]
                )
                reasons.extend(operation_reasons)

    if reasons:
        return invalid(*reasons)
    return {
        "valid": True,
        "plan": dict(value),
        "index_entry": dict(index_entry),
        "log_entry": dict(log_entry),
        "blocked_reasons": [],
    }


def verify_m3g_page(
    plan_page: Mapping[str, Any],
    content: bytes,
    *,
    index_entry: Mapping[str, Any],
    log_entry: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if len(content) != plan_page["page_bytes"]:
        reasons.append("primary_reconciliation_apply_page_bytes_mismatch")
    if sha256(content).hexdigest() != plan_page["page_digest"]:
        reasons.append("primary_reconciliation_apply_page_digest_mismatch")
    try:
        markdown = content.decode("utf-8")
    except UnicodeDecodeError:
        return dedupe(reasons + ["primary_reconciliation_apply_page_utf8_invalid"])
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return dedupe(reasons + ["primary_reconciliation_apply_page_front_matter_invalid"])
    metadata = parsed["metadata"]
    expected = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "memory_kind": plan_page["memory_kind"],
        "source_event_kind": index_entry["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": index_entry["namespace"],
        "lineage_fingerprint": log_entry["lineage_fingerprint"],
        "idempotency_key": plan_page["idempotency_key"],
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    for field, wanted in expected.items():
        if metadata.get(field) != wanted:
            reasons.append(f"primary_reconciliation_apply_page_{field}_mismatch")
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or len(summary) > MAX_SUMMARY
    ):
        reasons.append("primary_reconciliation_apply_page_summary_invalid")
    elif parsed["body"] != f"# Primary memory\n\n## Summary\n\n{summary}\n":
        reasons.append("primary_reconciliation_apply_page_body_mismatch")
    if (
        not isinstance(title, str)
        or title != title.strip()
        or len(title) > MAX_TITLE
        or bad_text(title)
        or any(char in title for char in "\n\r\t")
    ):
        reasons.append("primary_reconciliation_apply_page_title_invalid")
    return dedupe(reasons)


def _parse_page(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_reconciliation_apply_page_plan_missing")
    reasons: list[str] = []
    if set(value.keys()) != PAGE_FIELDS:
        reasons.append("primary_reconciliation_apply_page_plan_fields_mismatch")
    memory_kind = value.get("memory_kind")
    category = value.get("target_category")
    if not isinstance(memory_kind, str) or memory_kind not in KIND_TARGET:
        reasons.append("primary_reconciliation_apply_page_memory_kind_invalid")
    if not isinstance(category, str) or category not in TARGET_DIR:
        reasons.append("primary_reconciliation_apply_page_target_category_invalid")
    if (
        isinstance(memory_kind, str)
        and memory_kind in KIND_TARGET
        and category != KIND_TARGET[memory_kind]
    ):
        reasons.append("primary_reconciliation_apply_page_kind_category_mismatch")
    key = value.get("idempotency_key")
    digest = value.get("page_digest")
    if not is_sha256(key):
        reasons.append("primary_reconciliation_apply_page_idempotency_key_invalid")
    if not is_sha256(digest):
        reasons.append("primary_reconciliation_apply_page_digest_invalid")
    byte_count = value.get("page_bytes")
    if type(byte_count) is not int or byte_count <= 0 or byte_count > MAX_PAGE_BYTES:
        reasons.append("primary_reconciliation_apply_page_bytes_invalid")
    if not _exact_page_path(value.get("target_relative_path"), category, key):
        reasons.append("primary_reconciliation_apply_page_path_invalid")
    if reasons:
        return invalid(*reasons)
    return {"valid": True, "page": dict(value), "blocked_reasons": []}


def _parse_control_plan(
    value: object,
    *,
    role: str,
    page: Mapping[str, Any] | None,
    expected_index_identity: object,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid(f"primary_reconciliation_apply_{role}_plan_missing")
    reasons: list[str] = []
    if set(value.keys()) != CONTROL_PLAN_FIELDS:
        reasons.append(f"primary_reconciliation_apply_{role}_plan_fields_mismatch")
    expected_kind = f"append_{role}_entry"
    expected_path = INDEX_PATH if role == "index" else LOG_PATH
    marker = f"relaymem-primary-{role}-entry-v0"
    header = "# Index" if role == "index" else "# Log"
    if value.get("operation_kind") != expected_kind:
        reasons.append(f"primary_reconciliation_apply_{role}_operation_kind_invalid")
    if value.get("target_relative_path") != expected_path:
        reasons.append(f"primary_reconciliation_apply_{role}_target_path_invalid")
    if not is_sha256(value.get("entry_identity")):
        reasons.append(f"primary_reconciliation_apply_{role}_entry_identity_invalid")
    for field in ("expected_current_digest", "proposed_next_digest"):
        if not is_sha256(value.get(field)):
            reasons.append(f"primary_reconciliation_apply_{role}_{field}_invalid")
    for field in ("expected_current_bytes", "proposed_next_bytes"):
        actual = value.get(field)
        if type(actual) is not int or actual < 0 or actual > MAX_INDEX_LOG_BYTES:
            reasons.append(f"primary_reconciliation_apply_{role}_{field}_invalid")
    for field in ("idempotent_noop", "conflict"):
        if type(value.get(field)) is not bool:
            reasons.append(f"primary_reconciliation_apply_{role}_{field}_invalid")
    if value.get("conflict") is not False:
        reasons.append(f"primary_reconciliation_apply_{role}_conflict_not_eligible")
    content = value.get("proposed_next_content")
    encoded = b""
    if not isinstance(content, str):
        reasons.append(f"primary_reconciliation_apply_{role}_content_invalid")
    else:
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_INDEX_LOG_BYTES:
            reasons.append(f"primary_reconciliation_apply_{role}_content_size_exceeded")
        if len(encoded) != value.get("proposed_next_bytes"):
            reasons.append(f"primary_reconciliation_apply_{role}_proposed_bytes_mismatch")
        if sha256(encoded).hexdigest() != value.get("proposed_next_digest"):
            reasons.append(f"primary_reconciliation_apply_{role}_proposed_digest_mismatch")
    noop = value.get("idempotent_noop")
    if type(noop) is bool:
        same_state = (
            value.get("expected_current_bytes") == value.get("proposed_next_bytes")
            and value.get("expected_current_digest") == value.get("proposed_next_digest")
        )
        if noop is not same_state:
            reasons.append(f"primary_reconciliation_apply_{role}_noop_state_mismatch")
        if (
            noop is False
            and type(value.get("expected_current_bytes")) is int
            and type(value.get("proposed_next_bytes")) is int
            and value["proposed_next_bytes"] <= value["expected_current_bytes"]
        ):
            reasons.append(f"primary_reconciliation_apply_{role}_append_size_invalid")
    target_entry: Mapping[str, Any] | None = None
    if encoded:
        parsed = _parse_markers(encoded, marker, header)
        if parsed.get("valid") is not True:
            reasons.append(f"primary_reconciliation_apply_{role}_content_contract_invalid")
        else:
            matches = [
                entry
                for entry in parsed["entries"]
                if entry.get("entry_id") == value.get("entry_identity")
            ]
            if len(matches) != 1:
                reasons.append(f"primary_reconciliation_apply_{role}_entry_count_invalid")
            else:
                target_entry = matches[0]
                if not _valid_existing_entry(marker, target_entry):
                    reasons.append(f"primary_reconciliation_apply_{role}_entry_invalid")
    if isinstance(target_entry, Mapping) and isinstance(page, Mapping):
        expected_entry = {
            "page_relative_path": page["target_relative_path"],
            "memory_layer": "primary",
            "memory_kind": page["memory_kind"],
            "target_category": page["target_category"],
            "idempotency_key": page["idempotency_key"],
            "page_digest": page["page_digest"],
        }
        if any(
            target_entry.get(field) != wanted
            for field, wanted in expected_entry.items()
        ):
            reasons.append(f"primary_reconciliation_apply_{role}_entry_page_mismatch")
        if role == "log" and target_entry.get("index_entry_id") != expected_index_identity:
            reasons.append("primary_reconciliation_apply_log_index_identity_mismatch")
    if reasons:
        return invalid(*reasons)
    return {
        "valid": True,
        "plan": dict(value),
        "entry": dict(target_entry) if isinstance(target_entry, Mapping) else None,
        "blocked_reasons": [],
    }


def _validate_operation(
    value: object, *, position: int, control_plan: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    if not isinstance(value, Mapping):
        return ["primary_reconciliation_apply_operation_invalid"]
    if set(value.keys()) != OPERATION_FIELDS:
        reasons.append("primary_reconciliation_apply_operation_fields_mismatch")
    if type(value.get("operation_index")) is not int or value.get("operation_index") != position:
        reasons.append("primary_reconciliation_apply_operation_index_invalid")
    for field in OPERATION_FIELDS - {"operation_index"}:
        if value.get(field) != control_plan.get(field):
            reasons.append("primary_reconciliation_apply_operation_plan_mismatch")
            break
    return reasons


def _exact_page_path(value: object, category: object, key: object) -> bool:
    if (
        not isinstance(value, str)
        or not isinstance(category, str)
        or category not in TARGET_DIR
        or not isinstance(key, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or bad_text(value)
    ):
        return False
    expected = f"{TARGET_DIR[category]}/{key}.md"
    path = PurePosixPath(value)
    return path.as_posix() == value == expected and all(
        part not in {"", ".", ".."} for part in path.parts
    )


def invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": dedupe(reasons)}


def dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["parse_m3f_reconciliation_plan", "verify_m3g_page"]
