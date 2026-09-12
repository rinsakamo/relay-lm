from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import relaylm.actual_model_production_unresolved_only_diagnostic as diagnostic_module
import relaylm.providers.openai_compatible_extraction_projection as projection_module
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    load_retained_formation_binding,
)
from relaylm.actual_model_production_unresolved_only_diagnostic import (
    build_unresolved_only_extraction_request_body,
    parse_unresolved_only_completion,
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


def test_unresolved_only_builder_holds_context_overlay_and_schema_fixed(
    tmp_path: Path,
) -> None:
    prepared = build_unresolved_only_extraction_request_body(
        provider=_Provider(),
        extraction_input=_extraction(),
        pass_request=_pass_request(),
        binding=_binding(tmp_path),
    )

    receipt = prepared.diff_receipt
    assert receipt["same_system_instruction"] is True
    assert receipt["same_cognitive_input_and_pass1_prefix"] is True
    assert receipt["same_accepted_continuity_context"] is True
    assert receipt["same_retained_overlay"] is True
    assert receipt["same_nonprojection_request_fields"] is True
    assert receipt["same_continuity_candidate_item_schema"] is True
    assert receipt["continuity_only_has_full_kind_component"] is True
    assert receipt["unresolved_only_has_full_kind_component"] is False
    assert receipt["unresolved_only_keeps_unresolved_component"] is True
    assert receipt["removed_model_facing_responsibility"] == [
        "referent_projection_instruction",
        "active_task_projection_instruction",
        "multi_kind_decision_competition",
    ]

    content = prepared.unresolved_only_overlay_body["messages"][1]["content"]
    for expected in (
        "parcel_location",
        "on the table",
        "current_parcel",
        "the parcel",
        "inspect_parcel",
        "inspect the parcel contents",
        "I cannot know until the parcel is opened.",
        "what is inside",
        "remains unknown",
        CURRENT_SOURCE,
    ):
        assert expected in content

    for removed in (
        "`referent`: a specific subject",
        "`active_task`: an unfinished action",
        "Emit every distinct useful Continuity meaning",
        "For each Continuity kind",
        "  - Referent:",
        "  - Active task:",
    ):
        assert removed not in content

    continuity_schema = prepared.continuity_only_body["response_format"]["json_schema"]
    unresolved_schema = prepared.unresolved_only_body["response_format"]["json_schema"]
    assert unresolved_schema["name"] == "relaylm_unresolved_only_extraction_output"
    assert unresolved_schema["strict"] is True
    assert unresolved_schema["schema"] == continuity_schema["schema"]
    assert set(unresolved_schema["schema"]["properties"]) == {"continuity_candidates"}


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


def test_unresolved_only_parser_accepts_unresolved_and_rejects_other_kinds() -> None:
    unresolved = {
        "kind": "unresolved",
        "key": "parcel_contents",
        "op": "set",
        "value": "contents remain unknown",
        "sources": [CURRENT_SOURCE],
        "epistemic_role": "user_assertion",
    }
    output = parse_unresolved_only_completion(
        _envelope({"continuity_candidates": [unresolved]}),
        cognitive_input=_input(),
    )
    assert output.state_candidates == ()
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"

    referent = dict(unresolved)
    referent.update(kind="referent", key="parcel")
    with pytest.raises(ProviderProtocolError, match="non-unresolved"):
        parse_unresolved_only_completion(
            _envelope({"continuity_candidates": [referent]}),
            cognitive_input=_input(),
        )


def test_unresolved_only_parser_preserves_canonical_source_validation() -> None:
    with pytest.raises(ProviderProtocolError, match="sources"):
        parse_unresolved_only_completion(
            _envelope(
                {
                    "continuity_candidates": [
                        {
                            "kind": "unresolved",
                            "key": "parcel_contents",
                            "op": "set",
                            "value": "contents remain unknown",
                            "sources": ["invented-event"],
                            "epistemic_role": "user_assertion",
                        }
                    ]
                }
            ),
            cognitive_input=_input(),
        )


def test_unresolved_only_source_contains_no_fixture_answer_or_substitution() -> None:
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
