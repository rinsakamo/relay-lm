from __future__ import annotations

import hashlib
import json

import pytest

import relaylm.v2_cognitive_ir_strict_output_interface_qualification as ifq


def synthetic_payload() -> dict[str, object]:
    return {
        "operation": "affine_permutation",
        "permutation": [2, 0, 3, 1],
        "offsets": [1, 2, 0, 4],
        "modulus": 10,
        "provenance_handles": ["ifq-ref-a", "ifq-ref-b"],
    }


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_seed_identity_is_exact_unique_and_historically_disjoint() -> None:
    seeds = ifq.preregistered_case_seeds()
    assert len(seeds) == ifq.CASE_COUNT == 18
    assert len(set(seeds)) == 18
    for index, seed in enumerate(seeds):
        raw = hashlib.sha256(
            f"{ifq.PREREGISTRATION_LABEL}|case|{index}".encode()
        ).digest()
        assert seed == int.from_bytes(raw[:8], "big")
    assert not (set(seeds) & ifq.historical_case_seeds())
    ifq.validate_seed_admission()


def test_repository_binding_does_not_authorize_or_materialize_physical_cases() -> None:
    assert ifq.PHYSICAL_EXECUTION_AUTHORIZED is False
    assert not hasattr(ifq, "generate_preregistered_case")
    assert not hasattr(ifq, "materialize_preregistered_cases")


def test_response_format_is_one_mechanical_strict_schema() -> None:
    payload = ifq.response_format()
    assert payload["type"] == "json_schema"
    json_schema = payload["json_schema"]
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(ifq.SCORED_FIELDS)
    assert not _contains_key(schema, "const")
    assert not _contains_key(schema, "enum")


def test_neutral_request_exposes_only_visible_reference_payload() -> None:
    messages = ifq.build_neutral_messages(synthetic_payload())
    assert [message["role"] for message in messages] == ["system", "user"]
    assert messages[1]["content"].startswith("REFERENCE_PAYLOAD\n{")
    model_facing = "\n".join(message["content"] for message in messages)
    for marker in (
        "P4_MEMORY_PLUS_STRUCTURE",
        "P6_GENERIC_EQUAL_INFORMATION",
        "MEMORY_PLUS_STRUCTURE",
        "GENERIC_EQUAL_INFORMATION",
        '"memory"',
        '"structure"',
        '"context"',
        '"relation"',
    ):
        assert marker not in model_facing


def test_strict_parser_accepts_only_bare_valid_five_field_object() -> None:
    expected = synthetic_payload()
    text = json.dumps(expected, separators=(",", ":"))
    assert ifq.parse_strict_completion(text) == expected

    with pytest.raises(ifq.StrictOutputInterfaceQualificationError):
        ifq.parse_strict_completion(f"```json\n{text}\n```")

    extra = dict(expected, extra=True)
    with pytest.raises(ifq.StrictOutputInterfaceQualificationError):
        ifq.parse_strict_completion(json.dumps(extra))

    with pytest.raises(ifq.StrictOutputInterfaceQualificationError):
        ifq.parse_strict_completion(
            '{"operation":"affine_permutation","operation":"x",'
            '"permutation":[2,0,3,1],"offsets":[1,2,0,4],'
            '"modulus":10,"provenance_handles":["ifq-ref-a"]}'
        )

    with pytest.raises(ifq.StrictOutputInterfaceQualificationError):
        ifq.parse_strict_completion(
            '{"operation":"affine_permutation","permutation":[2,0,3,1],'
            '"offsets":[1,2,0,4],"modulus":NaN,'
            '"provenance_handles":["ifq-ref-a"]}'
        )


def test_visible_copy_score_uses_only_visible_reference_values() -> None:
    expected = synthetic_payload()
    exact = json.dumps(expected, separators=(",", ":"))
    score = ifq.score_completion(exact, expected)
    assert score.strict_parse_valid is True
    assert score.visible_payload_copy_exact is True
    assert score.failure_reason is None

    different = dict(expected)
    different["offsets"] = [1, 2, 0, 5]
    mismatch = ifq.score_completion(
        json.dumps(different, separators=(",", ":")), expected
    )
    assert mismatch.strict_parse_valid is True
    assert mismatch.visible_payload_copy_exact is False


def test_completed_qualification_requires_exact_frozen_gates() -> None:
    qualified_scores = tuple(
        ifq.InterfaceQualificationScore(True, True, None)
        for _ in range(ifq.CASE_COUNT)
    )
    base = {
        "provider_attempts": 18,
        "provider_completions": 18,
        "input_count_attempts": 36,
        "input_count_completions": 36,
        "rescue_counts": ifq.FORBIDDEN_RESCUE_COUNTS,
        "truncation_failures": 0,
        "identity_checks_passed": True,
    }
    assert (
        ifq.classify_qualification(qualified_scores, **base)
        == "STRICT_OUTPUT_INTERFACE_QUALIFIED"
    )

    one_copy_failure = (
        *qualified_scores[:16],
        ifq.InterfaceQualificationScore(True, False, "visible payload differs"),
        ifq.InterfaceQualificationScore(True, False, "visible payload differs"),
    )
    assert (
        ifq.classify_qualification(one_copy_failure, **base)
        == "STRICT_OUTPUT_INTERFACE_FAILED"
    )

    one_parse_failure = (
        *qualified_scores[:17],
        ifq.InterfaceQualificationScore(False, False, "invalid"),
    )
    assert (
        ifq.classify_qualification(one_parse_failure, **base)
        == "STRICT_OUTPUT_INTERFACE_FAILED"
    )


def test_incomplete_and_pre_wrapper_blocked_are_distinct() -> None:
    assert (
        ifq.classify_qualification(
            (),
            provider_attempts=1,
            provider_completions=0,
            input_count_attempts=2,
            input_count_completions=2,
            rescue_counts=ifq.FORBIDDEN_RESCUE_COUNTS,
            truncation_failures=0,
            identity_checks_passed=True,
        )
        == "QUALIFICATION_INCOMPLETE"
    )
    assert (
        ifq.classify_qualification(
            (),
            provider_attempts=0,
            provider_completions=0,
            input_count_attempts=0,
            input_count_completions=0,
            rescue_counts=ifq.FORBIDDEN_RESCUE_COUNTS,
            truncation_failures=0,
            identity_checks_passed=False,
            pre_wrapper_mechanical_blocked=True,
        )
        == "PRE_WRAPPER_MECHANICAL_BLOCKED"
    )


def test_frozen_accounting_and_no_rescue_contract() -> None:
    assert ifq.SEMANTIC_COMPLETIONS == 18
    assert ifq.INPUT_TOKEN_REQUESTS == 36
    assert ifq.CONTEXT_LIMIT == 8192
    assert ifq.MAX_OUTPUT_TOKENS == 256
    assert ifq.TEMPERATURE == 0.0
    assert ifq.REASONING == "none"
    assert ifq.REQUEST_SEED is None
    assert ifq.PARALLEL_SEMANTIC_SLOTS == 1
    assert ifq.STREAM is False
    assert set(ifq.FORBIDDEN_RESCUE_COUNTS.values()) == {0}
    assert ifq.CITABLE_FOR_REPRESENTATION_CLAIM is False
    assert ifq.ARCHITECTURE_CONSEQUENCE == "NONE"
