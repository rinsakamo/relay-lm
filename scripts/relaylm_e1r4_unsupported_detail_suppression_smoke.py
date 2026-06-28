#!/usr/bin/env python3
"""E1-R4 unsupported-detail suppression smoke."""
from __future__ import annotations

from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context

SONG_FACT = "CANARY_E1R4_SONG_FACT_DO_NOT_LEAK user said they like the song 天体"
ASSISTANT_SPEC = "CANARY_E1R4_ASSISTANT_SPEC_DO_NOT_LEAK maybe they first heard it in 2024"
HIDDEN_FACT = "CANARY_E1R4_HIDDEN_FACT_DO_NOT_LEAK favorite color is red"
PINNED_FACT = "CANARY_E1R4_PINNED_FACT_DO_NOT_LEAK favorite color is blue"
UNPINNED_FACT = "CANARY_E1R4_UNPINNED_FACT_DO_NOT_LEAK favorite color is green"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def memory(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "memory_id": "mem_e1r4_default",
        "revision": 1,
        "character_id": "default",
        "namespace": "e1r4_namespace",
        "lifecycle_state": "active",
        "provenance_source": "user_assertion",
        "fact_text": SONG_FACT,
    }
    value.update(extra)
    return value


def test_unsupported_date_suppressed() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory()],
        query_text="When did I first hear it?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "unsupported_detail_suppressed", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(context["unsupported_detail_count"] == 1, context)
    require("does not support at least one requested detail" in context["instruction"], context)
    require("suppress or omit that detail" in context["instruction"], context)
    require("2024" not in repr(context), context)


def test_assistant_speculation_not_injected() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory(
            memory_id="mem_e1r4_assistant_spec",
            provenance_source="assistant_speculation",
            fact_text=ASSISTANT_SPEC,
        )],
        query_text="When did I first hear it?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "retrieval_excluded", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(context["evidence_items"] == [], context)
    require(ASSISTANT_SPEC not in repr(context), context)


def test_lifecycle_and_scope_exclusion_before_grounding() -> None:
    excluded_states = ["hidden", "prior", "prepared", "recovery_required", "corrupt"]
    for state in excluded_states:
        result = build_grounded_recall_context(
            retrieved_memories=[memory(memory_id=f"mem_{state}", lifecycle_state=state, fact_text=HIDDEN_FACT)],
            query_text="what is my favorite color?",
            character_id="default",
            namespace="e1r4_namespace",
        )
        require(result.status == "retrieval_excluded", (state, result))
        context = result.grounded_recall_context
        require(context is not None and context["evidence_items"] == [], context)
        require(HIDDEN_FACT not in repr(context), context)
    cross_scope = build_grounded_recall_context(
        retrieved_memories=[memory(character_id="other", fact_text=HIDDEN_FACT)],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(cross_scope.status == "retrieval_excluded", cross_scope)
    require(HIDDEN_FACT not in repr(cross_scope.grounded_recall_context), cross_scope)


def test_pin_ranking_does_not_create_support() -> None:
    hidden_pinned = memory(
        memory_id="mem_e1r4_hidden_pinned",
        lifecycle_state="hidden",
        pinned=True,
        fact_text=HIDDEN_FACT,
    )
    unpinned = memory(
        memory_id="mem_e1r4_unpinned",
        pinned=False,
        fact_text=UNPINNED_FACT,
    )
    pinned = memory(
        memory_id="mem_e1r4_pinned",
        pinned=True,
        fact_text=PINNED_FACT,
    )
    result = build_grounded_recall_context(
        retrieved_memories=[hidden_pinned, unpinned, pinned],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "grounding_applied", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    items = context["evidence_items"]
    require([item["memory_ref"] for item in items] == ["mem_e1r4_pinned", "mem_e1r4_unpinned"], items)
    require(HIDDEN_FACT not in repr(context), context)
    require(all(item["support_level"] == "directly_supported" for item in items), items)


def main() -> None:
    test_unsupported_date_suppressed()
    test_assistant_speculation_not_injected()
    test_lifecycle_and_scope_exclusion_before_grounding()
    test_pin_ranking_does_not_create_support()
    print("relaylm_e1r4_unsupported_detail_suppression_smoke: ok")


if __name__ == "__main__":
    main()
