from __future__ import annotations

from pathlib import Path

from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _common_cognitive_prefix
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


def test_user_preference_semantics_separate_epistemic_strength_from_intensity() -> None:
    definition = STATE_CLASS_DEFINITIONS["user.preference"].casefold()

    assert "tentative or uncertain preference" in definition
    assert "does not by itself establish durable preference" in definition
    assert "degree_hint is intensity, not confidence" in definition
    assert "temporary mood or situational variation" in definition
    assert "does not revoke an established durable preference" in definition


def test_state_owned_epistemic_contrast_is_model_facing_in_cognitive_input() -> None:
    prefix = _common_cognitive_prefix(_extraction_input().cognitive_input)

    assert "degree_hint is intensity, not confidence" in prefix
    assert "tentative ('might prefer tea; not sure') means no durable State" in prefix
    assert "resolved ('prefer tea to coffee') may establish durable preference" in prefix
    assert (
        "temporary ('not in the mood for tea today; usual preference unchanged') "
        "must not remove durable preference" in prefix
    )


def test_actual_model_fixture_covers_tentative_resolved_and_temporary_preference() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_PATH)

    assert scenario_set.scenario_set_version == "preference-epistemic-strength-v1"
    assert len(scenario_set.scenarios) == 1
    definition = scenario_set.scenarios[0]
    assert definition.scenario.scenario_id == "preference-epistemic-strength-v1"
    assert definition.scenario.family == "state_candidate_quality"
    assert definition.scenario.turns == (
        "I might prefer tea to coffee, but I'm not sure yet.",
        "I've decided: tea is my preferred beverage.",
        "Today I'm not in the mood for tea, but my usual preference has not changed.",
    )

    first, second, third = definition.proposal_labels
    assert first.state == ()
    assert len(second.state) == 1
    assert second.state[0].state_class == "user.preference"
    assert second.state[0].key == "preferred_beverage"
    assert second.state[0].op == "set"
    assert second.state[0].match_value is True
    assert second.state[0].value == "tea"
    assert third.state == ()
