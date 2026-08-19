from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.crystallization import CrystallizationInput, CrystallizationOutput
from relaylm.events import Event
from relaylm.memory_provenance import MemoryTemporalScope, MemoryUnit
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory


MODULE = "relaylm.actual_model_crystallization"


def _subject():
    spec = importlib.util.find_spec(MODULE)
    assert spec is not None, "CRY2 actual-model crystallization evidence is not implemented"
    return importlib.import_module(MODULE)


class _ScriptedCrystallizer:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CrystallizationInput] = []

    async def generate(self, crystallization_input: CrystallizationInput) -> CrystallizationOutput:
        self.calls += 1
        self.inputs.append(crystallization_input)
        user_source = next(event.id for event in crystallization_input.events if event.actor == "user")
        assistant_source = next(
            event.id for event in crystallization_input.events if event.actor == "assistant"
        )
        return CrystallizationOutput(
            memory_units=(
                MemoryUnit(
                    heading="Preferences",
                    content="Rin likes tea.",
                    temporal_scope=MemoryTemporalScope.UNKNOWN,
                ),
                MemoryUnit(
                    heading="Historical assistant claim",
                    content="The assistant once said Rin lived in Hokkaido.",
                    temporal_scope=MemoryTemporalScope.UNKNOWN,
                ),
            ),
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(user_source,),
                ),
                StateCandidate.set(
                    state_class="user.fact",
                    key="residence_location",
                    value="Hokkaido",
                    sources=(assistant_source,),
                ),
            ),
        )


def _make_character(root: Path, *, prior_memory: str | None = "# Prior\n\nOld synthesis.\n") -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Actual Model Crystallization Character\n\nBe grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: actual-crystallization\n  name: Actual Crystallization\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    if prior_memory is not None:
        character.save_memory_markdown(prior_memory)

    character.append_event(
        Event.create(
            type="message",
            actor="user",
            payload={"content": "old event outside the bounded window"},
            event_id="crystal-old-user",
            timestamp="2026-08-18T00:00:00+00:00",
        )
    )
    character.append_event(
        Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="crystal-user-tea",
            timestamp="2026-08-18T00:01:00+00:00",
        )
    )
    character.append_event(
        Event.create(
            type="message",
            actor="assistant",
            payload={"content": "あなたは北海道に住んでいる"},
            event_id="crystal-assistant-hokkaido",
            timestamp="2026-08-18T00:02:00+00:00",
        )
    )
    return character


def _manifest(*, model_artifact: str = "google/gemma-4-12b@sha256:111", max_events: int = 2):
    subject = _subject()
    return subject.ActualModelCrystallizationManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="fixture-crystallization-aoi",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="lm-studio-openai-compatible",
        adapter_identity="relaylm.providers.OpenAICompatibleCrystallizer:v2",
        model_artifact=model_artifact,
        tokenizer_identity="gemma-4-tokenizer-v1",
        effective_context_window=32768,
        decoding_configuration=(("temperature", 0.0), ("top_p", 1.0)),
        reasoning_identity=subject.ActualModelCrystallizationReasoningIdentity(
            required_setting="on",
            effective_setting="on",
            allowed_options=("off", "on"),
            live_default="on",
            control_source="lmstudio_model_default",
            control_mode="attested_default_without_per_request_override",
        ),
        seed=7,
        structured_output_schema_version="relaylm_crystallization_output:v2",
        evaluation_contract_version="actual-model-crystallization-v2",
        condition_id="baseline",
        max_events=max_events,
        replicate_id="0",
    )


def _case():
    subject = _subject()
    return subject.ActualModelCrystallizationCase(
        case_id="correction-and-durability",
        version="1",
    )


