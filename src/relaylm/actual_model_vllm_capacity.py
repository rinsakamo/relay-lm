from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from relaylm.budget_enforcement import TokenCountMode
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


VLLM_RUNTIME_CAPACITY_EVIDENCE_FORMAT_VERSION = 1
VLLM_RUNTIME_CAPACITY_EVIDENCE_PREFIX = "amcap"
VLLM_CAPACITY_FAILURE_KIND = "input_context_overflow"


class VLLMRuntimeCapacityEvidenceError(ValueError):
    """A vLLM runtime-capacity artifact is not valid citable #1386 evidence."""


@dataclass(frozen=True, slots=True)
class VLLMCapacityFootprintObservation:
    """Content-free exact/conservative footprint for one production pass input."""

    topology: str
    pass_id: str
    scenario_id: str
    turn_index: int
    total_input_tokens: int
    required_input_framing_tokens: int
    count_mode: TokenCountMode

    def __post_init__(self) -> None:
        if self.topology not in {"single_pass", "two_pass"}:
            raise VLLMRuntimeCapacityEvidenceError(
                "capacity footprint topology must be single_pass or two_pass"
            )
        allowed_passes = (
            {"single_pass"} if self.topology == "single_pass" else {"pass1", "pass2"}
        )
        if self.pass_id not in allowed_passes:
            raise VLLMRuntimeCapacityEvidenceError(
                "capacity footprint pass_id does not match topology"
            )
        _non_empty_string("scenario_id", self.scenario_id)
        _positive_int("turn_index", self.turn_index)
        _non_negative_int("total_input_tokens", self.total_input_tokens)
        _non_negative_int(
            "required_input_framing_tokens", self.required_input_framing_tokens
        )
        if self.required_input_framing_tokens > self.total_input_tokens:
            raise VLLMRuntimeCapacityEvidenceError(
                "required_input_framing_tokens must not exceed total_input_tokens"
            )
        if not isinstance(self.count_mode, TokenCountMode):
            raise TypeError("count_mode must be TokenCountMode")

    def to_mapping(self) -> dict[str, object]:
        return {
            "topology": self.topology,
            "pass_id": self.pass_id,
            "scenario_id": self.scenario_id,
            "turn_index": self.turn_index,
            "total_input_tokens": self.total_input_tokens,
            "required_input_framing_tokens": self.required_input_framing_tokens,
            "count_mode": self.count_mode.value,
        }


@dataclass(frozen=True, slots=True)
class VLLMCapacityFailureObservation:
    """Independent content-free proof that a configured runtime capacity overflowed."""

    configured_max_model_len: int
    observed_input_tokens: int
    http_status: int
    failure_kind: str = VLLM_CAPACITY_FAILURE_KIND

    def __post_init__(self) -> None:
        _positive_int("configured_max_model_len", self.configured_max_model_len)
        _positive_int("observed_input_tokens", self.observed_input_tokens)
        if self.observed_input_tokens <= self.configured_max_model_len:
            raise VLLMRuntimeCapacityEvidenceError(
                "capacity failure observation must exceed configured_max_model_len"
            )
        if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
            raise TypeError("http_status must be an integer")
        if not 400 <= self.http_status <= 499:
            raise VLLMRuntimeCapacityEvidenceError(
                "capacity failure observation requires a 4xx HTTP status"
            )
        if self.failure_kind != VLLM_CAPACITY_FAILURE_KIND:
            raise VLLMRuntimeCapacityEvidenceError(
                "unsupported vLLM capacity failure_kind"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "configured_max_model_len": self.configured_max_model_len,
            "observed_input_tokens": self.observed_input_tokens,
            "http_status": self.http_status,
            "failure_kind": self.failure_kind,
        }


