"""MemConflict's RelayLM adapter boundary.

The public benchmark supplies session dialogue for ingestion and independent
questions for recall/answering.  This module keeps those two operations
separate without adding a benchmark branch to RelayLM Core: dialogue is
appended to the live package once, while every question runs the ordinary
RelayLM turn on a fresh clone of the frozen post-dialogue package.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from relaylm.cognitive import (
    CognitiveInput,
    ContextItem,
    EventEvidenceItem,
    RetrievedMemoryItem,
)
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionExtractionInput,
    CognitionPassRequest,
)
from relaylm.continuity import ContinuityContext
from relaylm.events import Event
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.state import StateRecord
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    run_user_turn,
)
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionStatus,
    run_user_turn_two_pass,
)


QueryMode = Literal["single_pass", "two_pass"]
FailurePhase = Literal["single_pass", "pass1", "pass2"]


class MemConflictAdapterError(ValueError):
    """The external adapter boundary received invalid or unsafe input."""


class RelayLMReadOnlyQueryExecutionError(RuntimeError):
    """A provider call failed before the isolated query could return a result."""

    def __init__(
        self,
        *,
        phase: FailurePhase,
        diagnostics: tuple["ReadOnlyQueryFailureDiagnostic", ...],
        adapter_mechanics: Mapping[str, object],
    ) -> None:
        super().__init__(f"isolated RelayLM query {phase} provider call failed")
        self.phase = phase
        self.diagnostics = diagnostics
        self.adapter_mechanics = dict(adapter_mechanics)

    def to_external_evidence(self) -> dict[str, object]:
        """Return bounded failure evidence for an in-flight durable question."""

        return {
            "adapter_mechanics": dict(self.adapter_mechanics),
            "pass": self.phase,
            "status": "failed",
            "failure_diagnostics": [
                item.to_mapping() for item in self.diagnostics
            ],
        }


@dataclass(frozen=True, slots=True)
class ReadOnlyQueryFailureDiagnostic:
    """The bounded #1871 failure identity carried into external evidence."""

    turn_index: int
    phase: FailurePhase
    exception_type: str
    exception_message: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("failure diagnostic turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("failure diagnostic turn_index must be positive")
        if self.phase not in {"single_pass", "pass1", "pass2"}:
            raise ValueError(f"unsupported failure diagnostic phase: {self.phase}")
        if not isinstance(self.exception_type, str) or not self.exception_type.strip():
            raise ValueError("failure diagnostic exception_type must be non-empty")
        if self.exception_message is not None and (
            not isinstance(self.exception_message, str)
            or not self.exception_message.strip()
        ):
            raise ValueError(
                "failure diagnostic exception_message must be non-empty when present"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "phase": self.phase,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
        }


@dataclass(frozen=True, slots=True)
class AnswerTimeEvidence:
    """Exactly the RelayLM evidence supplied to one answer-time turn.

    ``knowledge`` is deliberately absent.  Package KNOWLEDGE is still present
    in the ordinary ``CognitiveInput`` sent to the provider, but it is never
    relabeled as retrieved lived memory in the external evidence projection.
    """

    context: tuple[ContextItem, ...]
    memory: tuple[RetrievedMemoryItem, ...]
    event: tuple[EventEvidenceItem, ...]
    state: tuple[StateRecord, ...]

    @classmethod
    def from_cognitive_input(cls, cognitive_input: CognitiveInput) -> "AnswerTimeEvidence":
        return cls(
            context=cognitive_input.context,
            memory=cognitive_input.memory,
            event=cognitive_input.event_evidence,
            state=cognitive_input.state,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "context": [
                {
                    "content": item.content,
                    "sources": list(item.sources),
                    "actor": item.actor,
                }
                for item in self.context
            ],
            "memory": [
                {
                    "content": item.content,
                    "location": item.location,
                }
                for item in self.memory
            ],
            "event": [
                {
                    "event_id": item.event_id,
                    "event_type": item.event_type,
                    "actor": item.actor,
                    "timestamp": item.timestamp,
                    "content": item.content,
                }
                for item in self.event
            ],
            "state": [_state_record_mapping(item) for item in self.state],
        }

    def retrieved_memories_projection(self) -> tuple[dict[str, object], ...]:
        """Project only selected MEMORY/Event/State with an explicit source role."""

        projected: list[dict[str, object]] = []
        projected.extend(
            {
                "source_role": "memory",
                "content": item.content,
                "location": item.location,
            }
            for item in self.memory
        )
        projected.extend(
            {
                "source_role": "event",
                "content": item.content,
                "event_id": item.event_id,
                "event_type": item.event_type,
                "actor": item.actor,
                "timestamp": item.timestamp,
            }
            for item in self.event
        )
        projected.extend(
            {
                "source_role": "state",
                **_state_record_mapping(item),
            }
            for item in self.state
        )
        return tuple(projected)


@dataclass(frozen=True, slots=True)
class RelayLMQueryResult:
    """One isolated ordinary RelayLM answer and its answer-time evidence."""

    response: str
    cognitive_input: CognitiveInput
    pass1_completion: CognitionCompletionMetadata | None = None
    pass2_completion: CognitionCompletionMetadata | None = None
    pass2_status: str | None = None
    pass2_failure_reason: str | None = None
    failure_diagnostics: tuple[ReadOnlyQueryFailureDiagnostic, ...] = ()
    adapter_mechanics: tuple[tuple[str, object], ...] = ()

    @property
    def answer_time_evidence(self) -> AnswerTimeEvidence:
        return AnswerTimeEvidence.from_cognitive_input(self.cognitive_input)

    def to_external_evidence(self) -> dict[str, object]:
        """Return JSON-shaped evidence suitable for DurableQuestionRun."""

        return {
            "answer": self.response,
            "adapter_mechanics": dict(self.adapter_mechanics),
            "answer_time_evidence": self.answer_time_evidence.to_mapping(),
            "retrieved_memories": list(
                self.answer_time_evidence.retrieved_memories_projection()
            ),
            "pass1_completion": _completion_mapping(self.pass1_completion),
            "pass2_completion": _completion_mapping(self.pass2_completion),
            "pass2_status": self.pass2_status,
            "pass2_failure_reason": self.pass2_failure_reason,
            "failure_diagnostics": [
                item.to_mapping() for item in self.failure_diagnostics
            ],
        }


class RelayLMFrozenQuerySnapshot:
    """A post-dialogue snapshot whose questions execute on disposable clones."""

    def __init__(
        self,
        *,
        snapshot_root: Path,
        temporary_directory: TemporaryDirectory,
        provider: object,
        mode: QueryMode,
        memory_budget: MemoryRetrievalBudget | None,
        event_budget: EventRetrievalBudget | None,
        continuity_context: ContinuityContext | None,
        continuity_lifetime_revisions: int,
        cognitive_budget: object | None,
        pass_request: CognitionPassRequest | None,
        pass1_request: CognitionPassRequest | None,
        pass2_request: CognitionPassRequest | None,
        snapshot_fingerprint: str,
    ) -> None:
        self.root = snapshot_root
        self._temporary_directory = temporary_directory
        self._provider = provider
        self._mode = mode
        self._memory_budget = memory_budget
        self._event_budget = event_budget
        self._continuity_context = continuity_context
        self._continuity_lifetime_revisions = continuity_lifetime_revisions
        self._cognitive_budget = cognitive_budget
        self._pass_request = pass_request
        self._pass1_request = pass1_request
        self._pass2_request = pass2_request
        self.snapshot_fingerprint = snapshot_fingerprint
        self._closed = False

    @property
    def mechanics(self) -> dict[str, object]:
        """The adapter mechanics that must accompany external evidence."""

        ordinary_turn_path = {
            "single_pass": "relaylm.turn.run_user_turn",
            "two_pass": "relaylm.two_pass_turn.run_user_turn_two_pass",
        }[self._mode]
        return {
            "dialogue_ingest": "ordinary message Event append_event",
            "question_snapshot": "frozen post-dialogue package",
            "question_isolation": "fresh package clone per question, discarded after turn",
            "question_ingest": "none into live or frozen package",
            "answer_ingest": "none into live or frozen package",
            "ordinary_turn_path": ordinary_turn_path,
            "retry_policy": "no semantic retry or fallback",
            "snapshot_fingerprint": self.snapshot_fingerprint,
        }

    def __enter__(self) -> "RelayLMFrozenQuerySnapshot":
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._temporary_directory.cleanup()
            self._closed = True

    async def query(
        self,
        question: str,
        *,
        question_index: int = 1,
    ) -> RelayLMQueryResult:
        """Run exactly one ordinary RelayLM question against this snapshot."""

        if self._closed:
            raise MemConflictAdapterError("frozen query snapshot is closed")
        if not isinstance(question, str) or not question.strip():
            raise MemConflictAdapterError("evaluation question must not be empty")
        if isinstance(question_index, bool) or not isinstance(question_index, int):
            raise TypeError("question_index must be an integer")
        if question_index <= 0:
            raise ValueError("question_index must be positive")

        with TemporaryDirectory(prefix="relaylm-2047-question-") as query_directory:
            query_root = Path(query_directory) / "package"
            shutil.copytree(self.root, query_root, symlinks=True)
            package = CognitivePackageDirectory(query_root)
            observer = _ObservingProvider(
                self._provider,
                turn_index=question_index,
            )
            continuity_runtime = self._continuity_runtime()
            try:
                if self._mode == "single_pass":
                    turn = await run_user_turn(
                        character=package,
                        provider=observer,
                        content=question,
                        memory_budget=self._memory_budget,
                        event_budget=self._event_budget,
                        continuity_runtime=continuity_runtime,
                        cognitive_budget=self._cognitive_budget,
                        pass_request=self._pass_request,
                    )
                    return RelayLMQueryResult(
                        response=turn.response,
                        cognitive_input=_require_input(observer),
                        failure_diagnostics=tuple(observer.failures),
                        adapter_mechanics=tuple(self.mechanics.items()),
                    )

                turn = await run_user_turn_two_pass(
                    character=package,
                    provider=observer,
                    content=question,
                    execution_runtime=CognitionExecutionRuntime(),
                    memory_budget=self._memory_budget,
                    event_budget=self._event_budget,
                    continuity_runtime=continuity_runtime,
                    cognitive_budget=self._cognitive_budget,
                    pass1_request=self._pass1_request,
                    pass2_request=self._pass2_request,
                )
                extraction = await turn.extraction
                status = extraction.status
                if isinstance(status, TwoPassExtractionStatus):
                    status_text = status.value
                else:
                    status_text = str(status)
                return RelayLMQueryResult(
                    response=turn.response,
                    cognitive_input=_require_input(observer),
                    pass1_completion=turn.conversation_completion,
                    pass2_completion=extraction.completion,
                    pass2_status=status_text,
                    pass2_failure_reason=extraction.failure_reason,
                    failure_diagnostics=tuple(observer.failures),
                    adapter_mechanics=tuple(self.mechanics.items()),
                )
            except Exception as exc:
                if observer.failures:
                    raise RelayLMReadOnlyQueryExecutionError(
                        phase=observer.failures[-1].phase,
                        diagnostics=tuple(observer.failures),
                        adapter_mechanics=self.mechanics,
                    ) from exc
                raise

    def _continuity_runtime(self) -> ContinuityRuntime | None:
        if self._continuity_context is None:
            return None
        return ContinuityRuntime(
            context=self._continuity_context,
            lifetime_revisions=self._continuity_lifetime_revisions,
        )


class RelayLMReadOnlyQueryAdapter:
    """Ingest sessions normally, then produce frozen query snapshots."""

    def __init__(
        self,
        *,
        package_root: str | Path,
        provider: object,
        mode: QueryMode = "two_pass",
        memory_budget: MemoryRetrievalBudget | None = None,
        event_budget: EventRetrievalBudget | None = None,
        continuity_context: ContinuityContext | None = None,
        continuity_lifetime_revisions: int = 4,
        cognitive_budget: object | None = None,
        pass_request: CognitionPassRequest | None = None,
        pass1_request: CognitionPassRequest | None = None,
        pass2_request: CognitionPassRequest | None = None,
    ) -> None:
        if mode not in {"single_pass", "two_pass"}:
            raise MemConflictAdapterError(f"unsupported query mode: {mode}")
        if mode == "single_pass" and (
            pass1_request is not None or pass2_request is not None
        ):
            raise MemConflictAdapterError(
                "single_pass adapter must not receive two-pass requests"
            )
        if mode == "two_pass" and pass_request is not None:
            raise MemConflictAdapterError(
                "two_pass adapter must not receive a single-pass request"
            )
        if continuity_context is not None:
            ContinuityRuntime(
                context=continuity_context,
                lifetime_revisions=continuity_lifetime_revisions,
            )

        self.root = Path(package_root)
        self._package = CognitivePackageDirectory(self.root)
        self._package.load_config()
        self._provider = provider
        self._mode = mode
        self._memory_budget = memory_budget
        self._event_budget = event_budget
        self._continuity_context = continuity_context
        self._continuity_lifetime_revisions = continuity_lifetime_revisions
        self._cognitive_budget = cognitive_budget
        self._pass_request = pass_request
        self._pass1_request = pass1_request
        self._pass2_request = pass2_request
        self._snapshots: list[RelayLMFrozenQuerySnapshot] = []
        self._closed = False

    def __enter__(self) -> "RelayLMReadOnlyQueryAdapter":
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            for snapshot in self._snapshots:
                snapshot.close()
            self._snapshots.clear()
            self._closed = True

    def ingest_session_dialogue(
        self,
        dialogue: Iterable[Mapping[str, object]],
        *,
        session_id: str = "default",
        session_index: int = 0,
    ) -> tuple[Event, ...]:
        """Append shared-harness role/content messages as ordinary Events.

        The adapter accepts only the flattened dialogue shape.  Evaluation
        question/answer fields are not accepted here and therefore cannot be
        accidentally ingested by this boundary.
        """

        self._require_open()
        if not isinstance(session_id, str) or not session_id.strip():
            raise MemConflictAdapterError("session_id must be non-empty")
        if isinstance(session_index, bool) or not isinstance(session_index, int):
            raise TypeError("session_index must be an integer")
        if session_index < 0:
            raise ValueError("session_index must not be negative")

        appended: list[Event] = []
        for message_index, message in enumerate(dialogue):
            if not isinstance(message, Mapping):
                raise MemConflictAdapterError("dialogue entries must be objects")
            role = message.get("role", message.get("actor"))
            content = message.get("content")
            if role not in {"user", "assistant"}:
                raise MemConflictAdapterError(
                    "dialogue role must be user or assistant"
                )
            if not isinstance(content, str) or not content.strip():
                raise MemConflictAdapterError(
                    "dialogue content must be a non-empty string"
                )
            timestamp = message.get("timestamp")
            if timestamp is not None and (
                not isinstance(timestamp, str) or not timestamp.strip()
            ):
                raise MemConflictAdapterError(
                    "dialogue timestamp must be a non-empty string when provided"
                )
            event_id = _dialogue_event_id(
                session_id=session_id,
                session_index=session_index,
                message_index=message_index,
                role=role,
                content=content,
            )
            event = Event.create(
                type="message",
                actor=role,
                payload={"content": content},
                event_id=event_id,
                timestamp=timestamp,
            )
            self._package.append_event(event)
            appended.append(event)
        return tuple(appended)

    def freeze(self) -> RelayLMFrozenQuerySnapshot:
        """Freeze the current post-dialogue package for one session's questions."""

        self._require_open()
        self._package.load_config()
        temporary_directory = TemporaryDirectory(prefix="relaylm-2047-snapshot-")
        snapshot_root = Path(temporary_directory.name) / "package"
        try:
            shutil.copytree(self.root, snapshot_root, symlinks=True)
            snapshot = RelayLMFrozenQuerySnapshot(
                snapshot_root=snapshot_root,
                temporary_directory=temporary_directory,
                provider=self._provider,
                mode=self._mode,
                memory_budget=self._memory_budget,
                event_budget=self._event_budget,
                continuity_context=self._continuity_context,
                continuity_lifetime_revisions=self._continuity_lifetime_revisions,
                cognitive_budget=self._cognitive_budget,
                pass_request=self._pass_request,
                pass1_request=self._pass1_request,
                pass2_request=self._pass2_request,
                snapshot_fingerprint=_tree_fingerprint(snapshot_root),
            )
        except Exception:
            temporary_directory.cleanup()
            raise
        self._snapshots.append(snapshot)
        return snapshot

    def _require_open(self) -> None:
        if self._closed:
            raise MemConflictAdapterError("read-only query adapter is closed")


class _ObservingProvider:
    """Transparent provider wrapper for answer-time input and #1871 failures."""

    def __init__(self, delegate: object, *, turn_index: int) -> None:
        self._delegate = delegate
        self._turn_index = turn_index
        self.input: CognitiveInput | None = None
        self.failures: list[ReadOnlyQueryFailureDiagnostic] = []

    async def generate(self, cognitive_input: CognitiveInput, **kwargs: object):
        self.input = cognitive_input
        try:
            return await self._delegate.generate(cognitive_input, **kwargs)
        except BaseException as exc:
            self._record("single_pass", exc)
            raise

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        **kwargs: object,
    ):
        self.input = cognitive_input
        try:
            return await self._delegate.generate_conversation(
                cognitive_input,
                **kwargs,
            )
        except BaseException as exc:
            self._record("pass1", exc)
            raise

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        **kwargs: object,
    ):
        try:
            return await self._delegate.generate_extraction(
                extraction_input,
                **kwargs,
            )
        except BaseException as exc:
            self._record("pass2", exc)
            raise

    def _record(self, phase: FailurePhase, exc: BaseException) -> None:
        message = None
        if isinstance(exc, ProviderProtocolError):
            normalized = " ".join(str(exc).split())
            if normalized:
                message = normalized[:512]
        self.failures.append(
            ReadOnlyQueryFailureDiagnostic(
                turn_index=self._turn_index,
                phase=phase,
                exception_type=type(exc).__name__,
                exception_message=message,
            )
        )


