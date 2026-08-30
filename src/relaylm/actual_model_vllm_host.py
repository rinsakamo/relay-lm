from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_cognitive_budget import ExplicitCognitiveBudgetConfiguration
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioSet,
    load_actual_model_scenario_set,
)
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotTarget,
    ActualModelRepositorySnapshotVerification,
    load_actual_model_repository_snapshot_target,
    verify_actual_model_repository_snapshot,
)
from relaylm.actual_model_vllm import (
    ActualModelVLLMExecutionBinding,
    bind_vllm_execution_condition,
    run_bound_vllm_actual_model_scenario_definition,
    vllm_manifest_provider_identity,
    write_vllm_actual_model_execution_result,
)
from relaylm.actual_model_vllm_capacity import (
    VLLMCapacityFootprintCoverage,
    VLLMRuntimeCapacityEvidence,
    VLLMRuntimeCapacityEvidenceError,
    capacity_evidence_path,
    load_vllm_runtime_capacity_evidence,
    validate_capacity_coverage,
    validate_capacity_window,
    validate_vllm_model_runner,
    vllm_capacity_pass_request_id,
)
from relaylm.actual_model_vllm_counter import VLLMServingTokenizerCounter
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.cognition_execution_evidence import CognitionExecutionEvidenceIdentity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleTwoPassSerializedInputCounter,
    SerializedInputCounterIdentity,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)


HISTORICAL_VLLM_SCREENING_PLAN_FORMAT_VERSION = 1
VLLM_SCREENING_PLAN_FORMAT_VERSION = 2
VLLM_REASONING_PROBE_PROOF_FORMAT_VERSION = 1
CANONICAL_VLLM_TARGET_PATH = Path(
    "evaluation/actual_model/targets/"
    "gemma-4-12b-it-qat-w4a16-google-vllm-v1.json"
)
CANONICAL_VLLM_HISTORICAL_SCREENING_PLAN_PATH = Path(
    "evaluation/actual_model/screenings/cogp5-vllm-screening-v1.json"
)
CANONICAL_VLLM_SCREENING_PLAN_PATH = Path(
    "evaluation/actual_model/screenings/stage-r0-vllm-reference-v2.json"
)
CANONICAL_VLLM_REASONING_PROOF_PATH = Path(
    "evaluation/actual_model/attestations/"
    "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1.json"
)
CANONICAL_VLLM_CAPACITY_EVIDENCE_ROOT = Path("evaluation/actual_model/capacity")
CANONICAL_SCENARIO_SET_PATH = Path(
    "evaluation/actual_model/scenario_sets/foundation-v2.json"
)
CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION = "relaylm-cognitive-output-v1"
HISTORICAL_VLLM_SCREENING_CONDITION_IDS = ("A", "B", "C")
CURRENT_VLLM_SCREENING_CONDITION_IDS = (
    "reference_baseline",
    "pass2_reasoning_escalation",
)
VLLM_REASONING_PROOF_SOURCE_ISSUE = 1545
VLLM_REASONING_PROOF_SOURCE_COMMENT = 5357159619
VLLM_REASONING_PROOF_SOURCE_COMMENTS = frozenset(
    {
        VLLM_REASONING_PROOF_SOURCE_COMMENT,
        5357427205,
    }
)

FetchJSON = Callable[[str, str | None], object]


class ActualModelVLLMHostError(ValueError):
    """A canonical vLLM screening condition cannot be executed truthfully."""