def test_manifest_is_exact_and_crystallization_specific() -> None:
    subject = _subject()
    manifest = _manifest()

    assert manifest.max_events == 2
    assert manifest.structured_output_schema_version == "relaylm_crystallization_output:v2"
    assert manifest.reasoning_identity.to_mapping() == {
        "format_version": 1,
        "required_setting": "on",
        "effective_setting": "on",
        "allowed_options": ["off", "on"],
        "live_default": "on",
        "control_source": "lmstudio_model_default",
        "control_mode": "attested_default_without_per_request_override",
    }
    assert manifest.to_mapping()["execution_kind"] == "off_turn_crystallization"
    assert "continuity_runtime" not in manifest.to_mapping()
    assert "scenario_set_version" not in manifest.to_mapping()

    with pytest.raises(ValueError, match="exact 40-character Git SHA"):
        replace(manifest, relaylm_commit="v1")
    with pytest.raises(ValueError, match="max_events"):
        replace(manifest, max_events=-1)
    with pytest.raises(ValueError, match="decoding_configuration keys must be unique"):
        replace(manifest, decoding_configuration=(("temperature", 0.0), ("temperature", 1.0)))

    assert subject.ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION == 3


def test_runner_records_exact_bounded_input_raw_output_and_deterministic_result(tmp_path: Path) -> None:
    subject = _subject()
    character = _make_character(tmp_path)
    crystallizer = _ScriptedCrystallizer()

    evidence = asyncio.run(
        subject.run_actual_model_crystallization(
            character=character,
            crystallizer=crystallizer,
            manifest=_manifest(max_events=2),
            case=_case(),
        )
    )

    assert crystallizer.calls == 1
    assert len(crystallizer.inputs) == 1
    assert [item["id"] for item in evidence.input.events] == [
        "crystal-user-tea",
        "crystal-assistant-hokkaido",
    ]
    assert evidence.input.prior_memory == "# Prior\n\nOld synthesis.\n"
    assert evidence.input.identity["content"].startswith("# Actual Model Crystallization Character")

    assert evidence.raw_model.memory_units[0]["content"] == "Rin likes tea."
    assert [item["key"] for item in evidence.raw_model.state_candidates] == [
        "tea",
        "residence_location",
    ]
    assert [item["status"] for item in evidence.deterministic.state_decisions] == [
        "accepted",
        "rejected",
    ]
    assert evidence.deterministic.state_decisions[1]["reason"] == "user_state_requires_user_source"
    assert [item["key"] for item in evidence.deterministic.resulting_state] == ["tea"]
    assert evidence.deterministic.memory_changed is True
    assert evidence.deterministic.resulting_memory is not None
    assert "Rin likes tea" in evidence.deterministic.resulting_memory
    assert evidence.product_quality == ()


def test_evidence_serialization_keeps_raw_and_deterministic_channels_separate(tmp_path: Path) -> None:
    subject = _subject()
    evidence = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(),
            case=_case(),
        )
    )

    payload = json.loads(evidence.to_json())
    assert payload["run_id"] == evidence.run_id
    assert payload["input"]["events"][0]["id"] == "crystal-user-tea"
    assert payload["raw_model"]["state_candidates"][1]["key"] == "residence_location"
    assert payload["deterministic_relay"]["state_decisions"][1]["status"] == "rejected"
    resulting = payload["deterministic_relay"]["resulting_state"]
    assert len(resulting) == 1
    assert resulting[0]["state_class"] == "user.preference"
    assert resulting[0]["key"] == "tea"
    assert resulting[0]["value"] == "likes"
    assert resulting[0]["sources"] == ["crystal-user-tea"]
    assert resulting[0]["status"] == "active"
    assert isinstance(resulting[0]["valid_from"], str) and resulting[0]["valid_from"]
    assert resulting[0]["valid_to"] is None
    assert payload["product_quality"] == []
    assert "score" not in payload


