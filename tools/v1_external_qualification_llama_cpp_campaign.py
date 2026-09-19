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
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import httpx
from tools.external_qualification import (
    CLASSIFICATIONS,
    SLOTS,
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    LiveLaunchAdmissionAttestation,
    ScientificSpendLedger,
    _stable_capacity,
    freeze_experiment_identity,
    validate_manifest,
    validate_participant_accounting,
    validate_observation,
    validate_case,
    stable_run_id,
    write_citable_evidence,
)
from tools.external_qualification_readiness import (
    ExternalQualificationReadinessError,
    validate_launch_readiness,
)
from tools.llama_cpp_identity import (
    LlamaCppIdentityError,
    parse_props_build_info,
    probe_cli_identity,
    verify_props_build_info,
)


CAMPAIGN_TARGET = "v1:external-qualification-campaign"
CAMPAIGN_FORMAT_VERSION = 1
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_OWNER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_BANK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_RUN_MODES = {"fresh_run", "exact_infrastructure_resume"}

# These values are copied from the frozen Hermes/MemConflict common harness,
# not inferred from Hindsight defaults.  The C adapter owns retrieval only;
# answer generation below uses this one provider-neutral boundary for every
# governed axis (including the bounded LongMemEval knowledge-update axis).
HINDSIGHT_RETAIN_GRANULARITY = "exchange_append"
# Pinned Hindsight v0.10.0 defaults retain extraction to 64k output tokens,
# which cannot terminate safely inside the frozen 8192-token llama.cpp context.
# Keep this repository-owned, benchmark-independent infrastructure bound above
# Hindsight's pinned default 3000-character retain chunk size.
HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS = 4096
# Pinned Hindsight v0.10.0 otherwise permits completed retain operations after
# accumulated extraction errors. Qualification must never treat dropped facts
# as a successful comparator write.
HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS = True
HINDSIGHT_RECALL_BUDGET = "mid"
HINDSIGHT_RECALL_MAX_TOKENS = 4096
HINDSIGHT_RECALL_TYPES = ("observation",)
HINDSIGHT_PREFER_OBSERVATIONS = True
HINDSIGHT_HTTP_TIMEOUT_SECONDS = 120.0
HINDSIGHT_WAIT_CONSOLIDATION = True
HINDSIGHT_CONSOLIDATION_WAIT_TIMEOUT_SECONDS = 450.0
HINDSIGHT_CONSOLIDATION_POLL_SECONDS = 0.25
COMMON_ANSWER_SYSTEM_PROMPT = (
    "You answer memory-evaluation questions using only the retrieved memory context.\n\n"
    "Rules:\n"
    "1. Use only the retrieved memories.\n"
    "2. Do not invent facts that are not supported by the retrieved memories.\n"
    "3. If the memories are insufficient, say that you cannot confirm.\n"
    "4. If the memories contain inconsistent statements, briefly mention the inconsistency first and then give the best-supported answer.\n"
    "5. Keep the answer concise, natural, and directly responsive to the question."
)
_COMMON_ANSWER_USER_PREFIX = "Retrieved Memory Context:\n"
_COMMON_ANSWER_USER_QUESTION = "\n\nQuestion:\n"
_COMMON_ANSWER_USER_SUFFIX = "\n\nAnswer:"
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
_RC_KEYS = {
    "wheel_path",
    "wheel_sha256",
    "version",
    "source_revision",
    "source_tree",
    "distribution",
    "config_path",
    "config_sha256",
    "port",
}
_LIFECYCLE_KEYS = {
    "mode",
    "base_url",
    "health_path",
    "deployment_id",
    "dependency_fingerprint",
    "cleanup_path",
    "start_path",
    "runtime_python",
    "runtime_version",
    "source_revision",
    "source_tree",
    "database_profile",
    "llm_model",
    "llm_base_url",
    "retain_max_completion_tokens",
    "fail_on_extraction_errors",
    "embeddings_provider",
    "reranker_provider",
    "embeddings_onnx_model_path",
    "embeddings_onnx_model_sha256",
    "embeddings_onnx_tokenizer_path",
    "embeddings_onnx_tokenizer_tree_sha256",
    "package_wheel_sha256",
    "port",
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
_PRODUCTION_DESCRIPTOR_KEYS = _DESCRIPTOR_KEYS | {
    "owner_id",
    "spend_ledger_path",
    "relaylm_exact_rc",
    "hindsight_lifecycle",
}
_AXIS_KEYS = {"axis_id", "case", "manifest", "identity", "questions", "run_mode"}
_PRODUCTION_AXIS_KEYS = _AXIS_KEYS | {"classification"}
_PRODUCTION_AXIS_KEYS = _PRODUCTION_AXIS_KEYS | {"benchmark_material", "history_material"}
_MATERIAL_KEYS = {"path", "sha256", "case_fingerprint", "question_fingerprints"}
_HISTORY_MATERIAL_KEYS = {"path", "sha256"}
_QUESTION_KEYS = {"question_id", "prompt", "content_fingerprint", "session_id"}
_CLEANUP_KEYS = {
    "all_owned_processes_terminated",
    "external_processes_touched",
    "errors",
}


class CampaignCarriageError(ExternalQualificationError):
    """Raised when the bounded campaign contract cannot be admitted."""


class HindsightSemanticRequestError(CampaignCarriageError):
    """A bounded semantic Hindsight HTTP failure with route evidence."""

    def __init__(
        self,
        *,
        operation: str,
        method: str,
        path: str,
        status_code: int,
        allow: str | None,
        body: str,
    ) -> None:
        self.operation = operation
        self.method = method
        self.path = path
        self.status_code = status_code
        self.allow = allow
        self.body = body[:1024]
        allow_text = "" if allow is None else f" allow={allow!r}"
        super().__init__(
            f"Hindsight {operation} request failed: {method} {path} "
            f"HTTP {status_code}{allow_text} body={self.body!r}"
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "method": self.method,
            "path": self.path,
            "status": self.status_code,
            "allow": self.allow,
            "body": self.body,
        }


class _HindsightReadinessPending(Exception):
    """The owned Hindsight process is still becoming ready."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json_fsync(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)) + "\n")
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
        raise CampaignCarriageError(f"cannot persist launch evidence: {exc}") from exc


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


def _require_owner_id(value: object) -> str:
    owner_id = _require_nonempty_string(value, label="owner_id")
    if _OWNER_ID_RE.fullmatch(owner_id) is None:
        raise CampaignCarriageError(
            "owner_id must be a stable ASCII identifier using letters, digits, dot, underscore, or hyphen"
        )
    return owner_id


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


def _require_package_hashes(value: object) -> dict[str, str]:
    raw = _require_mapping(value, label="hindsight_lifecycle.package_wheel_sha256")
    expected = {
        "hindsight-all",
        "hindsight-api-slim",
        "hindsight-client",
        "hindsight-embed",
    }
    if set(raw) != expected:
        raise CampaignCarriageError(
            "hindsight_lifecycle.package_wheel_sha256 must identify the four exact Hindsight wheels"
        )
    return {
        name: _require_sha(
            raw[name],
            label=f"hindsight_lifecycle.package_wheel_sha256.{name}",
            pattern=_SHA256_RE,
        )
        for name in sorted(expected)
    }


def _require_material(value: object, *, label: str) -> dict[str, Any]:
    raw = _require_mapping(value, label=label)
    _require_exact_keys(raw, _MATERIAL_KEYS, label=label)
    path = _require_absolute_path(raw["path"], label=f"{label}.path")
    if not path.is_file():
        raise CampaignCarriageError(f"{label}.path is not a file: {path}")
    expected_sha = _require_sha(raw["sha256"], label=f"{label}.sha256", pattern=_SHA256_RE)
    observed_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed_sha != expected_sha:
        raise CampaignCarriageError(
            f"{label}.path content drifted: expected {expected_sha}, observed {observed_sha}"
        )
    case_fingerprint = _require_nonempty_string(
        raw["case_fingerprint"], label=f"{label}.case_fingerprint"
    )
    question_fingerprints = raw["question_fingerprints"]
    if not isinstance(question_fingerprints, list) or not all(
        isinstance(item, str) and _FINGERPRINT_RE.fullmatch(item) is not None
        for item in question_fingerprints
    ):
        raise CampaignCarriageError(
            f"{label}.question_fingerprints must be fingerprint strings"
        )
    return {
        "path": str(path),
        "sha256": expected_sha,
        "case_fingerprint": case_fingerprint,
        "question_fingerprints": list(question_fingerprints),
    }


@dataclass(frozen=True, slots=True)
class HindsightHistorySession:
    """One ordered model-facing session with no benchmark reference fields."""

    session_id: str
    order: int
    items: tuple[Mapping[str, str | None], ...]

    def exchanges(self) -> tuple[tuple[Mapping[str, str | None], ...], ...]:
        """Pair adjacent user/assistant turns exactly as the frozen adapter."""

        pairs: list[tuple[Mapping[str, str | None], ...]] = []
        index = 0
        while index < len(self.items):
            current = self.items[index]
            following = self.items[index + 1] if index + 1 < len(self.items) else None
            if (
                following is not None
                and current["role"] == "user"
                and following["role"] == "assistant"
            ):
                pairs.append((current, following))
                index += 2
            else:
                pairs.append((current,))
                index += 1
        return tuple(pairs)

    def to_retain_items(self) -> tuple[dict[str, object], ...]:
        """Return the pre-contract representation for diagnostic callers.

        Production C uses :meth:`to_retain_requests`, which is the frozen
        exchange-append shape.  Keeping this narrow helper avoids changing the
        typed history-material surface for read-only diagnostics.
        """

        document_id = f"relaylm-history-{self.order:08d}"
        return tuple(
            {
                "content": item["content"],
                "context": item["role"],
                "timestamp": item["timestamp"],
                "document_id": document_id,
            }
            for item in self.items
        )

    def to_retain_request(
        self,
        *,
        bank_id: str,
        context_label: str,
        exchange_index: int,
    ) -> dict[str, object]:
        """Materialize one exchange-append retain immediately before first use.

        MemConflict mirrors the frozen Hermes Arm-C metadata exactly. The
        retained_at value is wall-clock and is materialized only after durable
        state says the logical exchange is new. LongMemEval shares the typed
        history/append boundary but does not inherit MemConflict-only metadata.
        """

        exchanges = self.exchanges()
        if (
            isinstance(exchange_index, bool)
            or not isinstance(exchange_index, int)
            or exchange_index < 0
            or exchange_index >= len(exchanges)
        ):
            raise CampaignCarriageError(
                "Hindsight history exchange_index is outside the session"
            )
        session_base = _parse_history_timestamp(
            next(
                (
                    item["timestamp"]
                    for item in self.items
                    if isinstance(item.get("timestamp"), str)
                    and item["timestamp"].strip()
                ),
                None,
            )
        )
        exchange = exchanges[exchange_index]
        logical_timestamp = (
            session_base + timedelta(minutes=exchange_index)
            if session_base is not None
            else None
        )
        timestamp = (
            logical_timestamp.isoformat() if logical_timestamp is not None else None
        )
        turn_payload = [
            {
                "role": item["role"],
                "content": (
                    ("User: " if item["role"] == "user" else "Assistant: ")
                    + str(item["content"])
                ),
                "timestamp": timestamp,
            }
            for item in exchange
        ]
        request: dict[str, object] = {
            "content": json.dumps(
                turn_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "context": f"{context_label} dialogue session {self.session_id}",
            "timestamp": timestamp,
            "document_id": f"{bank_id}_doc_{self.session_id}",
            "update_mode": "append",
        }
        if context_label == "MemConflict":
            session_date_iso = (
                session_base.isoformat() if session_base is not None else None
            )
            request["metadata"] = {
                "retained_at": datetime.now(timezone.utc).isoformat(),
                "message_count": str(len(exchange)),
                "turn_index": str(exchange_index),
                "session_date": str(session_date_iso),
            }
        elif context_label == "LongMemEval":
            pass
        else:
            raise CampaignCarriageError(
                "Hindsight retain contract is bounded to MemConflict or LongMemEval"
            )
        return request

    def to_retain_requests(
        self,
        *,
        bank_id: str,
        context_label: str,
    ) -> tuple[dict[str, object], ...]:
        """Diagnostic wrapper over first-use request materialization."""

        return tuple(
            self.to_retain_request(
                bank_id=bank_id,
                context_label=context_label,
                exchange_index=exchange_index,
            )
            for exchange_index, _exchange in enumerate(self.exchanges())
        )


@dataclass(frozen=True, slots=True)
class HindsightHistoryPlan:
    """Validated model-facing history and question-time session prefixes."""

    sessions: tuple[HindsightHistorySession, ...]
    question_history: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_path(cls, path: Path) -> "HindsightHistoryPlan":
        try:
            raw_value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignCarriageError(
                f"cannot read Hindsight history material {path}: {exc}"
            ) from exc
        raw = _require_mapping(raw_value, label="Hindsight history material")
        _require_exact_keys(
            raw,
            {"format_version", "sessions", "question_history"},
            label="Hindsight history material",
        )
        if raw["format_version"] != 1:
            raise CampaignCarriageError(
                "Hindsight history material format_version must be 1"
            )
        sessions_raw = raw["sessions"]
        if not isinstance(sessions_raw, list) or not sessions_raw:
            raise CampaignCarriageError(
                "Hindsight history material sessions must be a non-empty list"
            )
        sessions: list[HindsightHistorySession] = []
        seen_ids: set[str] = set()
        for expected_order, session_value in enumerate(sessions_raw):
            session = _require_mapping(
                session_value,
                label=f"Hindsight history session {expected_order}",
            )
            _require_exact_keys(
                session,
                {"session_id", "order", "items"},
                label=f"Hindsight history session {expected_order}",
            )
            session_id = _require_nonempty_string(
                session["session_id"],
                label=f"Hindsight history session {expected_order}.session_id",
            )
            if session_id in seen_ids:
                raise CampaignCarriageError(
                    f"Hindsight history session id is duplicated: {session_id!r}"
                )
            seen_ids.add(session_id)
            order = session["order"]
            if isinstance(order, bool) or not isinstance(order, int) or order != expected_order:
                raise CampaignCarriageError(
                    "Hindsight history session order must be contiguous and ordered"
                )
            items_raw = session["items"]
            if not isinstance(items_raw, list) or not items_raw:
                raise CampaignCarriageError(
                    f"Hindsight history session {session_id!r} items must be non-empty"
                )
            items: list[Mapping[str, str | None]] = []
            for item_index, item_value in enumerate(items_raw):
                item = _require_mapping(
                    item_value,
                    label=f"Hindsight history {session_id} item {item_index}",
                )
                _require_exact_keys(
                    item,
                    {"role", "content", "timestamp"},
                    label=f"Hindsight history {session_id} item {item_index}",
                )
                role = _require_nonempty_string(
                    item["role"],
                    label=f"Hindsight history {session_id} item {item_index}.role",
                )
                if role not in {"user", "assistant"}:
                    raise CampaignCarriageError(
                        "Hindsight history item role must be user or assistant"
                    )
                content = _require_nonempty_string(
                    item["content"],
                    label=f"Hindsight history {session_id} item {item_index}.content",
                )
                timestamp = item["timestamp"]
                if timestamp is not None and (
                    not isinstance(timestamp, str) or not timestamp.strip()
                ):
                    raise CampaignCarriageError(
                        "Hindsight history item timestamp must be null or a non-empty string"
                    )
                items.append(
                    {
                        "role": role,
                        "content": content,
                        "timestamp": timestamp,
                    }
                )
            sessions.append(
                HindsightHistorySession(
                    session_id=session_id,
                    order=order,
                    items=tuple(items),
                )
            )

        question_history_raw = _require_mapping(
            raw["question_history"], label="Hindsight history question_history"
        )
        question_history: dict[str, tuple[str, ...]] = {}
        ordered_session_ids = tuple(session.session_id for session in sessions)
        for question_id, session_ids_value in question_history_raw.items():
            question_key = _require_nonempty_string(
                question_id,
                label="Hindsight history question id",
            )
            if not isinstance(session_ids_value, list) or not all(
                isinstance(item, str) and item in seen_ids for item in session_ids_value
            ):
                raise CampaignCarriageError(
                    f"Hindsight history question {question_key!r} has invalid session ids"
                )
            session_ids = tuple(session_ids_value)
            if len(session_ids) != len(set(session_ids)):
                raise CampaignCarriageError(
                    f"Hindsight history question {question_key!r} repeats a session"
                )
            if session_ids != ordered_session_ids[: len(session_ids)]:
                raise CampaignCarriageError(
                    f"Hindsight history question {question_key!r} is not an ordered prefix"
                )
            question_history[question_key] = session_ids
        if not question_history:
            raise CampaignCarriageError(
                "Hindsight history question_history must not be empty"
            )
        return cls(sessions=tuple(sessions), question_history=question_history)

    def validate_questions(self, question_ids: Sequence[str]) -> None:
        expected = set(question_ids)
        actual = set(self.question_history)
        if actual != expected:
            raise CampaignCarriageError(
                "Hindsight history question ids must exactly match campaign questions"
            )
        previous: tuple[str, ...] = ()
        for question_id in question_ids:
            current = self.question_history[question_id]
            if current[: len(previous)] != previous:
                raise CampaignCarriageError(
                    "Hindsight history prefixes must not regress in campaign question order"
                )
            previous = current

    def sessions_for_question(self, question_id: str) -> tuple[HindsightHistorySession, ...]:
        try:
            session_ids = self.question_history[question_id]
        except KeyError as exc:
            raise CampaignCarriageError(
                f"Hindsight history has no entry for question {question_id!r}"
            ) from exc
        by_id = {session.session_id: session for session in self.sessions}
        return tuple(by_id[session_id] for session_id in session_ids)

    def query_timestamp_for_question(
        self,
        question_id: str,
        *,
        question_timestamp: str | None = None,
    ) -> str | None:
        """Return the frozen logical-noon recall anchor.

        LongMemEval supplies an explicit question date; when that field is
        present the adapter-owned date wins.  MemConflict has no separate
        question date in the carried material, so its last retained session
        date is the deterministic anchor.  Missing/unparseable dates remain
        ``None`` and preserve Hindsight's documented wall-clock fallback.
        """

        sessions = self.sessions_for_question(question_id)
        candidate = question_timestamp
        if candidate is None and sessions:
            candidate = next(
                (
                    item["timestamp"]
                    for item in reversed(sessions[-1].items)
                    if isinstance(item.get("timestamp"), str)
                    and item["timestamp"].strip()
                ),
                None,
            )
        parsed = _parse_history_timestamp(candidate)
        return parsed.replace(hour=12, minute=0, second=0, microsecond=0).isoformat() if parsed else None


def _parse_history_timestamp(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.combine(
                datetime.fromisoformat(normalized).date(),
                datetime.min.time(),
            )
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc)


def _require_history_material(value: object, *, label: str) -> dict[str, str]:
    raw = _require_mapping(value, label=label)
    _require_exact_keys(raw, _HISTORY_MATERIAL_KEYS, label=label)
    path = _require_absolute_path(raw["path"], label=f"{label}.path")
    if not path.is_file():
        raise CampaignCarriageError(f"{label}.path is not a file: {path}")
    expected_sha = _require_sha(raw["sha256"], label=f"{label}.sha256", pattern=_SHA256_RE)
    if _sha256_file(path) != expected_sha:
        raise CampaignCarriageError(f"{label}.path content drifted")
    HindsightHistoryPlan.from_path(path)
    return {"path": str(path), "sha256": expected_sha}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CampaignCarriageError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _sha256_file_tree(path: Path) -> str:
    if not path.is_dir():
        raise CampaignCarriageError(f"tokenizer path is not a directory: {path}")
    entries: list[dict[str, str]] = []
    try:
        children = sorted(item for item in path.rglob("*") if item.is_file())
    except OSError as exc:
        raise CampaignCarriageError(f"cannot enumerate tokenizer path {path}: {exc}") from exc
    for child in children:
        if child.is_symlink():
            raise CampaignCarriageError(f"tokenizer path contains a symlink: {child}")
        entries.append(
            {
                "path": child.relative_to(path).as_posix(),
                "sha256": _sha256_file(child),
            }
        )
    if not entries:
        raise CampaignCarriageError(f"tokenizer path is empty: {path}")
    return _sha256_json(entries)


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
        return f"sha256:{_sha256_json(self.value)}"


class HindsightHealthProbe(Protocol):
    """Typed probe supplied by the scientific owner; it performs no benchmark work."""

    def attest_zero_semantic_health(self) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class HindsightLifecycleSpec:
    """Fixed lifecycle boundary for one exact Hindsight deployment.

    ``owned_local`` is the production binding.  Its interpreter, database
    profile, model endpoint, and package identity are typed deployment facts;
    the target supplies no executable, import string, or shell fragment.
    ``owned_http`` and ``attested_http`` remain available to deterministic
    controller tests and to an explicitly owned external supervisor.
    """

    mode: str
    base_url: str
    health_path: str
    deployment_id: str
    dependency_fingerprint: str
    cleanup_path: str
    start_path: str
    runtime_python: Path
    runtime_version: str
    source_revision: str
    source_tree: str
    database_profile: str
    llm_model: str
    llm_base_url: str
    retain_max_completion_tokens: int
    fail_on_extraction_errors: bool
    embeddings_provider: str
    reranker_provider: str
    package_wheel_sha256: Mapping[str, str]
    embeddings_onnx_model_path: Path
    embeddings_onnx_model_sha256: str
    embeddings_onnx_tokenizer_path: Path
    embeddings_onnx_tokenizer_tree_sha256: str
    port: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "HindsightLifecycleSpec":
        _require_exact_keys(raw, _LIFECYCLE_KEYS, label="hindsight_lifecycle")
        mode = _require_nonempty_string(raw["mode"], label="hindsight_lifecycle.mode")
        if mode not in {"owned_local", "owned_http", "attested_http"}:
            raise CampaignCarriageError(
                "hindsight_lifecycle.mode must be owned_local, owned_http, or attested_http"
            )
        base_url = _require_nonempty_string(
            raw["base_url"], label="hindsight_lifecycle.base_url"
        ).rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            raise CampaignCarriageError("hindsight_lifecycle.base_url must be HTTP(S)")
        paths = {
            name: _require_nonempty_string(
                raw[name], label=f"hindsight_lifecycle.{name}"
            )
            for name in ("health_path", "cleanup_path", "start_path")
        }
        if any(not value.startswith("/") or "?" in value for value in paths.values()):
            raise CampaignCarriageError(
                "hindsight_lifecycle paths must be fixed path-only values"
            )
        deployment_id = _require_nonempty_string(
            raw["deployment_id"], label="hindsight_lifecycle.deployment_id"
        )
        dependency = _require_sha(
            raw["dependency_fingerprint"],
            label="hindsight_lifecycle.dependency_fingerprint",
            pattern=_FINGERPRINT_RE,
        )
        port = _require_positive_int(raw["port"], label="Hindsight port")
        if port > 65535:
            raise CampaignCarriageError("Hindsight port must be <= 65535")
        onnx_model_path = _require_absolute_path(
            raw["embeddings_onnx_model_path"],
            label="hindsight_lifecycle.embeddings_onnx_model_path",
        )
        onnx_model_sha256 = _require_sha(
            raw["embeddings_onnx_model_sha256"],
            label="hindsight_lifecycle.embeddings_onnx_model_sha256",
            pattern=_SHA256_RE,
        )
        onnx_tokenizer_path = _require_absolute_path(
            raw["embeddings_onnx_tokenizer_path"],
            label="hindsight_lifecycle.embeddings_onnx_tokenizer_path",
        )
        onnx_tokenizer_tree_sha256 = _require_sha(
            raw["embeddings_onnx_tokenizer_tree_sha256"],
            label="hindsight_lifecycle.embeddings_onnx_tokenizer_tree_sha256",
            pattern=_SHA256_RE,
        )
        if not onnx_model_path.is_file():
            raise CampaignCarriageError(
                f"hindsight ONNX model is not a file: {onnx_model_path}"
            )
        if _sha256_file(onnx_model_path) != onnx_model_sha256:
            raise CampaignCarriageError("hindsight ONNX model content drifted")
        if _sha256_file_tree(onnx_tokenizer_path) != onnx_tokenizer_tree_sha256:
            raise CampaignCarriageError("hindsight ONNX tokenizer content drifted")
        retain_max_completion_tokens = _require_positive_int(
            raw["retain_max_completion_tokens"],
            label="hindsight_lifecycle.retain_max_completion_tokens",
        )
        if retain_max_completion_tokens != HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS:
            raise CampaignCarriageError(
                "hindsight_lifecycle.retain_max_completion_tokens must match "
                "the repository-owned qualification bound"
            )
        fail_on_extraction_errors = raw["fail_on_extraction_errors"]
        if not isinstance(fail_on_extraction_errors, bool):
            raise CampaignCarriageError(
                "hindsight_lifecycle.fail_on_extraction_errors must be a boolean"
            )
        if fail_on_extraction_errors is not HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS:
            raise CampaignCarriageError(
                "hindsight_lifecycle.fail_on_extraction_errors must match "
                "the repository-owned qualification reliability policy"
            )
        return cls(
            mode=mode,
            base_url=base_url,
            health_path=paths["health_path"],
            deployment_id=deployment_id,
            dependency_fingerprint=dependency,
            cleanup_path=paths["cleanup_path"],
            start_path=paths["start_path"],
            runtime_python=_require_absolute_path(
                raw["runtime_python"], label="hindsight_lifecycle.runtime_python"
            ),
            runtime_version=_require_nonempty_string(
                raw["runtime_version"], label="hindsight_lifecycle.runtime_version"
            ),
            source_revision=_require_sha(
                raw["source_revision"],
                label="hindsight_lifecycle.source_revision",
                pattern=_SHA1_RE,
            ),
            source_tree=_require_sha(
                raw["source_tree"],
                label="hindsight_lifecycle.source_tree",
                pattern=_SHA1_RE,
            ),
            database_profile=_require_nonempty_string(
                raw["database_profile"], label="hindsight_lifecycle.database_profile"
            ),
            llm_model=_require_nonempty_string(
                raw["llm_model"], label="hindsight_lifecycle.llm_model"
            ),
            llm_base_url=_require_nonempty_string(
                raw["llm_base_url"], label="hindsight_lifecycle.llm_base_url"
            ),
            retain_max_completion_tokens=retain_max_completion_tokens,
            fail_on_extraction_errors=fail_on_extraction_errors,
            embeddings_provider=_require_nonempty_string(
                raw["embeddings_provider"],
                label="hindsight_lifecycle.embeddings_provider",
            ),
            reranker_provider=_require_nonempty_string(
                raw["reranker_provider"],
                label="hindsight_lifecycle.reranker_provider",
            ),
            package_wheel_sha256=_require_package_hashes(
                raw["package_wheel_sha256"]
            ),
            embeddings_onnx_model_path=onnx_model_path,
            embeddings_onnx_model_sha256=onnx_model_sha256,
            embeddings_onnx_tokenizer_path=onnx_tokenizer_path,
            embeddings_onnx_tokenizer_tree_sha256=onnx_tokenizer_tree_sha256,
            port=port,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "base_url": self.base_url,
            "health_path": self.health_path,
            "deployment_id": self.deployment_id,
            "dependency_fingerprint": self.dependency_fingerprint,
            "cleanup_path": self.cleanup_path,
            "start_path": self.start_path,
            "runtime_python": str(self.runtime_python),
            "runtime_version": self.runtime_version,
            "source_revision": self.source_revision,
            "source_tree": self.source_tree,
            "database_profile": self.database_profile,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "retain_max_completion_tokens": self.retain_max_completion_tokens,
            "fail_on_extraction_errors": self.fail_on_extraction_errors,
            "embeddings_provider": self.embeddings_provider,
            "reranker_provider": self.reranker_provider,
            "embeddings_onnx_model_path": str(self.embeddings_onnx_model_path),
            "embeddings_onnx_model_sha256": self.embeddings_onnx_model_sha256,
            "embeddings_onnx_tokenizer_path": str(self.embeddings_onnx_tokenizer_path),
            "embeddings_onnx_tokenizer_tree_sha256": self.embeddings_onnx_tokenizer_tree_sha256,
            "package_wheel_sha256": dict(self.package_wheel_sha256),
            "port": self.port,
        }


@dataclass(frozen=True, slots=True)
class RelayLMExactRCSpec:
    """Exact accepted RC wheel identity; source checkout code is never rebuilt."""

    wheel_path: Path
    wheel_sha256: str
    version: str
    source_revision: str
    source_tree: str
    distribution: str
    config_path: Path
    config_sha256: str
    port: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RelayLMExactRCSpec":
        _require_exact_keys(raw, _RC_KEYS, label="relaylm_exact_rc")
        port = _require_positive_int(raw["port"], label="RC port")
        if port > 65535:
            raise CampaignCarriageError("RC port must be <= 65535")
        wheel_path = _require_absolute_path(raw["wheel_path"], label="wheel_path")
        wheel_sha256 = _require_sha(
            raw["wheel_sha256"], label="wheel_sha256", pattern=_SHA256_RE
        )
        if not wheel_path.is_file():
            raise CampaignCarriageError(f"exact RC wheel is not a file: {wheel_path}")
        if _sha256_file(wheel_path) != wheel_sha256:
            raise CampaignCarriageError("exact RC wheel content drifted")
        config_path = _require_absolute_path(raw["config_path"], label="RC config_path")
        config_sha256 = _require_sha(
            raw["config_sha256"], label="RC config_sha256", pattern=_SHA256_RE
        )
        if not config_path.is_file():
            raise CampaignCarriageError(f"exact RC config is not a file: {config_path}")
        if _sha256_file(config_path) != config_sha256:
            raise CampaignCarriageError("exact RC config content drifted")
        return cls(
            wheel_path=wheel_path,
            wheel_sha256=wheel_sha256,
            version=_require_nonempty_string(raw["version"], label="RC version"),
            source_revision=_require_sha(
                raw["source_revision"], label="RC source_revision", pattern=_SHA1_RE
            ),
            source_tree=_require_sha(
                raw["source_tree"], label="RC source_tree", pattern=_SHA1_RE
            ),
            distribution=_require_nonempty_string(
                raw["distribution"], label="RC distribution"
            ),
            config_path=config_path,
            config_sha256=config_sha256,
            port=port,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "wheel_path": str(self.wheel_path),
            "wheel_sha256": self.wheel_sha256,
            "version": self.version,
            "source_revision": self.source_revision,
            "source_tree": self.source_tree,
            "distribution": self.distribution,
            "config_path": str(self.config_path),
            "config_sha256": self.config_sha256,
            "port": self.port,
        }


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


class HindsightDeploymentSession:
    """Repository-owned lifecycle client for the exact Hindsight deployment.

    The target never accepts a shell command or import string from the plan.
    It talks to fixed lifecycle paths, verifies the complete zero-semantic
    health attestation, and cleans up the same deployment in all controller
    failure paths.
    """

    _HEALTH_READY_TIMEOUT_SECONDS = 180.0
    _HEALTH_POLL_SECONDS = 0.25

    def __init__(
        self,
        spec: HindsightLifecycleSpec,
        expected: HindsightHealthAttestation,
        *,
        repo_root: Path | None = None,
        evidence_root: Path | None = None,
    ) -> None:
        self.spec = spec
        self.expected = expected
        self.repo_root = repo_root
        self.evidence_root = evidence_root
        self.client = httpx.Client(
            timeout=HINDSIGHT_HTTP_TIMEOUT_SECONDS,
            trust_env=False,
        )
        self.process: subprocess.Popen[bytes] | None = None
        self.started = False
        self.start_count = 0
        self.health_count = 0
        self.semantic_operation_count = 0
        self.consolidation_wait_count = 0
        self.cleanup_count = 0
        self._last_health_response: Mapping[str, Any] | None = None
        self._runtime_identity_path: Path | None = None
        self._cleanup_receipt: Mapping[str, Any] | None = None

    def _url(self, path: str) -> str:
        return f"{self.spec.base_url}{path}"

    def start(self) -> None:
        if self.started:
            raise CampaignCarriageError("Hindsight lifecycle was started twice")
        if self.spec.mode == "owned_local":
            if self.repo_root is None or self.evidence_root is None:
                raise CampaignCarriageError(
                    "owned_local Hindsight requires repository and evidence roots"
                )
            if not self.spec.runtime_python.is_file():
                raise CampaignCarriageError(
                    f"Hindsight runtime interpreter is not a file: {self.spec.runtime_python}"
                )
            self.evidence_root.mkdir(parents=True, exist_ok=True)
            self._runtime_identity_path = self.evidence_root / "runtime-identity.json"
            if self._runtime_identity_path.exists():
                raise CampaignCarriageError("Hindsight runtime evidence root is not fresh")
            log_path = self.evidence_root / "hindsight-runtime.log"
            command = [
                str(self.spec.runtime_python),
                "-m",
                "tools.v1_external_qualification_hindsight_runtime",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.spec.port),
                "--database-profile",
                self.spec.database_profile,
                "--deployment-id",
                self.spec.deployment_id,
                "--dependency-fingerprint",
                self.spec.dependency_fingerprint,
                "--source-revision",
                self.spec.source_revision,
                "--source-tree",
                self.spec.source_tree,
                "--llm-model",
                self.spec.llm_model,
                "--llm-base-url",
                self.spec.llm_base_url,
                "--retain-max-completion-tokens",
                str(self.spec.retain_max_completion_tokens),
                "--fail-on-extraction-errors",
                str(self.spec.fail_on_extraction_errors).lower(),
                "--embeddings-provider",
                self.spec.embeddings_provider,
                "--reranker-provider",
                self.spec.reranker_provider,
                "--onnx-model-path",
                str(self.spec.embeddings_onnx_model_path),
                "--onnx-tokenizer-path",
                str(self.spec.embeddings_onnx_tokenizer_path),
                "--identity-path",
                str(self._runtime_identity_path),
            ]
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(self.repo_root)
            environment["PYTHONNOUSERSITE"] = "1"
            environment["HINDSIGHT_API_SKIP_LLM_VERIFICATION"] = "true"
            environment["HINDSIGHT_API_LLM_STRICT_SCHEMA_RETAIN"] = "true"
            environment["HINDSIGHT_API_LLM_STRICT_SCHEMA_CONSOLIDATION"] = "true"
            environment["HINDSIGHT_API_EMBEDDINGS_PROVIDER"] = (
                self.spec.embeddings_provider
            )
            environment["HINDSIGHT_API_RERANKER_PROVIDER"] = self.spec.reranker_provider
            environment["HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH"] = str(
                self.spec.embeddings_onnx_model_path
            )
            environment["HINDSIGHT_API_EMBEDDINGS_ONNX_TOKENIZER_NAME_OR_PATH"] = str(
                self.spec.embeddings_onnx_tokenizer_path
            )
            try:
                log_handle = log_path.open("ab")
                self.process = subprocess.Popen(
                    command,
                    cwd=self.repo_root,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                )
            except OSError as exc:
                try:
                    log_handle.close()
                except UnboundLocalError:
                    pass
                raise CampaignCarriageError("owned Hindsight launch failed") from exc
            log_handle.close()
        elif self.spec.mode == "owned_http":
            try:
                response = self.client.post(
                    self._url(self.spec.start_path),
                    json={
                        "deployment_id": self.spec.deployment_id,
                        "dependency_fingerprint": self.spec.dependency_fingerprint,
                    },
                )
            except httpx.HTTPError as exc:
                raise CampaignCarriageError("Hindsight lifecycle start failed") from exc
            if response.status_code not in {200, 201, 204}:
                raise CampaignCarriageError(
                    f"Hindsight lifecycle start returned HTTP {response.status_code}"
                )
        self.started = True
        self.start_count += 1

    def attest_zero_semantic_health(self) -> Mapping[str, Any]:
        if not self.started:
            raise CampaignCarriageError("Hindsight health was requested before start")
        deadline = time.monotonic() + self._HEALTH_READY_TIMEOUT_SECONDS
        while True:
            try:
                raw, version = self._attest_zero_semantic_health_once()
                break
            except _HindsightReadinessPending as exc:
                if time.monotonic() >= deadline:
                    detail = f": {exc}" if str(exc) else ""
                    raise CampaignCarriageError(
                        f"Hindsight health did not become ready within "
                        f"{self._HEALTH_READY_TIMEOUT_SECONDS:.0f}s{detail}"
                    ) from exc
                time.sleep(self._HEALTH_POLL_SECONDS)
            except CampaignCarriageError:
                raise
        self._last_health_response = {"health": dict(raw), "version": dict(version)}
        self.health_count += 1
        return self.expected.value

    def _attest_zero_semantic_health_once(
        self,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        """Probe readiness once; only startup-transient states are retryable."""

        if self.process is not None and self.process.poll() is not None:
            raise CampaignCarriageError("owned Hindsight exited before health")
        try:
            response = self.client.get(self._url(self.spec.health_path))
        except httpx.HTTPError as exc:
            raise _HindsightReadinessPending("Hindsight health request failed") from exc
        if response.status_code != 200:
            raise _HindsightReadinessPending(
                f"Hindsight health returned HTTP {response.status_code}"
            )
        try:
            raw = _require_mapping(response.json(), label="Hindsight health response")
        except (ValueError, TypeError) as exc:
            raise _HindsightReadinessPending(
                "Hindsight health response was not JSON"
            ) from exc
        if raw.get("status") != "healthy":
            raise _HindsightReadinessPending("Hindsight readiness response is not healthy")
        try:
            version_response = self.client.get(self._url("/version"))
        except httpx.HTTPError as exc:
            raise _HindsightReadinessPending("Hindsight version request failed") from exc
        if version_response.status_code != 200:
            raise _HindsightReadinessPending(
                f"Hindsight version returned HTTP {version_response.status_code}"
            )
        try:
            version = _require_mapping(
                version_response.json(), label="Hindsight version response"
            )
        except (ValueError, TypeError) as exc:
            raise _HindsightReadinessPending(
                "Hindsight version response was not JSON"
            ) from exc
        if version.get("api_version") != self.spec.runtime_version.lstrip("v"):
            raise CampaignCarriageError("Hindsight API version drifted from the frozen plan")
        if self.spec.mode == "owned_local":
            if self._runtime_identity_path is None or not self._runtime_identity_path.is_file():
                raise _HindsightReadinessPending(
                    "owned Hindsight runtime identity is not emitted yet"
                )
            try:
                runtime_identity = _require_mapping(
                    json.loads(self._runtime_identity_path.read_text(encoding="utf-8")),
                    label="Hindsight runtime identity",
                )
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
                raise CampaignCarriageError(
                    "owned Hindsight runtime identity is invalid"
                ) from exc
            if runtime_identity.get("version") != self.spec.runtime_version.lstrip("v"):
                raise CampaignCarriageError("owned Hindsight runtime version drifted")
            for name, expected in (
                ("implementation", "hindsight"),
                ("deployment_id", self.spec.deployment_id),
                ("dependency_fingerprint", self.spec.dependency_fingerprint),
                ("source_revision", self.spec.source_revision),
                ("source_tree", self.spec.source_tree),
                ("llm_model", self.spec.llm_model),
                ("llm_base_url", self.spec.llm_base_url),
                ("retain_max_completion_tokens", self.spec.retain_max_completion_tokens),
                ("fail_on_extraction_errors", self.spec.fail_on_extraction_errors),
                ("embeddings_provider", self.spec.embeddings_provider),
                ("reranker_provider", self.spec.reranker_provider),
            ):
                if runtime_identity.get(name) != expected:
                    raise CampaignCarriageError(f"owned Hindsight runtime {name} drifted")
            if runtime_identity.get("database_profile") != self.spec.database_profile:
                raise CampaignCarriageError("owned Hindsight database profile drifted")
            if runtime_identity.get("embeddings_onnx_model_path") != str(
                self.spec.embeddings_onnx_model_path
            ):
                raise CampaignCarriageError("owned Hindsight ONNX model path drifted")
            if runtime_identity.get("embeddings_onnx_model_sha256") != (
                self.spec.embeddings_onnx_model_sha256
            ):
                raise CampaignCarriageError("owned Hindsight ONNX model identity drifted")
            if runtime_identity.get("embeddings_onnx_tokenizer_path") != str(
                self.spec.embeddings_onnx_tokenizer_path
            ):
                raise CampaignCarriageError("owned Hindsight tokenizer path drifted")
            if runtime_identity.get("embeddings_onnx_tokenizer_tree_sha256") != (
                self.spec.embeddings_onnx_tokenizer_tree_sha256
            ):
                raise CampaignCarriageError("owned Hindsight tokenizer identity drifted")
            if runtime_identity.get("package_wheel_sha256") != dict(
                self.spec.package_wheel_sha256
            ):
                raise CampaignCarriageError("owned Hindsight package wheel identity drifted")
        return raw, version

    def cleanup(self) -> Mapping[str, Any]:
        if self._cleanup_receipt is not None:
            return self._cleanup_receipt
        errors: list[str] = []
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    errors.append("owned Hindsight process did not terminate")
        if self.started and self.process is None and self.spec.mode == "owned_http":
            try:
                response = self.client.post(
                    self._url(self.spec.cleanup_path),
                    json={"deployment_id": self.spec.deployment_id},
                )
                if response.status_code not in {200, 202, 204}:
                    errors.append(
                        f"Hindsight cleanup returned HTTP {response.status_code}"
                    )
            except httpx.HTTPError as exc:
                errors.append(f"Hindsight cleanup failed: {exc}")
        self.cleanup_count += 1
        try:
            self.client.close()
        except Exception as exc:
            errors.append(f"Hindsight HTTP client close failed: {exc}")
        self._cleanup_receipt = {
            "started": self.started,
            "start_count": self.start_count,
            "health_count": self.health_count,
            "semantic_operation_count": self.semantic_operation_count,
            "cleanup_count": self.cleanup_count,
            "deployment_id": self.spec.deployment_id,
            "all_owned_processes_terminated": not errors,
            "external_processes_touched": 0,
            "errors": errors,
            "live_health_response": self._last_health_response,
            "runtime_identity_path": (
                None
                if self._runtime_identity_path is None
                else str(self._runtime_identity_path)
            ),
        }
        return self._cleanup_receipt

    def _semantic_post(
        self,
        *,
        operation: str,
        path: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, Any]:
        if not self.started:
            raise CampaignCarriageError("Hindsight semantic execution was requested before start")
        try:
            response = self.client.post(self._url(path), json=dict(payload))
        except httpx.HTTPError as exc:
            raise CampaignCarriageError("Hindsight semantic request failed") from exc
        if response.status_code != 200:
            headers = getattr(response, "headers", {})
            allow = headers.get("allow") if hasattr(headers, "get") else None
            body = getattr(response, "text", "")
            if not isinstance(body, str):
                body = str(body)
            raise HindsightSemanticRequestError(
                operation=operation,
                method="POST",
                path=path,
                status_code=response.status_code,
                allow=allow,
                body=body,
            )
        try:
            value = _require_mapping(response.json(), label="Hindsight semantic response")
        except (ValueError, TypeError) as exc:
            raise CampaignCarriageError("Hindsight semantic response was not JSON") from exc
        self.semantic_operation_count += 1
        return value

    def _semantic_get(self, *, operation: str, path: str) -> Mapping[str, Any]:
        if not self.started:
            raise CampaignCarriageError("Hindsight semantic execution was requested before start")
        try:
            response = self.client.get(self._url(path))
        except httpx.HTTPError as exc:
            raise CampaignCarriageError("Hindsight semantic request failed") from exc
        if response.status_code != 200:
            headers = getattr(response, "headers", {})
            allow = headers.get("allow") if hasattr(headers, "get") else None
            body = getattr(response, "text", "")
            if not isinstance(body, str):
                body = str(body)
            raise HindsightSemanticRequestError(
                operation=operation,
                method="GET",
                path=path,
                status_code=response.status_code,
                allow=allow,
                body=body,
            )
        try:
            value = _require_mapping(response.json(), label="Hindsight semantic response")
        except (ValueError, TypeError) as exc:
            raise CampaignCarriageError("Hindsight semantic response was not JSON") from exc
        return value

    def retain(
        self,
        *,
        bank_id: str,
        items: Sequence[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        if _BANK_ID_RE.fullmatch(bank_id) is None:
            raise CampaignCarriageError("Hindsight bank id is invalid")
        return self._semantic_post(
            operation="retain",
            path=f"/v1/default/banks/{bank_id}/memories",
            payload={"items": [dict(item) for item in items], "async": False},
        )

    def recall(
        self,
        prompt: str,
        *,
        bank_id: str,
        query_timestamp: str | None = None,
    ) -> Mapping[str, Any]:
        if _BANK_ID_RE.fullmatch(bank_id) is None:
            raise CampaignCarriageError("Hindsight bank id is invalid")
        payload: dict[str, object] = {
            "query": prompt,
            "types": list(HINDSIGHT_RECALL_TYPES),
            "prefer_observations": HINDSIGHT_PREFER_OBSERVATIONS,
            "max_tokens": HINDSIGHT_RECALL_MAX_TOKENS,
            "budget": HINDSIGHT_RECALL_BUDGET,
        }
        if query_timestamp is not None:
            payload["query_timestamp"] = query_timestamp
        return self._semantic_post(
            operation="recall",
            path=f"/v1/default/banks/{bank_id}/memories/recall",
            payload=payload,
        )

    def consolidation_pending_ids(
        self,
        *,
        bank_id: str,
        allow_missing_bank: bool = False,
    ) -> set[str]:
        """Snapshot pending/processing ids before a new retain.

        Hindsight creates a bank on the first retain, while read-only
        operation listing returns 404 for a bank that has never been used.
        Only a caller that has independently proved a fresh empty preload
        journal may treat that first-use 404 as an empty snapshot. Resume
        callers keep the default fail-closed behavior.
        """

        if _BANK_ID_RE.fullmatch(bank_id) is None:
            raise CampaignCarriageError("Hindsight bank id is invalid")
        try:
            payload = self._semantic_get(
                operation="consolidation_snapshot",
                path=(
                    f"/v1/default/banks/{bank_id}/operations"
                    "?type=consolidation&limit=100&exclude_parents=true"
                ),
            )
        except HindsightSemanticRequestError as exc:
            if allow_missing_bank and exc.status_code == 404:
                return set()
            raise
        operations = payload.get("operations")
        if operations is None:
            return set()
        if not isinstance(operations, list) or not all(
            isinstance(item, Mapping) for item in operations
        ):
            raise CampaignCarriageError("Hindsight consolidation operations response is invalid")
        return {
            str(item["id"])
            for item in operations
            if isinstance(item.get("id"), str)
            and item.get("status") in {"pending", "processing"}
        }

    def wait_for_consolidation(
        self,
        *,
        bank_id: str,
        pre_existing_pending_ids: set[str],
    ) -> Mapping[str, object]:
        """Wait until new consolidation work is terminal and visible."""

        started = time.monotonic()
        deadline = started + HINDSIGHT_CONSOLIDATION_WAIT_TIMEOUT_SECONDS
        poll_count = 0
        self.consolidation_wait_count += 1
        while True:
            poll_count += 1
            payload = self._semantic_get(
                operation="consolidation_wait",
                path=(
                    f"/v1/default/banks/{bank_id}/operations"
                    "?type=consolidation&limit=100&exclude_parents=true"
                ),
            )
            operations = payload.get("operations")
            if not isinstance(operations, list) or not all(
                isinstance(item, Mapping) for item in operations
            ):
                raise CampaignCarriageError(
                    "Hindsight consolidation operations response is invalid"
                )
            new_operations = [
                item
                for item in operations
                if item.get("id") not in pre_existing_pending_ids
            ]
            active = [
                item
                for item in new_operations
                if item.get("status") in {"pending", "processing"}
            ]
            failed = [
                item
                for item in new_operations
                if item.get("status") in {"failed", "cancelled"}
            ]
            if failed:
                raise CampaignCarriageError(
                    "Hindsight consolidation failed or was cancelled for retained history"
                )
            if not active:
                return {
                    "poll_count": poll_count,
                    "elapsed_ms": (time.monotonic() - started) * 1000.0,
                    "pre_existing_pending_count": len(pre_existing_pending_ids),
                    "outstanding_count": 0,
                }
            if time.monotonic() >= deadline:
                raise CampaignCarriageError(
                    "Hindsight consolidation drain timed out before recall visibility"
                )
            time.sleep(HINDSIGHT_CONSOLIDATION_POLL_SECONDS)

    def reflect(
        self,
        prompt: str,
        *,
        context: Mapping[str, Any],
        bank_id: str,
    ) -> Mapping[str, Any]:
        if _BANK_ID_RE.fullmatch(bank_id) is None:
            raise CampaignCarriageError("Hindsight bank id is invalid")
        return self._semantic_post(
            operation="reflect",
            path=f"/v1/default/banks/{bank_id}/reflect",
            payload={
                "query": prompt,
                "context": _canonical_json(context),
                "budget": "low",
            },
        )


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
        expected_build_info = _require_nonempty_string(
            raw["expected_build_info"], label="llama_cpp.expected_build_info"
        )
        try:
            parsed_build = parse_props_build_info(expected_build_info)
        except LlamaCppIdentityError as exc:
            raise CampaignCarriageError(str(exc)) from exc
        upstream_revision = _require_sha(
            raw["upstream_revision"], label="llama_cpp.upstream_revision", pattern=_SHA1_RE
        )
        if parsed_build.commit != upstream_revision[: len(parsed_build.commit)].lower():
            raise CampaignCarriageError(
                "llama_cpp.expected_build_info commit does not match upstream_revision"
            )
        return cls(
            llama_cpp_root=_require_absolute_path(raw["llama_cpp_root"], label="llama_cpp_root"),
            artifact_path=_require_absolute_path(raw["artifact_path"], label="artifact_path"),
            upstream_revision=upstream_revision,
            expected_build_info=expected_build_info,
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


def _fingerprint(value: object) -> str:
    return f"sha256:{_sha256_json(value)}"


def _hindsight_owner_deployment_id(owner_id: str) -> str:
    """Derive the only production Hindsight deployment id allowed for one owner."""

    normalized = _require_owner_id(owner_id)
    owner_token = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"hindsight-v0.10.0-pg0-owner-{owner_token}"


def _hindsight_axis_bank_id(database_profile: str, axis_id: str) -> str:
    """Derive an opaque bank isolated by owner profile and campaign axis."""

    profile = _require_nonempty_string(database_profile, label="Hindsight database profile")
    axis = _require_nonempty_string(axis_id, label="Hindsight axis id")
    token = hashlib.sha256(f"{profile}\0{axis}".encode("utf-8")).hexdigest()[:24]
    bank_id = f"relaylm-{token}"
    if _BANK_ID_RE.fullmatch(bank_id) is None:
        raise CampaignCarriageError("derived Hindsight bank id is invalid")
    return bank_id


def _hindsight_operational_fingerprint(
    owner_id: str,
    lifecycle: HindsightLifecycleSpec,
) -> str:
    """Bind every qualification-significant Hindsight lifecycle fact to its owner."""

    return _fingerprint(
        {
            "owner_id": _require_owner_id(owner_id),
            "hindsight_lifecycle": lifecycle.to_mapping(),
        }
    )


def _campaign_contract(axis: "CampaignAxis") -> dict[str, str]:
    """Derive the exact resume linkage from repository-owned normalized inputs."""

    comparator = next(
        item["identity"]
        for item in axis.manifest["participants"]
        if item["slot"] == "serious_comparator"
    )
    return {
        "case_fingerprint": _fingerprint(axis.case),
        "manifest_fingerprint": _fingerprint(axis.manifest),
        "benchmark_material_fingerprint": _fingerprint(axis.benchmark_material),
        "history_material_fingerprint": _fingerprint(axis.history_material),
        "comparator_fingerprint": _fingerprint(comparator),
        "question_list_fingerprint": _fingerprint(
            [
                {
                    "question_id": question.question_id,
                    "prompt": question.prompt,
                    "content_fingerprint": question.content_fingerprint,
                    "session_id": question.session_id,
                }
                for question in axis.questions
            ]
        ),
        "qualification_authority_fingerprint": _fingerprint(
            axis.identity["authority"]
        ),
        "relaylm_release_fingerprint": _fingerprint(
            axis.manifest["relaylm_release"]
        ),
        "harness_revision": axis.manifest["harness"]["revision"],
        "adapter_revision": axis.manifest["adapter"]["revision"],
        "model_condition_fingerprint": _fingerprint(
            {
                "participants": axis.manifest["participants"],
                "identity_model": axis.identity["model"],
                "identity_decoding": axis.identity["decoding"],
                "identity_reasoning": axis.identity["reasoning"],
                "identity_context_capacity": axis.identity["context_capacity"],
            }
        ),
    }


def _embedded_sha(value: object, *, label: str) -> str:
    text = _require_nonempty_string(value, label=label)
    matches = re.findall(r"sha256[=:]([0-9a-f]{64})(?:$|[^0-9a-f])", text)
    if len(matches) != 1:
        raise CampaignCarriageError(f"{label} must carry an embedded sha256")
    return matches[0]


def _check_live_manifest_identity(
    *,
    axis: CampaignAxis,
    live_attestation: LiveLaunchAdmissionAttestation,
    spec: LlamaCppLaunchSpec,
) -> None:
    live_payload = live_attestation.payload
    runtime_identity = live_payload.get("runtime_identity")
    if not isinstance(runtime_identity, Mapping):
        if spec is not None and axis.classification is not None:
            raise CampaignCarriageError(
                "production campaign requires extended live runtime identity"
            )
        return
    plans = {
        str(plan["slot"]): plan for plan in axis.manifest["participants"]
    }
    for slot in ("same_model_direct", "relaylm_exact_rc"):
        identity = plans[slot]["identity"]
        if not isinstance(identity, Mapping):
            raise CampaignCarriageError(f"{axis.axis_id}.{slot} is not enabled")
        if identity["backend"] != live_payload["backend"]:
            raise CampaignCarriageError(f"{axis.axis_id}.{slot} backend drifted from live runtime")
        if identity["runtime"] != live_payload["runtime"]:
            raise CampaignCarriageError(f"{axis.axis_id}.{slot} runtime drifted from live runtime")
        if identity["context_capacity"] != live_payload["admitted_context"]:
            raise CampaignCarriageError(
                f"{axis.axis_id}.{slot} context_capacity drifted from live runtime"
            )
        physical = _require_mapping(
            identity["physical_model"], label=f"{axis.axis_id}.{slot}.physical_model"
        )
        if _embedded_sha(physical["artifact"], label=f"{axis.axis_id}.{slot}.artifact") != runtime_identity["artifact_sha256"]:
            raise CampaignCarriageError(
                f"{axis.axis_id}.{slot} model artifact differs from live llama.cpp"
            )
        template = axis.identity["template"]
        if isinstance(template, str) and re.search(r"sha256[=:]", template):
            if _embedded_sha(template, label=f"{axis.axis_id}.{slot}.template") != runtime_identity["chat_template_sha256"]:
                raise CampaignCarriageError(
                    f"{axis.axis_id}.{slot} chat template differs from live llama.cpp"
                )


@dataclass(frozen=True, slots=True)
class CampaignAxis:
    axis_id: str
    case: Mapping[str, Any]
    manifest: Mapping[str, Any]
    identity: Mapping[str, Any]
    questions: tuple[CampaignQuestion, ...]
    run_mode: Literal["fresh_run", "exact_infrastructure_resume"]
    classification: str | None = None
    benchmark_material: Mapping[str, Any] | None = None
    history_material: Mapping[str, str] | None = None
    history_plan: HindsightHistoryPlan | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CampaignAxis:
        if set(raw) == _AXIS_KEYS:
            classification = None
            benchmark_material = None
            history_material = None
        elif set(raw) == _PRODUCTION_AXIS_KEYS:
            classification = _require_nonempty_string(
                raw["classification"], label="classification"
            )
            if classification not in CLASSIFICATIONS:
                raise CampaignCarriageError(
                    f"unsupported result classification: {classification}"
                )
            benchmark_material = _require_material(
                raw["benchmark_material"], label=f"axis {raw.get('axis_id', 'unknown')} material"
            )
            history_material = _require_history_material(
                raw["history_material"],
                label=f"axis {raw.get('axis_id', 'unknown')} history material",
            )
        else:
            _require_exact_keys(raw, _PRODUCTION_AXIS_KEYS, label="campaign axis")
            raise AssertionError("unreachable")
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
        history_plan = (
            None
            if history_material is None
            else HindsightHistoryPlan.from_path(Path(history_material["path"]))
        )
        if history_plan is not None:
            history_plan.validate_questions(ids)
        run_mode = raw["run_mode"]
        if run_mode not in _RUN_MODES:
            raise CampaignCarriageError(
                f"axis {axis_id!r} run_mode must be fresh_run or exact_infrastructure_resume"
            )
        if benchmark_material is not None:
            expected_question_fingerprints = [
                question.content_fingerprint for question in questions
            ]
            if benchmark_material["case_fingerprint"] != _fingerprint(case):
                raise CampaignCarriageError(
                    f"axis {axis_id!r} benchmark material case fingerprint drifted"
                )
            if benchmark_material["question_fingerprints"] != expected_question_fingerprints:
                raise CampaignCarriageError(
                    f"axis {axis_id!r} benchmark material question fingerprints drifted"
                )
        return cls(
            axis_id,
            case,
            manifest,
            identity,
            questions,
            cast(Any, run_mode),
            classification,
            benchmark_material,
            history_material,
            history_plan,
        )


@dataclass(frozen=True, slots=True)
class CampaignDescriptor:
    execution_freeze: Mapping[str, Any]
    artifact_root: Path
    llama_cpp: LlamaCppLaunchSpec
    hindsight_health: HindsightHealthAttestation
    axes: tuple[CampaignAxis, ...]
    owner_id: str
    spend_ledger_path: Path
    relaylm_exact_rc: RelayLMExactRCSpec | None = None
    hindsight_lifecycle: HindsightLifecycleSpec | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CampaignDescriptor:
        if set(raw) == _DESCRIPTOR_KEYS:
            legacy_descriptor = True
        elif set(raw) == _PRODUCTION_DESCRIPTOR_KEYS:
            legacy_descriptor = False
        else:
            _require_exact_keys(raw, _PRODUCTION_DESCRIPTOR_KEYS, label="campaign descriptor")
            raise AssertionError("unreachable")
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
            if axis.benchmark_material is not None and (
                _canonical_json(axis.benchmark_material)
                != _canonical_json(frozen_case.get("benchmark_material"))
            ):
                raise CampaignCarriageError(
                    f"axis {axis.axis_id!r} benchmark material drifted from execution freeze"
                )
            if axis.history_material is not None and (
                _canonical_json(axis.history_material)
                != _canonical_json(frozen_case.get("history_material"))
            ):
                raise CampaignCarriageError(
                    f"axis {axis.axis_id!r} history material drifted from execution freeze"
                )
        if set(frozen_case_by_id) != set(axis_ids):
            raise CampaignCarriageError("campaign axes must cover every frozen release case exactly")
        artifact_root = _require_absolute_path(raw["artifact_root"], label="artifact_root")
        owner_id = (
            _require_owner_id(raw["owner_id"])
            if not legacy_descriptor
            else f"legacy:{artifact_root}"
        )
        spend_ledger_path = (
            _require_absolute_path(raw["spend_ledger_path"], label="spend_ledger_path")
            if not legacy_descriptor
            else artifact_root / "scientific-spend.json"
        )
        relaylm_exact_rc = (
            RelayLMExactRCSpec.from_mapping(
                _require_mapping(raw["relaylm_exact_rc"], label="relaylm_exact_rc")
            )
            if not legacy_descriptor
            else None
        )
        hindsight_lifecycle = (
            HindsightLifecycleSpec.from_mapping(
                _require_mapping(raw["hindsight_lifecycle"], label="hindsight_lifecycle")
            )
            if not legacy_descriptor
            else None
        )
        llama_cpp = LlamaCppLaunchSpec.from_mapping(
            _require_mapping(raw["llama_cpp"], label="llama_cpp")
        )
        if not legacy_descriptor:
            assert relaylm_exact_rc is not None
            assert hindsight_lifecycle is not None
            if "gpu_identity" not in llama_cpp.capacity_evidence:
                raise CampaignCarriageError(
                    "production llama_cpp capacity_evidence requires stable gpu_identity"
                )
            if artifact_root in spend_ledger_path.parents:
                raise CampaignCarriageError(
                    "production scientific spend ledger must be outside artifact_root"
                )
            if hindsight_lifecycle.database_profile != owner_id:
                raise CampaignCarriageError(
                    "Hindsight database profile must equal scientific owner_id"
                )
            expected_deployment_id = _hindsight_owner_deployment_id(owner_id)
            if hindsight_lifecycle.deployment_id != expected_deployment_id:
                raise CampaignCarriageError(
                    "Hindsight deployment_id must be derived from scientific owner_id"
                )
            operational_fingerprint = _hindsight_operational_fingerprint(
                owner_id,
                hindsight_lifecycle,
            )
            health_deployment = _require_mapping(
                _require_mapping(raw["hindsight_health"], label="hindsight_health")["deployment"],
                label="hindsight_health.deployment",
            )
            if (
                health_deployment["deployment_id"] != hindsight_lifecycle.deployment_id
                or health_deployment["dependency_fingerprint"]
                != hindsight_lifecycle.dependency_fingerprint
                or _require_mapping(raw["hindsight_health"], label="hindsight_health")[
                    "source_revision"
                ]
                != hindsight_lifecycle.source_revision
                or _require_mapping(raw["hindsight_health"], label="hindsight_health")[
                    "version"
                ]
                != hindsight_lifecycle.runtime_version
            ):
                raise CampaignCarriageError(
                    "Hindsight lifecycle identity does not match health attestation"
                )
            for axis in axes:
                if axis.classification is None:
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} requires classification"
                    )
                comparator = next(
                    participant["identity"]
                    for participant in axis.manifest["participants"]
                    if participant["slot"] == "serious_comparator"
                )
                if not isinstance(comparator, Mapping) or (
                    comparator.get("implementation") != "hindsight"
                    or comparator.get("source_revision") != hindsight_lifecycle.source_revision
                    or comparator.get("version") != hindsight_lifecycle.runtime_version
                    or comparator.get("deployment") != operational_fingerprint
                ):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} serious comparator identity does not match admitted Hindsight operational identity"
                    )
                identity = FrozenExperimentIdentity.from_mapping(axis.identity)
                identity_mapping = identity.to_mapping()
                if "campaign_contract" not in identity_mapping:
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} requires campaign_contract"
                    )
                contract = _campaign_contract(axis)
                if _canonical_json(identity_mapping["campaign_contract"]) != _canonical_json(contract):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} campaign contract drifted"
                    )
                manifest_release = axis.manifest["relaylm_release"]
                if not isinstance(manifest_release, Mapping):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} has no exact RC release identity"
                    )
                if (
                    manifest_release["version"] != relaylm_exact_rc.version
                    or manifest_release["commit"] != relaylm_exact_rc.source_revision
                ):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} RC identity does not match descriptor"
                    )
                if identity_mapping["candidate"] != relaylm_exact_rc.source_revision:
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} frozen candidate does not match exact RC"
                    )
                artifacts = manifest_release.get("artifacts")
                if not isinstance(artifacts, list):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} release artifacts are invalid"
                    )
                wheel_artifacts = [
                    artifact
                    for artifact in artifacts
                    if isinstance(artifact, Mapping)
                    and artifact.get("filename") == relaylm_exact_rc.wheel_path.name
                ]
                if (
                    len(wheel_artifacts) != 1
                    or wheel_artifacts[0].get("sha256") != relaylm_exact_rc.wheel_sha256
                ):
                    raise CampaignCarriageError(
                        f"production axis {axis.axis_id!r} RC wheel identity does not match descriptor"
                    )
        return cls(
            execution_freeze=dict(execution_freeze),
            artifact_root=artifact_root,
            llama_cpp=llama_cpp,
            hindsight_health=HindsightHealthAttestation.from_mapping(
                _require_mapping(raw["hindsight_health"], label="hindsight_health")
            ),
            axes=axes,
            owner_id=owner_id,
            spend_ledger_path=spend_ledger_path,
            relaylm_exact_rc=relaylm_exact_rc,
            hindsight_lifecycle=hindsight_lifecycle,
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
        return f"sha256:{_sha256_json(
            {
                "format_version": CAMPAIGN_FORMAT_VERSION,
                "target": CAMPAIGN_TARGET,
                "execution_freeze": self.execution_freeze,
                "artifact_root": str(self.artifact_root),
                "owner_id": self.owner_id,
                "spend_ledger_path": str(self.spend_ledger_path),
                "relaylm_exact_rc": (
                    None if self.relaylm_exact_rc is None else self.relaylm_exact_rc.to_mapping()
                ),
                "hindsight_lifecycle": (
                    None
                    if self.hindsight_lifecycle is None
                    else self.hindsight_lifecycle.to_mapping()
                ),
                "llama_cpp": {
                    **self.llama_cpp.to_mapping(),
                    "capacity_evidence": _stable_capacity(
                        self.llama_cpp.capacity_evidence
                    ),
                },
                "hindsight_health": self.hindsight_health.value,
                "axes": [
                    {
                        "axis_id": axis.axis_id,
                        "case": axis.case,
                        "manifest": axis.manifest,
                        "identity": FrozenExperimentIdentity.from_mapping(
                            axis.identity
                        ).to_mapping(),
                        "questions": [
                            {
                                "question_id": question.question_id,
                                "prompt": question.prompt,
                                "content_fingerprint": question.content_fingerprint,
                                "session_id": question.session_id,
                                "content": question.prompt,
                            }
                            for question in axis.questions
                        ],
                        "classification": axis.classification,
                        "benchmark_material": axis.benchmark_material,
                        "history_material": axis.history_material,
                    }
                    for axis in self.axes
                ],
            }
        )}"


@dataclass(frozen=True, slots=True)
class ParticipantExecutionContext:
    """The only input made available to an A/C/D participant hook."""

    axis_id: str
    case: Mapping[str, Any]
    manifest: Mapping[str, Any]
    question: DurableQuestion
    prompt: str
    participant_slot: str
    participant_identity: Mapping[str, Any]
    frozen_identity: FrozenExperimentIdentity
    live_attestation: LiveLaunchAdmissionAttestation
    history: HindsightHistoryPlan | None = None
    durable_run: DurableQuestionRun | None = None


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
    for key in ("status", "branch", "repository_head", "repository_tree"):
        if key not in expected:
            raise CampaignCarriageError(
                "citable current authority must include exact status, branch, "
                "repository_head, and repository_tree"
            )
        if observed.get(key) != expected[key]:
            raise CampaignCarriageError(f"current authority drifted at {key}")


def _aggregate_observations(
    observations: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    if not observations:
        return None
    qualities: dict[str, list[float]] = {}
    input_tokens = output_tokens = model_calls = 0
    latency_values: dict[str, list[float]] = {
        "ttft_ms": [],
        "query_latency_ms": [],
        "end_to_end_ms": [],
    }
    resource_values: dict[str, list[int]] = {
        "peak_gpu_memory_bytes": [],
        "peak_cpu_memory_bytes": [],
        "persistent_storage_bytes": [],
    }
    notes: list[str] = []
    limitations: list[str] = []
    failures: list[str] = []
    for item in observations:
        observation = validate_observation(item)
        for name, value in observation["quality"].items():
            assert isinstance(value, (int, float))
            qualities.setdefault(name, []).append(float(value))
        tokens = observation["tokens"]
        assert isinstance(tokens, Mapping)
        input_tokens += int(tokens["model_input_tokens"] or 0)
        output_tokens += int(tokens["model_output_tokens"] or 0)
        model_calls += int(tokens["model_call_count"])
        latency = observation["latency"]
        assert isinstance(latency, Mapping)
        for name in latency_values:
            value = latency[name]
            if value is not None:
                latency_values[name].append(float(value))
        resources = observation["resources"]
        assert isinstance(resources, Mapping)
        for name in resource_values:
            value = resources[name]
            if value is not None:
                resource_values[name].append(int(value))
        notes.extend(str(value) for value in resources["notes"])
        limitations.extend(str(value) for value in observation["known_limitations"])
        if observation["failure"] is not None:
            failures.append(str(observation["failure"]))

    def average(values: list[float]) -> float | None:
        return None if not values else sum(values) / len(values)

    def maximum(values: list[int]) -> int | None:
        return None if not values else max(values)

    return {
        "quality": {
            name: sum(values) / len(values) for name, values in sorted(qualities.items())
        },
        "tokens": {
            "model_input_tokens": input_tokens,
            "model_output_tokens": output_tokens,
            "model_call_count": model_calls,
        },
        "latency": {
            name: average(values) for name, values in latency_values.items()
        },
        "resources": {
            name: maximum(values) for name, values in resource_values.items()
        }
        | {"notes": sorted(set(notes))},
        "known_limitations": sorted(set(limitations)),
        "failure": failures[0] if failures else None,
    }


_PARTICIPANT_COUNTER_NAMES = (
    "semantic_generation_count",
    "answer_model_generation_count",
    "judge_call_count",
)


def _participant_result_counters(
    result: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, int]:
    counters: dict[str, int] = {}
    for name in _PARTICIPANT_COUNTER_NAMES:
        value = result.get(name, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CampaignCarriageError(f"{label}.{name} is not a non-negative integer")
        counters[name] = value
    return counters


def _durable_participant_aggregate(
    *,
    axis: CampaignAxis,
    durable: DurableQuestionRun,
    question_id: str,
    strict_production: bool,
) -> list[Mapping[str, Any]]:
    participant_plans = {
        str(plan["slot"]): plan for plan in axis.manifest["participants"]
    }
    aggregate: list[Mapping[str, Any]] = []
    for slot in SLOTS:
        participant_plan = participant_plans[slot]
        participant_identity = participant_plan["identity"]
        if participant_identity is None:
            aggregate.append(
                {
                    "slot": slot,
                    "status": "omitted",
                    "observation": None,
                    "omission_reason": participant_plan["omission_reason"],
                }
            )
            continue
        completed = durable.participant_record(question_id=question_id, slot=slot)
        if completed is None:
            raise CampaignCarriageError(
                f"completed question {axis.axis_id}.{question_id} is missing durable {slot}"
            )
        stored_identity = _require_mapping(
            completed["participant_identity"],
            label=f"{axis.axis_id}.{slot} stored identity",
        )
        expected_identity = _require_mapping(
            participant_identity,
            label=f"{axis.axis_id}.{slot} identity",
        )
        if _canonical_json(stored_identity) != _canonical_json(expected_identity):
            raise CampaignCarriageError(
                f"durable {axis.axis_id}.{question_id}.{slot} identity drifted"
            )
        stored_result = _require_mapping(
            completed["result"], label=f"{axis.axis_id}.{slot} stored result"
        )
        if stored_result.get("slot") != slot:
            raise CampaignCarriageError(
                f"durable {axis.axis_id}.{question_id}.{slot} result slot drifted"
            )
        try:
            stored_counters = _participant_result_counters(
                stored_result,
                label=f"{axis.axis_id}.{slot} stored result",
            )
            observation = validate_participant_accounting(
                observation=_require_mapping(
                    stored_result["observation"],
                    label=f"{axis.axis_id}.{slot} stored observation",
                ),
                semantic_generation_count=stored_counters[
                    "semantic_generation_count"
                ],
                answer_model_generation_count=stored_counters[
                    "answer_model_generation_count"
                ],
                judge_call_count=stored_counters["judge_call_count"],
                allow_zero_model_operation=not strict_production,
            )
        except (ExternalQualificationError, TypeError, ValueError) as exc:
            raise CampaignCarriageError(
                f"durable {axis.axis_id}.{question_id}.{slot} result is invalid: {exc}"
            ) from exc
        aggregate.append(
            {"slot": slot, "status": "observed", "observation": observation}
        )
    return aggregate


def _write_axis_citable_evidence(
    *,
    descriptor: CampaignDescriptor,
    axis: CampaignAxis,
    frozen_identity: FrozenExperimentIdentity,
    live_attestation: LiveLaunchAdmissionAttestation,
    health: HindsightHealthAttestation,
    authority: Mapping[str, Any],
    question_results: Sequence[Mapping[str, Any]],
    counters: Mapping[str, int],
) -> Path:
    if axis.classification is None:
        raise CampaignCarriageError("citable axis is missing classification")
    by_slot: dict[str, list[Mapping[str, Any]]] = {slot: [] for slot in SLOTS}
    for question in question_results:
        participants = _require_mapping(question, label="question evidence").get("participants")
        if not isinstance(participants, list):
            raise CampaignCarriageError("question evidence participants must be a list")
        for participant in participants:
            item = _require_mapping(participant, label="question participant evidence")
            slot = item.get("slot")
            if not isinstance(slot, str) or slot not in SLOTS:
                raise CampaignCarriageError("question participant evidence slot is invalid")
            observation = item.get("observation")
            if observation is not None:
                by_slot[slot].append(
                    _require_mapping(observation, label="question participant observation")
                )
    results = []
    for plan in axis.manifest["participants"]:
        slot = plan["slot"]
        if plan["identity"] is None:
            results.append(
                {
                    "slot": slot,
                    "observation": None,
                    "omission_reason": plan["omission_reason"],
                }
            )
        else:
            aggregate = _aggregate_observations(by_slot[slot])
            if aggregate is None:
                raise CampaignCarriageError(
                    f"citable evidence has no result for enabled {axis.axis_id}.{slot}"
                )
            results.append(
                {"slot": slot, "observation": aggregate, "omission_reason": None}
            )
    runtime_identity = live_attestation.payload.get("runtime_identity")
    if not isinstance(runtime_identity, Mapping):
        raise CampaignCarriageError(
            "citable evidence requires the extended live runtime identity"
        )
    evidence = {
        "format_version": 1,
        "run_id": stable_run_id(manifest=axis.manifest, case=axis.case),
        "manifest": axis.manifest,
        "case": axis.case,
        "classification": axis.classification,
        "results": results,
    }
    campaign = {
        "campaign_fingerprint": descriptor.fingerprint,
        "frozen_experiment_fingerprint": frozen_identity.fingerprint,
        "qualification_authority": dict(authority),
        "hindsight_health_fingerprint": health.fingerprint,
        "live_runtime_identity": dict(runtime_identity),
        "live_launch_observation": live_attestation.payload.get("launch_observation"),
        "live_runtime_evidence_reference": live_attestation.payload.get(
            "launch_evidence_reference"
        ),
        "live_runtime_ownership_evidence_reference": live_attestation.payload.get(
            "runtime_ownership_evidence_reference"
        ),
        "question_results": list(question_results),
        "counters": {
            name: int(counters.get(name, 0))
            for name in (
                "semantic_generation_count",
                "benchmark_question_count",
                "answer_model_generation_count",
                "judge_call_count",
            )
        },
    }
    return write_citable_evidence(
        evidence=evidence,
        artifact_root=descriptor.artifact_root / "evidence",
        campaign=campaign,
    )


class CampaignController:
    """Run one typed campaign, or stop at its zero-semantic pre-call barrier."""

    def __init__(
        self,
        descriptor: CampaignDescriptor,
        *,
        live_launch_factory: LiveLaunchFactory,
        hindsight_probe: HindsightHealthProbe,
        participant_executors: ParticipantExecutors,
        current_authority_reader: CurrentAuthorityReader,
        hindsight_lifecycle: HindsightDeploymentSession | None = None,
        pre_call_rehearsal: bool = False,
    ) -> None:
        self.descriptor = descriptor
        self.live_launch_factory = live_launch_factory
        self.hindsight_probe = hindsight_probe
        self.participant_executors = participant_executors
        self.current_authority_reader = current_authority_reader
        self.hindsight_lifecycle = hindsight_lifecycle
        self.pre_call_rehearsal = pre_call_rehearsal

    async def run(self) -> Mapping[str, Any]:
        descriptor = self.descriptor
        root = descriptor.artifact_root
        root.mkdir(parents=True, exist_ok=True)

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
        strict_production = descriptor.relaylm_exact_rc is not None
        ledger = ScientificSpendLedger.open(
            path=descriptor.spend_ledger_path,
            owner_id=descriptor.owner_id,
            campaign_fingerprint=descriptor.fingerprint,
            mode=(
                "exact_infrastructure_resume"
                if any(axis.run_mode == "exact_infrastructure_resume" for axis in descriptor.axes)
                else "fresh_run"
            ),
        )
        barrier_reached = False
        health: HindsightHealthAttestation | None = None
        live_attestation: LiveLaunchAdmissionAttestation | None = None
        lifecycle_cleanup: Mapping[str, Any] | None = None
        try:
            if self.hindsight_lifecycle is not None:
                self.hindsight_lifecycle.start()
                health = verify_hindsight_health(
                    descriptor.hindsight_health,
                    self.hindsight_lifecycle,
                )
            else:
                health = verify_hindsight_health(
                    descriptor.hindsight_health,
                    self.hindsight_probe,
                )
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
                _check_live_manifest_identity(
                    axis=axis,
                    live_attestation=live_attestation,
                    spec=descriptor.llama_cpp,
                )
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
                axis_authority = dict(current_authority)
                question_results: list[Mapping[str, Any]] = []
                participant_plans = {
                    str(plan["slot"]): plan for plan in axis.manifest["participants"]
                }
                for completed_question in durable.rebuild_completed_results():
                    completed_value = _require_mapping(
                        completed_question["result"],
                        label=f"{axis.axis_id} completed question result",
                    )
                    participants = completed_value.get("participants")
                    if not isinstance(participants, list):
                        raise CampaignCarriageError(
                            f"{axis.axis_id} completed question participants must be a list"
                        )
                    if strict_production:
                        canonical_participants = _durable_participant_aggregate(
                            axis=axis,
                            durable=durable,
                            question_id=str(completed_question["question_id"]),
                            strict_production=True,
                        )
                        if _canonical_json(participants) != _canonical_json(
                            canonical_participants
                        ):
                            raise CampaignCarriageError(
                                f"{axis.axis_id}.{completed_question['question_id']} aggregate disagrees with durable participant records"
                            )
                        participants = canonical_participants
                        counters["benchmark_question_count"] += 1
                    question_results.append(
                        {
                            "question_id": completed_question["question_id"],
                            "session_id": completed_question["session_id"],
                            "participants": participants,
                        }
                    )
                    if strict_production:
                        for completed_participant in durable.rebuild_participant_results(
                            str(completed_question["question_id"])
                        ):
                            stored_result = _require_mapping(
                                completed_participant["result"],
                                label=f"{axis.axis_id} completed participant result",
                            )
                            stored_counters = _participant_result_counters(
                                stored_result,
                                label=f"{axis.axis_id} completed participant",
                            )
                            for name, value in stored_counters.items():
                                counters[name] += value
                if self.pre_call_rehearsal:
                    axis_receipts.append(
                        {
                            "axis_id": axis.axis_id,
                            "frozen_identity_fingerprint": frozen_identity.fingerprint,
                            "durable_root": str(axis_root),
                            "question_count": 0,
                            "status": "pre_call_ready",
                        }
                    )
                    continue
                axis_question_count = 0
                while True:
                    question = durable.next_question()
                    if question is None:
                        break
                    question = durable.begin_question(question.question_id)
                    participant_records: list[Mapping[str, Any]] = []
                    enabled_slots = tuple(
                        slot
                        for slot in SLOTS
                        if participant_plans[slot]["identity"] is not None
                    )
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
                        completed = durable.participant_record(
                            question_id=question.question_id,
                            slot=slot,
                        )
                        if completed is not None:
                            stored_identity = _require_mapping(
                                completed["participant_identity"],
                                label=f"{axis.axis_id}.{slot} stored identity",
                            )
                            if _canonical_json(stored_identity) != _canonical_json(
                                _require_mapping(
                                    participant_identity,
                                    label=f"{axis.axis_id}.{slot} identity",
                                )
                            ):
                                raise CampaignCarriageError(
                                    f"durable {axis.axis_id}.{question.question_id}.{slot} identity drifted"
                                )
                            stored_result = _require_mapping(
                                completed["result"],
                                label=f"{axis.axis_id}.{slot} stored result",
                            )
                            stored_slot = stored_result.get("slot")
                            if stored_slot != slot:
                                raise CampaignCarriageError(
                                    f"durable {axis.axis_id}.{question.question_id}.{slot} result slot drifted"
                                )
                            try:
                                stored_counters = _participant_result_counters(
                                    stored_result,
                                    label=f"{axis.axis_id}.{slot} stored result",
                                )
                                observation = validate_participant_accounting(
                                    observation=_require_mapping(
                                        stored_result["observation"],
                                        label=f"{axis.axis_id}.{slot} stored observation",
                                    ),
                                    semantic_generation_count=stored_counters[
                                        "semantic_generation_count"
                                    ],
                                    answer_model_generation_count=stored_counters[
                                        "answer_model_generation_count"
                                    ],
                                    judge_call_count=stored_counters["judge_call_count"],
                                    allow_zero_model_operation=not strict_production,
                                )
                            except (ExternalQualificationError, TypeError, ValueError) as exc:
                                raise CampaignCarriageError(
                                    f"durable {axis.axis_id}.{question.question_id}.{slot} result is invalid: {exc}"
                                ) from exc
                            if strict_production:
                                for name, value in stored_counters.items():
                                    counters[name] += value
                            participant_records.append(
                                {
                                    "slot": slot,
                                    "status": "observed",
                                    "observation": observation,
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
                            prompt=(
                                question.content
                                if isinstance(question.content, str)
                                else ""
                            ),
                            participant_slot=slot,
                            participant_identity=_require_mapping(
                                participant_identity,
                                label=f"{axis.axis_id}.{slot} identity",
                            ),
                            frozen_identity=frozen_identity,
                            live_attestation=live_attestation,
                            history=axis.history_plan,
                            durable_run=durable,
                        )
                        if strict_production and not barrier_reached:
                            ledger.record_pre_call_barrier(
                                payload={
                                    "campaign_fingerprint": descriptor.fingerprint,
                                    "axis_id": axis.axis_id,
                                    "question_id": question.question_id,
                                    "participant_slot": slot,
                                    "hindsight_health_fingerprint": health.fingerprint
                                    if health is not None
                                    else None,
                                    "llama_server_launch_count": session.launch_count
                                    if session is not None
                                    else 0,
                                    "semantic_generation_count": 0,
                                    "benchmark_question_count": 0,
                                    "answer_model_generation_count": 0,
                                    "judge_call_count": 0,
                                    "SCIENTIFIC_SPEND": "UNSPENT",
                                }
                            )
                            barrier_reached = True
                            ledger.consume_before_first_scientific_call()
                        result = await _await_result(executor(context))
                        if not isinstance(result, ParticipantExecutionResult):
                            raise CampaignCarriageError(
                                f"executor for {slot} must return ParticipantExecutionResult"
                            )
                        if result.slot != slot:
                            raise CampaignCarriageError(
                                f"executor returned slot {result.slot!r} for {slot!r}"
                            )
                        try:
                            observation = validate_participant_accounting(
                                observation=result.observation,
                                semantic_generation_count=result.semantic_generation_count,
                                answer_model_generation_count=result.answer_model_generation_count,
                                judge_call_count=result.judge_call_count,
                                allow_zero_model_operation=not strict_production,
                            )
                        except ExternalQualificationError as exc:
                            raise CampaignCarriageError(str(exc)) from exc
                        if not strict_production and any(
                            (
                                result.semantic_generation_count,
                                result.answer_model_generation_count,
                                result.judge_call_count,
                                observation["tokens"]["model_call_count"],
                            )
                        ):
                            if not barrier_reached:
                                ledger.record_pre_call_barrier(
                                    payload={
                                        "campaign_fingerprint": descriptor.fingerprint,
                                        "axis_id": axis.axis_id,
                                        "question_id": question.question_id,
                                        "participant_slot": slot,
                                        "hindsight_health_fingerprint": health.fingerprint
                                        if health is not None
                                        else None,
                                        "llama_server_launch_count": session.launch_count
                                        if session is not None
                                        else 0,
                                        "semantic_generation_count": 0,
                                        "benchmark_question_count": 0,
                                        "answer_model_generation_count": 0,
                                        "judge_call_count": 0,
                                        "SCIENTIFIC_SPEND": "UNSPENT",
                                    }
                                )
                                barrier_reached = True
                            ledger.consume_before_first_scientific_call()
                        durable_result = {
                            "slot": slot,
                            "observation": observation,
                            "semantic_generation_count": result.semantic_generation_count,
                            "answer_model_generation_count": result.answer_model_generation_count,
                            "judge_call_count": result.judge_call_count,
                        }
                        durable.commit_participant(
                            question_id=question.question_id,
                            slot=slot,
                            participant_identity=_require_mapping(
                                participant_identity,
                                label=f"{axis.axis_id}.{slot} identity",
                            ),
                            result=durable_result,
                            request_evidence=result.request_evidence,
                            enabled_slots=enabled_slots,
                        )
                        participant_records.append(
                            {
                                "slot": slot,
                                "status": "observed",
                                "observation": observation,
                            }
                        )
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
                        request_evidence=(),
                    )
                    question_results.append(
                        {
                            "question_id": question.question_id,
                            "session_id": question.session_id,
                            "participants": participant_records,
                        }
                    )
                    counters["benchmark_question_count"] += 1
                    axis_question_count += 1
                durable.mark_completed()
                counters["scientific_durable_run_completion_count"] += 1
                evidence_path: Path | None = None
                if strict_production and not self.pre_call_rehearsal:
                    evidence_path = _write_axis_citable_evidence(
                        descriptor=descriptor,
                        axis=axis,
                        frozen_identity=frozen_identity,
                        live_attestation=live_attestation,
                        health=health,
                        authority=axis_authority,
                        question_results=question_results,
                        counters=counters,
                    )
                axis_receipts.append(
                    {
                        "axis_id": axis.axis_id,
                        "frozen_identity_fingerprint": frozen_identity.fingerprint,
                        "durable_root": str(axis_root),
                        "question_count": axis_question_count,
                        "status": "completed",
                        "evidence_path": None if evidence_path is None else str(evidence_path),
                    }
                )
            if not barrier_reached:
                ledger.record_pre_call_barrier(
                    payload={
                        "campaign_fingerprint": descriptor.fingerprint,
                        "hindsight_health_fingerprint": health.fingerprint
                        if health is not None
                        else None,
                        "axis_count": len(descriptor.axes),
                        "frozen_identity_count": len(axis_receipts),
                        "llama_server_launch_count": session.launch_count
                        if session is not None
                        else 0,
                        "semantic_generation_count": 0,
                        "benchmark_question_count": 0,
                        "answer_model_generation_count": 0,
                        "judge_call_count": 0,
                        "SCIENTIFIC_SPEND": "UNSPENT",
                    }
                )
                barrier_reached = True
            status = "COMPLETED"
        finally:
            active = sys.exc_info()[1]
            cleanup_errors: list[str] = []
            if session is not None:
                try:
                    cleanup = _normalise_cleanup(
                        _require_mapping(session.cleanup(), label="owned cleanup receipt")
                    )
                except BaseException as exc:
                    cleanup_errors.append(f"llama cleanup failed: {exc}")
            if self.hindsight_lifecycle is not None:
                try:
                    lifecycle_cleanup = self.hindsight_lifecycle.cleanup()
                except BaseException as exc:
                    cleanup_errors.append(f"Hindsight cleanup failed: {exc}")
            if cleanup_errors:
                if active is not None:
                    for detail in cleanup_errors:
                        active.add_note(detail)
                else:
                    raise CampaignCarriageError("; ".join(cleanup_errors))

        if health is None:
            raise CampaignCarriageError("campaign did not obtain Hindsight health")
        if session is None or cleanup is None:
            raise CampaignCarriageError("campaign did not create an owned runtime session")
        if self.pre_call_rehearsal:
            status = "PRE_CALL_BARRIER_REACHED"
        if lifecycle_cleanup is None and self.hindsight_lifecycle is not None:
            raise CampaignCarriageError("Hindsight lifecycle did not create a cleanup receipt")
        if live_attestation is None:
            raise CampaignCarriageError("campaign did not retain live launch attestation")

        observed_execution = {
            "authority": "OBSERVED_EXECUTION",
            "live_launch_attestation": live_attestation.to_mapping(),
            "live_launch_attestation_fingerprint": live_attestation.fingerprint,
            "hindsight_runtime_identity_path": (
                lifecycle_cleanup.get("runtime_identity_path")
                if lifecycle_cleanup is not None
                else None
            ),
            "artifact_root": str(descriptor.artifact_root),
            "spend_ledger_path": str(descriptor.spend_ledger_path),
            "axis_evidence_paths": {
                str(item["axis_id"]): item.get("evidence_path")
                for item in axis_receipts
            },
        }

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
            "hindsight_cleanup": lifecycle_cleanup,
            "observed_execution": observed_execution,
            "pre_call_barrier_reached": barrier_reached,
            "SCIENTIFIC_SPEND": ledger.state,
        }


def run_campaign(
    descriptor: CampaignDescriptor,
    *,
    live_launch_factory: LiveLaunchFactory,
    hindsight_probe: HindsightHealthProbe,
    participant_executors: ParticipantExecutors,
    current_authority_reader: CurrentAuthorityReader,
    hindsight_lifecycle: HindsightDeploymentSession | None = None,
    pre_call_rehearsal: bool = False,
) -> Mapping[str, Any]:
    return asyncio.run(
        CampaignController(
            descriptor,
            live_launch_factory=live_launch_factory,
            hindsight_probe=hindsight_probe,
            participant_executors=participant_executors,
            current_authority_reader=current_authority_reader,
            hindsight_lifecycle=hindsight_lifecycle,
            pre_call_rehearsal=pre_call_rehearsal,
        ).run()
    )


class LlamaCppLiveLaunchSession:
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
        digest = _sha256_file(self.spec.artifact_path)
        if digest != self.spec.artifact_sha256:
            raise CampaignCarriageError("release artifact digest drifted from the frozen plan")
        try:
            _identity, self._version_output = probe_cli_identity(
                binary,
                expected_build_info=self.spec.expected_build_info,
                upstream_revision=self.spec.upstream_revision,
            )
        except LlamaCppIdentityError as exc:
            raise CampaignCarriageError(str(exc)) from exc

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
        stable_gpu = {
            key: gpu[key]
            for key in ("name", "driver_version", "memory_total_mib")
        }
        expected_stable_gpu = (
            None
            if not isinstance(expected_gpu, Mapping)
            else {
                key: expected_gpu[key]
                for key in ("name", "driver_version", "memory_total_mib")
                if key in expected_gpu
            }
        )
        if expected_stable_gpu is not None and expected_stable_gpu != stable_gpu:
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
        runtime_payload = {
            "upstream_revision": runtime_identity.upstream_revision,
            "build_info": runtime_identity.build_info,
            "model_alias": runtime_identity.model_alias,
            "model_path": runtime_identity.model_path,
            "artifact_sha256": runtime_identity.artifact_sha256,
            "chat_template_sha256": runtime_identity.chat_template_sha256,
            "context_limit": runtime_identity.context_limit,
            "total_slots": runtime_identity.total_slots,
            "context_shift_enabled": runtime_identity.context_shift_enabled,
        }
        try:
            verify_props_build_info(
                actual_build_info=runtime_identity.build_info,
                expected_build_info=self.spec.expected_build_info,
                upstream_revision=self.spec.upstream_revision,
            )
        except LlamaCppIdentityError as exc:
            raise CampaignCarriageError(str(exc)) from exc
        launch_payload = {
            "format_version": 1,
            "kind": "llama_cpp_live_launch_attestation",
            "runtime": self.spec.runtime,
            "model_runner": self.spec.model_runner,
            "version_output": self._version_output,
            "runtime_identity": runtime_payload,
            "gpu": gpu,
            "capacity_evidence": self.spec.capacity_evidence,
        }
        _write_json_fsync(launch_ref, launch_payload)
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
        _write_json_fsync(ownership_ref, ownership_payload)
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
                "runtime_identity": runtime_payload,
                "gpu_identity": stable_gpu,
                "launch_observation": {
                    "runtime_evidence_path": str(launch_ref),
                    "runtime_ownership_evidence_path": str(ownership_ref),
                    "pid": self.process.pid,
                    "memory_used_mib": gpu["memory_used_mib"],
                    "observed_at": str(time.time_ns()),
                },
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
    return LlamaCppLiveLaunchSession.start(spec, evidence_root)


def _openai_observation(
    *,
    payload: Mapping[str, Any],
    elapsed_ms: float,
    note: str,
) -> dict[str, Any]:
    usage = payload.get("usage")
    usage_mapping = usage if isinstance(usage, Mapping) else {}
    choices = payload.get("choices")
    failure = None
    if not isinstance(choices, list) or not choices:
        failure = "provider_response_missing_choices"
    return {
        "quality": {},
        "tokens": {
            "model_input_tokens": usage_mapping.get("prompt_tokens"),
            "model_output_tokens": usage_mapping.get("completion_tokens"),
            "model_call_count": 1,
        },
        "latency": {
            "ttft_ms": None,
            "query_latency_ms": elapsed_ms,
            "end_to_end_ms": elapsed_ms,
        },
        "resources": {
            "peak_gpu_memory_bytes": None,
            "peak_cpu_memory_bytes": None,
            "persistent_storage_bytes": None,
            "notes": [note],
        },
        "known_limitations": ["benchmark-native scoring is owner-supplied"],
        "failure": failure,
    }


def _hindsight_retrieved_memories(
    recalled: Mapping[str, Any],
) -> list[dict[str, object]]:
    """Map v0.10 RecallResponse into the frozen common-harness shape."""

    results = recalled.get("results")
    if not isinstance(results, list) or not all(
        isinstance(item, Mapping) for item in results
    ):
        raise CampaignCarriageError("Hindsight recall response results are invalid")
    mapped: list[dict[str, object]] = []
    for result in results:
        memory = result.get("text", result.get("memory", ""))
        if not isinstance(memory, str):
            raise CampaignCarriageError("Hindsight recall result text is invalid")
        created_at = next(
            (
                result.get(name)
                for name in (
                    "occurred_start",
                    "mentioned_at",
                    "occurred_end",
                )
                if isinstance(result.get(name), str) and result.get(name)
            ),
            "Unknown Time",
        )
        scores = result.get("scores")
        final_score = scores.get("final") if isinstance(scores, Mapping) else None
        mapped.append(
            {
                "memory": memory,
                "created_at": created_at,
                "score": final_score,
                "id": result.get("id"),
                "type": result.get("type"),
            }
        )
    return mapped


def _build_common_retrieved_context(
    retrieved_memories: Sequence[Mapping[str, object]],
) -> str:
    lines = ["Retrieved memories:"]
    if not retrieved_memories:
        lines.append("No relevant memories found.")
    else:
        for index, item in enumerate(retrieved_memories, start=1):
            lines.append(
                f"{index}. [{item.get('created_at', 'Unknown Time')}] {item.get('memory', '')}"
            )
    return "\n".join(lines)


def _build_common_answer_user_prompt(
    retrieved_memories: Sequence[Mapping[str, object]],
    question: str,
) -> str:
    context = _build_common_retrieved_context(retrieved_memories)
    return (
        f"{_COMMON_ANSWER_USER_PREFIX}{context}"
        f"{_COMMON_ANSWER_USER_QUESTION}{question}"
        f"{_COMMON_ANSWER_USER_SUFFIX}"
    )


def _hindsight_context_label(context: ParticipantExecutionContext) -> str:
    benchmark = context.case.get("benchmark")
    if isinstance(benchmark, Mapping):
        benchmark_id = benchmark.get("id")
    else:
        benchmark_id = benchmark
    if isinstance(benchmark_id, str):
        normalized = benchmark_id.lower()
        if "longmemeval" in normalized:
            return "LongMemEval"
        if "memconflict" in normalized:
            return "MemConflict"
    raise CampaignCarriageError(
        "Hindsight comparator is bounded to MemConflict or LongMemEval"
    )


@dataclass(frozen=True, slots=True)
class CommonAnswerModelResult:
    observation: Mapping[str, Any]
    request_evidence: Mapping[str, Any]


class CommonAnswerModelExecutor:
    """The single provider-neutral answer-generation boundary for C."""

    def __init__(self, spec: LlamaCppLaunchSpec) -> None:
        self.spec = spec
        self.client = httpx.Client(timeout=120.0, trust_env=False)

    def answer(
        self,
        context: ParticipantExecutionContext,
        retrieved_memories: Sequence[Mapping[str, object]],
    ) -> CommonAnswerModelResult:
        decoding = context.participant_identity.get("decoding")
        reasoning = context.participant_identity.get("reasoning")
        if not isinstance(decoding, Mapping) or not isinstance(reasoning, Mapping):
            raise CampaignCarriageError("common answer model condition identity is invalid")
        if not decoding or not reasoning:
            raise CampaignCarriageError("common answer model condition identity is empty")

        def numeric_value(name: str, value: object) -> int | float:
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                raise CampaignCarriageError(
                    f"common answer model decoding.{name} is not numeric"
                )
            try:
                parsed = float(value)
            except (TypeError, ValueError) as exc:
                raise CampaignCarriageError(
                    f"common answer model decoding.{name} is not numeric"
                ) from exc
            if not math.isfinite(parsed):
                raise CampaignCarriageError(
                    f"common answer model decoding.{name} is not finite"
                )
            return int(parsed) if parsed.is_integer() else parsed

        # The frozen common harness passes its answer decoding from the run
        # environment.  The campaign identity is the only allowed carriage of
        # that condition; absent fields are intentionally omitted rather than
        # replaced with a provider default or a guessed value.
        request_decoding: dict[str, int | float] = {}
        for name in (
            "temperature",
            "top_p",
            "max_tokens",
            "presence_penalty",
            "frequency_penalty",
            "seed",
        ):
            if name in decoding:
                request_decoding[name] = numeric_value(name, decoding[name])

        effort = str(reasoning.get("effort", "")).strip().lower()
        mode = str(reasoning.get("mode", "")).strip().lower()
        if effort in {"", "none", "off", "false", "0"} and mode in {
            "",
            "none",
            "off",
            "false",
            "0",
        }:
            reasoning_extra: dict[str, object] | None = None
        elif effort:
            # Match benchmark/llm_reasoning.py: both spellings are sent so
            # the frozen OpenAI-compatible sidecar can consume its declared
            # reasoning contract without changing the common prompt.
            reasoning_extra = {
                "reasoning": {"effort": reasoning["effort"]},
                "reasoning_effort": reasoning["effort"],
            }
        else:
            raise CampaignCarriageError(
                "common answer model reasoning condition is not supported by the frozen boundary"
            )
        user_prompt = _build_common_answer_user_prompt(
            retrieved_memories,
            context.prompt,
        )
        started = time.monotonic()
        request_payload: dict[str, object] = {
            "model": self.spec.expected_model_alias,
            "messages": [
                {"role": "system", "content": COMMON_ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            **request_decoding,
        }
        if reasoning_extra is not None:
            request_payload["extra_body"] = reasoning_extra
        try:
            response = self.client.post(
                f"http://127.0.0.1:{self.spec.port}/v1/chat/completions",
                json=request_payload,
            )
            if response.status_code != 200:
                raise CampaignCarriageError(
                    f"common answer model returned HTTP {response.status_code}"
                )
            payload = _require_mapping(
                response.json(), label="common answer model response"
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise CampaignCarriageError("common answer model request failed") from exc
        return CommonAnswerModelResult(
            observation=_openai_observation(
                payload=payload,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
                note="frozen common answer-model llama.cpp boundary",
            ),
            request_evidence={
                "boundary": "common_answer_model",
                "endpoint": "/v1/chat/completions",
                "model": self.spec.expected_model_alias,
                "decoding": dict(decoding),
                "reasoning": dict(reasoning),
                "prompt_condition": {
                    "system_prompt_sha256": _fingerprint(COMMON_ANSWER_SYSTEM_PROMPT),
                    "user_prompt_sha256": _fingerprint(user_prompt),
                    "retrieved_context_sha256": _fingerprint(
                        _build_common_retrieved_context(retrieved_memories)
                    ),
                    "format": "frozen-hermes-common-answer-v1",
                },
                "retrieved_memory_count": len(retrieved_memories),
                "response_shape": sorted(payload),
            },
        )


class SameModelDirectExecutor:
    def __init__(self, spec: LlamaCppLaunchSpec) -> None:
        self.spec = spec
        self.client = httpx.Client(timeout=120.0, trust_env=False)

    def __call__(self, context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        started = time.monotonic()
        try:
            response = self.client.post(
                f"http://127.0.0.1:{self.spec.port}/v1/chat/completions",
                json={
                    "model": self.spec.expected_model_alias,
                    "messages": [{"role": "user", "content": context.prompt}],
                    "temperature": 0,
                    "stream": False,
                },
            )
            if response.status_code != 200:
                raise CampaignCarriageError(
                    f"same_model_direct returned HTTP {response.status_code}"
                )
            payload = _require_mapping(response.json(), label="same_model_direct response")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise CampaignCarriageError("same_model_direct request failed") from exc
        observation = _openai_observation(
            payload=payload,
            elapsed_ms=(time.monotonic() - started) * 1000.0,
            note="same_model_direct llama.cpp /v1/chat/completions",
        )
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation=observation,
            semantic_generation_count=1,
            request_evidence=(
                {
                    "boundary": "same_model_direct",
                    "endpoint": "/v1/chat/completions",
                    "question_id": context.question.question_id,
                },
            ),
        )


class HindsightComparatorExecutor:
    def __init__(
        self,
        lifecycle: HindsightDeploymentSession,
        answer_model: CommonAnswerModelExecutor,
    ) -> None:
        self.lifecycle = lifecycle
        self.answer_model = answer_model

    def __call__(self, context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        if context.history is None:
            raise CampaignCarriageError(
                "Hindsight comparator requires benchmark-faithful history material"
            )
        bank_id = _hindsight_axis_bank_id(
            self.lifecycle.spec.database_profile,
            context.axis_id,
        )
        sessions = context.history.sessions_for_question(context.question.question_id)
        if context.durable_run is None:
            raise CampaignCarriageError(
                "Hindsight comparator requires a repository-owned durable preload journal"
            )
        context_label = _hindsight_context_label(context)
        retained_exchange_count = sum(len(session.exchanges()) for session in sessions)
        newly_retained_exchange_count = 0
        consolidation_waits: list[dict[str, object]] = []
        initial_preload_counts = context.durable_run.hindsight_history_preload_counts()
        allow_missing_bank = (
            initial_preload_counts["completed"] == 0
            and initial_preload_counts["in_flight"] == 0
        )

        for session in sessions:
            pending_exchange_indices = [
                exchange_index
                for exchange_index, _exchange in enumerate(session.exchanges())
                if not context.durable_run.hindsight_history_preload_completed(
                    question_id=context.question.question_id,
                    bank_id=bank_id,
                    session_id=session.session_id,
                    exchange_index=exchange_index,
                )
            ]
            if not pending_exchange_indices:
                continue

            # Frozen Arm-C snapshots and drains consolidation per history session.
            pre_existing_pending_ids = self.lifecycle.consolidation_pending_ids(
                bank_id=bank_id,
                allow_missing_bank=allow_missing_bank,
            )
            session_pending: list[tuple[int, Mapping[str, object]]] = []
            for exchange_index in pending_exchange_indices:
                request = session.to_retain_request(
                    bank_id=bank_id,
                    context_label=context_label,
                    exchange_index=exchange_index,
                )
                if not context.durable_run.begin_hindsight_history_preload(
                    question_id=context.question.question_id,
                    bank_id=bank_id,
                    session_id=session.session_id,
                    exchange_index=exchange_index,
                    request=request,
                ):
                    continue
                self.lifecycle.retain(bank_id=bank_id, items=(request,))
                session_pending.append((exchange_index, request))
                newly_retained_exchange_count += 1

            if not session_pending:
                continue
            wait_result = self.lifecycle.wait_for_consolidation(
                bank_id=bank_id,
                pre_existing_pending_ids=pre_existing_pending_ids,
            )
            consolidation_waits.append(
                {
                    "session_id": session.session_id,
                    **dict(wait_result),
                }
            )
            for exchange_index, request in session_pending:
                context.durable_run.complete_hindsight_history_preload(
                    question_id=context.question.question_id,
                    bank_id=bank_id,
                    session_id=session.session_id,
                    exchange_index=exchange_index,
                    request=request,
                )
        question_timestamp = context.case.get("question_date")
        if not isinstance(question_timestamp, str):
            question_timestamp = None
        query_timestamp = context.history.query_timestamp_for_question(
            context.question.question_id,
            question_timestamp=question_timestamp,
        )
        recalled = self.lifecycle.recall(
            context.prompt,
            bank_id=bank_id,
            query_timestamp=query_timestamp,
        )
        retrieved_memories = _hindsight_retrieved_memories(recalled)
        answer = self.answer_model.answer(context, retrieved_memories)
        preload_counts = context.durable_run.hindsight_history_preload_counts()
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation=answer.observation,
            request_evidence=(
                {
                    "boundary": "hindsight_retrieval",
                    "operations": [
                        "retain",
                        "consolidation_wait",
                        "recall",
                    ]
                    if newly_retained_exchange_count
                    else ["recall"],
                    "bank_id": bank_id,
                    "retain_granularity": HINDSIGHT_RETAIN_GRANULARITY,
                    "document_update_mode": "append",
                    "recall_fact_types": list(HINDSIGHT_RECALL_TYPES),
                    "prefer_observations": HINDSIGHT_PREFER_OBSERVATIONS,
                    "wait_consolidation": HINDSIGHT_WAIT_CONSOLIDATION,
                    "consolidation_wait_timeout_seconds": HINDSIGHT_CONSOLIDATION_WAIT_TIMEOUT_SECONDS,
                    "retained_exchange_count": retained_exchange_count,
                    "newly_retained_exchange_count": newly_retained_exchange_count,
                    "retain_metadata_contract": (
                        "memconflict_frozen_arm_c"
                        if context_label == "MemConflict"
                        else "longmemeval_no_extra_metadata"
                    ),
                    "history_preload_durability": preload_counts,
                    "recall_request": {
                        "budget": HINDSIGHT_RECALL_BUDGET,
                        "max_tokens": HINDSIGHT_RECALL_MAX_TOKENS,
                        "types": list(HINDSIGHT_RECALL_TYPES),
                        "prefer_observations": HINDSIGHT_PREFER_OBSERVATIONS,
                        "query_timestamp": query_timestamp,
                    },
                    "response_shape": {
                        "recall": sorted(recalled),
                    },
                    "retrieved_memory_count": len(retrieved_memories),
                    "consolidation_waits": consolidation_waits,
                },
                dict(answer.request_evidence),
            ),
            answer_model_generation_count=1,
        )


class ExactRelayLMExecutor:
    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    @staticmethod
    def _history_sessions(
        context: ParticipantExecutionContext,
    ) -> list[dict[str, object]]:
        if context.history is None:
            raise CampaignCarriageError(
                "exact RC participant requires benchmark-faithful history material"
            )
        sessions = context.history.sessions_for_question(context.question.question_id)
        if not sessions:
            raise CampaignCarriageError(
                "exact RC participant requires a non-empty question history prefix"
            )
        return [
            {
                "session_id": session.session_id,
                "order": session.order,
                "items": [dict(item) for item in session.items],
            }
            for session in sessions
        ]

    def __call__(self, context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        started = time.monotonic()
        try:
            if self.adapter.start_count == 0:
                self.adapter.start()
            payload = self.adapter.query(
                axis_id=context.axis_id,
                question_id=context.question.question_id,
                question=context.prompt,
                sessions=self._history_sessions(context),
            )
        except Exception as exc:
            raise CampaignCarriageError("exact RC participant request failed") from exc

        model_call_count = payload.get("model_call_count")
        if (
            isinstance(model_call_count, bool)
            or not isinstance(model_call_count, int)
            or model_call_count <= 0
        ):
            raise CampaignCarriageError(
                "exact RC adapter returned an invalid model_call_count"
            )
        prompt_tokens = payload.get("prompt_tokens")
        completion_tokens = payload.get("completion_tokens")
        for name, value in (
            ("prompt_tokens", prompt_tokens),
            ("completion_tokens", completion_tokens),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise CampaignCarriageError(
                    f"exact RC adapter returned invalid {name}"
                )
        external_evidence = payload.get("external_evidence")
        if not isinstance(external_evidence, Mapping):
            raise CampaignCarriageError(
                "exact RC adapter omitted RelayLM query evidence"
            )
        history_session_ids = payload.get("history_session_ids")
        if not isinstance(history_session_ids, list) or not all(
            isinstance(item, str) and item for item in history_session_ids
        ):
            raise CampaignCarriageError(
                "exact RC adapter returned invalid history session ids"
            )

        elapsed_ms = (time.monotonic() - started) * 1000.0
        total_tokens = (
            None
            if prompt_tokens is None or completion_tokens is None
            else prompt_tokens + completion_tokens
        )
        observation = {
            "quality": {},
            "tokens": {
                "model_input_tokens": prompt_tokens,
                "model_output_tokens": completion_tokens,
                "model_call_count": model_call_count,
            },
            "latency": {
                "ttft_ms": None,
                "query_latency_ms": elapsed_ms,
                "end_to_end_ms": elapsed_ms,
            },
            "resources": {
                "peak_gpu_memory_bytes": None,
                "peak_cpu_memory_bytes": None,
                "persistent_storage_bytes": None,
                "notes": [
                    "accepted RC1 installed runtime transcript-replay/frozen-query adapter"
                ],
            },
            "known_limitations": [
                "benchmark-native scoring is owner-supplied",
                (
                    "exact-RC adapter trajectory is fail-closed after process loss; "
                    "semantic replay is not regenerated"
                ),
            ],
            "failure": None,
        }
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation=observation,
            semantic_generation_count=model_call_count,
            request_evidence=(
                {
                    "boundary": "relaylm_exact_rc_history_adapter",
                    "installed_runtime": True,
                    "question_id": context.question.question_id,
                    "history_session_ids": history_session_ids,
                    "new_history_session_count": payload.get(
                        "new_history_session_count"
                    ),
                    "new_history_pass2_calls": payload.get(
                        "new_history_pass2_calls"
                    ),
                    "snapshot_fingerprint": payload.get(
                        "snapshot_fingerprint"
                    ),
                    "adapter_query_evidence": dict(external_evidence),
                    "token_total": total_tokens,
                    "resume_policy": (
                        "fail_closed_after_exact_rc_adapter_trajectory_start"
                    ),
                },
            ),
        )


def _current_repository_authority(repo_root: Path) -> Mapping[str, Any]:
    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise CampaignCarriageError(
                f"current repository authority lookup failed: {completed.stderr.strip()}"
            )
        return completed.stdout.strip()

    if git("status", "--porcelain", "--untracked-files=all"):
        raise CampaignCarriageError("qualification checkout must remain clean")
    return {
        "status": "CURRENT_AUTHORITY_CONFIRMED",
        "branch": git("branch", "--show-current"),
        "repository_head": git("rev-parse", "HEAD"),
        "repository_tree": git("rev-parse", "HEAD^{tree}"),
        "source": "exact-qualification-checkout",
    }


def run_production_campaign(
    descriptor: CampaignDescriptor,
    *,
    repo_root: Path,
    rehearsal: bool,
) -> Mapping[str, Any]:
    if descriptor.relaylm_exact_rc is None or descriptor.hindsight_lifecycle is None:
        raise CampaignCarriageError(
            "production campaign requires exact RC and Hindsight lifecycle bindings"
        )
    from tools.v1_external_qualification_exact_rc import (
        ExactRCAdapterSession,
        ExactRCError,
        cleanup_exact_rc,
        install_exact_rc,
    )

    rc = descriptor.relaylm_exact_rc
    runtime_root = descriptor.artifact_root.with_name(
        descriptor.artifact_root.name + ".exact-rc-runtime"
    )
    installation = None
    rc_adapter: Any | None = None
    result_value: dict[str, Any] | None = None
    rc_cleanup: Mapping[str, object] | None = None
    installation_cleanup: Mapping[str, object] | None = None
    direct = SameModelDirectExecutor(descriptor.llama_cpp)
    answer_model = CommonAnswerModelExecutor(descriptor.llama_cpp)
    lifecycle = HindsightDeploymentSession(
        descriptor.hindsight_lifecycle,
        descriptor.hindsight_health,
        repo_root=repo_root,
        evidence_root=descriptor.artifact_root / "hindsight",
    )
    try:
        try:
            installation = install_exact_rc(
                wheel_path=rc.wheel_path,
                wheel_sha256=rc.wheel_sha256,
                expected_version=rc.version,
                expected_distribution=rc.distribution,
                checkout_root=repo_root,
                runtime_root=runtime_root,
            )
        except ExactRCError as exc:
            raise CampaignCarriageError(str(exc)) from exc
        if rehearsal:
            def d_rehearsal(_context: ParticipantExecutionContext) -> ParticipantExecutionResult:
                raise CampaignCarriageError(
                    "zero-semantic rehearsal reached the pre-call barrier before D"
                )

            exact_executor: ParticipantExecutor = d_rehearsal
        else:
            try:
                rc_adapter = ExactRCAdapterSession(
                    installation,
                    config_path=rc.config_path,
                    config_sha256=rc.config_sha256,
                    checkout_root=repo_root,
                    workspace_root=descriptor.artifact_root / "exact-rc-adapter",
                )
            except ExactRCError as exc:
                raise CampaignCarriageError(str(exc)) from exc
            exact_executor = ExactRelayLMExecutor(rc_adapter)
        comparator = HindsightComparatorExecutor(lifecycle, answer_model)
        result = run_campaign(
            descriptor,
            live_launch_factory=start_llama_cpp_session,
            hindsight_probe=lifecycle,
            participant_executors=ParticipantExecutors(
                same_model_direct=direct,
                serious_comparator=comparator,
                relaylm_exact_rc=exact_executor,
            ),
            current_authority_reader=lambda: _current_repository_authority(repo_root),
            hindsight_lifecycle=lifecycle,
            pre_call_rehearsal=rehearsal,
        )
        result_value = dict(result)
        result_value["exact_rc_installation"] = installation.to_mapping()
        result_value["exact_rc_identity"] = rc.to_mapping()
        result_value["exact_rc_adapter_launch_count"] = (
            0 if rc_adapter is None else rc_adapter.start_count
        )
        result_value["exact_rc_adapter_query_count"] = (
            0 if rc_adapter is None else rc_adapter.query_count
        )
    finally:
        if rc_adapter is not None:
            rc_cleanup = rc_adapter.cleanup()
        direct.client.close()
        answer_model.client.close()
        if installation is not None:
            installation_cleanup = cleanup_exact_rc(installation)
            if result_value is not None:
                result_value["exact_rc_cleanup"] = {
                    **dict(installation_cleanup),
                    "adapter": None if rc_cleanup is None else dict(rc_cleanup),
                }
    if result_value is None:
        raise CampaignCarriageError("production campaign did not return a receipt")
    if installation_cleanup is not None and installation_cleanup.get("errors"):
        raise CampaignCarriageError("exact RC runtime cleanup failed")
    if rc_cleanup is not None and rc_cleanup.get("errors"):
        raise CampaignCarriageError("exact RC adapter cleanup failed")
    return result_value


def validate_zero_semantic_carriage(descriptor: CampaignDescriptor) -> Mapping[str, Any]:
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
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--rehearsal",
        action="store_true",
        help="run typed setup and stop before the first scientific participant call",
    )
    modes.add_argument(
        "--execute",
        action="store_true",
        help="run the typed citable campaign for a separately authorized scientific owner",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        descriptor = CampaignDescriptor.from_path(args.plan)
        if args.rehearsal or args.execute:
            result = run_production_campaign(
                descriptor,
                repo_root=Path(__file__).resolve().parents[1],
                rehearsal=args.rehearsal,
            )
        else:
            result = validate_zero_semantic_carriage(descriptor)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CampaignCarriageError, ExternalQualificationError, ExternalQualificationReadinessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
