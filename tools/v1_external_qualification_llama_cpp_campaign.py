"""Bounded external-qualification campaign carriage for the v1 physical queue.

This module is the registered, llama.cpp-only campaign boundary.  It does not
discover or execute an executable supplied by a plan.  A scientific owner must
bind the typed live-launch, Hindsight-health, and participant hooks in Python.
The command-line entry point is intentionally limited to zero-semantic plan
validation; the full controller is exposed as ``run_campaign`` for that typed
owner binding.

The existing ``v1:external-qualification`` target remains the admission-only
freeze gate.  This target is the bounded carriage that can own a future full
campaign while the public physical runner owns the process-wide lease.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import socket
import subprocess
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import httpx
from tools.external_qualification import (
    SLOTS,
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    LiveLaunchAdmissionAttestation,
    freeze_experiment_identity,
    validate_manifest,
    validate_observation,
    validate_case,
)
from tools.external_qualification_readiness import (
    ExternalQualificationReadinessError,
    validate_launch_readiness,
)


CAMPAIGN_TARGET = "v1:external-qualification-campaign"
CAMPAIGN_FORMAT_VERSION = 1
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_MODES = {"fresh_run", "exact_infrastructure_resume"}
_HEALTH_KEYS = {
    "implementation",
    "source_revision",
    "version",
    "license",
    "deployment",
    "semantic_operations_called",
    "semantic_generation_count",
    "benchmark_question_count",
    "answer_model_generation_count",
    "judge_call_count",
}
_HEALTH_DEPLOYMENT_KEYS = {
    "deployment_id",
    "dependency_fingerprint",
    "import_status",
    "llm_connection_verification",
    "process_health_status",
    "capability_status",
}
_LAUNCH_SPEC_KEYS = {
    "llama_cpp_root",
    "artifact_path",
    "upstream_revision",
    "expected_build_info",
    "expected_model_alias",
    "artifact_sha256",
    "runtime",
    "model_runner",
    "context",
    "slots",
    "port",
    "gpu_layers",
    "effective_gpu_reservation",
    "capacity_evidence",
}
_DESCRIPTOR_KEYS = {
    "format_version",
    "target",
    "execution_freeze",
    "artifact_root",
    "llama_cpp",
    "hindsight_health",
    "axes",
}
_AXIS_KEYS = {"axis_id", "case", "manifest", "identity", "questions", "run_mode"}
_QUESTION_KEYS = {"question_id", "prompt", "content_fingerprint", "session_id"}
_CLEANUP_KEYS = {
    "all_owned_processes_terminated",
    "external_processes_touched",
    "errors",
}


class CampaignCarriageError(ExternalQualificationError):
    """Raised when the bounded campaign contract cannot be admitted."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignCarriageError(f"{label} must be an object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise CampaignCarriageError(
            f"{label} keys must be exact; missing={missing!r} extra={extra!r}"
        )


def _require_nonempty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CampaignCarriageError(f"{label} must be a non-empty string")
    return value


def _require_positive_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CampaignCarriageError(f"{label} must be a positive integer")
    return value


def _require_sha(value: object, *, label: str, pattern: re.Pattern[str]) -> str:
    result = _require_nonempty_string(value, label=label)
    if pattern.fullmatch(result) is None:
        raise CampaignCarriageError(f"{label} has an invalid digest")
    return result


def _require_absolute_path(value: object, *, label: str) -> Path:
    path = Path(_require_nonempty_string(value, label=label))
    if not path.is_absolute():
        raise CampaignCarriageError(f"{label} must be absolute")
    return path


@dataclass(frozen=True, slots=True)
class HindsightHealthAttestation:
    """Dependency-complete, zero-semantic Hindsight health evidence."""

    value: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> HindsightHealthAttestation:
        _require_exact_keys(raw, _HEALTH_KEYS, label="hindsight_health")
        if raw["implementation"] != "hindsight":
            raise CampaignCarriageError("hindsight_health implementation must be hindsight")
        if raw["version"] != "v0.10.0":
            raise CampaignCarriageError("hindsight_health must identify Hindsight v0.10.0")
        _require_nonempty_string(raw["license"], label="hindsight_health.license")
        _require_sha(raw["source_revision"], label="hindsight_health.source_revision", pattern=_SHA1_RE)
        deployment = _require_mapping(raw["deployment"], label="hindsight_health.deployment")
        _require_exact_keys(deployment, _HEALTH_DEPLOYMENT_KEYS, label="hindsight_health.deployment")
        for key in _HEALTH_DEPLOYMENT_KEYS:
            _require_nonempty_string(deployment[key], label=f"hindsight_health.deployment.{key}")
        for key in ("import_status", "process_health_status", "capability_status"):
            if deployment[key] != "passed":
                raise CampaignCarriageError(
                    f"hindsight_health.deployment.{key} must be passed"
                )
        if deployment["llm_connection_verification"] != "skipped_zero_semantic_policy":
            raise CampaignCarriageError(
                "Hindsight LLM connection verification must be skipped under the zero-semantic policy"
            )
        if _FINGERPRINT_RE.fullmatch(str(deployment["dependency_fingerprint"])) is None:
            raise CampaignCarriageError(
                "hindsight_health.deployment.dependency_fingerprint must be sha256:<64 hex>"
            )
        operations = raw["semantic_operations_called"]
        if not isinstance(operations, list) or operations:
            raise CampaignCarriageError("Hindsight semantic operations must be an empty list")
        for key in (
            "semantic_generation_count",
            "benchmark_question_count",
            "answer_model_generation_count",
            "judge_call_count",
        ):
            if raw[key] != 0:
                raise CampaignCarriageError(f"hindsight_health.{key} must remain zero")
        return cls(value=dict(raw))

    @property
    def fingerprint(self) -> str:
        return _sha256_json(self.value)


