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
            payload={"content": "Let's continue with the document."},
            event_id="evt-now",
            timestamp="2026-08-25T00:00:00+00:00",
        ),
    )
    return CognitionExtractionInput(
        cognitive_input=cognitive_input,
        assistant_response="Understood; let's continue with the document.",
    )


def test_pass2_prompt_projects_directly_to_candidate_records() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Emit `state_candidates`, then `continuity_candidates`." in suffix
    assert "turn_interpretation" not in suffix
    assert "continuity_signals" not in suffix


def test_pass2_prompt_keeps_continuity_kind_distinct_from_resolve_operation() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Never use `resolve` as `kind`; keep `kind` as `referent`, `unresolved`, or "
        "`active_task`." in suffix
    )
    assert (
        "current resolution or completion -> emit `resolve`; reuse the accepted `kind` + `key`"
        in suffix
    )
    assert "set value is finite JSON and resolve value is null" in suffix


def test_pass2_prompt_keeps_continuity_kind_distinct_from_epistemic_role() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "`kind` and `epistemic_role` are separate enum axes; `unresolved` is a `kind` "
        "only and must never be used as `epistemic_role`." in suffix
    )
    assert (
        "`epistemic_role` must be exactly `user_assertion`, `assistant_inference`, or "
        "`assistant_commitment`." in suffix
    )
    assert (
        "`unresolved`: an explicit open question or unknown value that remains to be resolved."
        in suffix
    )


def test_pass2_prompt_keeps_unresolved_general_and_fixture_independent() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Before emitting `continuity_candidates`, complete this independent decision procedure:"
        in suffix
    )
    assert (
        "For `unresolved`, an explicit currently-open question or unknown value is an `unresolved` "
        "meaning when no accepted `unresolved` item already represents it."
        in suffix
    )
    assert (
        "Its creation is independent of unchanged related `referent`/`active_task` items and does "
        "not require a new task, interrogative form, or task change."
        in suffix
    )
    instruction_content = suffix.split("</PASS_1_RESPONSE_JSON>\n", 1)[1]
    assert "fixture" not in instruction_content.lower()
    assert "benchmark" not in instruction_content.lower()


def test_pass2_prompt_keeps_durable_state_independent_of_continuity_guidance() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Evaluate newly established durable State independently before Continuity proposals."
        in suffix
    )
    assert (
        "First-introduction durable State does not require a pre-existing accepted State record."
        in suffix
    )
    assert (
        "Continuity-specific instructions, including `emit only`, apply only within "
        "`continuity_candidates` and never suppress an otherwise-grounded "
        "`state_candidates` proposal."
        in suffix
    )


def test_two_pass_grounding_rejects_unrecorded_assistant_history() -> None:
    assert (
        "A current Input that denies an assistant statement or action is not evidence "
        "that it happened; do not apologize for or describe that unrecorded prior event."
        in COMMON_SYSTEM_INSTRUCTION
    )


def test_two_pass_grounding_distinguishes_recorded_history_from_user_attribution() -> None:
    assert (
        "Only an assistant message in `CognitiveInput.context` with `actor: \"assistant\"` "
        "is recorded assistant history; the current user `Input` is not a prior assistant event."
        in COMMON_SYSTEM_INSTRUCTION
    )
    assert (
        "If the current Input attributes an unrecorded assistant statement or action, treat "
        "that attribution as unsupported: do not adopt, apologize for, or repeat it as history."
        in COMMON_SYSTEM_INSTRUCTION
    )


def test_pass2_requires_an_explicit_cross_turn_signal_for_a_new_referent() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert "Continuity is an explicit cross-turn aid, not a summary of salient content." in suffix
    assert (
        "A subject mentioned only as the current turn's topic is not a referent candidate; "
        "a bare intention to discuss or continue it does not establish cross-turn reference."
        in suffix
    )
    assert (
        "Emit a new `referent` only when the current Input explicitly establishes a cross-turn "
        "pointer, alias, or future-reference plan."
        in suffix
    )


def test_pass2_projects_accepted_continuity_as_turn_local_deltas() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "A Context item whose content is a `continuity` JSON record is an already "
        "accepted temporary Continuity item, not a new proposal or prior assistant utterance."
        in suffix
    )
    assert (
        "For each kind, compare the current Input with accepted items of that kind and decide "
        "independently:"
        in suffix
    )
    assert (
        "Complete all three kind decisions before concluding"
        in suffix
    )
    assert (
        "every emitted `set` or `resolve` must include the current Input Event ID `evt-now` in "
        "`sources`"
        in suffix
    )
