from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from relaylm.actual_model_artifacts import (
    character_fixture_revision,
    run_actual_model_fixture,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
)
from relaylm.actual_model_scenarios import ActualModelScenarioSet, load_actual_model_scenario_set
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotTarget,
    ActualModelRepositorySnapshotVerification,
    load_actual_model_repository_snapshot_target,
    verify_actual_model_repository_snapshot,
)
from relaylm.actual_model_vllm import (
    bind_vllm_execution_condition,
    vllm_manifest_provider_identity,
)
from relaylm.actual_model_vllm_capacity import (
    VLLMCapacityFootprintObservation,
    VLLMCapacitySelectedLayerOccupancy,
    VLLMRuntimeCapacityEvidence,
    VLLMRuntimeCapacityEvidenceError,
    validate_capacity_coverage,
    validate_vllm_model_runner,
    vllm_capacity_pass_request_id,
    write_vllm_runtime_capacity_evidence,
)
from relaylm.actual_model_vllm_counter import PostJSON, VLLMServingTokenizerCounter
from relaylm.actual_model_vllm_host import (
    CANONICAL_FIXTURE_PATH,
    CANONICAL_SCENARIO_SET_PATH,
    CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION,
    CANONICAL_VLLM_TARGET_PATH,
    FetchJSON,
    VLLMScreeningCondition,
    VLLMScreeningPlan,
    _required_capacity_coverage,
    _validate_scenarios,
    _verify_clean_exact_repo,
    acquire_vllm_reasoning_capability,
    load_vllm_reasoning_probe_proof,
)
from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
    OpenAICompatibleTwoPassSerializedInputCounter,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_reasoning_capability import VLLMReasoningCapabilityAttestation


class VLLMCapacityAcquisitionError(ValueError):
    """A vLLM capacity-acquisition trajectory cannot be measured truthfully."""


@dataclass(frozen=True, slots=True)
class VLLMCapacityAcquisitionArtifact:
    evidence_id: str
    artifact_path: str
    footprint_count: int
    maximum_observed_input_tokens: int
    complete: bool

    def to_mapping(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "artifact_path": self.artifact_path,
            "footprint_count": self.footprint_count,
            "maximum_observed_input_tokens": self.maximum_observed_input_tokens,
            "complete": self.complete,
        }


class VLLMCapacityAcquisitionFailure(VLLMCapacityAcquisitionError):
    """Capacity acquisition stopped after zero or more truthfully measured requests."""

    def __init__(
        self,
        message: str,
        *,
        artifact: VLLMCapacityAcquisitionArtifact | None = None,
    ) -> None:
        super().__init__(message)
        self.artifact = artifact


@dataclass(frozen=True, slots=True)
class PreparedVLLMCapacityAcquisition:
    """Fresh runtime identity and exact counters prepared without capacity citation."""

    plan: VLLMScreeningPlan
    screening_condition_id: str
    condition: VLLMScreeningCondition
    target: ActualModelRepositorySnapshotTarget
    snapshot_verification: ActualModelRepositorySnapshotVerification
    reasoning_capability: VLLMReasoningCapabilityAttestation
    scenario_set: ActualModelScenarioSet
    fixture_root: Path
    provider: OpenAICompatibleProvider
    manifest: ActualModelRunManifest
    model_runner: str
    serving_counter: VLLMServingTokenizerCounter
    single_pass_counter: OpenAICompatibleSerializedInputCounter | None
    two_pass_counter: OpenAICompatibleTwoPassSerializedInputCounter | None
    scenario_ids: tuple[str, ...]