@dataclass(frozen=True, slots=True)
class VLLMScreeningCondition:
    condition_id: str
    cognition_execution: CognitionExecutionEvidenceIdentity
    pass_requests: ActualModelCognitionPassRequests

    def __post_init__(self) -> None:
        if not isinstance(self.condition_id, str) or not self.condition_id.strip():
            raise ActualModelVLLMHostError("condition_id must be a non-empty string")
        if not isinstance(self.cognition_execution, CognitionExecutionEvidenceIdentity):
            raise TypeError("cognition_execution must be CognitionExecutionEvidenceIdentity")
        if not isinstance(self.pass_requests, ActualModelCognitionPassRequests):
            raise TypeError("pass_requests must be ActualModelCognitionPassRequests")
        if self.cognition_execution.mode != self.pass_requests.mode:
            raise ActualModelVLLMHostError(
                "screening cognition execution mode must match pass-request shape"
            )
        if self.cognition_execution.execution_path != "buffered":
            raise ActualModelVLLMHostError(
                "vLLM screening currently supports buffered execution only"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "condition_id": self.condition_id,
            "cognition_execution": self.cognition_execution.mode,
            "pass_requests": self.pass_requests.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class VLLMScreeningPlan:
    screening_id: str
    target_id: str
    effective_context_window: int
    temperature: int | float | None
    top_p: int | float | None
    seed: int | None
    supported_decoding_controls: tuple[str, ...]
    execution_path: str
    continuity_runtime: ExplicitContinuityRuntimeConfiguration
    scenario_ids: tuple[str, ...]
    conditions: dict[str, VLLMScreeningCondition]
    scenario_set_path: str | None = None
    scenario_set_revision: str | None = None
    capacity_evidence_id: str | None = None
    format_version: int = VLLM_SCREENING_PLAN_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version == HISTORICAL_VLLM_SCREENING_PLAN_FORMAT_VERSION:
            expected_conditions = HISTORICAL_VLLM_SCREENING_CONDITION_IDS
        elif self.format_version == VLLM_SCREENING_PLAN_FORMAT_VERSION:
            expected_conditions = CURRENT_VLLM_SCREENING_CONDITION_IDS
        else:
            raise ActualModelVLLMHostError(
                f"unsupported vLLM screening plan format_version: {self.format_version}"
            )
        for name in ("screening_id", "target_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelVLLMHostError(f"{name} must be a non-empty string")
        if (self.scenario_set_path is None) != (self.scenario_set_revision is None):
            raise ActualModelVLLMHostError(
                "scenario_set_path and scenario_set_revision must be supplied together"
            )
        if self.scenario_set_path is not None:
            if not isinstance(self.scenario_set_path, str) or not self.scenario_set_path.strip():
                raise ActualModelVLLMHostError(
                    "scenario_set_path must be a non-empty string or null"
                )
            scenario_path = Path(self.scenario_set_path)
            if scenario_path.is_absolute() or ".." in scenario_path.parts:
                raise ActualModelVLLMHostError(
                    "scenario_set_path must be repository-relative"
                )
            assert self.scenario_set_revision is not None
            if (
                not isinstance(self.scenario_set_revision, str)
                or not self.scenario_set_revision.startswith("sha256:")
                or len(self.scenario_set_revision) != 71
            ):
                raise ActualModelVLLMHostError(
                    "scenario_set_revision must be a sha256 revision or null"
                )
        if self.capacity_evidence_id is not None and (
            not isinstance(self.capacity_evidence_id, str)
            or not self.capacity_evidence_id.strip()
        ):
            raise ActualModelVLLMHostError(
                "capacity_evidence_id must be a non-empty string or null"
            )
        if isinstance(self.effective_context_window, bool) or not isinstance(
            self.effective_context_window, int
        ):
            raise ActualModelVLLMHostError(
                "effective_context_window must be an integer"
            )
        if self.effective_context_window <= 0:
            raise ActualModelVLLMHostError(
                "effective_context_window must be positive"
            )
        if self.execution_path != "buffered":
            raise ActualModelVLLMHostError(
                "canonical vLLM screening execution_path must be buffered"
            )
        if not isinstance(
            self.continuity_runtime,
            ExplicitContinuityRuntimeConfiguration,
        ):
            raise TypeError(
                "continuity_runtime must be ExplicitContinuityRuntimeConfiguration"
            )
        if not self.scenario_ids or len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ActualModelVLLMHostError(
                "scenario_ids must be non-empty and unique"
            )
        if not all(isinstance(item, str) and item.strip() for item in self.scenario_ids):
            raise ActualModelVLLMHostError(
                "scenario_ids must contain non-empty strings"
            )
        if tuple(self.conditions) != expected_conditions:
            if self.format_version == HISTORICAL_VLLM_SCREENING_PLAN_FORMAT_VERSION:
                expected_label = "A, B, C"
            else:
                expected_label = "reference_baseline, pass2_reasoning_escalation"
            raise ActualModelVLLMHostError(
                "vLLM screening plan format "
                f"{self.format_version} conditions must be exactly {expected_label} in order"
            )
        if self.format_version == VLLM_SCREENING_PLAN_FORMAT_VERSION:
            _validate_current_screening_role_semantics(self.conditions)
        if len(set(self.supported_decoding_controls)) != len(
            self.supported_decoding_controls
        ):
            raise ActualModelVLLMHostError(
                "supported_decoding_controls must be unique"
            )

    @property
    def decoding_config(self) -> OpenAICompatibleDecodingConfig:
        return OpenAICompatibleDecodingConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            seed=self.seed,
        )

    @property
    def decoding_capabilities(self) -> OpenAICompatibleDecodingCapabilities:
        return OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset(self.supported_decoding_controls)
        )

    def to_mapping(self) -> dict[str, object]:
        mapping: dict[str, object] = {
            "format_version": self.format_version,
            "screening_id": self.screening_id,
            "target_id": self.target_id,
            "effective_context_window": self.effective_context_window,
            "decoding": self.decoding_config.to_mapping(),
            "supported_decoding_controls": list(self.supported_decoding_controls),
            "execution_path": self.execution_path,
            "continuity_runtime": {
                "max_items": self.continuity_runtime.max_items,
                "lifetime_revisions": self.continuity_runtime.lifetime_revisions,
            },
            "scenario_ids": list(self.scenario_ids),
            "conditions": {
                key: condition.to_mapping()
                for key, condition in self.conditions.items()
            },
        }
        if self.scenario_set_path is not None:
            mapping["scenario_set_path"] = self.scenario_set_path
            mapping["scenario_set_revision"] = self.scenario_set_revision
        if self.capacity_evidence_id is not None:
            mapping["capacity_evidence_id"] = self.capacity_evidence_id
        return mapping


def _validate_current_screening_role_semantics(
    conditions: Mapping[str, VLLMScreeningCondition],
) -> None:
    reference = conditions["reference_baseline"]
    reference_requests = reference.pass_requests
    reference_pass1 = reference_requests.pass1
    reference_pass2 = reference_requests.pass2
    if (
        reference.cognition_execution.mode != "two_pass"
        or reference_requests.mode != "two_pass"
        or reference_pass1 is None
        or reference_pass2 is None
        or reference_pass1.reasoning_mode is not CognitionReasoningMode.OFF
        or reference_pass2.reasoning_mode is not CognitionReasoningMode.OFF
        or reference_pass1.reasoning_budget is not None
        or reference_pass2.reasoning_budget is not None
        or reference_pass1.structured_output_mode is not None
        or reference_pass2.structured_output_mode
        is not CognitionStructuredOutputMode.NATIVE
    ):
        raise ActualModelVLLMHostError(
            "reference_baseline must be a two-pass OFF/OFF condition with "
            "plain Pass 1 and native Pass 2 transport"
        )

    escalation = conditions["pass2_reasoning_escalation"]
    escalation_requests = escalation.pass_requests
    escalation_pass1 = escalation_requests.pass1
    escalation_pass2 = escalation_requests.pass2
    if (
        escalation.cognition_execution.mode != "two_pass"
        or escalation_requests.mode != "two_pass"
        or escalation_pass1 is None
        or escalation_pass2 is None
    ):
        raise ActualModelVLLMHostError(
            "pass2_reasoning_escalation must be a two-pass screening condition"
        )
    if escalation_pass1 != reference_pass1:
        raise ActualModelVLLMHostError(
            "pass2_reasoning_escalation must preserve reference_baseline Pass 1"
        )
    if (
        escalation_pass2.reasoning_mode is None
        or escalation_pass2.reasoning_mode is CognitionReasoningMode.OFF
    ):
        raise ActualModelVLLMHostError(
            "pass2_reasoning_escalation must use non-OFF Pass 2 reasoning"
        )
    reference_non_reasoning = (
        reference_pass2.temperature,
        reference_pass2.top_p,
        reference_pass2.max_output_tokens,
        reference_pass2.structured_output_mode,
    )
    escalation_non_reasoning = (
        escalation_pass2.temperature,
        escalation_pass2.top_p,
        escalation_pass2.max_output_tokens,
        escalation_pass2.structured_output_mode,
    )
    if escalation_non_reasoning != reference_non_reasoning:
        raise ActualModelVLLMHostError(
            "pass2_reasoning_escalation must preserve reference_baseline Pass 2 "
            "decoding/output/structured-output controls"
        )


