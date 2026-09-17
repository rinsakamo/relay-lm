from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from tools.release_identity import ReleaseIdentityError, expected_release_tag, parse_release_version

if TYPE_CHECKING:
    from tools.memconflict_adapter import (
        RelayLMFrozenQuerySnapshot,
        RelayLMQueryResult,
        RelayLMReadOnlyQueryExecutionError,
    )

FORMAT_VERSION = 1
SLOTS = (
    "same_model_direct",
    "simple_baseline",
    "serious_comparator",
    "relaylm_exact_rc",
)
PURPOSES = {"dry_run", "prequalification_smoke", "release_qualification"}
CLASSIFICATIONS = {
    "reproducible_competitive_result",
    "specialist_deferred_capability_loss",
    "generalizable_core_defect_candidate",
    "benchmark_adapter_mismatch",
    "non_reproducible_workload",
    "resource_impracticality",
    "comparison_condition_mismatch",
}

DURABLE_RUN_FORMAT_VERSION = 1
PARTICIPANT_RECORD_FORMAT_VERSION = 1
SCIENTIFIC_SPEND_FORMAT_VERSION = 1
LIVE_LAUNCH_ADMISSION_FIELDS = (
    "backend",
    "runtime",
    "model_runner",
    "effective_gpu_reservation",
    "admitted_context",
    "capacity_evidence",
    "launch_evidence_reference",
    "runtime_ownership_evidence_reference",
)
LIVE_LAUNCH_ADMISSION_EXTENDED_FIELDS = LIVE_LAUNCH_ADMISSION_FIELDS + (
    "runtime_identity",
    "gpu_identity",
    "launch_observation",
)
LIVE_LAUNCH_STABLE_FIELDS = (
    "backend",
    "runtime",
    "model_runner",
    "effective_gpu_reservation",
    "admitted_context",
    "capacity_evidence",
)
LIVE_LAUNCH_FROZEN_EXTENDED_FIELDS = LIVE_LAUNCH_STABLE_FIELDS + (
    "runtime_identity",
    "gpu_identity",
)
FROZEN_EXPERIMENT_IDENTITY_FIELDS = (
    "repository",
    "candidate",
    "prompt_core",
    "benchmark",
    "dataset",
    "harness",
    "adapter",
    "model",
    "artifact",
    "tokenizer",
    "template",
    "backend",
    "runtime",
    "decoding",
    "reasoning",
    "structured_output",
    "context_capacity",
    "capacity_evidence",
    "hardware",
    "execution_order",
    "retry_policy",
    "authority",
    "launch_admission",
)


class ExternalQualificationError(ValueError):
    """External qualification input or evidence violates the frozen contract."""


class ExactResumeError(ExternalQualificationError):
    """A durable run cannot be resumed under the supplied frozen identity."""


class ScientificSpendLedger:
    """Fail-closed, fsync-backed campaign-level scientific-spend state.

    The ledger is deliberately outside the question store.  A process can
    die after the transition and before a participant returns; a later fresh
    owner therefore still observes ``CONSUMED`` and cannot start a new
    scientific campaign.  Exact infrastructure resume may reopen the same
    consumed ledger because it carries the same owner and campaign identity.
    """

    _KEYS = {
        "format_version",
        "owner_id",
        "campaign_fingerprint",
        "state",
        "transition",
        "updated_at",
    }

    def __init__(
        self,
        *,
        path: Path,
        owner_id: str,
        campaign_fingerprint: str,
        state: str,
    ) -> None:
        self.path = path
        self.owner_id = owner_id
        self.campaign_fingerprint = campaign_fingerprint
        self._state = state

    @classmethod
    def open(
        cls,
        *,
        path: str | Path,
        owner_id: str,
        campaign_fingerprint: str,
        mode: str,
    ) -> "ScientificSpendLedger":
        ledger_path = Path(path)
        owner_id = _text(owner_id, "scientific spend owner_id")
        campaign_fingerprint = _text(
            campaign_fingerprint,
            "scientific spend campaign_fingerprint",
        )
        if mode not in {"fresh_run", "exact_infrastructure_resume"}:
            raise ExternalQualificationError(
                "scientific spend ledger requires fresh_run or exact_infrastructure_resume"
            )
        if not ledger_path.exists():
            ledger = cls(
                path=ledger_path,
                owner_id=owner_id,
                campaign_fingerprint=campaign_fingerprint,
                state="UNSPENT",
            )
            ledger._persist(transition="INITIALIZED")
            return ledger
        raw = _load_json_object(ledger_path, "scientific spend ledger")
        cls._validate(raw)
        if raw["owner_id"] != owner_id:
            raise ExactResumeError("scientific spend owner_id does not match")
        if raw["campaign_fingerprint"] != campaign_fingerprint:
            raise ExactResumeError("scientific spend campaign fingerprint does not match")
        state = raw["state"]
        if mode == "fresh_run" and state != "UNSPENT":
            raise ExactResumeError(
                "a fresh scientific campaign is forbidden after the owner was consumed"
            )
        return cls(
            path=ledger_path,
            owner_id=owner_id,
            campaign_fingerprint=campaign_fingerprint,
            state=state,
        )

    @classmethod
    def _validate(cls, raw: Mapping[str, object]) -> None:
        _keys(raw, cls._KEYS, "scientific spend ledger")
        if raw["format_version"] != SCIENTIFIC_SPEND_FORMAT_VERSION:
            raise ExactResumeError("unsupported scientific spend ledger format_version")
        if raw["state"] not in {"UNSPENT", "CONSUMED"}:
            raise ExactResumeError("scientific spend ledger state is invalid")
        _text(raw["owner_id"], "scientific spend owner_id")
        _text(raw["campaign_fingerprint"], "scientific spend campaign_fingerprint")
        _text(raw["transition"], "scientific spend transition")
        if isinstance(raw["updated_at"], bool) or not isinstance(raw["updated_at"], int):
            raise ExactResumeError("scientific spend ledger timestamp is invalid")

    @property
    def state(self) -> str:
        return self._state

    def record_pre_call_barrier(self, *, payload: Mapping[str, object]) -> None:
        """Persist the zero-semantic barrier receipt while remaining UNSPENT."""

        if self._state == "CONSUMED":
            return
        if self._state != "UNSPENT":
            raise ExactResumeError("pre-call barrier cannot move a consumed owner backward")
        normalized = _json_copy(dict(payload), "scientific pre-call barrier")
        _write_json_atomically(
            self.path.with_name(self.path.name + ".barrier"),
            {
                "format_version": SCIENTIFIC_SPEND_FORMAT_VERSION,
                "owner_id": self.owner_id,
                "campaign_fingerprint": self.campaign_fingerprint,
                "state": "UNSPENT",
                "transition": "PRE_CALL_BARRIER_REACHED",
                "updated_at": time_now(),
                "payload": normalized,
            },
        )

    def consume_before_first_scientific_call(self) -> None:
        """Atomically transition UNSPENT to CONSUMED immediately before A/B/C/D."""

        if self._state == "CONSUMED":
            return
        if self._state != "UNSPENT":
            raise ExactResumeError("scientific spend ledger is not in a consumable state")
        self._state = "CONSUMED"
        self._persist(transition="CONSUMED_BEFORE_FIRST_SCIENTIFIC_PARTICIPANT_CALL")

    def _persist(self, *, transition: str) -> None:
        _write_json_atomically(
            self.path,
            {
                "format_version": SCIENTIFIC_SPEND_FORMAT_VERSION,
                "owner_id": self.owner_id,
                "campaign_fingerprint": self.campaign_fingerprint,
                "state": self._state,
                "transition": transition,
                "updated_at": time_now(),
            },
        )


@dataclass(frozen=True, slots=True)
class LiveLaunchAdmissionAttestation:
    """Qualification-significant facts observed from the final live launch."""

    payload: dict[str, object] = field(repr=False, compare=False)
    fingerprint: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "LiveLaunchAdmissionAttestation":
        normalized = _normalize_live_launch_admission(raw)
        encoded = _canonical_json(normalized).encode("utf-8")
        return cls(
            payload=normalized,
            fingerprint=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        )

    def to_mapping(self) -> dict[str, object]:
        copied = json.loads(_canonical_json(self.payload))
        if not isinstance(copied, dict):
            raise ExternalQualificationError(
                "live launch/admission attestation must be an object"
            )
        return copied


