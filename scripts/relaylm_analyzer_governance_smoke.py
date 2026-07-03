"""Analyzer Candidate Governance contract smoke."""
from __future__ import annotations

import json

from relaylm.analyzer_governance import (
    ANALYZER_KINDS,
    POLICY_AUTHORITIES,
    SCHEMA_VERSION,
    SOURCE_CLASSES,
    analyzer_governance_enum_values,
    build_analyzer_candidate_artifact,
    can_open_runtime_policy,
    content_free_projection,
    is_policy_authoritative,
    validate_analyzer_candidate_artifact,
)


EXPECTED_PUBLIC_KEYS = {
    "analyzer_kind",
    "candidate_applied",
    "confidence_bucket",
    "content_free",
    "policy_authority",
    "reason_ids",
    "restrictive_only",
    "schema_version",
    "source_authoritative",
    "source_class",
    "stability_bucket",
    "validation_error_ids",
}


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assert_content_free(value: object) -> None:
    serialized = _serialized(value)
    forbidden = [
        "secret patient name",
        "free-form private detail",
        "private user message",
        "LLM says private",
        "keyword:private body",
        "SECRET_USER_TEXT",
        "SECRET_MODEL_OUTPUT",
    ]
    for token in forbidden:
        assert token not in serialized, serialized


