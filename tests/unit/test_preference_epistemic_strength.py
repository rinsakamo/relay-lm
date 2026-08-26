from __future__ import annotations

from pathlib import Path

from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _extraction_pass_suffix
from relaylm.state import STATE_CLASS_DEFINITIONS


_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "preference-epistemic-strength-v1.json"
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
            payload={"content": "I might prefer tea to coffee, but I'm not sure yet."},
            event_id="evt-now",
            timestamp="2026-08-26T00:00:00+00:00",
        ),
    )
    return CognitionExtractionInput(
        cognitive_input=cognitive_input,
        assistant_response="That sounds tentative for now.",
    )


def test_preference_class_keeps_intensity_semantics_but_not_language_examples() -> None:
    definition = STATE_CLASS_DEFINITIONS["user.preference"].casefold()

    assert "degree_hint" in definition
    assert "intensity" in definition
    assert "confidence" in definition
    assert "might prefer tea" not in definition
    assert "not in the mood for tea" not in definition


def test_global_state_durability_gate_is_model_facing_and_language_independent() -> None:
    suffix = _extraction_pass_suffix(_extraction_input())

    assert (
        "Durable State gate: emit State only when the current Input presents the candidate "
        "meaning as sufficiently asserted, committed, or otherwise established" in suffix
    )
    assert (
        "Tentative, hypothetical, merely possible, guessed, hedged, or explicitly "
        "self-uncertain meaning stays uncommitted" in suffix
    )
    assert "Apply this gate by meaning regardless of language or state_class" in suffix
    assert "do not use surface keywords or grammatical patterns as the gate" in suffix
    assert "Epistemic uncertainty is not degree_hint" in suffix
    assert "A later resolved assertion may establish State normally" in suffix
    assert "たぶん紅茶のほうが好きかも" not in suffix


def test_actual_model_fixture_covers_english_contrast_and_japanese_black_box_s5() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_PATH)

    assert scenario_set.scenario_set_version == "preference-epistemic-strength-v1"
    assert len(scenario_set.scenarios) == 2

    english = scenario_set.scenario("preference-epistemic-strength-v1")
    assert english.scenario.family == "state_candidate_quality"
    assert english.scenario.turns == (
        "I might prefer tea to coffee, but I'm not sure yet.",
        "I've decided: tea is my preferred beverage.",
        "Today I'm not in the mood for tea, but my usual preference has not changed.",
    )
    first, second, third = english.proposal_labels
    assert first.state == ()
    assert len(second.state) == 1
    assert second.state[0].state_class == "user.preference"
    assert second.state[0].key == "preferred_beverage"
    assert second.state[0].op == "set"
    assert second.state[0].match_value is True
    assert second.state[0].value == "tea"
    assert third.state == ()

    japanese = scenario_set.scenario("preference-epistemic-strength-ja-s5-v1")
    assert japanese.scenario.family == "state_candidate_quality"
    assert japanese.scenario.turns == ("たぶん紅茶のほうが好きかも。",)
    assert japanese.proposal_labels[0].state == ()
    assert japanese.proposal_labels[0].continuity == ()