@dataclass(frozen=True, slots=True)
class FrozenExperimentIdentity:
    """The complete identity that a durable semantic run is allowed to resume."""

    payload: dict[str, object] = field(repr=False, compare=False)
    fingerprint: str
    live_attestation_fingerprint: str | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "FrozenExperimentIdentity":
        if not isinstance(raw, Mapping):
            raise ExternalQualificationError("frozen experiment identity must be an object")
        expected_keys = set(FROZEN_EXPERIMENT_IDENTITY_FIELDS)
        extended_keys = expected_keys | {"campaign_contract"}
        if set(raw) != expected_keys and set(raw) != extended_keys:
            _keys(set(raw), expected_keys, "frozen experiment identity")
        normalized = _json_copy(dict(raw), "frozen experiment identity")
        for name in FROZEN_EXPERIMENT_IDENTITY_FIELDS:
            if normalized[name] is None:
                raise ExternalQualificationError(
                    f"frozen experiment identity {name} must not be null"
                )
        if (
            isinstance(normalized["context_capacity"], bool)
            or not isinstance(normalized["context_capacity"], int)
            or normalized["context_capacity"] <= 0
        ):
            raise ExternalQualificationError(
                "frozen experiment identity context_capacity must be a positive integer"
            )
        normalized["capacity_evidence"] = _stable_capacity(
            normalized["capacity_evidence"]
        )
        launch_admission = _normalize_live_launch_admission(
            _mapping(normalized["launch_admission"], "frozen identity launch_admission"),
            allow_stable_extended=True,
        )
        if "runtime_identity" in launch_admission:
            # Extended launch attestations carry per-launch evidence paths,
            # PID, timestamps, and current GPU usage.  Those observations are
            # retained on LiveLaunchAdmissionAttestation and in campaign
            # evidence, but are not part of the immutable identity used for
            # exact infrastructure resume.
            launch_admission = {
                **{
                    name: _stable_capacity(launch_admission[name])
                    if name == "capacity_evidence"
                    else launch_admission[name]
                    for name in LIVE_LAUNCH_STABLE_FIELDS
                },
                "runtime_identity": launch_admission["runtime_identity"],
                "gpu_identity": launch_admission["gpu_identity"],
            }
        normalized["launch_admission"] = launch_admission
        authority = normalized["authority"]
        if not isinstance(authority, Mapping) or authority.get("status") != "CURRENT_AUTHORITY_CONFIRMED":
            raise ExternalQualificationError(
                "frozen experiment identity requires CURRENT_AUTHORITY_CONFIRMED authority"
            )
        for name, validator in (
            ("branch", _text),
            ("repository_head", _commit),
            ("repository_tree", _commit),
        ):
            if name not in authority:
                raise ExternalQualificationError(
                    "frozen experiment identity authority requires exact "
                    "status, branch, repository_head, and repository_tree"
                )
            validator(authority[name], f"authority {name}")
        if "campaign_contract" in normalized:
            if not isinstance(normalized["campaign_contract"], Mapping):
                raise ExternalQualificationError(
                    "frozen experiment identity campaign_contract must be an object"
                )
        encoded = _canonical_json(normalized).encode("utf-8")
        return cls(
            payload=normalized,
            fingerprint=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        )

    @classmethod
    def from_live_attestation(
        cls,
        raw: Mapping[str, object],
        live_attestation: LiveLaunchAdmissionAttestation | Mapping[str, object],
    ) -> "FrozenExperimentIdentity":
        """Construct an identity only after matching the final live condition."""

        return freeze_experiment_identity(
            identity=raw,
            live_attestation=live_attestation,
        )

    def to_mapping(self) -> dict[str, object]:
        return _json_copy(self.payload, "frozen experiment identity")


