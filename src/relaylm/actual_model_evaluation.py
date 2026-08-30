from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from relaylm.actual_model_cognitive_budget import (
    ActualModelBoundedBudgetFailureEvidence,
    ActualModelCognitiveBudgetDiagnostics,
    ExplicitCognitiveBudgetConfiguration,
    validate_cognitive_budget_runtime_identity,
)
from relaylm.actual_model_request_evidence import (
    ActualModelRequestEvidence,
    ActualModelRequestEvidenceRecorder,
    RequestPassIdentity,
    install_model_facing_request_capture,
)
from relaylm.budget_diagnostics import CognitiveBudgetExceededWithDiagnostics
from relaylm.budget_runtime import (
    CognitiveBudgetRuntimeConfig,
    TwoPassCognitiveBudgetRuntimeConfig,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput, CognitiveProvider
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.cognition_execution_evidence import (
    CognitionExecutionEvidenceIdentity,
    ShadowExtractionEvidence,
    ShadowExtractionStatus,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.shadow_turn import (
    run_user_turn_shadow_two_pass,
    run_user_turn_shadow_two_pass_streaming,
)
from relaylm.state import StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    TurnResult,
    run_user_turn,
    run_user_turn_streaming,
    run_user_turn_streaming_with_cognitive_budget_diagnostics,
    run_user_turn_with_cognitive_budget_diagnostics,
)
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionResult,
    run_user_turn_two_pass,
    run_user_turn_two_pass_streaming,
)
from relaylm.validation import CandidateDecision

ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION = 1
ACTUAL_MODEL_SCENARIO_FORMAT_VERSION = 1
ACTUAL_MODEL_COGNITION_PASS_REQUESTS_FORMAT_VERSION = 1
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
    """Caller-chosen legacy layer budgets used as an evaluation condition, never defaults."""

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
class ActualModelCognitionPassRequests:
    """Exact fully resolved per-pass requests participating in #1386 run identity."""

    single_request: CognitionPassRequest | None = None
    pass1: CognitionPassRequest | None = None
    pass2: CognitionPassRequest | None = None
    format_version: int = ACTUAL_MODEL_COGNITION_PASS_REQUESTS_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_COGNITION_PASS_REQUESTS_FORMAT_VERSION:
            raise ValueError(
                "unsupported actual-model cognition pass requests format_version: "
                f"{self.format_version}"
            )
        for name in ("single_request", "pass1", "pass2"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, CognitionPassRequest):
                raise TypeError(f"{name} must be CognitionPassRequest or None")
        single_shape = (
            self.single_request is not None
            and self.pass1 is None
            and self.pass2 is None
        )
        two_pass_shape = (
            self.single_request is None
            and self.pass1 is not None
            and self.pass2 is not None
        )
        if not (single_shape or two_pass_shape):
            raise ValueError(
                "cognition pass requests must contain exactly single_pass or both pass1 and pass2"
            )

    @classmethod
    def single_pass(cls, request: CognitionPassRequest) -> "ActualModelCognitionPassRequests":
        return cls(single_request=request)

    @classmethod
    def two_pass(
        cls,
        *,
        pass1: CognitionPassRequest,
        pass2: CognitionPassRequest,
    ) -> "ActualModelCognitionPassRequests":
        return cls(pass1=pass1, pass2=pass2)

    @property
    def mode(self) -> str:
        return "single_pass" if self.single_request is not None else "two_pass"

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "single_pass": (
                _cognition_pass_request_mapping(self.single_request)
                if self.single_request is not None
                else None
            ),
            "pass1": (
                _cognition_pass_request_mapping(self.pass1)
                if self.pass1 is not None
                else None
            ),
            "pass2": (
                _cognition_pass_request_mapping(self.pass2)
                if self.pass2 is not None
                else None
            ),
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
    cognitive_budget: ExplicitCognitiveBudgetConfiguration | None = None
    continuity_runtime: ExplicitContinuityRuntimeConfiguration | None = None
    execution_path: ExecutionPath = "buffered"
    restart_boundary: RestartBoundary = "none"
    seed: int | None = None
    provider_capabilities: tuple[str, ...] = field(default_factory=tuple)
    replicate_id: str = "0"
    cognition_execution: CognitionExecutionEvidenceIdentity | None = None
    cognition_pass_requests: ActualModelCognitionPassRequests | None = None
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
            if isinstance(value, float) and (
                value != value or value in {float("inf"), -float("inf")}
            ):
                raise ValueError("decoding_configuration values must be finite")
        if len(set(self.provider_capabilities)) != len(self.provider_capabilities):
            raise ValueError("provider_capabilities must not contain duplicates")
        if not all(item.strip() for item in self.provider_capabilities):
            raise ValueError("provider_capabilities must contain non-empty strings")
        if self.cognition_execution is not None and not isinstance(
            self.cognition_execution,
            CognitionExecutionEvidenceIdentity,
        ):
            raise TypeError(
                "cognition_execution must be CognitionExecutionEvidenceIdentity or None"
            )
        if self.cognitive_budget is not None:
            if not isinstance(
                self.cognitive_budget,
                ExplicitCognitiveBudgetConfiguration,
            ):
                raise TypeError(
                    "cognitive_budget must be ExplicitCognitiveBudgetConfiguration or None"
                )
            if self.budgets != ExplicitBudgetConfiguration():
                raise ValueError(
                    "cognitive_budget cannot be combined with legacy explicit MEMORY/Event budgets"
                )
            if not self.cognitive_budget.uses_context_window(
                self.effective_context_window
            ):
                raise ValueError(
                    "cognitive budget model_context_window must match effective_context_window"
                )
            if self.cognitive_budget.mode == "two_pass":
                if (
                    self.cognition_execution is None
                    or self.cognition_execution.mode != "two_pass"
                ):
                    raise ValueError(
                        "two-pass cognitive budget requires two_pass cognition execution"
                    )
            elif (
                self.cognition_execution is not None
                and self.cognition_execution.mode == "two_pass"
            ):
                raise ValueError(
                    "two_pass cognition execution requires two-pass cognitive budget identity"
                )
        if self.cognition_execution is not None:
            if self.cognition_execution.execution_path != self.execution_path:
                raise ValueError(
                    "cognition execution path must match manifest execution_path"
                )
        if self.cognition_pass_requests is not None:
            if not isinstance(
                self.cognition_pass_requests,
                ActualModelCognitionPassRequests,
            ):
                raise TypeError(
                    "cognition_pass_requests must be ActualModelCognitionPassRequests or None"
                )
            if self.cognition_execution is None:
                raise ValueError(
                    "cognition pass requests require explicit cognition_execution identity"
                )
            if (
                self.execution_path != "buffered"
                and self.cognition_execution.mode != "two_pass"
            ):
                raise ValueError(
                    "single-pass cognition pass request evidence currently requires buffered execution"
                )
            if self.cognition_execution.mode == "single_pass":
                if self.cognition_pass_requests.mode != "single_pass":
                    raise ValueError(
                        "single_pass cognition pass requests must contain only single_pass"
                    )
            elif self.cognition_execution.mode == "two_pass":
                if self.cognition_pass_requests.mode != "two_pass":
                    raise ValueError(
                        "two_pass cognition pass requests must contain pass1 and pass2"
                    )
            else:
                raise ValueError(
                    "shadow_two_pass cognition pass request evidence is not implemented"
                )

    def to_mapping(self) -> dict[str, object]:
        mapping: dict[str, object] = {
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
            "cognitive_budget": (
                self.cognitive_budget.to_mapping()
                if self.cognitive_budget is not None
                else None
            ),
            "continuity_runtime": (
                self.continuity_runtime.to_mapping()
                if self.continuity_runtime is not None
                else None
            ),
            "execution_path": self.execution_path,
            "restart_boundary": self.restart_boundary,
            "replicate_id": self.replicate_id,
        }
        if self.cognition_execution is not None:
            mapping["cognition_execution"] = self.cognition_execution.to_mapping()
        if self.cognition_pass_requests is not None:
            mapping["cognition_pass_requests"] = self.cognition_pass_requests.to_mapping()
        return mapping


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
            raise ValueError(f"unsupported actual-model format_version: {self.format_version}")
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
        if not self.turns or not all(
            isinstance(turn, str) and turn.strip() for turn in self.turns
        ):
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
class RawStructuredModelObservation:
    """Raw structured proposal output from canonical or shadow Pass 2."""

    state_candidates: tuple[dict[str, object], ...]
    continuity_candidates: tuple[dict[str, object], ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "state_candidates": list(self.state_candidates),
            "continuity_candidates": list(self.continuity_candidates),
        }


