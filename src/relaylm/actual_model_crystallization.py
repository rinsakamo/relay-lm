from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from relaylm.crystallization import (
    CrystallizationInput,
    CrystallizationOutput,
    Crystallizer,
    run_crystallization,
)
from relaylm.events import Event
from relaylm.state import StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import CandidateDecision


ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION = 1
ACTUAL_MODEL_CRYSTALLIZATION_REVIEW_FORMAT_VERSION = 1
CRYSTALLIZATION_QUALITY_RUBRIC_VERSION = "actual-model-crystallization-quality-v1"

CrystallizationQualityAxis = Literal[
    "durable_information_selection",
    "state_taxonomy_key_normalization",
    "transient_durable_discipline",
    "correction_supersession_preservation",
    "temporal_provenance_fidelity",
    "memory_organization_readability",
    "semantic_stability",
]
CrystallizationQualityOutcome = Literal["pass", "fail", "not_rated"]

CRYSTALLIZATION_QUALITY_AXES: tuple[CrystallizationQualityAxis, ...] = (
    "durable_information_selection",
    "state_taxonomy_key_normalization",
    "transient_durable_discipline",
    "correction_supersession_preservation",
    "temporal_provenance_fidelity",
    "memory_organization_readability",
    "semantic_stability",
)


class ActualModelCrystallizationArtifactError(RuntimeError):
    """Crystallization evidence violated immutable artifact rules."""


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationManifest:
    """Exact runtime/model identity for one off-turn crystallization evaluation pass."""

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
    evaluation_contract_version: str
    condition_id: str
    max_events: int
    seed: int | None = None
    replicate_id: str = "0"
    format_version: int = ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION:
            raise ValueError(
                "unsupported actual-model crystallization format_version: "
                f"{self.format_version}"
            )
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
            "evaluation_contract_version",
            "condition_id",
            "replicate_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if isinstance(self.effective_context_window, bool) or not isinstance(
            self.effective_context_window, int
        ):
            raise TypeError("effective_context_window must be an integer")
        if self.effective_context_window <= 0:
            raise ValueError("effective_context_window must be positive")
        if isinstance(self.max_events, bool) or not isinstance(self.max_events, int):
            raise TypeError("max_events must be an integer")
        if self.max_events < 0:
            raise ValueError("max_events must not be negative")
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise TypeError("seed must be an integer when provided")
        keys = tuple(key for key, _ in self.decoding_configuration)
        if len(set(keys)) != len(keys):
            raise ValueError("decoding_configuration keys must be unique")
        for key, value in self.decoding_configuration:
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    "decoding_configuration keys must be non-empty strings"
                )
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("decoding_configuration values must be finite")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "execution_kind": "off_turn_crystallization",
            "relaylm_commit": self.relaylm_commit,
            "character_fixture": {
                "id": self.character_fixture_id,
                "revision": self.character_fixture_revision,
            },
            "provider": {
                "identity": self.provider_identity,
                "adapter": self.adapter_identity,
            },
            "model_artifact": self.model_artifact,
            "tokenizer_identity": self.tokenizer_identity,
            "effective_context_window": self.effective_context_window,
            "decoding_configuration": dict(self.decoding_configuration),
            "seed": self.seed,
            "structured_output_schema_version": self.structured_output_schema_version,
            "evaluation_contract_version": self.evaluation_contract_version,
            "condition_id": self.condition_id,
            "max_events": self.max_events,
            "replicate_id": self.replicate_id,
        }


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationCase:
    """Provider-neutral semantic purpose for one crystallization evidence pass."""

    case_id: str
    version: str

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must not be empty")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("case version must not be empty")

    def to_mapping(self) -> dict[str, object]:
        return {"id": self.case_id, "version": self.version}


@dataclass(frozen=True, slots=True)
class CrystallizationInputEvidence:
    """Exact CrystallizationInput observed by the recording wrapper."""

    identity: dict[str, object]
    state: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
    prior_memory: str | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "state": list(self.state),
            "events": list(self.events),
            "prior_memory": self.prior_memory,
        }


@dataclass(frozen=True, slots=True)
class RawCrystallizationObservation:
    """Raw semantic output emitted by the crystallizer before validation."""

    memory_markdown: str
    state_candidates: tuple[dict[str, object], ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "memory_markdown": self.memory_markdown,
            "state_candidates": list(self.state_candidates),
        }


