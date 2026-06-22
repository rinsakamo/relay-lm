"""Primary page verification helpers for RelayMEM M3h."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from ._relaymem_primary_page_writer_common import (
    KIND_TARGET,
    MAX_SUMMARY,
    MAX_TITLE,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    parse_page_markdown,
)


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
    }
    reasons = [
        f"primary_reconciliation_recovery_page_{field}_mismatch"
        for field, wanted in expected.items()
        if metadata.get(field) != wanted
    ]
    if expected_path != receipt["page_relative_path"]:
        reasons.append("primary_reconciliation_recovery_page_path_binding_mismatch")
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or len(summary) > MAX_SUMMARY
        or parsed.get("body") != f"# Primary memory\n\n## Summary\n\n{summary}\n"
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
