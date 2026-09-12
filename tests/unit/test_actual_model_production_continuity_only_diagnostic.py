from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import relaylm.actual_model_production_continuity_only_diagnostic as diagnostic_module
import relaylm.providers.openai_compatible_extraction_projection as projection_module
from relaylm.actual_model_production_continuity_only_diagnostic import (
    build_continuity_only_extraction_request_body,
    parse_continuity_only_completion,
)
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    load_retained_formation_binding,
)
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


REVISION = "sha256:" + "a" * 64
T2 = "The parcel is still closed, so what is inside remains unknown."
STABLE_SOURCE = f"stage-r:{REVISION}:primary:turn-2"
CURRENT_SOURCE = "evt-run-local"


def _input() -> CognitiveInput:
    accepted_continuity = json.dumps(
        {
            "continuity": {
                "kind": "referent",
                "key": "current_parcel",
                "op": "set",
                "value": "the parcel",
                "sources": ["evt-t1"],
                "epistemic_role": "user_assertion",
            }
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return CognitiveInput(
        identity=Identity("Synthetic diagnostic identity."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="state-t1",
                state_class="user.fact",
                key="parcel_location",
                value="on the table",
                sources=("evt-t1",),
            ),
        ),
        context=(ContextItem(content=accepted_continuity, sources=("evt-t1",)),),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": T2},
            event_id=CURRENT_SOURCE,
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )


def _extraction() -> CognitionExtractionInput:
    return CognitionExtractionInput(
        cognitive_input=_input(),
        assistant_response="I cannot know until the parcel is opened.",
    )


def _payload() -> dict[str, object]:
    return {
        "diagnostic": "epistemic-formation-t2",
        "mechanical_validation": "pass",
        "items": [
            {
                "subject_span": "what is inside",
                "unknown_evidence_span": "remains unknown",
                "source_event_id": STABLE_SOURCE,
            }
        ],
    }


def _binding(tmp_path: Path):
    path = tmp_path / "retained.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    return load_retained_formation_binding(
        path=path,
        scenario_set_revision=REVISION,
        authoritative_t2_content=T2,
    )


class _Provider:
    model = "synthetic-model"

    def _resolve_llama_cpp_pass_request(self, *, pass_request, reasoning_request):
        assert reasoning_request is None
        assert pass_request is not None
        return (
            OpenAICompatibleDecodingConfig(temperature=0, top_p=1),
            OpenAICompatibleReasoningRequest(mode="off"),
        )

    def _llama_cpp_reasoning_fields(self, request):
        assert request is not None and request.mode == "off"
        return {"reasoning_effort": "none"}


def _pass_request() -> CognitionPassRequest:
    return CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
    )


def test_continuity_only_builder_holds_context_and_overlay_fixed(tmp_path: Path) -> None:
    prepared = build_continuity_only_extraction_request_body(
        provider=_Provider(),
        extraction_input=_extraction(),
        pass_request=_pass_request(),
        binding=_binding(tmp_path),
    )

    receipt = prepared.diff_receipt
    assert receipt["same_system_instruction"] is True
    assert receipt["same_cognitive_input_and_pass1_prefix"] is True
    assert receipt["same_continuity_component"] is True
    assert receipt["same_retained_overlay"] is True
    assert receipt["same_nonprojection_request_fields"] is True
    assert receipt["production_has_state_component"] is True
    assert receipt["continuity_only_has_state_component"] is False
    assert receipt["production_schema_properties"] == [
        "continuity_candidates",
        "state_candidates",
    ]
    assert receipt["continuity_only_schema_properties"] == ["continuity_candidates"]
    assert receipt["removed_model_facing_responsibility"] == [
        "state_extraction_instruction",
        "state_candidates_output_schema",
    ]

    assert prepared.retained_source_event_id == STABLE_SOURCE
    assert prepared.run_local_source_event_id == CURRENT_SOURCE
    assert prepared.model_overlay == (
        {
            "subject_span": "what is inside",
            "unknown_evidence_span": "remains unknown",
            "source_event_id": "E0",
        },
    )

    production_content = prepared.production_overlay_body["messages"][1]["content"]
    diagnostic_content = prepared.continuity_only_overlay_body["messages"][1]["content"]
    for expected in (
        "parcel_location",
        "on the table",
        "current_parcel",
        "the parcel",
        "I cannot know until the parcel is opened.",
        "what is inside",
        "remains unknown",
        "E0",
    ):
        assert expected in production_content
        assert expected in diagnostic_content
    assert CURRENT_SOURCE not in production_content
    assert CURRENT_SOURCE not in diagnostic_content

    schema = prepared.continuity_only_overlay_body["response_format"]["json_schema"]
    assert schema["name"] == "relaylm_continuity_only_extraction_output"
    assert schema["strict"] is True
    assert set(schema["schema"]["properties"]) == {"continuity_candidates"}
    assert "state_candidates" not in schema["schema"]["properties"]


