"""Durable, bounded read-model receipts for SOUL Lab observation.

These receipts are secondary observation evidence. They never repair or mutate
RelayMEM, RelaySLP, RelayRUN, or RelayCTX authority.
"""
from __future__ import annotations

import heapq
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

STORE_SCHEMA = "relaylm.lab.observation_store.v0"
RUN_RECEIPT_SCHEMA = "relaylm.lab.run_receipt.v0"
OUTCOME_RECEIPT_SCHEMA = "relaylm.lab.memory_outcome_receipt.v0"
USED_RECEIPT_SCHEMA = "relaylm.lab.used_memory_receipt.v0"

_OBSERVATION_DIR = ".relaylm-lab-observation-v0"
_MAX_RECEIPT_BYTES = 64 * 1024
_MAX_RECEIPTS_PER_KIND = 256
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")


class ObservationStoreError(ValueError):
    """Bounded store validation failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_correlation(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def bounded_text(value: object, *, maximum: int) -> str:
    """Return one safe, bounded user-facing text value.

    Control characters and Unicode line/paragraph separators are normalized to
    spaces. The result is text-only and is never intended for HTML insertion.
    """

    if not isinstance(value, str):
        return ""
    output: list[str] = []
    previous_space = False
    for character in value:
        code = ord(character)
        unsafe = code < 32 or code == 127 or character in {"\u2028", "\u2029"}
        normalized = " " if unsafe else character
        if normalized.isspace():
            if previous_space:
                continue
            normalized = " "
            previous_space = True
        else:
            previous_space = False
        output.append(normalized)
        if len(output) >= maximum:
            break
    return "".join(output).strip()


def normalize_reason_ids(values: object, *, maximum: int = 32) -> list[str]:
    output: list[str] = []
    if isinstance(values, (str, bytes, bytearray)):
        values = [values]
    try:
        iterator = iter(values)  # type: ignore[arg-type]
    except TypeError:
        iterator = iter(())
    for value in iterator:
        if not isinstance(value, str) or _REASON_RE.fullmatch(value) is None:
            continue
        if value not in output:
            output.append(value)
        if len(output) >= maximum:
            break
    return output


def write_run_receipt(store_root: object, payload: Mapping[str, Any]) -> bool:
    validated = _validate_run_payload(payload)
    return _write_receipt(store_root, "runs", str(validated["run_id"]), validated)


def write_outcome_receipt(store_root: object, payload: Mapping[str, Any]) -> bool:
    validated = _validate_outcome_payload(payload)
    name = f"{validated['run_id']}--{validated['job_correlation_id']}"
    return _write_receipt(store_root, "outcomes", name, validated)


def write_used_receipt(store_root: object, payload: Mapping[str, Any]) -> bool:
    validated = _validate_used_payload(payload)
    return _write_receipt(store_root, "used", str(validated["run_id"]), validated)


def read_run_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(store_root, "runs", RUN_RECEIPT_SCHEMA, _validate_run_payload)


def read_outcome_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(
        store_root, "outcomes", OUTCOME_RECEIPT_SCHEMA, _validate_outcome_payload
    )


def read_used_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(store_root, "used", USED_RECEIPT_SCHEMA, _validate_used_payload)


def _validate_run_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "runtime_private", "read_model_only", "request_id", "run_id",
        "character_id", "namespace", "started_at", "completed_at", "duration_ms",
        "response_mode", "http_status", "relayrun_status", "relayctx_repack_status",
        "relayctx_unpack_status", "slp_status", "recovery_required", "reason_ids",
    }
    _exact_keys(value, expected)
    if value.get("schema") != RUN_RECEIPT_SCHEMA:
        raise ObservationStoreError("run_receipt_schema_invalid")
    _true(value, "runtime_private")
    _true(value, "read_model_only")
    _token(value, "request_id")
    _token(value, "run_id")
    _token(value, "character_id")
    _token(value, "namespace")
    _timestamp(value, "started_at")
    _timestamp(value, "completed_at")
    duration = value.get("duration_ms")
    if type(duration) is not int or duration < 0 or duration > 86_400_000:
        raise ObservationStoreError("run_receipt_duration_invalid")
    if value.get("response_mode") not in {"stream", "non_stream"}:
        raise ObservationStoreError("run_receipt_response_mode_invalid")
    status = value.get("http_status")
    if type(status) is not int or not 100 <= status <= 599:
        raise ObservationStoreError("run_receipt_http_status_invalid")
    if value.get("relayrun_status") not in {"completed", "failed"}:
        raise ObservationStoreError("run_receipt_relayrun_status_invalid")
    if value.get("relayctx_repack_status") not in {"applied", "not_applied", "blocked", "unavailable"}:
        raise ObservationStoreError("run_receipt_repack_status_invalid")
    if value.get("relayctx_unpack_status") not in {"not_observed", "completed", "blocked", "unavailable"}:
        raise ObservationStoreError("run_receipt_unpack_status_invalid")
    if value.get("slp_status") not in {"disabled", "deferred", "unavailable"}:
        raise ObservationStoreError("run_receipt_slp_status_invalid")
    if type(value.get("recovery_required")) is not bool:
        raise ObservationStoreError("run_receipt_recovery_invalid")
    reasons = normalize_reason_ids(value.get("reason_ids"))
    if reasons != value.get("reason_ids"):
        raise ObservationStoreError("run_receipt_reasons_invalid")
    return dict(value)


def _validate_outcome_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "runtime_private", "read_model_only", "run_id",
        "job_correlation_id", "namespace", "turn_index", "outcome_status",
        "worker_status", "pipeline_status", "title", "bounded_summary",
        "observed_at", "reason_ids",
    }
    _exact_keys(value, expected)
    if value.get("schema") != OUTCOME_RECEIPT_SCHEMA:
        raise ObservationStoreError("outcome_receipt_schema_invalid")
    _true(value, "runtime_private")
    _true(value, "read_model_only")
    _token(value, "run_id")
    correlation = value.get("job_correlation_id")
    if not isinstance(correlation, str) or _HEX_RE.fullmatch(correlation) is None:
        raise ObservationStoreError("outcome_receipt_correlation_invalid")
    _token(value, "namespace")
    turn = value.get("turn_index")
    if type(turn) is not int or turn < 0:
        raise ObservationStoreError("outcome_receipt_turn_invalid")
    if value.get("outcome_status") not in {"formed", "held", "blocked"}:
        raise ObservationStoreError("outcome_receipt_status_invalid")
    _token(value, "worker_status")
    pipeline = value.get("pipeline_status")
    if pipeline is not None and (not isinstance(pipeline, str) or _TOKEN_RE.fullmatch(pipeline) is None):
        raise ObservationStoreError("outcome_receipt_pipeline_status_invalid")
    title = value.get("title")
    summary = value.get("bounded_summary")
    if not isinstance(title, str) or title != bounded_text(title, maximum=160):
        raise ObservationStoreError("outcome_receipt_title_invalid")
    if not isinstance(summary, str) or summary != bounded_text(summary, maximum=512):
        raise ObservationStoreError("outcome_receipt_summary_invalid")
    _timestamp(value, "observed_at")
    reasons = normalize_reason_ids(value.get("reason_ids"))
    if reasons != value.get("reason_ids"):
        raise ObservationStoreError("outcome_receipt_reasons_invalid")
    return dict(value)


def _validate_used_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "runtime_private", "read_model_only", "request_id", "run_id",
        "character_id", "namespace", "retrieval_attempted", "candidate_discovered",
        "selected", "relayctx_injection_performed", "backend_bound_included", "items",
        "captured_at", "reason_ids",
    }
    _exact_keys(value, expected)
    if value.get("schema") != USED_RECEIPT_SCHEMA:
        raise ObservationStoreError("used_receipt_schema_invalid")
    _true(value, "runtime_private")
    _true(value, "read_model_only")
    _token(value, "request_id")
    _token(value, "run_id")
    _token(value, "character_id")
    _token(value, "namespace")
    for key in (
        "retrieval_attempted", "candidate_discovered", "selected",
        "relayctx_injection_performed", "backend_bound_included",
    ):
        if type(value.get(key)) is not bool:
            raise ObservationStoreError(f"used_receipt_{key}_invalid")
    raw_items = value.get("items")
    if not isinstance(raw_items, list) or len(raw_items) > 16:
        raise ObservationStoreError("used_receipt_items_invalid")
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise ObservationStoreError("used_receipt_item_invalid")
        _exact_keys(item, {"memory_id", "injected_summary", "source_kind"})
        memory_id = item.get("memory_id")
        if not isinstance(memory_id, str) or _HEX_RE.fullmatch(memory_id) is None:
            raise ObservationStoreError("used_receipt_memory_id_invalid")
        summary = item.get("injected_summary")
        if not isinstance(summary, str) or summary != bounded_text(summary, maximum=512):
            raise ObservationStoreError("used_receipt_summary_invalid")
        source_kind = item.get("source_kind")
        if not isinstance(source_kind, str) or _TOKEN_RE.fullmatch(source_kind) is None:
            raise ObservationStoreError("used_receipt_source_kind_invalid")
        items.append(dict(item))
    _timestamp(value, "captured_at")
    reasons = normalize_reason_ids(value.get("reason_ids"))
    if reasons != value.get("reason_ids"):
        raise ObservationStoreError("used_receipt_reasons_invalid")
    validated = dict(value)
    validated["items"] = items
    return validated


def _write_receipt(store_root: object, kind: str, identity: str, payload: Mapping[str, Any]) -> bool:
    root = _safe_store_root(store_root, create_observation=True)
    kind_dir = root / kind
    _ensure_safe_directory(root, kind_dir)
    final_path = kind_dir / f"{stable_correlation(identity)}.json"
    if final_path.is_symlink():
        raise ObservationStoreError("observation_receipt_symlink_refused")
    envelope = _envelope(payload)
    encoded = _canonical_bytes(envelope)
    if len(encoded) > _MAX_RECEIPT_BYTES:
        raise ObservationStoreError("observation_receipt_size_exceeded")
    if final_path.exists():
        existing = _read_one(final_path, kind_dir)
        if existing == envelope:
            return False
        raise ObservationStoreError("observation_receipt_no_clobber")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".tmp-", dir=kind_dir)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.is_symlink():
            raise ObservationStoreError("observation_temporary_symlink_refused")
        try:
            os.link(temporary, final_path)
        except FileExistsError:
            existing = _read_one(final_path, kind_dir)
            if existing == envelope:
                return False
            raise ObservationStoreError("observation_receipt_no_clobber")
        directory_fd = os.open(kind_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _read_receipts(store_root: object, kind: str, expected_schema: str, validator: Any) -> tuple[list[dict[str, Any]], list[str]]:
    reasons: set[str] = set()
    try:
        root = _safe_store_root(store_root, create_observation=False)
    except ObservationStoreError as exc:
        return [], [str(exc)]
    kind_dir = root / kind
    if not kind_dir.exists():
        return [], []
    if kind_dir.is_symlink() or not kind_dir.is_dir():
        return [], ["observation_kind_directory_unsafe"]

    retained: list[tuple[datetime, str, str, dict[str, Any]]] = []
    valid_count = 0
    try:
        for path in kind_dir.iterdir():
            if path.name.startswith(".tmp-"):
                continue
            try:
                envelope = _read_one(path, kind_dir)
                payload = _validate_envelope(envelope, expected_schema)
                validated = validator(payload)
                timestamp, identity = _receipt_order_key(validated, expected_schema)
                entry = (timestamp, identity, path.name, validated)
                valid_count += 1
                if len(retained) < _MAX_RECEIPTS_PER_KIND:
                    heapq.heappush(retained, entry)
                elif entry[:3] > retained[0][:3]:
                    heapq.heapreplace(retained, entry)
            except (OSError, UnicodeError, json.JSONDecodeError, ObservationStoreError):
                reasons.add("observation_receipt_corrupt_ignored")
    except OSError:
        return [], ["observation_kind_directory_unreadable"]

    if valid_count > _MAX_RECEIPTS_PER_KIND:
        reasons.add("observation_receipt_count_exceeded")
    receipts = [entry[3] for entry in sorted(retained)]
    return receipts, normalize_reason_ids(sorted(reasons))


def _receipt_order_key(payload: Mapping[str, Any], schema: str) -> tuple[datetime, str]:
    if schema == RUN_RECEIPT_SCHEMA:
        timestamp_key = "completed_at"
        identity = str(payload["run_id"])
    elif schema == OUTCOME_RECEIPT_SCHEMA:
        timestamp_key = "observed_at"
        identity = f"{payload['run_id']}:{payload['job_correlation_id']}"
    elif schema == USED_RECEIPT_SCHEMA:
        timestamp_key = "captured_at"
        identity = str(payload["run_id"])
    else:
        raise ObservationStoreError("observation_receipt_schema_unsupported")
    timestamp = datetime.fromisoformat(str(payload[timestamp_key]).replace("Z", "+00:00"))
    return timestamp.astimezone(timezone.utc), identity


def _envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    canonical_payload = json.loads(_canonical_bytes(dict(payload)).decode("utf-8"))
    digest = sha256(_canonical_bytes(canonical_payload)).hexdigest()
    return {"schema": STORE_SCHEMA, "payload": canonical_payload, "payload_digest": digest}


def _validate_envelope(value: object, expected_payload_schema: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ObservationStoreError("observation_envelope_invalid")
    _exact_keys(value, {"schema", "payload", "payload_digest"})
    if value.get("schema") != STORE_SCHEMA:
        raise ObservationStoreError("observation_envelope_schema_invalid")
    payload = value.get("payload")
    digest = value.get("payload_digest")
    if not isinstance(payload, Mapping) or not isinstance(digest, str):
        raise ObservationStoreError("observation_envelope_shape_invalid")
    if payload.get("schema") != expected_payload_schema:
        raise ObservationStoreError("observation_payload_schema_invalid")
    expected_digest = sha256(_canonical_bytes(dict(payload))).hexdigest()
    if digest != expected_digest:
        raise ObservationStoreError("observation_payload_digest_mismatch")
    return dict(payload)


def _read_one(path: Path, root: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ObservationStoreError("observation_receipt_unsafe")
    resolved_root = root.resolve(strict=True)
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ObservationStoreError("observation_receipt_path_escape") from exc
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_RECEIPT_BYTES:
        raise ObservationStoreError("observation_receipt_size_invalid")
    value = json.loads(raw.decode("utf-8"))
    if _canonical_bytes(value) != raw:
        raise ObservationStoreError("observation_receipt_noncanonical")
    if not isinstance(value, dict):
        raise ObservationStoreError("observation_receipt_shape_invalid")
    return value


def _safe_store_root(store_root: object, *, create_observation: bool) -> Path:
    if not isinstance(store_root, str) or not store_root or store_root != store_root.strip():
        raise ObservationStoreError("observation_store_root_invalid")
    root = Path(store_root)
    if _has_symlink_component(root) or not root.exists() or not root.is_dir():
        raise ObservationStoreError("observation_store_root_unsafe_or_missing")
    resolved = root.resolve(strict=True)
    observation = resolved / _OBSERVATION_DIR
    if observation.is_symlink():
        raise ObservationStoreError("observation_directory_symlink_refused")
    if observation.exists() and not observation.is_dir():
        raise ObservationStoreError("observation_directory_unsafe")
    if create_observation:
        observation.mkdir(mode=0o700, exist_ok=True)
    if not observation.exists():
        raise ObservationStoreError("observation_directory_missing")
    return observation


def _ensure_safe_directory(root: Path, path: Path) -> None:
    if path.is_symlink():
        raise ObservationStoreError("observation_kind_symlink_refused")
    if path.exists() and not path.is_dir():
        raise ObservationStoreError("observation_kind_directory_unsafe")
    path.mkdir(mode=0o700, exist_ok=True)
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ObservationStoreError("observation_kind_path_escape") from exc


def _has_symlink_component(path: Path) -> bool:
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _exact_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ObservationStoreError("observation_receipt_exact_keys_required")


def _true(value: Mapping[str, Any], key: str) -> None:
    if value.get(key) is not True:
        raise ObservationStoreError(f"observation_receipt_{key}_required")


def _token(value: Mapping[str, Any], key: str) -> None:
    item = value.get(key)
    if not isinstance(item, str) or _TOKEN_RE.fullmatch(item) is None:
        raise ObservationStoreError(f"observation_receipt_{key}_invalid")


def _timestamp(value: Mapping[str, Any], key: str) -> None:
    item = value.get(key)
    if not isinstance(item, str) or len(item) > 64:
        raise ObservationStoreError(f"observation_receipt_{key}_invalid")
    try:
        parsed = datetime.fromisoformat(item.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ObservationStoreError(f"observation_receipt_{key}_invalid") from exc
    if parsed.tzinfo is None:
        raise ObservationStoreError(f"observation_receipt_{key}_timezone_required")


__all__ = [
    "OUTCOME_RECEIPT_SCHEMA", "RUN_RECEIPT_SCHEMA", "USED_RECEIPT_SCHEMA",
    "ObservationStoreError", "bounded_text", "normalize_reason_ids",
    "read_outcome_receipts", "read_run_receipts", "read_used_receipts",
    "stable_correlation", "utc_now", "write_outcome_receipt", "write_run_receipt",
    "write_used_receipt",
]
