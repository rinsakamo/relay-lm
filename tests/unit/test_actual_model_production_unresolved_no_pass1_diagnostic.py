from __future__ import annotations

import inspect
import json
from pathlib import Path

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    load_retained_formation_binding,
)
import relaylm.actual_model_production_unresolved_no_pass1_diagnostic as diagnostic_module
from relaylm.actual_model_production_unresolved_no_pass1_diagnostic import (
    build_unresolved_no_pass1_extraction_request_body,
    parse_unresolved_no_pass1_completion,
)
import relaylm.providers.openai_compatible_extraction_projection as projection_module
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_extraction_projection import (
    extraction_response_component,
    unresolved_only_continuity_extraction_component,
    unresolved_only_extraction_intro,
    unresolved_only_extraction_outro,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import _common_cognitive_prefix
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


REVISION = "sha256:" + "b" * 64
T2 = "The parcel is still closed, so what is inside remains unknown."
STABLE_SOURCE = f"stage-r:{REVISION}:primary:turn-2"
CURRENT_SOURCE = "evt-run-local"
PASS1 = "I cannot know what is inside until the parcel is opened."


def _continuity_item(*, kind: str, key: str, value: str) -> ContextItem:
    return ContextItem(
        content=json.dumps(
            {
                "continuity": {
                    "kind": kind,
                    "key": key,
                    "op": "set",
                    "value": value,
                    "sources": ["evt-t1"],
                    "epistemic_role": "user_assertion",
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        sources=("evt-t1",),
    )


def _input() -> CognitiveInput:
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
        context=(
            _continuity_item(
                kind="referent",
                key="current_parcel",
                value="the parcel",
            ),
            _continuity_item(
                kind="active_task",
                key="inspect_parcel",
                value="inspect the parcel contents",
            ),
        ),
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
        assistant_response=PASS1,
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


def test_no_pass1_builder_changes_only_canonical_pass1_component(tmp_path: Path) -> None:
    extraction = _extraction()
    prepared = build_unresolved_no_pass1_extraction_request_body(
        provider=_Provider(),
        extraction_input=extraction,
        pass_request=_pass_request(),
        binding=_binding(tmp_path),
    )

    baseline = prepared.baseline.unresolved_only_body
    no_pass1 = prepared.no_pass1_body
    baseline_content = baseline["messages"][1]["content"]
    no_pass1_content = no_pass1["messages"][1]["content"]
    prefix = _common_cognitive_prefix(extraction.cognitive_input)
    projection = (
        unresolved_only_extraction_intro()
        + unresolved_only_continuity_extraction_component("E0")
        + unresolved_only_extraction_outro()
    )
    pass1_component = extraction_response_component(extraction)

    assert baseline_content == prefix + pass1_component + projection
    assert no_pass1_content == prefix + projection
    assert "<PASS_1_RESPONSE_JSON>" in baseline_content
    assert PASS1 in baseline_content
    assert "<PASS_1_RESPONSE_JSON>" not in no_pass1_content
    assert PASS1 not in no_pass1_content

    for fixed in (
        "parcel_location",
        "on the table",
        "current_parcel",
        "the parcel",
        "inspect_parcel",
        "inspect the parcel contents",
        "what is inside",
        "remains unknown",
        CURRENT_SOURCE,
    ):
        assert fixed in prepared.no_pass1_overlay_body["messages"][1]["content"]

    assert baseline["messages"][0] == no_pass1["messages"][0]
    assert baseline["response_format"] == no_pass1["response_format"]
    baseline_nonprojection = {
        key: value for key, value in baseline.items() if key not in {"messages", "response_format"}
    }
    no_pass1_nonprojection = {
        key: value for key, value in no_pass1.items() if key not in {"messages", "response_format"}
    }
    assert baseline_nonprojection == no_pass1_nonprojection

    receipt = prepared.diff_receipt
    assert receipt["same_system_instruction"] is True
    assert receipt["same_cognitive_input"] is True
    assert receipt["same_accepted_continuity_context"] is True
    assert receipt["same_unresolved_projection_component"] is True
    assert receipt["same_retained_overlay"] is True
    assert receipt["same_response_schema"] is True
    assert receipt["same_nonprojection_request_fields"] is True
    assert receipt["baseline_has_pass1_response_component"] is True
    assert receipt["no_pass1_has_pass1_response_component"] is False
    assert receipt["removed_model_facing_responsibility"] == ["pass1_response_component"]
    assert receipt["baseline_unresolved_only_request_sha256"] != receipt[
        "no_pass1_request_sha256"
    ]
    assert receipt["baseline_unresolved_only_overlay_request_sha256"] != receipt[
        "no_pass1_overlay_request_sha256"
    ]


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


def test_no_pass1_parser_reuses_unresolved_only_contract() -> None:
    output = parse_unresolved_no_pass1_completion(
        _envelope(
            {
                "continuity_candidates": [
                    {
                        "kind": "unresolved",
                        "key": "parcel_contents",
                        "op": "set",
                        "value": "contents remain unknown",
                        "sources": [CURRENT_SOURCE],
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


def test_no_pass1_source_contains_no_fixture_answer_or_runtime_substitution() -> None:
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
