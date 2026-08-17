from __future__ import annotations

from pathlib import Path

from relaylm.actual_model_scenarios import load_actual_model_scenario_set

_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_ROOT = _REPO_ROOT / "evaluation" / "actual_model" / "scenario_sets"


def test_foundation_v2_preserves_v1_and_expands_required_semantic_coverage() -> None:
    v1 = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v1.json")
    v2 = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v2.json")

    assert v1.scenario_set_version == "actual-model-foundation-v1"
    assert v2.scenario_set_version == "actual-model-foundation-v2"
    assert v1.character_fixture_id == v2.character_fixture_id == (
        "actual-model-foundation-v1"
    )
    assert v1.revision != v2.revision

    v1_ids = {definition.scenario.scenario_id for definition in v1.scenarios}
    v2_ids = {definition.scenario.scenario_id for definition in v2.scenarios}
    assert v1_ids.issubset(v2_ids)
    assert len(v1_ids) == 5
    assert len(v2_ids) == 9
    assert {
        "response-self-identity-stability-v1",
        "response-continuity-referent-unresolved-task-v1",
        "continuity-stale-after-resolution-v1",
        "state-noop-churn-v1",
    }.issubset(v2_ids)


def test_response_coverage_has_self_identity_and_all_initial_continuity_kinds() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v2.json")

    identity = scenario_set.scenario("response-self-identity-stability-v1")
    assert identity.scenario.family == "response_persona_continuity"
    assert identity.required_provider_capabilities == ("state_candidates",)
    assert all(
        not labels.state and not labels.continuity
        for labels in identity.proposal_labels
    )

    continuity = scenario_set.scenario(
        "response-continuity-referent-unresolved-task-v1"
    )
    assert continuity.scenario.family == "response_persona_continuity"
    assert continuity.required_provider_capabilities == ("continuity_candidates",)
    first = next(item for item in continuity.proposal_labels if item.turn_index == 1)
    assert {(label.kind, label.op) for label in first.continuity} == {
        ("referent", "set"),
        ("unresolved", "set"),
        ("active_task", "set"),
    }
    third = next(item for item in continuity.proposal_labels if item.turn_index == 3)
    assert [(label.kind, label.op) for label in third.continuity] == [
        ("unresolved", "resolve"),
    ]


def test_continuity_stale_fixture_labels_resolve_then_expect_no_new_proposal() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v2.json")
    stale = scenario_set.scenario("continuity-stale-after-resolution-v1")

    assert stale.scenario.family == "continuity_proposal_quality"
    first = next(item for item in stale.proposal_labels if item.turn_index == 1)
    second = next(item for item in stale.proposal_labels if item.turn_index == 2)
    third = next(item for item in stale.proposal_labels if item.turn_index == 3)
    assert [(label.kind, label.key, label.op) for label in first.continuity] == [
        ("unresolved", "meeting_location", "set"),
    ]
    assert [(label.kind, label.key, label.op) for label in second.continuity] == [
        ("unresolved", "meeting_location", "resolve"),
    ]
    assert third.continuity == ()
    assert third.state == ()


def test_state_noop_fixture_labels_initial_fact_but_not_repeated_churn() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v2.json")
    churn = scenario_set.scenario("state-noop-churn-v1")

    assert churn.scenario.family == "state_candidate_quality"
    first = next(item for item in churn.proposal_labels if item.turn_index == 1)
    second = next(item for item in churn.proposal_labels if item.turn_index == 2)
    third = next(item for item in churn.proposal_labels if item.turn_index == 3)
    assert len(first.state) == 1
    assert first.state[0].state_class == "user.preference"
    assert first.state[0].key == "favorite_beverage"
    assert first.state[0].op == "set"
    assert first.state[0].match_value is True
    assert first.state[0].value == "麦茶"
    assert second.state == ()
    assert third.state == ()


def test_foundation_v2_still_has_all_five_issue_families() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_ROOT / "foundation-v2.json")

    assert {definition.scenario.family for definition in scenario_set.scenarios} == {
        "response_persona_continuity",
        "continuity_proposal_quality",
        "state_candidate_quality",
        "cognitive_pressure_robustness",
        "restart_quality",
    }