class HindsightHealthProbe(Protocol):
    """Typed probe supplied by the scientific owner; it performs no benchmark work."""

    def attest_zero_semantic_health(self) -> Mapping[str, Any]:
        ...


def verify_hindsight_health(
    expected: HindsightHealthAttestation,
    probe: HindsightHealthProbe,
) -> HindsightHealthAttestation:
    """Run one dependency-complete health probe and compare it byte-for-byte."""

    observed = HindsightHealthAttestation.from_mapping(
        _require_mapping(
            probe.attest_zero_semantic_health(),
            label="hindsight health probe result",
        )
    )
    if _canonical_json(observed.value) != _canonical_json(expected.value):
        raise CampaignCarriageError("live Hindsight health does not match the frozen plan")
    return observed


@dataclass(frozen=True, slots=True)
class LlamaCppLaunchSpec:
    """Fixed llama.cpp launch inputs; no plan-provided executable is accepted."""

    llama_cpp_root: Path
    artifact_path: Path
    upstream_revision: str
    expected_build_info: str
    expected_model_alias: str
    artifact_sha256: str
    runtime: str
    model_runner: str
    context: int
    slots: int
    port: int
    gpu_layers: int
    effective_gpu_reservation: float
    capacity_evidence: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> LlamaCppLaunchSpec:
        _require_exact_keys(raw, _LAUNCH_SPEC_KEYS, label="llama_cpp")
        reservation = raw["effective_gpu_reservation"]
        if isinstance(reservation, bool) or not isinstance(reservation, (int, float)):
            raise CampaignCarriageError("llama_cpp.effective_gpu_reservation must be numeric")
        if not math.isfinite(float(reservation)) or not 0 < float(reservation) <= 1:
            raise CampaignCarriageError(
                "llama_cpp.effective_gpu_reservation must be in (0, 1]"
            )
        port = raw["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise CampaignCarriageError("llama_cpp.port must be a valid TCP port")
        gpu_layers = raw["gpu_layers"]
        if isinstance(gpu_layers, bool) or not isinstance(gpu_layers, int) or gpu_layers < 0:
            raise CampaignCarriageError("llama_cpp.gpu_layers must be a non-negative integer")
        capacity = _require_mapping(raw["capacity_evidence"], label="llama_cpp.capacity_evidence")
        return cls(
            llama_cpp_root=_require_absolute_path(raw["llama_cpp_root"], label="llama_cpp_root"),
            artifact_path=_require_absolute_path(raw["artifact_path"], label="artifact_path"),
            upstream_revision=_require_sha(
                raw["upstream_revision"], label="llama_cpp.upstream_revision", pattern=_SHA1_RE
            ),
            expected_build_info=_require_nonempty_string(
                raw["expected_build_info"], label="llama_cpp.expected_build_info"
            ),
            expected_model_alias=_require_nonempty_string(
                raw["expected_model_alias"], label="llama_cpp.expected_model_alias"
            ),
            artifact_sha256=_require_sha(
                raw["artifact_sha256"], label="llama_cpp.artifact_sha256", pattern=_SHA256_RE
            ),
            runtime=_require_nonempty_string(raw["runtime"], label="llama_cpp.runtime"),
            model_runner=_require_nonempty_string(
                raw["model_runner"], label="llama_cpp.model_runner"
            ),
            context=_require_positive_int(raw["context"], label="llama_cpp.context"),
            slots=_require_positive_int(raw["slots"], label="llama_cpp.slots"),
            port=port,
            gpu_layers=gpu_layers,
            effective_gpu_reservation=float(reservation),
            capacity_evidence=dict(capacity),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "llama_cpp_root": str(self.llama_cpp_root),
            "artifact_path": str(self.artifact_path),
            "upstream_revision": self.upstream_revision,
            "expected_build_info": self.expected_build_info,
            "expected_model_alias": self.expected_model_alias,
            "artifact_sha256": self.artifact_sha256,
            "runtime": self.runtime,
            "model_runner": self.model_runner,
            "context": self.context,
            "slots": self.slots,
            "port": self.port,
            "gpu_layers": self.gpu_layers,
            "effective_gpu_reservation": self.effective_gpu_reservation,
            "capacity_evidence": self.capacity_evidence,
        }


@dataclass(frozen=True, slots=True)
class CampaignQuestion:
    question_id: str
    prompt: str
    content_fingerprint: str
    session_id: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CampaignQuestion:
        _require_exact_keys(raw, _QUESTION_KEYS, label="campaign question")
        question_id = _require_nonempty_string(raw["question_id"], label="question_id")
        prompt = _require_nonempty_string(raw["prompt"], label="prompt")
        content_fingerprint = _require_sha(
            raw["content_fingerprint"],
            label="content_fingerprint",
            pattern=_FINGERPRINT_RE,
        )
        session_id = _require_nonempty_string(raw["session_id"], label="session_id")
        durable = DurableQuestion.from_content(
            question_id=question_id,
            content=prompt,
            session_id=session_id,
        )
        if durable.content_fingerprint != content_fingerprint:
            raise CampaignCarriageError(
                f"question {question_id!r} content fingerprint does not match prompt"
            )
        return cls(question_id, prompt, content_fingerprint, session_id)

    def to_durable_question(self) -> DurableQuestion:
        return DurableQuestion.from_content(
            question_id=self.question_id,
            content=self.prompt,
            session_id=self.session_id,
        )


@dataclass(frozen=True, slots=True)
class CampaignAxis:
    axis_id: str
    case: Mapping[str, Any]
    manifest: Mapping[str, Any]
    identity: Mapping[str, Any]
    questions: tuple[CampaignQuestion, ...]
    run_mode: Literal["fresh_run", "exact_infrastructure_resume"]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CampaignAxis:
        _require_exact_keys(raw, _AXIS_KEYS, label="campaign axis")
        axis_id = _require_nonempty_string(raw["axis_id"], label="axis_id")
        if axis_id in {".", ".."} or "/" in axis_id or "\\" in axis_id:
            raise CampaignCarriageError("axis_id must be a single safe path component")
        case = validate_case(_require_mapping(raw["case"], label=f"axis {axis_id} case"))
        manifest = validate_manifest(
            _require_mapping(raw["manifest"], label=f"axis {axis_id} manifest")
        )
        identity = _require_mapping(raw["identity"], label=f"axis {axis_id} identity")
        FrozenExperimentIdentity.from_mapping(identity)
        questions_raw = raw["questions"]
        if not isinstance(questions_raw, list) or not questions_raw:
            raise CampaignCarriageError(f"axis {axis_id!r} must contain questions")
        questions = tuple(
            CampaignQuestion.from_mapping(
                _require_mapping(item, label=f"axis {axis_id} question")
            )
            for item in questions_raw
        )
        ids = [question.question_id for question in questions]
        if len(ids) != len(set(ids)):
            raise CampaignCarriageError(f"axis {axis_id!r} contains duplicate question ids")
        run_mode = raw["run_mode"]
        if run_mode not in _RUN_MODES:
            raise CampaignCarriageError(
                f"axis {axis_id!r} run_mode must be fresh_run or exact_infrastructure_resume"
            )
        return cls(axis_id, case, manifest, identity, questions, cast(Any, run_mode))


@dataclass(frozen=True, slots=True)
class CampaignDescriptor:
    execution_freeze: Mapping[str, Any]
    artifact_root: Path
    llama_cpp: LlamaCppLaunchSpec
    hindsight_health: HindsightHealthAttestation
    axes: tuple[CampaignAxis, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CampaignDescriptor:
        _require_exact_keys(raw, _DESCRIPTOR_KEYS, label="campaign descriptor")
        if raw["format_version"] != CAMPAIGN_FORMAT_VERSION:
            raise CampaignCarriageError("unsupported campaign descriptor format_version")
        if raw["target"] != CAMPAIGN_TARGET:
            raise CampaignCarriageError(
                f"campaign descriptor target must be {CAMPAIGN_TARGET!r}"
            )
        execution_freeze = _require_mapping(raw["execution_freeze"], label="execution_freeze")
        readiness = validate_launch_readiness(execution_freeze)
        if readiness["phase"] != "execution_freeze":
            raise CampaignCarriageError("campaign requires an execution_freeze plan")
        carriage = _require_mapping(readiness["physical_carriage"], label="physical_carriage")
        expected_carriage = {
            "target": CAMPAIGN_TARGET,
            "backend": "llama.cpp",
            "resource_key": "llama-cpp:local-gpu",
            "registered": True,
        }
        if any(carriage.get(key) != value for key, value in expected_carriage.items()):
            raise CampaignCarriageError(
                "execution_freeze physical_carriage must identify the campaign target"
            )
        if readiness["status"] != "EXECUTION_FROZEN":
            raise CampaignCarriageError("campaign requires status EXECUTION_FROZEN")
        axes_raw = raw["axes"]
        if not isinstance(axes_raw, list) or len(axes_raw) < 2:
            raise CampaignCarriageError("campaign requires at least two axes")
        axes = tuple(
            CampaignAxis.from_mapping(_require_mapping(item, label="campaign axis"))
            for item in axes_raw
        )
        axis_ids = [axis.axis_id for axis in axes]
        if len(axis_ids) != len(set(axis_ids)):
            raise CampaignCarriageError("campaign axes must have unique axis_id values")
        frozen_case_by_id = {
            str(item["axis_id"]): item for item in readiness["release_cases"]
        }
        for axis in axes:
            frozen_case = frozen_case_by_id.get(axis.axis_id)
            if frozen_case is None:
                raise CampaignCarriageError(
                    f"axis {axis.axis_id!r} is not present in the execution freeze"
                )
            if _canonical_json(axis.case) != _canonical_json(frozen_case["case"]):
                raise CampaignCarriageError(f"axis {axis.axis_id!r} case drifted from execution freeze")
            if _canonical_json(axis.manifest) != _canonical_json(frozen_case["manifest"]):
                raise CampaignCarriageError(
                    f"axis {axis.axis_id!r} manifest drifted from execution freeze"
                )
        if set(frozen_case_by_id) != set(axis_ids):
            raise CampaignCarriageError("campaign axes must cover every frozen release case exactly")
        return cls(
            execution_freeze=dict(execution_freeze),
            artifact_root=_require_absolute_path(raw["artifact_root"], label="artifact_root"),
            llama_cpp=LlamaCppLaunchSpec.from_mapping(
                _require_mapping(raw["llama_cpp"], label="llama_cpp")
            ),
            hindsight_health=HindsightHealthAttestation.from_mapping(
                _require_mapping(raw["hindsight_health"], label="hindsight_health")
            ),
            axes=axes,
        )

    @classmethod
    def from_path(cls, path: Path) -> CampaignDescriptor:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignCarriageError(f"cannot read campaign descriptor {path}: {exc}") from exc
        return cls.from_mapping(_require_mapping(raw, label="campaign descriptor"))

    @property
    def fingerprint(self) -> str:
        return _sha256_json(
            {
                "format_version": CAMPAIGN_FORMAT_VERSION,
                "target": CAMPAIGN_TARGET,
                "execution_freeze": self.execution_freeze,
                "artifact_root": str(self.artifact_root),
                "llama_cpp": self.llama_cpp.to_mapping(),
                "hindsight_health": self.hindsight_health.value,
                "axes": [
                    {
                        "axis_id": axis.axis_id,
                        "case": axis.case,
                        "manifest": axis.manifest,
                        "identity": axis.identity,
                        "questions": [
                            {
                                "question_id": question.question_id,
                                "prompt": question.prompt,
                                "content_fingerprint": question.content_fingerprint,
                                "session_id": question.session_id,
                            }
                            for question in axis.questions
                        ],
                        "run_mode": axis.run_mode,
                    }
                    for axis in self.axes
                ],
            }
        )


@dataclass(frozen=True, slots=True)
class ParticipantExecutionContext:
    """The only input made available to an A/C/D participant hook."""

    axis_id: str
    case: Mapping[str, Any]
    manifest: Mapping[str, Any]
    question: DurableQuestion
    participant_slot: str
    participant_identity: Mapping[str, Any]
    frozen_identity: FrozenExperimentIdentity
    live_attestation: LiveLaunchAdmissionAttestation


@dataclass(frozen=True, slots=True)
class ParticipantExecutionResult:
    """Typed participant output; raw executables and replay directives are absent."""

    slot: str
    observation: Mapping[str, Any]
    request_evidence: tuple[Mapping[str, Any], ...] = ()
    semantic_generation_count: int = 0
    answer_model_generation_count: int = 0
    judge_call_count: int = 0

    def __post_init__(self) -> None:
        if self.slot not in SLOTS:
            raise CampaignCarriageError(f"unknown participant slot {self.slot!r}")
        if (
            isinstance(self.semantic_generation_count, bool)
            or not isinstance(self.semantic_generation_count, int)
            or isinstance(self.answer_model_generation_count, bool)
            or not isinstance(self.answer_model_generation_count, int)
            or isinstance(self.judge_call_count, bool)
            or not isinstance(self.judge_call_count, int)
            or self.semantic_generation_count < 0
            or self.answer_model_generation_count < 0
            or self.judge_call_count < 0
        ):
            raise CampaignCarriageError("participant counters cannot be negative")
        for evidence in self.request_evidence:
            if not isinstance(evidence, Mapping):
                raise CampaignCarriageError("request_evidence entries must be objects")


ParticipantExecutor = Callable[
    [ParticipantExecutionContext],
    ParticipantExecutionResult | Awaitable[ParticipantExecutionResult],
]


@dataclass(frozen=True, slots=True)
class ParticipantExecutors:
    """Explicit A/C/D hooks, with the simple baseline optional by frozen plan."""

    same_model_direct: ParticipantExecutor
    serious_comparator: ParticipantExecutor
    relaylm_exact_rc: ParticipantExecutor
    simple_baseline: ParticipantExecutor | None = None

    def for_slot(self, slot: str) -> ParticipantExecutor | None:
        if slot == "same_model_direct":
            return self.same_model_direct
        if slot == "simple_baseline":
            return self.simple_baseline
        if slot == "serious_comparator":
            return self.serious_comparator
        if slot == "relaylm_exact_rc":
            return self.relaylm_exact_rc
        raise CampaignCarriageError(f"unknown participant slot {slot!r}")


class LiveLaunchSession(Protocol):
    """Owned llama.cpp session with one fresh attestation and deterministic cleanup."""

    launch_count: int

    def attest(self) -> LiveLaunchAdmissionAttestation | Mapping[str, Any]:
        ...

    def cleanup(self) -> Mapping[str, Any]:
        ...


LiveLaunchFactory = Callable[[LlamaCppLaunchSpec, Path], LiveLaunchSession]
CurrentAuthorityReader = Callable[[], Mapping[str, Any]]


def _normalise_cleanup(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    _require_exact_keys(raw, _CLEANUP_KEYS, label="owned cleanup receipt")
    if raw["all_owned_processes_terminated"] is not True:
        raise CampaignCarriageError("owned cleanup did not terminate every owned process")
    touched = raw["external_processes_touched"]
    if touched != 0:
        raise CampaignCarriageError("owned cleanup touched an external process")
    errors = raw["errors"]
    if not isinstance(errors, list) or errors:
        raise CampaignCarriageError("owned cleanup reported errors")
    return dict(raw)


async def _await_result(value: ParticipantExecutionResult | Awaitable[ParticipantExecutionResult]) -> ParticipantExecutionResult:
    if hasattr(value, "__await__"):
        return await cast(Awaitable[ParticipantExecutionResult], value)
    return value


def _authority_matches(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> None:
    if observed.get("status") != "CURRENT_AUTHORITY_CONFIRMED":
        raise CampaignCarriageError("current repository authority was not confirmed")
    for key in ("repository_head", "repository_tree", "branch"):
        if key in expected and observed.get(key) != expected[key]:
            raise CampaignCarriageError(f"current authority drifted at {key}")


class CampaignController:
    """Run the bounded campaign after a scientific owner supplies typed hooks."""

    def __init__(
        self,
        descriptor: CampaignDescriptor,
        *,
        live_launch_factory: LiveLaunchFactory,
        hindsight_probe: HindsightHealthProbe,
        participant_executors: ParticipantExecutors,
        current_authority_reader: CurrentAuthorityReader,
    ) -> None:
        self.descriptor = descriptor
        self.live_launch_factory = live_launch_factory
        self.hindsight_probe = hindsight_probe
        self.participant_executors = participant_executors
        self.current_authority_reader = current_authority_reader

    async def run(self) -> Mapping[str, Any]:
        descriptor = self.descriptor
        health = verify_hindsight_health(descriptor.hindsight_health, self.hindsight_probe)
        root = descriptor.artifact_root
        root.mkdir(parents=True, exist_ok=True)
        if any(axis.run_mode == "fresh_run" for axis in descriptor.axes) and any(root.iterdir()):
            raise CampaignCarriageError(
                "fresh campaign execution requires an empty artifact root"
            )

        session: LiveLaunchSession | None = None
        cleanup: Mapping[str, Any] | None = None
        axis_receipts: list[Mapping[str, Any]] = []
        counters = {
            "semantic_generation_count": 0,
            "benchmark_question_count": 0,
            "answer_model_generation_count": 0,
            "judge_call_count": 0,
            "scientific_durable_run_completion_count": 0,
        }
        try:
            session = self.live_launch_factory(descriptor.llama_cpp, root / "live")
            if session.launch_count != 1:
                raise CampaignCarriageError("campaign requires exactly one owned llama.cpp launch")
            raw_attestation = session.attest()
            if isinstance(raw_attestation, LiveLaunchAdmissionAttestation):
                live_attestation = raw_attestation
            else:
                live_attestation = LiveLaunchAdmissionAttestation.from_mapping(
                    _require_mapping(raw_attestation, label="live launch attestation")
                )

            for axis in descriptor.axes:
                current_authority = _require_mapping(
                    self.current_authority_reader(), label="current repository authority"
                )
                expected_authority = _require_mapping(
                    axis.identity["authority"], label=f"axis {axis.axis_id} authority"
                )
                _authority_matches(expected_authority, current_authority)
                try:
                    frozen_identity = freeze_experiment_identity(
                        identity=axis.identity,
                        live_attestation=live_attestation,
                    )
                except ExternalQualificationError as exc:
                    raise CampaignCarriageError(str(exc)) from exc
                axis_root = root / axis.axis_id
                durable = DurableQuestionRun.open(
                    artifact_root=axis_root,
                    identity=frozen_identity,
                    questions=tuple(question.to_durable_question() for question in axis.questions),
                    mode=axis.run_mode,
                )
                axis_question_count = 0
                while True:
                    question = durable.next_question()
                    if question is None:
                        break
                    question = durable.begin_question(question.question_id)
                    participant_records: list[Mapping[str, Any]] = []
                    request_evidence: list[Mapping[str, Any]] = []
                    participant_plans = {
                        str(plan["slot"]): plan
                        for plan in axis.manifest["participants"]
                    }
                    for slot in SLOTS:
                        participant_plan = participant_plans[slot]
                        participant_identity = participant_plan["identity"]
                        if participant_identity is None:
                            participant_records.append(
                                {
                                    "slot": slot,
                                    "status": "omitted",
                                    "observation": None,
                                    "omission_reason": participant_plan["omission_reason"],
                                }
                            )
                            continue
                        executor = self.participant_executors.for_slot(slot)
                        if executor is None:
                            raise CampaignCarriageError(
                                f"frozen plan enables {slot} but no typed executor is bound"
                            )
                        context = ParticipantExecutionContext(
                            axis_id=axis.axis_id,
                            case=axis.case,
                            manifest=axis.manifest,
                            question=question,
                            participant_slot=slot,
                            participant_identity=_require_mapping(
                                participant_identity,
                                label=f"{axis.axis_id}.{slot} identity",
                            ),
                            frozen_identity=frozen_identity,
                            live_attestation=live_attestation,
                        )
                        result = await _await_result(executor(context))
                        if not isinstance(result, ParticipantExecutionResult):
                            raise CampaignCarriageError(
                                f"executor for {slot} must return ParticipantExecutionResult"
                            )
                        if result.slot != slot:
                            raise CampaignCarriageError(
                                f"executor returned slot {result.slot!r} for {slot!r}"
                            )
                        observation = validate_observation(result.observation)
                        participant_records.append(
                            {
                                "slot": slot,
                                "status": "observed",
                                "observation": observation,
                            }
                        )
                        request_evidence.extend(result.request_evidence)
                        counters["semantic_generation_count"] += result.semantic_generation_count
                        counters["answer_model_generation_count"] += result.answer_model_generation_count
                        counters["judge_call_count"] += result.judge_call_count
                    durable.commit_question(
                        question_id=question.question_id,
                        result={
                            "format_version": CAMPAIGN_FORMAT_VERSION,
                            "axis_id": axis.axis_id,
                            "question_id": question.question_id,
                            "participants": participant_records,
                        },
                        request_evidence=request_evidence,
                    )
                    counters["benchmark_question_count"] += 1
                    axis_question_count += 1
                durable.mark_completed()
                counters["scientific_durable_run_completion_count"] += 1
                axis_receipts.append(
                    {
                        "axis_id": axis.axis_id,
                        "frozen_identity_fingerprint": frozen_identity.fingerprint,
                        "durable_root": str(axis_root),
                        "question_count": axis_question_count,
                        "status": "completed",
                    }
                )
            status = "COMPLETED"
        finally:
            if session is not None:
                cleanup = _normalise_cleanup(
                    _require_mapping(session.cleanup(), label="owned cleanup receipt")
                )

        if cleanup is None:
            raise CampaignCarriageError("campaign did not create an owned runtime session")
        return {
            "format_version": CAMPAIGN_FORMAT_VERSION,
            "target": CAMPAIGN_TARGET,
            "status": status,
            "campaign_fingerprint": descriptor.fingerprint,
            "readiness_fingerprint": validate_launch_readiness(
                descriptor.execution_freeze
            )["fingerprint"],
            "hindsight_health_fingerprint": health.fingerprint,
            "axis_receipts": axis_receipts,
            "counters": counters,
            "llama_server_launch_count": 1,
            "cleanup": cleanup,
            "SCIENTIFIC_SPEND": (
                "CONSUMED"
                if any(
                    counters[key]
                    for key in (
                        "semantic_generation_count",
                        "answer_model_generation_count",
                        "judge_call_count",
                    )
                )
                else "UNSPENT"
            ),
        }


def run_campaign(
    descriptor: CampaignDescriptor,
    *,
    live_launch_factory: LiveLaunchFactory,
    hindsight_probe: HindsightHealthProbe,
    participant_executors: ParticipantExecutors,
    current_authority_reader: CurrentAuthorityReader,
) -> Mapping[str, Any]:
    """Synchronous bridge for the queue-owned typed campaign controller."""

    return asyncio.run(
        CampaignController(
            descriptor,
            live_launch_factory=live_launch_factory,
            hindsight_probe=hindsight_probe,
            participant_executors=participant_executors,
            current_authority_reader=current_authority_reader,
        ).run()
    )


class LlamaCppLiveLaunchSession:
    """Fixed local llama.cpp launch/session used by a future scientific owner."""

    _READY_TIMEOUT_SECONDS = 120.0

    def __init__(self, spec: LlamaCppLaunchSpec, evidence_root: Path) -> None:
        self.spec = spec
        self.evidence_root = evidence_root
        self.process: subprocess.Popen[bytes] | None = None
        self.launch_count = 0
        self._cleanup_receipt: Mapping[str, Any] | None = None
        self._version_output = ""

    def _server_binary(self) -> Path:
        binary = self.spec.llama_cpp_root / "build" / "bin" / "llama-server"
        if binary.name != "llama-server":
            raise CampaignCarriageError("campaign server binary path is not llama-server")
        if not binary.is_file() or not binary.stat().st_mode & 0o111:
            raise CampaignCarriageError(f"llama-server is not executable: {binary}")
        return binary

    def _verify_source_and_artifact(self, binary: Path) -> None:
        clean = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=self.spec.llama_cpp_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if clean.returncode != 0 or clean.stdout.strip():
            raise CampaignCarriageError("llama.cpp source checkout is not clean")
        source = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.spec.llama_cpp_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if source.returncode != 0 or source.stdout.strip() != self.spec.upstream_revision:
            raise CampaignCarriageError("llama.cpp source revision drifted from the frozen plan")
        if not self.spec.artifact_path.is_file():
            raise CampaignCarriageError(f"release artifact is not a file: {self.spec.artifact_path}")
        digest = hashlib.sha256(self.spec.artifact_path.read_bytes()).hexdigest()
        if digest != self.spec.artifact_sha256:
            raise CampaignCarriageError("release artifact digest drifted from the frozen plan")
        version = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if version.returncode != 0 or not version.stdout.strip():
            raise CampaignCarriageError("llama-server version probe failed")
        self._version_output = version.stdout.strip()
        if self.spec.expected_build_info not in self._version_output:
            raise CampaignCarriageError("llama-server build identity drifted from the frozen plan")

    def _fixed_launch_arguments(self, binary: Path, log_path: Path) -> list[str]:
        return [
            str(binary),
            "-m",
            str(self.spec.artifact_path),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.spec.port),
            "-c",
            str(self.spec.context),
            "-np",
            str(self.spec.slots),
            "-ngl",
            str(self.spec.gpu_layers),
            "--no-context-shift",
            "--log-file",
            str(log_path),
        ]

    def _port_is_free(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", self.spec.port))
            except OSError:
                return False
        return True

    def _wait_for_health(self, client: httpx.Client) -> None:
        deadline = time.monotonic() + self._READY_TIMEOUT_SECONDS
        url = f"http://127.0.0.1:{self.spec.port}/health"
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise CampaignCarriageError("owned llama-server exited before health")
            try:
                response = client.get(url)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise CampaignCarriageError("llama-server health did not become ready")

    def _probe_runtime(self) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            self._wait_for_health(client)
            props_response = client.get(f"http://127.0.0.1:{self.spec.port}/props")
            slots_response = client.get(f"http://127.0.0.1:{self.spec.port}/slots")
            if props_response.status_code != 200 or slots_response.status_code != 200:
                raise CampaignCarriageError("llama-server runtime probes were not HTTP-200")
            try:
                props = _require_mapping(props_response.json(), label="llama props")
                slots_value = slots_response.json()
            except (ValueError, TypeError) as exc:
                raise CampaignCarriageError("llama-server runtime probes were not JSON") from exc
            if not isinstance(slots_value, list):
                raise CampaignCarriageError("llama-server slots probe must be a list")
            slots = [
                _require_mapping(item, label="llama slot")
                for item in slots_value
            ]
            return props, slots

    def _probe_gpu(self) -> Mapping[str, Any]:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise CampaignCarriageError("fresh nvidia-smi GPU attestation failed")
        rows = []
        for line in result.stdout.splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) != 4:
                raise CampaignCarriageError("nvidia-smi GPU attestation shape changed")
            rows.append(
                {
                    "name": fields[0],
                    "driver_version": fields[1],
                    "memory_total_mib": fields[2],
                    "memory_used_mib": fields[3],
                }
            )
        if len(rows) != 1:
            raise CampaignCarriageError("campaign requires exactly one freshly attested GPU")
        return rows[0]

    def attest(self) -> LiveLaunchAdmissionAttestation:
        if self.process is None or self.process.poll() is not None:
            raise CampaignCarriageError("cannot attest a non-running owned llama-server")
        from relaylm.actual_model_llama_cpp import attest_llama_cpp_runtime

        props, slots = self._probe_runtime()
        runtime_identity = attest_llama_cpp_runtime(
            props=props,
            slots=slots,
            upstream_revision=self.spec.upstream_revision,
            expected_build_info=self.spec.expected_build_info,
            expected_model_alias=self.spec.expected_model_alias,
            expected_model_path=str(self.spec.artifact_path),
            artifact_sha256=self.spec.artifact_sha256,
            context_shift_enabled=False,
        )
        gpu = self._probe_gpu()
        expected_gpu = self.spec.capacity_evidence.get("gpu_identity")
        if expected_gpu is not None and expected_gpu != gpu:
            raise CampaignCarriageError("fresh GPU identity drifted from the frozen capacity plan")
        if runtime_identity.context_limit != self.spec.context:
            raise CampaignCarriageError("fresh runtime context drifted from the frozen plan")
        if runtime_identity.total_slots != self.spec.slots:
            raise CampaignCarriageError("fresh runtime slots drifted from the frozen plan")
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        launch_ref = self.evidence_root / "runtime-attestation.json"
        ownership_ref = self.evidence_root / "runtime-ownership.json"
        if launch_ref.exists() or ownership_ref.exists():
            raise CampaignCarriageError("live evidence root is not fresh")
        launch_payload = {
            "format_version": 1,
            "kind": "llama_cpp_live_launch_attestation",
            "runtime": self.spec.runtime,
            "model_runner": self.spec.model_runner,
            "version_output": self._version_output,
            "runtime_identity": {
                "upstream_revision": runtime_identity.upstream_revision,
                "build_info": runtime_identity.build_info,
                "model_alias": runtime_identity.model_alias,
                "model_path": runtime_identity.model_path,
                "model_ftype": runtime_identity.model_ftype,
                "artifact_sha256": runtime_identity.artifact_sha256,
                "chat_template_sha256": runtime_identity.chat_template_sha256,
                "context_limit": runtime_identity.context_limit,
                "total_slots": runtime_identity.total_slots,
                "context_shift_enabled": runtime_identity.context_shift_enabled,
            },
            "gpu": gpu,
            "capacity_evidence": self.spec.capacity_evidence,
        }
        launch_ref.write_text(_canonical_json(launch_payload) + "\n", encoding="utf-8")
        ownership_payload = {
            "format_version": 1,
            "kind": "owned_llama_cpp_runtime",
            "pid": self.process.pid,
            "port": self.spec.port,
            "binary": str(self._server_binary()),
            "argv_sha256": hashlib.sha256(
                _canonical_json(self._fixed_launch_arguments(self._server_binary(), self.evidence_root / "llama-server.log")).encode("utf-8")
            ).hexdigest(),
        }
        ownership_ref.write_text(_canonical_json(ownership_payload) + "\n", encoding="utf-8")
        return LiveLaunchAdmissionAttestation.from_mapping(
            {
                "backend": "llama.cpp",
                "runtime": self.spec.runtime,
                "model_runner": self.spec.model_runner,
                "effective_gpu_reservation": self.spec.effective_gpu_reservation,
                "admitted_context": self.spec.context,
                "capacity_evidence": self.spec.capacity_evidence,
                "launch_evidence_reference": str(launch_ref),
                "runtime_ownership_evidence_reference": str(ownership_ref),
            }
        )

    @classmethod
    def start(cls, spec: LlamaCppLaunchSpec, evidence_root: Path) -> LlamaCppLiveLaunchSession:
        session = cls(spec, evidence_root)
        binary = session._server_binary()
        session._verify_source_and_artifact(binary)
        if not session._port_is_free():
            raise CampaignCarriageError("fixed llama-server port is already occupied")
        try:
            evidence_root.mkdir(parents=True, exist_ok=True)
            existing = tuple(evidence_root.iterdir())
        except OSError as exc:
            raise CampaignCarriageError(f"cannot prepare live evidence root: {exc}") from exc
        if existing:
            indices = [
                int(match.group(1))
                for path in existing
                if path.is_dir()
                for match in [re.fullmatch(r"launch-(\d{4})", path.name)]
                if match is not None
            ]
            next_index = max(indices, default=0) + 1
            selected_root = evidence_root / f"launch-{next_index:04d}"
            try:
                selected_root.mkdir()
            except OSError as exc:
                raise CampaignCarriageError(
                    f"cannot create fresh live evidence root: {exc}"
                ) from exc
            session.evidence_root = selected_root
        log_path = session.evidence_root / "llama-server.log"
        try:
            session.process = subprocess.Popen(
                session._fixed_launch_arguments(binary, log_path),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise CampaignCarriageError(f"owned llama-server launch failed: {exc}") from exc
        session.launch_count = 1
        return session

    def cleanup(self) -> Mapping[str, Any]:
        if self._cleanup_receipt is not None:
            return self._cleanup_receipt
        errors: list[str] = []
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    errors.append("owned llama-server did not terminate")
        receipt = {
            "all_owned_processes_terminated": not errors
            and (self.process is None or self.process.poll() is not None),
            "external_processes_touched": 0,
            "errors": errors,
        }
        self._cleanup_receipt = receipt
        return receipt


def start_llama_cpp_session(spec: LlamaCppLaunchSpec, evidence_root: Path) -> LiveLaunchSession:
    """Fixed factory for the one allowed local llama.cpp runtime launch."""

    return LlamaCppLiveLaunchSession.start(spec, evidence_root)


def validate_zero_semantic_carriage(descriptor: CampaignDescriptor) -> Mapping[str, Any]:
    """Validate the campaign shape without probing, launching, or generating."""

    return {
        "format_version": CAMPAIGN_FORMAT_VERSION,
        "target": CAMPAIGN_TARGET,
        "status": "FULL_CAMPAIGN_CARRIAGE_READY",
        "campaign_fingerprint": descriptor.fingerprint,
        "readiness_fingerprint": validate_launch_readiness(
            descriptor.execution_freeze
        )["fingerprint"],
        "hindsight_health_disposition": "ZERO_SEMANTIC_ATTESTATION_REQUIRED_AT_EXECUTION",
        "live_attestation_disposition": "REQUIRED_BEFORE_FROZEN_IDENTITY",
        "semantic_generation_count": 0,
        "benchmark_question_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
        "llama_server_launch_count": 0,
        "scientific_durable_run_completion_count": 0,
        "SCIENTIFIC_SPEND": "UNSPENT",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the bounded v1 external-qualification campaign carriage"
    )
    parser.add_argument("--plan", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        descriptor = CampaignDescriptor.from_path(
            _parser().parse_args(argv).plan
        )
        print(json.dumps(validate_zero_semantic_carriage(descriptor), sort_keys=True))
        return 0
    except (CampaignCarriageError, ExternalQualificationError, ExternalQualificationReadinessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
