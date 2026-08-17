from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from relaylm.cognitive import CognitiveInput, CognitiveOutput, CognitiveProvider
from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.state import StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    TurnResult,
    run_user_turn,
    run_user_turn_streaming,
)
from relaylm.validation import CandidateDecision

ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION = 1
ACTUAL_MODEL_SCENARIO_FORMAT_VERSION = 1
ExecutionPath = Literal["buffered", "streaming"]
RestartBoundary = Literal["none", "before_scenario"]
ScenarioFamily = Literal[
    "response_persona_continuity",
    "continuity_proposal_quality",
    "state_candidate_quality",
    "cognitive_pressure_robustness",
    "restart_quality",
]


@dataclass(frozen=True, slots=True)
class ExplicitBudgetConfiguration:
    """Caller-chosen layer budgets used as an evaluation condition, never defaults."""

    memory_max_chunks: int | None = None
    memory_max_chars: int | None = None
    event_max_events: int | None = None
    event_max_chars: int | None = None

    def __post_init__(self) -> None:
        _validate_optional_non_negative_int(self.memory_max_chunks, "memory_max_chunks")
        _validate_optional_non_negative_int(self.memory_max_chars, "memory_max_chars")
        _validate_optional_non_negative_int(self.event_max_events, "event_max_events")
        _validate_optional_non_negative_int(self.event_max_chars, "event_max_chars")
        if (self.memory_max_chunks is None) != (self.memory_max_chars is None):
            raise ValueError("memory budget count and character limit must be provided together")
        if (self.event_max_events is None) != (self.event_max_chars is None):
            raise ValueError("event budget count and character limit must be provided together")

    def to_mapping(self) -> dict[str, int | None]:
        return {
            "memory_max_chunks": self.memory_max_chunks,
            "memory_max_chars": self.memory_max_chars,
            "event_max_events": self.event_max_events,
            "event_max_chars": self.event_max_chars,
        }


@dataclass(frozen=True, slots=True)
class ExplicitContinuityRuntimeConfiguration:
    """Evaluation-owned identity for process-local Continuity Runtime settings."""

    max_items: int
    lifetime_revisions: int

    def __post_init__(self) -> None:
        _validate_positive_int(self.max_items, "continuity max_items")
        _validate_positive_int(
            self.lifetime_revisions,
            "continuity lifetime_revisions",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "max_items": self.max_items,
            "lifetime_revisions": self.lifetime_revisions,
            "persistence": "process_local_non_durable",
        }