@dataclass(frozen=True, slots=True)
class VLLMReasoningProbeProof:
    proof_id: str
    source_issue: int
    source_comment_id: int
    target_id: str
    target_revision: str
    backend_version: str
    request_model: str
    reasoning_parser: str
    template_thinking_control: str
    off_probe: VLLMReasoningProbeEvidence
    bounded_probe: VLLMReasoningProbeEvidence
    format_version: int = VLLM_REASONING_PROBE_PROOF_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != VLLM_REASONING_PROBE_PROOF_FORMAT_VERSION:
            raise ActualModelVLLMHostError(
                "unsupported vLLM reasoning probe proof format_version"
            )
        for name in (
            "proof_id",
            "target_id",
            "target_revision",
            "backend_version",
            "request_model",
            "reasoning_parser",
            "template_thinking_control",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelVLLMHostError(f"{name} must be a non-empty string")
        if self.source_issue != VLLM_REASONING_PROOF_SOURCE_ISSUE:
            raise ActualModelVLLMHostError(
                "vLLM reasoning proof source_issue is not the canonical provider owner"
            )
        if self.source_comment_id not in VLLM_REASONING_PROOF_SOURCE_COMMENTS:
            raise ActualModelVLLMHostError(
                "vLLM reasoning proof source_comment_id is not a frozen provider "
                "reasoning evidence comment"
            )
        if not isinstance(self.off_probe, VLLMReasoningProbeEvidence):
            raise TypeError("off_probe must be VLLMReasoningProbeEvidence")
        if not isinstance(self.bounded_probe, VLLMReasoningProbeEvidence):
            raise TypeError("bounded_probe must be VLLMReasoningProbeEvidence")


@dataclass(frozen=True, slots=True)
class PreparedVLLMHostRun:
    plan: VLLMScreeningPlan
    screening_condition_id: str
    condition: VLLMScreeningCondition
    capacity_evidence: VLLMRuntimeCapacityEvidence
    target: ActualModelRepositorySnapshotTarget
    snapshot_verification: ActualModelRepositorySnapshotVerification
    reasoning_capability: VLLMReasoningCapabilityAttestation
    scenario_set: ActualModelScenarioSet
    fixture_root: Path
    provider: OpenAICompatibleProvider
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None
    manifest: ActualModelRunManifest
    binding: ActualModelVLLMExecutionBinding
    scenario_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VLLMHostRunArtifact:
    scenario_id: str
    execution_id: str
    run_id: str
    artifact_path: str
    boundary_verdict_id: str
    boundary_outcome: str
    boundary_artifact_path: str
    timing_id: str
    timing_artifact_path: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "scenario_id": self.scenario_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
            "boundary_verdict_id": self.boundary_verdict_id,
            "boundary_outcome": self.boundary_outcome,
            "boundary_artifact_path": self.boundary_artifact_path,
            "timing_id": self.timing_id,
            "timing_artifact_path": self.timing_artifact_path,
        }


