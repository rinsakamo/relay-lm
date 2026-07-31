"""Validated, read-only Primary recall store acquisition."""

from __future__ import annotations
import json, re
from hashlib import sha256
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any
from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    FRONT_MATTER_KEYS,
    KIND_TARGET,
    MAX_PAGE_BYTES,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)

_CHARACTER_PARTITION_VERSION = "relaymem-character-store-v0"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_MAX_CONTROL_BYTES = 65_536
_MAX_MARKERS = 256
_MAX_MARKER_LINE_BYTES = 4_096
_PRIMARY_DIRS = tuple(TARGET_DIR.values())
_INDEX_SCHEMA = "relaymem.primary_index_entry.v0"
_LOG_SCHEMA = "relaymem.primary_log_entry.v0"


def resolve_relaymem_character_store_root(
    configured_root: object,
    character_id: object,
) -> str | None:
    """Resolve one opaque character partition below the configured store root.

    The configured root remains the operator-owned RelayMEM root.  Character
    values are not used as path components and are never returned by the public
    projection.
    """

    if not isinstance(configured_root, str) or not configured_root.strip():
        return None
    if configured_root != configured_root.strip() or "\x00" in configured_root:
        return None
    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return None
    root = Path(configured_root)
    if _path_has_symlink_component(root):
        return None
    if root.exists() and not root.is_dir():
        return None
    character_root = root / "characters"
    if character_root.is_symlink():
        return None
    if character_root.exists() and not character_root.is_dir():
        return None
    digest = stable_hash((_CHARACTER_PARTITION_VERSION, character_id))
    return str(character_root / digest)


