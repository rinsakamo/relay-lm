from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    run_actual_model_scenario,
    stable_actual_model_run_id,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    STREAMING_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Eval\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: actual-eval\n  name: Eval\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="cognition-execution-v1",
        family="state_candidate_quality",
        version="1",
        turns=("I am choosing tea.",),
    )


def _manifest(
    *,
    cognition_execution: CognitionExecutionEvidenceIdentity | None = None,
    execution_path: str = "buffered",
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="actual-eval",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="provider-v1",
        adapter_identity="adapter-v1",
        model_artifact="model@sha256:111",
        tokenizer_identity="tokenizer-v1",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        seed=7,
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="cognition-execution",
        budgets=ExplicitBudgetConfiguration(),
        execution_path=execution_path,
        provider_capabilities=("state_candidates",),
        cognition_execution=cognition_execution,
    )


class _TwoPassProvider:
    def __init__(self) -> None:
        self.single_calls = 0
        self.conversation_calls = 0
        self.extraction_calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.single_calls += 1
        raise AssertionError("canonical single-pass must not run in two_pass evidence")

    async def generate_conversation(self, _: CognitiveInput) -> CognitionConversationOutput:
        self.conversation_calls += 1
        return CognitionConversationOutput(response="Pass 1 response")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="tea",
                    sources=(source,),
                ),
            )
        )


class _SecondPassFailureProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.extraction_calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("single-pass must not run")

    async def generate_conversation(self, _: CognitiveInput) -> CognitionConversationOutput:
        self.conversation_calls += 1
        return CognitionConversationOutput(response=f"reply-{self.conversation_calls}")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        if self.extraction_calls == 2:
            raise RuntimeError("second extraction failed")
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="tea",
                    sources=(extraction_input.originating_event_id,),
                ),
            )
        )


class _ShadowProvider:
    def __init__(self) -> None:
        self.single_calls = 0
        self.extraction_calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.single_calls += 1
        return CognitiveOutput(
            response="Canonical response",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="tea",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="coffee",
                    sources=(extraction_input.originating_event_id,),
                ),
            )
        )


def test_legacy_manifest_mapping_is_unchanged_when_execution_identity_is_absent() -> None:
    legacy = _manifest()
    mapping = legacy.to_mapping()

    assert "cognition_execution" not in mapping

    explicit = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        )
    )
    assert explicit.to_mapping()["cognition_execution"]["mode"] == "single_pass"
    assert stable_actual_model_run_id(
        manifest=legacy, scenario=_scenario()
    ) != stable_actual_model_run_id(manifest=explicit, scenario=_scenario())


def test_manifest_rejects_execution_identity_delivery_mismatch() -> None:
    with pytest.raises(ValueError, match="cognition execution path"):
        _manifest(
            execution_path="buffered",
            cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
                execution_path=STREAMING_EXECUTION_PATH
            ),
        )


def test_two_pass_actual_model_evidence_separates_pass1_and_pass2_and_commits_pass2(
    tmp_path: Path,
) -> None:
    provider = _TwoPassProvider()
    manifest = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        )
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
        )
    )

    assert provider.single_calls == 0
    assert provider.conversation_calls == 1
    assert provider.extraction_calls == 1
    turn = evidence.turns[0]
    assert turn.raw_model.response == "Pass 1 response"
    assert turn.raw_model.state_candidates[0]["value"] == "tea"
    assert turn.deterministic.resulting_state[0]["value"] == "tea"
    assert turn.cognition_execution is not None
    assert turn.cognition_execution.mode == "two_pass"
    assert turn.cognition_execution.pass2_status == "committed"
    assert turn.cognition_execution.pass2_raw is not None
    assert turn.cognition_execution.pass2_raw.state_candidates[0]["value"] == "tea"
    assert turn.cognition_execution.shadow_status is None


def test_failed_later_pass2_does_not_reuse_previous_turn_raw_output(tmp_path: Path) -> None:
    provider = _SecondPassFailureProvider()
    manifest = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        )
    )
    scenario = ActualModelScenario(
        scenario_id="two-turn-pass2-failure-v1",
        family="state_candidate_quality",
        version="1",
        turns=("first", "second"),
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=scenario,
        )
    )

    assert evidence.turns[0].cognition_execution is not None
    assert evidence.turns[0].cognition_execution.pass2_raw is not None
    second = evidence.turns[1]
    assert second.raw_model.response == "reply-2"
    assert second.raw_model.state_candidates == ()
    assert second.cognition_execution is not None
    assert second.cognition_execution.pass2_status == "failed"
    assert second.cognition_execution.pass2_failure_reason == "pass2_failed"
    assert second.cognition_execution.pass2_raw is None


def test_shadow_actual_model_evidence_keeps_canonical_raw_and_separate_shadow_raw(
    tmp_path: Path,
) -> None:
    provider = _ShadowProvider()
    manifest = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.shadow_two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        )
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
        )
    )

    assert provider.single_calls == 1
    assert provider.extraction_calls == 1
    turn = evidence.turns[0]
    assert turn.raw_model.response == "Canonical response"
    assert turn.raw_model.state_candidates[0]["value"] == "tea"
    assert turn.deterministic.resulting_state[0]["value"] == "tea"
    assert turn.cognition_execution is not None
    assert turn.cognition_execution.mode == "shadow_two_pass"
    assert turn.cognition_execution.pass2_status is None
    assert turn.cognition_execution.shadow_status == "completed"
    assert turn.cognition_execution.shadow_raw is not None
    assert turn.cognition_execution.shadow_raw.state_candidates[0]["value"] == "coffee"
    assert CharacterDirectory(tmp_path).load_state().states[0].value == "tea"
