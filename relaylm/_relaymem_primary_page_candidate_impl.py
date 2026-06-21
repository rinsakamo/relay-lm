"""RelayMEM M3c: build runtime-private Primary MEM page candidates without writing."""
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
KIND_TARGET = {
    "recent_project_event": "primary_projects",
    "relationship_moment": "primary_relationships",
    "session_episode": "primary_sessions",
    "scene_bound_memory": "primary_scenes",
    "experience_event": "primary_scenes",
}
TARGET_DIR = {
    "primary_projects": "memory/mem/primary/projects",
    "primary_relationships": "memory/mem/primary/relationships",
    "primary_sessions": "memory/mem/primary/sessions",
    "primary_scenes": "memory/mem/primary/scenes",
}
MAX_TOKEN, MAX_TITLE, MAX_SUMMARY, MAX_PAGE_BYTES, MAX_OPERATIONS = 128, 160, 2048, 8192, 32


def build_relaymem_governed_experience_summary(*, candidate_id: str, source_event_kind: str,
        namespace: str, summary_text: str, title: str | None = None) -> dict[str, Any]:
    candidate_id, r1 = _token(candidate_id, "governed_experience_candidate_id_invalid")
    event_kind, r2 = _event(source_event_kind)
    namespace, r3 = _token(namespace, "governed_experience_namespace_invalid")
    summary, r4 = _text(summary_text, MAX_SUMMARY, "governed_experience_summary_invalid", True)
    title, r5 = _optional_text(title, MAX_TITLE, "governed_experience_title_invalid")
    reasons = _dedupe(r1 + r2 + r3 + r4 + r5)
    return {
        "schema_version": EXPERIENCE_SCHEMA, "runtime_private": True,
        "content_included": True, "raw_source_text_included": False,
        "raw_message_history_included": False, "raw_affect_estimates_included": False,
        "summary_origin": "trusted_in_process_summary", "candidate_id": candidate_id,
        "source_event_kind": event_kind, "namespace": namespace, "title": title,
        "summary_text": summary, "summary_chars": len(summary), "valid": not reasons,
        "blocked_reasons": reasons,
    }


def build_relaymem_primary_page_candidate_dry_run(*, preflight_artifact: Mapping[str, Any] | None,
        source_lineage_artifact: Mapping[str, Any] | None,
        governed_experience_artifact: Mapping[str, Any] | None, enabled: bool = False,
        dry_run_only: bool = True, apply_enabled: bool = False) -> dict[str, Any]:
    lineage = _lineage(source_lineage_artifact)
    experience = _experience(governed_experience_artifact)
    preflight = _preflight(preflight_artifact, str(experience.get("candidate_id", "")))
    reasons = [] if enabled else ["primary_page_candidate_disabled"]
    for artifact in (lineage, experience, preflight):
        if artifact.get("valid") is not True:
            reasons.extend(_strings(artifact.get("blocked_reasons")))
    if not reasons:
        reasons.extend(_cross(lineage, experience, preflight))
    reasons = _dedupe(reasons)
    pages: list[dict[str, Any]] = []
    if not reasons:
        page = _page(lineage, experience, preflight, dry_run_only, apply_enabled)
        reasons = list(page["blocked_reasons"])
        if not reasons:
            pages.append(page)
    projection = _projection(pages, reasons)
    return {
        "schema_version": RESULT_SCHEMA, "diagnostics_only": True, "helper_only": True,
        "read_only": True, "runtime_private_candidates": True, "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only), "apply_enabled": bool(apply_enabled),
        "write_apply_supported": False, "apply_allowed": False, "writes_memory": False,
        "mutates_soul": False, "invokes_slp": False, "lab_api_exposed": False,
        "page_candidate_count": len(pages), "page_candidates": pages,
        "blocked_reasons": reasons, "projection": projection,
    }