def main() -> None:
    trusted = build_analyzer_candidate_artifact(
        analyzer_kind="query_detail_candidate",
        source="trusted_explicit",
        source_language="en",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="bounded",
        restrictive_only=False,
        confidence=0.9,
        stability=0.8,
        content_free=True,
    )
    trusted_result = validate_analyzer_candidate_artifact(trusted)
    assert trusted_result.is_valid is True
    assert is_policy_authoritative(trusted) is True
    assert can_open_runtime_policy(trusted) is True
    trusted_public = content_free_projection(trusted)
    assert trusted_public["source_class"] == "trusted_explicit"
    assert trusted_public["policy_authority"] == "bounded"
    assert trusted_public["confidence_bucket"] == "high"
    assert trusted_public["stability_bucket"] == "high"
    assert set(trusted_public) == EXPECTED_PUBLIC_KEYS
    assert trusted_public["content_free"] is True

    direct_raw = {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": "query_detail_candidate",
        "source": "trusted_explicit",
        "source_language": "en",
        "source_authoritative": True,
        "candidate_applied": True,
        "policy_authority": "bounded",
        "restrictive_only": False,
        "confidence": 0.9,
        "stability": 0.8,
        "content_free": True,
        "raw_user_text": "private user message",
        "rationale": "LLM says private ...",
        "future_private_field": "SECRET_USER_TEXT",
    }
    direct_result = validate_analyzer_candidate_artifact(direct_raw)
    direct_public = direct_result.to_public_dict()
    assert direct_result.is_valid is False
    assert can_open_runtime_policy(direct_raw) is False
    assert "raw_diagnostic_field_dropped" in direct_public["validation_error_ids"]
    assert "unsupported_field_dropped" in direct_public["validation_error_ids"]
    _assert_content_free(direct_public)

    enum_non_string_raw = {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": "query_detail_candidate",
        "source": "trusted_explicit",
        "source_language": "en",
        "source_authoritative": True,
        "candidate_applied": True,
        "policy_authority": "bounded",
        "restrictive_only": False,
        "confidence": 0.9,
        "stability": 0.8,
        "content_free": True,
        "enum_values": [123],
    }
    enum_non_string_result = validate_analyzer_candidate_artifact(enum_non_string_raw)
    enum_non_string_public = enum_non_string_result.to_public_dict()
    assert enum_non_string_result.is_valid is False
    assert can_open_runtime_policy(enum_non_string_raw) is False
    assert "unknown_enum_value" in enum_non_string_public["validation_error_ids"]

    nonfinite = build_analyzer_candidate_artifact(
        analyzer_kind="query_detail_candidate",
        source="trusted_explicit",
        source_language="en",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="bounded",
        restrictive_only=False,
        confidence="nan",
        stability=float("inf"),
        content_free=True,
    )
    nonfinite_public = content_free_projection(nonfinite)
    assert can_open_runtime_policy(nonfinite) is False
    assert "malformed_confidence" in nonfinite_public["validation_error_ids"]
    assert "malformed_stability" in nonfinite_public["validation_error_ids"]

    single_reason = build_analyzer_candidate_artifact(
        analyzer_kind="affect_candidate",
        source="trusted_tool_signal",
        reason_ids="candidate_not_applied",
        policy_authority="none",
        content_free=True,
    )
    single_reason_public = content_free_projection(single_reason)
    assert "candidate_not_applied" in single_reason_public["reason_ids"]
    assert "malformed_reason_id" not in single_reason_public["validation_error_ids"]
    assert validate_analyzer_candidate_artifact(single_reason).is_valid is True

    heuristic = build_analyzer_candidate_artifact(
        analyzer_kind="retrieval_query_candidate",
        source="heuristic",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="open",
        restrictive_only=False,
        confidence=0.8,
        stability=0.8,
    )
    heuristic_public = content_free_projection(heuristic)
    assert heuristic["source_authoritative"] is False
    assert heuristic["policy_authority"] == "none"
    assert heuristic["restrictive_only"] is True
    assert can_open_runtime_policy(heuristic) is False
    assert "policy_authority_not_permitted" in heuristic_public["validation_error_ids"]

    llm_candidate = build_analyzer_candidate_artifact(
        analyzer_kind="reference_intent_candidate",
        source="llm_candidate",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="update",
        restrictive_only=False,
        confidence=0.7,
        stability=0.5,
    )
    llm_public = content_free_projection(llm_candidate)
    assert llm_candidate["source_authoritative"] is False
    assert llm_candidate["policy_authority"] == "none"
    assert llm_candidate["restrictive_only"] is True
    assert can_open_runtime_policy(llm_candidate) is False
    assert "llm_candidate_restrictive_only" in llm_public["reason_ids"]

    unknown_source = build_analyzer_candidate_artifact(
        analyzer_kind="affect_candidate",
        source="whatever",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="bounded",
        restrictive_only=False,
    )
    unknown_public = content_free_projection(unknown_source)
    assert unknown_source["source"] == "unknown"
    assert unknown_source["source_authoritative"] is False
    assert unknown_source["restrictive_only"] is True
    assert unknown_source["candidate_applied"] is False
    assert "invalid_source_class" in unknown_public["validation_error_ids"]

    leak_attempt = build_analyzer_candidate_artifact(
        analyzer_kind="scene_policy_candidate",
        source="trusted_route",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="bounded",
        restrictive_only=False,
        reason_ids=["secret patient name"],
        enum_values=["free-form private detail"],
        raw_text="private user message",
        rationale="LLM says private ...",
        signals=["keyword:private body"],
        raw_user_text="SECRET_USER_TEXT",
        raw_assistant_text="SECRET_MODEL_OUTPUT",
    )
    leak_public = content_free_projection(leak_attempt)
    _assert_content_free(leak_attempt)
    _assert_content_free(leak_public)
    assert "unknown_reason" in leak_public["reason_ids"]
    assert "malformed_reason_id" in leak_public["validation_error_ids"]
    assert "unknown_enum_value" in leak_public["validation_error_ids"]
    assert "raw_diagnostic_field_dropped" in leak_public["validation_error_ids"]
    assert leak_public["content_free"] is True

    malformed = build_analyzer_candidate_artifact(
        analyzer_kind="private analyzer name",
        source="trusted_explicit",
        source_authoritative=True,
        candidate_applied=True,
        policy_authority="private policy value",
        confidence="not-a-number",
        stability=1.5,
        content_free="yes",
    )
    malformed_public = content_free_projection(malformed)
    _assert_content_free(malformed_public)
    assert malformed["analyzer_kind"] == "unknown"
    assert malformed["policy_authority"] == "none"
    assert malformed["confidence"] == 0.0
    assert malformed["stability"] == 0.0
    assert malformed["content_free"] is False
    assert can_open_runtime_policy(malformed) is False
    assert "invalid_analyzer_kind" in malformed_public["validation_error_ids"]
    assert "unknown_policy_authority" in malformed_public["validation_error_ids"]

    for analyzer_kind in (
        "query_detail_candidate",
        "retrieval_query_candidate",
        "reference_intent_candidate",
        "affect_candidate",
        "scene_policy_candidate",
    ):
        artifact = build_analyzer_candidate_artifact(
            analyzer_kind=analyzer_kind,
            source="trusted_tool_signal",
            source_authoritative=False,
            candidate_applied=False,
            policy_authority="none",
        )
        assert artifact["analyzer_kind"] == analyzer_kind

    registries = analyzer_governance_enum_values()
    assert ANALYZER_KINDS <= set(registries["analyzer_kind"])
    assert SOURCE_CLASSES == set(registries["source_class"])
    assert POLICY_AUTHORITIES == set(registries["policy_authority"])

    for public_value in (
        trusted_public,
        direct_public,
        enum_non_string_public,
        nonfinite_public,
        single_reason_public,
        heuristic_public,
        llm_public,
        unknown_public,
        leak_public,
    ):
        assert set(public_value).issubset(EXPECTED_PUBLIC_KEYS | {"is_valid"})
        assert public_value["source_class"] in SOURCE_CLASSES
        assert public_value["policy_authority"] in POLICY_AUTHORITIES
        assert public_value["confidence_bucket"] in registries["confidence_bucket"]
        assert public_value["stability_bucket"] in registries["stability_bucket"]
        for key in public_value:
            assert key in registries["schema_key"], key
        _assert_content_free(public_value)


if __name__ == "__main__":
    main()
