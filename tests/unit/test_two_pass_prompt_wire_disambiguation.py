from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import (
    COMMON_SYSTEM_INSTRUCTION,
    _extraction_pass_suffix,
)
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


def test_pass1_prompt_uses_general_authority_and_provenance_principles() -> None:
    assert "Context, Memory, Knowledge, Event Evidence, and Input retain the authority" in (
        COMMON_SYSTEM_INSTRUCTION
    )
    assert (
        "Do not treat inference, conversational implication, or model output as evidence"
        in COMMON_SYSTEM_INSTRUCTION
    )
    assert "Do not invent history, evidence, motives, shared experiences" in (
        COMMON_SYSTEM_INSTRUCTION
    )


def test_pass1_prompt_removes_failure_specific_history_wording() -> None:
    assert "apologize" not in COMMON_SYSTEM_INSTRUCTION
    assert "unrecorded assistant" not in COMMON_SYSTEM_INSTRUCTION
    assert "actor: \"assistant\"" not in COMMON_SYSTEM_INSTRUCTION


def test_pass2_prompt_projects_directly_to_candidate_records() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert '`{"state_candidates":[],"continuity_candidates":[]}`' in suffix
    assert "turn_interpretation" not in suffix
    assert "continuity_signals" not in suffix


def test_pass2_prompt_preserves_durable_state_principle_and_wire() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "State represents durable accepted current understanding." in suffix
    assert "Tentative, hypothetical, guessed, hedged, merely possible" in suffix
    assert "New durable meaning -> `set`." in suffix
    assert "Unchanged accepted State -> no candidate." in suffix
    assert "State wire is `{state_class,key,op,value,sources}`." in suffix
    assert "degree_hint is semantic intensity, not confidence" in suffix


def test_pass2_prompt_preserves_independent_continuity_lifecycle() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Evaluate these meanings independently" in suffix
    assert "`referent` is a specific cross-turn reference target" in suffix
    assert "`unresolved` is an open question or unknown value" in suffix
    assert "`active_task` is unfinished work" in suffix
    assert "New useful meaning -> `set`." in suffix
    assert "Unchanged accepted meaning -> no candidate." in suffix
    assert "Resolution of one Continuity kind does not automatically resolve another." in suffix


def test_pass2_prompt_preserves_continuity_wire_axes() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Continuity wire is `{kind,key,op,value,sources,epistemic_role}`." in suffix
    assert "`kind` is exactly `referent`, `unresolved`, or `active_task`" in suffix
    assert "`kind` and `epistemic_role` are separate axes." in suffix
    assert (
        "`epistemic_role` is exactly `user_assertion`, `assistant_inference`, or "
        "`assistant_commitment`." in suffix
    )


def test_pass2_prompt_preserves_source_authority() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Pass 1 response is interpretive context only." in suffix
    assert "Candidate `sources` must be non-empty Event IDs present in CognitiveInput" in suffix
    assert "current Input Event ID `evt-now`" in suffix
    assert "Do not promote model inference into higher authority" in suffix


def test_pass2_prompt_removes_fixture_driven_continuity_rules_and_examples() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "bare intention to discuss or continue" not in suffix
    assert "future-reference plan" not in suffix
    assert "Before concluding there are no Continuity candidates" not in suffix
    assert "Unresolved transition example" not in suffix
    assert '"current_document"' not in suffix
    assert '"document_author"' not in suffix
    assert '"verify_document_author"' not in suffix
