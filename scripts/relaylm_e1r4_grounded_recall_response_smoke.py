#!/usr/bin/env python3
"""E1-R4 grounded recall response smoke."""
from __future__ import annotations

from pathlib import Path

from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context

ROOT = Path(__file__).resolve().parents[1]
USER_FACT = "CANARY_E1R4_USER_FACT_DO_NOT_LEAK favorite color is blue"
PRIMARY_RECALL_FACT = "CANARY_E1R4_PRIMARY_RECALL_FACT_DO_NOT_LEAK favorite snack is senbei"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def eligible_memory(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "memory_id": "mem_e1r4_color",
        "revision": 3,
        "character_id": "default",
        "namespace": "e1r4_namespace",
        "lifecycle_state": "active",
        "provenance_source": "user_assertion",
        "fact_text": USER_FACT,
    }
    value.update(extra)
    return value


def test_directly_supported_recall() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[eligible_memory()],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "grounding_applied", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    items = context["evidence_items"]
    require(len(items) == 1, items)
    require(items[0]["support_level"] == "directly_supported", items)
    require(items[0]["provenance_source"] == "user_assertion", items)
    require(USER_FACT in items[0]["fact_text"], items)
    instruction = context["instruction"]
    require("Do not invent dates, names, preferences, quantities, relationships, or causes" in instruction, instruction)
    require("Answer only from directly supported evidence" in instruction, instruction)
    backend_messages = context["backend_messages"]
    require(USER_FACT in backend_messages[0]["content"], backend_messages)
    public = result.to_log_dict()
    require(public["grounding_enabled"] is True, public)
    require(public["grounded_item_count"] == 1, public)
    require(public["evidence_content_included"] is False, public)
    require(USER_FACT not in repr(public), public)


def test_current_primary_recall_selected_memories() -> None:
    selected_memory = {
        "memory_layer": "primary",
        "idempotency_key": "logical-memory-1",
        "physical_idempotency_key": "physical-memory-1",
        "revision": 7,
        "evidence_id": "evidence:0",
        "namespace": "e1r4_namespace",
        "summary": PRIMARY_RECALL_FACT,
        "snippet_text": PRIMARY_RECALL_FACT,
        "snippet_chars": len(PRIMARY_RECALL_FACT),
        "estimated_tokens": 8,
    }
    result = build_grounded_recall_context(
        retrieved_memories=[selected_memory],
        query_text="what is my favorite snack?",
        namespace="e1r4_namespace",
    )
    require(result.status == "grounding_applied", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    items = context["evidence_items"]
    require(len(items) == 1, items)
    require(items[0]["support_level"] == "directly_supported", items)
    require(items[0]["provenance_source"] == "primary_recall_selected_memory", items)
    require(items[0]["revision_ref"] == "rev:7", items)
    require(PRIMARY_RECALL_FACT in items[0]["fact_text"], items)
    require(PRIMARY_RECALL_FACT in context["backend_messages"][0]["content"], context)
    require(PRIMARY_RECALL_FACT not in repr(result.to_log_dict()), result.to_log_dict())


def test_no_retrieved_evidence() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "no_retrieved_evidence", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(context["evidence_items"] == [], context)
    require("No retrieved evidence is present" in context["instruction"], context)
    require("do not claim to remember" in context["instruction"], context)
    require(USER_FACT not in repr(context), context)


def test_request_path_wiring() -> None:
    source = (ROOT / "relaylm" / "relayctx_repack.py").read_text(encoding="utf-8")
    require("build_grounded_recall_context" in source, "E1-R4 helper not wired")
    require("relaymem_grounded_recall_response" in source, "E1-R4 import missing")
    require("relaymem_grounded_recall_response" in source, "E1-R4 pipeline step missing")
    require("grounded_recall_projection" in source, "E1-R4 public projection missing")


def main() -> None:
    test_directly_supported_recall()
    test_current_primary_recall_selected_memories()
    test_no_retrieved_evidence()
    test_request_path_wiring()
    print("relaylm_e1r4_grounded_recall_response_smoke: ok")


if __name__ == "__main__":
    main()
