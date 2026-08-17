from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_quality import (
    QUALITY_RUBRIC_VERSION,
    ContinuityProposalLabel,
)
from relaylm.actual_model_scenarios import (
    ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION,
    ActualModelScenarioSetError,
    load_actual_model_scenario_set,
)
from relaylm.storage.filesystem import CharacterDirectory

_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_SET = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v1.json"
)
_CHARACTER_FIXTURE = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)


def _write_mapping(tmp_path: Path, mapping: dict[str, object]) -> Path:
    path = tmp_path / "scenario-set.json"
    path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_canonical_scenario_set_is_versioned_isolated_and_covers_current_families() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)

    assert scenario_set.format_version == ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION
    assert scenario_set.scenario_set_version == "actual-model-foundation-v1"
    assert scenario_set.quality_rubric_version == QUALITY_RUBRIC_VERSION
    assert scenario_set.character_fixture_id == "actual-model-foundation-v1"
    assert {
        item.scenario.family for item in scenario_set.scenarios
    } == {
        "response_persona_continuity",
        "continuity_proposal_quality",
        "state_candidate_quality",
        "cognitive_pressure_robustness",
        "restart_quality",
    }
    assert scenario_set.revision.startswith("sha256:")
    assert len(scenario_set.revision) == len("sha256:") + 64


def test_canonical_character_fixture_matches_scenario_set_identity() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)
    character = CharacterDirectory(_CHARACTER_FIXTURE)

    assert character.load_config().character_id == scenario_set.character_fixture_id
    assert character.load_config().name == "Aoi"
    assert character.load_state().states == ()
    assert character.load_identity().content.startswith("# Aoi")
    assert character_fixture_revision(_CHARACTER_FIXTURE).startswith("sha256:")


def test_scenario_set_revision_is_based_on_normalized_machine_readable_content(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)
    normalized = scenario_set.to_mapping()
    rewritten = _write_mapping(tmp_path, normalized)

    assert load_actual_model_scenario_set(rewritten).revision == scenario_set.revision


def test_continuity_lifecycle_fixture_uses_canonical_resolve_operation() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)
    lifecycle = scenario_set.scenario("continuity-lifecycle-v1")

    third_turn = next(
        item for item in lifecycle.proposal_labels if item.turn_index == 3
    )
    assert [(item.kind, item.op) for item in third_turn.continuity] == [
        ("unresolved", "resolve"),
        ("active_task", "resolve"),
    ]

    label = ContinuityProposalLabel(
        kind="unresolved",
        key="question",
        op="resolve",
    )
    assert label.op == "resolve"
    with pytest.raises(ValueError, match="unsupported Continuity proposal op"):
        ContinuityProposalLabel(
            kind="unresolved",
            key="question",
            op="remove",  # type: ignore[arg-type]
        )


def test_provider_capability_requirements_keep_unsupported_channels_explicit() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)

    response = scenario_set.scenario("response-persona-correction-v1")
    continuity = scenario_set.scenario("continuity-lifecycle-v1")
    pressure = scenario_set.scenario("cognitive-pressure-shared-semantics-v1")
    restart = scenario_set.scenario("restart-durable-vs-temporary-v1")

    assert response.required_provider_capabilities == ("state_candidates",)
    assert continuity.required_provider_capabilities == ("continuity_candidates",)
    assert pressure.required_provider_capabilities == (
        "state_candidates",
        "continuity_candidates",
    )
    assert restart.required_provider_capabilities == (
        "state_candidates",
        "continuity_candidates",
    )
    assert restart.restart_after_turn_count == 2


def test_loader_rejects_unknown_fields_and_duplicate_json_keys(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)
    mapping = scenario_set.to_mapping()
    mapping["unexpected"] = True

    with pytest.raises(ActualModelScenarioSetError, match="unknown unexpected"):
        load_actual_model_scenario_set(_write_mapping(tmp_path, mapping))

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"format_version":1,"format_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(ActualModelScenarioSetError, match="duplicate JSON object key"):
        load_actual_model_scenario_set(duplicate)


def test_loader_rejects_cross_turn_and_restart_shape_drift(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)

    out_of_range = scenario_set.to_mapping()
    scenarios = out_of_range["scenarios"]
    assert isinstance(scenarios, list)
    first = scenarios[0]
    assert isinstance(first, dict)
    labels = first["proposal_labels"]
    assert isinstance(labels, list)
    first_label = labels[0]
    assert isinstance(first_label, dict)
    first_label["turn_index"] = 99
    with pytest.raises(ActualModelScenarioSetError, match="outside the scenario"):
        load_actual_model_scenario_set(_write_mapping(tmp_path, out_of_range))

    invalid_restart = scenario_set.to_mapping()
    restart_scenarios = invalid_restart["scenarios"]
    assert isinstance(restart_scenarios, list)
    non_restart = restart_scenarios[0]
    assert isinstance(non_restart, dict)
    non_restart["restart_after_turn_count"] = 1
    with pytest.raises(
        ActualModelScenarioSetError,
        match="only valid for restart_quality",
    ):
        load_actual_model_scenario_set(_write_mapping(tmp_path, invalid_restart))


def test_loader_rejects_rubric_drift(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET)
    mapping = scenario_set.to_mapping()
    mapping["quality_rubric_version"] = "future-unfrozen-rubric"

    with pytest.raises(
        ActualModelScenarioSetError,
        match="pin the current actual-model quality rubric version",
    ):
        load_actual_model_scenario_set(_write_mapping(tmp_path, mapping))