@dataclass(frozen=True, slots=True)
class VLLMRuntimeCapacityEvidence:
    """Immutable content-free capacity prerequisite evidence for one vLLM runtime class."""

    relaylm_commit: str
    target_id: str
    target_revision: str
    tokenizer_identity: str
    chat_template_identity: str
    backend_version: str
    request_model: str
    observed_max_model_len: int
    counter_identity: SerializedInputCounterIdentity
    footprints: tuple[VLLMCapacityFootprintObservation, ...]
    failed_capacity: VLLMCapacityFailureObservation | None = None
    format_version: int = VLLM_RUNTIME_CAPACITY_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != VLLM_RUNTIME_CAPACITY_EVIDENCE_FORMAT_VERSION:
            raise VLLMRuntimeCapacityEvidenceError(
                "unsupported vLLM runtime-capacity evidence format_version"
            )
        _hex_string("relaylm_commit", self.relaylm_commit, 40)
        for name in (
            "target_id",
            "tokenizer_identity",
            "chat_template_identity",
            "backend_version",
            "request_model",
        ):
            _non_empty_string(name, getattr(self, name))
        if not self.target_revision.startswith("sha256:"):
            raise VLLMRuntimeCapacityEvidenceError(
                "target_revision must be a sha256 identity"
            )
        _hex_string("target_revision digest", self.target_revision.removeprefix("sha256:"), 64)
        _positive_int("observed_max_model_len", self.observed_max_model_len)
        if not isinstance(self.counter_identity, SerializedInputCounterIdentity):
            raise TypeError("counter_identity must be SerializedInputCounterIdentity")
        if not isinstance(self.footprints, tuple) or not self.footprints:
            raise VLLMRuntimeCapacityEvidenceError(
                "capacity evidence footprints must be a non-empty tuple"
            )
        if any(
            not isinstance(item, VLLMCapacityFootprintObservation)
            for item in self.footprints
        ):
            raise TypeError(
                "capacity evidence footprints must contain VLLMCapacityFootprintObservation"
            )
        if self.failed_capacity is not None and not isinstance(
            self.failed_capacity, VLLMCapacityFailureObservation
        ):
            raise TypeError(
                "failed_capacity must be VLLMCapacityFailureObservation or None"
            )
        _validate_counter_identity(self)

    @property
    def maximum_observed_input_tokens(self) -> int:
        return max(item.total_input_tokens for item in self.footprints)

    @property
    def evidence_id(self) -> str:
        digest = hashlib.sha256(_canonical_json_bytes(self._identity_mapping())).hexdigest()
        return f"{VLLM_RUNTIME_CAPACITY_EVIDENCE_PREFIX}-{digest}"

    def _identity_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "relaylm_commit": self.relaylm_commit,
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "tokenizer_identity": self.tokenizer_identity,
            "chat_template_identity": self.chat_template_identity,
            "backend_version": self.backend_version,
            "request_model": self.request_model,
            "observed_max_model_len": self.observed_max_model_len,
            "counter_identity": self.counter_identity.to_mapping(),
            "footprints": [item.to_mapping() for item in self.footprints],
            "failed_capacity": (
                self.failed_capacity.to_mapping()
                if self.failed_capacity is not None
                else None
            ),
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self._identity_mapping()
        mapping["evidence_id"] = self.evidence_id
        return mapping

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def validate_capacity_window(
    *,
    evidence: VLLMRuntimeCapacityEvidence,
    capacity_evidence_id: str,
    effective_context_window: int,
) -> None:
    """Validate one selected window against cited demand without selecting a value."""

    if not isinstance(evidence, VLLMRuntimeCapacityEvidence):
        raise TypeError("evidence must be VLLMRuntimeCapacityEvidence")
    if capacity_evidence_id != evidence.evidence_id:
        raise VLLMRuntimeCapacityEvidenceError(
            "capacity_evidence_id does not match the cited evidence artifact"
        )
    _positive_int("effective_context_window", effective_context_window)
    if effective_context_window <= evidence.maximum_observed_input_tokens:
        raise VLLMRuntimeCapacityEvidenceError(
            "effective_context_window does not resolve the cited serialized-input footprint"
        )
    if effective_context_window > evidence.observed_max_model_len:
        raise VLLMRuntimeCapacityEvidenceError(
            "effective_context_window exceeds the attested vLLM runtime capacity"
        )