def load_vllm_screening_plan(path: str | Path) -> VLLMScreeningPlan:
    mapping = _load_json_mapping(path, label="vLLM screening plan")
    required_keys = {
        "format_version",
        "screening_id",
        "target_id",
        "effective_context_window",
        "decoding",
        "supported_decoding_controls",
        "execution_path",
        "continuity_runtime",
        "scenario_ids",
        "conditions",
    }
    observed_keys = set(mapping)
    missing_keys = sorted(required_keys - observed_keys)
    unknown_keys = sorted(
        observed_keys
        - required_keys
        - {"capacity_evidence_id", "scenario_set_path", "scenario_set_revision"}
    )
    if missing_keys:
        raise ActualModelVLLMHostError(
            "vLLM screening plan is missing fields: " + ", ".join(missing_keys)
        )
    if unknown_keys:
        raise ActualModelVLLMHostError(
            "vLLM screening plan has unknown fields: " + ", ".join(unknown_keys)
        )
    format_version = _integer(mapping["format_version"], "format_version")
    decoding = _mapping(mapping["decoding"], "decoding")
    _require_exact_keys(decoding, {"temperature", "top_p", "seed"}, "decoding")
    continuity = _mapping(mapping["continuity_runtime"], "continuity_runtime")
    _require_exact_keys(
        continuity,
        {"max_items", "lifetime_revisions"},
        "continuity_runtime",
    )
    conditions_raw = _mapping(mapping["conditions"], "conditions")
    execution_path = _string(mapping["execution_path"], "execution_path")
    conditions: dict[str, VLLMScreeningCondition] = {}
    for key, value in conditions_raw.items():
        conditions[key] = _parse_screening_condition(
            value,
            label=f"conditions.{key}",
            execution_path=execution_path,
            format_version=format_version,
        )
    controls = _list(mapping["supported_decoding_controls"], "supported_decoding_controls")
    scenarios = _list(mapping["scenario_ids"], "scenario_ids")
    try:
        return VLLMScreeningPlan(
            format_version=format_version,
            screening_id=_string(mapping["screening_id"], "screening_id"),
            target_id=_string(mapping["target_id"], "target_id"),
            effective_context_window=_integer(
                mapping["effective_context_window"],
                "effective_context_window",
            ),
            temperature=_optional_number(decoding["temperature"], "decoding.temperature"),
            top_p=_optional_number(decoding["top_p"], "decoding.top_p"),
            seed=_optional_integer(decoding["seed"], "decoding.seed"),
            supported_decoding_controls=tuple(
                _string(value, f"supported_decoding_controls[{index}]")
                for index, value in enumerate(controls)
            ),
            execution_path=execution_path,
            continuity_runtime=ExplicitContinuityRuntimeConfiguration(
                max_items=_integer(
                    continuity["max_items"],
                    "continuity_runtime.max_items",
                ),
                lifetime_revisions=_integer(
                    continuity["lifetime_revisions"],
                    "continuity_runtime.lifetime_revisions",
                ),
            ),
            scenario_ids=tuple(
                _string(value, f"scenario_ids[{index}]")
                for index, value in enumerate(scenarios)
            ),
            conditions=conditions,
            scenario_set_path=(
                _string(mapping["scenario_set_path"], "scenario_set_path")
                if mapping.get("scenario_set_path") is not None
                else None
            ),
            scenario_set_revision=(
                _string(mapping["scenario_set_revision"], "scenario_set_revision")
                if mapping.get("scenario_set_revision") is not None
                else None
            ),
            capacity_evidence_id=(
                _string(mapping["capacity_evidence_id"], "capacity_evidence_id")
                if mapping.get("capacity_evidence_id") is not None
                else None
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelVLLMHostError):
            raise
        raise ActualModelVLLMHostError(f"invalid vLLM screening plan: {exc}") from exc


def load_vllm_reasoning_probe_proof(path: str | Path) -> VLLMReasoningProbeProof:
    mapping = _load_json_mapping(path, label="vLLM reasoning probe proof")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "proof_id",
            "source_issue",
            "source_comment_id",
            "target_id",
            "target_revision",
            "backend_version",
            "request_model",
            "reasoning_parser",
            "template_thinking_control",
            "off_probe",
            "bounded_probe",
        },
        "vLLM reasoning probe proof",
    )
    try:
        return VLLMReasoningProbeProof(
            format_version=_integer(mapping["format_version"], "format_version"),
            proof_id=_string(mapping["proof_id"], "proof_id"),
            source_issue=_integer(mapping["source_issue"], "source_issue"),
            source_comment_id=_integer(
                mapping["source_comment_id"], "source_comment_id"
            ),
            target_id=_string(mapping["target_id"], "target_id"),
            target_revision=_string(mapping["target_revision"], "target_revision"),
            backend_version=_string(mapping["backend_version"], "backend_version"),
            request_model=_string(mapping["request_model"], "request_model"),
            reasoning_parser=_string(mapping["reasoning_parser"], "reasoning_parser"),
            template_thinking_control=_string(
                mapping["template_thinking_control"],
                "template_thinking_control",
            ),
            off_probe=_parse_probe(mapping["off_probe"], "off_probe"),
            bounded_probe=_parse_probe(mapping["bounded_probe"], "bounded_probe"),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelVLLMHostError):
            raise
        raise ActualModelVLLMHostError(
            f"invalid vLLM reasoning probe proof: {exc}"
        ) from exc


def acquire_vllm_reasoning_capability(
    *,
    proof: VLLMReasoningProbeProof,
    target: ActualModelRepositorySnapshotTarget,
    base_url: str,
    api_key: str | None,
    fetch_json: FetchJSON | None = None,
) -> VLLMReasoningCapabilityAttestation:
    """Re-bind frozen R3B probe facts to the exact live backend/model identity."""

    if not isinstance(proof, VLLMReasoningProbeProof):
        raise TypeError("proof must be VLLMReasoningProbeProof")
    if not isinstance(target, ActualModelRepositorySnapshotTarget):
        raise TypeError("target must be ActualModelRepositorySnapshotTarget")
    if proof.target_id != target.target_id or proof.target_revision != target.revision:
        raise ActualModelVLLMHostError(
            "vLLM reasoning proof does not match the frozen target"
        )
    version_url, models_url = _vllm_attestation_urls(base_url)
    loader = fetch_json or _fetch_json
    try:
        version_response = loader(version_url, api_key)
        models_response = loader(models_url, api_key)
        backend = attest_vllm_backend(
            request_model=proof.request_model,
            version_response=version_response,
            models_response=models_response,
        )
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelVLLMHostError):
            raise
        raise ActualModelVLLMHostError(
            f"cannot attest live vLLM backend identity: {exc}"
        ) from exc
    if backend.version != proof.backend_version:
        raise ActualModelVLLMHostError(
            "live vLLM version does not match the frozen reasoning probe proof"
        )
    try:
        return attest_vllm_reasoning_capabilities(
            backend_attestation=backend,
            target=target,
            reasoning_parser=proof.reasoning_parser,
            template_thinking_control=proof.template_thinking_control,
            off_probe=proof.off_probe,
            bounded_probe=proof.bounded_probe,
        )
    except (TypeError, ValueError) as exc:
        raise ActualModelVLLMHostError(
            f"cannot reconstruct vLLM reasoning capability: {exc}"
        ) from exc


def _capacity_evidence_commit_requirement(
    *,
    plan: VLLMScreeningPlan,
    capacity_evidence: VLLMRuntimeCapacityEvidence,
    capacity_evidence_root: str | Path | None,
) -> str | None:
    """Return the measurement commit that must equal the screening checkout.

    Capacity evidence is an exact execution-admission artifact. Current Stage R
    does not waive its RelayLM commit merely because the artifact is tracked in
    the repository; material prompt/wire/transport changes require fresh evidence.
    """

    del plan, capacity_evidence_root
    return capacity_evidence.relaylm_commit


