#!/usr/bin/env python3
"""Smoke tests for E1-R4 grounded recall response behavior."""
from __future__ import annotations

from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def memory(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "memory_id": "mem1",
        "revision": 3,
        "character_id": "char1",
        "namespace": "ns1",
        "lifecycle_state": "active",
        "provenance_source": "user_assertion",
        "fact_text": "user said their favorite song is 天体",
    }
    value.update(extra)
    return value


def test_supported_evidence_injected() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory()],
        query_text="What is my favorite song?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "grounding_applied", result)
    require(result.backend_request_changed is True, result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(context["schema_version"] == "relaymem.grounded_recall_context.v0", context)
    require(len(context["evidence_items"]) == 1, context)
    require("Do not invent dates, names, preferences, quantities, relationships, locations, identities, or causes" in context["instruction"], context)
    log = result.to_log_dict()
    require(log["content_free"] is True, log)
    require(log["grounded_item_count"] == 1, log)
    require(log["raw_memory_text_included"] is False, log)
    require("天体" not in repr(log), log)


def test_unsupported_detail_suppressed() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory(fact_text="user said they like a song")],
        query_text="When did I first hear it?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "unsupported_detail_suppressed", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(context["unsupported_detail_count"] >= 1, context)
    require("requested_detail_not_supported_by_retrieved_memory" in result.blocked_reasons, result)


def test_excluded_evidence_not_used() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory(lifecycle_state="hidden")],
        query_text="What is my favorite song?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "retrieval_excluded", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(len(context["evidence_items"]) == 0, context)
    require(context["excluded_evidence"][0]["content_included"] is False, context)


def test_provenance_required() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory(provenance_source="assistant_speculation")],
        query_text="What is my favorite song?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "retrieval_excluded", result)
    require("unsupported_provenance" in result.blocked_reasons, result)


def test_scope_isolation() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[memory(character_id="other")],
        query_text="What is my favorite song?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "retrieval_excluded", result)
    require("character_scope_mismatch" in result.blocked_reasons, result)


def test_no_evidence_context() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[],
        query_text="What is my favorite song?",
        character_id="char1",
        namespace="ns1",
    )
    require(result.status == "no_retrieved_evidence", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require("No retrieved evidence is present" in context["instruction"], context)


def main() -> None:
    test_supported_evidence_injected()
    test_unsupported_detail_suppressed()
    test_excluded_evidence_not_used()
    test_provenance_required()
    test_scope_isolation()
    test_no_evidence_context()
    print("relaylm_e1r4_grounded_recall_response_smoke: ok")


if __name__ == "__main__":
    main()