@dataclass(frozen=True, slots=True)
class ActualModelRunManifest:
    """Reproducible identity for one actual-model scenario execution."""

    relaylm_commit: str
    character_fixture_id: str
    character_fixture_revision: str
    provider_identity: str
    adapter_identity: str
    model_artifact: str
    tokenizer_identity: str
    effective_context_window: int
    decoding_configuration: tuple[tuple[str, str | int | float | bool | None], ...]
    structured_output_schema_version: str
    scenario_set_version: str
    condition_id: str
    budgets: ExplicitBudgetConfiguration = field(default_factory=ExplicitBudgetConfiguration)
    continuity_runtime: ExplicitContinuityRuntimeConfiguration | None = None
    execution_path: ExecutionPath = "buffered"
    restart_boundary: RestartBoundary = "none"
    seed: int | None = None
    provider_capabilities: tuple[str, ...] = field(default_factory=tuple)
    replicate_id: str = "0"
    format_version: int = ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION:
            raise ValueError(f"unsupported actual-model format_version: {self.format_version}")
        if len(self.relaylm_commit) != 40 or any(
            char not in "0123456789abcdef" for char in self.relaylm_commit.casefold()
        ):
            raise ValueError("relaylm_commit must be an exact 40-character Git SHA")
        for name in (
            "character_fixture_id",
            "character_fixture_revision",
            "provider_identity",
            "adapter_identity",
            "model_artifact",
            "tokenizer_identity",
            "structured_output_schema_version",
            "scenario_set_version",
            "condition_id",
            "replicate_id",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if isinstance(self.effective_context_window, bool) or not isinstance(
            self.effective_context_window, int
        ):
            raise TypeError("effective_context_window must be an integer")
        if self.effective_context_window <= 0:
            raise ValueError("effective_context_window must be positive")
        if self.execution_path not in {"buffered", "streaming"}:
            raise ValueError(f"unsupported execution_path: {self.execution_path}")
        if self.restart_boundary not in {"none", "before_scenario"}:
            raise ValueError(f"unsupported restart_boundary: {self.restart_boundary}")
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise TypeError("seed must be an integer when provided")
        if len({key for key, _ in self.decoding_configuration}) != len(
            self.decoding_configuration
        ):
            raise ValueError("decoding_configuration keys must be unique")
        for key, value in self.decoding_configuration:
            if not isinstance(key, str) or not key.strip():
                raise ValueError("decoding_configuration keys must be non-empty strings")
            if isinstance(value, float) and (value != value or value in {float("inf"), -float("inf")}):
                raise ValueError("decoding_configuration values must be finite")
        if len(set(self.provider_capabilities)) != len(self.provider_capabilities):
            raise ValueError("provider_capabilities must not contain duplicates")
        if not all(item.strip() for item in self.provider_capabilities):
            raise ValueError("provider_capabilities must contain non-empty strings")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "relaylm_commit": self.relaylm_commit,
            "character_fixture": {
                "id": self.character_fixture_id,
                "revision": self.character_fixture_revision,
            },
            "provider": {
                "identity": self.provider_identity,
                "adapter": self.adapter_identity,
                "capabilities": list(self.provider_capabilities),
            },
            "model_artifact": self.model_artifact,
            "tokenizer_identity": self.tokenizer_identity,
            "effective_context_window": self.effective_context_window,
            "decoding_configuration": dict(self.decoding_configuration),
            "seed": self.seed,
            "structured_output_schema_version": self.structured_output_schema_version,
            "scenario_set_version": self.scenario_set_version,
            "condition_id": self.condition_id,
            "budgets": self.budgets.to_mapping(),
            "continuity_runtime": (
                self.continuity_runtime.to_mapping()
                if self.continuity_runtime is not None
                else None
            ),
            "execution_path": self.execution_path,
            "restart_boundary": self.restart_boundary,
            "replicate_id": self.replicate_id,
        }


@dataclass(frozen=True, slots=True)
class ActualModelScenario:
    """Provider-neutral semantic fixture; conditions belong in the run manifest."""

    scenario_id: str
    family: ScenarioFamily
    turns: tuple[str, ...]
    version: str
    format_version: int = ACTUAL_MODEL_SCENARIO_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_SCENARIO_FORMAT_VERSION:
            raise ValueError(f"unsupported scenario format_version: {self.format_version}")
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")
        if self.family not in {
            "response_persona_continuity",
            "continuity_proposal_quality",
            "state_candidate_quality",
            "cognitive_pressure_robustness",
            "restart_quality",
        }:
            raise ValueError(f"unsupported scenario family: {self.family}")
        if not self.version.strip():
            raise ValueError("scenario version must not be empty")
        if not self.turns or not all(isinstance(turn, str) and turn.strip() for turn in self.turns):
            raise ValueError("scenario turns must contain at least one non-empty turn")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "id": self.scenario_id,
            "family": self.family,
            "version": self.version,
            "turns": list(self.turns),
        }


@dataclass(frozen=True, slots=True)
class ProductQualityObservation:
    """Bounded human/product-quality annotation kept separate from runtime truth."""

    axis: str
    outcome: Literal["pass", "fail", "not_rated"]
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise ValueError("product-quality axis must not be empty")
        if self.outcome not in {"pass", "fail", "not_rated"}:
            raise ValueError(f"unsupported product-quality outcome: {self.outcome}")

    def to_mapping(self) -> dict[str, object]:
        return {"axis": self.axis, "outcome": self.outcome, "note": self.note}


@dataclass(frozen=True, slots=True)
class RawModelObservation:
    response: str
    state_candidates: tuple[dict[str, object], ...]
    continuity_candidates: tuple[dict[str, object], ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "response": self.response,
            "state_candidates": list(self.state_candidates),
            "continuity_candidates": list(self.continuity_candidates),
        }


@dataclass(frozen=True, slots=True)
class DeterministicRelayObservation:
    state_decisions: tuple[dict[str, object], ...]
    continuity_decisions: tuple[dict[str, object], ...]
    resulting_state: tuple[dict[str, object], ...]
    resulting_continuity: dict[str, object] | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "state_decisions": list(self.state_decisions),
            "continuity_decisions": list(self.continuity_decisions),
            "resulting_state": list(self.resulting_state),
            "resulting_continuity": self.resulting_continuity,
        }


