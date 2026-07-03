#!/usr/bin/env python3
"""ACG-2 Query Detail Analyzer and Grounded Recall integration smoke."""
from __future__ import annotations

from relaylm.query_detail_analyzer import (
    QUERY_DETAIL_TYPES,
    analyze_query_detail_candidate,
)
from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context

FACT = "CANARY_ACG2_FACT user said they like the song 天体"
NO_PREF_FACT = "CANARY_ACG2_NO_PREF user said they heard the song 天体"
UNRELATED_PREF = "CANARY_ACG2_PREF favorite snack is senbei"
PRIVATE_PATIENT = "secret patient name"
PRIVATE_DATE = "private appointment date"
PRIVATE_BODY = "keyword:private body"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def memory(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "memory_id": "mem_acg2_default",
        "revision": 1,
        "character_id": "default",
        "namespace": "acg2_namespace",
        "lifecycle_state": "active",
        "provenance_source": "user_assertion",
        "fact_text": FACT,
    }
    value.update(extra)
    return value


def public_repr(value: object) -> str:
    return repr(value)


def assert_public_content_free(value: object) -> None:
    text = public_repr(value)
    for secret in (PRIVATE_PATIENT, PRIVATE_DATE, PRIVATE_BODY, FACT, NO_PREF_FACT, UNRELATED_PREF):
        require(secret not in text, text)


def context_for(query: str, fact_text: str = FACT, candidate: object | None = None):
    return build_grounded_recall_context(
        retrieved_memories=[memory(fact_text=fact_text)],
        query_text=query,
        query_detail_candidate=candidate,
        character_id="default",
        namespace="acg2_namespace",
    )


def test_english_detail_queries_still_suppress() -> None:
    cases = [
        ("When did I first hear it?", "date_or_time"),
        ("What name did I tell you?", "person_or_name"),
        ("How many times did I hear it?", "quantity"),
        ("What is my relationship to them?", "relationship"),
        ("Why did I like it?", "cause_or_reason"),
        ("What is my favorite color?", "preference"),
    ]
    for query, detail_type in cases:
        fact = UNRELATED_PREF if detail_type == "preference" else FACT
        result = context_for(query, fact)
        context = result.grounded_recall_context
        require(result.status == "unsupported_detail_suppressed", (query, result))
        require(context is not None, result)
        require(detail_type in context["query_detail_types"], context)
        require(context["unsupported_detail_count"] >= 1, context)


def test_japanese_detail_queries_still_suppress() -> None:
    cases = [
        ("いつ初めて聞いた？", "date_or_time"),
        ("名前は何？", "person_or_name"),
        ("何回聞いた？", "quantity"),
        ("関係は？", "relationship"),
        ("理由は？", "cause_or_reason"),
        ("好きな色は？", "preference"),
    ]
    for query, detail_type in cases:
        fact = NO_PREF_FACT if detail_type == "preference" else FACT
        result = context_for(query, fact)
        context = result.grounded_recall_context
        require(result.status == "unsupported_detail_suppressed", (query, result))
        require(context is not None, result)
        require(detail_type in context["query_detail_types"], context)


def test_fixed_english_enum_values() -> None:
    analysis = analyze_query_detail_candidate(query_text="When and why did I like it?")
    require(set(analysis.requested_detail_types).issubset(QUERY_DETAIL_TYPES), analysis)
    require(all(value.isascii() for value in analysis.requested_detail_types), analysis)
    public = analysis.to_public_dict()
    require(public["requested_detail_types"] == analysis.requested_detail_types, public)
    require(public["content_free"] is True, public)


def test_unknown_or_malformed_detail_fails_closed_without_raw_leak() -> None:
    candidate = {
        "source": "llm_candidate",
        "source_language": "en",
        "requested_detail_types": [PRIVATE_BODY],
        "confidence": 0.9,
        "policy_authority": "bounded",
        "source_authoritative": True,
        "candidate_applied": True,
        "restrictive_only": False,
        "raw_user_text": PRIVATE_PATIENT,
        "rationale": PRIVATE_DATE,
    }
    result = context_for("Please recall the detail.", candidate=candidate)
    context = result.grounded_recall_context
    require(result.status == "unsupported_detail_suppressed", result)
    require(context is not None, result)
    require("unknown" in context["query_detail_types"], context)
    require(context["unsupported_detail_count"] >= 1, context)
    assert_public_content_free(context["query_detail_analysis"])
    assert_public_content_free(result.to_log_dict())


def test_fallback_regex_cannot_open_policy() -> None:
    candidate = {
        "source": "fallback_regex",
        "source_language": "en",
        "requested_detail_types": ["date_or_time"],
        "confidence": 1.0,
        "stability": 1.0,
        "source_authoritative": True,
        "candidate_applied": True,
        "policy_authority": "bounded",
        "restrictive_only": False,
    }
    analysis = analyze_query_detail_candidate(query_text="", candidate=candidate)
    require(analysis.source_authoritative is False, analysis)
    require(analysis.restrictive_only is True, analysis)
    require(analysis.policy_authority in {"none", "restrictive"}, analysis)