@dataclass(frozen=True, slots=True)
class DeterministicCrystallizationObservation:
    """Existing RelayLM decisions and durable results after the raw output."""

    state_decisions: tuple[dict[str, object], ...]
    resulting_state: tuple[dict[str, object], ...]
    memory_changed: bool
    resulting_memory: str | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "state_decisions": list(self.state_decisions),
            "resulting_state": list(self.resulting_state),
            "memory_changed": self.memory_changed,
            "resulting_memory": self.resulting_memory,
        }


@dataclass(frozen=True, slots=True)
class CrystallizationQualityObservation:
    axis: CrystallizationQualityAxis
    outcome: CrystallizationQualityOutcome
    note: str | None = None

    def __post_init__(self) -> None:
        if self.axis not in CRYSTALLIZATION_QUALITY_AXES:
            raise ValueError(f"unsupported crystallization quality axis: {self.axis}")
        if self.outcome not in {"pass", "fail", "not_rated"}:
            raise ValueError(
                f"unsupported crystallization quality outcome: {self.outcome}"
            )
        if self.note is not None and not isinstance(self.note, str):
            raise TypeError("crystallization quality note must be a string or None")

    def to_mapping(self) -> dict[str, object]:
        return {"axis": self.axis, "outcome": self.outcome, "note": self.note}


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationEvidence:
    run_id: str
    manifest: ActualModelCrystallizationManifest
    case: ActualModelCrystallizationCase
    input: CrystallizationInputEvidence
    raw_model: RawCrystallizationObservation
    deterministic: DeterministicCrystallizationObservation
    product_quality: tuple[CrystallizationQualityObservation, ...] = field(
        default_factory=tuple
    )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": ACTUAL_MODEL_CRYSTALLIZATION_EVIDENCE_FORMAT_VERSION,
            "run_id": self.run_id,
            "manifest": self.manifest.to_mapping(),
            "case": self.case.to_mapping(),
            "input": self.input.to_mapping(),
            "raw_model": self.raw_model.to_mapping(),
            "deterministic_relay": self.deterministic.to_mapping(),
            "product_quality": [item.to_mapping() for item in self.product_quality],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationReview:
    """Citable bounded product-quality review; never a composite score."""

    reviewer_identity: str
    evidence_run_ids: tuple[str, ...]
    case_id: str
    case_version: str
    observations: tuple[CrystallizationQualityObservation, ...]
    rubric_version: str = CRYSTALLIZATION_QUALITY_RUBRIC_VERSION
    format_version: int = ACTUAL_MODEL_CRYSTALLIZATION_REVIEW_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_CRYSTALLIZATION_REVIEW_FORMAT_VERSION:
            raise ValueError(
                "unsupported actual-model crystallization review format_version: "
                f"{self.format_version}"
            )
        for name in ("reviewer_identity", "case_id", "case_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.rubric_version != CRYSTALLIZATION_QUALITY_RUBRIC_VERSION:
            raise ValueError("unsupported crystallization quality rubric_version")
        if not self.evidence_run_ids or not all(
            isinstance(item, str) and item.strip() for item in self.evidence_run_ids
        ):
            raise ValueError("evidence_run_ids must contain non-empty run IDs")
        if len(set(self.evidence_run_ids)) != len(self.evidence_run_ids):
            raise ValueError("evidence_run_ids must not contain duplicates")
        axes = tuple(item.axis for item in self.observations)
        if axes != CRYSTALLIZATION_QUALITY_AXES:
            raise ValueError(
                "review must contain the exact crystallization quality axes once and in canonical order"
            )

    @property
    def review_id(self) -> str:
        return stable_actual_model_crystallization_review_id(self)

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "rubric_version": self.rubric_version,
            "reviewer_identity": self.reviewer_identity,
            "evidence_run_ids": list(self.evidence_run_ids),
            "case": {"id": self.case_id, "version": self.case_version},
            "observations": [item.to_mapping() for item in self.observations],
        }


class _RecordingCrystallizer:
    def __init__(self, delegate: Crystallizer) -> None:
        self.delegate = delegate
        self.inputs: list[CrystallizationInput] = []
        self.outputs: list[CrystallizationOutput] = []

    async def generate(
        self, crystallization_input: CrystallizationInput
    ) -> CrystallizationOutput:
        self.inputs.append(crystallization_input)
        output = await self.delegate.generate(crystallization_input)
        self.outputs.append(output)
        return output


