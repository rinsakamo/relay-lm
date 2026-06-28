"""Primary page verification helpers for RelayMEM M3h."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    KIND_TARGET,
    MAX_SUMMARY,
    MAX_TITLE,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    token,
)


_BODY_PREFIX = "# Primary memory\n\n## Summary\n\n"


def apply_page_result(
    state: dict[str, Any], result: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    if result.get("valid") is not True:
        state["page_state"] = "missing" if result.get("status") == "missing" else "invalid"
        state["blocked_reasons"].extend(result.get("blocked_reasons", []))
        return
    content = result["content"]
    if sha256(content).hexdigest() != receipt["page_digest"]:
        state["page_state"] = "mismatch"
        state["blocked_reasons"].append("primary_reconciliation_recovery_page_digest_mismatch")
        return
    try:
        markdown = content.decode("utf-8")
    except UnicodeDecodeError:
        state["page_state"] = "invalid"
        state["blocked_reasons"].append("primary_reconciliation_recovery_page_utf8_invalid")
        return
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        state["page_state"] = "invalid"
        state["blocked_reasons"].append("primary_reconciliation_recovery_page_contract_invalid")
        return
    metadata = parsed["metadata"]
    memory_kind = metadata.get("memory_kind")
    target_category = KIND_TARGET.get(memory_kind) if isinstance(memory_kind, str) else None
    expected_path = (
        f"{TARGET_DIR[target_category]}/{receipt['idempotency_key']}.md"
        if isinstance(target_category, str) and target_category in TARGET_DIR
        else None
    )
    expected = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "idempotency_key": receipt["idempotency_key"],
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    reasons = [
        f"primary_reconciliation_recovery_page_{field}_mismatch"
        for field, wanted in expected.items()
        if metadata.get(field) != wanted
    ]
    if expected_path != receipt["page_relative_path"]:
        reasons.append("primary_reconciliation_recovery_page_path_binding_mismatch")
    if not isinstance(memory_kind, str) or memory_kind not in KIND_TARGET:
        reasons.append("primary_reconciliation_recovery_page_memory_kind_mismatch")
    event_kind = metadata.get("source_event_kind")
    if not isinstance(event_kind, str) or event_kind not in EVENT_KINDS:
        reasons.append("primary_reconciliation_recovery_page_source_event_kind_mismatch")
    _, namespace_reasons = token(
        metadata.get("namespace"),
        "primary_reconciliation_recovery_page_namespace_invalid",
    )
    reasons.extend(namespace_reasons)
    if not is_sha256(metadata.get("lineage_fingerprint")):
        reasons.append("primary_reconciliation_recovery_page_lineage_fingerprint_invalid")
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or len(summary) > MAX_SUMMARY
        or not _body_matches_summary(parsed.get("body"), summary)
    ):
        reasons.append("primary_reconciliation_recovery_page_summary_invalid")
    if (
        not isinstance(title, str)
        or title != title.strip()
        or len(title) > MAX_TITLE
        or bad_text(title)
        or any(char in title for char in "\n\r\t")
    ):
        reasons.append("primary_reconciliation_recovery_page_title_invalid")
    if reasons:
        state["page_state"] = "mismatch"
        state["blocked_reasons"].extend(reasons)
        return
    state["page_state"] = "verified"
    state["page_metadata"] = dict(metadata)


def _body_matches_summary(body: object, summary: str) -> bool:
    if not isinstance(body, str):
        return False
    exact = f"{_BODY_PREFIX}{summary}\n"
    if body == exact:
        return True
    if not body.startswith(_BODY_PREFIX):
        return False
    remainder = body[len(_BODY_PREFIX):]
    return remainder == summary or remainder.startswith(f"{summary}\n")
