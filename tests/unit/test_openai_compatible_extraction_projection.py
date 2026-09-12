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
)
from relaylm.providers.openai_compatible_two_pass import (
    _extraction_pass_suffix,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


LEGACY_PRODUCTION_SUFFIX_BYTES = 7767
LEGACY_PRODUCTION_SUFFIX_SHA256 = (
    "2d6c4d3f7b55148da36b139999802564bf6bfb73ccb44179691663ee57ca4e1f"
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
    encoded = suffix.encode("utf-8")

    assert len(encoded) == LEGACY_PRODUCTION_SUFFIX_BYTES
    assert hashlib.sha256(encoded).hexdigest() == LEGACY_PRODUCTION_SUFFIX_SHA256


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
