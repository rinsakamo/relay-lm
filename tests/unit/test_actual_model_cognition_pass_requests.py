from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
    run_actual_model_scenario,
    stable_actual_model_run_id,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionError,
    plan_actual_model_scenario_execution,
)
from relaylm.actual_model_restart import ActualModelRestartRunManifest
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory

_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_SET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v1.json"
)
_FIXTURE_ROOT = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)


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
        scenario_id="cognition-pass-request-v1",
        family="state_candidate_quality",
        version="1",
        turns=("hello",),
    )


def _manifest(
    *,
    cognition_execution: CognitionExecutionEvidenceIdentity,
    cognition_pass_requests: ActualModelCognitionPassRequests | None = None,
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
        effective_context_window=1024,
        decoding_configuration=(("temperature", 0.0), ("top_p", 1.0)),
        seed=7,
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="cogp5-screening",
        budgets=ExplicitBudgetConfiguration(),
        execution_path=execution_path,
        provider_capabilities=("state_candidates",),
        cognition_execution=cognition_execution,
        cognition_pass_requests=cognition_pass_requests,
    )


class _SinglePassRequestProvider:
    def __init__(self) -> None:
        self.requests: list[CognitionPassRequest] = []

    async def generate(
        self,
        _: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        assert pass_request is not None
        self.requests.append(pass_request)
        return CognitiveOutput(response="single")


class _TwoPassRequestProvider:
    def __init__(self) -> None:
        self.pass1_requests: list[CognitionPassRequest] = []
        self.pass2_requests: list[CognitionPassRequest] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("single-pass generation must not run")

    async def generate_conversation(
        self,
        _: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        assert pass_request is not None
        self.pass1_requests.append(pass_request)
        return CognitionConversationOutput(response="conversation")

    async def generate_extraction(
        self,
        _: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        assert pass_request is not None
        self.pass2_requests.append(pass_request)
        return CognitionExtractionOutput()


def test_cognition_pass_requests_are_explicit_run_identity() -> None:
    off = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    bounded = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.BOUNDED,
        reasoning_budget=64,
        temperature=0,
        top_p=1,
    )
    topology = CognitionExecutionEvidenceIdentity.two_pass(
        execution_path=BUFFERED_EXECUTION_PATH
    )

    baseline = _manifest(cognition_execution=topology)
    configured = _manifest(
        cognition_execution=topology,
        cognition_pass_requests=ActualModelCognitionPassRequests.two_pass(
            pass1=off,
            pass2=bounded,
        ),
    )

    assert "cognition_pass_requests" not in baseline.to_mapping()
    assert configured.to_mapping()["cognition_pass_requests"] == {
        "format_version": 1,
        "single_pass": None,
        "pass1": {
            "reasoning_mode": "off",
            "reasoning_budget": None,
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": None,
            "structured_output_mode": None,
        },
        "pass2": {
            "reasoning_mode": "bounded",
            "reasoning_budget": 64,
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": None,
            "structured_output_mode": None,
        },
    }
    assert stable_actual_model_run_id(
        manifest=baseline,
        scenario=_scenario(),
    ) != stable_actual_model_run_id(
        manifest=configured,
        scenario=_scenario(),
    )


def test_manifest_rejects_pass_request_shape_that_does_not_match_topology() -> None:
    off = CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF)

    with pytest.raises(ValueError, match="single_pass cognition pass requests"):
        _manifest(
            cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
                execution_path=BUFFERED_EXECUTION_PATH
            ),
            cognition_pass_requests=ActualModelCognitionPassRequests.two_pass(
                pass1=off,
                pass2=off,
            ),
        )

    with pytest.raises(ValueError, match="two_pass cognition pass requests"):
        _manifest(
            cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
                execution_path=BUFFERED_EXECUTION_PATH
            ),
            cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(off),
        )

    with pytest.raises(ValueError, match="buffered"):
        _manifest(
            execution_path="streaming",
            cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
                execution_path="streaming"
            ),
            cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(off),
        )


def test_actual_model_single_pass_carries_explicit_resolved_request(tmp_path: Path) -> None:
    off = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    provider = _SinglePassRequestProvider()
    manifest = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(off),
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
        )
    )

    assert provider.requests == [off]
    assert evidence.turns[0].raw_model.response == "single"


def test_actual_model_two_pass_carries_distinct_resolved_requests(tmp_path: Path) -> None:
    off = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    bounded = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.BOUNDED,
        reasoning_budget=64,
        temperature=0,
        top_p=1,
    )
    provider = _TwoPassRequestProvider()
    manifest = _manifest(
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.two_pass(
            pass1=off,
            pass2=bounded,
        ),
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=manifest,
            scenario=_scenario(),
        )
    )

    assert provider.pass1_requests == [off]
    assert provider.pass2_requests == [bounded]
    assert evidence.turns[0].raw_model.response == "conversation"
    assert evidence.turns[0].cognition_execution is not None
    assert evidence.turns[0].cognition_execution.pass2_status == "committed"


def test_restart_scenario_rejects_pass_request_evidence_until_restart_bridge_exists() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    off = CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF)
    manifest = ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity="provider-v1",
        adapter_identity="adapter-v1",
        model_artifact="model@sha256:111",
        tokenizer_identity="tokenizer-v1",
        effective_context_window=1024,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="cogp5-screening",
        provider_capabilities=("state_candidates", "continuity_candidates"),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        ),
        cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(off),
    )

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="restart scenarios do not support cognition pass request evidence",
    ):
        plan_actual_model_scenario_execution(
            scenario_set=scenario_set,
            scenario_id="restart-durable-vs-temporary-v1",
            fixture_root=_FIXTURE_ROOT,
            manifest=manifest,
        )

    with pytest.raises(
        ValueError,
        match="restart evidence does not support cognition pass request evidence",
    ):
        ActualModelRestartRunManifest(
            base=manifest,
            restart_after_turn_count=1,
            continuity_max_items=4,
            continuity_lifetime_revisions=3,
        )