def prepare_vllm_screening_condition(
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
    capacity_evidence_root: str | Path | None = None,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None = None,
) -> PreparedVLLMHostRun:
    if condition_id not in plan.conditions:
        raise ActualModelVLLMHostError(
            f"unknown vLLM screening condition: {condition_id}"
        )
    condition = plan.conditions[condition_id]
    if cognitive_budget is not None:
        if not isinstance(cognitive_budget, TwoPassCognitiveBudgetRuntimeConfig):
            raise TypeError(
                "cognitive_budget must be TwoPassCognitiveBudgetRuntimeConfig or None"
            )
        if condition.cognition_execution.mode != "two_pass":
            raise ActualModelVLLMHostError(
                "explicit two-pass cognitive budget requires a two_pass screening condition"
            )
        if (
            cognitive_budget.pass1_total.model_context_window
            != plan.effective_context_window
            or cognitive_budget.pass2_total.model_context_window
            != plan.effective_context_window
        ):
            raise ActualModelVLLMHostError(
                "two-pass cognitive budget context windows must match the screening effective_context_window"
            )
    if plan.capacity_evidence_id is None:
        raise ActualModelVLLMHostError(
            "vLLM screening execution requires citable capacity evidence"
        )
    root = Path(repo_root).resolve()
    capacity_root = (
        Path(capacity_evidence_root)
        if capacity_evidence_root is not None
        else root / CANONICAL_VLLM_CAPACITY_EVIDENCE_ROOT
    )
    try:
        capacity_evidence = load_vllm_runtime_capacity_evidence(
            capacity_evidence_path(
                artifact_root=capacity_root,
                evidence_id=plan.capacity_evidence_id,
            )
        )
        validate_capacity_window(
            evidence=capacity_evidence,
            capacity_evidence_id=plan.capacity_evidence_id,
            effective_context_window=plan.effective_context_window,
        )
    except (OSError, TypeError, ValueError, VLLMRuntimeCapacityEvidenceError) as exc:
        raise ActualModelVLLMHostError(
            f"cannot validate cited vLLM capacity evidence: {exc}"
        ) from exc
    try:
        expected_model_runner = validate_vllm_model_runner(
            model_runner,
            label="expected runtime model_runner",
        )
    except (TypeError, ValueError, VLLMRuntimeCapacityEvidenceError) as exc:
        raise ActualModelVLLMHostError(
            f"current vLLM screening requires an explicit model_runner identity: {exc}"
        ) from exc
    if capacity_evidence.model_runner is None:
        raise ActualModelVLLMHostError(
            "cited capacity evidence has no model_runner identity and cannot "
            "authorize current vLLM screening"
        )
    if capacity_evidence.model_runner != expected_model_runner:
        raise ActualModelVLLMHostError(
            "cited capacity evidence model_runner "
            f"{capacity_evidence.model_runner} does not match expected runtime "
            f"model_runner {expected_model_runner}"
        )

    _verify_clean_exact_repo(
        root=root,
        expected_commit=relaylm_commit,
        capacity_evidence_commit=_capacity_evidence_commit_requirement(
            plan=plan,
            capacity_evidence=capacity_evidence,
            capacity_evidence_root=capacity_evidence_root,
        ),
    )
    target = load_actual_model_repository_snapshot_target(
        root / CANONICAL_VLLM_TARGET_PATH
    )
    if target.target_id != plan.target_id:
        raise ActualModelVLLMHostError(
            "screening target_id does not match the canonical frozen target"
        )
    if (
        capacity_evidence.target_id != target.target_id
        or capacity_evidence.target_revision != target.revision
        or capacity_evidence.tokenizer_identity != target.tokenizer_identity
        or capacity_evidence.chat_template_identity != target.chat_template_identity
    ):
        raise ActualModelVLLMHostError(
            "cited capacity evidence does not match the canonical frozen target"
        )
    try:
        snapshot_verification = verify_actual_model_repository_snapshot(
            target=target,
            snapshot_root=snapshot_root,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ActualModelVLLMHostError(
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
    if (
        capacity_evidence.backend_version != capability.backend_version
        or capacity_evidence.request_model != capability.request_model
        or capacity_evidence.observed_max_model_len
        != capability.backend_attestation.max_model_len
    ):
        raise ActualModelVLLMHostError(
            "cited capacity evidence does not match the live vLLM runtime"
        )
    try:
        live_serving_counter = VLLMServingTokenizerCounter(
            base_url=base_url,
            target=target,
            reasoning_capability=capability,
            expected_max_model_len=capacity_evidence.observed_max_model_len,
            api_key=api_key,
        )
        live_counter_identity = live_serving_counter.evidence_identity
    except (TypeError, ValueError) as exc:
        raise ActualModelVLLMHostError(
            f"cannot reconstruct vLLM capacity counter identity: {exc}"
        ) from exc
    if capacity_evidence.counter_identity != live_counter_identity:
        raise ActualModelVLLMHostError(
            "cited capacity evidence counter identity does not match current vLLM counting semantics"
        )
    bound_cognitive_budget = None
    if cognitive_budget is not None:
        bound_cognitive_budget = _bind_vllm_two_pass_cognitive_budget(
            runtime=cognitive_budget,
            plan=plan,
            capability=capability,
            live_serving_counter=live_serving_counter,
            live_counter_identity=live_counter_identity,
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
        raise ActualModelVLLMHostError(
            "screening scenario-set revision does not match the execution template"
        )
    fixture_root = root / CANONICAL_FIXTURE_PATH
    fixture_revision = character_fixture_revision(fixture_root)
    _validate_scenarios(plan=plan, scenario_set=scenario_set)
    try:
        validate_capacity_coverage(
            evidence=capacity_evidence,
            scenario_set_revision=scenario_set.revision,
            required_coverage=_required_capacity_coverage(
                condition=condition,
                scenario_set=scenario_set,
                scenario_ids=plan.scenario_ids,
            ),
        )
    except (TypeError, ValueError, VLLMRuntimeCapacityEvidenceError) as exc:
        raise ActualModelVLLMHostError(
            f"cannot validate cited vLLM capacity coverage: {exc}"
        ) from exc

    provider_type: type[OpenAICompatibleProvider] = OpenAICompatibleProvider
    if condition.cognition_execution.mode == "two_pass":
        provider_type = OpenAICompatibleTwoPassProvider
    provider = provider_type(
        base_url=base_url,
        model=proof.request_model,
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
            effective_context_window=plan.effective_context_window,
            decoding_configuration=tuple(
                sorted(identity.effective_decoding_configuration.items())
            ),
            structured_output_schema_version=CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION,
            scenario_set_version=scenario_set.scenario_set_version,
            condition_id=condition.condition_id,
            budgets=ExplicitBudgetConfiguration(),
            cognitive_budget=(
                ExplicitCognitiveBudgetConfiguration.from_runtime(bound_cognitive_budget)
                if bound_cognitive_budget is not None
                else None
            ),
            continuity_runtime=plan.continuity_runtime,
            execution_path=plan.execution_path,
            restart_boundary="none",
            seed=plan.seed,
            provider_capabilities=identity.provider_capabilities,
            replicate_id=replicate_id,
            cognition_execution=condition.cognition_execution,
            cognition_pass_requests=condition.pass_requests,
        )
        binding = bind_vllm_execution_condition(
            target=target,
            snapshot_verification=snapshot_verification,
            snapshot_root=snapshot_root,
            reasoning_capability=capability,
            provider=provider,
            manifest=manifest,
            configured_context_window=plan.effective_context_window,
        )
    except Exception:
        _close_provider_best_effort(provider)
        raise
    return PreparedVLLMHostRun(
        plan=plan,
        screening_condition_id=condition_id,
        condition=condition,
        capacity_evidence=capacity_evidence,
        target=target,
        snapshot_verification=snapshot_verification,
        reasoning_capability=capability,
        scenario_set=scenario_set,
        fixture_root=fixture_root,
        provider=provider,
        cognitive_budget=bound_cognitive_budget,
        manifest=manifest,
        binding=binding,
        scenario_ids=plan.scenario_ids,
    )


async def execute_vllm_host_run(
    *,
    prepared: PreparedVLLMHostRun,
    snapshot_root: str | Path,
    workspace_root: str | Path,
    artifact_root: str | Path,
) -> tuple[VLLMHostRunArtifact, ...]:
    # Import locally because the timing module type-checks VLLMScreeningPlan.
    # Keeping this edge local avoids a module-import cycle while preserving the
    # existing timing and execution-boundary ownership.
    from relaylm.actual_model_fast_screening import (
        ScreeningTimingRecorder,
        instrument_screening_provider,
    )
    from relaylm.actual_model_fast_screening_artifacts import (
        bind_fast_screening_timing_artifact,
        write_fast_screening_timing_artifact,
    )

    workspace_base = Path(workspace_root)
    artifact_base = Path(artifact_root)
    results: list[VLLMHostRunArtifact] = []
    try:
        for scenario_id in prepared.scenario_ids:
            timing_recorder = ScreeningTimingRecorder()
            scenario_started_ns = timing_recorder.clock_ns()
            timed_provider = instrument_screening_provider(
                prepared.provider,
                recorder=timing_recorder,
            )
            result = await run_bound_vllm_actual_model_scenario_definition(
                binding=prepared.binding,
                scenario_set=prepared.scenario_set,
                scenario_id=scenario_id,
                fixture_root=prepared.fixture_root,
                workspace_root=(
                    workspace_base
                    / prepared.plan.screening_id
                    / prepared.screening_condition_id
                    / prepared.manifest.replicate_id
                    / scenario_id
                ),
                provider=timed_provider,
                cognitive_budget=prepared.cognitive_budget,
            )
            scenario_elapsed_ms = (
                timing_recorder.clock_ns() - scenario_started_ns
            ) / 1_000_000
            definition = prepared.scenario_set.scenario(scenario_id)
            execution_id = result.execution.execution_id
            timing = bind_fast_screening_timing_artifact(
                screening_id=prepared.plan.screening_id,
                condition_id=prepared.screening_condition_id,
                replicate_id=prepared.manifest.replicate_id,
                scenario_id=scenario_id,
                execution_id=execution_id,
                run_id=result.run_id,
                execution_mode=prepared.condition.cognition_execution.mode,
                turn_count=len(definition.scenario.turns),
                scenario_elapsed_ms=scenario_elapsed_ms,
                calls=tuple(timing_recorder.calls),
            )
            timing_path = write_fast_screening_timing_artifact(
                artifact=timing,
                artifact_root=artifact_base,
            )
            path = write_vllm_actual_model_execution_result(
                result=result,
                artifact_root=artifact_base,
            )
            verdict = evaluate_actual_model_deterministic_boundary(
                result=result.execution,
            )
            boundary_path = write_actual_model_deterministic_boundary_verdict(
                verdict=verdict,
                artifact_root=artifact_base,
            )
            results.append(
                VLLMHostRunArtifact(
                    scenario_id=scenario_id,
                    execution_id=result.execution_id,
                    run_id=result.run_id,
                    artifact_path=str(path),
                    boundary_verdict_id=verdict.verdict_id,
                    boundary_outcome=verdict.outcome,
                    boundary_artifact_path=str(boundary_path),
                    timing_id=timing.timing_id,
                    timing_artifact_path=str(timing_path),
                )
            )
    finally:
        await prepared.provider.aclose()
    return tuple(results)


def _bind_vllm_two_pass_cognitive_budget(
    *,
    runtime: TwoPassCognitiveBudgetRuntimeConfig,
    plan: VLLMScreeningPlan,
    capability: VLLMReasoningCapabilityAttestation,
    live_serving_counter: VLLMServingTokenizerCounter,
    live_counter_identity: SerializedInputCounterIdentity,
) -> TwoPassCognitiveBudgetRuntimeConfig:
    declared_counter = runtime.token_counter
    if not isinstance(declared_counter, OpenAICompatibleTwoPassSerializedInputCounter):
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive budget requires the production OpenAI-compatible two-pass counter"
        )
    if declared_counter.model != capability.request_model:
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive-budget counter model does not match live runtime"
        )
    if declared_counter.decoding_config != plan.decoding_config:
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive-budget counter decoding config does not match screening plan"
        )
    if declared_counter.decoding_capabilities != plan.decoding_capabilities:
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive-budget counter capabilities do not match screening plan"
        )
    if declared_counter.vllm_reasoning_capability != capability:
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive-budget counter reasoning capability does not match live runtime"
        )
    if declared_counter.evidence_identity != live_counter_identity:
        raise ActualModelVLLMHostError(
            "vLLM two-pass cognitive-budget counter identity does not match cited capacity semantics"
        )

    bound_counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model=capability.request_model,
        count_input=live_serving_counter.count_input,
        decoding_config=plan.decoding_config,
        decoding_capabilities=plan.decoding_capabilities,
        vllm_reasoning_capability=capability,
        evidence_identity=live_counter_identity,
    )
    return TwoPassCognitiveBudgetRuntimeConfig(
        pass1_total=runtime.pass1_total,
        pass2_total=runtime.pass2_total,
        policy=runtime.policy,
        token_counter=bound_counter,
    )