@dataclass(frozen=True, slots=True)
class DurableQuestion:
    """Stable question/session identity used by append-only durable evidence."""

    question_id: str
    content_fingerprint: str
    session_id: str = "default"
    content: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("question_id", "content_fingerprint", "session_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ExternalQualificationError(f"question {name} must be non-empty")
        if self.content is not None:
            encoded = _canonical_json(self.content).encode("utf-8")
            expected = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
            if expected != self.content_fingerprint:
                raise ExternalQualificationError(
                    "question content does not match content_fingerprint"
                )

    @classmethod
    def from_content(
        cls,
        question_id: str,
        content: object,
        *,
        session_id: str = "default",
    ) -> "DurableQuestion":
        encoded = _canonical_json(content).encode("utf-8")
        return cls(
            question_id=question_id,
            content_fingerprint=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
            session_id=session_id,
            content=_json_value_copy(content, "question content"),
        )

    def to_mapping(self, *, order: int) -> dict[str, object]:
        result: dict[str, object] = {
            "order": order,
            "question_id": self.question_id,
            "content_fingerprint": self.content_fingerprint,
            "session_id": self.session_id,
        }
        if self.content is not None:
            result["content"] = _json_value_copy(self.content, "question content")
        return result


class DurableQuestionRun:
    """Detached, question-level persistence for long external/actual-model runs.

    The store owns only execution durability. It never invokes a model or
    interprets a semantic answer, so an adapter can keep its existing product
    and benchmark contracts while using exact infrastructure resume.
    """

    _MANIFEST_KEYS = {
        "format_version",
        "run_id",
        "identity",
        "identity_fingerprint",
        "questions",
    }
    _CHECKPOINT_KEYS = {
        "format_version",
        "run_id",
        "identity_fingerprint",
        "completed_questions",
        "next_order",
    }

    def __init__(
        self,
        *,
        artifact_root: str | Path,
        identity: FrozenExperimentIdentity,
        questions: tuple[DurableQuestion, ...],
        run_id: str,
        run_mode: str,
        partial_tail_detected: bool = False,
    ) -> None:
        self.root = Path(artifact_root)
        self.identity = identity
        self.questions = questions
        self.run_id = run_id
        self.run_mode = run_mode
        self._question_by_id = {item.question_id: item for item in questions}
        self._order_by_id = {
            item.question_id: order for order, item in enumerate(questions)
        }
        self._completed: dict[str, dict[str, object]] = {}
        self._in_flight: dict[str, int] = {}
        self._participant_completed: dict[tuple[str, str], dict[str, object]] = {}
        self._partial_tail_detected = partial_tail_detected
        self._status = "RUNNING"

    @classmethod
    def start(
        cls,
        *,
        artifact_root: str | Path,
        identity: FrozenExperimentIdentity | Mapping[str, object],
        questions: Sequence[DurableQuestion],
        run_id: str | None = None,
        run_mode: str = "fresh_run",
    ) -> "DurableQuestionRun":
        if run_mode == "semantic_retry":
            raise ExternalQualificationError(
                "semantic retry is not a supported durable run mode"
            )
        if run_mode != "fresh_run":
            raise ExternalQualificationError("new durable runs must use fresh_run mode")
        normalized_identity = _coerce_frozen_identity(identity)
        _require_live_attested_identity(normalized_identity)
        normalized_questions = _normalize_questions(questions)
        root = Path(artifact_root)
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise ExternalQualificationError(
                "fresh durable run artifact root must be empty"
            )
        resolved_run_id = run_id or _stable_durable_run_id(
            identity=normalized_identity,
            questions=normalized_questions,
        )
        run = cls(
            artifact_root=root,
            identity=normalized_identity,
            questions=normalized_questions,
            run_id=resolved_run_id,
            run_mode="fresh_run",
        )
        run._write_manifest()
        run._write_checkpoint()
        run._write_state()
        return run

    @classmethod
    def resume(
        cls,
        *,
        artifact_root: str | Path,
        identity: FrozenExperimentIdentity | Mapping[str, object],
        questions: Sequence[DurableQuestion],
    ) -> "DurableQuestionRun":
        normalized_identity = _coerce_frozen_identity(identity)
        normalized_questions = _normalize_questions(questions)
        root = Path(artifact_root)
        manifest = _load_json_object(root / "run-manifest.json", "durable run manifest")
        _keys(manifest, cls._MANIFEST_KEYS, "durable run manifest")
        if manifest["format_version"] != DURABLE_RUN_FORMAT_VERSION:
            raise ExactResumeError("unsupported durable run format_version")
        run_id = _text(manifest["run_id"], "durable run_id")
        if manifest["identity_fingerprint"] != normalized_identity.fingerprint:
            raise ExactResumeError(
                "exact resume requires an identical frozen experiment identity"
            )
        try:
            manifest_identity = FrozenExperimentIdentity.from_mapping(
                _mapping(manifest["identity"], "durable run identity")
            )
        except ExternalQualificationError as exc:
            raise ExactResumeError(
                f"durable manifest frozen experiment identity is invalid: {exc}"
            ) from exc
        if manifest_identity.fingerprint != normalized_identity.fingerprint:
            raise ExactResumeError(
                "exact resume requires an identical frozen experiment identity"
            )
        if manifest["questions"] != [
            item.to_mapping(order=order)
            for order, item in enumerate(normalized_questions)
        ]:
            raise ExactResumeError(
                "exact resume requires identical question order or fingerprint"
            )
        run = cls(
            artifact_root=root,
            identity=normalized_identity,
            questions=normalized_questions,
            run_id=run_id,
            run_mode="exact_infrastructure_resume",
        )
        run._load_observations()
        run._load_participant_observations()
        run._load_request_evidence()
        run._validate_or_rebuild_checkpoint()
        run._status = "RUNNING"
        run._write_state()
        return run

    @classmethod
    def open(
        cls,
        *,
        artifact_root: str | Path,
        identity: FrozenExperimentIdentity | Mapping[str, object],
        questions: Sequence[DurableQuestion],
        mode: str,
    ) -> "DurableQuestionRun":
        if mode == "fresh_run":
            return cls.start(
                artifact_root=artifact_root,
                identity=identity,
                questions=questions,
            )
        if mode == "exact_infrastructure_resume":
            return cls.resume(
                artifact_root=artifact_root,
                identity=identity,
                questions=questions,
            )
        if mode == "semantic_retry":
            raise ExternalQualificationError(
                "semantic retry is not a supported durable run mode"
            )
        raise ExternalQualificationError(f"unsupported durable run mode: {mode}")

    @property
    def partial_tail_detected(self) -> bool:
        return self._partial_tail_detected

    def next_question(self) -> DurableQuestion | None:
        for question in self.questions:
            if question.question_id not in self._completed:
                return question
        return None

    def begin_question(self, question_id: str) -> DurableQuestion:
        question = self._question_by_id.get(question_id)
        if question is None:
            raise ExternalQualificationError(f"unknown durable question: {question_id}")
        if question_id in self._completed:
            raise ExternalQualificationError(
                "question already durably completed; semantic regeneration is forbidden"
            )
        expected = self.next_question()
        if expected is None or expected.question_id != question_id:
            raise ExternalQualificationError(
                "durable questions must execute in the frozen execution order"
            )
        if question_id in self._in_flight:
            if self.run_mode == "fresh_run":
                raise ExternalQualificationError("question is already in flight")
            return question
        attempt = self._in_flight.get(question_id, 0) + 1
        self._append_observation(
            {
                "format_version": DURABLE_RUN_FORMAT_VERSION,
                "run_id": self.run_id,
                "identity_fingerprint": self.identity.fingerprint,
                "event": "in_flight",
                "order": self._order_by_id[question_id],
                "question_id": question.question_id,
                "content_fingerprint": question.content_fingerprint,
                "session_id": question.session_id,
                "attempt": attempt,
            }
        )
        self._in_flight[question_id] = attempt
        self._write_state()
        return question

    def completed_participant_slots(self, question_id: str) -> tuple[str, ...]:
        """Return durably completed participant slots in canonical A/B/C/D order."""

        if question_id not in self._question_by_id:
            raise ExternalQualificationError(f"unknown durable question: {question_id}")
        return tuple(
            slot
            for slot in SLOTS
            if (question_id, slot) in self._participant_completed
        )

    def participant_record(
        self,
        *,
        question_id: str,
        slot: str,
    ) -> dict[str, object] | None:
        if slot not in SLOTS:
            raise ExternalQualificationError(f"unknown participant slot: {slot}")
        record = self._participant_completed.get((question_id, slot))
        return None if record is None else _json_copy(record, "participant record")

    def commit_participant(
        self,
        *,
        question_id: str,
        slot: str,
        participant_identity: Mapping[str, object],
        result: Mapping[str, object],
        request_evidence: Sequence[Mapping[str, object]] = (),
        enabled_slots: Sequence[str] | None = None,
    ) -> None:
        """Persist one validated participant result before the next slot runs."""

        question = self._require_in_flight(question_id)
        if slot not in SLOTS:
            raise ExternalQualificationError(f"unknown participant slot: {slot}")
        key = (question_id, slot)
        if key in self._participant_completed:
            raise ExactResumeError(
                "duplicate participant completion record is not resumable"
            )
        ordered_slots = tuple(SLOTS if enabled_slots is None else enabled_slots)
        if any(slot_name not in SLOTS for slot_name in ordered_slots):
            raise ExternalQualificationError("enabled participant slots are invalid")
        if slot not in ordered_slots:
            raise ExternalQualificationError(
                f"participant slot {slot!r} is not enabled in the frozen manifest"
            )
        expected_slot = next(
            (
                candidate
                for candidate in ordered_slots
                if (question_id, candidate) not in self._participant_completed
            ),
            None,
        )
        if slot != expected_slot:
            raise ExternalQualificationError(
                f"participant slots must commit in canonical A/B/C/D order; expected {expected_slot}"
            )
        identity = _json_copy(dict(participant_identity), "participant identity")
        normalized_result = _json_copy(dict(result), "participant result")
        evidence = [
            _json_copy(dict(item), "participant request evidence")
            for item in request_evidence
        ]
        record = {
            "format_version": PARTICIPANT_RECORD_FORMAT_VERSION,
            "run_id": self.run_id,
            "identity_fingerprint": self.identity.fingerprint,
            "event": "participant_completed",
            "order": self._order_by_id[question_id],
            "question_id": question.question_id,
            "content_fingerprint": question.content_fingerprint,
            "session_id": question.session_id,
            "attempt": self._in_flight[question_id],
            "slot": slot,
            "participant_identity": identity,
            "participant_identity_fingerprint": _sha256_mapping(identity),
            "result": normalized_result,
            "request_evidence": evidence,
        }
        # The append itself flushes and fsyncs before the next participant can
        # be invoked.  The in-memory index is updated only after that succeeds.
        self._append_line(self.root / "participant-observations.jsonl", record)
        self._participant_completed[key] = record
        for item in evidence:
            self.append_request_evidence(question_id=question_id, evidence=item)
        self._write_state()

    def append_request_evidence(
        self,
        *,
        question_id: str,
        evidence: Mapping[str, object],
    ) -> None:
        question = self._require_in_flight(question_id)
        normalized = _json_copy(dict(evidence), "request evidence")
        self._append_line(
            self.root / "request-evidence.jsonl",
            {
                "format_version": DURABLE_RUN_FORMAT_VERSION,
                "run_id": self.run_id,
                "identity_fingerprint": self.identity.fingerprint,
                "order": self._order_by_id[question_id],
                "question_id": question.question_id,
                "content_fingerprint": question.content_fingerprint,
                "session_id": question.session_id,
                "attempt": self._in_flight[question_id],
                "evidence": normalized,
            },
        )
        self._write_state()

    def commit_question(
        self,
        *,
        question_id: str,
        result: Mapping[str, object],
        request_evidence: Sequence[Mapping[str, object]] = (),
    ) -> None:
        question = self._require_in_flight(question_id)
        for evidence in request_evidence:
            self.append_request_evidence(question_id=question_id, evidence=evidence)
        normalized_result = _json_copy(dict(result), "question result")
        record = {
            "format_version": DURABLE_RUN_FORMAT_VERSION,
            "run_id": self.run_id,
            "identity_fingerprint": self.identity.fingerprint,
            "event": "completed",
            "order": self._order_by_id[question_id],
            "question_id": question.question_id,
            "content_fingerprint": question.content_fingerprint,
            "session_id": question.session_id,
            "attempt": self._in_flight[question_id],
            "result": normalized_result,
        }
        self._append_observation(record)
        self._completed[question_id] = record
        del self._in_flight[question_id]
        self._write_checkpoint()
        self._write_state()

    def mark_process_exited(self) -> None:
        self._status = "PROCESS_EXITED"
        self._write_state()

    def mark_stopped(self) -> None:
        self._status = "INCOMPLETE"
        self._write_state()

    def mark_completed(self) -> None:
        if self.next_question() is not None:
            raise ExternalQualificationError(
                "cannot mark durable run completed while questions remain"
            )
        self._status = "COMPLETED"
        self._write_state()

    def heartbeat(
        self,
        *,
        status: str = "RUNNING",
        resource_observations: Mapping[str, object] | None = None,
    ) -> None:
        if status not in {"RUNNING", "STALLED", "PROCESS_EXITED", "INCOMPLETE", "COMPLETED"}:
            raise ExternalQualificationError(f"unsupported durable run status: {status}")
        self._status = status
        self._write_state(resource_observations=resource_observations)

    def health(self) -> dict[str, object]:
        return self._state_mapping()

    def rebuild_completed_results(self) -> list[dict[str, object]]:
        return [
            {
                "order": self._order_by_id[question.question_id],
                "question_id": question.question_id,
                "content_fingerprint": question.content_fingerprint,
                "session_id": question.session_id,
                "attempt": self._completed[question.question_id]["attempt"],
                "result": _json_copy(
                    _mapping(
                        self._completed[question.question_id]["result"],
                        "durable question result",
                    ),
                    "durable question result",
                ),
            }
            for question in self.questions
            if question.question_id in self._completed
        ]

    def rebuild_participant_results(self, question_id: str) -> list[dict[str, object]]:
        """Return durable participant records for one question in A/B/C/D order."""

        if question_id not in self._question_by_id:
            raise ExternalQualificationError(f"unknown durable question: {question_id}")
        result: list[dict[str, object]] = []
        for slot in SLOTS:
            record = self._participant_completed.get((question_id, slot))
            if record is not None:
                result.append(_json_copy(record, "participant record"))
        return result

    def rebuild_aggregate(self) -> dict[str, object]:
        sessions: dict[str, list[dict[str, object]]] = {}
        for result in self.rebuild_completed_results():
            session = str(result["session_id"])
            sessions.setdefault(session, []).append(result)
        return {
            "format_version": DURABLE_RUN_FORMAT_VERSION,
            "run_id": self.run_id,
            "identity_fingerprint": self.identity.fingerprint,
            "completed_count": len(self._completed),
            "total_count": len(self.questions),
            "sessions": sessions,
        }

    def _write_manifest(self) -> None:
        payload = {
            "format_version": DURABLE_RUN_FORMAT_VERSION,
            "run_id": self.run_id,
            "identity": self.identity.to_mapping(),
            "identity_fingerprint": self.identity.fingerprint,
            "questions": [
                item.to_mapping(order=order)
                for order, item in enumerate(self.questions)
            ],
        }
        _write_json_atomically(self.root / "run-manifest.json", payload)

    def _write_checkpoint(self) -> None:
        completed = [
            {
                "order": self._order_by_id[question.question_id],
                "question_id": question.question_id,
                "content_fingerprint": question.content_fingerprint,
            }
            for question in self.questions
            if question.question_id in self._completed
        ]
        next_order = next(
            (
                order
                for order, question in enumerate(self.questions)
                if question.question_id not in self._completed
            ),
            len(self.questions),
        )
        _write_json_atomically(
            self.root / "checkpoint.json",
            {
                "format_version": DURABLE_RUN_FORMAT_VERSION,
                "run_id": self.run_id,
                "identity_fingerprint": self.identity.fingerprint,
                "completed_questions": completed,
                "next_order": next_order,
            },
        )

    def _write_state(
        self,
        *,
        resource_observations: Mapping[str, object] | None = None,
    ) -> None:
        payload = self._state_mapping()
        payload["last_heartbeat"] = time_now()
        if resource_observations is not None:
            payload["resource_observations"] = _json_copy(
                dict(resource_observations), "resource observations"
            )
        _write_json_atomically(self.root / "run-state.json", payload)

    def _state_mapping(self) -> dict[str, object]:
        return {
            "format_version": DURABLE_RUN_FORMAT_VERSION,
            "run_id": self.run_id,
            "identity_fingerprint": self.identity.fingerprint,
            "status": self._status,
            "run_mode": self.run_mode,
            "control_plane": "detached_durable",
            "question_count": len(self.questions),
            "completed_question_count": len(self._completed),
            "completed_participant_count": len(self._participant_completed),
            "completed_participants": [
                {
                    "question_id": question.question_id,
                    "slot": slot,
                }
                for question in self.questions
                for slot in SLOTS
                if (question.question_id, slot) in self._participant_completed
            ],
            "in_flight_questions": [
                question.question_id
                for question in self.questions
                if question.question_id in self._in_flight
            ],
            "next_question": (
                self.next_question().question_id if self.next_question() is not None else None
            ),
            "pass1_calls": self._count_request_evidence("pass1"),
            "pass2_calls": self._count_request_evidence("pass2"),
            "last_heartbeat": None,
        }

    def _append_observation(self, record: Mapping[str, object]) -> None:
        self._append_line(self.root / "question-observations.jsonl", record)

    def _load_participant_observations(self) -> None:
        for record in self._read_jsonl(self.root / "participant-observations.jsonl"):
            if record.get("format_version") != PARTICIPANT_RECORD_FORMAT_VERSION:
                raise ExactResumeError("participant evidence format_version is invalid")
            question_id = self._validate_record_identity(record, "participant evidence")
            if record.get("event") != "participant_completed":
                raise ExactResumeError("participant evidence event is invalid")
            slot = record.get("slot")
            if not isinstance(slot, str) or slot not in SLOTS:
                raise ExactResumeError("participant evidence slot is invalid")
            attempt = record.get("attempt")
            if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
                raise ExactResumeError("participant evidence attempt is invalid")
            expected_attempt = self._in_flight.get(question_id)
            if expected_attempt is None and question_id in self._completed:
                completed_record = self._completed[question_id]
                completed_attempt = completed_record.get("attempt")
                if isinstance(completed_attempt, int) and not isinstance(
                    completed_attempt, bool
                ):
                    expected_attempt = completed_attempt
            if expected_attempt is None:
                raise ExactResumeError(
                    "participant evidence exists for a question with no durable attempt"
                )
            if attempt != expected_attempt:
                raise ExactResumeError(
                    "participant evidence attempt does not match the durable question attempt"
                )
            participant_identity = record.get("participant_identity")
            result = record.get("result")
            evidence = record.get("request_evidence")
            if not isinstance(participant_identity, Mapping) or not isinstance(result, Mapping):
                raise ExactResumeError("participant evidence payload is invalid")
            if not isinstance(evidence, list) or not all(
                isinstance(item, Mapping) for item in evidence
            ):
                raise ExactResumeError("participant request evidence is invalid")
            expected_identity_fingerprint = _sha256_mapping(participant_identity)
            if record.get("participant_identity_fingerprint") != expected_identity_fingerprint:
                raise ExactResumeError("participant identity fingerprint is invalid")
            key = (question_id, slot)
            if key in self._participant_completed:
                raise ExactResumeError(
                    "duplicate or conflicting participant completion records are not resumable"
                )
            self._participant_completed[key] = dict(record)

    def _append_line(self, path: Path, record: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical_json(dict(record)) + "\n"
        try:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ExternalQualificationError(
                f"cannot persist durable question evidence: {exc}"
            ) from exc

    def _load_observations(self) -> None:
        for record in self._read_jsonl(self.root / "question-observations.jsonl"):
            event = record.get("event")
            question_id = self._validate_record_identity(record, "question observation")
            attempt = record.get("attempt")
            if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
                raise ExactResumeError("durable question observation attempt is invalid")
            if event == "in_flight":
                if question_id in self._completed:
                    raise ExactResumeError(
                        "durable question has in-flight evidence after completion"
                    )
                self._in_flight[question_id] = max(
                    attempt, self._in_flight.get(question_id, 0)
                )
            elif event == "completed":
                if question_id in self._completed:
                    raise ExactResumeError(
                        "durable question has more than one completion record"
                    )
                if not isinstance(record.get("result"), Mapping):
                    raise ExactResumeError("completed durable question result is invalid")
                self._completed[question_id] = dict(record)
                self._in_flight.pop(question_id, None)
            else:
                raise ExactResumeError("durable question observation event is invalid")

    def _load_request_evidence(self) -> None:
        for record in self._read_jsonl(self.root / "request-evidence.jsonl"):
            self._validate_record_identity(record, "request evidence")
            attempt = record.get("attempt")
            if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
                raise ExactResumeError("request evidence attempt is invalid")
            if not isinstance(record.get("evidence"), Mapping):
                raise ExactResumeError("request evidence payload is invalid")

    def _read_jsonl(self, path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        try:
            raw_lines = path.read_bytes().splitlines(keepends=True)
        except OSError as exc:
            raise ExactResumeError(f"cannot read durable evidence: {exc}") from exc
        records: list[dict[str, object]] = []
        for index, raw_line in enumerate(raw_lines):
            if not raw_line.endswith(b"\n"):
                try:
                    decoded = json.loads(raw_line.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError):
                    if index == len(raw_lines) - 1:
                        self._partial_tail_detected = True
                        break
                    raise ExactResumeError("non-final durable evidence record is torn")
            else:
                try:
                    decoded = json.loads(raw_line.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    if index == len(raw_lines) - 1:
                        self._partial_tail_detected = True
                        break
                    raise ExactResumeError("durable evidence record is malformed") from exc
            if not isinstance(decoded, dict):
                raise ExactResumeError("durable evidence record must be an object")
            records.append(decoded)
        return records

    def _validate_or_rebuild_checkpoint(self) -> None:
        path = self.root / "checkpoint.json"
        if not path.exists():
            self._write_checkpoint()
            return
        checkpoint = _load_json_object(path, "durable checkpoint")
        _keys(checkpoint, self._CHECKPOINT_KEYS, "durable checkpoint")
        if (
            checkpoint["format_version"] != DURABLE_RUN_FORMAT_VERSION
            or checkpoint["run_id"] != self.run_id
            or checkpoint["identity_fingerprint"] != self.identity.fingerprint
        ):
            raise ExactResumeError("durable checkpoint identity does not match frozen run")
        expected = [
            {
                "order": self._order_by_id[question.question_id],
                "question_id": question.question_id,
                "content_fingerprint": question.content_fingerprint,
            }
            for question in self.questions
            if question.question_id in self._completed
        ]
        if checkpoint["completed_questions"] != expected:
            self._write_checkpoint()
        expected_next = next(
            (
                order
                for order, question in enumerate(self.questions)
                if question.question_id not in self._completed
            ),
            len(self.questions),
        )
        if checkpoint["next_order"] != expected_next:
            self._write_checkpoint()

    def _validate_record_identity(
        self,
        record: Mapping[str, object],
        label: str,
    ) -> str:
        if record.get("format_version") != DURABLE_RUN_FORMAT_VERSION:
            raise ExactResumeError(f"{label} format_version does not match durable run")
        if record.get("run_id") != self.run_id:
            raise ExactResumeError(f"{label} run_id does not match durable run")
        if record.get("identity_fingerprint") != self.identity.fingerprint:
            raise ExactResumeError(f"{label} identity does not match frozen run")
        question_id = record.get("question_id")
        if not isinstance(question_id, str) or question_id not in self._question_by_id:
            raise ExactResumeError(f"{label} question identity is unknown")
        question = self._question_by_id[question_id]
        if (
            record.get("order") != self._order_by_id[question_id]
            or record.get("content_fingerprint") != question.content_fingerprint
            or record.get("session_id") != question.session_id
        ):
            raise ExactResumeError(f"{label} question order or fingerprint does not match")
        return question_id

    def _require_in_flight(self, question_id: str) -> DurableQuestion:
        question = self._question_by_id.get(question_id)
        if question is None:
            raise ExternalQualificationError(f"unknown durable question: {question_id}")
        if question_id in self._completed:
            raise ExternalQualificationError(
                "question already durably completed; semantic regeneration is forbidden"
            )
        if question_id not in self._in_flight:
            raise ExternalQualificationError(
                "question must be marked in-flight before evidence or completion"
            )
        return question

    def _count_request_evidence(self, pass_name: str) -> int:
        path = self.root / "request-evidence.jsonl"
        if not path.exists():
            return 0
        count = 0
        for record in self._read_jsonl(path):
            evidence = record.get("evidence")
            if isinstance(evidence, Mapping) and evidence.get("pass") == pass_name:
                count += 1
        return count


def _coerce_frozen_identity(
    value: FrozenExperimentIdentity | Mapping[str, object],
) -> FrozenExperimentIdentity:
    if isinstance(value, FrozenExperimentIdentity):
        return value
    return FrozenExperimentIdentity.from_mapping(value)


def _require_live_attested_identity(identity: FrozenExperimentIdentity) -> None:
    if (
        not isinstance(identity.live_attestation_fingerprint, str)
        or not identity.live_attestation_fingerprint.strip()
    ):
        raise ExternalQualificationError(
            "new durable runs require a live-attested frozen experiment identity"
        )
    try:
        normalized = FrozenExperimentIdentity.from_mapping(identity.to_mapping())
    except ExternalQualificationError as exc:
        raise ExternalQualificationError(
            "live-attested frozen experiment identity is invalid"
        ) from exc
    if normalized.fingerprint != identity.fingerprint:
        raise ExternalQualificationError(
            "live-attested frozen experiment identity fingerprint is invalid"
        )


def freeze_experiment_identity(
    *,
    identity: FrozenExperimentIdentity | Mapping[str, object],
    live_attestation: LiveLaunchAdmissionAttestation | Mapping[str, object],
) -> FrozenExperimentIdentity:
    """Freeze an experiment identity only when it matches final live facts.

    The caller may supply the semantic/benchmark portions of the identity, but
    the launch/admission portions are never trusted merely because they are
    present in a historical manifest.  Every qualification-significant fact is
    compared with the final live attestation immediately before freeze.
    """

    if isinstance(live_attestation, LiveLaunchAdmissionAttestation):
        live = LiveLaunchAdmissionAttestation.from_mapping(
            live_attestation.to_mapping()
        )
    else:
        live = LiveLaunchAdmissionAttestation.from_mapping(live_attestation)
    if isinstance(identity, FrozenExperimentIdentity):
        candidate = identity.to_mapping()
    else:
        candidate = identity
    frozen = FrozenExperimentIdentity.from_mapping(candidate)
    live_payload = live.payload

    for identity_name, live_name in (
        ("backend", "backend"),
        ("runtime", "runtime"),
        ("context_capacity", "admitted_context"),
    ):
        if _canonical_json(frozen.payload[identity_name]) != _canonical_json(
            live_payload[live_name]
        ):
            raise ExternalQualificationError(
                f"frozen experiment identity {identity_name} does not match "
                "live launch/admission attestation"
            )

    if _canonical_json(_stable_capacity(frozen.payload["capacity_evidence"])) != _canonical_json(
        _stable_capacity(live_payload["capacity_evidence"])
    ):
        raise ExternalQualificationError(
            "frozen experiment identity capacity_evidence does not match "
            "live launch/admission attestation"
        )

    represented_launch = _mapping(
        frozen.payload["launch_admission"],
        "frozen identity launch_admission",
    )
    extended_live = "runtime_identity" in live_payload
    names = LIVE_LAUNCH_STABLE_FIELDS if extended_live else LIVE_LAUNCH_ADMISSION_FIELDS
    for name in names:
        left = represented_launch[name]
        right = live_payload[name]
        if name == "capacity_evidence":
            left = _stable_capacity(left)
            right = _stable_capacity(right)
        if _canonical_json(left) != _canonical_json(right):
            raise ExternalQualificationError(
                f"frozen experiment identity launch_admission.{name} does not "
                "match live launch/admission attestation"
            )
    if extended_live:
        for name in ("runtime_identity", "gpu_identity"):
            if name not in represented_launch:
                raise ExternalQualificationError(
                    f"frozen experiment identity launch_admission.{name} is missing"
                )
            if _canonical_json(represented_launch[name]) != _canonical_json(
                live_payload[name]
            ):
                raise ExternalQualificationError(
                    f"frozen experiment identity launch_admission.{name} does not "
                    "match live launch/admission attestation"
                )
    return FrozenExperimentIdentity(
        payload=frozen.payload,
        fingerprint=frozen.fingerprint,
        live_attestation_fingerprint=live.fingerprint,
    )


def commit_relaylm_query_result(
    *,
    durable_run: DurableQuestionRun,
    question_id: str,
    query_result: RelayLMQueryResult,
    request_evidence: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    """Commit only the adapter's public typed result to a durable question.

    This is the sole success bridge for the external controller.  In
    particular, it never inspects a Pass 1/Pass 2 implementation object or
    reconstructs semantic evidence from one.
    """

    if not isinstance(durable_run, DurableQuestionRun):
        raise TypeError("durable_run must be DurableQuestionRun")
    from tools.memconflict_adapter import RelayLMQueryResult as _RelayLMQueryResult

    if not isinstance(query_result, _RelayLMQueryResult):
        raise TypeError("query_result must be RelayLMQueryResult")
    external_evidence = _json_copy(
        query_result.to_external_evidence(),
        "RelayLMQueryResult external evidence",
    )
    durable_run.commit_question(
        question_id=question_id,
        result=external_evidence,
        request_evidence=request_evidence,
    )
    return external_evidence


def record_relaylm_query_failure(
    *,
    durable_run: DurableQuestionRun,
    question_id: str,
    failure: RelayLMReadOnlyQueryExecutionError,
    request_evidence: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    """Persist bounded adapter failure evidence without completing a question."""

    if not isinstance(durable_run, DurableQuestionRun):
        raise TypeError("durable_run must be DurableQuestionRun")
    from tools.memconflict_adapter import (
        RelayLMReadOnlyQueryExecutionError as _RelayLMReadOnlyQueryExecutionError,
    )

    if not isinstance(failure, _RelayLMReadOnlyQueryExecutionError):
        raise TypeError(
            "failure must be RelayLMReadOnlyQueryExecutionError"
        )
    external_evidence = _json_copy(
        failure.to_external_evidence(),
        "RelayLMReadOnlyQueryExecutionError external evidence",
    )
    for evidence in request_evidence:
        durable_run.append_request_evidence(
            question_id=question_id,
            evidence=evidence,
        )
    durable_run.append_request_evidence(
        question_id=question_id,
        evidence=external_evidence,
    )
    durable_run.mark_stopped()
    return external_evidence


async def execute_relaylm_question(
    *,
    snapshot: RelayLMFrozenQuerySnapshot,
    durable_run: DurableQuestionRun,
    question_id: str,
    question: str,
    question_index: int,
    request_evidence: Sequence[Mapping[str, object]] = (),
) -> dict[str, object] | None:
    """Run one frozen query and route it through the canonical durable bridge.

    A provider failure remains an in-flight question with bounded request
    evidence.  The function deliberately has no retry or alternate result
    path; an incomplete question is left for the existing exact-resume
    policy.
    """

    if not isinstance(durable_run, DurableQuestionRun):
        raise TypeError("durable_run must be DurableQuestionRun")
    from tools.memconflict_adapter import (
        RelayLMFrozenQuerySnapshot as _RelayLMFrozenQuerySnapshot,
        RelayLMReadOnlyQueryExecutionError as _RelayLMReadOnlyQueryExecutionError,
    )

    if not isinstance(snapshot, _RelayLMFrozenQuerySnapshot):
        raise TypeError("snapshot must be RelayLMFrozenQuerySnapshot")
    durable_run.begin_question(question_id)
    try:
        query_result = await snapshot.query(
            question,
            question_index=question_index,
        )
    except _RelayLMReadOnlyQueryExecutionError as failure:
        record_relaylm_query_failure(
            durable_run=durable_run,
            question_id=question_id,
            failure=failure,
            request_evidence=request_evidence,
        )
        return None
    return commit_relaylm_query_result(
        durable_run=durable_run,
        question_id=question_id,
        query_result=query_result,
        request_evidence=request_evidence,
    )


def _normalize_live_launch_admission(
    raw: Mapping[str, object],
    *,
    allow_stable_extended: bool = False,
) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise ExternalQualificationError(
            "live launch/admission attestation must be an object"
        )
    keys = set(raw)
    if allow_stable_extended and keys == set(LIVE_LAUNCH_FROZEN_EXTENDED_FIELDS):
        # A FrozenExperimentIdentity stores only immutable extended runtime
        # facts. Reuse the live-attestation grammar with fixed placeholders,
        # then discard the per-launch fields below.
        normalized_live = _normalize_live_launch_admission(
            {
                **dict(raw),
                "launch_evidence_reference": "stable-identity",
                "runtime_ownership_evidence_reference": "stable-identity",
                "launch_observation": {
                    "runtime_evidence_path": "stable-identity",
                    "runtime_ownership_evidence_path": "stable-identity",
                    "pid": 1,
                    "memory_used_mib": "stable-identity",
                    "observed_at": "stable-identity",
                },
            }
        )
        return {
            **{
                name: _stable_capacity(normalized_live[name])
                if name == "capacity_evidence"
                else normalized_live[name]
                for name in LIVE_LAUNCH_STABLE_FIELDS
            },
            "runtime_identity": normalized_live["runtime_identity"],
            "gpu_identity": normalized_live["gpu_identity"],
        }
    legacy = keys == set(LIVE_LAUNCH_ADMISSION_FIELDS)
    extended = keys == set(LIVE_LAUNCH_ADMISSION_EXTENDED_FIELDS)
    if not legacy and not extended:
        _keys(raw, set(LIVE_LAUNCH_ADMISSION_FIELDS), "live launch/admission attestation")
    reservation = raw["effective_gpu_reservation"]
    if (
        isinstance(reservation, bool)
        or not isinstance(reservation, (int, float))
        or not _finite(reservation)
        or reservation <= 0
        or reservation > 1
    ):
        raise ExternalQualificationError(
            "live effective_gpu_reservation must be a finite number in (0, 1]"
        )
    admitted_context = raw["admitted_context"]
    if (
        isinstance(admitted_context, bool)
        or not isinstance(admitted_context, int)
        or admitted_context <= 0
    ):
        raise ExternalQualificationError(
            "live admitted_context must be a positive integer"
        )
    capacity_evidence = _json_value_copy(
        raw["capacity_evidence"],
        "live capacity_evidence",
    )
    if capacity_evidence is None:
        raise ExternalQualificationError(
            "live capacity_evidence must not be null"
        )
    normalized: dict[str, object] = {
        "backend": _text(raw["backend"], "live backend"),
        "runtime": _text(raw["runtime"], "live runtime"),
        "model_runner": _text(raw["model_runner"], "live model_runner"),
        "effective_gpu_reservation": reservation,
        "admitted_context": admitted_context,
        "capacity_evidence": capacity_evidence,
        "launch_evidence_reference": _text(
            raw["launch_evidence_reference"],
            "live launch_evidence_reference",
        ),
        "runtime_ownership_evidence_reference": _text(
            raw["runtime_ownership_evidence_reference"],
            "live runtime_ownership_evidence_reference",
        ),
    }
    if extended:
        runtime_identity = _mapping(raw["runtime_identity"], "live runtime_identity")
        required_runtime = {
            "upstream_revision",
            "build_info",
            "model_alias",
            "model_path",
            "artifact_sha256",
            "chat_template_sha256",
            "context_limit",
            "total_slots",
            "context_shift_enabled",
        }
        if set(runtime_identity) != required_runtime:
            _keys(runtime_identity, required_runtime, "live runtime_identity")
        normalized_runtime = _json_copy(dict(runtime_identity), "live runtime_identity")
        _commit(normalized_runtime["upstream_revision"], "live runtime upstream_revision")
        _sha256(normalized_runtime["artifact_sha256"], "live runtime artifact_sha256")
        _sha256(
            normalized_runtime["chat_template_sha256"],
            "live runtime chat_template_sha256",
        )
        for name in ("build_info", "model_alias", "model_path"):
            _text(normalized_runtime[name], f"live runtime {name}")
        for name in ("context_limit", "total_slots"):
            if (
                isinstance(normalized_runtime[name], bool)
                or not isinstance(normalized_runtime[name], int)
                or normalized_runtime[name] <= 0
            ):
                raise ExternalQualificationError(
                    f"live runtime {name} must be a positive integer"
                )
        if not isinstance(normalized_runtime["context_shift_enabled"], bool):
            raise ExternalQualificationError(
                "live runtime context_shift_enabled must be boolean"
            )

        gpu_identity = _mapping(raw["gpu_identity"], "live gpu_identity")
        _keys(
            gpu_identity,
            {"name", "driver_version", "memory_total_mib"},
            "live gpu_identity",
        )
        normalized_gpu = {
            name: _text(gpu_identity[name], f"live gpu_identity {name}")
            for name in ("name", "driver_version", "memory_total_mib")
        }

        observation = _mapping(raw["launch_observation"], "live launch_observation")
        _keys(
            observation,
            {
                "runtime_evidence_path",
                "runtime_ownership_evidence_path",
                "pid",
                "memory_used_mib",
                "observed_at",
            },
            "live launch_observation",
        )
        if (
            isinstance(observation["pid"], bool)
            or not isinstance(observation["pid"], int)
            or observation["pid"] <= 0
        ):
            raise ExternalQualificationError("live launch_observation pid is invalid")
        _text(observation["runtime_evidence_path"], "live runtime evidence path")
        _text(
            observation["runtime_ownership_evidence_path"],
            "live ownership evidence path",
        )
        _text(observation["memory_used_mib"], "live memory_used_mib")
        _text(observation["observed_at"], "live observed_at")
        normalized["runtime_identity"] = normalized_runtime
        normalized["gpu_identity"] = normalized_gpu
        normalized["launch_observation"] = _json_copy(
            dict(observation), "live launch_observation"
        )
    return normalized


def _stable_capacity(value: object) -> object:
    """Remove volatile GPU usage while retaining stable capacity facts."""

    copied = _json_value_copy(value, "capacity evidence")
    if isinstance(copied, dict):
        gpu = copied.get("gpu_identity")
        if isinstance(gpu, dict):
            gpu.pop("memory_used_mib", None)
            gpu.pop("used_memory_mib", None)
            copied["gpu_identity"] = gpu
        copied.pop("memory_used_mib", None)
        copied.pop("used_memory_mib", None)
    return copied


def _normalize_questions(
    questions: Sequence[DurableQuestion],
) -> tuple[DurableQuestion, ...]:
    if isinstance(questions, (str, bytes)) or not isinstance(questions, Sequence):
        raise ExternalQualificationError("durable questions must be a non-empty sequence")
    normalized = tuple(questions)
    if not normalized:
        raise ExternalQualificationError("durable questions must not be empty")
    if any(not isinstance(item, DurableQuestion) for item in normalized):
        raise ExternalQualificationError("durable questions must contain DurableQuestion values")
    ids = [item.question_id for item in normalized]
    if len(set(ids)) != len(ids):
        raise ExternalQualificationError("durable question IDs must be unique")
    return normalized


def _stable_durable_run_id(
    *,
    identity: FrozenExperimentIdentity,
    questions: tuple[DurableQuestion, ...],
) -> str:
    encoded = _canonical_json(
        {
            "identity": identity.to_mapping(),
            "identity_fingerprint": identity.fingerprint,
            "questions": [
                item.to_mapping(order=order)
                for order, item in enumerate(questions)
            ],
        }
    ).encode("utf-8")
    return f"durable-question-run-{hashlib.sha256(encoded).hexdigest()}"


def _sha256_mapping(value: Mapping[str, object]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(dict(value)).encode('utf-8')).hexdigest()}"


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ExternalQualificationError("durable evidence must be JSON-serializable") from exc


def _json_value_copy(value: object, label: str) -> object:
    try:
        copied = json.loads(_canonical_json(value))
    except ExternalQualificationError as exc:
        raise ExternalQualificationError(f"{label} must be JSON-serializable") from exc
    return copied


def _json_copy(value: object, label: str) -> dict[str, object]:
    copied = _json_value_copy(value, label)
    if not isinstance(copied, dict):
        raise ExternalQualificationError(f"{label} must be an object")
    return copied


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExactResumeError(f"cannot load {label}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ExactResumeError(f"{label} must be an object")
    return raw


def _write_json_atomically(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json(dict(value)) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ExternalQualificationError(f"cannot persist durable run state: {exc}") from exc


def time_now() -> int:
    """Return a content-free heartbeat timestamp without affecting run identity."""

    import time

    return time.time_ns()


def validate_release_identity(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"schema_version", "package", "version", "release_kind", "tag", "commit", "artifacts"}, "release identity")
    if raw["schema_version"] != 1 or raw["package"] != "relaylm":
        raise ExternalQualificationError("release identity must be RelayLM schema v1")
    version = _text(raw["version"], "release version")
    try:
        parsed = parse_release_version(version)
    except ReleaseIdentityError as exc:
        raise ExternalQualificationError(str(exc)) from exc
    if parsed.kind not in {"rc", "final"}:
        raise ExternalQualificationError("citable qualification requires an rc or final identity")
    if raw["release_kind"] != parsed.kind or raw["tag"] != expected_release_tag(parsed):
        raise ExternalQualificationError("release kind/tag does not match release version")
    commit = _commit(raw["commit"], "release commit")
    artifacts = raw["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ExternalQualificationError("release identity must contain exactly wheel and sdist")
    normalized_artifacts = []
    for item in artifacts:
        item = _mapping(item, "release artifact")
        _keys(item, {"filename", "sha256"}, "release artifact")
        normalized_artifacts.append(
            {"filename": _text(item["filename"], "artifact filename"), "sha256": _sha256(item["sha256"], "artifact sha256")}
        )
    names = {item["filename"] for item in normalized_artifacts}
    wheels = [name for name in names if name.startswith(f"relaylm-{version}-") and name.endswith(".whl")]
    if f"relaylm-{version}.tar.gz" not in names or len(wheels) != 1:
        raise ExternalQualificationError("release artifacts must be version-matching wheel and sdist")
    return {
        "schema_version": 1,
        "package": "relaylm",
        "version": version,
        "release_kind": parsed.kind,
        "tag": raw["tag"],
        "commit": commit,
        "artifacts": sorted(normalized_artifacts, key=lambda item: item["filename"]),
    }


def validate_case(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"case_id", "axis", "benchmark", "dataset", "adapter_case_ref"}, "benchmark case")
    benchmark = _mapping(raw["benchmark"], "benchmark")
    dataset = _mapping(raw["dataset"], "dataset")
    _keys(benchmark, {"id", "repository", "revision", "license"}, "benchmark")
    _keys(dataset, {"revision", "license"}, "dataset")
    return {
        "case_id": _text(raw["case_id"], "case_id"),
        "axis": _text(raw["axis"], "axis"),
        "benchmark": {key: _text(benchmark[key], f"benchmark {key}") for key in ("id", "repository", "revision", "license")},
        "dataset": {key: _text(dataset[key], f"dataset {key}") for key in ("revision", "license")},
        "adapter_case_ref": _text(raw["adapter_case_ref"], "adapter_case_ref"),
    }


def validate_manifest(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"format_version", "purpose", "harness", "adapter", "participants", "relaylm_release", "judge", "replicate_id"}, "manifest")
    if raw["format_version"] != FORMAT_VERSION:
        raise ExternalQualificationError(f"unsupported format_version: {raw['format_version']}")
    purpose = _text(raw["purpose"], "purpose")
    if purpose not in PURPOSES:
        raise ExternalQualificationError(f"unsupported purpose: {purpose}")
    harness = _revision_identity(raw["harness"], "harness")
    adapter = _revision_identity(raw["adapter"], "adapter")
    replicate_id = _text(raw["replicate_id"], "replicate_id")
    judge = _optional_judge(raw["judge"])

    participants = raw["participants"]
    if not isinstance(participants, list) or len(participants) != len(SLOTS):
        raise ExternalQualificationError("participants must be canonical A/B/C/D slots")
    normalized_participants = [_participant(item) for item in participants]
    if tuple(item["slot"] for item in normalized_participants) != SLOTS:
        raise ExternalQualificationError("participants must be canonical A/B/C/D slots")
    plans = {item["slot"]: item for item in normalized_participants}

    release = None if raw["relaylm_release"] is None else validate_release_identity(_mapping(raw["relaylm_release"], "relaylm_release"))
    if purpose != "release_qualification":
        if release is not None:
            raise ExternalQualificationError("pre-RC dry/smoke evidence must not carry a citable #1447 release identity")
    else:
        if release is None:
            raise ExternalQualificationError("release_qualification is blocked until exact #1447 release identity is supplied")
        for slot in ("same_model_direct", "serious_comparator", "relaylm_exact_rc"):
            if plans[slot]["identity"] is None:
                raise ExternalQualificationError(f"release_qualification requires enabled {slot}")
        direct = plans["same_model_direct"]["identity"]
        relay = plans["relaylm_exact_rc"]["identity"]
        assert isinstance(direct, dict) and isinstance(relay, dict)
        if relay["version"] != release["version"] or relay["source_revision"] != release["commit"]:
            raise ExternalQualificationError("RelayLM slot must match exact release version and commit")
        if direct["physical_model"] != relay["physical_model"]:
            raise ExternalQualificationError("same_model_direct must match RelayLM physical model/tokenizer/quantization")

    return {
        "format_version": FORMAT_VERSION,
        "purpose": purpose,
        "citable": purpose == "release_qualification",
        "harness": harness,
        "adapter": adapter,
        "participants": normalized_participants,
        "relaylm_release": release,
        "judge": judge,
        "replicate_id": replicate_id,
    }


def validate_observation(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"quality", "tokens", "latency", "resources", "known_limitations", "failure"}, "observation")
    quality = _mapping(raw["quality"], "quality")
    normalized_quality: dict[str, int | float] = {}
    for key, value in quality.items():
        key = _text(key, "benchmark metric name")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not _finite(value):
            raise ExternalQualificationError("benchmark-native metric values must be finite numbers")
        normalized_quality[key] = value

    tokens = _mapping(raw["tokens"], "tokens")
    latency = _mapping(raw["latency"], "latency")
    resources = _mapping(raw["resources"], "resources")
    _keys(tokens, {"model_input_tokens", "model_output_tokens", "model_call_count"}, "tokens")
    _keys(latency, {"ttft_ms", "query_latency_ms", "end_to_end_ms"}, "latency")
    _keys(resources, {"peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes", "notes"}, "resources")
    for name, value in tokens.items():
        _non_negative(value, f"tokens {name}")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ExternalQualificationError(f"tokens {name} must be an integer or null")
    if tokens["model_call_count"] is None:
        raise ExternalQualificationError("model_call_count must not be null")
    for name, value in latency.items():
        _non_negative(value, f"latency {name}")
    for name in ("peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes"):
        value = resources[name]
        _non_negative(value, f"resources {name}")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ExternalQualificationError(f"resources {name} must be an integer or null")
    notes = _text_list(resources["notes"], "resource notes")
    limitations = _text_list(raw["known_limitations"], "known_limitations")
    failure = None if raw["failure"] is None else _text(raw["failure"], "failure")
    return {
        "quality": normalized_quality,
        "tokens": dict(tokens),
        "latency": dict(latency),
        "resources": {**{name: resources[name] for name in ("peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes")}, "notes": notes},
        "known_limitations": limitations,
        "failure": failure,
    }


def validate_participant_accounting(
    *,
    observation: Mapping[str, object],
    semantic_generation_count: int,
    answer_model_generation_count: int,
    judge_call_count: int,
    allow_zero_model_operation: bool = False,
) -> dict[str, object]:
    """Reject impossible counter combinations at the participant boundary."""

    normalized = validate_observation(observation)
    counters = {
        "semantic_generation_count": semantic_generation_count,
        "answer_model_generation_count": answer_model_generation_count,
        "judge_call_count": judge_call_count,
    }
    for name, value in counters.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExternalQualificationError(f"{name} must be a non-negative integer")
    tokens = normalized["tokens"]
    assert isinstance(tokens, dict)
    model_call_count = tokens["model_call_count"]
    assert isinstance(model_call_count, int)
    required_calls = sum(counters.values())
    if model_call_count < required_calls:
        raise ExternalQualificationError(
            "participant counters contradict observation.tokens.model_call_count"
        )
    if (
        normalized["failure"] is None
        and model_call_count == 0
        and not allow_zero_model_operation
    ):
        raise ExternalQualificationError(
            "successful scientific participant observation cannot have zero model calls"
        )
    return normalized


Executor = Callable[[Mapping[str, object], Mapping[str, object]], Mapping[str, object]]


def run_case(
    *,
    manifest: Mapping[str, object],
    case: Mapping[str, object],
    classification: str,
    executors: Mapping[str, Executor],
) -> dict[str, object]:
    manifest = validate_manifest(manifest)
    case = validate_case(case)
    if classification not in CLASSIFICATIONS:
        raise ExternalQualificationError(f"unsupported result classification: {classification}")
    results = []
    for plan in manifest["participants"]:
        assert isinstance(plan, dict)
        slot = plan["slot"]
        identity = plan["identity"]
        if identity is None:
            results.append({"slot": slot, "observation": None, "omission_reason": plan["omission_reason"]})
            continue
        executor = executors.get(slot)
        if executor is None:
            raise ExternalQualificationError(f"missing executor for enabled {slot}")
        observation = validate_observation(_mapping(executor(case, identity), f"{slot} observation"))
        results.append({"slot": slot, "observation": observation, "omission_reason": None})
    run_id = stable_run_id(manifest=manifest, case=case)
    return {
        "format_version": FORMAT_VERSION,
        "run_id": run_id,
        "manifest": manifest,
        "case": case,
        "classification": classification,
        "results": results,
    }


def stable_run_id(*, manifest: Mapping[str, object], case: Mapping[str, object]) -> str:
    manifest = _validated_manifest(manifest)
    case = validate_case(case)
    encoded = json.dumps({"manifest": manifest, "case": case}, sort_keys=True, separators=(",", ":")).encode()
    return f"external-qualification-{hashlib.sha256(encoded).hexdigest()}"


def write_evidence(*, evidence: Mapping[str, object], artifact_root: str | Path) -> Path:
    evidence = dict(evidence)
    base_keys = {"format_version", "run_id", "manifest", "case", "classification", "results"}
    allowed_keys = base_keys | {"campaign"}
    if set(evidence) != base_keys and set(evidence) != allowed_keys:
        _keys(evidence, base_keys, "evidence")
    if evidence["format_version"] != FORMAT_VERSION:
        raise ExternalQualificationError("unsupported evidence format_version")
    manifest = _validated_manifest(_mapping(evidence["manifest"], "evidence manifest"))
    case = validate_case(_mapping(evidence["case"], "evidence case"))
    expected = stable_run_id(manifest=manifest, case=case)
    if evidence["run_id"] != expected:
        raise ExternalQualificationError("run_id does not match manifest and case")
    classification = evidence["classification"]
    if classification not in CLASSIFICATIONS:
        raise ExternalQualificationError("unsupported result classification")
    results = _evidence_results(evidence["results"])
    normalized_evidence: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "run_id": expected,
        "manifest": manifest,
        "case": case,
        "classification": classification,
        "results": results,
    }
    if "campaign" in evidence:
        normalized_evidence["campaign"] = _campaign_evidence(
            _mapping(evidence["campaign"], "campaign evidence")
        )
    evidence = normalized_evidence
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{expected}.json"
    payload = json.dumps(evidence, sort_keys=True, indent=2) + "\n"
    if path.exists():
        return _existing(path, payload)
    temporary = root / f".{expected}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _existing(path, payload)
    except OSError as exc:
        raise ExternalQualificationError(f"cannot persist external qualification evidence: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def write_citable_evidence(
    *,
    evidence: Mapping[str, object],
    artifact_root: str | Path,
    campaign: Mapping[str, object],
) -> Path:
    """Persist canonical external evidence with controller-owned campaign linkage."""

    payload = dict(evidence)
    payload["campaign"] = dict(campaign)
    return write_evidence(evidence=payload, artifact_root=artifact_root)


def _campaign_evidence(raw: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "campaign_fingerprint",
        "frozen_experiment_fingerprint",
        "qualification_authority",
        "hindsight_health_fingerprint",
        "live_runtime_identity",
        "live_launch_observation",
        "live_runtime_evidence_reference",
        "live_runtime_ownership_evidence_reference",
        "question_results",
        "counters",
    }
    _keys(raw, expected, "campaign evidence")
    for name in (
        "campaign_fingerprint",
        "frozen_experiment_fingerprint",
        "hindsight_health_fingerprint",
    ):
        value = _text(raw[name], f"campaign evidence {name}")
        if not value.startswith("sha256:"):
            raise ExternalQualificationError(
                f"campaign evidence {name} must be a content fingerprint"
            )
    authority = _mapping(raw["qualification_authority"], "campaign qualification authority")
    if authority.get("status") != "CURRENT_AUTHORITY_CONFIRMED":
        raise ExternalQualificationError("campaign evidence authority is not current")
    for name in ("branch", "repository_head", "repository_tree"):
        if name not in authority:
            raise ExternalQualificationError(
                "campaign evidence authority requires exact branch/head/tree"
            )
    _commit(authority["repository_head"], "campaign repository_head")
    _commit(authority["repository_tree"], "campaign repository_tree")
    _text(authority["branch"], "campaign authority branch")
    runtime = _mapping(raw["live_runtime_identity"], "campaign live runtime identity")
    for name in (
        "upstream_revision",
        "build_info",
        "model_alias",
        "model_path",
        "artifact_sha256",
        "chat_template_sha256",
        "context_limit",
        "total_slots",
        "context_shift_enabled",
    ):
        if name not in runtime:
            raise ExternalQualificationError(
                f"campaign live runtime identity is missing {name}"
            )
    _commit(runtime["upstream_revision"], "campaign runtime upstream_revision")
    _sha256(runtime["artifact_sha256"], "campaign runtime artifact_sha256")
    _sha256(runtime["chat_template_sha256"], "campaign runtime chat_template_sha256")
    observation = _mapping(
        raw["live_launch_observation"], "campaign live launch observation"
    )
    _keys(
        observation,
        {
            "runtime_evidence_path",
            "runtime_ownership_evidence_path",
            "pid",
            "memory_used_mib",
            "observed_at",
        },
        "campaign live launch observation",
    )
    if (
        isinstance(observation["pid"], bool)
        or not isinstance(observation["pid"], int)
        or observation["pid"] <= 0
    ):
        raise ExternalQualificationError("campaign live launch observation pid is invalid")
    for name in (
        "runtime_evidence_path",
        "runtime_ownership_evidence_path",
        "memory_used_mib",
        "observed_at",
        "live_runtime_evidence_reference",
        "live_runtime_ownership_evidence_reference",
    ):
        _text(
            observation[name]
            if name in observation
            else raw[name],
            f"campaign {name}",
        )
    question_results = raw["question_results"]
    if not isinstance(question_results, list):
        raise ExternalQualificationError("campaign question_results must be a list")
    counters = _mapping(raw["counters"], "campaign counters")
    for name in (
        "semantic_generation_count",
        "benchmark_question_count",
        "answer_model_generation_count",
        "judge_call_count",
    ):
        value = counters.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExternalQualificationError(f"campaign counter {name} is invalid")
    return {
        "campaign_fingerprint": _text(raw["campaign_fingerprint"], "campaign_fingerprint"),
        "frozen_experiment_fingerprint": _text(
            raw["frozen_experiment_fingerprint"], "frozen_experiment_fingerprint"
        ),
        "qualification_authority": _json_copy(dict(authority), "campaign authority"),
        "hindsight_health_fingerprint": _text(
            raw["hindsight_health_fingerprint"], "hindsight_health_fingerprint"
        ),
        "live_runtime_identity": _json_copy(dict(runtime), "campaign runtime identity"),
        "live_launch_observation": _json_copy(
            dict(observation), "campaign live launch observation"
        ),
        "live_runtime_evidence_reference": _text(
            raw["live_runtime_evidence_reference"],
            "campaign live_runtime_evidence_reference",
        ),
        "live_runtime_ownership_evidence_reference": _text(
            raw["live_runtime_ownership_evidence_reference"],
            "campaign live_runtime_ownership_evidence_reference",
        ),
        "question_results": _json_value_copy(question_results, "campaign question_results"),
        "counters": _json_copy(dict(counters), "campaign counters"),
    }


def _evidence_results(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list) or len(raw) != len(SLOTS):
        raise ExternalQualificationError("evidence results must contain canonical A/B/C/D slots")
    normalized = []
    for expected_slot, item in zip(SLOTS, raw, strict=True):
        item = _mapping(item, "evidence result")
        _keys(item, {"slot", "observation", "omission_reason"}, "evidence result")
        if item["slot"] != expected_slot:
            raise ExternalQualificationError("evidence results must contain canonical A/B/C/D slots")
        observation = item["observation"]
        omission = item["omission_reason"]
        if observation is None:
            omission = _text(omission, "omission_reason")
        else:
            observation = validate_observation(_mapping(observation, "evidence observation"))
            if omission is not None:
                raise ExternalQualificationError("executed evidence result must not have omission_reason")
        normalized.append({"slot": expected_slot, "observation": observation, "omission_reason": omission})
    return normalized


def _validated_manifest(raw: Mapping[str, object]) -> dict[str, object]:
    if "citable" not in raw:
        return validate_manifest(raw)
    raw = dict(raw)
    raw.pop("citable")
    return validate_manifest(raw)


def _participant(raw: object) -> dict[str, object]:
    raw = _mapping(raw, "participant")
    _keys(raw, {"slot", "identity", "omission_reason"}, "participant")
    slot = _text(raw["slot"], "participant slot")
    if slot not in SLOTS:
        raise ExternalQualificationError(f"unsupported architecture slot: {slot}")
    identity = None if raw["identity"] is None else _participant_identity(raw["identity"])
    omission = raw["omission_reason"]
    if identity is None:
        omission = _text(omission, "omission_reason")
    elif omission is not None:
        raise ExternalQualificationError("enabled participant must not have omission_reason")
    return {"slot": slot, "identity": identity, "omission_reason": omission}


def _participant_identity(raw: object) -> dict[str, object]:
    raw = _mapping(raw, "participant identity")
    keys = {
        "implementation", "source_revision", "version", "deployment", "license", "physical_model",
        "provider", "backend", "runtime", "context_capacity", "decoding", "reasoning", "hardware",
        "retry_policy", "matched_condition_differences",
    }
    _keys(raw, keys, "participant identity")
    physical = _mapping(raw["physical_model"], "physical_model")
    hardware = _mapping(raw["hardware"], "hardware")
    _keys(physical, {"artifact", "tokenizer", "quantization"}, "physical_model")
    _keys(hardware, {"gpu", "cpu", "offload"}, "hardware")
    capacity = raw["context_capacity"]
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        raise ExternalQualificationError("context_capacity must be a positive integer")
    decoding = _string_mapping(raw["decoding"], "decoding")
    reasoning = _string_mapping(raw["reasoning"], "reasoning")
    return {
        "implementation": _text(raw["implementation"], "implementation"),
        "source_revision": _commit(raw["source_revision"], "source_revision"),
        "version": _text(raw["version"], "version"),
        "deployment": _text(raw["deployment"], "deployment"),
        "license": _text(raw["license"], "license"),
        "physical_model": {name: _text(physical[name], f"physical_model {name}") for name in ("artifact", "tokenizer", "quantization")},
        **{name: _text(raw[name], name) for name in ("provider", "backend", "runtime")},
        "context_capacity": capacity,
        "decoding": decoding,
        "reasoning": reasoning,
        "hardware": {name: _text(hardware[name], f"hardware {name}") for name in ("gpu", "cpu", "offload")},
        "retry_policy": _text(raw["retry_policy"], "retry_policy"),
        "matched_condition_differences": _text_list(raw["matched_condition_differences"], "matched_condition_differences"),
    }


def _revision_identity(raw: object, name: str) -> dict[str, str]:
    raw = _mapping(raw, name)
    _keys(raw, {"identity", "revision"}, name)
    return {"identity": _text(raw["identity"], f"{name} identity"), "revision": _commit(raw["revision"], f"{name} revision")}


def _optional_judge(raw: object) -> dict[str, str] | None:
    if raw is None:
        return None
    raw = _mapping(raw, "judge")
    _keys(raw, {"identity", "policy"}, "judge")
    return {"identity": _text(raw["identity"], "judge identity"), "policy": _text(raw["policy"], "judge policy")}


def _existing(path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExternalQualificationError(f"cannot read existing evidence: {exc}") from exc
    if existing == payload:
        return path
    raise ExternalQualificationError("run ID already exists with different evidence; use a distinct replicate_id")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ExternalQualificationError(f"{name} must be an object")
    return value


def _keys(raw: Mapping[str, object], expected: set[str], name: str) -> None:
    if set(raw) != expected:
        raise ExternalQualificationError(f"{name} fields must be exactly: {', '.join(sorted(expected))}")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalQualificationError(f"{name} must be a non-empty string")
    return value


def _commit(value: object, name: str) -> str:
    value = _text(value, name)
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ExternalQualificationError(f"{name} must be a lowercase 40-hex commit SHA")
    return value


def _sha256(value: object, name: str) -> str:
    value = _text(value, name)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ExternalQualificationError(f"{name} must be a lowercase 64-hex sha256")
    return value


def _string_mapping(value: object, name: str) -> dict[str, str]:
    value = _mapping(value, name)
    return {_text(key, f"{name} key"): _text(item, f"{name} value") for key, item in value.items()}


def _text_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ExternalQualificationError(f"{name} must be a list")
    return [_text(item, name) for item in value]


def _finite(value: int | float) -> bool:
    return not isinstance(value, float) or float("-inf") < value < float("inf")


def _non_negative(value: object, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or not _finite(value):
        raise ExternalQualificationError(f"{name} must be a finite non-negative number or null")
