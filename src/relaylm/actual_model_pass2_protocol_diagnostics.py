from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from relaylm.actual_model_evaluation import ActualModelEvidence
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)

PASS2_PROTOCOL_DIAGNOSTIC_FORMAT_VERSION = 1


class ActualModelPass2ProtocolDiagnosticError(ValueError):
    """Pass 2 protocol diagnostic evidence is malformed or conflicting."""


@dataclass(frozen=True, slots=True)
class Pass2ProtocolHTTPObservation:
    http_status: int
    response_text: str
    message_content: str | None
    finish_reason: str | None
    usage: dict[str, object] | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "http_status": self.http_status,
            "response_text": self.response_text,
            "message_content": self.message_content,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
        }


@dataclass(frozen=True, slots=True)
class Pass2ProtocolFailureObservation:
    turn_index: int
    http_status: int | None
    response_text: str | None
    message_content: str | None
    finish_reason: str | None
    usage: dict[str, object] | None
    exception_chain: tuple[dict[str, str], ...]

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("turn_index must be positive")
        if not self.exception_chain:
            raise ValueError("exception_chain must not be empty")

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "http_status": self.http_status,
            "response_text": self.response_text,
            "message_content": self.message_content,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "exception_chain": [dict(item) for item in self.exception_chain],
        }


@dataclass(slots=True)
class Pass2ProtocolDiagnosticRecorder:
    """Explicit #1386-only observer for one two-pass provider execution."""

    failures: list[Pass2ProtocolFailureObservation] = field(default_factory=list)
    _turn_index: int = 0
    _active_turn_index: int | None = None
    _current_http: Pass2ProtocolHTTPObservation | None = None

    def begin_extraction(self) -> int:
        if self._active_turn_index is not None:
            raise RuntimeError("Pass 2 protocol diagnostic extraction is already active")
        self._turn_index += 1
        self._active_turn_index = self._turn_index
        self._current_http = None
        return self._turn_index

    def complete_extraction(self) -> None:
        self._active_turn_index = None
        self._current_http = None

    def fail_extraction(self, exc: BaseException) -> None:
        turn_index = self._active_turn_index
        if turn_index is None:
            raise RuntimeError("Pass 2 protocol diagnostic extraction is not active")
        http = self._current_http
        self.failures.append(
            Pass2ProtocolFailureObservation(
                turn_index=turn_index,
                http_status=http.http_status if http is not None else None,
                response_text=http.response_text if http is not None else None,
                message_content=http.message_content if http is not None else None,
                finish_reason=http.finish_reason if http is not None else None,
                usage=dict(http.usage) if http is not None and http.usage is not None else None,
                exception_chain=_exception_chain(exc),
            )
        )
        self._active_turn_index = None
        self._current_http = None

    async def observe_response(self, response: httpx.Response) -> None:
        if self._active_turn_index is None:
            return
        if not _is_pass2_extraction_request(response.request):
            return
        await response.aread()
        try:
            response_text = response.content.decode("utf-8")
        except UnicodeDecodeError:
            response_text = response.content.decode("utf-8", errors="replace")
        self._current_http = _http_observation(
            status_code=response.status_code,
            response_text=response_text,
        )


class _Pass2ProtocolDiagnosticProvider:
    def __init__(self, delegate: object, recorder: Pass2ProtocolDiagnosticRecorder) -> None:
        self._delegate = delegate
        self._recorder = recorder

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        generate = getattr(self._delegate, "generate", None)
        if not callable(generate):
            raise TypeError("provider does not support cognitive generation")
        if pass_request is None:
            return await generate(cognitive_input)
        return await generate(cognitive_input, pass_request=pass_request)

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        generate = getattr(self._delegate, "generate_conversation", None)
        if not callable(generate):
            raise TypeError("provider does not support two-pass conversation generation")
        if pass_request is None:
            return await generate(cognitive_input)
        return await generate(cognitive_input, pass_request=pass_request)

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        generate = getattr(self._delegate, "generate_extraction", None)
        if not callable(generate):
            raise TypeError("provider does not support structured extraction")
        self._recorder.begin_extraction()
        try:
            if pass_request is None:
                output = await generate(extraction_input)
            else:
                output = await generate(extraction_input, pass_request=pass_request)
        except BaseException as exc:
            self._recorder.fail_extraction(exc)
            raise
        self._recorder.complete_extraction()
        return output


def instrument_pass2_protocol_diagnostics(
    provider: object,
    *,
    recorder: Pass2ProtocolDiagnosticRecorder,
) -> object:
    """Observe one existing OpenAI-compatible provider without changing its requests."""

    if not isinstance(recorder, Pass2ProtocolDiagnosticRecorder):
        raise TypeError("recorder must be Pass2ProtocolDiagnosticRecorder")
    client = getattr(provider, "_client", None)
    if not isinstance(client, httpx.AsyncClient):
        raise TypeError(
            "Pass 2 protocol diagnostics require an OpenAI-compatible httpx AsyncClient"
        )
    hooks = client.event_hooks.setdefault("response", [])
    if recorder.observe_response not in hooks:
        hooks.append(recorder.observe_response)
    return _Pass2ProtocolDiagnosticProvider(provider, recorder)