def _required_capacity_coverage(
    *,
    condition: VLLMScreeningCondition,
    scenario_set: ActualModelScenarioSet,
    scenario_ids: tuple[str, ...],
) -> tuple[VLLMCapacityFootprintCoverage, ...]:
    if condition.pass_requests.mode == "single_pass":
        request = condition.pass_requests.single_request
        if request is None:
            raise ActualModelVLLMHostError(
                "single-pass screening condition is missing its pass request"
            )
        topology = "single_pass"
        requests = (("single_pass", request),)
    elif condition.pass_requests.mode == "two_pass":
        if condition.pass_requests.pass1 is None or condition.pass_requests.pass2 is None:
            raise ActualModelVLLMHostError(
                "two-pass screening condition is missing pass1/pass2 requests"
            )
        topology = "two_pass"
        requests = (
            ("pass1", condition.pass_requests.pass1),
            ("pass2", condition.pass_requests.pass2),
        )
    else:
        raise ActualModelVLLMHostError(
            "unsupported screening cognition pass-request mode"
        )

    required: list[VLLMCapacityFootprintCoverage] = []
    for scenario_id in scenario_ids:
        try:
            definition = scenario_set.scenario(scenario_id)
        except KeyError as exc:
            raise ActualModelVLLMHostError(
                f"screening scenario is not in the bound scenario set: {scenario_id}"
            ) from exc
        for turn_index in range(1, len(definition.scenario.turns) + 1):
            for pass_id, request in requests:
                required.append(
                    VLLMCapacityFootprintCoverage(
                        condition_id=condition.condition_id,
                        topology=topology,
                        pass_id=pass_id,
                        scenario_id=scenario_id,
                        turn_index=turn_index,
                        pass_request_id=vllm_capacity_pass_request_id(request),
                    )
                )
    return tuple(required)


