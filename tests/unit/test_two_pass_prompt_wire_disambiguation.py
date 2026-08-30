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
        "Resolve only when the current turn actually resolves or completes an existing item"
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
    assert "which blue box" not in suffix


def test_pass2_prompt_keeps_new_unresolved_independent_of_unchanged_related_continuity() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Unchanged accepted `referent` or `active_task` meanings do not suppress a "
        "distinct newly established `unresolved` meaning." in suffix
    )
    assert (
        "If related accepted referent/task meanings are unchanged and the current Event "
        "newly establishes an unknown value with no accepted unresolved item, emit only "
        "the new `unresolved` set as applicable." in suffix
    )
    assert "Unresolved transition example" in suffix
    assert '"kind":"unresolved"' in suffix
    assert '"sources":["evt-now"]' in suffix
    assert "blue_box" not in suffix
    assert "box_contents_question" not in suffix


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


def test_pass2_projects_accepted_continuity_as_turn_local_deltas() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "A Context item whose content is a `continuity` JSON record is an already "
        "accepted temporary Continuity item, not a new proposal or prior assistant utterance."
        in suffix
    )
    assert (
        "For each Continuity kind, compare the current Input with the accepted item "
        "independently: `set` for a new meaning, `resolve` for a current resolution, "
        "and no candidate for an unchanged meaning."
        in suffix
    )
    assert (
        "Never copy an accepted item's prior `sources` into a new transition; every "
        "transition caused by the current turn uses the current Input Event ID."
        in suffix
    )