class VLLMCapacityMeasurementProvider:
    """Measure exact production inputs immediately before real provider delegation.

    The wrapper never serializes prompts itself. It delegates counting to the
    existing OpenAI-compatible serialized-input counters, binds each successful
    count to the selected screening condition/scenario/pass coordinate, records
    that content-free observation, and only then invokes the real provider.
    Consequently an upstream provider failure cannot erase a footprint already
    proven by the serving tokenizer, while calls that were never reached are
    never fabricated.
    """

    def __init__(
        self,
        *,
        delegate: Any,
        condition: VLLMScreeningCondition,
        scenario_id: str,
        single_pass_counter: OpenAICompatibleSerializedInputCounter | Any | None = None,
        two_pass_counter: OpenAICompatibleTwoPassSerializedInputCounter | Any | None = None,
    ) -> None:
        if not isinstance(condition, VLLMScreeningCondition):
            raise TypeError("condition must be VLLMScreeningCondition")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        if condition.pass_requests.mode == "single_pass":
            if single_pass_counter is None:
                raise VLLMCapacityAcquisitionError(
                    "single-pass capacity measurement requires a single-pass counter"
                )
            if two_pass_counter is not None:
                raise VLLMCapacityAcquisitionError(
                    "single-pass capacity measurement must not receive a two-pass counter"
                )
        elif condition.pass_requests.mode == "two_pass":
            if two_pass_counter is None:
                raise VLLMCapacityAcquisitionError(
                    "two-pass capacity measurement requires a two-pass counter"
                )
            if single_pass_counter is not None:
                raise VLLMCapacityAcquisitionError(
                    "two-pass capacity measurement must not receive a single-pass counter"
                )
        else:
            raise VLLMCapacityAcquisitionError(
                "unsupported screening pass-request topology"
            )
        self.delegate = delegate
        self.condition = condition
        self.scenario_id = scenario_id
        self.single_pass_counter = single_pass_counter
        self.two_pass_counter = two_pass_counter
        self._observations: list[VLLMCapacityFootprintObservation] = []
        self._single_turns = 0
        self._conversation_turns = 0
        self._extraction_turns = 0

    @property
    def observations(self) -> tuple[VLLMCapacityFootprintObservation, ...]:
        return tuple(self._observations)

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        expected = self.condition.pass_requests.single_request
        if self.condition.pass_requests.mode != "single_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "single-pass generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        counter = self.single_pass_counter
        assert counter is not None
        turn_index = self._single_turns + 1
        count = counter.count_serialized_input(
            cognitive_input,
            pass_request=pass_request,
        )
        self._record(
            topology="single_pass",
            pass_id="single_pass",
            turn_index=turn_index,
            pass_request=expected,
            cognitive_input=cognitive_input,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._single_turns = turn_index
        output = await self.delegate.generate(
            cognitive_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitiveOutput):
            raise TypeError("provider generate must return CognitiveOutput")
        return output

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        expected = self.condition.pass_requests.pass1
        if self.condition.pass_requests.mode != "two_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "conversation generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        counter = self.two_pass_counter
        assert counter is not None
        if self._conversation_turns != self._extraction_turns:
            raise VLLMCapacityAcquisitionError(
                "next Pass 1 cannot start before the prior Pass 2 trajectory completes"
            )
        turn_index = self._conversation_turns + 1
        count = counter.count_conversation_input(
            cognitive_input,
            pass_request=pass_request,
        )
        self._record(
            topology="two_pass",
            pass_id="pass1",
            turn_index=turn_index,
            pass_request=expected,
            cognitive_input=cognitive_input,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._conversation_turns = turn_index
        output = await self.delegate.generate_conversation(
            cognitive_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitionConversationOutput):
            raise TypeError(
                "provider generate_conversation must return CognitionConversationOutput"
            )
        self._attach_completion_observation(output.completion)
        return output

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        expected = self.condition.pass_requests.pass2
        if self.condition.pass_requests.mode != "two_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "extraction generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        if self._conversation_turns != self._extraction_turns + 1:
            raise VLLMCapacityAcquisitionError(
                "Pass 2 measurement requires exactly one completed Pass 1"
            )
        counter = self.two_pass_counter
        assert counter is not None
        turn_index = self._extraction_turns + 1
        count = counter.count_extraction_input(
            extraction_input,
            pass_request=pass_request,
        )
        self._record(
            topology="two_pass",
            pass_id="pass2",
            turn_index=turn_index,
            pass_request=expected,
            cognitive_input=extraction_input.cognitive_input,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._extraction_turns = turn_index
        output = await self.delegate.generate_extraction(
            extraction_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitionExtractionOutput):
            raise TypeError(
                "provider generate_extraction must return CognitionExtractionOutput"
            )
        self._attach_completion_observation(output.completion)
        return output

    async def aclose(self) -> None:
        close = getattr(self.delegate, "aclose", None)
        if callable(close):
            await close()

    def _record(
        self,
        *,
        topology: str,
        pass_id: str,
        turn_index: int,
        pass_request: CognitionPassRequest,
        cognitive_input: CognitiveInput,
        total_input_tokens: int,
        required_input_framing_tokens: int,
        count_mode: TokenCountMode,
    ) -> None:
        self._observations.append(
            VLLMCapacityFootprintObservation(
                condition_id=self.condition.condition_id,
                topology=topology,
                pass_id=pass_id,
                scenario_id=self.scenario_id,
                turn_index=turn_index,
                pass_request_id=vllm_capacity_pass_request_id(pass_request),
                total_input_tokens=total_input_tokens,
                required_input_framing_tokens=required_input_framing_tokens,
                count_mode=count_mode,
                selected_layer_occupancy=_observe_selected_layer_occupancy(
                    cognitive_input
                ),
            )
        )

    def _attach_completion_observation(self, completion: object) -> None:
        if not self._observations:
            raise VLLMCapacityAcquisitionError(
                "completion observation cannot be attached before a footprint"
            )
        self._observations[-1] = replace(
            self._observations[-1],
            completion_observation=completion,
        )


def prepare_vllm_capacity_acquisition(
    *,
    plan: VLLMScreeningPlan,
    condition_id: str,
    proof_path: str | Path,
    repo_root: str | Path,
    snapshot_root: str | Path,
    relaylm_commit: str,
    base_url: str,
    api_key: str | None,
    model_runner: str | None = None,
    replicate_id: str = "0",
    fetch_json: FetchJSON | None = None,
    tokenize_post_json: PostJSON | None = None,
) -> PreparedVLLMCapacityAcquisition:
    """Prepare exact capacity acquisition without requiring prior capacity evidence.

    The selected screening plan contributes topology, scenarios, decoding, and
    pass semantics only. Its historical effective context window and optional
    capacity citation do not select the acquisition runtime. The live attested
    vLLM ``max_model_len`` is recorded as an observed runtime fact and bound to
    the provider/manifest/counter before any model request.
    """

    if not isinstance(plan, VLLMScreeningPlan):
        raise TypeError("plan must be VLLMScreeningPlan")
    if condition_id not in plan.conditions:
        raise VLLMCapacityAcquisitionError(
            f"unknown vLLM screening condition: {condition_id}"
        )
    try:
        resolved_model_runner = validate_vllm_model_runner(
            model_runner,
            label="capacity acquisition model_runner",
        )
    except (TypeError, ValueError, VLLMRuntimeCapacityEvidenceError) as exc:
        raise VLLMCapacityAcquisitionError(
            f"capacity acquisition requires an explicit model_runner identity: {exc}"
        ) from exc
    root = Path(repo_root).resolve()
    _verify_clean_exact_repo(root=root, expected_commit=relaylm_commit)
    condition = plan.conditions[condition_id]
    target = load_actual_model_repository_snapshot_target(
        root / CANONICAL_VLLM_TARGET_PATH
    )
    if target.target_id != plan.target_id:
        raise VLLMCapacityAcquisitionError(
            "screening target_id does not match the canonical frozen target"
        )
    try:
        snapshot_verification = verify_actual_model_repository_snapshot(
            target=target,
            snapshot_root=snapshot_root,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise VLLMCapacityAcquisitionError(
            f"cannot verify vLLM repository snapshot: {exc}"
        ) from exc
    proof = load_vllm_reasoning_probe_proof(proof_path)
    capability = acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url=base_url,
        api_key=api_key,
        fetch_json=fetch_json,
    )
    live_max_model_len = capability.backend_attestation.max_model_len
    if live_max_model_len is None or live_max_model_len <= 0:
        raise VLLMCapacityAcquisitionError(
            "live vLLM capacity acquisition requires a positive max_model_len"
        )
    scenario_set_path = (
        root / plan.scenario_set_path
        if plan.scenario_set_path is not None
        else root / CANONICAL_SCENARIO_SET_PATH
    )
    scenario_set = load_actual_model_scenario_set(scenario_set_path)
    if (
        plan.scenario_set_revision is not None
        and scenario_set.revision != plan.scenario_set_revision
    ):
        raise VLLMCapacityAcquisitionError(
            "capacity scenario-set revision does not match the execution template"
        )
    fixture_root = root / CANONICAL_FIXTURE_PATH
    fixture_revision = character_fixture_revision(fixture_root)
    _validate_scenarios(plan=plan, scenario_set=scenario_set)

    serving_counter = VLLMServingTokenizerCounter(
        base_url=base_url,
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=live_max_model_len,
        api_key=api_key,
        post_json=tokenize_post_json,
    )
    provider_type: type[OpenAICompatibleProvider] = OpenAICompatibleProvider
    if condition.cognition_execution.mode == "two_pass":
        provider_type = OpenAICompatibleTwoPassProvider
    provider = provider_type(
        base_url=base_url,
        model=capability.request_model,
        api_key=api_key,
        decoding_config=plan.decoding_config,
        decoding_capabilities=plan.decoding_capabilities,
        vllm_reasoning_capability=capability,
    )
    try:
        identity = describe_openai_compatible_provider(provider)
        manifest = ActualModelRunManifest(
            relaylm_commit=relaylm_commit,
            character_fixture_id=scenario_set.character_fixture_id,
            character_fixture_revision=fixture_revision,
            provider_identity=vllm_manifest_provider_identity(capability),
            adapter_identity=identity.adapter_identity,
            model_artifact=target.model_artifact_identity,
            tokenizer_identity=target.tokenizer_identity,
            effective_context_window=live_max_model_len,
            decoding_configuration=tuple(
                sorted(identity.effective_decoding_configuration.items())
            ),
            structured_output_schema_version=CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION,
            scenario_set_version=scenario_set.scenario_set_version,
            condition_id=condition.condition_id,
            budgets=ExplicitBudgetConfiguration(),
            continuity_runtime=plan.continuity_runtime,
            execution_path=plan.execution_path,
            restart_boundary="none",
            seed=plan.seed,
            provider_capabilities=identity.provider_capabilities,
            replicate_id=replicate_id,
            cognition_execution=condition.cognition_execution,
            cognition_pass_requests=condition.pass_requests,
        )
        bind_vllm_execution_condition(
            target=target,
            snapshot_verification=snapshot_verification,
            snapshot_root=snapshot_root,
            reasoning_capability=capability,
            provider=provider,
            manifest=manifest,
            configured_context_window=live_max_model_len,
        )
        if condition.pass_requests.mode == "single_pass":
            single_counter = OpenAICompatibleSerializedInputCounter(
                model=capability.request_model,
                count_input=serving_counter.count_input,
                decoding_config=plan.decoding_config,
                decoding_capabilities=plan.decoding_capabilities,
                vllm_reasoning_capability=capability,
                evidence_identity=serving_counter.evidence_identity,
            )
            two_counter = None
        elif condition.pass_requests.mode == "two_pass":
            single_counter = None
            two_counter = OpenAICompatibleTwoPassSerializedInputCounter(
                model=capability.request_model,
                count_input=serving_counter.count_input,
                decoding_config=plan.decoding_config,
                decoding_capabilities=plan.decoding_capabilities,
                vllm_reasoning_capability=capability,
                evidence_identity=serving_counter.evidence_identity,
            )
        else:
            raise VLLMCapacityAcquisitionError(
                "unsupported screening pass-request topology"
            )
    except Exception:
        _close_provider_best_effort(provider)
        raise

    return PreparedVLLMCapacityAcquisition(
        plan=plan,
        screening_condition_id=condition_id,
        condition=condition,
        target=target,
        snapshot_verification=snapshot_verification,
        reasoning_capability=capability,
        scenario_set=scenario_set,
        fixture_root=fixture_root,
        provider=provider,
        manifest=manifest,
        model_runner=resolved_model_runner,
        serving_counter=serving_counter,
        single_pass_counter=single_counter,
        two_pass_counter=two_counter,
        scenario_ids=plan.scenario_ids,
    )


async def execute_vllm_capacity_acquisition(
    *,
    prepared: PreparedVLLMCapacityAcquisition,
    workspace_root: str | Path,
    artifact_root: str | Path,
) -> VLLMCapacityAcquisitionArtifact:
    """Run one selected condition trajectory and persist only capacity evidence."""

    if not isinstance(prepared, PreparedVLLMCapacityAcquisition):
        raise TypeError("prepared must be PreparedVLLMCapacityAcquisition")
    workspace_base = Path(workspace_root)
    observations: list[VLLMCapacityFootprintObservation] = []
    try:
        for scenario_id in prepared.scenario_ids:
            measurement = VLLMCapacityMeasurementProvider(
                delegate=prepared.provider,
                condition=prepared.condition,
                scenario_id=scenario_id,
                single_pass_counter=prepared.single_pass_counter,
                two_pass_counter=prepared.two_pass_counter,
            )
            try:
                definition = prepared.scenario_set.scenario(scenario_id)
                await run_actual_model_fixture(
                    fixture_root=prepared.fixture_root,
                    workspace_root=(
                        workspace_base
                        / prepared.plan.screening_id
                        / prepared.screening_condition_id
                        / prepared.manifest.replicate_id
                        / "capacity-acquisition"
                        / scenario_id
                    ),
                    provider=measurement,
                    manifest=prepared.manifest,
                    scenario=definition.scenario,
                )
            except Exception as exc:
                observations.extend(measurement.observations)
                artifact = _persist_capacity_observations(
                    prepared=prepared,
                    observations=tuple(observations),
                    artifact_root=artifact_root,
                    complete=False,
                )
                raise VLLMCapacityAcquisitionFailure(
                    f"vLLM capacity acquisition stopped during {scenario_id}: {exc}",
                    artifact=artifact,
                ) from exc
            observations.extend(measurement.observations)

        evidence = _capacity_evidence(
            prepared=prepared,
            observations=tuple(observations),
        )
        try:
            validate_capacity_coverage(
                evidence=evidence,
                scenario_set_revision=prepared.scenario_set.revision,
                required_coverage=_required_capacity_coverage(
                    condition=prepared.condition,
                    scenario_set=prepared.scenario_set,
                    scenario_ids=prepared.scenario_ids,
                ),
            )
        except (TypeError, ValueError, VLLMRuntimeCapacityEvidenceError) as exc:
            artifact = _write_capacity_artifact(
                evidence=evidence,
                artifact_root=artifact_root,
                complete=False,
            )
            raise VLLMCapacityAcquisitionFailure(
                f"vLLM capacity acquisition coverage is incomplete: {exc}",
                artifact=artifact,
            ) from exc
        return _write_capacity_artifact(
            evidence=evidence,
            artifact_root=artifact_root,
            complete=True,
        )
    finally:
        await prepared.provider.aclose()


def _capacity_evidence(
    *,
    prepared: PreparedVLLMCapacityAcquisition,
    observations: tuple[VLLMCapacityFootprintObservation, ...],
) -> VLLMRuntimeCapacityEvidence:
    if not observations:
        raise VLLMCapacityAcquisitionError(
            "cannot persist capacity evidence before any exact footprint is observed"
        )
    live_max_model_len = prepared.reasoning_capability.backend_attestation.max_model_len
    assert live_max_model_len is not None
    return VLLMRuntimeCapacityEvidence(
        relaylm_commit=prepared.manifest.relaylm_commit,
        target_id=prepared.target.target_id,
        target_revision=prepared.target.revision,
        tokenizer_identity=prepared.target.tokenizer_identity,
        chat_template_identity=prepared.target.chat_template_identity,
        backend_version=prepared.reasoning_capability.backend_version,
        request_model=prepared.reasoning_capability.request_model,
        observed_max_model_len=live_max_model_len,
        scenario_set_revision=prepared.scenario_set.revision,
        counter_identity=prepared.serving_counter.evidence_identity,
        footprints=observations,
        model_runner=prepared.model_runner,
        failed_capacity=None,
    )


def _persist_capacity_observations(
    *,
    prepared: PreparedVLLMCapacityAcquisition,
    observations: tuple[VLLMCapacityFootprintObservation, ...],
    artifact_root: str | Path,
    complete: bool,
) -> VLLMCapacityAcquisitionArtifact | None:
    if not observations:
        return None
    evidence = _capacity_evidence(prepared=prepared, observations=observations)
    return _write_capacity_artifact(
        evidence=evidence,
        artifact_root=artifact_root,
        complete=complete,
    )


def _write_capacity_artifact(
    *,
    evidence: VLLMRuntimeCapacityEvidence,
    artifact_root: str | Path,
    complete: bool,
) -> VLLMCapacityAcquisitionArtifact:
    path = write_vllm_runtime_capacity_evidence(
        evidence=evidence,
        artifact_root=artifact_root,
    )
    return VLLMCapacityAcquisitionArtifact(
        evidence_id=evidence.evidence_id,
        artifact_path=str(path),
        footprint_count=len(evidence.footprints),
        maximum_observed_input_tokens=evidence.maximum_observed_input_tokens,
        complete=complete,
    )


def _observe_selected_layer_occupancy(
    cognitive_input: CognitiveInput,
) -> VLLMCapacitySelectedLayerOccupancy:
    """Observe owner-selected layers without rerunning any selection logic.

    ``compile_cognitive_input`` emits accepted continuity before working
    context, and marks working-context items with their user/assistant actor.
    The actor marker is therefore used only to classify the already-built
    projection; no candidate, memory, event, or context selector is rerun.
    Character occupancy follows the owner character-budget unit: ``len`` of
    each selected item content string.
    """

    if not isinstance(cognitive_input, CognitiveInput):
        raise TypeError("cognitive_input must be CognitiveInput")
    working_context = tuple(
        item
        for item in cognitive_input.context
        if item.actor in {"user", "assistant"}
    )
    return VLLMCapacitySelectedLayerOccupancy(
        canonical_state_item_count=len(cognitive_input.state),
        working_context_item_count=len(working_context),
        working_context_character_occupancy=sum(
            len(item.content) for item in working_context
        ),
        retrieved_memory_item_count=len(cognitive_input.memory),
        retrieved_memory_character_occupancy=sum(
            len(item.content) for item in cognitive_input.memory
        ),
        event_evidence_item_count=len(cognitive_input.event_evidence),
        event_evidence_character_occupancy=sum(
            len(item.content) for item in cognitive_input.event_evidence
        ),
    )


def _require_pass_request(
    *,
    pass_request: CognitionPassRequest | None,
    expected: CognitionPassRequest,
) -> None:
    if pass_request != expected:
        raise VLLMCapacityAcquisitionError(
            "provider pass request does not match selected screening pass request"
        )


def _close_provider_best_effort(provider: OpenAICompatibleProvider) -> None:
    try:
        client = getattr(provider, "_client", None)
        if client is not None and not getattr(client, "is_closed", True):
            try:
                import asyncio

                asyncio.run(provider.aclose())
            except RuntimeError:
                pass
    except Exception:
        pass