@dataclass(frozen=True, slots=True)
class ActualModelCognitionExecutionObservation:
    """Per-turn execution-policy observation kept separate from RelayLM decisions."""

    mode: str
    pass2_status: str | None = None
    pass2_failure_reason: str | None = None
    pass2_raw: RawStructuredModelObservation | None = None
    shadow_status: str | None = None
    shadow_failure_reason: str | None = None
    shadow_raw: RawStructuredModelObservation | None = None

    def __post_init__(self) -> None:
        if self.mode == "two_pass":
            if self.pass2_status not in {"committed", "stale", "failed"}:
                raise ValueError("two_pass observation requires a valid pass2_status")
            if self.shadow_status is not None or self.shadow_raw is not None:
                raise ValueError("two_pass observation must not carry shadow fields")
            if self.shadow_failure_reason is not None:
                raise ValueError("two_pass observation must not carry shadow failure")
            if self.pass2_status == "failed":
                if self.pass2_failure_reason is None:
                    raise ValueError("failed Pass 2 observation requires failure reason")
            elif self.pass2_failure_reason is not None:
                raise ValueError("non-failed Pass 2 observation cannot carry failure reason")
            return
        if self.mode == "shadow_two_pass":
            if self.shadow_status not in {"completed", "failed"}:
                raise ValueError("shadow observation requires a valid shadow_status")
            if self.pass2_status is not None or self.pass2_raw is not None:
                raise ValueError("shadow observation must not carry canonical Pass 2 fields")
            if self.pass2_failure_reason is not None:
                raise ValueError("shadow observation must not carry Pass 2 failure")
            if self.shadow_status == "completed":
                if self.shadow_raw is None:
                    raise ValueError("completed shadow observation requires raw output")
                if self.shadow_failure_reason is not None:
                    raise ValueError("completed shadow observation cannot carry failure")
            else:
                if self.shadow_raw is not None:
                    raise ValueError("failed shadow observation cannot carry raw output")
                if self.shadow_failure_reason is None:
                    raise ValueError("failed shadow observation requires failure reason")
            return
        raise ValueError(f"unsupported cognition execution observation mode: {self.mode}")

    def to_mapping(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "pass2_status": self.pass2_status,
            "pass2_failure_reason": self.pass2_failure_reason,
            "pass2_raw": self.pass2_raw.to_mapping() if self.pass2_raw is not None else None,
            "shadow_status": self.shadow_status,
            "shadow_failure_reason": self.shadow_failure_reason,
            "shadow_raw": self.shadow_raw.to_mapping() if self.shadow_raw is not None else None,
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
    cognitive_budget: ActualModelCognitiveBudgetDiagnostics | None = None
    cognition_execution: ActualModelCognitionExecutionObservation | None = None
    request_evidence: tuple[ActualModelRequestEvidence, ...] = field(default_factory=tuple)

    def to_mapping(self) -> dict[str, object]:
        mapping: dict[str, object] = {
            "turn_index": self.turn_index,
            "input": self.input,
            "raw_model": self.raw_model.to_mapping(),
            "deterministic_relay": self.deterministic.to_mapping(),
            "product_quality": [item.to_mapping() for item in self.product_quality],
            "cognitive_budget": (
                self.cognitive_budget.to_mapping()
                if self.cognitive_budget is not None
                else None
            ),
        }
        if self.cognition_execution is not None:
            mapping["cognition_execution"] = self.cognition_execution.to_mapping()
        if self.request_evidence:
            mapping["request_evidence"] = [
                item.to_mapping() for item in self.request_evidence
            ]
        return mapping


@dataclass(frozen=True, slots=True)
class ActualModelRequestAttemptFailureEvidence:
    """A request crossed transport but produced no usable provider completion."""

    turn_index: int
    input: str
    pass_identity: RequestPassIdentity
    request_evidence: tuple[ActualModelRequestEvidence, ...]

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("request failure turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("request failure turn_index must be positive")
        if not isinstance(self.input, str) or not self.input.strip():
            raise ValueError("request failure input must be non-empty")
        if self.pass_identity not in {"single_pass", "pass1", "pass2"}:
            raise ValueError("request failure pass_identity is unsupported")
        if not self.request_evidence:
            raise ValueError("request failure requires attempted request evidence")
        if any(
            not isinstance(item, ActualModelRequestEvidence)
            for item in self.request_evidence
        ):
            raise TypeError(
                "request failure evidence must contain ActualModelRequestEvidence"
            )
        if any(item.turn_index != self.turn_index for item in self.request_evidence):
            raise ValueError("request failure request evidence does not match turn")
        if not any(
            item.pass_identity == self.pass_identity for item in self.request_evidence
        ):
            raise ValueError("request failure has no evidence for failing pass")

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "input": self.input,
            "pass": self.pass_identity,
            "request_evidence": [item.to_mapping() for item in self.request_evidence],
        }


@dataclass(frozen=True, slots=True)
class ActualModelEvidence:
    run_id: str
    manifest: ActualModelRunManifest
    scenario: ActualModelScenario
    turns: tuple[ActualModelTurnEvidence, ...]
    bounded_failure: ActualModelBoundedBudgetFailureEvidence | None = None
    request_failure: ActualModelRequestAttemptFailureEvidence | None = None

    def to_mapping(self) -> dict[str, object]:
        mapping: dict[str, object] = {
            "format_version": ACTUAL_MODEL_EVIDENCE_FORMAT_VERSION,
            "run_id": self.run_id,
            "manifest": self.manifest.to_mapping(),
            "scenario": self.scenario.to_mapping(),
            "turns": [turn.to_mapping() for turn in self.turns],
            "bounded_failure": (
                self.bounded_failure.to_mapping()
                if self.bounded_failure is not None
                else None
            ),
        }
        if self.request_failure is not None:
            mapping["request_failure"] = self.request_failure.to_mapping()
        return mapping

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


class _RecordingProvider:
    def __init__(
        self,
        delegate: CognitiveProvider,
        *,
        request_evidence: ActualModelRequestEvidenceRecorder | None = None,
    ) -> None:
        self.delegate = delegate
        install_model_facing_request_capture(delegate)
        self.outputs: list[CognitiveOutput] = []
        self.conversation_outputs: list[CognitionConversationOutput] = []
        self.extraction_outputs: list[CognitionExtractionOutput] = []
        self.request_evidence = request_evidence
        self.turn_index: int | None = None
        self.last_pass_identity: RequestPassIdentity | None = None
        self.last_request_attempt_failed = False

    def set_turn_index(self, turn_index: int) -> None:
        self.turn_index = turn_index

    @contextmanager
    def _request_scope(self, pass_identity: RequestPassIdentity):
        self.last_pass_identity = pass_identity
        self.last_request_attempt_failed = False
        capture = (
            nullcontext()
            if self.request_evidence is None or self.turn_index is None
            else self.request_evidence.capture(
                turn_index=self.turn_index,
                pass_identity=pass_identity,
            )
        )
        try:
            with capture:
                yield
        except Exception:
            self.last_request_attempt_failed = True
            raise

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        with self._request_scope("single_pass"):
            if pass_request is None:
                output = await self.delegate.generate(cognitive_input)
            else:
                output = await self.delegate.generate(
                    cognitive_input,
                    pass_request=pass_request,
                )
            if not isinstance(output, CognitiveOutput):
                raise TypeError("provider generate must return CognitiveOutput")
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
        with self._request_scope("single_pass"):
            output = await stream_generate(cognitive_input, emit_response_delta)
            if not isinstance(output, CognitiveOutput):
                raise TypeError("provider stream_generate must return CognitiveOutput")
        self.outputs.append(output)
        return output

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        generate_conversation = getattr(self.delegate, "generate_conversation", None)
        if not callable(generate_conversation):
            raise TypeError("provider does not support two-pass conversation generation")
        with self._request_scope("pass1"):
            if pass_request is None:
                output = await generate_conversation(cognitive_input)
            else:
                output = await generate_conversation(
                    cognitive_input,
                    pass_request=pass_request,
                )
            if not isinstance(output, CognitionConversationOutput):
                raise TypeError(
                    "provider generate_conversation must return CognitionConversationOutput"
                )
        self.conversation_outputs.append(output)
        return output

    async def stream_generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        stream_generate_conversation = getattr(
            self.delegate,
            "stream_generate_conversation",
            None,
        )
        if not callable(stream_generate_conversation):
            raise TypeError("provider does not support two-pass conversation streaming")
        with self._request_scope("pass1"):
            if pass_request is None:
                output = await stream_generate_conversation(
                    cognitive_input,
                    emit_response_delta,
                )
            else:
                output = await stream_generate_conversation(
                    cognitive_input,
                    emit_response_delta,
                    pass_request=pass_request,
                )
            if not isinstance(output, CognitionConversationOutput):
                raise TypeError(
                    "provider stream_generate_conversation must return CognitionConversationOutput"
                )
        self.conversation_outputs.append(output)
        return output

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        generate_extraction = getattr(self.delegate, "generate_extraction", None)
        if not callable(generate_extraction):
            raise TypeError("provider does not support structured extraction")
        with self._request_scope("pass2"):
            if pass_request is None:
                output = await generate_extraction(extraction_input)
            else:
                output = await generate_extraction(
                    extraction_input,
                    pass_request=pass_request,
                )
            if not isinstance(output, CognitionExtractionOutput):
                raise TypeError("provider generate_extraction must return CognitionExtractionOutput")
        self.extraction_outputs.append(output)
        return output


async def run_actual_model_scenario(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    manifest: ActualModelRunManifest,
    scenario: ActualModelScenario,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | TwoPassCognitiveBudgetRuntimeConfig | None = None,
    execution_id: str | None = None,
    scenario_revision: str | None = None,
) -> ActualModelEvidence:
    """Execute a semantic fixture through the resolved real ordinary-turn path.

    Historical manifests without cognition-execution identity preserve the original
    single-pass harness exactly. New execution-policy evidence dispatches through
    the corresponding COGP runtime while keeping raw model proposals separate from
    deterministic RelayLM authority.
    """

    validate_cognitive_budget_runtime_identity(
        declared=manifest.cognitive_budget,
        runtime=cognitive_budget,
        effective_context_window=manifest.effective_context_window,
    )
    execution_mode = _execution_mode(manifest)
    pass_requests = manifest.cognition_pass_requests
    if execution_mode == "shadow_two_pass" and cognitive_budget is not None:
        raise ValueError(
            "shadow two-pass cognition execution does not expose #1386 total "
            "cognitive-budget diagnostics"
        )

    evidence: list[ActualModelTurnEvidence] = []
    bounded_failure: ActualModelBoundedBudgetFailureEvidence | None = None
    request_failure: ActualModelRequestAttemptFailureEvidence | None = None
    memory_budget = None if cognitive_budget is not None else _memory_budget(manifest.budgets)
    event_budget = None if cognitive_budget is not None else _event_budget(manifest.budgets)
    manifest, continuity_runtime = _materialize_continuity_runtime(
        manifest=manifest,
        runtime=continuity_runtime,
    )
    run_id = stable_actual_model_run_id(manifest=manifest, scenario=scenario)
    request_recorder = ActualModelRequestEvidenceRecorder(
        execution_id=(
            execution_id
            if execution_id is not None
            else _fallback_request_execution_id(run_id)
        ),
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        scenario_revision=(
            scenario_revision if scenario_revision is not None else scenario.version
        ),
        provider_identity=manifest.provider_identity,
        adapter_identity=manifest.adapter_identity,
    )
    recording_provider = _RecordingProvider(
        provider,
        request_evidence=request_recorder,
    )
    two_pass_runtime = CognitionExecutionRuntime() if execution_mode == "two_pass" else None

    if manifest.restart_boundary == "before_scenario":
        character = CharacterDirectory(character.root)

    for turn_index, content in enumerate(scenario.turns, start=1):
        recording_provider.set_turn_index(turn_index)
        budget_observation: ActualModelCognitiveBudgetDiagnostics | None = None
        execution_observation: ActualModelCognitionExecutionObservation | None = None
        extraction_output_count = len(recording_provider.extraction_outputs)
        try:
            if execution_mode == "two_pass":
                assert two_pass_runtime is not None
                pass1_request = pass_requests.pass1 if pass_requests is not None else None
                pass2_request = pass_requests.pass2 if pass_requests is not None else None
                two_pass_budget = (
                    cognitive_budget
                    if isinstance(cognitive_budget, TwoPassCognitiveBudgetRuntimeConfig)
                    else None
                )
                if manifest.execution_path == "buffered":
                    two_pass = await run_user_turn_two_pass(
                        character=character,
                        provider=recording_provider,
                        content=content,
                        execution_runtime=two_pass_runtime,
                        memory_budget=memory_budget,
                        event_budget=event_budget,
                        continuity_runtime=continuity_runtime,
                        cognitive_budget=two_pass_budget,
                        pass1_request=pass1_request,
                        pass2_request=pass2_request,
                    )
                else:
                    two_pass = await run_user_turn_two_pass_streaming(
                        character=character,
                        provider=recording_provider,
                        content=content,
                        emit_response_delta=_discard_delta,
                        execution_runtime=two_pass_runtime,
                        memory_budget=memory_budget,
                        event_budget=event_budget,
                        continuity_runtime=continuity_runtime,
                        cognitive_budget=two_pass_budget,
                        pass1_request=pass1_request,
                        pass2_request=pass2_request,
                    )
                extraction = await two_pass.extraction
                extraction_output = (
                    recording_provider.extraction_outputs[-1]
                    if len(recording_provider.extraction_outputs) > extraction_output_count
                    else None
                )
                raw_model = _raw_two_pass_observation(
                    response=two_pass.response,
                    output=extraction_output,
                )
                deterministic = _deterministic_two_pass_observation(
                    extraction,
                    continuity_runtime=continuity_runtime,
                )
                execution_observation = _two_pass_execution_observation(
                    extraction=extraction,
                    output=extraction_output,
                )
            elif execution_mode == "shadow_two_pass":
                if manifest.execution_path == "buffered":
                    shadow_turn = await run_user_turn_shadow_two_pass(
                        character=character,
                        provider=recording_provider,
                        content=content,
                        memory_budget=memory_budget,
                        event_budget=event_budget,
                        continuity_runtime=continuity_runtime,
                    )
                else:
                    shadow_turn = await run_user_turn_shadow_two_pass_streaming(
                        character=character,
                        provider=recording_provider,
                        content=content,
                        emit_response_delta=_discard_delta,
                        memory_budget=memory_budget,
                        event_budget=event_budget,
                        continuity_runtime=continuity_runtime,
                    )
                shadow = await shadow_turn.shadow
                output = recording_provider.outputs[-1]
                raw_model = _raw_observation(output)
                deterministic = _deterministic_observation(shadow_turn.turn)
                execution_observation = _shadow_execution_observation(shadow)
            else:
                single_pass_request = (
                    pass_requests.single_request if pass_requests is not None else None
                )
                if cognitive_budget is None:
                    if manifest.execution_path == "buffered":
                        result = await run_user_turn(
                            character=character,
                            provider=recording_provider,
                            content=content,
                            memory_budget=memory_budget,
                            event_budget=event_budget,
                            continuity_runtime=continuity_runtime,
                            pass_request=single_pass_request,
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
                else:
                    if not isinstance(cognitive_budget, CognitiveBudgetRuntimeConfig):
                        raise TypeError(
                            "single-pass actual-model execution requires "
                            "CognitiveBudgetRuntimeConfig"
                        )
                    if manifest.execution_path == "buffered":
                        budgeted = await run_user_turn_with_cognitive_budget_diagnostics(
                            character=character,
                            provider=recording_provider,
                            content=content,
                            cognitive_budget=cognitive_budget,
                            continuity_runtime=continuity_runtime,
                        )
                    else:
                        budgeted = (
                            await run_user_turn_streaming_with_cognitive_budget_diagnostics(
                                character=character,
                                provider=recording_provider,
                                content=content,
                                emit_response_delta=_discard_delta,
                                cognitive_budget=cognitive_budget,
                                continuity_runtime=continuity_runtime,
                            )
                        )
                    result = budgeted.turn
                    budget_observation = ActualModelCognitiveBudgetDiagnostics.from_runtime(
                        budgeted.cognitive_budget
                    )
                output = recording_provider.outputs[-1]
                raw_model = _raw_observation(output)
                deterministic = _deterministic_observation(result)
        except CognitiveBudgetExceededWithDiagnostics as failure:
            if cognitive_budget is None:
                raise
            bounded_failure = ActualModelBoundedBudgetFailureEvidence(
                turn_index=turn_index,
                input=content,
                cognitive_budget=ActualModelCognitiveBudgetDiagnostics.from_runtime(
                    failure.diagnostics
                ),
            )
            break
        except Exception:
            request_evidence = request_recorder.records_for_turn(turn_index)
            if (
                not request_evidence
                or recording_provider.last_pass_identity is None
                or not recording_provider.last_request_attempt_failed
            ):
                raise
            request_failure = ActualModelRequestAttemptFailureEvidence(
                turn_index=turn_index,
                input=content,
                pass_identity=recording_provider.last_pass_identity,
                request_evidence=request_evidence,
            )
            break

        request_evidence = request_recorder.records_for_turn(turn_index)
        evidence.append(
            ActualModelTurnEvidence(
                turn_index=turn_index,
                input=content,
                raw_model=raw_model,
                deterministic=deterministic,
                cognitive_budget=budget_observation,
                cognition_execution=execution_observation,
                request_evidence=request_evidence,
            )
        )

    return ActualModelEvidence(
        run_id=run_id,
        manifest=manifest,
        scenario=scenario,
        turns=tuple(evidence),
        bounded_failure=bounded_failure,
        request_failure=request_failure,
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


def _fallback_request_execution_id(run_id: str) -> str:
    """Give direct scenario callers a stable binding until an execution plan exists."""

    if run_id.startswith("amr-"):
        return "amx-" + run_id[4:]
    return "amx-" + hashlib.sha256(run_id.encode("utf-8")).hexdigest()


def _execution_mode(manifest: ActualModelRunManifest) -> str:
    if manifest.cognition_execution is None:
        return "single_pass"
    return manifest.cognition_execution.mode


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
        state_candidates=tuple(
            _serialize_state_candidate(item) for item in output.state_candidates
        ),
        continuity_candidates=tuple(
            _serialize_continuity_candidate(item) for item in output.continuity_candidates
        ),
    )


def _raw_structured_observation(
    output: CognitionExtractionOutput,
) -> RawStructuredModelObservation:
    return RawStructuredModelObservation(
        state_candidates=tuple(
            _serialize_state_candidate(item) for item in output.state_candidates
        ),
        continuity_candidates=tuple(
            _serialize_continuity_candidate(item) for item in output.continuity_candidates
        ),
    )


def _raw_two_pass_observation(
    *,
    response: str,
    output: CognitionExtractionOutput | None,
) -> RawModelObservation:
    if output is None:
        return RawModelObservation(
            response=response,
            state_candidates=(),
            continuity_candidates=(),
        )
    raw = _raw_structured_observation(output)
    return RawModelObservation(
        response=response,
        state_candidates=raw.state_candidates,
        continuity_candidates=raw.continuity_candidates,
    )


def _two_pass_execution_observation(
    *,
    extraction: TwoPassExtractionResult,
    output: CognitionExtractionOutput | None,
) -> ActualModelCognitionExecutionObservation:
    return ActualModelCognitionExecutionObservation(
        mode="two_pass",
        pass2_status=extraction.status.value,
        pass2_failure_reason=extraction.failure_reason,
        pass2_raw=(
            _raw_structured_observation(output) if output is not None else None
        ),
    )


def _shadow_execution_observation(
    shadow: ShadowExtractionEvidence,
) -> ActualModelCognitionExecutionObservation:
    return ActualModelCognitionExecutionObservation(
        mode="shadow_two_pass",
        shadow_status=shadow.status.value,
        shadow_failure_reason=shadow.failure_reason,
        shadow_raw=(
            _raw_structured_observation(shadow.output)
            if shadow.status is ShadowExtractionStatus.COMPLETED
            and shadow.output is not None
            else None
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
        state_decisions=tuple(
            _serialize_state_decision(item) for item in result.decisions
        ),
        continuity_decisions=continuity_decisions,
        resulting_state=tuple(
            _serialize_state_record(item) for item in result.state.states
        ),
        resulting_continuity=resulting_continuity,
    )


def _deterministic_two_pass_observation(
    extraction: TwoPassExtractionResult,
    *,
    continuity_runtime: ContinuityRuntime | None,
) -> DeterministicRelayObservation:
    continuity_decisions: tuple[dict[str, object], ...] = ()
    resulting_continuity = None
    if extraction.continuity is not None:
        continuity_decisions = tuple(
            {
                "candidate": _serialize_continuity_candidate(item.candidate),
                "status": item.status,
                "action": item.action,
                "reason": item.reason,
            }
            for item in extraction.continuity.decisions
        )
        resulting_continuity = _serialize_continuity_context(
            extraction.continuity.context
        )
    elif continuity_runtime is not None:
        resulting_continuity = _serialize_continuity_context(
            continuity_runtime.context
        )
    return DeterministicRelayObservation(
        state_decisions=tuple(
            _serialize_state_decision(item) for item in extraction.decisions
        ),
        continuity_decisions=continuity_decisions,
        resulting_state=tuple(
            _serialize_state_record(item) for item in extraction.state.states
        ),
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


def _cognition_pass_request_mapping(request: CognitionPassRequest) -> dict[str, object]:
    return {
        "reasoning_mode": (
            request.reasoning_mode.value if request.reasoning_mode is not None else None
        ),
        "reasoning_budget": request.reasoning_budget,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_output_tokens": request.max_output_tokens,
        "structured_output_mode": (
            request.structured_output_mode.value
            if request.structured_output_mode is not None
            else None
        ),
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