def _parse_screening_condition(
    value: object,
    *,
    label: str,
    execution_path: str,
    format_version: int,
) -> VLLMScreeningCondition:
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {"condition_id", "cognition_execution", "pass_requests"},
        label,
    )
    mode = _string(mapping["cognition_execution"], f"{label}.cognition_execution")
    if mode == "single_pass":
        cognition_execution = CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=execution_path
        )
    elif mode == "two_pass":
        cognition_execution = CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=execution_path
        )
    else:
        raise ActualModelVLLMHostError(
            f"{label}.cognition_execution must be single_pass or two_pass"
        )
    requests = _parse_pass_requests(
        mapping["pass_requests"],
        f"{label}.pass_requests",
        format_version=format_version,
    )
    return VLLMScreeningCondition(
        condition_id=_string(mapping["condition_id"], f"{label}.condition_id"),
        cognition_execution=cognition_execution,
        pass_requests=requests,
    )


def _parse_pass_requests(
    value: object,
    label: str,
    *,
    format_version: int,
) -> ActualModelCognitionPassRequests:
    mapping = _mapping(value, label)
    _require_exact_keys(mapping, {"single_pass", "pass1", "pass2"}, label)
    single_raw = mapping["single_pass"]
    pass1_raw = mapping["pass1"]
    pass2_raw = mapping["pass2"]
    try:
        if single_raw is not None:
            if pass1_raw is not None or pass2_raw is not None:
                raise ActualModelVLLMHostError(
                    f"{label} single_pass cannot coexist with pass1/pass2"
                )
            return ActualModelCognitionPassRequests.single_pass(
                _parse_pass_request(
                    single_raw,
                    f"{label}.single_pass",
                    format_version=format_version,
                )
            )
        if pass1_raw is None or pass2_raw is None:
            raise ActualModelVLLMHostError(
                f"{label} must contain single_pass or both pass1/pass2"
            )
        return ActualModelCognitionPassRequests.two_pass(
            pass1=_parse_pass_request(
                pass1_raw,
                f"{label}.pass1",
                format_version=format_version,
            ),
            pass2=_parse_pass_request(
                pass2_raw,
                f"{label}.pass2",
                format_version=format_version,
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelVLLMHostError):
            raise
        raise ActualModelVLLMHostError(f"invalid {label}: {exc}") from exc


def _parse_pass_request(
    value: object,
    label: str,
    *,
    format_version: int,
) -> CognitionPassRequest:
    mapping = _mapping(value, label)
    expected = {
        "reasoning_mode",
        "reasoning_budget",
        "temperature",
        "top_p",
        "max_output_tokens",
    }
    if format_version == VLLM_SCREENING_PLAN_FORMAT_VERSION:
        expected.add("structured_output_mode")
    _require_exact_keys(mapping, expected, label)
    mode_raw = mapping["reasoning_mode"]
    mode = None
    if mode_raw is not None:
        try:
            mode = CognitionReasoningMode(_string(mode_raw, f"{label}.reasoning_mode"))
        except ValueError as exc:
            raise ActualModelVLLMHostError(
                f"{label}.reasoning_mode is unsupported"
            ) from exc
    structured_output_mode = None
    if format_version == VLLM_SCREENING_PLAN_FORMAT_VERSION:
        structured_raw = mapping["structured_output_mode"]
        if structured_raw is not None:
            try:
                structured_output_mode = CognitionStructuredOutputMode(
                    _string(
                        structured_raw,
                        f"{label}.structured_output_mode",
                    )
                )
            except ValueError as exc:
                raise ActualModelVLLMHostError(
                    f"{label}.structured_output_mode is unsupported"
                ) from exc
    return CognitionPassRequest(
        reasoning_mode=mode,
        reasoning_budget=_optional_integer(
            mapping["reasoning_budget"], f"{label}.reasoning_budget"
        ),
        temperature=_optional_number(mapping["temperature"], f"{label}.temperature"),
        top_p=_optional_number(mapping["top_p"], f"{label}.top_p"),
        max_output_tokens=_optional_integer(
            mapping["max_output_tokens"], f"{label}.max_output_tokens"
        ),
        structured_output_mode=structured_output_mode,
    )


def _parse_probe(value: object, label: str) -> VLLMReasoningProbeEvidence:
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {
            "wire_controls",
            "http_status",
            "accepted",
            "effect_proven",
            "repeatable",
            "activation_applied",
            "template_kwargs",
            "ambiguous",
        },
        label,
    )
    wire = _mapping(mapping["wire_controls"], f"{label}.wire_controls")
    unknown_wire = set(wire) - {"reasoning_effort", "thinking_token_budget"}
    if unknown_wire:
        raise ActualModelVLLMHostError(
            f"{label}.wire_controls has unknown fields: " + ", ".join(sorted(unknown_wire))
        )
    template = _mapping(mapping["template_kwargs"], f"{label}.template_kwargs")
    template_mapping: list[tuple[str, str | int | bool]] = []
    for key, raw in template.items():
        if not isinstance(key, str) or not key.strip():
            raise ActualModelVLLMHostError(
                f"{label}.template_kwargs keys must be non-empty strings"
            )
        if not isinstance(raw, (str, int, bool)):
            raise ActualModelVLLMHostError(
                f"{label}.template_kwargs values must be strings, integers, or booleans"
            )
        template_mapping.append((key, raw))
    controls = VLLMReasoningWireControls(
        reasoning_effort=(
            _string(wire["reasoning_effort"], f"{label}.wire_controls.reasoning_effort")
            if "reasoning_effort" in wire
            else None
        ),
        thinking_token_budget=(
            _integer(
                wire["thinking_token_budget"],
                f"{label}.wire_controls.thinking_token_budget",
            )
            if "thinking_token_budget" in wire
            else None
        ),
    )
    return VLLMReasoningProbeEvidence(
        wire_controls=controls,
        http_status=_integer(mapping["http_status"], f"{label}.http_status"),
        accepted=_boolean(mapping["accepted"], f"{label}.accepted"),
        effect_proven=_boolean(
            mapping["effect_proven"], f"{label}.effect_proven"
        ),
        repeatable=_boolean(mapping["repeatable"], f"{label}.repeatable"),
        activation_applied=_boolean(
            mapping["activation_applied"], f"{label}.activation_applied"
        ),
        template_kwargs=tuple(sorted(template_mapping)),
        ambiguous=_boolean(mapping["ambiguous"], f"{label}.ambiguous"),
    )


