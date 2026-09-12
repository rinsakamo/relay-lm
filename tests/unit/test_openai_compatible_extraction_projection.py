from __future__ import annotations

import hashlib

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput, CognitionStructuredOutputMode
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_extraction_projection import (
    CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA,
    EXTRACTION_WIRE_SCHEMA,
    ExtractionProjectionMode,
    build_extraction_pass_suffix,
    continuity_extraction_component,
    unresolved_only_continuity_extraction_component,
)
from relaylm.providers.openai_compatible_two_pass import (
    _extraction_pass_suffix,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


LEGACY_PRODUCTION_SUFFIX_SHA256 = (
    "7dea2101a8039e81d1905ee34072a5dae14b3f51ccf02796d1aad3351daf264b"
)


def _extraction_input() -> CognitionExtractionInput:
    cognitive_input = CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "机の上の青い箱を確認しよう"},
            event_id="evt-now",
            timestamp="2026-08-25T00:00:00+00:00",
        ),
    )
    return CognitionExtractionInput(
        cognitive_input=cognitive_input,
        assistant_response="うん、青い箱を順番に確認しよう。",
    )


def test_factorization_preserves_exact_legacy_production_suffix() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert hashlib.sha256(suffix.encode("utf-8")).hexdigest() == (
        LEGACY_PRODUCTION_SUFFIX_SHA256
    )


def test_default_request_is_exactly_explicit_production_mode() -> None:
    common = {
        "model": "gemma",
        "extraction_input": _extraction_input(),
        "decoding": {"temperature": 0, "top_p": 1},
        "structured_output_mode": CognitionStructuredOutputMode.NATIVE,
    }
    implicit = _extraction_request_body(**common)
    explicit = _extraction_request_body(
        **common,
        projection_mode=ExtractionProjectionMode.PRODUCTION,
    )

    assert implicit == explicit
    assert implicit["response_format"]["json_schema"] == {
        "name": "relaylm_structured_cognition_output",
        "strict": True,
        "schema": EXTRACTION_WIRE_SCHEMA,
    }


def test_continuity_only_schema_is_strict_projection_of_production_schema() -> None:
    diagnostic = CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA
    production = EXTRACTION_WIRE_SCHEMA

    assert diagnostic == {
        "type": "object",
        "additionalProperties": False,
        "required": ["continuity_candidates"],
        "properties": {
            "continuity_candidates": production["properties"]["continuity_candidates"]
        },
    }
    assert diagnostic["properties"] is not production["properties"]
    assert diagnostic["properties"]["continuity_candidates"] is not production[
        "properties"
    ]["continuity_candidates"]


def test_continuity_only_request_uses_same_transport_fields_without_state_schema() -> None:
    production = _extraction_request_body(
        model="gemma",
        extraction_input=_extraction_input(),
        decoding={"temperature": 0, "top_p": 1},
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
    )
    diagnostic = _extraction_request_body(
        model="gemma",
        extraction_input=_extraction_input(),
        decoding={"temperature": 0, "top_p": 1},
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
        projection_mode=ExtractionProjectionMode.CONTINUITY_ONLY,
    )

    assert diagnostic["model"] == production["model"]
    assert diagnostic["stream"] is production["stream"] is False
    assert diagnostic["temperature"] == production["temperature"] == 0
    assert diagnostic["top_p"] == production["top_p"] == 1
    assert diagnostic["messages"][0] == production["messages"][0]
    assert diagnostic["response_format"]["json_schema"] == {
        "name": "relaylm_continuity_only_extraction_output",
        "strict": True,
        "schema": CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA,
    }
    assert "state_candidates" not in diagnostic["response_format"]["json_schema"][
        "schema"
    ]["properties"]


def test_unresolved_only_reuses_continuity_schema_without_kind_hint() -> None:
    diagnostic = _extraction_request_body(
        model="gemma",
        extraction_input=_extraction_input(),
        decoding={"temperature": 0, "top_p": 1},
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
        projection_mode=ExtractionProjectionMode.UNRESOLVED_ONLY,
    )

    schema = diagnostic["response_format"]["json_schema"]
    assert schema == {
        "name": "relaylm_unresolved_only_extraction_output",
        "strict": True,
        "schema": CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA,
    }
    kind_schema = schema["schema"]["properties"]["continuity_candidates"]["items"][
        "properties"
    ]["kind"]
    assert set(kind_schema["enum"]) == {"referent", "unresolved", "active_task"}


def test_unresolved_only_removes_other_kind_decision_responsibilities() -> None:
    source_id = _extraction_input().originating_event_id
    all_kinds = continuity_extraction_component(source_id)
    unresolved_only = unresolved_only_continuity_extraction_component(source_id)

    assert "`unresolved`: an explicit open question" in unresolved_only
    assert "explicitly maintained unknown value" in unresolved_only
    assert "Unresolved transition example" in unresolved_only
    assert "current Input Event ID `evt-now`" in unresolved_only
    assert "`epistemic_role` must be exactly" in unresolved_only

    for removed in (
        "`referent`: a specific subject",
        "`active_task`: an unfinished action",
        "Emit every distinct useful Continuity meaning",
        "For each Continuity kind",
        "Referent:",
        "Active task:",
    ):
        assert removed in all_kinds
        assert removed not in unresolved_only


def test_existing_continuity_only_still_uses_full_canonical_continuity_component() -> None:
    extraction_input = _extraction_input()
    diagnostic = build_extraction_pass_suffix(
        extraction_input,
        mode=ExtractionProjectionMode.CONTINUITY_ONLY,
    )
    full_component = continuity_extraction_component(extraction_input.originating_event_id)

    assert full_component in diagnostic
    assert "Emit every distinct useful Continuity meaning" in diagnostic
    assert "`referent`: a specific subject" in diagnostic
    assert "`active_task`: an unfinished action" in diagnostic
