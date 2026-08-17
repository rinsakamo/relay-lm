from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import ActualModelRunManifest, ActualModelScenario
from relaylm.actual_model_restart import (
    ActualModelRestartRunManifest,
    run_actual_model_restart_scenario,
    stable_actual_model_restart_run_id,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import ContinuityCandidate
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory


class _RestartProvider:
    def __init__(self) -> None:
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        if len(self.inputs) == 1:
            source = cognitive_input.input.id
            return CognitiveOutput(
                response="覚えたよ。次はその青い箱の話を続けよう。",
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.identity",
                        key="name",
                        value="Rin",
                        sources=(source,),
                    ),
                ),
                continuity_candidates=(
                    ContinuityCandidate.set(
                        kind="referent",
                        key="current_subject",
                        value="青い箱",
                        sources=(source,),
                        epistemic_role="user_assertion",
                    ),
                ),
            )
        return CognitiveOutput(response="名前の記録はRin。続きを確認しよう。")


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Restart Fixture\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: restart-fixture\n  name: Restart Fixture\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _base_manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="374a60aa9770084a3b46c6159b0bc72713bac119",
        character_fixture_id="restart-fixture",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="restart-foundation-v1",
        condition_id="restart",
        provider_capabilities=("state_candidates", "continuity_candidates"),
    )


def _restart_manifest(*, restart_after_turn_count: int = 1) -> ActualModelRestartRunManifest:
    return ActualModelRestartRunManifest(
        base=_base_manifest(),
        restart_after_turn_count=restart_after_turn_count,
        continuity_max_items=4,
        continuity_lifetime_revisions=3,
    )


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="durable_state_nondurable_continuity",
        family="restart_quality",
        version="1",
        turns=(
            "僕の名前はRin。次は青い箱について続けよう。",
            "再起動後。僕の名前は？ それと続きを話そう。",
        ),
    )


def test_restart_manifest_owns_explicit_process_boundary() -> None:
    manifest = _restart_manifest()
    mapping = manifest.to_mapping()

    assert mapping["restart_boundary"] == {
        "kind": "relaylm_process_restart",
        "after_turn_count": 1,
    }
    assert mapping["continuity_runtime"]["persistence"] == "process_local_non_durable"

    base = _base_manifest()
    invalid_base = ActualModelRunManifest(
        relaylm_commit=base.relaylm_commit,
        character_fixture_id=base.character_fixture_id,
        character_fixture_revision=base.character_fixture_revision,
        provider_identity=base.provider_identity,
        adapter_identity=base.adapter_identity,
        model_artifact=base.model_artifact,
        tokenizer_identity=base.tokenizer_identity,
        effective_context_window=base.effective_context_window,
        decoding_configuration=base.decoding_configuration,
        structured_output_schema_version=base.structured_output_schema_version,
        scenario_set_version=base.scenario_set_version,
        condition_id=base.condition_id,
        provider_capabilities=base.provider_capabilities,
        restart_boundary="before_scenario",
    )
    with pytest.raises(ValueError, match="wrapper owns the boundary"):
        ActualModelRestartRunManifest(
            base=invalid_base,
            restart_after_turn_count=1,
            continuity_max_items=4,
            continuity_lifetime_revisions=3,
        )


def test_restart_run_preserves_state_and_events_but_resets_continuity(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _RestartProvider()

    evidence = asyncio.run(
        run_actual_model_restart_scenario(
            character=character,
            provider=provider,
            manifest=_restart_manifest(),
            scenario=_scenario(),
        )
    )

    assert len(provider.inputs) == 2
    boundary = evidence.boundary
    assert boundary.state_before_restart == boundary.state_after_restart
    assert [item["key"] for item in boundary.state_after_restart] == ["name"]
    assert boundary.event_ids_before_restart == boundary.event_ids_after_restart
    assert len(boundary.event_ids_after_restart) == 2
    assert [item["key"] for item in boundary.continuity_before_restart["items"]] == [
        "current_subject"
    ]
    assert boundary.continuity_after_restart == {
        "max_items": 4,
        "revision": 0,
        "items": [],
    }

    post_restart_input = provider.inputs[1]
    assert [(item.state_class, item.key, item.value) for item in post_restart_input.state] == [
        ("user.identity", "name", "Rin")
    ]
    assert all(
        not item.content.startswith('{"continuity":')
        for item in post_restart_input.context
    )

    final_events = tuple(CharacterDirectory(tmp_path).iter_events())
    assert [event.actor for event in final_events] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert evidence.before_restart.turns[0].raw_model.continuity_candidates[0]["key"] == (
        "current_subject"
    )
    assert evidence.after_restart.turns[0].deterministic.resulting_state[0]["key"] == "name"


def test_restart_boundary_must_split_the_scenario(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="leave at least one turn"):
        asyncio.run(
            run_actual_model_restart_scenario(
                character=_make_character(tmp_path),
                provider=_RestartProvider(),
                manifest=_restart_manifest(restart_after_turn_count=2),
                scenario=_scenario(),
            )
        )


def test_restart_run_id_changes_when_boundary_or_runtime_configuration_changes() -> None:
    scenario = ActualModelScenario(
        scenario_id="three-turn-restart",
        family="restart_quality",
        version="1",
        turns=("one", "two", "three"),
    )
    first = _restart_manifest(restart_after_turn_count=1)
    second = _restart_manifest(restart_after_turn_count=2)
    different_runtime = ActualModelRestartRunManifest(
        base=_base_manifest(),
        restart_after_turn_count=1,
        continuity_max_items=8,
        continuity_lifetime_revisions=3,
    )

    assert stable_actual_model_restart_run_id(manifest=first, scenario=scenario) != (
        stable_actual_model_restart_run_id(manifest=second, scenario=scenario)
    )
    assert stable_actual_model_restart_run_id(manifest=first, scenario=scenario) != (
        stable_actual_model_restart_run_id(manifest=different_runtime, scenario=scenario)
    )