def _validate_scenarios(
    *, plan: VLLMScreeningPlan, scenario_set: ActualModelScenarioSet
) -> None:
    for scenario_id in plan.scenario_ids:
        try:
            definition = scenario_set.scenario(scenario_id)
        except KeyError as exc:
            raise ActualModelVLLMHostError(
                f"screening scenario is not in the bound scenario set: {scenario_id}"
            ) from exc
        if definition.scenario.family == "restart_quality":
            raise ActualModelVLLMHostError(
                "vLLM COGP5 screening does not include restart scenarios"
            )


def _vllm_attestation_urls(base_url: str) -> tuple[str, str]:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ActualModelVLLMHostError("vLLM base_url must be an HTTP(S) URL")
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    return f"{origin}/version", f"{origin}/v1/models"


def _fetch_json(url: str, api_key: str | None) -> object:
    headers = {"Accept": "application/json"}
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise ActualModelVLLMHostError(
                    f"vLLM identity request returned HTTP {response.status}"
                )
            return json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ActualModelVLLMHostError(
            f"vLLM identity request failed: {exc}"
        ) from exc


def _verify_clean_exact_repo(
    *,
    root: Path,
    expected_commit: str,
    capacity_evidence_commit: str | None = None,
) -> None:
    if not root.is_dir():
        raise ActualModelVLLMHostError("repo_root must be an existing directory")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ActualModelVLLMHostError(
            f"cannot verify host repository snapshot: {exc}"
        ) from exc
    if head != expected_commit:
        raise ActualModelVLLMHostError(
            f"host repository HEAD does not match relaylm_commit: {head}"
        )
    if capacity_evidence_commit is not None and head != capacity_evidence_commit:
        raise ActualModelVLLMHostError(
            "capacity evidence RelayLM commit does not match the exact screening checkout"
        )
    if status:
        raise ActualModelVLLMHostError(
            "host repository must be clean, including untracked files, before evidence execution"
        )


def _close_provider_best_effort(provider: OpenAICompatibleProvider) -> None:
    client = getattr(provider, "_client", None)
    close = getattr(client, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def _load_json_mapping(path: str | Path, *, label: str) -> Mapping[str, object]:
    try:
        raw = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActualModelVLLMHostError(f"cannot load {label}: {exc}") from exc
    return _mapping(raw, label)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelVLLMHostError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ActualModelVLLMHostError(f"{label} must be a JSON object")
    if not all(isinstance(key, str) for key in value):
        raise ActualModelVLLMHostError(f"{label} keys must be strings")
    return value


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ActualModelVLLMHostError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    mapping: Mapping[str, object], expected: set[str], label: str
) -> None:
    observed = set(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ActualModelVLLMHostError(
            f"{label} is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise ActualModelVLLMHostError(
            f"{label} has unknown fields: " + ", ".join(unknown)
        )


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActualModelVLLMHostError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActualModelVLLMHostError(f"{label} must be an integer")
    return value


def _optional_integer(value: object, label: str) -> int | None:
    if value is None:
        return None
    return _integer(value, label)


def _optional_number(value: object, label: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActualModelVLLMHostError(f"{label} must be a number or null")
    return value


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ActualModelVLLMHostError(f"{label} must be boolean")
    return value