def write_vllm_runtime_capacity_evidence(
    *,
    evidence: VLLMRuntimeCapacityEvidence,
    artifact_root: str | Path,
) -> Path:
    """Persist one capacity record immutably under its content-addressed evidence ID."""

    if not isinstance(evidence, VLLMRuntimeCapacityEvidence):
        raise TypeError("evidence must be VLLMRuntimeCapacityEvidence")
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{evidence.evidence_id}.json"
    payload = evidence.to_json() + "\n"
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{evidence.evidence_id}.{os.getpid()}.tmp"
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
        raise VLLMRuntimeCapacityEvidenceError(
            f"cannot persist vLLM runtime-capacity evidence: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_vllm_runtime_capacity_evidence(path: str | Path) -> VLLMRuntimeCapacityEvidence:
    """Strictly load and identity-check one reviewed capacity artifact."""

    source = Path(path)
    try:
        raw = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VLLMRuntimeCapacityEvidenceError(
            f"cannot load vLLM runtime-capacity evidence: {exc}"
        ) from exc
    mapping = _mapping(raw, "vLLM runtime-capacity evidence")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "evidence_id",
            "relaylm_commit",
            "target_id",
            "target_revision",
            "tokenizer_identity",
            "chat_template_identity",
            "backend_version",
            "request_model",
            "observed_max_model_len",
            "counter_identity",
            "footprints",
            "failed_capacity",
        },
        "vLLM runtime-capacity evidence",
    )
    evidence = VLLMRuntimeCapacityEvidence(
        format_version=_integer(mapping["format_version"], "format_version"),
        relaylm_commit=_string(mapping["relaylm_commit"], "relaylm_commit"),
        target_id=_string(mapping["target_id"], "target_id"),
        target_revision=_string(mapping["target_revision"], "target_revision"),
        tokenizer_identity=_string(mapping["tokenizer_identity"], "tokenizer_identity"),
        chat_template_identity=_string(
            mapping["chat_template_identity"], "chat_template_identity"
        ),
        backend_version=_string(mapping["backend_version"], "backend_version"),
        request_model=_string(mapping["request_model"], "request_model"),
        observed_max_model_len=_integer(
            mapping["observed_max_model_len"], "observed_max_model_len"
        ),
        counter_identity=_parse_counter_identity(mapping["counter_identity"]),
        footprints=tuple(
            _parse_footprint(item, index=index)
            for index, item in enumerate(_list(mapping["footprints"], "footprints"))
        ),
        failed_capacity=_parse_failure(mapping["failed_capacity"]),
    )
    observed_id = _string(mapping["evidence_id"], "evidence_id")
    if observed_id != evidence.evidence_id:
        raise VLLMRuntimeCapacityEvidenceError(
            "capacity evidence_id does not match artifact contents"
        )
    return evidence


def capacity_evidence_path(*, artifact_root: str | Path, evidence_id: str) -> Path:
    _non_empty_string("evidence_id", evidence_id)
    prefix = f"{VLLM_RUNTIME_CAPACITY_EVIDENCE_PREFIX}-"
    if not evidence_id.startswith(prefix):
        raise VLLMRuntimeCapacityEvidenceError(
            "vLLM capacity evidence ID must be a content-addressed amcap SHA-256 ID"
        )
    digest = evidence_id[len(prefix) :]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise VLLMRuntimeCapacityEvidenceError(
            "vLLM capacity evidence ID must be a content-addressed amcap SHA-256 ID"
        )
    return Path(artifact_root) / f"{evidence_id}.json"


def _validate_counter_identity(evidence: VLLMRuntimeCapacityEvidence) -> None:
    counter = evidence.counter_identity
    if counter.tokenizer_identity != evidence.tokenizer_identity:
        raise VLLMRuntimeCapacityEvidenceError(
            "capacity counter tokenizer identity does not match evidence"
        )
    if any(item.count_mode is not counter.mode for item in evidence.footprints):
        raise VLLMRuntimeCapacityEvidenceError(
            "capacity footprint count mode does not match counter identity"
        )
    parameters = dict(counter.parameters)
    expected = {
        "backend": "vllm",
        "backend_version": evidence.backend_version,
        "chat_template_identity": evidence.chat_template_identity,
        "context_limit": evidence.observed_max_model_len,
        "request_model": evidence.request_model,
        "target_id": evidence.target_id,
    }
    for key, value in expected.items():
        if parameters.get(key) != value:
            raise VLLMRuntimeCapacityEvidenceError(
                f"capacity counter identity {key} does not match evidence"
            )


