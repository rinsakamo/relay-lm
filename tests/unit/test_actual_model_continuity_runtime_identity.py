from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitContinuityRuntimeConfiguration,
    run_actual_model_scenario,
    stable_actual_model_run_id,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import (
    ContinuityCandidate,
    ContinuityContext,
    ContinuityItem,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime


class _ContinuityProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        source = cognitive_input.input.id
        return CognitiveOutput(
            response="その青い箱の話を続けよう。",
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


def _character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Continuity Identity Fixture\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: continuity-identity\n  name: Aoi\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _manifest(
    *, continuity: ExplicitContinuityRuntimeConfiguration | None = None
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="d235dc3ff7f74290c508d99250feb38da5d1ff4e",
        character_fixture_id="continuity-identity",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id="baseline",
        continuity_runtime=continuity,
        provider_capabilities=("continuity_candidates",),
    )


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="continuity-runtime-identity",
        family="continuity_proposal_quality",
        version="1",
        turns=("青い箱について続けよう。",),
    )


def _runtime(*, max_items: int = 4, lifetime_revisions: int = 3) -> ContinuityRuntime:
    return ContinuityRuntime(
        context=ContinuityContext(max_items=max_items),
        lifetime_revisions=lifetime_revisions,
    )


def test_continuity_runtime_configuration_is_explicit_and_bounded() -> None:
    config = ExplicitContinuityRuntimeConfiguration(
        max_items=4,
        lifetime_revisions=3,
    )
    assert config.to_mapping() == {
        "max_items": 4,
        "lifetime_revisions": 3,
        "persistence": "process_local_non_durable",
    }

    with pytest.raises(ValueError, match="max_items.*positive"):
        ExplicitContinuityRuntimeConfiguration(max_items=0, lifetime_revisions=3)
    with pytest.raises(TypeError, match="lifetime_revisions.*integer"):
        ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=True,  # type: ignore[arg-type]
        )


def test_supplied_runtime_is_materialized_into_evidence_identity(tmp_path: Path) -> None:
    manifest = _manifest()
    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_character(tmp_path),
            provider=_ContinuityProvider(),
            manifest=manifest,
            scenario=_scenario(),
            continuity_runtime=_runtime(max_items=4, lifetime_revisions=3),
        )
    )

    assert manifest.continuity_runtime is None
    assert evidence.manifest.continuity_runtime == ExplicitContinuityRuntimeConfiguration(
        max_items=4,
        lifetime_revisions=3,
    )
    assert evidence.manifest.to_mapping()["continuity_runtime"] == {
        "max_items": 4,
        "lifetime_revisions": 3,
        "persistence": "process_local_non_durable",
    }
    assert evidence.run_id == stable_actual_model_run_id(
        manifest=evidence.manifest,
        scenario=_scenario(),
    )
    assert evidence.run_id != stable_actual_model_run_id(
        manifest=manifest,
        scenario=_scenario(),
    )


def test_declared_runtime_is_constructed_from_manifest_before_generation(tmp_path: Path) -> None:
    provider = _ContinuityProvider()
    manifest = _manifest(
        continuity=ExplicitContinuityRuntimeConfiguration(
            max_items=6,
            lifetime_revisions=2,
        )
    )
    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
        )
    )

    assert provider.calls == 1
    resulting = evidence.turns[0].deterministic.resulting_continuity
    assert resulting is not None
    assert resulting["max_items"] == 6
    assert resulting["revision"] == 1
    assert resulting["items"][0]["expires_revision"] == 3


def test_runtime_configuration_changes_stable_run_identity() -> None:
    scenario = _scenario()
    four_items = _manifest(
        continuity=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        )
    )
    eight_items = _manifest(
        continuity=ExplicitContinuityRuntimeConfiguration(
            max_items=8,
            lifetime_revisions=3,
        )
    )

    assert stable_actual_model_run_id(
        manifest=four_items,
        scenario=scenario,
    ) != stable_actual_model_run_id(
        manifest=eight_items,
        scenario=scenario,
    )


def test_declared_and_supplied_runtime_must_match_before_provider_call(
    tmp_path: Path,
) -> None:
    provider = _ContinuityProvider()
    manifest = _manifest(
        continuity=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        )
    )

    with pytest.raises(ValueError, match="does not match the run manifest"):
        asyncio.run(
            run_actual_model_scenario(
                character=_character(tmp_path),
                provider=provider,
                manifest=manifest,
                scenario=_scenario(),
                continuity_runtime=_runtime(max_items=8, lifetime_revisions=3),
            )
        )
    assert provider.calls == 0


def test_supplied_runtime_must_start_from_empty_revision_zero_context(
    tmp_path: Path,
) -> None:
    provider = _ContinuityProvider()
    context = ContinuityContext(
        max_items=4,
        revision=1,
        items=(
            ContinuityItem(
                item_id="ci-existing",
                kind="referent",
                key="existing",
                value="already present",
                sources=("evt-existing",),
                epistemic_role="user_assertion",
                accepted_revision=1,
                expires_revision=4,
            ),
        ),
    )

    with pytest.raises(ValueError, match="empty revision-0 context"):
        asyncio.run(
            run_actual_model_scenario(
                character=_character(tmp_path),
                provider=provider,
                manifest=_manifest(),
                scenario=_scenario(),
                continuity_runtime=ContinuityRuntime(
                    context=context,
                    lifetime_revisions=3,
                ),
            )
        )
    assert provider.calls == 0
