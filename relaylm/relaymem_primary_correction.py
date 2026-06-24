"""Auditable Primary MEM correction using the canonical M3e-M3g boundaries.

The correction layer owns only semantic successor construction, revision fencing,
operation idempotency, and immutable audit receipts. Primary page publication and
index/log convergence remain owned by the existing RelayMEM boundaries.
"""
from __future__ import annotations

import base64
import fcntl
import hmac
import json
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from ._relaymem_primary_page_writer_common import (
    FRONT_MATTER_KEYS,
    KIND_TARGET,
    MAX_PAGE_BYTES,
    MAX_SUMMARY,
    MAX_TITLE,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)
from .relaymem_primary_index_log_apply import apply_relaymem_primary_index_log_reconciliation
from .relaymem_primary_index_log_reconciliation import build_relaymem_primary_index_log_reconciliation_preflight
from .relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from .relaymem_primary_page_writer import apply_relaymem_primary_page_write
from .relaymem_primary_recall import _load_control_state, _load_validated_page
from .relaymem_primary_write_preflight import build_relaymem_primary_write_preflight_dry_run
from .relaymem_primary_writer_handoff import build_relaymem_primary_writer_handoff_preflight

PREFLIGHT_REQUEST_SCHEMA = "relaylm.lab.memory_correct_preflight_request.v0"
PREFLIGHT_RESPONSE_SCHEMA = "relaylm.lab.memory_correct_preflight.v0"
APPLY_REQUEST_SCHEMA = "relaylm.lab.memory_correct_apply_request.v0"
APPLY_RESPONSE_SCHEMA = "relaylm.lab.memory_correct_apply.v0"
HISTORY_SCHEMA = "relaylm.lab.memory_corrections.v0"
PREPARED_SCHEMA = "relaylm.mem.correct_prepared.v0"
RECEIPT_SCHEMA = "relaylm.mem.correct_receipt.v0"

_MAX_REASON = 512
_MAX_OPERATION_ID = 128
_TOKEN_TTL = timedelta(minutes=5)
_CORRECTION_ROOT = PurePosixPath("memory/mem/corrections/v0")
_TOKEN_SECRET = secrets.token_bytes(32)


class PrimaryCorrectionError(RuntimeError):
    """Bounded correction failure safe for API mapping."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CorrectionState:
    current_by_logical: dict[str, tuple[str, int]]
    logical_by_physical: dict[str, str]
    superseded_physical: frozenset[str]
    pending_physical: frozenset[str]
    invalid_logical: frozenset[str]
    receipts_by_logical: dict[str, tuple[dict[str, Any], ...]]


def preflight_primary_memory_correction(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    corrected_title: str,
    corrected_summary: str,
    reason: str,
    operation_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one real formed Primary MEM and issue a short-lived opaque token."""

    _validate_scope_tokens(character_id, namespace, memory_id, operation_id)
    title = _semantic_text(corrected_title, MAX_TITLE, allow_empty=True)
    summary = _semantic_text(corrected_summary, MAX_SUMMARY, allow_empty=False)
    bounded_reason = _semantic_text(reason, _MAX_REASON, allow_empty=False)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryCorrectionError("invalid_request")

    root = _safe_store_root(store_root)
    state = load_primary_correction_state(root, namespace=namespace)
    target = _load_current_target(
        root,
        namespace=namespace,
        logical_memory_id=memory_id,
        expected_revision=expected_revision,
        state=state,
    )
    before_title = str(target["metadata"]["title"])
    before_summary = str(target["metadata"]["summary"])
    if title == before_title and summary == before_summary:
        raise PrimaryCorrectionError("invalid_request")

    candidate_digest = _candidate_digest(title, summary, bounded_reason)
    issued_at = _utc(now)
    expires_at = issued_at + _TOKEN_TTL
    claims = {
        "v": 0,
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "current_physical_id": target["physical_id"],
        "current_revision": expected_revision,
        "candidate_revision": expected_revision + 1,
        "corrected_title": title,
        "corrected_summary": summary,
        "reason": bounded_reason,
        "candidate_digest": candidate_digest,
        "operation_id": operation_id,
        "issued_at": _iso(issued_at),
        "expires_at": _iso(expires_at),
    }
    token = _encode_token(claims)
    return {
        "schema": PREFLIGHT_RESPONSE_SCHEMA,
        "status": "ready",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": expected_revision,
        "candidate_revision": expected_revision + 1,
        "diff": {
            "title_changed": title != before_title,
            "summary_changed": summary != before_summary,
            "before": {"title": before_title, "summary": before_summary},
            "after": {"title": title, "summary": summary},
        },
        "apply_token": token,
        "expires_at": _iso(expires_at),
    }