def _require_input(observer: _ObservingProvider) -> CognitiveInput:
    if observer.input is None:
        raise MemConflictAdapterError(
            "ordinary RelayLM query completed without a captured CognitiveInput"
        )
    return observer.input


def _dialogue_event_id(
    *,
    session_id: str,
    session_index: int,
    message_index: int,
    role: object,
    content: str,
) -> str:
    encoded = json.dumps(
        {
            "session_id": session_id,
            "session_index": session_index,
            "message_index": message_index,
            "role": role,
            "content": content,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"relaylm-session-{hashlib.sha256(encoded).hexdigest()}"


def _state_record_mapping(record: StateRecord) -> dict[str, object]:
    mapping: dict[str, object] = {
        "state_id": record.state_id,
        "state_class": record.state_class,
        "key": record.key,
        "value": _json_copy(record.value),
        "status": record.status,
        "sources": list(record.sources),
    }
    if record.valid_from is not None:
        mapping["valid_from"] = record.valid_from
    if record.valid_to is not None:
        mapping["valid_to"] = record.valid_to
    return mapping


def _completion_mapping(
    completion: CognitionCompletionMetadata | None,
) -> dict[str, object] | None:
    if completion is None:
        return None
    return {
        "finish_reason": completion.finish_reason,
        "prompt_tokens": completion.prompt_tokens,
        "completion_tokens": completion.completion_tokens,
        "total_tokens": completion.total_tokens,
        "reasoning_tokens": completion.reasoning_tokens,
    }


def _json_copy(value: object) -> object:
    return json.loads(
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    )


def _tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(b"symlink\0" + relative + b"\0")
            digest.update(os.readlink(path).encode("utf-8"))
            digest.update(b"\n")
        elif path.is_file():
            digest.update(b"file\0" + relative + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"
