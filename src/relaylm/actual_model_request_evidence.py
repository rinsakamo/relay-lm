from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_request_observation import model_facing_request_observation


ACTUAL_MODEL_REQUEST_EVIDENCE_FORMAT_VERSION = 1
RequestPassIdentity = Literal["single_pass", "pass1", "pass2"]
_REQUEST_PASSES = frozenset({"single_pass", "pass1", "pass2"})
_FAILURE_MESSAGE_LIMIT = 512
_FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "access_token",
        "access-token",
        "api_token",
        "api-token",
        "api-key",
        "api_key",
        "apikey",
        "auth",
        "auth_token",
        "authentication",
        "authorization",
        "authorization_token",
        "authorization-token",
        "bearer",
        "bearer_token",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "env",
        "environment",
        "headers",
        "password",
        "refresh_token",
        "refresh-token",
        "secret",
        "secrets",
        "session",
        "session_id",
        "token",
        "tokens",
    }
)


class ActualModelRequestEvidenceError(RuntimeError):
    """A request-evidence artifact violated its immutable evidence contract."""


def bounded_provider_failure_diagnostic(
    exc: BaseException,
) -> tuple[str, str | None]:
    """Return the existing bounded provider-failure diagnostic privacy shape."""

    exception_type = type(exc).__name__
    if not isinstance(exc, ProviderProtocolError):
        return exception_type, None
    message = " ".join(str(exc).split())
    if not message:
        return exception_type, None
    return exception_type, message[:_FAILURE_MESSAGE_LIMIT]