def test_llm_candidate_cannot_open_policy() -> None:
    candidate = {
        "source": "llm_candidate",
        "source_language": "en",
        "requested_detail_types": ["quantity"],
        "confidence": 1.0,
        "stability": 1.0,
        "source_authoritative": True,
        "candidate_applied": True,
        "policy_authority": "bounded",
        "restrictive_only": False,
    }
    analysis = analyze_query_detail_candidate(query_text="", candidate=candidate)
    require(analysis.source_authoritative is False, analysis)
    require(analysis.restrictive_only is True, analysis)
    require(analysis.policy_authority in {"none", "restrictive"}, analysis)


def test_missing_analyzer_output_preserves_legacy_suppression() -> None:
    result = context_for("When did I first hear it?", candidate=None)
    context = result.grounded_recall_context
    require(result.status == "unsupported_detail_suppressed", result)
    require(context is not None, result)
    require(context["unsupported_detail_count"] == 1, context)
    require("date_or_time" in context["query_detail_types"], context)


def test_public_diagnostics_are_content_free() -> None:
    result = context_for(
        "When was the private appointment date?",
        fact_text=f"{PRIVATE_PATIENT} {PRIVATE_DATE} favorite snack is senbei",
    )
    require(result.grounded_recall_context is not None, result)
    assert_public_content_free(result.to_log_dict())
    assert_public_content_free(result.grounded_recall_context["query_detail_analysis"])


def test_location_identity_support_matching_stays_fail_closed() -> None:
    location_result = context_for(
        "Where did I meet Alice?",
        fact_text="user said they are interested in music",
    )
    location_context = location_result.grounded_recall_context
    require(location_result.status == "unsupported_detail_suppressed", location_result)
    require(location_context is not None, location_result)
    require("location" in location_context["query_detail_types"], location_context)
    require(location_context["unsupported_detail_count"] >= 1, location_context)

    country_music_result = context_for(
        "Where did I meet Alice?",
        fact_text="user said they like country music",
    )
    country_music_context = country_music_result.grounded_recall_context
    require(country_music_result.status == "unsupported_detail_suppressed", country_music_result)
    require(country_music_context is not None, country_music_result)
    require("location" in country_music_context["query_detail_types"], country_music_context)
    require(country_music_context["unsupported_detail_count"] >= 1, country_music_context)

    identity_result = context_for(
        "Who am I?",
        fact_text="user is interested in music",
    )
    identity_context = identity_result.grounded_recall_context
    require(identity_result.status == "unsupported_detail_suppressed", identity_result)
    require(identity_context is not None, identity_result)
    require("identity" in identity_context["query_detail_types"], identity_context)
    require(identity_context["unsupported_detail_count"] >= 1, identity_context)


def test_identity_query_does_not_require_name_detail() -> None:
    result = context_for(
        "Who am I?",
        fact_text="user profile: software engineer",
    )
    context = result.grounded_recall_context
    require(result.status == "grounding_applied", result)
    require(context is not None, result)
    require(context["query_detail_types"] == ["identity"], context)
    require(context["unsupported_detail_count"] == 0, context)


def test_grounded_recall_consumes_analyzer_output_request_side_only() -> None:
    candidate = {
        "source": "trusted_explicit",
        "source_language": "en",
        "requested_detail_types": ["date_or_time"],
        "confidence": 0.95,
        "stability": 0.95,
        "source_authoritative": True,
        "candidate_applied": True,
        "policy_authority": "restrictive",
        "restrictive_only": True,
    }
    result = context_for("Please recall that detail.", candidate=candidate)
    context = result.grounded_recall_context
    require(result.status == "unsupported_detail_suppressed", result)
    require(context is not None, result)
    require(context["query_detail_types"] == ["date_or_time"], context)
    require("backend_messages" in context, context)
    require("visible_response" not in context, context)


def main() -> None:
    test_english_detail_queries_still_suppress()
    test_japanese_detail_queries_still_suppress()
    test_fixed_english_enum_values()
    test_unknown_or_malformed_detail_fails_closed_without_raw_leak()
    test_fallback_regex_cannot_open_policy()
    test_llm_candidate_cannot_open_policy()
    test_missing_analyzer_output_preserves_legacy_suppression()
    test_public_diagnostics_are_content_free()
    test_location_identity_support_matching_stays_fail_closed()
    test_identity_query_does_not_require_name_detail()
    test_grounded_recall_consumes_analyzer_output_request_side_only()
    print("relaylm_acg2_query_detail_analyzer_smoke: ok")


if __name__ == "__main__":
    main()
