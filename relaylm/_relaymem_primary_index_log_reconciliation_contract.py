"""Exact M3e receipt and Primary page validation for RelayMEM M3f."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    KIND_TARGET,
    MAX_PAGE_BYTES,
    MAX_SUMMARY,
    MAX_TITLE,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)

RECEIPT_SCHEMA = "relaymem.primary_page_write_receipt.v0"
RECEIPT_FIELDS = {
    "schema_version",
    "runtime_private",
    "content_included",
    "candidate_id",
    "namespace",
    "source_event_kind",
    "memory_layer",
    "memory_kind",
    "promotion_policy",
    "safety_scope",
    "target_category",
    "target_relative_path",
    "lineage_fingerprint",
    "idempotency_key",
    "page_bytes",
    "page_digest",
    "status",
    "writes_memory",
    "page_applied",
    "idempotent_noop",
    "durability_confirmed",
    "cleanup_complete",
    "updates_index",
    "updates_log",
}


def parse_m3e_receipt(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_reconciliation_receipt_missing")
    reasons: list[str] = []
    if set(value.keys()) != RECEIPT_FIELDS:
        reasons.append("primary_reconciliation_receipt_fields_mismatch")
    if value.get("schema_version") != RECEIPT_SCHEMA:
        reasons.append("primary_reconciliation_receipt_schema_mismatch")

    exact = {
        "runtime_private": True,
        "content_included": False,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "cleanup_complete": True,
        "updates_index": False,
        "updates_log": False,
    }
    for field, expected in exact.items():
        actual = value.get(field)
        if isinstance(expected, bool):
            if type(actual) is not bool or actual is not expected:
                reasons.append(f"primary_reconciliation_receipt_{field}_invalid")
        elif actual != expected:
            reasons.append(f"primary_reconciliation_receipt_{field}_invalid")

    status = value.get("status")
    if status == "applied":
        status_exact = {
            "writes_memory": True,
            "page_applied": True,
            "idempotent_noop": False,
            "durability_confirmed": True,
        }
    elif status == "already_applied":
        status_exact = {
            "writes_memory": False,
            "page_applied": False,
            "idempotent_noop": True,
            "durability_confirmed": False,
        }
    else:
        status_exact = {}
        reasons.append("primary_reconciliation_receipt_status_ineligible")
    for field, expected in status_exact.items():
        actual = value.get(field)
        if type(actual) is not bool or actual is not expected:
            reasons.append(f"primary_reconciliation_receipt_{field}_invalid")

    for field in ("candidate_id", "namespace"):
        if not token(value.get(field)):
            reasons.append(f"primary_reconciliation_receipt_{field}_invalid")
    event_kind = value.get("source_event_kind")
    event_kind_valid = isinstance(event_kind, str) and event_kind in EVENT_KINDS
    if not event_kind_valid:
        reasons.append("primary_reconciliation_receipt_source_event_kind_invalid")
    memory_kind = value.get("memory_kind")
    memory_kind_valid = isinstance(memory_kind, str) and memory_kind in KIND_TARGET
    if not memory_kind_valid:
        reasons.append("primary_reconciliation_receipt_memory_kind_invalid")
    target_category = value.get("target_category")
    target_category_valid = (
        isinstance(target_category, str) and target_category in TARGET_DIR
    )
    if not target_category_valid:
        reasons.append("primary_reconciliation_receipt_target_category_invalid")
    if memory_kind_valid and target_category != KIND_TARGET[memory_kind]:
        reasons.append("primary_reconciliation_receipt_kind_category_mismatch")

    for field in ("lineage_fingerprint", "idempotency_key", "page_digest"):
        if not is_sha256(value.get(field)):
            reasons.append(f"primary_reconciliation_receipt_{field}_invalid")
    page_bytes = value.get("page_bytes")
    if type(page_bytes) is not int or page_bytes <= 0 or page_bytes > MAX_PAGE_BYTES:
        reasons.append("primary_reconciliation_receipt_page_bytes_invalid")

    if (
        token(value.get("candidate_id"))
        and token(value.get("namespace"))
        and event_kind_valid
        and memory_kind_valid
        and is_sha256(value.get("lineage_fingerprint"))
        and is_sha256(value.get("idempotency_key"))
    ):
        expected_key = stable_hash(
            (
                "relaymem-primary-write-preflight-v0",
                value["namespace"],
                event_kind,
                value["lineage_fingerprint"],
                value["candidate_id"],
                event_kind,
                "primary",
                memory_kind,
                "free_to_update",
            )
        )
        if value["idempotency_key"] != expected_key:
            reasons.append("primary_reconciliation_receipt_idempotency_key_mismatch")

    expected_path = ""
    if target_category_valid and is_sha256(value.get("idempotency_key")):
        expected_path = f"{TARGET_DIR[target_category]}/{value['idempotency_key']}.md"
    if not exact_primary_path(value.get("target_relative_path"), expected_path):
        reasons.append("primary_reconciliation_receipt_target_path_invalid")

    if reasons:
        return invalid(*reasons)
    return {"valid": True, "receipt": dict(value), "blocked_reasons": []}


def verify_primary_page(receipt: Mapping[str, Any], content: bytes) -> list[str]:
    reasons: list[str] = []
    if len(content) != receipt["page_bytes"]:
        reasons.append("primary_reconciliation_page_bytes_mismatch")
    if sha256(content).hexdigest() != receipt["page_digest"]:
        reasons.append("primary_reconciliation_page_digest_mismatch")
    try:
        markdown = content.decode("utf-8")
    except UnicodeDecodeError:
        return dedupe(reasons + ["primary_reconciliation_page_utf8_invalid"])

    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return dedupe(reasons + ["primary_reconciliation_page_front_matter_invalid"])
    metadata = parsed["metadata"]
    expected = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "memory_kind": receipt["memory_kind"],
        "source_event_kind": receipt["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": receipt["namespace"],
        "lineage_fingerprint": receipt["lineage_fingerprint"],
        "idempotency_key": receipt["idempotency_key"],
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    for field, wanted in expected.items():
        if metadata.get(field) != wanted:
            reasons.append(f"primary_reconciliation_page_{field}_mismatch")

    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or len(summary) > MAX_SUMMARY
    ):
        reasons.append("primary_reconciliation_page_summary_invalid")
    elif parsed["body"] != f"# Primary memory\n\n## Summary\n\n{summary}\n":
        reasons.append("primary_reconciliation_page_body_mismatch")
    if (
        not isinstance(title, str)
        or title != title.strip()
        or len(title) > MAX_TITLE
        or bad_text(title)
        or any(char in title for char in "\n\r\t")
    ):
        reasons.append("primary_reconciliation_page_title_invalid")
    return dedupe(reasons)


def exact_primary_path(value: object, expected: str) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or bad_text(value)
    ):
        return False
    path = PurePosixPath(value)
    return path.as_posix() == value == expected and all(
        part not in {"", ".", ".."} for part in path.parts
    )


def token(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and bool(value)
        and len(value) <= 128
        and not bad_text(value)
        and not any(char in value for char in "\n\r\t")
    )


def invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": dedupe(reasons)}


def dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["parse_m3e_receipt", "verify_primary_page"]