@dataclass(frozen=True, slots=True)
class ActualModelPass2ProtocolDiagnosticArtifact:
    relaylm_commit: str
    run_id: str
    scenario_id: str
    condition_id: str
    replicate_id: str
    failures: tuple[Pass2ProtocolFailureObservation, ...]
    execution_id: str | None = None
    format_version: int = PASS2_PROTOCOL_DIAGNOSTIC_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != PASS2_PROTOCOL_DIAGNOSTIC_FORMAT_VERSION:
            raise ValueError("unsupported Pass 2 protocol diagnostic format_version")
        for name in (
            "relaylm_commit",
            "run_id",
            "scenario_id",
            "condition_id",
            "replicate_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not self.failures:
            raise ValueError("Pass 2 protocol diagnostic requires at least one failure")
        indexes = tuple(item.turn_index for item in self.failures)
        if len(set(indexes)) != len(indexes):
            raise ValueError("Pass 2 protocol diagnostic turn indexes must be unique")

    @property
    def diagnostic_id(self) -> str:
        payload = json.dumps(
            self._identity_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"amp2d-{hashlib.sha256(payload).hexdigest()}"

    def _identity_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "relaylm_commit": self.relaylm_commit,
            "run_id": self.run_id,
            "execution_id": self.execution_id,
            "scenario_id": self.scenario_id,
            "condition_id": self.condition_id,
            "replicate_id": self.replicate_id,
            "failures": [item.to_mapping() for item in self.failures],
        }

    def to_mapping(self) -> dict[str, object]:
        return {"diagnostic_id": self.diagnostic_id, **self._identity_mapping()}

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ) + "\n"


def bind_pass2_protocol_diagnostic_artifact(
    *,
    evidence: ActualModelEvidence,
    recorder: Pass2ProtocolDiagnosticRecorder,
    execution_id: str | None = None,
) -> ActualModelPass2ProtocolDiagnosticArtifact:
    if not isinstance(evidence, ActualModelEvidence):
        raise TypeError("evidence must be ActualModelEvidence")
    if not isinstance(recorder, Pass2ProtocolDiagnosticRecorder):
        raise TypeError("recorder must be Pass2ProtocolDiagnosticRecorder")
    if not recorder.failures:
        raise ActualModelPass2ProtocolDiagnosticError(
            "cannot bind Pass 2 protocol diagnostic without a recorded failure"
        )

    turn_by_index = {turn.turn_index: turn for turn in evidence.turns}
    for failure in recorder.failures:
        turn = turn_by_index.get(failure.turn_index)
        if turn is None or turn.cognition_execution is None:
            raise ActualModelPass2ProtocolDiagnosticError(
                "diagnostic failure does not match a two-pass evidence turn"
            )
        if (
            turn.cognition_execution.pass2_status != "failed"
            or turn.cognition_execution.pass2_failure_reason != "pass2_failed"
        ):
            raise ActualModelPass2ProtocolDiagnosticError(
                "diagnostic failure must correspond to stable pass2_failed evidence"
            )

    return ActualModelPass2ProtocolDiagnosticArtifact(
        relaylm_commit=evidence.manifest.relaylm_commit,
        run_id=evidence.run_id,
        execution_id=execution_id,
        scenario_id=evidence.scenario.scenario_id,
        condition_id=evidence.manifest.condition_id,
        replicate_id=evidence.manifest.replicate_id,
        failures=tuple(recorder.failures),
    )


def write_pass2_protocol_diagnostic_artifact(
    *,
    artifact: ActualModelPass2ProtocolDiagnosticArtifact,
    artifact_root: str | Path,
) -> Path:
    if not isinstance(artifact, ActualModelPass2ProtocolDiagnosticArtifact):
        raise TypeError("artifact must be ActualModelPass2ProtocolDiagnosticArtifact")
    directory = Path(artifact_root) / "pass2_protocol_diagnostics"
    path = directory / f"{artifact.diagnostic_id}.json"
    payload = artifact.to_json()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ActualModelPass2ProtocolDiagnosticError(
            f"cannot create Pass 2 protocol diagnostic directory: {exc}"
        ) from exc
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = directory / f".{artifact.diagnostic_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelPass2ProtocolDiagnosticError(
            f"cannot write Pass 2 protocol diagnostic: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelPass2ProtocolDiagnosticError(
            f"cannot read existing Pass 2 protocol diagnostic: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelPass2ProtocolDiagnosticError(
        "conflicting Pass 2 protocol diagnostic already exists"
    )


def _is_pass2_extraction_request(request: httpx.Request) -> bool:
    try:
        body = json.loads(request.content)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return False
    if not isinstance(body, dict):
        return False
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return False
    user_message = messages[1]
    if not isinstance(user_message, dict):
        return False
    content = user_message.get("content")
    return isinstance(content, str) and "<PASS>\nEXTRACTION" in content


def _http_observation(*, status_code: int, response_text: str) -> Pass2ProtocolHTTPObservation:
    message_content: str | None = None
    finish_reason: str | None = None
    usage: dict[str, object] | None = None
    try:
        envelope = json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        envelope = None
    if isinstance(envelope, dict):
        choices = envelope.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
            raw_finish = choice.get("finish_reason")
            if isinstance(raw_finish, str):
                finish_reason = raw_finish
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                message_content = message["content"]
        raw_usage = envelope.get("usage")
        if isinstance(raw_usage, dict):
            usage = {str(key): _json_safe(value) for key, value in raw_usage.items()}
    return Pass2ProtocolHTTPObservation(
        http_status=status_code,
        response_text=response_text,
        message_content=message_content,
        finish_reason=finish_reason,
        usage=usage,
    )


def _exception_chain(exc: BaseException) -> tuple[dict[str, str], ...]:
    chain: list[dict[str, str]] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append({"type": type(current).__name__, "message": str(current)})
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None
    return tuple(chain)


def _json_safe(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(nested) for nested in value]
    return str(value)