async def run_actual_model_crystallization(
    *,
    character: CharacterDirectory,
    crystallizer: Crystallizer,
    manifest: ActualModelCrystallizationManifest,
    case: ActualModelCrystallizationCase,
) -> ActualModelCrystallizationEvidence:
    """Record one real off-turn crystallization pass without redefining its semantics."""

    recording = _RecordingCrystallizer(crystallizer)
    result = await run_crystallization(
        character=character,
        crystallizer=recording,
        max_events=manifest.max_events,
    )
    if len(recording.inputs) != 1 or len(recording.outputs) != 1:
        raise RuntimeError(
            "one actual-model crystallization evaluation must observe exactly one generation"
        )

    input_evidence = _serialize_input(recording.inputs[0])
    raw = RawCrystallizationObservation(
        memory_markdown=recording.outputs[0].memory_markdown,
        state_candidates=tuple(
            _serialize_state_candidate(item)
            for item in recording.outputs[0].state_candidates
        ),
    )
    deterministic = DeterministicCrystallizationObservation(
        state_decisions=tuple(_serialize_decision(item) for item in result.decisions),
        resulting_state=tuple(_serialize_state_record(item) for item in result.state.states),
        memory_changed=result.memory_changed,
        resulting_memory=character.load_memory_markdown(),
    )
    run_id = stable_actual_model_crystallization_run_id(
        manifest=manifest,
        case=case,
        input=input_evidence,
    )
    return ActualModelCrystallizationEvidence(
        run_id=run_id,
        manifest=manifest,
        case=case,
        input=input_evidence,
        raw_model=raw,
        deterministic=deterministic,
    )


def stable_actual_model_crystallization_run_id(
    *,
    manifest: ActualModelCrystallizationManifest,
    case: ActualModelCrystallizationCase,
    input: CrystallizationInputEvidence,
) -> str:
    identity = {
        "manifest": manifest.to_mapping(),
        "case": case.to_mapping(),
        "input": input.to_mapping(),
    }
    return _stable_digest(identity)


def stable_actual_model_crystallization_review_id(
    review: ActualModelCrystallizationReview,
) -> str:
    return _stable_digest(review.to_mapping())


def write_actual_model_crystallization_evidence(
    *,
    evidence: ActualModelCrystallizationEvidence,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable run-id-addressed crystallization evidence artifact."""

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{evidence.run_id}.json"
    payload = evidence.to_json() + "\n"
    if path.exists():
        return _resolve_existing_evidence(path=path, payload=payload)

    temporary = root / f".{evidence.run_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing_evidence(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelCrystallizationArtifactError(
            f"cannot persist actual-model crystallization evidence: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _resolve_existing_evidence(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelCrystallizationArtifactError(
            f"cannot read existing crystallization evidence: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelCrystallizationArtifactError(
        "run ID already exists with different evidence; use a distinct replicate_id"
    )


def _serialize_input(value: CrystallizationInput) -> CrystallizationInputEvidence:
    return CrystallizationInputEvidence(
        identity={"content": value.identity.content},
        state=tuple(_serialize_state_record(item) for item in value.state.states),
        events=tuple(_serialize_event(item) for item in value.events),
        prior_memory=value.prior_memory,
    )


def _serialize_event(event: Event) -> dict[str, object]:
    return {
        "id": event.id,
        "type": event.type,
        "actor": event.actor,
        "timestamp": event.timestamp,
        "payload": event.payload,
    }


def _serialize_state_record(record: StateRecord) -> dict[str, object]:
    return {
        "state_id": record.state_id,
        "state_class": record.state_class,
        "key": record.key,
        "value": record.value,
        "sources": list(record.sources),
        "status": record.status,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
    }


def _serialize_state_candidate(candidate: StateCandidate) -> dict[str, object]:
    result: dict[str, object] = {
        "state_class": candidate.state_class,
        "key": candidate.key,
        "op": candidate.op,
        "sources": list(candidate.sources),
    }
    if candidate.has_value:
        result["value"] = candidate.value
    return result


def _serialize_decision(decision: CandidateDecision) -> dict[str, object]:
    return {
        "candidate": _serialize_state_candidate(decision.candidate),
        "status": decision.status,
        "action": decision.action,
        "reason": decision.reason,
    }


def _stable_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
