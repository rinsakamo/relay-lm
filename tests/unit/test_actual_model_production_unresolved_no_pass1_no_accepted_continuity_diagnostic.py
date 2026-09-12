from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    load_retained_formation_binding,
)
import relaylm.actual_model_production_unresolved_no_pass1_no_accepted_continuity_diagnostic as diagnostic_module
from relaylm.actual_model_production_unresolved_no_pass1_no_accepted_continuity_diagnostic import (
    build_unresolved_no_pass1_no_accepted_continuity_request_body,
    parse_unresolved_no_pass1_no_accepted_continuity_completion,
)
from relaylm.actual_model_production_unresolved_no_pass1_diagnostic import (
    build_unresolved_no_pass1_extraction_request_body,
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
from relaylm.providers.openai_compatible_two_pass import _common_cognitive_prefix
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


REVISION = "sha256:" + "c" * 64
T2 = "The parcel is still closed, so what is inside remains unknown."
STABLE_SOURCE = f"stage-r:{REVISION}:primary:turn-2"
CURRENT_SOURCE = "evt-run-local"
PASS1 = "I cannot know what is inside until the parcel is opened."


def _accepted_continuity_item(
    *,
    kind: str,
    key: str,
    value: str,
) -> ContextItem:
    return ContextItem(
        content=json.dumps(
            {
                "continuity": {
                    "epistemic_role": "user_assertion",
                    "key": key,
                    "kind": kind,
                    "value": value,
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        sources=("evt-t1",),
    )


def _working_context() -> tuple[ContextItem, ...]:
    return (
        ContextItem(
            content="Earlier user turn.",
            sources=("evt-t1-user",),
            actor="user",
        ),
        ContextItem(
            content="Earlier assistant turn.",
            sources=("evt-t1-assistant",),
            actor="assistant",
        ),
    )


def _input(*, context: tuple[ContextItem, ...] | None = None) -> CognitiveInput:
    if context is None:
        context = (
            _accepted_continuity_item(
                kind="referent",
                key="current_parcel",
                value="the parcel",
            ),
            _accepted_continuity_item(
                kind="active_task",
                key="inspect_parcel",
                value="inspect the parcel contents",
            ),
        ) + _working_context()
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
        context=context,
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": T2},
            event_id=CURRENT_SOURCE,
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )


def _extraction(*, context: tuple[ContextItem, ...] | None = None) -> CognitionExtractionInput:
    return CognitionExtractionInput(
        cognitive_input=_input(context=context),
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


def test_builder_removes_only_compiled_accepted_continuity_prefix(
    tmp_path: Path,
) -> None:
    extraction = _extraction()
    direct_baseline = build_unresolved_no_pass1_extraction_request_body(
        provider=_Provider(),
        extraction_input=extraction,
        pass_request=_pass_request(),
        binding=_binding(tmp_path),
    )
    prepared = (
        build_unresolved_no_pass1_no_accepted_continuity_request_body(
            provider=_Provider(),
            extraction_input=extraction,
            pass_request=_pass_request(),
            binding=_binding(tmp_path),
        )
    )

    assert prepared.baseline.no_pass1_body == direct_baseline.no_pass1_body
    assert (
        prepared.baseline.no_pass1_overlay_body
        == direct_baseline.no_pass1_overlay_body
    )
    assert prepared.treatment_cognitive_input.state == extraction.cognitive_input.state
    assert (
        prepared.treatment_cognitive_input.context
        == _working_context()
    )
    assert len(prepared.removed_context_items) == 2

    baseline_content = prepared.baseline.no_pass1_body["messages"][1]["content"]
    treatment_content = prepared.treatment_body["messages"][1]["content"]
    assert baseline_content.startswith(
        _common_cognitive_prefix(extraction.cognitive_input)
    )
    assert treatment_content.startswith(
        _common_cognitive_prefix(prepared.treatment_cognitive_input)
    )
    assert "<PASS_1_RESPONSE_JSON>" not in baseline_content
    assert "<PASS_1_RESPONSE_JSON>" not in treatment_content
    assert PASS1 not in baseline_content
    assert PASS1 not in treatment_content

    assert "current_parcel" in baseline_content
    assert "inspect_parcel" in baseline_content
    assert "current_parcel" not in treatment_content
    assert "inspect_parcel" not in treatment_content
    assert "Earlier user turn." in treatment_content
    assert "Earlier assistant turn." in treatment_content
    assert "parcel_location" in treatment_content
    assert "on the table" in treatment_content
    assert "what is inside" in prepared.treatment_overlay_body["messages"][1][
        "content"
    ]
    assert "remains unknown" in prepared.treatment_overlay_body["messages"][1][
        "content"
    ]
    assert CURRENT_SOURCE not in prepared.treatment_overlay_body["messages"][1]["content"]

    receipt = prepared.diff_receipt
    assert receipt["same_system_instruction"] is True
    assert receipt["same_selected_state"] is True
    assert receipt["same_noncontext_cognitive_input"] is True
    assert receipt["same_working_context_suffix"] is True
    assert receipt["same_unresolved_projection_component"] is True
    assert receipt["same_retained_overlay"] is True
    assert receipt["same_response_schema"] is True
    assert receipt["same_nonprojection_request_fields"] is True
    assert receipt["baseline_has_pass1_response_component"] is False
    assert receipt["treatment_has_pass1_response_component"] is False
    assert receipt["removed_accepted_continuity_context_count"] == 2
    assert receipt["removed_model_facing_responsibility"] == [
        "accepted_continuity_context"
    ]
    assert receipt["baseline_no_pass1_request_sha256"] != receipt[
        "treatment_request_sha256"
    ]
    assert receipt["baseline_no_pass1_overlay_request_sha256"] != receipt[
        "treatment_overlay_request_sha256"
    ]

    baseline_context = prepared.baseline_cognitive_input["context"]
    treatment_context = prepared.treatment_cognitive_input_serialized["context"]
    assert baseline_context[2:] == treatment_context


def test_builder_fails_closed_without_accepted_continuity_prefix(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ProviderProtocolError,
        match="no projected accepted Continuity prefix",
    ):
        build_unresolved_no_pass1_no_accepted_continuity_request_body(
            provider=_Provider(),
            extraction_input=_extraction(context=_working_context()),
            pass_request=_pass_request(),
            binding=_binding(tmp_path),
        )


def test_builder_fails_closed_on_noncanonical_actor_none_prefix(
    tmp_path: Path,
) -> None:
    context = (
        ContextItem(
            content='{"not_continuity":true}',
            sources=("evt-t1",),
        ),
    ) + _working_context()
    with pytest.raises(
        ProviderProtocolError,
        match="must contain only continuity",
    ):
        build_unresolved_no_pass1_no_accepted_continuity_request_body(
            provider=_Provider(),
            extraction_input=_extraction(context=context),
            pass_request=_pass_request(),
            binding=_binding(tmp_path),
        )


def test_builder_fails_closed_on_late_actor_none_context(
    tmp_path: Path,
) -> None:
    context = (
        _accepted_continuity_item(
            kind="referent",
            key="current_parcel",
            value="the parcel",
        ),
        ContextItem(
            content="Earlier user turn.",
            sources=("evt-t1-user",),
            actor="user",
        ),
        _accepted_continuity_item(
            kind="active_task",
            key="inspect_parcel",
            value="inspect the parcel contents",
        ),
    )
    with pytest.raises(
        ProviderProtocolError,
        match="working context boundary",
    ):
        build_unresolved_no_pass1_no_accepted_continuity_request_body(
            provider=_Provider(),
            extraction_input=_extraction(context=context),
            pass_request=_pass_request(),
            binding=_binding(tmp_path),
        )


def _envelope(payload: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                },
            }
        ]
    }


def test_parser_reuses_unresolved_only_contract() -> None:
    treatment_context = _working_context()
    output = parse_unresolved_no_pass1_no_accepted_continuity_completion(
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
        cognitive_input=_input(context=treatment_context),
    )
    assert output.state_candidates == ()
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"
    assert output.continuity_candidates[0].sources == (CURRENT_SOURCE,)


def test_source_contains_no_fixture_answer_or_runtime_substitution() -> None:
    source = inspect.getsource(diagnostic_module)
    for forbidden in (
        "blue_box",
        "box_contents_question",
        "monkeypatch",
        "setattr(",
        "sys.modules",
        "sys.meta_path",
        "importlib",
        "continuity_context=None",
    ):
        assert forbidden not in source