@dataclass(frozen=True, slots=True)
class ActualModelTurnEvidence:
    turn_index: int
    input: str
    raw_model: RawModelObservation
    deterministic: DeterministicRelayObservation
    product_quality: tuple[ProductQualityObservation, ...] = field(default_factory=tuple)

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "input": self.input,
            "raw_model": self.raw_model.to_mapping(),
            "deterministic_relay": self.deterministic.to_mapping(),
            "product_quality": [item.to_mapping() for item in self.product_quality],
        }


@dataclass(frozen=True, slots=True)
class ActualModelEvidence:
    run_id: str
    manifest: ActualModelRunManifest
    scenario: ActualModelScenario
    turns: tuple[ActualModelTurnEvidence, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION,
            "run_id": self.run_id,
            "manifest": self.manifest.to_mapping(),
            "scenario": self.scenario.to_mapping(),
            "turns": [turn.to_mapping() for turn in self.turns],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)


class _RecordingProvider:
    def __init__(self, delegate: CognitiveProvider) -> None:
        self.delegate = delegate
        self.outputs: list[CognitiveOutput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        output = await self.delegate.generate(cognitive_input)
        self.outputs.append(output)
        return output

    async def stream_generate(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
    ) -> CognitiveOutput:
        stream_generate = getattr(self.delegate, "stream_generate", None)
        if stream_generate is None:
            raise TypeError("provider does not support cognitive streaming")
        output = await stream_generate(cognitive_input, emit_response_delta)
        self.outputs.append(output)
        return output


async def run_actual_model_scenario(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    manifest: ActualModelRunManifest,
    scenario: ActualModelScenario,
    continuity_runtime: ContinuityRuntime | None = None,
) -> ActualModelEvidence:
    """Execute a semantic fixture through the real ordinary-turn path.

    The harness records the raw CognitiveOutput before treating the TurnResult as
    deterministic RelayLM evidence. It never scores model quality itself and never
    adds another semantic model call.
    """

    recording_provider = _RecordingProvider(provider)
    evidence: list[ActualModelTurnEvidence] = []
    memory_budget = _memory_budget(manifest.budgets)
    event_budget = _event_budget(manifest.budgets)
    manifest, continuity_runtime = _materialize_continuity_runtime(
        manifest=manifest,
        runtime=continuity_runtime,
    )

    if manifest.restart_boundary == "before_scenario":
        character = CharacterDirectory(character.root)

    for turn_index, content in enumerate(scenario.turns, start=1):
        if manifest.execution_path == "buffered":
            result = await run_user_turn(
                character=character,
                provider=recording_provider,
                content=content,
                memory_budget=memory_budget,
                event_budget=event_budget,
                continuity_runtime=continuity_runtime,
            )
        else:
            result = await run_user_turn_streaming(
                character=character,
                provider=recording_provider,
                content=content,
                emit_response_delta=_discard_delta,
                memory_budget=memory_budget,
                event_budget=event_budget,
                continuity_runtime=continuity_runtime,
            )
        output = recording_provider.outputs[-1]
        evidence.append(
            ActualModelTurnEvidence(
                turn_index=turn_index,
                input=content,
                raw_model=_raw_observation(output),
                deterministic=_deterministic_observation(result),
            )
        )

    return ActualModelEvidence(
        run_id=stable_actual_model_run_id(manifest=manifest, scenario=scenario),
        manifest=manifest,
        scenario=scenario,
        turns=tuple(evidence),
    )


def stable_actual_model_run_id(
    *, manifest: ActualModelRunManifest, scenario: ActualModelScenario
) -> str:
    identity = {"manifest": manifest.to_mapping(), "scenario": scenario.to_mapping()}
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amr-{hashlib.sha256(payload).hexdigest()}"


async def _discard_delta(_: str) -> None:
    return None


def _memory_budget(config: ExplicitBudgetConfiguration) -> MemoryRetrievalBudget | None:
    if config.memory_max_chunks is None:
        return None
    assert config.memory_max_chars is not None
    return MemoryRetrievalBudget(
        max_chunks=config.memory_max_chunks,
        max_chars=config.memory_max_chars,
    )


def _event_budget(config: ExplicitBudgetConfiguration) -> EventRetrievalBudget | None:
    if config.event_max_events is None:
        return None
    assert config.event_max_chars is not None
    return EventRetrievalBudget(
        max_events=config.event_max_events,
        max_chars=config.event_max_chars,
    )


def _materialize_continuity_runtime(
    *,
    manifest: ActualModelRunManifest,
    runtime: ContinuityRuntime | None,
) -> tuple[ActualModelRunManifest, ContinuityRuntime | None]:
    declared = manifest.continuity_runtime
    if runtime is None:
        if declared is None:
            return manifest, None
        return (
            manifest,
            ContinuityRuntime(
                context=ContinuityContext(max_items=declared.max_items),
                lifetime_revisions=declared.lifetime_revisions,
            ),
        )

    if runtime.context.revision != 0 or runtime.context.items:
        raise ValueError(
            "actual-model Continuity Runtime must start from an empty revision-0 context"
        )
    observed = ExplicitContinuityRuntimeConfiguration(
        max_items=runtime.context.max_items,
        lifetime_revisions=runtime.lifetime_revisions,
    )
    if declared is None:
        return replace(manifest, continuity_runtime=observed), runtime
    if declared != observed:
        raise ValueError(
            "actual-model Continuity Runtime does not match the run manifest"
        )
    return manifest, runtime


def _raw_observation(output: CognitiveOutput) -> RawModelObservation:
    return RawModelObservation(
        response=output.response,
        state_candidates=tuple(_serialize_state_candidate(item) for item in output.state_candidates),
        continuity_candidates=tuple(
            _serialize_continuity_candidate(item) for item in output.continuity_candidates
        ),
    )


def _deterministic_observation(result: TurnResult) -> DeterministicRelayObservation:
    continuity_decisions: tuple[dict[str, object], ...] = ()
    resulting_continuity = None
    if result.continuity is not None:
        continuity_decisions = tuple(
            {
                "candidate": _serialize_continuity_candidate(item.candidate),
                "status": item.status,
                "action": item.action,
                "reason": item.reason,
            }
            for item in result.continuity.decisions
        )
        resulting_continuity = _serialize_continuity_context(result.continuity.context)
    return DeterministicRelayObservation(
        state_decisions=tuple(_serialize_state_decision(item) for item in result.decisions),
        continuity_decisions=continuity_decisions,
        resulting_state=tuple(_serialize_state_record(item) for item in result.state.states),
        resulting_continuity=resulting_continuity,
    )


def _serialize_state_decision(decision: CandidateDecision) -> dict[str, object]:
    return {
        "candidate": _serialize_state_candidate(decision.candidate),
        "status": decision.status,
        "action": decision.action,
        "reason": decision.reason,
    }


def _serialize_state_candidate(candidate: StateCandidate) -> dict[str, object]:
    result: dict[str, object] = {
        "state_class": candidate.state_class,
        "key": candidate.key,
        "op": candidate.op,
        "sources": list(candidate.sources),
    }
    if candidate.has_value:
        result["value"] = _thaw_json(candidate.value)
    return result


def _serialize_continuity_candidate(candidate: ContinuityCandidate) -> dict[str, object]:
    result: dict[str, object] = {
        "kind": candidate.kind,
        "key": candidate.key,
        "op": candidate.op,
        "sources": list(candidate.sources),
        "epistemic_role": candidate.epistemic_role,
    }
    if candidate.has_value:
        result["value"] = _thaw_json(candidate.value)
    return result


def _serialize_state_record(record: StateRecord) -> dict[str, object]:
    return {
        "state_id": record.state_id,
        "state_class": record.state_class,
        "key": record.key,
        "value": _thaw_json(record.value),
        "sources": list(record.sources),
        "status": record.status,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
    }


def _serialize_continuity_context(context: ContinuityContext) -> dict[str, object]:
    return {
        "max_items": context.max_items,
        "revision": context.revision,
        "items": [_serialize_continuity_item(item) for item in context.items],
    }


def _serialize_continuity_item(item: ContinuityItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "kind": item.kind,
        "key": item.key,
        "value": _thaw_json(item.value),
        "sources": list(item.sources),
        "epistemic_role": item.epistemic_role,
        "accepted_revision": item.accepted_revision,
        "expires_revision": item.expires_revision,
    }


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(nested) for nested in value]
    return value


def _validate_optional_non_negative_int(value: int | None, label: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer when provided")
    if value < 0:
        raise ValueError(f"{label} must not be negative")


def _validate_positive_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value <= 0:
        raise ValueError(f"{label} must be positive")
