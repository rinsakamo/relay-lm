"""Deterministic index/log mutation-plan construction for RelayMEM M3f."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    KIND_TARGET,
    TARGET_DIR,
    bad_text,
    is_sha256,
    stable_hash,
)

INDEX_PATH = "memory/mem/index.md"
LOG_PATH = "memory/mem/log.md"
MAX_INDEX_LOG_BYTES = 65536
MAX_MARKERS = 256
MAX_MARKER_LINE_BYTES = 4096
_INDEX_ENTRY_SCHEMA = "relaymem.primary_index_entry.v0"
_LOG_ENTRY_SCHEMA = "relaymem.primary_log_entry.v0"


def build_index_plan(receipt: Mapping[str, Any], current: bytes) -> dict[str, Any]:
    entry_id = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            receipt["idempotency_key"],
            receipt["page_digest"],
            receipt["target_relative_path"],
        )
    )
    entry = {
        "schema_version": _INDEX_ENTRY_SCHEMA,
        "entry_id": entry_id,
        "page_relative_path": receipt["target_relative_path"],
        "memory_layer": "primary",
        "memory_kind": receipt["memory_kind"],
        "target_category": receipt["target_category"],
        "namespace": receipt["namespace"],
        "source_event_kind": receipt["source_event_kind"],
        "promotion_policy": receipt["promotion_policy"],
        "safety_scope": receipt["safety_scope"],
        "idempotency_key": receipt["idempotency_key"],
        "page_digest": receipt["page_digest"],
    }
    return _mutation_plan(
        operation_kind="append_index_entry",
        target_relative_path=INDEX_PATH,
        marker="relaymem-primary-index-entry-v0",
        entry=entry,
        current=current,
        identity_fields=("entry_id", "page_relative_path", "idempotency_key"),
    )


def build_log_plan(
    receipt: Mapping[str, Any], current: bytes, index_entry_id: str
) -> dict[str, Any]:
    entry_id = stable_hash(
        (
            "relaymem-primary-log-entry-v0",
            receipt["idempotency_key"],
            receipt["page_digest"],
            receipt["target_relative_path"],
        )
    )
    entry = {
        "schema_version": _LOG_ENTRY_SCHEMA,
        "entry_id": entry_id,
        "index_entry_id": index_entry_id,
        "operation": "primary_page_published",
        "page_relative_path": receipt["target_relative_path"],
        "memory_layer": "primary",
        "memory_kind": receipt["memory_kind"],
        "target_category": receipt["target_category"],
        "namespace": receipt["namespace"],
        "source_event_kind": receipt["source_event_kind"],
        "promotion_policy": receipt["promotion_policy"],
        "safety_scope": receipt["safety_scope"],
        "lineage_fingerprint": receipt["lineage_fingerprint"],
        "idempotency_key": receipt["idempotency_key"],
        "page_digest": receipt["page_digest"],
    }
    return _mutation_plan(
        operation_kind="append_log_entry",
        target_relative_path=LOG_PATH,
        marker="relaymem-primary-log-entry-v0",
        entry=entry,
        current=current,
        identity_fields=("entry_id", "page_relative_path", "idempotency_key"),
    )


def operation(plan: Mapping[str, Any], operation_index: int) -> dict[str, Any]:
    return {
        "operation_index": operation_index,
        "operation_kind": plan["operation_kind"],
        "target_relative_path": plan["target_relative_path"],
        "entry_identity": plan["entry_identity"],
        "expected_current_bytes": plan["expected_current_bytes"],
        "expected_current_digest": plan["expected_current_digest"],
        "proposed_next_bytes": plan["proposed_next_bytes"],
        "proposed_next_digest": plan["proposed_next_digest"],
        "proposed_next_content": plan["proposed_next_content"],
    }


def _mutation_plan(
    *,
    operation_kind: str,
    target_relative_path: str,
    marker: str,
    entry: Mapping[str, Any],
    current: bytes,
    identity_fields: Sequence[str],
) -> dict[str, Any]:
    parsed = _parse_markers(current, marker)
    conflict = parsed.get("valid") is not True
    exact_present = False
    exact_count = 0
    if not conflict:
        for existing in parsed["entries"]:
            if set(existing.keys()) != set(entry.keys()):
                conflict = True
                continue
            if not _valid_existing_entry(marker, existing):
                conflict = True
                continue
            if existing.get("entry_id") == entry["entry_id"]:
                if existing == entry:
                    exact_count += 1
                    exact_present = True
                else:
                    conflict = True
            elif any(
                existing.get(field) == entry[field] for field in identity_fields[1:]
            ):
                conflict = True
        if exact_count > 1:
            conflict = True

    next_content = (
        current if exact_present or conflict else _append_marker(current, marker, entry)
    )
    if len(next_content) > MAX_INDEX_LOG_BYTES:
        conflict = True
        exact_present = False
        next_content = current
    return {
        "operation_kind": operation_kind,
        "target_relative_path": target_relative_path,
        "entry_identity": entry["entry_id"],
        "expected_current_bytes": len(current),
        "expected_current_digest": sha256(current).hexdigest(),
        "proposed_next_bytes": len(next_content),
        "proposed_next_digest": sha256(next_content).hexdigest(),
        "proposed_next_content": next_content.decode("utf-8"),
        "idempotent_noop": exact_present and not conflict,
        "conflict": conflict,
    }


def _parse_markers(content: bytes, marker: str) -> dict[str, Any]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return _invalid("primary_reconciliation_control_file_utf8_invalid")
    entries: list[dict[str, Any]] = []
    prefix = f"<!-- {marker} "
    suffix = " -->"
    for line in text.splitlines():
        if len(line.encode("utf-8")) > MAX_MARKER_LINE_BYTES and marker in line:
            return _invalid("primary_reconciliation_marker_line_too_large")
        if marker not in line:
            continue
        if not line.startswith(prefix) or not line.endswith(suffix):
            return _invalid("primary_reconciliation_marker_malformed")
        if len(entries) >= MAX_MARKERS:
            return _invalid("primary_reconciliation_marker_count_exceeded")
        payload = line[len(prefix) : -len(suffix)]
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return _invalid("primary_reconciliation_marker_malformed")
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            return _invalid("primary_reconciliation_marker_malformed")
        canonical = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if payload != canonical:
            return _invalid("primary_reconciliation_marker_noncanonical")
        entries.append(value)
    return {"valid": True, "entries": entries, "blocked_reasons": []}


def _valid_existing_entry(marker: str, entry: Mapping[str, Any]) -> bool:
    if any(not isinstance(value, str) or not value for value in entry.values()):
        return False
    if entry.get("memory_layer") != "primary":
        return False
    if entry.get("promotion_policy") != "free_to_update":
        return False
    if entry.get("safety_scope") != "ordinary_memory":
        return False

    memory_kind = entry.get("memory_kind")
    target_category = entry.get("target_category")
    source_event_kind = entry.get("source_event_kind")
    namespace = entry.get("namespace")
    if memory_kind not in KIND_TARGET or target_category != KIND_TARGET[memory_kind]:
        return False
    if source_event_kind not in EVENT_KINDS or not _marker_token(namespace):
        return False

    key = entry.get("idempotency_key")
    digest = entry.get("page_digest")
    relative_path = entry.get("page_relative_path")
    if not is_sha256(key) or not is_sha256(digest):
        return False
    if not _exact_entry_path(relative_path, target_category, key):
        return False

    expected_index_id = stable_hash(
        ("relaymem-primary-index-entry-v0", key, digest, relative_path)
    )
    if marker == "relaymem-primary-index-entry-v0":
        return (
            entry.get("schema_version") == _INDEX_ENTRY_SCHEMA
            and entry.get("entry_id") == expected_index_id
        )
    if marker == "relaymem-primary-log-entry-v0":
        lineage = entry.get("lineage_fingerprint")
        expected_log_id = stable_hash(
            ("relaymem-primary-log-entry-v0", key, digest, relative_path)
        )
        return (
            entry.get("schema_version") == _LOG_ENTRY_SCHEMA
            and entry.get("entry_id") == expected_log_id
            and entry.get("index_entry_id") == expected_index_id
            and entry.get("operation") == "primary_page_published"
            and is_sha256(lineage)
        )
    return False


def _exact_entry_path(value: object, target_category: str, key: str) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or bad_text(value)
    ):
        return False
    expected = f"{TARGET_DIR[target_category]}/{key}.md"
    path = PurePosixPath(value)
    return path.as_posix() == value == expected and all(
        part not in {"", ".", ".."} for part in path.parts
    )


def _token(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and bool(value)
        and len(value) <= 128
        and not bad_text(value)
        and not any(char in value for char in "\n\r\t")
    )


def _marker_token(value: object) -> bool:
    return (
        _token(value)
        and isinstance(value, str)
        and "--" not in value
        and len(value.splitlines()) == 1
    )


def _append_marker(current: bytes, marker: str, entry: Mapping[str, Any]) -> bytes:
    serialized = json.dumps(
        dict(entry), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    line = f"<!-- {marker} {serialized} -->\n".encode("utf-8")
    prefix = current
    if prefix and not prefix.endswith(b"\n"):
        prefix += b"\n"
    return prefix + line


def _invalid(*reasons: str) -> dict[str, Any]:
    return {
        "valid": False,
        "blocked_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
    }


__all__ = [
    "INDEX_PATH",
    "LOG_PATH",
    "MAX_INDEX_LOG_BYTES",
    "build_index_plan",
    "build_log_plan",
    "operation",
]
