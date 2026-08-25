from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _extraction_pass_suffix
from relaylm.state import STATE_CLASS_DEFINITIONS


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


def test_pass2_prompt_keeps_interpretation_strings_distinct_from_candidate_records() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Interpretation arrays contain text strings only; never put State/Continuity "
        "wire objects in `turn_interpretation`." in suffix
    )
    assert (
        "`continuity_signals` contains only bounded meaning strings; structured "
        "Continuity records belong only in top-level `continuity_candidates`." in suffix
    )
    assert (
        "Structured State records belong only in top-level `state_candidates`." in suffix
    )


def test_pass2_prompt_keeps_continuity_kind_distinct_from_resolve_operation() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Never use `resolve` as `kind`; keep `kind` as `referent`, `unresolved`, or "
        "`active_task`." in suffix
    )
    assert (
        'Resolve example for an active task: `{"kind":"active_task","op":"resolve",'
        '"value":null}`.' in suffix
    )