def _lineage(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping): return _invalid("source_lineage_missing")
    if value.get("schema_version") != LINEAGE_SCHEMA: return _invalid("source_lineage_schema_mismatch")
    if value.get("valid") is not True: return _invalid("source_lineage_invalid")
    reasons = _exact(value, {
        "content_free": True, "content_included": False, "raw_text_included": False,
    }, "source_lineage_")
    if _strings(value.get("blocked_reasons")): reasons.append("source_lineage_blocked")
    event, er = _event(value.get("source_event_kind")); reasons += er
    namespace, nr = _token(value.get("namespace"), "source_lineage_namespace_invalid"); reasons += nr
    fingerprint = value.get("lineage_fingerprint")
    if not _sha(fingerprint): reasons.append("source_lineage_fingerprint_invalid")
    if reasons: return _invalid(*reasons)
    return {"valid": True, "source_event_kind": event, "namespace": namespace,
            "lineage_fingerprint": fingerprint, "blocked_reasons": []}


def _experience(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping): return _invalid("governed_experience_missing")
    if value.get("schema_version") != EXPERIENCE_SCHEMA: return _invalid("governed_experience_schema_mismatch")
    if value.get("valid") is not True: return _invalid("governed_experience_invalid")
    reasons = _exact(value, {
        "runtime_private": True, "content_included": True,
        "raw_source_text_included": False, "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "summary_origin": "trusted_in_process_summary",
    }, "governed_experience_")
    if _strings(value.get("blocked_reasons")): reasons.append("governed_experience_blocked")
    candidate, r1 = _token(value.get("candidate_id"), "governed_experience_candidate_id_invalid")
    event, r2 = _event(value.get("source_event_kind"))
    namespace, r3 = _token(value.get("namespace"), "governed_experience_namespace_invalid")
    summary, r4 = _text(value.get("summary_text"), MAX_SUMMARY, "governed_experience_summary_invalid", True)
    title, r5 = _optional_text(value.get("title"), MAX_TITLE, "governed_experience_title_invalid")
    count = value.get("summary_chars")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(summary):
        r4.append("governed_experience_summary_chars_mismatch")
    reasons = _dedupe(reasons + r1 + r2 + r3 + r4 + r5)
    if reasons: return _invalid(*reasons)
    return {"valid": True, "candidate_id": candidate, "source_event_kind": event,
            "namespace": namespace, "summary_origin": "trusted_in_process_summary",
            "summary_text": summary, "summary_chars": len(summary), "title": title,
            "blocked_reasons": []}


def _preflight(value: Mapping[str, Any] | None, candidate_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping): return _invalid("primary_write_preflight_missing")
    if value.get("schema_version") != PREFLIGHT_SCHEMA: return _invalid("primary_write_preflight_schema_mismatch")
    reasons = _exact(value, {
        "enabled": True, "diagnostics_only": True, "helper_only": True, "read_only": True,
        "writes_memory": False, "mutates_soul": False, "invokes_slp": False,
        "lab_api_exposed": False, "write_apply_supported": False, "apply_allowed": False,
        "source_lineage_valid": True, "candidate_limit_exceeded": False,
    }, "primary_write_preflight_")
    if _strings(value.get("blocked_reasons")): reasons.append("primary_write_preflight_blocked")
    operations = value.get("operations")
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        return _invalid(*(reasons + ["primary_write_preflight_operations_invalid"]))
    if len(operations) > MAX_OPERATIONS: reasons.append("primary_write_preflight_operations_unbounded")
    if value.get("operation_count") != len(operations): reasons.append("primary_write_preflight_operation_count_mismatch")
    matched = [x for x in operations if isinstance(x, Mapping) and x.get("candidate_id") == candidate_id]
    if len(matched) != 1: return _invalid(*(reasons + ["primary_write_preflight_operation_match_invalid"]))
    op = matched[0]
    if op.get("schema_version") != OPERATION_SCHEMA: reasons.append("primary_write_preflight_operation_schema_mismatch")
    fields: dict[str, str] = {}
    for key in ("candidate_id", "memory_layer", "memory_kind", "promotion_policy", "safety_scope", "target_category"):
        fields[key], rs = _token(op.get(key), f"primary_write_preflight_{key}_invalid"); reasons += rs
    event, rs = _event(op.get("source_event_kind")); reasons += rs
    idem = op.get("idempotency_key")
    if not _sha(idem): reasons.append("primary_write_preflight_idempotency_key_invalid")
    reasons += _exact(op, {
        "preflight_status": "eligible", "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory", "memory_layer": "primary",
        "content_included": False, "raw_text_included": False,
        "raw_affect_estimates_included": False, "writes_memory": False,
        "mutates_soul": False, "invokes_slp": False, "applied": False,
    }, "primary_write_preflight_")
    expected_target = KIND_TARGET.get(fields.get("memory_kind", ""))
    if expected_target is None: reasons.append("primary_write_preflight_memory_kind_unsupported")
    elif fields.get("target_category") != expected_target:
        reasons.append("primary_write_preflight_memory_kind_target_category_mismatch")
    if fields.get("target_category") not in TARGET_DIR: reasons.append("primary_write_preflight_target_category_unsupported")
    if _strings(op.get("blocked_reasons")): reasons.append("primary_write_preflight_operation_blocked")
    reasons = _dedupe(reasons)
    if reasons: return _invalid(*reasons)
    return {"valid": True, **fields, "source_event_kind": event,
            "idempotency_key": idem, "blocked_reasons": []}


