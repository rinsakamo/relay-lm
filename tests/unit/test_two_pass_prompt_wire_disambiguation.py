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


def test_pass2_prompt_projects_directly_to_candidate_records() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert '`{"state_candidates":[],"continuity_candidates":[]}`' in suffix
    assert "turn_interpretation" not in suffix
    assert "continuity_signals" not in suffix


def test_pass2_prompt_keeps_continuity_kind_distinct_from_resolve_operation() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "`kind` is exactly `referent`, `unresolved`, or `active_task`" in suffix
    assert "`op` is `set` or `resolve`; `resolve` uses null value" in suffix
    assert "A meaning explicitly resolved, completed, replaced, dismissed, or invalidated" in suffix


def test_pass2_prompt_keeps_continuity_kind_distinct_from_epistemic_role() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "`kind` and `epistemic_role` are separate axes." in suffix
    assert (
        "`epistemic_role` is exactly `user_assertion`, `assistant_inference`, or "
        "`assistant_commitment`." in suffix
    )
    assert "`unresolved` is an open question or unknown value that remains unresolved" in suffix
    assert "which blue box" not in suffix


def test_pass2_prompt_keeps_new_unresolved_independent_of_related_continuity() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "An `unresolved` dependency is an explicit unanswered question, unknown value, or "
        "missing answer that remains open; it does not require future action." in suffix
    )
    assert (
        "An `active_task` dependency is unfinished work or a goal that still requires future "
        "action; an unresolved dependency does not by itself establish one." in suffix
    )
    assert (
        "Evaluate each dependency on its own lifecycle; an unchanged related dependency "
        "does not suppress a newly established one." in suffix
    )
    assert "blue_box" not in suffix
    assert "box_contents_question" not in suffix


def test_pass2_keeps_durable_state_semantics_independent_from_continuity() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert suffix.index("State:\n") < suffix.index("Continuity:\n")
    assert "State represents durable accepted current understanding." in suffix
    assert "New durable meaning -> `set`." in suffix
    assert "Unchanged accepted State -> no candidate." in suffix


def test_two_pass_grounding_rejects_unsupported_history_generally() -> None:
    assert (
        "Do not treat inference, conversational implication, or model output as evidence when "
        "the supplied cognitive context does not support it." in COMMON_SYSTEM_INSTRUCTION
    )
    assert (
        "Do not invent history, evidence, motives, shared experiences, or supporting details."
        in COMMON_SYSTEM_INSTRUCTION
    )


def test_pass2_requires_a_cross_turn_dependency_for_continuity() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Continuity represents temporary cross-turn coherence" in suffix
    assert "`referent` is a specific cross-turn reference target" in suffix
    assert "Create Continuity only for a concrete cross-turn dependency" in suffix


def test_pass2_projects_accepted_continuity_as_turn_local_deltas() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Treat accepted Continuity in Context as existing lifecycle state, not a new proposal; "
        "emit only current-turn changes." in suffix
    )
    assert "Reuse the accepted lifecycle key" in suffix
    assert "Unchanged accepted meaning -> no candidate." in suffix
    assert "Every new Continuity transition must be grounded in the current Input Event." in suffix
