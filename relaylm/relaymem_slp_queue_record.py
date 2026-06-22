"""Internal canonical record helpers for Phase 6-B2/B3 durable queue files."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"
DISPATCH_KEY_VERSION = "relaymem.slp_dispatch_key.v0"
JOB_ID_VERSION = "relaymem.slp_job_id.v0"
DISPATCH_KEY_PREFIX = "slp-dispatch-v0:"
JOB_ID_PREFIX = "slp-job-v0:"
FILENAME_PREFIX = "slp-dispatch-v0-"
MAX_RECORD_BYTES = 32 * 1024
MAX_TOKEN = 128
MAX_REASON_COUNT = 32
MAX_COUNTER = 2**63 - 1
MAX_LEASE_SECONDS = 7 * 24 * 60 * 60
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled", "dead_letter"})
MUTABLE_STATES = frozenset({"queued", "claimed"})
ALL_STATES = MUTABLE_STATES | TERMINAL_STATES
ALLOWED_STAGES = frozenset({"primary_formation", "primary_write_preflight"})
ALLOWED_ADMISSION_STATUSES = frozenset({"admitted_dry_run", "eligible_for_enqueue"})
ALLOWED_RUNTIME_STATUSES = frozenset({"completed", "succeeded", "idle"})
ALLOWED_POLICY_STATUSES = frozenset({"allowed", "free_to_update"})
DURABLE_JOB_FIELDS = frozenset({
    "schema_version", "job_id", "dispatch_idempotency_key", "dispatch_key_version",
    "candidate_schema_version", "candidate_kind", "trigger_mode", "processing_stage",
    "source_event_kind", "run_id", "turn_index", "session_id", "namespace",
    "source_count", "source_lineage_fingerprint", "source_admission_status",
    "runtime_terminal_status", "persistence_policy_status", "state",
    "record_revision", "created_at", "updated_at", "attempt_count",
    "claim_generation", "claim_owner", "lease_token", "lease_acquired_at",
    "lease_expires_at", "retry_class", "retry_not_before", "failure_class",
    "terminal_reason_id",
})
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def decode_canonical_record(data: bytes) -> tuple[dict[str, object] | None, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "queue_record_malformed_utf8"
    duplicate = False

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        nonlocal duplicate
        output: dict[str, object] = {}
        for key, value in pairs:
            if key in output:
                duplicate = True
            output[key] = value
        return output

    def reject_nonfinite(_: str) -> object:
        raise ValueError("non-finite JSON")

    try:
        value = json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=reject_nonfinite,
        )
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None, "queue_record_malformed_json"
    if duplicate:
        return None, "queue_record_duplicate_json_key"
    if not isinstance(value, dict):
        return None, "queue_record_json_not_object"
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return None, "queue_record_malformed_json"
    if canonical != data:
        return None, "queue_record_noncanonical_json"
    return value, None


def derive_dispatch_key(record: Mapping[str, object]) -> str:
    session_id = record["session_id"]
    canonical_input = [
        ["dispatch_key_version", record["dispatch_key_version"]],
        ["candidate_schema_version", record["candidate_schema_version"]],
        ["candidate_kind", record["candidate_kind"]],
        ["trigger_mode", record["trigger_mode"]],
        ["processing_stage", record["processing_stage"]],
        ["source_event_kind", record["source_event_kind"]],
        ["run_id", record["run_id"]],
        ["turn_index", record["turn_index"]],
        ["session_id_present", session_id is not None],
        ["session_id", session_id if session_id is not None else ""],
        ["namespace", record["namespace"]],
        ["source_count", record["source_count"]],
        ["source_lineage_fingerprint", record["source_lineage_fingerprint"]],
    ]
    encoded = json.dumps(
        canonical_input,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return DISPATCH_KEY_PREFIX + hashlib.sha256(encoded).hexdigest()


def derive_job_id(dispatch_key: str) -> str:
    encoded = (JOB_ID_VERSION + "\0" + dispatch_key).encode("utf-8")
    return JOB_ID_PREFIX + hashlib.sha256(encoded).hexdigest()


def record_filename(dispatch_key: str) -> str:
    digest = dispatch_key.removeprefix(DISPATCH_KEY_PREFIX)
    return FILENAME_PREFIX + digest + ".json"


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("UTC datetime required")
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def parse_timestamp(value: object) -> datetime | None:
    if type(value) is not str or _TIMESTAMP_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timedelta(0) or format_timestamp(parsed) != value:
        return None
    return parsed


def validate_record_mapping(runtime: object) -> tuple[str, ...]:
    if not isinstance(runtime, Mapping):
        return ("durable_job_shape_invalid",)
    if len(runtime) != len(DURABLE_JOB_FIELDS) or set(runtime) != DURABLE_JOB_FIELDS:
        return ("durable_job_shape_mismatch",)
    fixed_values = {
        "schema_version": (DURABLE_JOB_SCHEMA, "durable_job_schema_mismatch"),
        "dispatch_key_version": (DISPATCH_KEY_VERSION, "durable_job_dispatch_key_version_invalid"),
        "candidate_schema_version": ("relaymem.slp_enqueue_candidate.v0", "durable_job_candidate_schema_invalid"),
        "candidate_kind": ("relayslp_deferred_job", "durable_job_candidate_kind_invalid"),
        "trigger_mode": ("turn_end", "durable_job_trigger_mode_invalid"),
        "source_event_kind": ("turn", "durable_job_source_event_kind_invalid"),
    }
    for field, (expected, reason) in fixed_values.items():
        if runtime.get(field) != expected:
            return (reason,)
    if runtime.get("processing_stage") not in ALLOWED_STAGES:
        return ("durable_job_processing_stage_invalid",)
    for field in (
        "run_id", "namespace", "source_admission_status",
        "runtime_terminal_status", "persistence_policy_status",
    ):
        if not is_token(runtime.get(field)):
            return (f"durable_job_{field}_invalid",)
    if runtime.get("source_admission_status") not in ALLOWED_ADMISSION_STATUSES:
        return ("durable_job_source_admission_status_invalid",)
    if runtime.get("runtime_terminal_status") not in ALLOWED_RUNTIME_STATUSES:
        return ("durable_job_runtime_terminal_status_invalid",)
    if runtime.get("persistence_policy_status") not in ALLOWED_POLICY_STATUSES:
        return ("durable_job_persistence_policy_status_invalid",)
    session_id = runtime.get("session_id")
    if session_id is not None and not is_token(session_id):
        return ("durable_job_session_id_invalid",)
    if type(runtime.get("turn_index")) is not int or runtime["turn_index"] < 0:
        return ("durable_job_turn_index_invalid",)
    if type(runtime.get("source_count")) is not int or not 1 <= runtime["source_count"] <= 32:
        return ("durable_job_source_count_invalid",)
    if not is_sha256(runtime.get("source_lineage_fingerprint")):
        return ("durable_job_lineage_invalid",)
    dispatch_key = runtime.get("dispatch_idempotency_key")
    job_id = runtime.get("job_id")
    if not has_prefixed_digest(dispatch_key, DISPATCH_KEY_PREFIX):
        return ("durable_job_dispatch_key_invalid",)
    if dispatch_key != derive_dispatch_key(runtime):
        return ("durable_job_dispatch_key_mismatch",)
    if not has_prefixed_digest(job_id, JOB_ID_PREFIX):
        return ("durable_job_job_id_invalid",)
    if job_id != derive_job_id(str(dispatch_key)):
        return ("durable_job_job_id_mismatch",)
    state = runtime.get("state")
    if state not in ALL_STATES:
        return ("durable_job_state_invalid",)
    for field in ("record_revision", "attempt_count", "claim_generation"):
        if not is_counter(runtime.get(field)):
            return (f"durable_job_{field}_invalid",)
    if runtime["attempt_count"] != runtime["claim_generation"]:
        return ("durable_job_attempt_generation_mismatch",)
    if runtime["record_revision"] < runtime["claim_generation"]:
        return ("durable_job_revision_generation_mismatch",)
    created = parse_timestamp(runtime.get("created_at"))
    updated = parse_timestamp(runtime.get("updated_at"))
    if created is None or updated is None or updated < created:
        return ("durable_job_timestamp_invalid",)
    if not is_token(runtime.get("retry_class")):
        return ("durable_job_retry_class_invalid",)
    if not is_token(runtime.get("failure_class")):
        return ("durable_job_failure_class_invalid",)
    retry_at = runtime.get("retry_not_before")
    if retry_at is not None and parse_timestamp(retry_at) is None:
        return ("durable_job_retry_not_before_invalid",)
    owner = runtime.get("claim_owner")
    token = runtime.get("lease_token")
    acquired = runtime.get("lease_acquired_at")
    expires = runtime.get("lease_expires_at")
    reason = runtime.get("terminal_reason_id")
    if type(owner) is not str or type(token) is not str or type(reason) is not str:
        return ("durable_job_queue_string_type_invalid",)
    if state == "queued":
        if owner or token or acquired is not None or expires is not None:
            return ("durable_job_queued_claim_invariant_invalid",)
        if reason:
            return ("durable_job_queued_terminal_reason_invalid",)
    elif state == "claimed":
        if not is_token(owner) or not is_token(token):
            return ("durable_job_claim_identity_invalid",)
        acquired_at = parse_timestamp(acquired)
        expires_at = parse_timestamp(expires)
        if acquired_at is None or expires_at is None or expires_at <= acquired_at:
            return ("durable_job_lease_timestamp_invalid",)
        if retry_at is not None or reason:
            return ("durable_job_claimed_state_invariant_invalid",)
        if runtime["attempt_count"] < 1:
            return ("durable_job_claimed_counter_invalid",)
    else:
        if owner or token or acquired is not None or expires is not None or retry_at is not None:
            return ("durable_job_terminal_claim_invariant_invalid",)
        if not is_token(reason):
            return ("durable_job_terminal_reason_invalid",)
        if state in {"failed", "dead_letter"} and runtime.get("failure_class") == "none":
            return ("durable_job_terminal_failure_class_invalid",)
        if state in {"succeeded", "cancelled"} and runtime.get("failure_class") != "none":
            return ("durable_job_terminal_failure_class_invalid",)
    return ()


def strict_bool(value: Any, reason: str) -> tuple[bool, tuple[str, ...]]:
    return (value, ()) if type(value) is bool else (False, (reason,))


def is_counter(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_COUNTER


def is_token(value: object) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 0 < len(value) <= MAX_TOKEN
        and all(
            character.isascii()
            and (character.isalnum() or character in "-_.:/")
            for character in value
        )
    )


def is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def has_prefixed_digest(value: object, prefix: str) -> bool:
    return (
        type(value) is str
        and value.startswith(prefix)
        and is_sha256(value[len(prefix):])
    )


def bad_text(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if type(value) is str and value))


__all__ = [
    "ALL_STATES", "DISPATCH_KEY_PREFIX", "DURABLE_JOB_SCHEMA", "MAX_COUNTER",
    "MAX_LEASE_SECONDS", "MAX_REASON_COUNT", "MAX_RECORD_BYTES", "TERMINAL_STATES",
    "bad_text", "canonical_json_bytes", "decode_canonical_record", "dedupe",
    "derive_dispatch_key", "derive_job_id", "format_timestamp", "has_prefixed_digest",
    "is_counter", "is_token", "parse_timestamp", "record_filename", "strict_bool",
    "validate_record_mapping",
]
