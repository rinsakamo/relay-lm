"""RelayMEM Primary MEM page-candidate helpers.

MEM-M3c joins an M3b preflight operation with a runtime-private governed
experience summary. It builds a deterministic page candidate only; it never
writes files or mutates RelaySOUL/RelaySLP/runtime-visible output.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

EXPERIENCE_SCHEMA = "relaymem.governed_experience_summary.v0"
PREFLIGHT_SCHEMA = "relaymem.primary_write_preflight_dry_run.v0"
OPERATION_SCHEMA = "relaymem.primary_write_preflight_operation.v0"
LINEAGE_SCHEMA = "relaymem.primary_source_lineage.v0"
RESULT_SCHEMA = "relaymem.primary_page_candidate_dry_run.v0"
CANDIDATE_SCHEMA = "relaymem.primary_page_candidate.v0"
PROJECTION_SCHEMA = "relaymem.primary_page_candidate_projection.v0"

EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
TARGET_DIRS = {
    "primary_projects": "memory/mem/primary/projects",
    "primary_relationships": "memory/mem/primary/relationships",
    "primary_sessions": "memory/mem/primary/sessions",
    "primary_scenes": "memory/mem/primary/scenes",
}
MAX_TOKEN = 128
MAX_TITLE = 160
MAX_SUMMARY = 2048
MAX_PAGE_BYTES = 8192
MAX_OPERATIONS = 32


def build_relaymem_governed_experience_summary(
    *,
    candidate_id: str,
    source_event_kind: str,
    namespace: str,
    summary_text: str,
    title: str | None = None,
) -> dict[str, Any]:
    """Build a bounded content-bearing artifact for a trusted in-process summary."""

    candidate_id, reasons = _token(candidate_id, "governed_experience_candidate_id_invalid")
    event_kind, event_reasons = _event_kind(source_event_kind)
    namespace, namespace_reasons = _token(
        namespace, "governed_experience_namespace_invalid"
    )
    summary_text, summary_reasons = _text(
        summary_text,
        MAX_SUMMARY,
        "governed_experience_summary_invalid",
        multiline=True,
    )
    title, title_reasons = _optional_text(
        title,
        MAX_TITLE,
        "governed_experience_title_invalid",
        multiline=False,
    )
    reasons = _dedupe(
        reasons + event_reasons + namespace_reasons + summary_reasons + title_reasons
    )
    return {
        "schema_version": EXPERIENCE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "summary_origin": "trusted_in_process_summary",
        "candidate_id": candidate_id,
        "source_event_kind": event_kind,
        "namespace": namespace,
        "title": title,
        "summary_text": summary_text,
        "summary_chars": len(summary_text),
        "valid": not reasons,
        "blocked_reasons": reasons,
    }


def build_relaymem_primary_page_candidate_dry_run(
    *,
    preflight_artifact: Mapping[str, Any] | None,
    source_lineage_artifact: Mapping[str, Any] | None,
    governed_experience_artifact: Mapping[str, Any] | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Build one deterministic Primary MEM page candidate without writing it."""

    lineage = _parse_lineage(source_lineage_artifact)
    experience = _parse_experience(governed_experience_artifact)
    preflight = _parse_preflight(
        preflight_artifact,
        str(experience.get("candidate_id", "")),
    )
    reasons = [] if enabled else ["primary_page_candidate_disabled"]
    for parsed in (lineage, experience, preflight):
        if parsed.get("valid") is not True:
            reasons.extend(_strings(parsed.get("blocked_reasons")))
    if not reasons:
        reasons.extend(_cross_check(lineage, experience, preflight))
    reasons = _dedupe(reasons)

    candidates: list[dict[str, Any]] = []
    if not reasons:
        candidate = _page_candidate(
            lineage=lineage,
            experience=experience,
            preflight=preflight,
            dry_run_only=dry_run_only,
            apply_enabled=apply_enabled,
        )
        if candidate["blocked_reasons"]:
            reasons = list(candidate["blocked_reasons"])
        else:
            candidates.append(candidate)

    projection = {
        "schema_version": PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "candidate_id_included": False,
        "target_path_included": False,
        "lineage_fingerprint_included": False,
        "idempotency_key_included": False,
        "page_markdown_included": False,
        "page_digest_included": False,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "page_candidate_count": len(candidates),
        "status_counts": _counts(candidates, "status"),
        "target_category_counts": _counts(candidates, "target_category"),
        "blocked_reasons": reasons,
        "page_candidates": [
            {
                "operation_index": index,
                "source_event_kind": item["source_event_kind"],
                "memory_layer": "primary",
                "memory_kind": item["memory_kind"],
                "promotion_policy": item["promotion_policy"],
                "safety_scope": item["safety_scope"],
                "target_category": item["target_category"],
                "status": item["status"],
                "writer_handoff_eligible": item["writer_handoff_eligible"],
                "summary_chars": item["summary_chars"],
                "page_bytes": item["page_bytes"],
            }
            for index, item in enumerate(candidates)
        ],
    }
    return {
        "schema_version": RESULT_SCHEMA,
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_candidates": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "page_candidate_count": len(candidates),
        "page_candidates": candidates,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _parse_lineage(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _invalid("source_lineage_missing")
    if value.get("schema_version") != LINEAGE_SCHEMA:
        return _invalid("source_lineage_schema_mismatch")
    if value.get("valid") is not True:
        return _invalid(*(_strings(value.get("blocked_reasons")) or ["source_lineage_invalid"]))
    fingerprint = value.get("lineage_fingerprint")
    event_kind, event_reasons = _event_kind(value.get("source_event_kind"))
    namespace, namespace_reasons = _token(
        value.get("namespace"), "source_lineage_namespace_invalid"
    )
    reasons = event_reasons + namespace_reasons
    if not _sha256_hex(fingerprint):
        reasons.append("source_lineage_fingerprint_invalid")
    if reasons:
        return _invalid(*reasons)
    return {
        "valid": True,
        "source_event_kind": event_kind,
        "namespace": namespace,
        "lineage_fingerprint": fingerprint,
        "blocked_reasons": [],
    }


def _parse_experience(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _invalid("governed_experience_missing")
    if value.get("schema_version") != EXPERIENCE_SCHEMA:
        return _invalid("governed_experience_schema_mismatch")
    if value.get("valid") is not True:
        return _invalid(*(_strings(value.get("blocked_reasons")) or ["governed_experience_invalid"]))
    invariant_reasons: list[str] = []
    expected = {
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "summary_origin": "trusted_in_process_summary",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            invariant_reasons.append(f"governed_experience_{key}_invalid")

    candidate_id, candidate_reasons = _token(
        value.get("candidate_id"), "governed_experience_candidate_id_invalid"
    )
    event_kind, event_reasons = _event_kind(value.get("source_event_kind"))
    namespace, namespace_reasons = _token(
        value.get("namespace"), "governed_experience_namespace_invalid"
    )
    summary, summary_reasons = _text(
        value.get("summary_text"),
        MAX_SUMMARY,
        "governed_experience_summary_invalid",
        multiline=True,
    )
    title, title_reasons = _optional_text(
        value.get("title"),
        MAX_TITLE,
        "governed_experience_title_invalid",
        multiline=False,
    )
    if value.get("summary_chars") != len(summary):
        summary_reasons.append("governed_experience_summary_chars_mismatch")
    reasons = _dedupe(
        invariant_reasons
        + candidate_reasons
        + event_reasons
        + namespace_reasons
        + summary_reasons
        + title_reasons
    )
    if reasons:
        return _invalid(*reasons)
    return {
        "valid": True,
        "candidate_id": candidate_id,
        "source_event_kind": event_kind,
        "namespace": namespace,
        "summary_origin": "trusted_in_process_summary",
        "summary_text": summary,
        "summary_chars": len(summary),
        "title": title,
        "blocked_reasons": [],
    }


def _parse_preflight(
    value: Mapping[str, Any] | None,
    candidate_id: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _invalid("primary_write_preflight_missing")
    if value.get("schema_version") != PREFLIGHT_SCHEMA:
        return _invalid("primary_write_preflight_schema_mismatch")

    reasons: list[str] = []
    exact = {
        "enabled": True,
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "writes_memory": False,
        "write_apply_supported": False,
        "apply_allowed": False,
        "source_lineage_valid": True,
        "candidate_limit_exceeded": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            reasons.append(f"primary_write_preflight_{key}_invalid")
    if _strings(value.get("blocked_reasons")):
        reasons.append("primary_write_preflight_blocked")

    operations = value.get("operations")
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        return _invalid(*(reasons + ["primary_write_preflight_operations_invalid"]))
    if len(operations) > MAX_OPERATIONS:
        reasons.append("primary_write_preflight_operations_unbounded")
    if value.get("operation_count") != len(operations):
        reasons.append("primary_write_preflight_operation_count_mismatch")
    matched = [
        item
        for item in operations
        if isinstance(item, Mapping) and item.get("candidate_id") == candidate_id
    ]
    if len(matched) != 1:
        return _invalid(*(reasons + ["primary_write_preflight_operation_match_invalid"]))
    operation = matched[0]
    if operation.get("schema_version") != OPERATION_SCHEMA:
        reasons.append("primary_write_preflight_operation_schema_mismatch")

    fields: dict[str, str] = {}
    for key in (
        "candidate_id",
        "memory_layer",
        "memory_kind",
        "promotion_policy",
        "safety_scope",
        "target_category",
    ):
        fields[key], field_reasons = _token(
            operation.get(key), f"primary_write_preflight_{key}_invalid"
        )
        reasons.extend(field_reasons)
    event_kind, event_reasons = _event_kind(operation.get("source_event_kind"))
    reasons.extend(event_reasons)

    idempotency_key = operation.get("idempotency_key")
    if not _sha256_hex(idempotency_key):
        reasons.append("primary_write_preflight_idempotency_key_invalid")
    required = {
        "preflight_status": "eligible",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "memory_layer": "primary",
        "content_included": False,
        "raw_text_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "applied": False,
    }
    for key, expected in required.items():
        if operation.get(key) != expected:
            reasons.append(f"primary_write_preflight_{key}_invalid")
    if fields.get("target_category") not in TARGET_DIRS:
        reasons.append("primary_write_preflight_target_category_unsupported")
    if _strings(operation.get("blocked_reasons")):
        reasons.append("primary_write_preflight_operation_blocked")
    reasons = _dedupe(reasons)
    if reasons:
        return _invalid(*reasons)
    return {
        "valid": True,
        **fields,
        "source_event_kind": event_kind,
        "idempotency_key": idempotency_key,
        "blocked_reasons": [],
    }


def _cross_check(
    lineage: Mapping[str, Any],
    experience: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if experience["candidate_id"] != preflight["candidate_id"]:
        reasons.append("primary_page_candidate_candidate_id_mismatch")
    if not (
        experience["source_event_kind"]
        == preflight["source_event_kind"]
        == lineage["source_event_kind"]
    ):
        reasons.append("primary_page_candidate_source_event_kind_mismatch")
    if experience["namespace"] != lineage["namespace"]:
        reasons.append("primary_page_candidate_namespace_mismatch")
    expected_key = _stable_hash(
        [
            "relaymem-primary-write-preflight-v0",
            lineage["namespace"],
            lineage["source_event_kind"],
            lineage["lineage_fingerprint"],
            preflight["candidate_id"],
            preflight["source_event_kind"],
            preflight["memory_layer"],
            preflight["memory_kind"],
            preflight["promotion_policy"],
        ]
    )
    if preflight["idempotency_key"] != expected_key:
        reasons.append("primary_page_candidate_idempotency_key_mismatch")
    return reasons


def _page_candidate(
    *,
    lineage: Mapping[str, Any],
    experience: Mapping[str, Any],
    preflight: Mapping[str, Any],
    dry_run_only: bool,
    apply_enabled: bool,
) -> dict[str, Any]:
    target_dir = TARGET_DIRS[preflight["target_category"]]
    target_path = f"{target_dir}/{preflight['idempotency_key']}.md"
    fields = {
        "schema_version": "relaymem.primary_page.v0",
        "memory_layer": "primary",
        "memory_kind": preflight["memory_kind"],
        "source_event_kind": preflight["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": lineage["namespace"],
        "lineage_fingerprint": lineage["lineage_fingerprint"],
        "idempotency_key": preflight["idempotency_key"],
        "summary_origin": experience["summary_origin"],
        "content_role": "evidence",
        "title": experience.get("title") or "",
    }
    front_matter = "\n".join(
        f"{key}: {json.dumps(str(value), ensure_ascii=False)}"
        for key, value in fields.items()
    )
    markdown = (
        f"---\n{front_matter}\n---\n"
        "# Primary memory\n\n"
        "## Summary\n\n"
        f"{experience['summary_text'].strip()}\n"
    )
    try:
        encoded_page = markdown.encode("utf-8")
    except UnicodeEncodeError:
        encoded_page = b""
        reasons = ["primary_page_candidate_utf8_invalid"]
    else:
        reasons = (
            ["primary_page_candidate_page_size_exceeded"]
            if len(encoded_page) > MAX_PAGE_BYTES
            else []
        )
    page_bytes = len(encoded_page)
    status = "blocked" if reasons else "ready"
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "candidate_id": preflight["candidate_id"],
        "source_event_kind": preflight["source_event_kind"],
        "memory_layer": "primary",
        "memory_kind": preflight["memory_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": lineage["namespace"],
        "target_category": preflight["target_category"],
        "target_relative_path": target_path,
        "lineage_fingerprint": lineage["lineage_fingerprint"],
        "idempotency_key": preflight["idempotency_key"],
        "summary_origin": experience["summary_origin"],
        "summary_chars": experience["summary_chars"],
        "page_markdown": markdown,
        "page_bytes": page_bytes,
        "page_digest": sha256(encoded_page).hexdigest() if encoded_page else "",
        "status": status,
        "writer_handoff_eligible": (
            status == "ready" and bool(apply_enabled) and not bool(dry_run_only)
        ),
        "writes_memory": False,
        "applied": False,
        "blocked_reasons": reasons,
    }


def _invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": _dedupe(list(reasons))}


def _token(value: object, reason: str) -> tuple[str, list[str]]:
    if not isinstance(value, str):
        return "", [reason]
    value = value.strip()
    if (
        not value
        or len(value) > MAX_TOKEN
        or _control(value)
        or _surrogate(value)
        or any(char in value for char in ("\n", "\r", "\t"))
    ):
        return "", [reason]
    return value, []


def _event_kind(value: object) -> tuple[str, list[str]]:
    if isinstance(value, str) and value in EVENT_KINDS:
        return value, []
    return "unknown", ["source_event_kind_invalid"]


def _text(
    value: object,
    limit: int,
    reason: str,
    *,
    multiline: bool,
) -> tuple[str, list[str]]:
    if not isinstance(value, str):
        return "", [reason]
    value = value.strip()
    if (
        not value
        or len(value) > limit
        or _control(value)
        or _surrogate(value)
        or (not multiline and any(char in value for char in ("\n", "\r", "\t")))
    ):
        return "", [reason]
    return value, []


def _optional_text(
    value: object,
    limit: int,
    reason: str,
    *,
    multiline: bool,
) -> tuple[str | None, list[str]]:
    if value is None:
        return None, []
    text, reasons = _text(value, limit, reason, multiline=multiline)
    return (text or None), reasons


def _control(value: str) -> bool:
    return any(ord(char) < 32 and char not in {"\n", "\t"} for char in value)


def _surrogate(value: str) -> bool:
    return any(0xD800 <= ord(char) <= 0xDFFF for char in value)


def _sha256_hex(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _stable_hash(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dedupe(reasons: Sequence[str]) -> list[str]:
    result: list[str] = []
    for reason in reasons:
        if reason and reason not in result:
            result.append(reason)
    return result


def _counts(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        result[value] = result.get(value, 0) + 1
    return result
