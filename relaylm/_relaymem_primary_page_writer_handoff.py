"""M3d private handoff validation for RelayMEM M3e."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
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
    dedupe,
    exact,
    exact_fields,
    invalid,
    is_sha256,
    parse_page_markdown,
    path_reasons,
    stable_hash,
    strings,
    token,
)

M3D_HANDOFF_SCHEMA = "relaymem.primary_writer_handoff.v0"
M3D_HANDOFF_FIELDS = {
    "schema_version",
    "runtime_private",
    "content_included",
    "raw_source_text_included",
    "raw_message_history_included",
    "raw_affect_estimates_included",
    "candidate_id",
    "source_event_kind",
    "memory_layer",
    "memory_kind",
    "promotion_policy",
    "safety_scope",
    "namespace",
    "target_category",
    "target_relative_path",
    "lineage_fingerprint",
    "idempotency_key",
    "page_markdown",
    "page_bytes",
    "page_digest",
    "preflight_status",
    "target_exists",
    "target_digest_matches",
    "idempotent_noop",
    "upstream_writer_handoff_eligible",
    "writer_apply_eligible",
    "writes_memory",
    "updates_index",
    "updates_log",
    "applied",
    "blocked_reasons",
}


def parse_m3d_handoff(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != M3D_HANDOFF_SCHEMA:
        return invalid("primary_writer_handoff_schema_mismatch")
    reasons = exact_fields(
        value, M3D_HANDOFF_FIELDS, "primary_writer_handoff_fields_mismatch"
    )
    reasons.extend(
        exact(
            value,
            {
                "runtime_private": True,
                "content_included": True,
                "raw_source_text_included": False,
                "raw_message_history_included": False,
                "raw_affect_estimates_included": False,
                "memory_layer": "primary",
                "promotion_policy": "free_to_update",
                "safety_scope": "ordinary_memory",
                "preflight_status": "ready",
                "target_exists": False,
                "target_digest_matches": False,
                "idempotent_noop": False,
                "upstream_writer_handoff_eligible": True,
                "writer_apply_eligible": True,
                "writes_memory": False,
                "updates_index": False,
                "updates_log": False,
                "applied": False,
            },
            "primary_writer_handoff_",
        )
    )
    if strings(value.get("blocked_reasons")):
        reasons.append("primary_writer_handoff_blocked")

    candidate_id, candidate_reasons = token(
        value.get("candidate_id"), "primary_writer_handoff_candidate_id_invalid"
    )
    namespace, namespace_reasons = token(
        value.get("namespace"), "primary_writer_handoff_namespace_invalid"
    )
    reasons.extend(candidate_reasons + namespace_reasons)

    event_kind = value.get("source_event_kind")
    if not isinstance(event_kind, str) or event_kind not in EVENT_KINDS:
        reasons.append("primary_writer_handoff_source_event_kind_invalid")
        event_kind = "unknown"
    memory_kind = value.get("memory_kind")
    if not isinstance(memory_kind, str) or memory_kind not in KIND_TARGET:
        reasons.append("primary_writer_handoff_memory_kind_unsupported")
        memory_kind = "unknown"
    target_category = value.get("target_category")
    if not isinstance(target_category, str) or target_category not in TARGET_DIR:
        reasons.append("primary_writer_handoff_target_category_unsupported")
        target_category = "unknown"
    expected_category = KIND_TARGET.get(memory_kind)
    if expected_category is not None and target_category != expected_category:
        reasons.append("primary_writer_handoff_memory_kind_target_category_mismatch")

    lineage = value.get("lineage_fingerprint")
    key = value.get("idempotency_key")
    digest = value.get("page_digest")
    if not is_sha256(lineage):
        reasons.append("primary_writer_handoff_lineage_fingerprint_invalid")
    if not is_sha256(key):
        reasons.append("primary_writer_handoff_idempotency_key_invalid")
    if not is_sha256(digest):
        reasons.append("primary_writer_handoff_page_digest_invalid")

    if (
        candidate_id
        and namespace
        and event_kind in EVENT_KINDS
        and memory_kind in KIND_TARGET
        and is_sha256(lineage)
        and is_sha256(key)
    ):
        expected_key = stable_hash(
            (
                "relaymem-primary-write-preflight-v0",
                namespace,
                event_kind,
                lineage,
                candidate_id,
                event_kind,
                "primary",
                memory_kind,
                "free_to_update",
            )
        )
        if key != expected_key:
            reasons.append("primary_writer_handoff_idempotency_key_mismatch")

    target_path = value.get("target_relative_path")
    expected_path = (
        f"{TARGET_DIR[target_category]}/{key}.md"
        if target_category in TARGET_DIR and is_sha256(key)
        else ""
    )
    reasons.extend(path_reasons(target_path, expected_path))

    page_markdown = value.get("page_markdown")
    page_bytes = value.get("page_bytes")
    if not isinstance(page_markdown, str) or not page_markdown:
        reasons.append("primary_writer_handoff_page_markdown_invalid")
        page_markdown = ""
        encoded = b""
    else:
        try:
            encoded = page_markdown.encode("utf-8")
        except UnicodeEncodeError:
            encoded = b""
            reasons.append("primary_writer_handoff_page_utf8_invalid")
    if len(encoded) > MAX_PAGE_BYTES:
        reasons.append("primary_writer_handoff_page_size_exceeded")
    if (
        isinstance(page_bytes, bool)
        or not isinstance(page_bytes, int)
        or page_bytes != len(encoded)
    ):
        reasons.append("primary_writer_handoff_page_bytes_mismatch")
    if encoded and is_sha256(digest) and sha256(encoded).hexdigest() != digest:
        reasons.append("primary_writer_handoff_page_digest_mismatch")

    parsed_page = parse_page_markdown(page_markdown)
    if parsed_page.get("valid") is not True:
        reasons.extend(parsed_page["blocked_reasons"])
    else:
        metadata = parsed_page["metadata"]
        expected_metadata = {
            "schema_version": PAGE_SCHEMA,
            "memory_layer": "primary",
            "memory_kind": memory_kind,
            "source_event_kind": event_kind,
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "namespace": namespace,
            "lineage_fingerprint": lineage,
            "idempotency_key": key,
            "summary_origin": "trusted_in_process_summary",
            "content_role": "evidence",
        }
        for field, expected in expected_metadata.items():
            if metadata.get(field) != expected:
                reasons.append(f"primary_writer_handoff_page_{field}_mismatch")
        summary = metadata.get("summary", "")
        title = metadata.get("title", "")
        if (
            not isinstance(summary, str)
            or not summary
            or summary != summary.strip()
            or len(summary) > MAX_SUMMARY
        ):
            reasons.append("primary_writer_handoff_page_summary_invalid")
        if (
            not isinstance(title, str)
            or title != title.strip()
            or len(title) > MAX_TITLE
            or bad_text(title)
            or any(char in title for char in "\n\r\t")
        ):
            reasons.append("primary_writer_handoff_page_title_invalid")
        expected_body = f"# Primary memory\n\n## Summary\n\n{summary.strip()}\n"
        if parsed_page.get("body") != expected_body:
            reasons.append("primary_writer_handoff_page_body_mismatch")

    reasons = dedupe(reasons)
    if reasons:
        return invalid(*reasons)
    return {
        "valid": True,
        "candidate_id": candidate_id,
        "namespace": namespace,
        "source_event_kind": event_kind,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": target_category,
        "target_relative_path": target_path,
        "lineage_fingerprint": lineage,
        "idempotency_key": key,
        "page_markdown": page_markdown,
        "page_bytes": page_bytes,
        "page_digest": digest,
        "blocked_reasons": [],
    }