def _load_validated_page(
    root: Path,
    candidate: Mapping[str, Any],
    *,
    expected_namespace: str,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, Any] | None, list[str]]:
    relative = candidate.get("path")
    if not isinstance(relative, str) or not _primary_relative_path(relative):
        return None, ["primary_recall_path_invalid"]
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, ["primary_recall_page_unsafe_or_missing"]
    try:
        raw = path.read_bytes()
    except OSError:
        return None, ["primary_recall_page_unreadable"]
    if not raw or len(raw) > MAX_PAGE_BYTES:
        return None, ["primary_recall_page_size_invalid"]
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, ["primary_recall_page_utf8_invalid"]
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return None, ["primary_recall_page_schema_invalid"]
    metadata = parsed["metadata"]
    if set(metadata) != set(FRONT_MATTER_KEYS):
        return None, ["primary_recall_page_schema_invalid"]
    fixed = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    if any(metadata.get(key) != value for key, value in fixed.items()):
        return None, ["primary_recall_page_policy_invalid"]
    if metadata.get("namespace") != expected_namespace:
        return None, ["primary_recall_namespace_mismatch"]
    memory_kind = metadata.get("memory_kind")
    target_category = KIND_TARGET.get(str(memory_kind))
    if target_category is None:
        return None, ["primary_recall_memory_kind_invalid"]
    if metadata.get("source_event_kind") not in EVENT_KINDS:
        return None, ["primary_recall_event_kind_invalid"]
    identity = metadata.get("idempotency_key")
    lineage = metadata.get("lineage_fingerprint")
    if not is_sha256(identity) or not is_sha256(lineage):
        return None, ["primary_recall_lineage_invalid"]
    expected_path = f"{TARGET_DIR[target_category]}/{identity}.md"
    if relative != expected_path:
        return None, ["primary_recall_path_identity_mismatch"]
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or bad_text(summary)
        or not isinstance(title, str)
        or title != title.strip()
        or bad_text(title)
    ):
        return None, ["primary_recall_page_content_invalid"]
    expected_body = f"# Primary memory\n\n## Summary\n\n{summary}\n"
    if parsed.get("body") != expected_body:
        return None, ["primary_recall_page_body_mismatch"]

    digest = sha256(raw).hexdigest()
    index_matches = [
        entry
        for entry in control["index"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    log_matches = [
        entry
        for entry in control["log"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    if len(index_matches) != 1 or len(log_matches) != 1:
        return None, ["primary_recall_reconciliation_missing_or_duplicate"]
    index_entry = index_matches[0]
    log_entry = log_matches[0]
    shared = {
        "page_relative_path": relative,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "target_category": target_category,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "idempotency_key": identity,
        "page_digest": digest,
    }
    if any(index_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_index_mismatch"]
    if any(log_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_log_mismatch"]
    if log_entry.get("lineage_fingerprint") != lineage:
        return None, ["primary_recall_log_lineage_mismatch"]
    if log_entry.get("index_entry_id") != index_entry.get("entry_id"):
        return None, ["primary_recall_index_log_link_mismatch"]
    return {
        "path": relative,
        "idempotency_key": identity,
        "lineage_fingerprint": lineage,
        "page_digest": digest,
        "summary": summary,
        "title": title,
        "memory_kind": memory_kind,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
    }, []


def _load_control_state(
    root: Path,
) -> tuple[dict[str, list[dict[str, Any]]] | None, list[str]]:
    index, index_reason = _read_markers(
        root, "memory/mem/index.md", "# Index", "relaymem-primary-index-entry-v0"
    )
    log, log_reason = _read_markers(
        root, "memory/mem/log.md", "# Log", "relaymem-primary-log-entry-v0"
    )
    reasons = [reason for reason in (index_reason, log_reason) if reason]
    if reasons:
        return None, reasons
    assert index is not None and log is not None
    if any(not _valid_index_entry(entry) for entry in index):
        return None, ["primary_recall_index_invalid"]
    if any(not _valid_log_entry(entry) for entry in log):
        return None, ["primary_recall_log_invalid"]
    return {"index": index, "log": log}, []


def _read_markers(
    root: Path,
    relative: str,
    header: str,
    marker: str,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, "primary_recall_control_file_unsafe_or_missing"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "primary_recall_control_file_unreadable"
    if len(raw) > _MAX_CONTROL_BYTES:
        return None, "primary_recall_control_file_size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "primary_recall_control_file_utf8_invalid"
    lines = text.splitlines()
    if not lines or lines[0] != header:
        return None, "primary_recall_control_file_header_mismatch"
    prefix = f"<!-- {marker} "
    suffix = " -->"
    entries: list[dict[str, Any]] = []
    for line in lines[1:]:
        if line.lstrip().startswith("<!-- relaymem-primary-") and marker not in line:
            return None, "primary_recall_control_file_schema_conflict"
        if marker not in line:
            continue
        if len(line.encode("utf-8")) > _MAX_MARKER_LINE_BYTES:
            return None, "primary_recall_control_marker_too_large"
        if not line.startswith(prefix) or not line.endswith(suffix):
            return None, "primary_recall_control_marker_malformed"
        if len(entries) >= _MAX_MARKERS:
            return None, "primary_recall_control_marker_count_exceeded"
        payload = line[len(prefix) : -len(suffix)]
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return None, "primary_recall_control_marker_malformed"
        if not isinstance(value, dict):
            return None, "primary_recall_control_marker_malformed"
        canonical = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if canonical != payload:
            return None, "primary_recall_control_marker_noncanonical"
        entries.append(value)
    return entries, None


def _valid_index_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version",
        "entry_id",
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
    }
    if set(entry) != expected_keys or any(
        not isinstance(value, str) or not value for value in entry.values()
    ):
        return False
    if entry.get("schema_version") != _INDEX_SCHEMA:
        return False
    if not _valid_shared_control_entry(entry):
        return False
    expected = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return entry.get("entry_id") == expected


def _valid_log_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version",
        "entry_id",
        "index_entry_id",
        "operation",
        "page_relative_path",
        "memory_layer",
        "memory_kind",
        "target_category",
        "namespace",
        "source_event_kind",
        "promotion_policy",
        "safety_scope",
        "lineage_fingerprint",
        "idempotency_key",
        "page_digest",
    }
    if set(entry) != expected_keys or any(
        not isinstance(value, str) or not value for value in entry.values()
    ):
        return False
    if (
        entry.get("schema_version") != _LOG_SCHEMA
        or entry.get("operation") != "primary_page_published"
    ):
        return False
    if not _valid_shared_control_entry(entry) or not is_sha256(
        entry.get("lineage_fingerprint")
    ):
        return False
    expected_index = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    expected_log = stable_hash(
        (
            "relaymem-primary-log-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return (
        entry.get("index_entry_id") == expected_index
        and entry.get("entry_id") == expected_log
    )


def _valid_shared_control_entry(entry: Mapping[str, Any]) -> bool:
    kind = entry.get("memory_kind")
    category = entry.get("target_category")
    identity = entry.get("idempotency_key")
    digest = entry.get("page_digest")
    relative = entry.get("page_relative_path")
    if (
        entry.get("memory_layer") != "primary"
        or entry.get("promotion_policy") != "free_to_update"
        or entry.get("safety_scope") != "ordinary_memory"
        or kind not in KIND_TARGET
        or category != KIND_TARGET[kind]
        or entry.get("source_event_kind") not in EVENT_KINDS
        or _token(entry.get("namespace")) is None
        or not is_sha256(identity)
        or not is_sha256(digest)
    ):
        return False
    expected_path = f"{TARGET_DIR[str(category)]}/{identity}.md"
    return relative == expected_path and _primary_relative_path(str(relative))


def _safe_root(value: object) -> Path | None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        return None
    path = Path(value)
    if _path_has_symlink_component(path) or not path.exists() or not path.is_dir():
        return None
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def _path_has_symlink_component(path: Path) -> bool:
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _contains_symlink(root: Path, target: Path) -> bool:
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        return True
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    try:
        resolved = target.resolve(strict=False)
    except OSError:
        return True
    return resolved != root and root not in resolved.parents


def _primary_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        path.as_posix() == value
        and value.endswith(".md")
        and all(part not in {"", ".", ".."} for part in path.parts)
        and any(value.startswith(f"{directory}/") for directory in _PRIMARY_DIRS)
    )


def _token(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or _TOKEN_RE.fullmatch(value) is None
        or bad_text(value)
    ):
        return None
    return value
