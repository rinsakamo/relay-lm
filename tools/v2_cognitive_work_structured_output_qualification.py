from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Protocol

import httpx

from tools import v2_cognitive_work_r2_host as historical_host
from tools.v2_cognitive_work_r0 import ExecutionBinding


CLAIM_STATUS = "STRUCTURED_OUTPUT_PROTOCOL_QUALIFICATION"
QUALIFICATION_VERSION = "relaylm2-cognitive-work-sopq-v1"
ANSWER_SCHEMA_NAME = "relaylm2_cognitive_work_answer_v1"
OPERATION_SCHEMA_NAME = "relaylm2_cognitive_work_operation_v1"
QUALIFICATION_CALL_COUNT = 12
CONTEXT_LIMIT = 8192

MANIFEST_NAME = "qualification-manifest.json"
STATE_NAME = "qualification-state.json"
REQUEST_EVIDENCE_NAME = "request-evidence.jsonl"
RESULT_NAME = "qualification-result.json"


class StructuredOutputQualificationError(ValueError):
    """The bounded structured-output qualification cannot satisfy its contract."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: object) -> str:
    payload = (
        value.encode("utf-8")
        if isinstance(value, str)
        else _canonical_json(value).encode("utf-8")
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


ANSWER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

OPERATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["ZERO", "THINK", "RETRIEVE", "OBSERVE"],
        }
    },
    "required": ["operation"],
    "additionalProperties": False,
}

ANSWER_SCHEMA_DIGEST = _sha256(ANSWER_SCHEMA)
OPERATION_SCHEMA_DIGEST = _sha256(OPERATION_SCHEMA)


def response_format_for(schema_kind: str) -> dict[str, object]:
    if schema_kind == "answer":
        name = ANSWER_SCHEMA_NAME
        schema = ANSWER_SCHEMA
    elif schema_kind == "operation":
        name = OPERATION_SCHEMA_NAME
        schema = OPERATION_SCHEMA
    else:
        raise StructuredOutputQualificationError("unknown structured-output schema kind")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


ANSWER_RESPONSE_FORMAT_DIGEST = _sha256(response_format_for("answer"))
OPERATION_RESPONSE_FORMAT_DIGEST = _sha256(response_format_for("operation"))


@dataclass(frozen=True, slots=True)
class QualificationCall:
    call_id: str
    fixture_class: str
    schema_kind: str
    messages: tuple[dict[str, str], ...]

    def __post_init__(self) -> None:
        if not self.call_id.strip() or not self.fixture_class.strip():
            raise StructuredOutputQualificationError(
                "qualification call id/class must be non-empty"
            )
        if self.schema_kind not in {"answer", "operation"}:
            raise StructuredOutputQualificationError(
                "qualification call schema kind is invalid"
            )
        if not self.messages:
            raise StructuredOutputQualificationError(
                "qualification call messages must not be empty"
            )


def _answer_messages(instruction: str, payload: Mapping[str, object]) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                instruction
                + " Return the requested answer. The provider enforces the response schema."
            ),
        },
        {"role": "user", "content": _canonical_json(payload)},
    )


def _operation_messages(instruction: str) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "Choose the single operation requested by the calibration instruction. "
                "The provider enforces the response schema."
            ),
        },
        {"role": "user", "content": instruction},
    )


def qualification_plan() -> tuple[QualificationCall, ...]:
    answer_calls = (
        QualificationCall(
            "answer-direct-1",
            "A_DIRECT",
            "answer",
            _answer_messages("Compute the trivial expression.", {"expression": "2 + 3"}),
        ),
        QualificationCall(
            "answer-direct-2",
            "A_DIRECT",
            "answer",
            _answer_messages("Compute the trivial expression.", {"expression": "8 - 3"}),
        ),
        QualificationCall(
            "answer-reconsider-1",
            "A_RECONSIDER",
            "answer",
            _answer_messages(
                "Reconsider the previous candidate using only the public information.",
                {"question": "What is 4 + 5?", "previous_answer": "8"},
            ),
        ),
        QualificationCall(
            "answer-reconsider-2",
            "A_RECONSIDER",
            "answer",
            _answer_messages(
                "Reconsider the previous candidate using only the public information.",
                {"question": "What is 6 + 7?", "previous_answer": "12"},
            ),
        ),
        QualificationCall(
            "answer-context-1",
            "A_ADDED_CONTEXT",
            "answer",
            _answer_messages(
                "Answer using the newly supplied benign fact.",
                {"question": "What is the codename?", "new_fact": "The codename is BLUE."},
            ),
        ),
        QualificationCall(
            "answer-context-2",
            "A_ADDED_CONTEXT",
            "answer",
            _answer_messages(
                "Answer using the newly supplied benign fact.",
                {"question": "What is the marker?", "new_fact": "The marker is NOVA."},
            ),
        ),
        QualificationCall(
            "answer-symbolic-1",
            "A_SYMBOLIC",
            "answer",
            _answer_messages("Return the requested symbol.", {"symbol": "K7"}),
        ),
        QualificationCall(
            "answer-symbolic-2",
            "A_SYMBOLIC",
            "answer",
            _answer_messages("Return the requested symbol.", {"symbol": "Q2"}),
        ),
    )
    operation_calls = tuple(
        QualificationCall(
            f"operation-{operation.lower()}",
            "O_ROUTING",
            "operation",
            _operation_messages(
                f"For this transport calibration, select operation {operation}."
            ),
        )
        for operation in ("ZERO", "THINK", "RETRIEVE", "OBSERVE")
    )
    plan = answer_calls + operation_calls
    if len(plan) != QUALIFICATION_CALL_COUNT:
        raise StructuredOutputQualificationError(
            "structured-output qualification plan must contain exactly 12 calls"
        )
    if len({item.call_id for item in plan}) != len(plan):
        raise StructuredOutputQualificationError(
            "structured-output qualification call ids must be unique"
        )
    return plan


QUALIFICATION_PLAN_DIGEST = _sha256(
    [
        {
            "call_id": item.call_id,
            "fixture_class": item.fixture_class,
            "schema_kind": item.schema_kind,
            "messages": item.messages,
            "response_format": response_format_for(item.schema_kind),
        }
        for item in qualification_plan()
    ]
)


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StructuredOutputQualificationError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StructuredOutputQualificationError(
        f"non-standard JSON numeric constant: {value}"
    )


def _strict_json_object(text: str) -> dict[str, object]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except StructuredOutputQualificationError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise StructuredOutputQualificationError(
            "structured output is not strict whole-response JSON"
        ) from exc
    if not isinstance(value, dict):
        raise StructuredOutputQualificationError(
            "structured output must be one JSON object"
        )
    return value


def parse_answer(text: str) -> str:
    payload = _strict_json_object(text)
    if set(payload) != {"answer"}:
        raise StructuredOutputQualificationError(
            "answer output must contain exactly answer"
        )
    answer = payload["answer"]
    if not isinstance(answer, str) or not answer.strip():
        raise StructuredOutputQualificationError(
            "answer output must contain a non-empty string"
        )
    return answer.strip()


def parse_operation(text: str) -> str:
    payload = _strict_json_object(text)
    if set(payload) != {"operation"}:
        raise StructuredOutputQualificationError(
            "operation output must contain exactly operation"
        )
    operation = payload["operation"]
    if operation not in {"ZERO", "THINK", "RETRIEVE", "OBSERVE"}:
        raise StructuredOutputQualificationError(
            "operation output must contain one declared operation"
        )
    return str(operation)


@dataclass(frozen=True, slots=True)
class StructuredOutputCompletion:
    content: str
    input_tokens: int
    output_tokens: int
    response_id: str | None
    finish_reason: str | None


class StructuredOutputClient(Protocol):
    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: Mapping[str, object],
    ) -> StructuredOutputCompletion: ...


class OpenAICompatibleStructuredOutputClient:
    """Minimal structured Chat Completions client for #2302 only."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not base_url.strip() or not model.strip():
            raise StructuredOutputQualificationError(
                "structured-output provider base_url/model must be non-empty"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: Mapping[str, object],
    ) -> StructuredOutputCompletion:
        if not messages:
            raise StructuredOutputQualificationError("messages must not be empty")
        body: dict[str, object] = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "response_format": dict(response_format),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise StructuredOutputQualificationError(
                f"structured-output provider request failed: {exc}"
            ) from exc
        if not response.is_success:
            raise StructuredOutputQualificationError(
                "structured-output provider request failed with status "
                f"{response.status_code}"
            )
        try:
            envelope = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StructuredOutputQualificationError(
                "structured-output provider envelope is invalid JSON"
            ) from exc
        if not isinstance(envelope, dict):
            raise StructuredOutputQualificationError(
                "structured-output provider envelope must be an object"
            )
        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise StructuredOutputQualificationError(
                "structured-output provider must return exactly one choice"
            )
        choice = choices[0]
        if not isinstance(choice, dict):
            raise StructuredOutputQualificationError(
                "structured-output provider choice must be an object"
            )
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise StructuredOutputQualificationError(
                "structured-output finish_reason must be string or null"
            )
        if finish_reason != "stop":
            raise StructuredOutputQualificationError(
                "structured-output provider did not finish with stop"
            )
        message = choice.get("message")
        if not isinstance(message, dict):
            raise StructuredOutputQualificationError(
                "structured-output provider message must be an object"
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructuredOutputQualificationError(
                "structured-output provider content must be non-empty"
            )
        usage = envelope.get("usage")
        if not isinstance(usage, dict):
            raise StructuredOutputQualificationError(
                "structured-output provider usage must be an object"
            )
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        for label, value in (
            ("prompt_tokens", input_tokens),
            ("completion_tokens", output_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StructuredOutputQualificationError(
                    f"structured-output {label} must be a non-negative integer"
                )
        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructuredOutputQualificationError(
                "structured-output response id must be string or null"
            )
        return StructuredOutputCompletion(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_id=response_id,
            finish_reason=finish_reason,
        )


@dataclass(frozen=True, slots=True)
class StructuredOutputExecutionAuthorization:
    authorization_id: str
    execution_repository_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip() or not self.execution_repository_commit.strip():
            raise StructuredOutputQualificationError(
                "structured-output authorization identity must be non-empty"
            )


@dataclass(frozen=True, slots=True)
class StructuredOutputQualificationIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise StructuredOutputQualificationError(
                "structured-output repository commit/tree must be non-empty"
            )
        if self.execution.context_limit != CONTEXT_LIMIT:
            raise StructuredOutputQualificationError(
                f"structured-output context limit must be {CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise StructuredOutputQualificationError(
                "structured-output qualification retries must be disabled"
            )

    @property
    def fingerprint(self) -> str:
        return _sha256(
            {
                "qualification_version": QUALIFICATION_VERSION,
                "repository_commit": self.repository_commit,
                "repository_tree": self.repository_tree,
                "execution": asdict(self.execution),
                "answer_schema_digest": ANSWER_SCHEMA_DIGEST,
                "operation_schema_digest": OPERATION_SCHEMA_DIGEST,
                "answer_response_format_digest": ANSWER_RESPONSE_FORMAT_DIGEST,
                "operation_response_format_digest": OPERATION_RESPONSE_FORMAT_DIGEST,
                "plan_digest": QUALIFICATION_PLAN_DIGEST,
                "automatic_retry": self.automatic_retry,
                "semantic_retry": self.semantic_retry,
            }
        )


@dataclass(frozen=True, slots=True)
class StructuredOutputQualificationResult:
    run_id: str
    identity_fingerprint: str
    status: str
    verdict: str
    provider_attempts: int
    provider_completions: int


def probe_repository(repository_root: str | Path) -> historical_host.RepositoryState:
    return historical_host.probe_repository(repository_root)


def _validate_repository(
    identity: StructuredOutputQualificationIdentity,
    observed: historical_host.RepositoryState,
) -> None:
    if not observed.clean:
        raise StructuredOutputQualificationError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise StructuredOutputQualificationError(
            "repository commit does not match qualification identity"
        )
    if observed.tree != identity.repository_tree:
        raise StructuredOutputQualificationError(
            "repository tree does not match qualification identity"
        )


def _validate_authorization(
    identity: StructuredOutputQualificationIdentity,
    authorization: StructuredOutputExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise StructuredOutputQualificationError(
            "structured-output physical qualification is not authorized"
        )
    if authorization.execution_repository_commit != identity.repository_commit:
        raise StructuredOutputQualificationError(
            "structured-output authorization does not bind execution commit"
        )


def _append_evidence(root: Path, record: Mapping[str, object]) -> None:
    historical_host._append_jsonl(root / REQUEST_EVIDENCE_NAME, record)


def run_structured_output_qualification(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: StructuredOutputQualificationIdentity,
    authorization: StructuredOutputExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: StructuredOutputClient,
    run_id: str,
) -> StructuredOutputQualificationResult:
    if not run_id.strip():
        raise StructuredOutputQualificationError("qualification run_id must be non-empty")
    _validate_authorization(identity, authorization)
    _validate_repository(identity, probe_repository(repository_root))
    plan = qualification_plan()
    root = historical_host._validate_artifact_root(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )
    manifest = {
        "run_id": run_id,
        "claim_status": CLAIM_STATUS,
        "qualification_version": QUALIFICATION_VERSION,
        "execution_authorization": asdict(authorization),
        "execution_repository": {
            "commit": identity.repository_commit,
            "tree": identity.repository_tree,
            "clean_required": True,
        },
        "execution_binding": asdict(identity.execution),
        "identity_fingerprint": identity.fingerprint,
        "answer_schema": ANSWER_SCHEMA,
        "answer_schema_digest": ANSWER_SCHEMA_DIGEST,
        "operation_schema": OPERATION_SCHEMA,
        "operation_schema_digest": OPERATION_SCHEMA_DIGEST,
        "answer_response_format": response_format_for("answer"),
        "answer_response_format_digest": ANSWER_RESPONSE_FORMAT_DIGEST,
        "operation_response_format": response_format_for("operation"),
        "operation_response_format_digest": OPERATION_RESPONSE_FORMAT_DIGEST,
        "plan_digest": QUALIFICATION_PLAN_DIGEST,
        "plan": [
            {
                "call_id": item.call_id,
                "fixture_class": item.fixture_class,
                "schema_kind": item.schema_kind,
                "messages": item.messages,
            }
            for item in plan
        ],
        "retry_policy": {
            "automatic_retry": False,
            "semantic_retry": False,
            "provider_retry": False,
            "fallback_provider": False,
            "fallback_model": False,
            "partial_replay": False,
        },
        "r2_campaign_tasks": 0,
        "architecture_consequence": "NONE",
    }
    historical_host._write_json_exclusive(root / MANIFEST_NAME, manifest)
    historical_host._write_json_exclusive(
        root / STATE_NAME,
        {
            "run_id": run_id,
            "status": "RUNNING",
            "provider_attempts": 0,
            "provider_completions": 0,
            "plan_cursor": 0,
            "plan_size": len(plan),
        },
    )

    try:
        preflight = live_binding_probe()
    except Exception as exc:
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "INCOMPLETE",
                "provider_attempts": 0,
                "provider_completions": 0,
                "plan_cursor": 0,
                "plan_size": len(plan),
                "failure": {"kind": "preflight_probe_failure", "detail": str(exc)},
            },
        )
        raise StructuredOutputQualificationError(
            "structured-output preflight binding probe failed"
        ) from exc
    if preflight != identity.execution:
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "INCOMPLETE",
                "provider_attempts": 0,
                "provider_completions": 0,
                "plan_cursor": 0,
                "plan_size": len(plan),
                "failure": {
                    "kind": "preflight_binding_drift",
                    "detail": "preflight binding differs from frozen identity",
                },
            },
        )
        raise StructuredOutputQualificationError(
            "structured-output preflight binding drift"
        )

    attempts = 0
    completions = 0
    cursor = 0
    for item in plan:
        try:
            observed_binding = live_binding_probe()
        except Exception as exc:
            historical_host._write_json_atomic(
                root / STATE_NAME,
                {
                    "run_id": run_id,
                    "status": "INCOMPLETE",
                    "provider_attempts": attempts,
                    "provider_completions": completions,
                    "plan_cursor": cursor,
                    "plan_size": len(plan),
                    "failure": {"kind": "binding_probe_failure", "detail": str(exc)},
                },
            )
            raise StructuredOutputQualificationError(
                "structured-output live binding probe failed"
            ) from exc
        if observed_binding != identity.execution:
            historical_host._write_json_atomic(
                root / STATE_NAME,
                {
                    "run_id": run_id,
                    "status": "INCOMPLETE",
                    "provider_attempts": attempts,
                    "provider_completions": completions,
                    "plan_cursor": cursor,
                    "plan_size": len(plan),
                    "failure": {
                        "kind": "binding_drift",
                        "detail": f"binding drift before {item.call_id}",
                    },
                },
            )
            raise StructuredOutputQualificationError(
                "structured-output physical binding drift"
            )

        response_format = response_format_for(item.schema_kind)
        attempts += 1
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "RUNNING",
                "provider_attempts": attempts,
                "provider_completions": completions,
                "plan_cursor": cursor,
                "plan_size": len(plan),
                "current_call_id": item.call_id,
            },
        )
        try:
            completion = client.complete(
                item.messages,
                response_format=response_format,
            )
        except Exception as exc:
            _append_evidence(
                root,
                {
                    "run_id": run_id,
                    "identity_fingerprint": identity.fingerprint,
                    "order": attempts,
                    "kind": "provider_failure",
                    "call_id": item.call_id,
                    "fixture_class": item.fixture_class,
                    "schema_kind": item.schema_kind,
                    "messages": item.messages,
                    "response_format": response_format,
                    "provider_attempts": attempts,
                    "provider_completions": completions,
                    "detail": str(exc),
                },
            )
            historical_host._write_json_atomic(
                root / STATE_NAME,
                {
                    "run_id": run_id,
                    "status": "INCOMPLETE",
                    "provider_attempts": attempts,
                    "provider_completions": completions,
                    "plan_cursor": cursor,
                    "plan_size": len(plan),
                    "failure": {"kind": "provider_failure", "detail": str(exc)},
                },
            )
            raise StructuredOutputQualificationError(
                "structured-output provider call failed"
            ) from exc

        completions += 1
        _append_evidence(
            root,
            {
                "run_id": run_id,
                "identity_fingerprint": identity.fingerprint,
                "order": attempts,
                "kind": "model_exchange",
                "call_id": item.call_id,
                "fixture_class": item.fixture_class,
                "schema_kind": item.schema_kind,
                "schema_digest": (
                    ANSWER_SCHEMA_DIGEST
                    if item.schema_kind == "answer"
                    else OPERATION_SCHEMA_DIGEST
                ),
                "messages": item.messages,
                "response_format": response_format,
                "response": {
                    "content": completion.content,
                    "content_sha256": _sha256(completion.content),
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "response_id": completion.response_id,
                    "finish_reason": completion.finish_reason,
                },
                "provider_attempts": attempts,
                "provider_completions": completions,
            },
        )

        try:
            if completion.finish_reason != "stop":
                raise StructuredOutputQualificationError(
                    "structured-output completion did not finish with stop"
                )
            if item.schema_kind == "answer":
                parse_answer(completion.content)
            else:
                parse_operation(completion.content)
        except StructuredOutputQualificationError as exc:
            historical_host._write_json_atomic(
                root / STATE_NAME,
                {
                    "run_id": run_id,
                    "status": "INCOMPLETE",
                    "provider_attempts": attempts,
                    "provider_completions": completions,
                    "plan_cursor": cursor,
                    "plan_size": len(plan),
                    "failure": {
                        "kind": "protocol_invalid",
                        "call_id": item.call_id,
                        "detail": str(exc),
                    },
                },
            )
            raise

        cursor += 1
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "RUNNING",
                "provider_attempts": attempts,
                "provider_completions": completions,
                "plan_cursor": cursor,
                "plan_size": len(plan),
            },
        )

    if attempts != QUALIFICATION_CALL_COUNT or completions != QUALIFICATION_CALL_COUNT:
        raise StructuredOutputQualificationError(
            "structured-output qualification did not complete all 12 calls"
        )
    result = {
        "run_id": run_id,
        "claim_status": CLAIM_STATUS,
        "verdict": "STRUCTURED_OUTPUT_PROTOCOL_QUALIFIED",
        "identity_fingerprint": identity.fingerprint,
        "provider_attempts": attempts,
        "provider_completions": completions,
        "plan_cursor": cursor,
        "plan_size": len(plan),
        "strict_whole_response_json": "12/12",
        "schema_validation": "12/12",
        "strict_parser_validation": "12/12",
        "wrapper_or_prose_defects": 0,
        "binding_drift": 0,
        "retries_fallbacks_repairs": 0,
        "r2_campaign_tasks": 0,
        "scientific_allocator_verdict": "NONE",
        "architecture_consequence": "NONE",
    }
    historical_host._write_json_exclusive(root / RESULT_NAME, result)
    historical_host._write_json_atomic(
        root / STATE_NAME,
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "provider_attempts": attempts,
            "provider_completions": completions,
            "plan_cursor": cursor,
            "plan_size": len(plan),
        },
    )
    return StructuredOutputQualificationResult(
        run_id=run_id,
        identity_fingerprint=identity.fingerprint,
        status="COMPLETED",
        verdict="STRUCTURED_OUTPUT_PROTOCOL_QUALIFIED",
        provider_attempts=attempts,
        provider_completions=completions,
    )
