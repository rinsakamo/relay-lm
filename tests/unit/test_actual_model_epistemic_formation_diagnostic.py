from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_epistemic_formation_diagnostic import (
    DIAGNOSTIC_SCHEMA_NAME,
    EPISTEMIC_FORMATION_INSTRUCTION,
    EPISTEMIC_FORMATION_SCHEMA,
    EPISTEMIC_FORMATION_SYSTEM_INSTRUCTION,
    build_epistemic_formation_request_body,
    build_t2_epistemic_formation_input,
    parse_epistemic_formation_wire,
    serialize_epistemic_formation_input,
)
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.storage.filesystem import CharacterDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PROMPT_TERMS = (
    "unresolved",
    "open_question",
    "Continuity",
    "continuity_candidate",
    "set",
    "resolve",
    "blue_box",
    "box_contents_question",
    "机の青い箱",
)


class _BodyProvider:
    model = "gemma-local"

    def _resolve_llama_cpp_pass_request(self, *, pass_request, reasoning_request):
        assert reasoning_request is None
        assert pass_request.reasoning_mode is CognitionReasoningMode.OFF
        assert pass_request.structured_output_mode is CognitionStructuredOutputMode.NATIVE
        return (
            OpenAICompatibleDecodingConfig(
                temperature=pass_request.temperature,
                top_p=pass_request.top_p,
            ),
            OpenAICompatibleReasoningRequest(mode="off", token_budget=None),
        )

    def _llama_cpp_reasoning_fields(self, request):
        assert request is not None
        assert request.mode == "off"
        assert request.token_budget is None
        return {"reasoning_effort": "none"}


def _input():
    authority = load_stage_r_semantic_authority(
        REPO_ROOT / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=REPO_ROOT,
        authority=authority,
    )
    fixture = CharacterDirectory(REPO_ROOT / "evaluation/actual_model/characters/foundation-v1")
    return build_t2_epistemic_formation_input(
        identity=fixture.load_identity(),
        state=fixture.load_state(),
        scenario=scenario_set.scenario("continuity-lifecycle-v1").scenario,
        scenario_set_revision=authority.scenario_set_revision,
    )


def test_instruction_and_native_schema_are_fixture_independent() -> None:
    prompt = f"{EPISTEMIC_FORMATION_SYSTEM_INSTRUCTION}\n{EPISTEMIC_FORMATION_INSTRUCTION}"
    for term in FORBIDDEN_PROMPT_TERMS:
        assert term not in prompt
    serialized_schema = json.dumps(EPISTEMIC_FORMATION_SCHEMA, ensure_ascii=False)
    for term in FORBIDDEN_PROMPT_TERMS:
        assert term not in serialized_schema
    assert set(EPISTEMIC_FORMATION_SCHEMA["properties"]) == {"items"}


def test_t2_input_is_current_and_has_only_prior_user_context() -> None:
    cognitive_input = _input()
    serialized = serialize_epistemic_formation_input(cognitive_input)
    assert serialized["input"]["content"] == (
        "それの中身は何だと思う？まだ開けていないから、答えは未解決のままにして。"
    )
    assert [item["content"] for item in serialized["context"]] == [
        "机の青い箱の話を続けたい。次のターンで『それ』と言うよ。中身をあとで確認する作業も続けたい。"
    ]
    serialized_text = json.dumps(serialized, ensure_ascii=False)
    assert "box_contents_question" not in serialized_text
    assert "開けたら空だった" not in serialized_text
    assert "continuity" not in serialized_text.casefold()


def test_request_body_uses_exact_native_schema_and_reasoning_off() -> None:
    body = build_epistemic_formation_request_body(
        provider=_BodyProvider(),
        cognitive_input=_input(),
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            structured_output_mode=CognitionStructuredOutputMode.NATIVE,
        ),
    )
    assert body["reasoning_effort"] == "none"
    assert body["stream"] is False
    assert body["response_format"]["json_schema"]["name"] == DIAGNOSTIC_SCHEMA_NAME
    assert body["response_format"]["json_schema"]["schema"] == EPISTEMIC_FORMATION_SCHEMA
    instruction = body["messages"][0]["content"] + body["messages"][1]["content"]
    # The scenario text is present in the input block; inspect the instruction
    # separately so a legitimate current-input phrase is not treated as a hint.
    instruction = instruction.split("</CURRENT_INPUT>\n\n", 1)[-1]
    for term in FORBIDDEN_PROMPT_TERMS:
        assert term not in instruction


def test_source_event_and_substrings_fail_closed() -> None:
    cognitive_input = _input()
    valid = {
        "items": [
            {
                "subject_span": "それの中身",
                "unknown_evidence_span": "まだ開けていない",
                "source_event_id": cognitive_input.input.id,
            }
        ]
    }
    output = parse_epistemic_formation_wire(wire=valid, cognitive_input=cognitive_input)
    assert output.items[0].source_event_id == cognitive_input.input.id

    wrong_source = json.loads(json.dumps(valid))
    wrong_source["items"][0]["source_event_id"] = "event-not-current"
    with pytest.raises(ProviderProtocolError, match="source_event_id"):
        parse_epistemic_formation_wire(wire=wrong_source, cognitive_input=cognitive_input)

    wrong_span = json.loads(json.dumps(valid))
    wrong_span["items"][0]["subject_span"] = "not in input"
    with pytest.raises(ProviderProtocolError, match="subject_span"):
        parse_epistemic_formation_wire(wire=wrong_span, cognitive_input=cognitive_input)


@pytest.mark.parametrize(
    "wire",
    [
        {"items": [], "extra": True},
        {"items": [{"subject_span": "それの中身"}]},
        {
            "items": [
                {
                    "subject_span": "それの中身",
                    "unknown_evidence_span": "まだ開けていない",
                    "source_event_id": "event",
                    "extra": "reject",
                }
            ]
        },
        {"items": "not-an-array"},
    ],
)
def test_malformed_or_extra_wire_content_is_rejected(wire: object) -> None:
    with pytest.raises(ProviderProtocolError):
        parse_epistemic_formation_wire(wire=wire, cognitive_input=_input())
