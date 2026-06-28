#!/usr/bin/env python3
"""E1-R4 grounded recall response smoke."""
from __future__ import annotations

from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context

USER_FACT = "CANARY_E1R4_USER_FACT_DO_NOT_LEAK favorite color is blue"


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
    public = result.to_log_dict()
    require(public["grounding_enabled"] is True, public)
    require(public["grounded_item_count"] == 1, public)
    require(public["evidence_content_included"] is False, public)
    require(USER_FACT not in repr(public), public)


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


def main() -> None:
    test_directly_supported_recall()
    test_no_retrieved_evidence()
    print("relaylm_e1r4_grounded_recall_response_smoke: ok")


if __name__ == "__main__":
    main()
