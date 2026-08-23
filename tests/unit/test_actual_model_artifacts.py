from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import (
    ActualModelArtifactError,
    character_fixture_revision,
    load_actual_model_evidence_mapping,
    prepare_character_fixture_workspace,
    run_actual_model_fixture,
    write_actual_model_evidence,
)
from relaylm.actual_model_evaluation import ActualModelRunManifest, ActualModelScenario
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory


class _FixtureProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response=self.response)


def _make_fixture(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Fixture Character\n\nStay grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: fixture\n  name: Fixture\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _manifest(revision: str, *, replicate_id: str = "0") -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="ae4d7afd6599b8587f1de0bbf6ec9dd52e8b55d8",
        character_fixture_id="fixture-character-v1",
        character_fixture_revision=revision,
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test-tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-fixture-v1",
        condition_id="baseline",
        provider_capabilities=("state_candidates",),
        replicate_id=replicate_id,
    )


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="fixture_isolation",
        family="response_persona_continuity",
        turns=("こんにちは。",),
        version="1",
    )


def test_character_fixture_revision_covers_path_and_bytes(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    before = character_fixture_revision(fixture)

    (fixture / "SOUL.md").write_text(
        "# Fixture Character\n\nChanged fixture semantics.\n",
        encoding="utf-8",
    )
    after_content_change = character_fixture_revision(fixture)
    assert after_content_change != before

    (fixture / "SOUL.md").rename(fixture / "IDENTITY.md")
    after_path_change = character_fixture_revision(fixture)
    assert after_path_change != after_content_change


def test_workspace_requires_manifest_revision_and_never_reuses_existing_directory(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    revision = character_fixture_revision(fixture)

    with pytest.raises(ActualModelArtifactError, match="does not match run manifest"):
        prepare_character_fixture_workspace(
            fixture_root=fixture,
            workspace_root=tmp_path / "wrong",
            manifest=_manifest("sha256:" + "0" * 64),
        )

    workspace = tmp_path / "workspace"
    prepared = prepare_character_fixture_workspace(
        fixture_root=fixture,
        workspace_root=workspace,
        manifest=_manifest(revision),
    )
    assert prepared.root == workspace
    assert character_fixture_revision(workspace) == revision

    with pytest.raises(ActualModelArtifactError, match="must not already exist"):
        prepare_character_fixture_workspace(
            fixture_root=fixture,
            workspace_root=workspace,
            manifest=_manifest(revision),
        )


def test_actual_model_run_mutates_workspace_not_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    revision = character_fixture_revision(fixture)
    provider = _FixtureProvider("こんにちは。")

    evidence = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run",
            provider=provider,
            manifest=_manifest(revision),
            scenario=_scenario(),
        )
    )

    assert provider.calls == 1
    assert character_fixture_revision(fixture) == revision
    assert not (fixture / "memory" / "events.jsonl").exists()
    run_events = list(CharacterDirectory(tmp_path / "run").iter_events())
    assert [event.actor for event in run_events] == ["user", "assistant"]
    assert evidence.manifest.character_fixture_revision == revision


def test_evidence_artifact_is_run_id_addressed_idempotent_and_non_overwriting(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    revision = character_fixture_revision(fixture)
    manifest = _manifest(revision)
    scenario = _scenario()

    first = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run-a",
            provider=_FixtureProvider("first response"),
            manifest=manifest,
            scenario=scenario,
        )
    )
    artifact_root = tmp_path / "artifacts"
    path = write_actual_model_evidence(evidence=first, artifact_root=artifact_root)
    assert path.name == f"{first.run_id}.json"
    assert write_actual_model_evidence(evidence=first, artifact_root=artifact_root) == path
    loaded = load_actual_model_evidence_mapping(path)
    assert loaded["run_id"] == first.run_id
    assert loaded["turns"][0]["raw_model"]["response"] == "first response"

    conflicting = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run-b",
            provider=_FixtureProvider("different nondeterministic response"),
            manifest=manifest,
            scenario=scenario,
        )
    )
    assert conflicting.run_id == first.run_id
    with pytest.raises(ActualModelArtifactError, match="distinct replicate_id"):
        write_actual_model_evidence(evidence=conflicting, artifact_root=artifact_root)


def test_replicate_id_produces_distinct_citable_artifact_identity(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    revision = character_fixture_revision(fixture)
    scenario = _scenario()

    first = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run-0",
            provider=_FixtureProvider("response"),
            manifest=_manifest(revision, replicate_id="0"),
            scenario=scenario,
        )
    )
    second = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run-1",
            provider=_FixtureProvider("response"),
            manifest=_manifest(revision, replicate_id="1"),
            scenario=scenario,
        )
    )

    assert first.run_id != second.run_id


def test_evidence_writer_rejects_non_content_derived_run_id(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    _make_fixture(fixture)
    revision = character_fixture_revision(fixture)
    evidence = asyncio.run(
        run_actual_model_fixture(
            fixture_root=fixture,
            workspace_root=tmp_path / "run",
            provider=_FixtureProvider("response"),
            manifest=_manifest(revision),
            scenario=_scenario(),
        )
    )
    forged = replace(evidence, run_id="amr-" + "f" * 64)
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelArtifactError,
        match="run_id does not match actual-model evidence",
    ):
        write_actual_model_evidence(evidence=forged, artifact_root=artifact_root)

    assert not artifact_root.exists()