def test_continuity_only_overlay_has_no_answer_fields(tmp_path: Path) -> None:
    prepared = build_continuity_only_extraction_request_body(
        provider=_Provider(),
        extraction_input=_extraction(),
        pass_request=_pass_request(),
        binding=_binding(tmp_path),
    )
    content = prepared.continuity_only_overlay_body["messages"][1]["content"]
    block = content.split("<RETAINED_FORMED_OBSERVATIONS>\n", 1)[1].split(
        "\n</RETAINED_FORMED_OBSERVATIONS>", 1
    )[0]
    payload = json.loads(block)
    item = payload["formed_epistemic_observations"][0]

    assert set(item) == {"subject_span", "unknown_evidence_span", "source_event_id"}
    assert item["source_event_id"] == "E0"
    assert CURRENT_SOURCE not in block
    assert '"kind"' not in block
    assert '"key"' not in block
    assert '"op"' not in block
    assert '"value"' not in block


def _envelope(payload: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                },
            }
        ]
    }


def test_continuity_only_parser_uses_canonical_candidate_and_source_contract() -> None:
    output = parse_continuity_only_completion(
        _envelope(
            {
                "continuity_candidates": [
                    {
                        "kind": "unresolved",
                        "key": "parcel_contents",
                        "op": "set",
                        "value": "contents remain unknown",
                        "sources": ["E0"],
                        "epistemic_role": "user_assertion",
                    }
                ]
            }
        ),
        cognitive_input=_input(),
    )

    assert output.state_candidates == ()
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"
    assert output.continuity_candidates[0].sources == (CURRENT_SOURCE,)

    with pytest.raises(ProviderProtocolError, match="exactly continuity_candidates"):
        parse_continuity_only_completion(
            _envelope({"state_candidates": [], "continuity_candidates": []}),
            cognitive_input=_input(),
        )

    with pytest.raises(ProviderProtocolError, match="provenance alias"):
        parse_continuity_only_completion(
            _envelope(
                {
                    "continuity_candidates": [
                        {
                            "kind": "unresolved",
                            "key": "parcel_contents",
                            "op": "set",
                            "value": "contents remain unknown",
                            "sources": ["E999"],
                            "epistemic_role": "user_assertion",
                        }
                    ]
                }
            ),
            cognitive_input=_input(),
        )


def test_continuity_only_builder_inherits_retained_binding_fail_closed(tmp_path: Path) -> None:
    bad = _payload()
    bad["items"][0]["unknown_evidence_span"] = "not present"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")

    with pytest.raises(ProviderProtocolError, match="substring"):
        load_retained_formation_binding(
            path=path,
            scenario_set_revision=REVISION,
            authoritative_t2_content=T2,
        )


def test_discriminator_source_contains_no_fixture_answer_or_runtime_substitution() -> None:
    source = inspect.getsource(diagnostic_module) + inspect.getsource(projection_module)

    for forbidden in (
        "blue_box",
        "box_contents_question",
        "monkeypatch",
        "setattr(",
        "sys.modules",
        "sys.meta_path",
        "importlib",
    ):
        assert forbidden not in source