@dataclass(frozen=True, slots=True)
class ActualModelRequestEvidence:
    """One exact model-facing request captured immediately before transport."""

    evidence_id: str
    execution_id: str
    run_id: str
    scenario_id: str
    scenario_revision: str
    turn_index: int
    pass_identity: RequestPassIdentity
    request_ordinal: int
    provider_identity: str
    adapter_identity: str
    request_body: dict[str, Any]
    request_body_sha256: str
    attempted: bool = True
    failure_exception_type: str | None = None
    failure_exception_message: str | None = None
    format_version: int = ACTUAL_MODEL_REQUEST_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_REQUEST_EVIDENCE_FORMAT_VERSION:
            raise ValueError(
                "unsupported actual-model request evidence format_version: "
                f"{self.format_version}"
            )
        for name in (
            "evidence_id",
            "execution_id",
            "run_id",
            "scenario_id",
            "scenario_revision",
            "provider_identity",
            "adapter_identity",
            "request_body_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.pass_identity not in _REQUEST_PASSES:
            raise ValueError(f"unsupported request pass identity: {self.pass_identity}")
        _require_positive_int(self.turn_index, "turn_index")
        _require_positive_int(self.request_ordinal, "request_ordinal")
        if self.attempted is not True:
            raise ValueError("request evidence must represent an attempted request")
        if self.failure_exception_type is not None:
            if not isinstance(self.failure_exception_type, str):
                raise TypeError("failure_exception_type must be a string or None")
            if not self.failure_exception_type.strip():
                raise ValueError("failure_exception_type must not be empty")
        if self.failure_exception_message is not None:
            if self.failure_exception_type is None:
                raise ValueError(
                    "failure_exception_message requires failure_exception_type"
                )
            if not isinstance(self.failure_exception_message, str):
                raise TypeError("failure_exception_message must be a string or None")
            if not self.failure_exception_message.strip():
                raise ValueError("failure_exception_message must not be empty")
            if len(self.failure_exception_message) > _FAILURE_MESSAGE_LIMIT:
                raise ValueError(
                    "failure_exception_message exceeds the bounded diagnostic limit"
                )
        _validate_request_body(self.request_body)
        self.validate_identity()

    @classmethod
    def create(
        cls,
        *,
        execution_id: str,
        run_id: str,
        scenario_id: str,
        scenario_revision: str,
        turn_index: int,
        pass_identity: RequestPassIdentity,
        request_ordinal: int,
        provider_identity: str,
        adapter_identity: str,
        request_body: Mapping[str, Any],
    ) -> "ActualModelRequestEvidence":
        normalized_body = _normalize_request_body(request_body)
        body_sha256 = canonical_request_body_sha256(normalized_body)
        evidence_id = _stable_request_evidence_id(
            execution_id=execution_id,
            run_id=run_id,
            scenario_id=scenario_id,
            scenario_revision=scenario_revision,
            turn_index=turn_index,
            pass_identity=pass_identity,
            request_ordinal=request_ordinal,
            provider_identity=provider_identity,
            adapter_identity=adapter_identity,
            request_body_sha256=body_sha256,
        )
        return cls(
            evidence_id=evidence_id,
            execution_id=execution_id,
            run_id=run_id,
            scenario_id=scenario_id,
            scenario_revision=scenario_revision,
            turn_index=turn_index,
            pass_identity=pass_identity,
            request_ordinal=request_ordinal,
            provider_identity=provider_identity,
            adapter_identity=adapter_identity,
            request_body=normalized_body,
            request_body_sha256=body_sha256,
        )

    def validate_identity(self) -> None:
        """Recheck content identity before exposing or persisting mutable input."""

        _validate_request_body(self.request_body)
        observed_sha256 = canonical_request_body_sha256(self.request_body)
        if self.request_body_sha256 != observed_sha256:
            raise ActualModelRequestEvidenceError(
                "request body SHA-256 does not match request evidence"
            )
        expected_id = _stable_request_evidence_id(
            execution_id=self.execution_id,
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            scenario_revision=self.scenario_revision,
            turn_index=self.turn_index,
            pass_identity=self.pass_identity,
            request_ordinal=self.request_ordinal,
            provider_identity=self.provider_identity,
            adapter_identity=self.adapter_identity,
            request_body_sha256=self.request_body_sha256,
        )
        if self.evidence_id != expected_id:
            raise ActualModelRequestEvidenceError(
                "request evidence ID does not match its binding and request body"
            )

    def to_mapping(self) -> dict[str, object]:
        self.validate_identity()
        mapping: dict[str, object] = {
            "format_version": self.format_version,
            "evidence_id": self.evidence_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "scenario": {
                "id": self.scenario_id,
                "revision": self.scenario_revision,
            },
            "turn_index": self.turn_index,
            "pass": self.pass_identity,
            "request_ordinal": self.request_ordinal,
            "provider": {
                "identity": self.provider_identity,
                "adapter": self.adapter_identity,
            },
            "attempted": self.attempted,
            "request_body": _copy_json_value(self.request_body),
            "request_body_sha256": self.request_body_sha256,
        }
        if self.failure_exception_type is not None:
            mapping["failure"] = {
                "exception_type": self.failure_exception_type,
                "exception_message": self.failure_exception_message,
            }
        return mapping

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )


@dataclass(slots=True)
class ActualModelRequestEvidenceRecorder:
    """Collect exact attempted requests for one execution without capturing headers."""

    execution_id: str
    run_id: str
    scenario_id: str
    scenario_revision: str
    provider_identity: str
    adapter_identity: str
    _records: list[ActualModelRequestEvidence] = field(default_factory=list, init=False)
    _ordinals: dict[tuple[int, str], int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for name in (
            "execution_id",
            "run_id",
            "scenario_id",
            "scenario_revision",
            "provider_identity",
            "adapter_identity",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    @property
    def records(self) -> tuple[ActualModelRequestEvidence, ...]:
        return tuple(self._records)

    def records_for_turn(self, turn_index: int) -> tuple[ActualModelRequestEvidence, ...]:
        _require_positive_int(turn_index, "turn_index")
        return tuple(item for item in self._records if item.turn_index == turn_index)

    @contextmanager
    def capture(
        self,
        *,
        turn_index: int,
        pass_identity: RequestPassIdentity,
    ) -> Iterator[None]:
        _require_positive_int(turn_index, "turn_index")
        if pass_identity not in _REQUEST_PASSES:
            raise ValueError(f"unsupported request pass identity: {pass_identity}")

        def observe(request_body: Mapping[str, Any]) -> None:
            self.record(
                turn_index=turn_index,
                pass_identity=pass_identity,
                request_body=request_body,
            )

        try:
            with model_facing_request_observation(observe):
                yield
        except BaseException as exc:
            self._annotate_latest_failure(
                turn_index=turn_index,
                pass_identity=pass_identity,
                exc=exc,
            )
            raise

    def record(
        self,
        *,
        turn_index: int,
        pass_identity: RequestPassIdentity,
        request_body: Mapping[str, Any],
    ) -> ActualModelRequestEvidence:
        _require_positive_int(turn_index, "turn_index")
        if pass_identity not in _REQUEST_PASSES:
            raise ValueError(f"unsupported request pass identity: {pass_identity}")
        key = (turn_index, pass_identity)
        ordinal = self._ordinals.get(key, 0) + 1
        self._ordinals[key] = ordinal
        evidence = ActualModelRequestEvidence.create(
            execution_id=self.execution_id,
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            scenario_revision=self.scenario_revision,
            turn_index=turn_index,
            pass_identity=pass_identity,
            request_ordinal=ordinal,
            provider_identity=self.provider_identity,
            adapter_identity=self.adapter_identity,
            request_body=request_body,
        )
        self._records.append(evidence)
        return evidence

    def _annotate_latest_failure(
        self,
        *,
        turn_index: int,
        pass_identity: RequestPassIdentity,
        exc: BaseException,
    ) -> None:
        exception_type, exception_message = bounded_provider_failure_diagnostic(exc)
        for index in range(len(self._records) - 1, -1, -1):
            record = self._records[index]
            if (
                record.turn_index != turn_index
                or record.pass_identity != pass_identity
            ):
                continue
            self._records[index] = replace(
                record,
                failure_exception_type=exception_type,
                failure_exception_message=exception_message,
            )
            return


def canonical_request_body_sha256(request_body: Mapping[str, Any]) -> str:
    normalized = _normalize_request_body(request_body)
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _stable_request_evidence_id(
    *,
    execution_id: str,
    run_id: str,
    scenario_id: str,
    scenario_revision: str,
    turn_index: int,
    pass_identity: RequestPassIdentity,
    request_ordinal: int,
    provider_identity: str,
    adapter_identity: str,
    request_body_sha256: str,
) -> str:
    identity = {
        "format_version": ACTUAL_MODEL_REQUEST_EVIDENCE_FORMAT_VERSION,
        "execution_id": execution_id,
        "run_id": run_id,
        "scenario": {"id": scenario_id, "revision": scenario_revision},
        "turn_index": turn_index,
        "pass": pass_identity,
        "request_ordinal": request_ordinal,
        "provider": {
            "identity": provider_identity,
            "adapter": adapter_identity,
        },
        "request_body_sha256": request_body_sha256,
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amreq-{hashlib.sha256(encoded).hexdigest()}"


def _normalize_request_body(request_body: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request_body, Mapping):
        raise TypeError("request body must be a JSON object")
    normalized = _normalize_json_value(request_body, path="request_body")
    assert isinstance(normalized, dict)
    return normalized


def _normalize_json_value(value: Any, *, path: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not (value == value and value not in {float("inf"), -float("inf")}):
            raise ValueError(f"{path} must contain finite JSON numbers")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(f"{path} keys must be non-empty strings")
            if key.casefold() in _FORBIDDEN_REQUEST_KEYS:
                raise ActualModelRequestEvidenceError(
                    f"request body contains forbidden secret-bearing field: {path}.{key}"
                )
            normalized[key] = _normalize_json_value(item, path=f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            _normalize_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} must contain only JSON-compatible values")


def _validate_request_body(request_body: object) -> None:
    _normalize_request_body(request_body)  # type: ignore[arg-type]


def _copy_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_json_value(item) for item in value]
    return value


def _require_positive_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