def apply_primary_memory_correction(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> dict[str, Any]:
    """Apply one exact preflight candidate and converge through M3e-M3g."""

    _validate_scope_tokens(character_id, namespace, memory_id, operation_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryCorrectionError("invalid_request")
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > 8192:
        raise PrimaryCorrectionError("token_invalid")

    root = _safe_store_root(store_root)
    token_digest = sha256(apply_token.encode("utf-8")).hexdigest()
    operation_key = _operation_key(operation_id)

    with _memory_lock(root, memory_id):
        replay = _read_operation_receipt(root, memory_id, operation_key, "applied")
        if replay is not None:
            _validate_replay(
                replay,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=expected_revision,
                operation_id=operation_id,
                token_digest=token_digest,
            )
            return _public_apply_result(replay, idempotent_replay=True)

        claims = _decode_token(apply_token)
        _validate_token_claims(
            claims,
            character_id=character_id,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=expected_revision,
            operation_id=operation_id,
            now=_utc(now),
        )

        prepared = _read_operation_receipt(root, memory_id, operation_key, "prepared")
        if prepared is not None:
            _validate_prepared_replay(prepared, claims=claims, token_digest=token_digest)
        else:
            state = load_primary_correction_state(root, namespace=namespace)
            target = _load_current_target(
                root,
                namespace=namespace,
                logical_memory_id=memory_id,
                expected_revision=expected_revision,
                state=state,
            )
            if target["physical_id"] != claims["current_physical_id"]:
                raise PrimaryCorrectionError("stale_revision")
            prepared = _build_prepared_receipt(
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                operation_id=operation_id,
                operation_key=operation_key,
                token_digest=token_digest,
                claims=claims,
                target=target,
                requested_at=str(claims["issued_at"]),
                prepared_at=_iso(_utc(now)),
            )
            _write_immutable_json(
                _operation_path(root, memory_id, operation_key, "prepared"),
                prepared,
            )
        if fault_at == "after_audit_prepared":
            raise PrimaryCorrectionError("reconciliation_required")

        result = _publish_prepared_successor(root, prepared, fault_at=fault_at)
        applied = {
            "schema_version": RECEIPT_SCHEMA,
            "runtime_private": True,
            "content_included": False,
            "operation_id": operation_id,
            "operation_key": operation_key,
            "correction_id": str(prepared["correction_id"]),
            "character_id": character_id,
            "namespace": namespace,
            "memory_id": memory_id,
            "prior_revision": expected_revision,
            "result_revision": expected_revision + 1,
            "prior_physical_id": str(prepared["prior_physical_id"]),
            "result_physical_id": str(result["result_physical_id"]),
            "prior_canonical_digest": str(prepared["prior_canonical_digest"]),
            "result_canonical_digest": str(result["result_canonical_digest"]),
            "candidate_digest": str(prepared["candidate_digest"]),
            "token_digest": token_digest,
            "requested_at": str(prepared["requested_at"]),
            "applied_at": _iso(_utc(now)),
            "reason": str(prepared["reason"]),
            "status": "reconciled",
            "title_changed": bool(prepared["title_changed"]),
            "summary_changed": bool(prepared["summary_changed"]),
            "recovery_required": False,
        }
        _write_immutable_json(
            _operation_path(root, memory_id, operation_key, "applied"),
            applied,
        )
        if fault_at == "after_audit_finalization":
            raise PrimaryCorrectionError("response_lost")
        return _public_apply_result(applied, idempotent_replay=False)


def list_primary_memory_corrections(
    *, store_root: str, namespace: str, memory_id: str
) -> dict[str, Any]:
    root = _safe_store_root(store_root)
    if not is_sha256(memory_id):
        raise PrimaryCorrectionError("not_found_or_wrong_scope")
    state = load_primary_correction_state(root, namespace=namespace)
    if "*" in state.invalid_logical or memory_id in state.invalid_logical:
        raise PrimaryCorrectionError("target_corrupt")
    current = state.current_by_logical.get(memory_id)
    if current is None:
        target = _load_current_target(
            root,
            namespace=namespace,
            logical_memory_id=memory_id,
            expected_revision=1,
            state=state,
        )
        current = (str(target["physical_id"]), 1)
    receipts = state.receipts_by_logical.get(memory_id, ())
    items = [
        {
            "correction_id": str(item["correction_id"]),
            "prior_revision": int(item["prior_revision"]),
            "result_revision": int(item["result_revision"]),
            "reason": _bounded(str(item["reason"]), _MAX_REASON),
            "status": str(item["status"]),
            "applied_at": str(item["applied_at"]),
            "title_changed": bool(item["title_changed"]),
            "summary_changed": bool(item["summary_changed"]),
        }
        for item in receipts[-50:]
    ]
    return {
        "schema": HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": int(current[1]),
        "correction_count": len(receipts),
        "last_corrected_at": str(receipts[-1]["applied_at"]) if receipts else None,
        "last_correction_status": str(receipts[-1]["status"]) if receipts else None,
        "has_prior_revision": bool(receipts),
        "items": items,
    }


def load_primary_correction_state(
    store_root: str | Path, *, namespace: str
) -> CorrectionState:
    """Load validated applied/pending correction metadata for retrieval and Lab reads."""

    root = _safe_store_root(str(store_root))
    base = root / _CORRECTION_ROOT
    if base.is_symlink():
        return _empty_state(invalid={"*"})
    if not base.exists():
        return _empty_state()
    if not base.is_dir():
        return _empty_state(invalid={"*"})

    current: dict[str, tuple[str, int]] = {}
    logical_by_physical: dict[str, str] = {}
    superseded: set[str] = set()
    pending: set[str] = set()
    invalid: set[str] = set()
    receipts_by_logical: dict[str, tuple[dict[str, Any], ...]] = {}

    try:
        memory_dirs = sorted(base.iterdir(), key=lambda item: item.name)
    except OSError:
        return _empty_state(invalid={"*"})

    for memory_dir in memory_dirs:
        logical = memory_dir.name
        if not is_sha256(logical) or memory_dir.is_symlink() or not memory_dir.is_dir():
            invalid.add(logical if is_sha256(logical) else "*")
            continue
        prepared_by_operation: dict[str, dict[str, Any]] = {}
        applied: list[dict[str, Any]] = []
        try:
            entries = sorted(memory_dir.iterdir(), key=lambda item: item.name)
        except OSError:
            invalid.add(logical)
            continue
        for path in entries:
            if path.name == ".lock":
                continue
            if path.is_symlink() or not path.is_file():
                invalid.add(logical)
                continue
            if path.name.endswith(".prepared.json"):
                value = _read_json(path)
                if not _valid_prepared(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                prepared_by_operation[str(value["operation_key"])] = value
            elif path.name.endswith(".applied.json"):
                value = _read_json(path)
                if not _valid_applied(value, namespace=namespace, memory_id=logical):
                    invalid.add(logical)
                    continue
                applied.append(value)
            else:
                invalid.add(logical)

        applied.sort(key=lambda item: int(item["result_revision"]))
        prior_physical = logical
        prior_revision = 1
        seen_operations: set[str] = set()
        chain_ok = True
        for item in applied:
            operation_key = str(item["operation_key"])
            if (
                operation_key in seen_operations
                or int(item["prior_revision"]) != prior_revision
                or int(item["result_revision"]) != prior_revision + 1
                or item["prior_physical_id"] != prior_physical
            ):
                chain_ok = False
                break
            seen_operations.add(operation_key)
            superseded.add(prior_physical)
            logical_by_physical[prior_physical] = logical
            prior_physical = str(item["result_physical_id"])
            logical_by_physical[prior_physical] = logical
            prior_revision += 1
        if not chain_ok:
            invalid.add(logical)
            continue
        current[logical] = (prior_physical, prior_revision)
        receipts_by_logical[logical] = tuple(applied)
        for operation_key, item in prepared_by_operation.items():
            if operation_key not in seen_operations:
                successor = item.get("successor_physical_id")
                if is_sha256(successor):
                    pending.add(str(successor))
                    logical_by_physical[str(successor)] = logical

    return CorrectionState(
        current_by_logical=current,
        logical_by_physical=logical_by_physical,
        superseded_physical=frozenset(superseded),
        pending_physical=frozenset(pending),
        invalid_logical=frozenset(invalid),
        receipts_by_logical=receipts_by_logical,
    )


def resolve_primary_correction_identity(
    state: CorrectionState, physical_identity: str
) -> tuple[str, int, bool] | None:
    """Map one validated physical page to stable logical identity/current state."""

    if not is_sha256(physical_identity):
        return None
    logical = state.logical_by_physical.get(physical_identity, physical_identity)
    if "*" in state.invalid_logical or logical in state.invalid_logical:
        return None
    if physical_identity in state.pending_physical:
        return None
    current = state.current_by_logical.get(logical, (logical, 1))
    return logical, int(current[1]), physical_identity == current[0]


def recover_primary_memory_corrections(
    *, store_root: str, namespace: str
) -> dict[str, int]:
    """Converge prepared operations without exposing an HTTP mutation shortcut."""

    root = _safe_store_root(store_root)
    base = root / _CORRECTION_ROOT
    if not base.exists() or base.is_symlink() or not base.is_dir():
        return {"recovered": 0, "failed": 0}
    recovered = 0
    failed = 0
    for memory_dir in sorted(base.iterdir(), key=lambda item: item.name):
        logical = memory_dir.name
        if not is_sha256(logical) or memory_dir.is_symlink() or not memory_dir.is_dir():
            failed += 1
            continue
        for prepared_path in sorted(memory_dir.glob("*.prepared.json")):
            operation_key = prepared_path.name.removesuffix(".prepared.json")
            applied_path = _operation_path(root, logical, operation_key, "applied")
            if applied_path.exists():
                continue
            prepared = _read_json(prepared_path)
            if not _valid_prepared(prepared, namespace=namespace, memory_id=logical):
                failed += 1
                continue
            try:
                with _memory_lock(root, logical):
                    result = _publish_prepared_successor(root, prepared, fault_at=None)
                    applied = {
                        "schema_version": RECEIPT_SCHEMA,
                        "runtime_private": True,
                        "content_included": False,
                        "operation_id": str(prepared["operation_id"]),
                        "operation_key": operation_key,
                        "correction_id": str(prepared["correction_id"]),
                        "character_id": str(prepared["character_id"]),
                        "namespace": namespace,
                        "memory_id": logical,
                        "prior_revision": int(prepared["prior_revision"]),
                        "result_revision": int(prepared["result_revision"]),
                        "prior_physical_id": str(prepared["prior_physical_id"]),
                        "result_physical_id": str(result["result_physical_id"]),
                        "prior_canonical_digest": str(prepared["prior_canonical_digest"]),
                        "result_canonical_digest": str(result["result_canonical_digest"]),
                        "candidate_digest": str(prepared["candidate_digest"]),
                        "token_digest": str(prepared["token_digest"]),
                        "requested_at": str(prepared["requested_at"]),
                        "applied_at": _iso(_utc(None)),
                        "reason": str(prepared["reason"]),
                        "status": "reconciled",
                        "title_changed": bool(prepared["title_changed"]),
                        "summary_changed": bool(prepared["summary_changed"]),
                        "recovery_required": False,
                    }
                    _write_immutable_json(applied_path, applied)
                    recovered += 1
            except PrimaryCorrectionError:
                failed += 1
    return {"recovered": recovered, "failed": failed}


def _publish_prepared_successor(
    root: Path, prepared: Mapping[str, Any], *, fault_at: str | None
) -> dict[str, str]:
    lineage = {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": prepared["source_event_kind"],
        "namespace": prepared["namespace"],
        "valid": True,
        "lineage_fingerprint": prepared["lineage_fingerprint"],
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": False,
            "session_id_present": False,
            "turn_index_present": False,
        },
        "blocked_reasons": [],
    }
    candidate = {
        "candidate_id": prepared["successor_candidate_id"],
        "source_event_kind": prepared["source_event_kind"],
        "memory_layer": "primary",
        "memory_kind": prepared["memory_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
    }
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    experience = build_relaymem_governed_experience_summary(
        candidate_id=str(prepared["successor_candidate_id"]),
        source_event_kind=str(prepared["source_event_kind"]),
        namespace=str(prepared["namespace"]),
        summary_text=str(prepared["corrected_summary"]),
        title=str(prepared["corrected_title"]),
    )
    page_candidate = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    pages = page_candidate.get("page_candidates")
    if (
        not isinstance(pages, Sequence)
        or isinstance(pages, (str, bytes))
        or len(pages) != 1
        or not isinstance(pages[0], Mapping)
    ):
        raise PrimaryCorrectionError("target_corrupt")
    successor_identity = pages[0].get("idempotency_key")
    if successor_identity != prepared["successor_physical_id"]:
        raise PrimaryCorrectionError("operation_conflict")

    handoff = build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=page_candidate,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    write_result = apply_relaymem_primary_page_write(
        writer_handoff_artifact=handoff,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    receipt = write_result.get("receipt")
    if not isinstance(receipt, Mapping) or write_result.get("durability_confirmed") is not True:
        raise PrimaryCorrectionError("store_unavailable")
    if fault_at == "after_successor_page_publication":
        raise PrimaryCorrectionError("reconciliation_required")

    reconciliation = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=receipt,
        root_path=str(root),
        enabled=True,
        dry_run_only=True,
    )
    plan = reconciliation.get("plan")
    if not isinstance(plan, Mapping):
        raise PrimaryCorrectionError("reconciliation_required")
    apply_result = apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    if fault_at == "after_index_apply":
        raise PrimaryCorrectionError("reconciliation_required")
    if (
        apply_result.get("index_reconciled") is not True
        or apply_result.get("log_reconciled") is not True
        or apply_result.get("durability_confirmed") is not True
    ):
        raise PrimaryCorrectionError("reconciliation_required")
    if fault_at == "after_reconciliation":
        raise PrimaryCorrectionError("reconciliation_required")
    return {
        "result_physical_id": str(successor_identity),
        "result_canonical_digest": str(receipt["page_digest"]),
    }


def _build_prepared_receipt(
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    operation_id: str,
    operation_key: str,
    token_digest: str,
    claims: Mapping[str, Any],
    target: Mapping[str, Any],
    requested_at: str,
    prepared_at: str,
) -> dict[str, Any]:
    successor_candidate_id = stable_hash(
        (
            "relaymem-primary-correction-candidate-v0",
            memory_id,
            operation_id,
            str(claims["candidate_digest"]),
            str(claims["candidate_revision"]),
        )
    )
    successor_identity = stable_hash(
        (
            "relaymem-primary-write-preflight-v0",
            namespace,
            str(target["metadata"]["source_event_kind"]),
            str(target["metadata"]["lineage_fingerprint"]),
            successor_candidate_id,
            str(target["metadata"]["source_event_kind"]),
            "primary",
            str(target["metadata"]["memory_kind"]),
            "free_to_update",
        )
    )
    return {
        "schema_version": PREPARED_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "operation_id": operation_id,
        "operation_key": operation_key,
        "correction_id": stable_hash(("relaymem-primary-correction-v0", memory_id, operation_id)),
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": int(claims["current_revision"]),
        "result_revision": int(claims["candidate_revision"]),
        "prior_physical_id": str(target["physical_id"]),
        "successor_physical_id": successor_identity,
        "successor_candidate_id": successor_candidate_id,
        "source_event_kind": str(target["metadata"]["source_event_kind"]),
        "memory_kind": str(target["metadata"]["memory_kind"]),
        "lineage_fingerprint": str(target["metadata"]["lineage_fingerprint"]),
        "prior_canonical_digest": str(target["page_digest"]),
        "candidate_digest": str(claims["candidate_digest"]),
        "token_digest": token_digest,
        "corrected_title": str(claims["corrected_title"]),
        "corrected_summary": str(claims["corrected_summary"]),
        "reason": str(claims["reason"]),
        "title_changed": str(claims["corrected_title"]) != str(target["metadata"]["title"]),
        "summary_changed": str(claims["corrected_summary"]) != str(target["metadata"]["summary"]),
        "requested_at": requested_at,
        "prepared_at": prepared_at,
        "status": "prepared",
        "recovery_required": True,
    }


def _load_current_target(
    root: Path,
    *,
    namespace: str,
    logical_memory_id: str,
    expected_revision: int,
    state: CorrectionState,
) -> dict[str, Any]:
    if not is_sha256(logical_memory_id):
        raise PrimaryCorrectionError("not_found_or_wrong_scope")
    if "*" in state.invalid_logical or logical_memory_id in state.invalid_logical:
        raise PrimaryCorrectionError("target_corrupt")
    current_physical, current_revision = state.current_by_logical.get(logical_memory_id, (logical_memory_id, 1))
    if current_revision != expected_revision:
        raise PrimaryCorrectionError("stale_revision")
    control, reasons = _load_control_state(root)
    if control is None or reasons:
        raise PrimaryCorrectionError("target_corrupt")
    matches = [
        entry
        for entry in control["index"]
        if entry.get("idempotency_key") == current_physical
        and entry.get("namespace") == namespace
    ]
    if len(matches) != 1:
        raise PrimaryCorrectionError("not_found_or_wrong_scope")
    relative = matches[0].get("page_relative_path")
    loaded, blocked = _load_validated_page(
        root,
        {"path": relative},
        expected_namespace=namespace,
        control=control,
    )
    if loaded is None or blocked:
        raise PrimaryCorrectionError("target_corrupt")
    path = root / PurePosixPath(str(relative))
    if path.is_symlink() or not path.is_file():
        raise PrimaryCorrectionError("target_corrupt")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PrimaryCorrectionError("store_unavailable") from exc
    if not raw or len(raw) > MAX_PAGE_BYTES:
        raise PrimaryCorrectionError("target_corrupt")
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrimaryCorrectionError("target_corrupt") from exc
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        raise PrimaryCorrectionError("target_corrupt")
    metadata = parsed["metadata"]
    if set(metadata) != set(FRONT_MATTER_KEYS):
        raise PrimaryCorrectionError("target_corrupt")
    return {
        "physical_id": current_physical,
        "revision": current_revision,
        "metadata": metadata,
        "page_digest": sha256(raw).hexdigest(),
        "relative_path": str(relative),
    }


def _validate_scope_tokens(character_id: str, namespace: str, memory_id: str, operation_id: str) -> None:
    for value in (character_id, namespace, operation_id):
        if (
            not isinstance(value, str)
            or value != value.strip()
            or not value
            or len(value) > _MAX_OPERATION_ID
            or _unsafe_text(value)
            or any(char in value for char in "\n\r\t")
        ):
            raise PrimaryCorrectionError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryCorrectionError("not_found_or_wrong_scope")


def _semantic_text(value: object, limit: int, *, allow_empty: bool) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) > limit:
        raise PrimaryCorrectionError("invalid_request")
    if (not value and not allow_empty) or _unsafe_text(value):
        raise PrimaryCorrectionError("invalid_request")
    return value


def _unsafe_text(value: str) -> bool:
    return bad_text(value) or any(
        ord(char) in {0x2028, 0x2029} or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


def _candidate_digest(title: str, summary: str, reason: str) -> str:
    return sha256(_canonical_json({"title": title, "summary": summary, "reason": reason})).hexdigest()


def _encode_token(claims: Mapping[str, Any]) -> str:
    payload = _canonical_json(claims)
    signature = hmac.new(_TOKEN_SECRET, payload, sha256).digest()
    return f"{_b64(payload)}.{_b64(signature)}"


def _decode_token(token: str) -> dict[str, Any]:
    try:
        payload_part, signature_part = token.split(".", 1)
        payload = _unb64(payload_part)
        signature = _unb64(signature_part)
    except (ValueError, TypeError):
        raise PrimaryCorrectionError("token_invalid") from None
    expected = hmac.new(_TOKEN_SECRET, payload, sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise PrimaryCorrectionError("token_invalid")
    try:
        claims = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PrimaryCorrectionError("token_invalid") from None
    if not isinstance(claims, dict) or _canonical_json(claims) != payload:
        raise PrimaryCorrectionError("token_invalid")
    return claims


def _validate_token_claims(
    claims: Mapping[str, Any],
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    operation_id: str,
    now: datetime,
) -> None:
    required = {
        "v", "character_id", "namespace", "memory_id", "current_physical_id",
        "current_revision", "candidate_revision", "corrected_title", "corrected_summary",
        "reason", "candidate_digest", "operation_id", "issued_at", "expires_at",
    }
    if set(claims) != required or claims.get("v") != 0:
        raise PrimaryCorrectionError("token_invalid")
    exact = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "current_revision": expected_revision,
        "candidate_revision": expected_revision + 1,
        "operation_id": operation_id,
    }
    if any(claims.get(key) != value for key, value in exact.items()):
        raise PrimaryCorrectionError("token_invalid")
    if not is_sha256(claims.get("current_physical_id")) or not is_sha256(claims.get("candidate_digest")):
        raise PrimaryCorrectionError("token_invalid")
    try:
        title = _semantic_text(claims.get("corrected_title"), MAX_TITLE, allow_empty=True)
        summary = _semantic_text(claims.get("corrected_summary"), MAX_SUMMARY, allow_empty=False)
        reason = _semantic_text(claims.get("reason"), _MAX_REASON, allow_empty=False)
    except PrimaryCorrectionError:
        raise PrimaryCorrectionError("token_invalid") from None
    if claims["candidate_digest"] != _candidate_digest(title, summary, reason):
        raise PrimaryCorrectionError("token_invalid")
    try:
        expires = datetime.fromisoformat(str(claims["expires_at"]).replace("Z", "+00:00"))
    except ValueError:
        raise PrimaryCorrectionError("token_invalid") from None
    if expires.tzinfo is None or now >= expires.astimezone(timezone.utc):
        raise PrimaryCorrectionError("token_expired")


def _validate_replay(
    receipt: Mapping[str, Any],
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    operation_id: str,
    token_digest: str,
) -> None:
    expected = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "operation_id": operation_id,
        "token_digest": token_digest,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise PrimaryCorrectionError("operation_conflict")


def _validate_prepared_replay(
    prepared: Mapping[str, Any], *, claims: Mapping[str, Any], token_digest: str
) -> None:
    expected = {
        "operation_id": claims["operation_id"],
        "memory_id": claims["memory_id"],
        "prior_revision": claims["current_revision"],
        "result_revision": claims["candidate_revision"],
        "candidate_digest": claims["candidate_digest"],
        "token_digest": token_digest,
    }
    if any(prepared.get(key) != value for key, value in expected.items()):
        raise PrimaryCorrectionError("operation_conflict")


def _public_apply_result(receipt: Mapping[str, Any], *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "schema": APPLY_RESPONSE_SCHEMA,
        "status": "applied",
        "memory_id": str(receipt["memory_id"]),
        "prior_revision": int(receipt["prior_revision"]),
        "result_revision": int(receipt["result_revision"]),
        "correction_id": str(receipt["correction_id"]),
        "reconciled": receipt.get("status") == "reconciled",
        "recovery_required": bool(receipt.get("recovery_required")),
        "idempotent_replay": idempotent_replay,
        "applied_at": str(receipt["applied_at"]),
    }


def _valid_prepared(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "schema_version", "runtime_private", "content_included", "operation_id",
        "operation_key", "correction_id", "character_id", "namespace", "memory_id",
        "prior_revision", "result_revision", "prior_physical_id", "successor_physical_id",
        "successor_candidate_id", "source_event_kind", "memory_kind", "lineage_fingerprint",
        "prior_canonical_digest", "candidate_digest", "token_digest", "corrected_title",
        "corrected_summary", "reason", "title_changed", "summary_changed", "requested_at",
        "prepared_at", "status", "recovery_required",
    }
    return (
        set(value) == required
        and value.get("schema_version") == PREPARED_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is True
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "prepared"
        and value.get("recovery_required") is True
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id", "successor_physical_id",
                "successor_candidate_id", "lineage_fingerprint", "prior_canonical_digest",
                "candidate_digest", "token_digest",
            )
        )
        and isinstance(value.get("operation_id"), str)
        and isinstance(value.get("character_id"), str)
        and value.get("memory_kind") in KIND_TARGET
        and isinstance(value.get("source_event_kind"), str)
        and isinstance(value.get("corrected_title"), str)
        and isinstance(value.get("corrected_summary"), str)
        and isinstance(value.get("reason"), str)
        and type(value.get("title_changed")) is bool
        and type(value.get("summary_changed")) is bool
    )


def _valid_applied(value: object, *, namespace: str, memory_id: str) -> bool:
    if not isinstance(value, dict):
        return False
    required = {
        "schema_version", "runtime_private", "content_included", "operation_id",
        "operation_key", "correction_id", "character_id", "namespace", "memory_id",
        "prior_revision", "result_revision", "prior_physical_id", "result_physical_id",
        "prior_canonical_digest", "result_canonical_digest", "candidate_digest", "token_digest",
        "requested_at", "applied_at", "reason", "status", "title_changed", "summary_changed",
        "recovery_required",
    }
    return (
        set(value) == required
        and value.get("schema_version") == RECEIPT_SCHEMA
        and value.get("runtime_private") is True
        and value.get("content_included") is False
        and value.get("namespace") == namespace
        and value.get("memory_id") == memory_id
        and value.get("status") == "reconciled"
        and value.get("recovery_required") is False
        and type(value.get("prior_revision")) is int
        and type(value.get("result_revision")) is int
        and value.get("result_revision") == value.get("prior_revision") + 1
        and all(
            is_sha256(value.get(key))
            for key in (
                "operation_key", "correction_id", "prior_physical_id", "result_physical_id",
                "prior_canonical_digest", "result_canonical_digest", "candidate_digest", "token_digest",
            )
        )
        and isinstance(value.get("operation_id"), str)
        and isinstance(value.get("character_id"), str)
        and isinstance(value.get("reason"), str)
        and type(value.get("title_changed")) is bool
        and type(value.get("summary_changed")) is bool
    )


def _read_operation_receipt(
    root: Path, memory_id: str, operation_key: str, state: str
) -> dict[str, Any] | None:
    path = _operation_path(root, memory_id, operation_key, state)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise PrimaryCorrectionError("target_corrupt")
    value = _read_json(path)
    validator = _valid_applied if state == "applied" else _valid_prepared
    namespace = value.get("namespace") if isinstance(value, dict) else ""
    if not validator(value, namespace=str(namespace), memory_id=memory_id):
        raise PrimaryCorrectionError("target_corrupt")
    return value


def _operation_path(root: Path, memory_id: str, operation_key: str, state: str) -> Path:
    if not is_sha256(memory_id) or not is_sha256(operation_key) or state not in {"prepared", "applied"}:
        raise PrimaryCorrectionError("invalid_request")
    memory_dir = root / _CORRECTION_ROOT / memory_id
    _ensure_private_dir(root, memory_dir)
    return memory_dir / f"{operation_key}.{state}.json"


def _operation_key(operation_id: str) -> str:
    return stable_hash(("relaymem-primary-correction-operation-v0", operation_id))


@contextmanager
def _memory_lock(root: Path, memory_id: str) -> Iterator[None]:
    memory_dir = root / _CORRECTION_ROOT / memory_id
    _ensure_private_dir(root, memory_dir)
    lock_path = memory_dir / ".lock"
    if lock_path.is_symlink():
        raise PrimaryCorrectionError("target_corrupt")
    try:
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise PrimaryCorrectionError("store_unavailable") from exc


def _write_immutable_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = _canonical_json(value) + b"\n"
    if path.exists():
        existing = _read_json(path)
        if existing == dict(value):
            return
        raise PrimaryCorrectionError("operation_conflict")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError:
        existing = _read_json(path) if path.exists() else None
        if existing != dict(value):
            raise PrimaryCorrectionError("operation_conflict") from None
    except OSError as exc:
        raise PrimaryCorrectionError("store_unavailable") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or _canonical_json(value) + b"\n" != raw:
        return None
    return value


def _safe_store_root(value: str) -> Path:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise PrimaryCorrectionError("store_unavailable")
    root = Path(value)
    if _path_has_symlink(root):
        raise PrimaryCorrectionError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryCorrectionError("store_unavailable")
    return root


def _ensure_private_dir(root: Path, directory: Path) -> None:
    try:
        directory.relative_to(root)
    except ValueError:
        raise PrimaryCorrectionError("target_corrupt") from None
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise PrimaryCorrectionError("target_corrupt")
        if current.exists() and not current.is_dir():
            raise PrimaryCorrectionError("target_corrupt")
        current.mkdir(mode=0o700, exist_ok=True)


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _empty_state(*, invalid: set[str] | None = None) -> CorrectionState:
    return CorrectionState({}, {}, frozenset(), frozenset(), frozenset(invalid or ()), {})


def _canonical_json(value: Mapping[str, Any] | dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _utc(value: datetime | None) -> datetime:
    now = value or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded(value: str, maximum: int) -> str:
    return value if len(value) <= maximum else value[: maximum - 1] + "…"


__all__ = [
    "APPLY_REQUEST_SCHEMA",
    "APPLY_RESPONSE_SCHEMA",
    "HISTORY_SCHEMA",
    "PREFLIGHT_REQUEST_SCHEMA",
    "PREFLIGHT_RESPONSE_SCHEMA",
    "PrimaryCorrectionError",
    "apply_primary_memory_correction",
    "list_primary_memory_corrections",
    "load_primary_correction_state",
    "preflight_primary_memory_correction",
    "recover_primary_memory_corrections",
    "resolve_primary_correction_identity",
]
