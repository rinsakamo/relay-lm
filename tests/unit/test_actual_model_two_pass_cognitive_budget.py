from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_cognitive_budget import ExplicitCognitiveBudgetConfiguration
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ActualModelScenario,
    run_actual_model_scenario,
)
from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.cognition_execution_evidence import CognitionExecutionEvidenceIdentity
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory


class _Counter:
    def __init__(self, *, extraction_total: int = 90) -> None:
        self.extraction_total = extraction_total
        self.conversation_requests: list[CognitionPassRequest | None] = []
        self.extraction_requests: list[CognitionPassRequest | None] = []

    @staticmethod
    def _count(total: int) -> SerializedInputTokenCount:
        return SerializedInputTokenCount(
            total_input_tokens=total,
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )

    def count_conversation_input(
        self,
        _cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> SerializedInputTokenCount:
        self.conversation_requests.append(pass_request)
        return self._count(50)

    def count_extraction_input(
        self,
        _extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> SerializedInputTokenCount:
        self.extraction_requests.append(pass_request)
        return self._count(self.extraction_total)


class _Provider:
    def __init__(self) -> None:
        self.buffered_calls = 0
        self.streaming_calls = 0
        self.extraction_calls = 0
        self.pass1_requests: list[CognitionPassRequest | None] = []
        self.pass2_requests: list[CognitionPassRequest | None] = []

    async def generate_conversation(
        self,
        _cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        self.buffered_calls += 1
        self.pass1_requests.append(pass_request)
        return CognitionConversationOutput(response="visible")

    async def stream_generate_conversation(
        self,
        _cognitive_input: CognitiveInput,
        emit,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        self.streaming_calls += 1
        self.pass1_requests.append(pass_request)
        await emit("visible")
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(
        self,
        _extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        self.pass2_requests.append(pass_request)
        return CognitionExtractionOutput()


def _zero_plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )


def _runtime(counter: _Counter) -> TwoPassCognitiveBudgetRuntimeConfig:
    return TwoPassCognitiveBudgetRuntimeConfig(
        pass1_total=TotalBudgetConfig(
            model_context_window=100,
            reserved_output_tokens=10,
        ),
        pass2_total=TotalBudgetConfig(
            model_context_window=100,
            reserved_output_tokens=20,
        ),
        policy=BudgetDegradationPolicy(initial_plan=_zero_plan(), steps=()),
        token_counter=counter,
    )


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Eval\n\nStay grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: actual-eval\n  name: Eval\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="two-pass-budget-v1",
        family="cognitive_pressure_robustness",
        version="1",
        turns=("hello",),
    )


def _requests() -> tuple[CognitionPassRequest, CognitionPassRequest]:
    return (
        CognitionPassRequest(max_output_tokens=16),
        CognitionPassRequest(max_output_tokens=8),
    )


def _manifest(
    runtime: TwoPassCognitiveBudgetRuntimeConfig,
    *,
    execution_path: str = "buffered",
) -> ActualModelRunManifest:
    pass1, pass2 = _requests()
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="actual-eval",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="provider-v1",
        adapter_identity="adapter-v1",
        model_artifact="model@sha256:111",
        tokenizer_identity="tokenizer-v1",
        effective_context_window=100,
        decoding_configuration=(),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="two-pass-budget",
        cognitive_budget=ExplicitCognitiveBudgetConfiguration.from_runtime(runtime),
        execution_path=execution_path,  # type: ignore[arg-type]
        provider_capabilities=("state_candidates",),
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=execution_path
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.two_pass(
            pass1=pass1,
            pass2=pass2,
        ),
    )


def test_two_pass_budget_is_citable_manifest_identity() -> None:
    runtime = _runtime(_Counter())
    manifest = _manifest(runtime)

    assert manifest.to_mapping()["cognitive_budget"] == {
        "mode": "two_pass",
        "pass1": {
            "model_context_window": 100,
            "reserved_output_tokens": 10,
        },
        "pass2": {
            "model_context_window": 100,
            "reserved_output_tokens": 20,
        },
        "initial_plan": {
            "canonical_state": {"max_items": 0, "floor_items": 0},
            "working_context": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
            "retrieved_memory": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
            "event_evidence": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
        },
        "degradation_steps": [],
    }


def test_two_pass_budget_preserves_manifest_execution_type_failure() -> None:
    manifest = _manifest(_runtime(_Counter()))

    with pytest.raises(
        TypeError,
        match="cognition_execution must be CognitionExecutionEvidenceIdentity or None",
    ):
        replace(manifest, cognition_execution=object())


@pytest.mark.parametrize("execution_path", ["buffered", "streaming"])
def test_actual_model_two_pass_uses_same_budget_and_resolved_requests(
    tmp_path: Path,
    execution_path: str,
) -> None:
    counter = _Counter(extraction_total=90)
    runtime = _runtime(counter)
    provider = _Provider()
    manifest = _manifest(runtime, execution_path=execution_path)
    pass1, pass2 = _requests()

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
            cognitive_budget=runtime,
        )
    )

    assert evidence.manifest.cognitive_budget == ExplicitCognitiveBudgetConfiguration.from_runtime(
        runtime
    )
    assert evidence.turns[0].raw_model.response == "visible"
    assert evidence.turns[0].cognition_execution is not None
    assert evidence.turns[0].cognition_execution.pass2_status == "failed"
    assert evidence.turns[0].cognition_execution.pass2_failure_reason == "pass2_budget_exceeded"
    assert provider.buffered_calls + provider.streaming_calls == 1
    assert provider.extraction_calls == 0
    assert provider.pass1_requests == [pass1]
    assert provider.pass2_requests == []
    assert counter.conversation_requests == [pass1, pass1]
    assert counter.extraction_requests == [pass2]