def test_run_identity_changes_with_model_budget_or_actual_prepass_input(tmp_path: Path) -> None:
    subject = _subject()

    first = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "first", prior_memory="# Prior\n\nA\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(),
            case=_case(),
        )
    )
    same = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "same", prior_memory="# Prior\n\nA\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(),
            case=_case(),
        )
    )
    changed_model = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "model", prior_memory="# Prior\n\nA\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(model_artifact="google/gemma-4-12b@sha256:222"),
            case=_case(),
        )
    )
    changed_reasoning = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "reasoning", prior_memory="# Prior\n\nA\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=replace(
                _manifest(),
                reasoning_identity=subject.ActualModelCrystallizationReasoningIdentity(
                    required_setting="off",
                    effective_setting="off",
                    allowed_options=("off", "on"),
                    live_default="off",
                    control_source="lmstudio_model_default",
                    control_mode="attested_default_without_per_request_override",
                ),
            ),
            case=_case(),
        )
    )
    changed_budget = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "budget", prior_memory="# Prior\n\nA\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(max_events=3),
            case=_case(),
        )
    )
    changed_input = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "input", prior_memory="# Prior\n\nB\n"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(),
            case=_case(),
        )
    )

    assert first.run_id == same.run_id
    assert first.run_id != changed_model.run_id
    assert first.run_id != changed_reasoning.run_id
    assert first.run_id != changed_budget.run_id
    assert first.run_id != changed_input.run_id


def test_quality_review_requires_exact_bounded_axes_and_has_no_composite_score() -> None:
    subject = _subject()
    observations = tuple(
        subject.CrystallizationQualityObservation(axis=axis, outcome="pass")
        for axis in subject.CRYSTALLIZATION_QUALITY_AXES
    )
    review = subject.ActualModelCrystallizationReview(
        reviewer_identity="rin/manual-review-v1",
        evidence_run_ids=("run-a", "run-b"),
        case_id="correction-and-durability",
        case_version="1",
        observations=observations,
    )

    payload = review.to_mapping()
    assert tuple(item["axis"] for item in payload["observations"]) == subject.CRYSTALLIZATION_QUALITY_AXES
    assert payload["evidence_run_ids"] == ["run-a", "run-b"]
    assert "score" not in payload
    assert review.review_id == subject.stable_actual_model_crystallization_review_id(review)

    with pytest.raises(ValueError, match="exact crystallization quality axes"):
        replace(review, observations=observations[:-1])
    with pytest.raises(ValueError, match="evidence_run_ids must not contain duplicates"):
        replace(review, evidence_run_ids=("run-a", "run-a"))


def test_quality_axes_cover_the_architecture_decision() -> None:
    subject = _subject()
    assert subject.CRYSTALLIZATION_QUALITY_AXES == (
        "durable_information_selection",
        "state_taxonomy_key_normalization",
        "transient_durable_discipline",
        "correction_supersession_preservation",
        "temporal_provenance_fidelity",
        "memory_organization_readability",
        "semantic_stability",
    )


def test_evidence_artifact_is_idempotent_and_conflict_requires_distinct_identity(tmp_path: Path) -> None:
    subject = _subject()
    evidence = asyncio.run(
        subject.run_actual_model_crystallization(
            character=_make_character(tmp_path / "character"),
            crystallizer=_ScriptedCrystallizer(),
            manifest=_manifest(),
            case=_case(),
        )
    )
    artifact_root = tmp_path / "artifacts"

    first_path = subject.write_actual_model_crystallization_evidence(
        evidence=evidence,
        artifact_root=artifact_root,
    )
    second_path = subject.write_actual_model_crystallization_evidence(
        evidence=evidence,
        artifact_root=artifact_root,
    )
    assert first_path == second_path
    assert json.loads(first_path.read_text(encoding="utf-8"))["run_id"] == evidence.run_id

    conflicting = replace(
        evidence,
        raw_model=replace(
            evidence.raw_model,
            memory_units=({"heading": "Different"},),
        ),
    )
    with pytest.raises(subject.ActualModelCrystallizationArtifactError, match="run ID already exists"):
        subject.write_actual_model_crystallization_evidence(
            evidence=conflicting,
            artifact_root=artifact_root,
        )