def _parse_counter_identity(value: object) -> SerializedInputCounterIdentity:
    mapping = _mapping(value, "counter_identity")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "capability",
            "implementation",
            "version",
            "mode",
            "tokenizer_identity",
            "parameters",
        },
        "counter_identity",
    )
    params = _mapping(mapping["parameters"], "counter_identity.parameters")
    for key, item in params.items():
        if not isinstance(item, (str, int, float, bool)) and item is not None:
            raise VLLMRuntimeCapacityEvidenceError(
                f"counter_identity.parameters.{key} must be a JSON scalar"
            )
    try:
        mode = TokenCountMode(_string(mapping["mode"], "counter_identity.mode"))
        return SerializedInputCounterIdentity(
            format_version=_integer(
                mapping["format_version"], "counter_identity.format_version"
            ),
            capability=_string(mapping["capability"], "counter_identity.capability"),
            implementation=_string(
                mapping["implementation"], "counter_identity.implementation"
            ),
            version=_string(mapping["version"], "counter_identity.version"),
            mode=mode,
            tokenizer_identity=_string(
                mapping["tokenizer_identity"], "counter_identity.tokenizer_identity"
            ),
            parameters=tuple(sorted(params.items())),
        )
    except (TypeError, ValueError) as exc:
        raise VLLMRuntimeCapacityEvidenceError(
            f"invalid counter_identity: {exc}"
        ) from exc


def _parse_footprint(value: object, *, index: int) -> VLLMCapacityFootprintObservation:
    label = f"footprints[{index}]"
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {
            "topology",
            "pass_id",
            "scenario_id",
            "turn_index",
            "total_input_tokens",
            "required_input_framing_tokens",
            "count_mode",
        },
        label,
    )
    try:
        return VLLMCapacityFootprintObservation(
            topology=_string(mapping["topology"], f"{label}.topology"),
            pass_id=_string(mapping["pass_id"], f"{label}.pass_id"),
            scenario_id=_string(mapping["scenario_id"], f"{label}.scenario_id"),
            turn_index=_integer(mapping["turn_index"], f"{label}.turn_index"),
            total_input_tokens=_integer(
                mapping["total_input_tokens"], f"{label}.total_input_tokens"
            ),
            required_input_framing_tokens=_integer(
                mapping["required_input_framing_tokens"],
                f"{label}.required_input_framing_tokens",
            ),
            count_mode=TokenCountMode(
                _string(mapping["count_mode"], f"{label}.count_mode")
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, VLLMRuntimeCapacityEvidenceError):
            raise
        raise VLLMRuntimeCapacityEvidenceError(
            f"invalid {label}: {exc}"
        ) from exc


def _parse_failure(value: object) -> VLLMCapacityFailureObservation | None:
    if value is None:
        return None
    mapping = _mapping(value, "failed_capacity")
    _require_exact_keys(
        mapping,
        {
            "configured_max_model_len",
            "observed_input_tokens",
            "http_status",
            "failure_kind",
        },
        "failed_capacity",
    )
    return VLLMCapacityFailureObservation(
        configured_max_model_len=_integer(
            mapping["configured_max_model_len"],
            "failed_capacity.configured_max_model_len",
        ),
        observed_input_tokens=_integer(
            mapping["observed_input_tokens"], "failed_capacity.observed_input_tokens"
        ),
        http_status=_integer(mapping["http_status"], "failed_capacity.http_status"),
        failure_kind=_string(mapping["failure_kind"], "failed_capacity.failure_kind"),
    )


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise VLLMRuntimeCapacityEvidenceError(
            f"cannot read existing vLLM runtime-capacity evidence: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise VLLMRuntimeCapacityEvidenceError(
        "capacity evidence ID already exists with different bytes"
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VLLMRuntimeCapacityEvidenceError(
                f"duplicate JSON key in vLLM capacity evidence: {key}"
            )
        result[key] = value
    return result


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be an object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be a list")
    return value


def _require_exact_keys(mapping: Mapping[str, object], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(mapping))
    unknown = sorted(set(mapping) - expected)
    if missing:
        raise VLLMRuntimeCapacityEvidenceError(
            f"{label} is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise VLLMRuntimeCapacityEvidenceError(
            f"{label} has unknown fields: " + ", ".join(unknown)
        )


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be an integer")
    return value


def _positive_int(label: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value <= 0:
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be positive")


def _non_negative_int(label: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < 0:
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must be non-negative")


def _non_empty_string(label: str, value: object) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if not value.strip():
        raise VLLMRuntimeCapacityEvidenceError(f"{label} must not be empty")


def _hex_string(label: str, value: object, length: int) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise VLLMRuntimeCapacityEvidenceError(
            f"{label} must be {length} lowercase hexadecimal characters"
        )