def _cross(lineage: Mapping[str, Any], exp: Mapping[str, Any], pre: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if exp["candidate_id"] != pre["candidate_id"]: reasons.append("primary_page_candidate_candidate_id_mismatch")
    if not exp["source_event_kind"] == pre["source_event_kind"] == lineage["source_event_kind"]:
        reasons.append("primary_page_candidate_source_event_kind_mismatch")
    if exp["namespace"] != lineage["namespace"]: reasons.append("primary_page_candidate_namespace_mismatch")
    expected = _stable(["relaymem-primary-write-preflight-v0", lineage["namespace"],
        lineage["source_event_kind"], lineage["lineage_fingerprint"], pre["candidate_id"],
        pre["source_event_kind"], pre["memory_layer"], pre["memory_kind"], pre["promotion_policy"]])
    if pre["idempotency_key"] != expected: reasons.append("primary_page_candidate_idempotency_key_mismatch")
    return reasons


def _page(lineage: Mapping[str, Any], exp: Mapping[str, Any], pre: Mapping[str, Any],
        dry: bool, apply: bool) -> dict[str, Any]:
    path = f"{TARGET_DIR[pre['target_category']]}/{pre['idempotency_key']}.md"
    meta = {"schema_version": "relaymem.primary_page.v0", "memory_layer": "primary",
        "memory_kind": pre["memory_kind"], "source_event_kind": pre["source_event_kind"],
        "promotion_policy": "free_to_update", "safety_scope": "ordinary_memory",
        "namespace": lineage["namespace"], "lineage_fingerprint": lineage["lineage_fingerprint"],
        "idempotency_key": pre["idempotency_key"], "summary_origin": exp["summary_origin"],
        "content_role": "evidence", "title": exp.get("title") or ""}
    front = "\n".join(f"{k}: {json.dumps(str(v), ensure_ascii=False)}" for k, v in meta.items())
    markdown = f"---\n{front}\n---\n# Primary memory\n\n## Summary\n\n{exp['summary_text'].strip()}\n"
    try: encoded = markdown.encode("utf-8")
    except UnicodeEncodeError: encoded, reasons = b"", ["primary_page_candidate_utf8_invalid"]
    else: reasons = ["primary_page_candidate_page_size_exceeded"] if len(encoded) > MAX_PAGE_BYTES else []
    status = "blocked" if reasons else "ready"
    return {"schema_version": CANDIDATE_SCHEMA, "runtime_private": True,
        "content_included": True, "raw_source_text_included": False,
        "raw_message_history_included": False, "raw_affect_estimates_included": False,
        "candidate_id": pre["candidate_id"], "source_event_kind": pre["source_event_kind"],
        "memory_layer": "primary", "memory_kind": pre["memory_kind"],
        "promotion_policy": "free_to_update", "safety_scope": "ordinary_memory",
        "namespace": lineage["namespace"], "target_category": pre["target_category"],
        "target_relative_path": path, "lineage_fingerprint": lineage["lineage_fingerprint"],
        "idempotency_key": pre["idempotency_key"], "summary_origin": exp["summary_origin"],
        "summary_chars": exp["summary_chars"], "page_markdown": markdown,
        "page_bytes": len(encoded), "page_digest": sha256(encoded).hexdigest() if encoded else "",
        "status": status, "writer_handoff_eligible": status == "ready" and bool(apply) and not bool(dry),
        "writes_memory": False, "applied": False, "blocked_reasons": reasons}


def _projection(pages: Sequence[Mapping[str, Any]], reasons: Sequence[str]) -> dict[str, Any]:
    return {"schema_version": PROJECTION_SCHEMA, "diagnostics_only": True,
        "content_free": True, "content_included": False, "candidate_id_included": False,
        "target_path_included": False, "lineage_fingerprint_included": False,
        "idempotency_key_included": False, "page_markdown_included": False,
        "page_digest_included": False, "raw_source_text_included": False,
        "raw_message_history_included": False, "raw_affect_estimates_included": False,
        "writes_memory": False, "page_candidate_count": len(pages),
        "status_counts": _counts(pages, "status"),
        "target_category_counts": _counts(pages, "target_category"),
        "blocked_reasons": list(reasons), "page_candidates": [
            {"operation_index": i, "source_event_kind": p["source_event_kind"],
             "memory_layer": "primary", "memory_kind": p["memory_kind"],
             "promotion_policy": p["promotion_policy"], "safety_scope": p["safety_scope"],
             "target_category": p["target_category"], "status": p["status"],
             "writer_handoff_eligible": p["writer_handoff_eligible"],
             "summary_chars": p["summary_chars"], "page_bytes": p["page_bytes"]}
            for i, p in enumerate(pages)]}


def _exact(value: Mapping[str, Any], expected: Mapping[str, Any], prefix: str) -> list[str]:
    return [f"{prefix}{key}_invalid" for key, wanted in expected.items() if value.get(key) != wanted]

def _invalid(*reasons: str) -> dict[str, Any]: return {"valid": False, "blocked_reasons": _dedupe(reasons)}
def _event(value: object) -> tuple[str, list[str]]:
    return (value, []) if isinstance(value, str) and value in EVENT_KINDS else ("unknown", ["source_event_kind_invalid"])
def _token(value: object, reason: str) -> tuple[str, list[str]]:
    if not isinstance(value, str): return "", [reason]
    value = value.strip()
    return ("", [reason]) if not value or len(value) > MAX_TOKEN or _bad(value) or any(c in value for c in "\n\r\t") else (value, [])
def _text(value: object, limit: int, reason: str, multiline: bool) -> tuple[str, list[str]]:
    if not isinstance(value, str): return "", [reason]
    value = value.strip()
    bad_lines = not multiline and any(c in value for c in "\n\r\t")
    return ("", [reason]) if not value or len(value) > limit or _bad(value) or bad_lines else (value, [])
def _optional_text(value: object, limit: int, reason: str) -> tuple[str | None, list[str]]:
    if value is None: return None, []
    text, reasons = _text(value, limit, reason, False); return text or None, reasons
def _bad(value: str) -> bool:
    return any((ord(c) < 32 and c not in "\n\t") or 0xD800 <= ord(c) <= 0xDFFF for c in value)
def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
def _stable(parts: Sequence[str]) -> str:
    h = sha256()
    for part in parts: h.update(part.encode("utf-8")); h.update(b"\0")
    return h.hexdigest()
def _strings(value: object) -> list[str]:
    return [x for x in value if isinstance(x, str) and x] if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []
def _dedupe(values: Sequence[str]) -> list[str]: return list(dict.fromkeys(x for x in values if x))
def _counts(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown")); result[value] = result.get(value, 0) + 1
    return result
