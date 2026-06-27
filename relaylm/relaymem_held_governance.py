"""I-7C durable Held Apply / Discard governance runtime.

This module records a human governance decision for one already-held candidate.
It delegates governability checks to the I-7A/B preflight helper, stores only
runtime-private evidence, and returns content-free public projections.  It does
not start workers, schedulers, retry loops, daemons, or rewrite B3 queue files.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .relaymem_held_governance_contract import HELD_STATUS, PUBLIC_EFFECTS
from .relaymem_held_governance_preflight import preflight_held_governance

HELD_GOVERNANCE_CANDIDATE_EVIDENCE_SCHEMA = "relaylm.mem.held_governance_candidate_evidence.v0"
HELD_GOVERNANCE_TOKEN_SCHEMA = "relaylm.mem.held_governance_preflight_token.v0"
HELD_GOVERNANCE_DECISION_SCHEMA = "relaylm.mem.held_governance_decision.v0"
HELD_GOVERNANCE_PREFLIGHT_PUBLIC_SCHEMA = "relaylm.lab.held_governance_preflight.v0"
HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA = "relaylm.lab.held_governance_receipt.v0"
HELD_GOVERNANCE_HISTORY_PUBLIC_SCHEMA = "relaylm.lab.held_governance_history.v0"

_STORE_DIR = ".relaylm-held-governance-v0"
_TOKEN_TTL_SECONDS = 300
_MAX_FILE_BYTES = 64 * 1024
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_ACTIONS = frozenset({"apply", "discard"})
_TERMINAL_BY_ACTION = {"apply": "applied", "discard": "discarded"}
_ALREADY_BY_ACTION = {"apply": "already_applied", "discard": "already_discarded"}


class HeldGovernanceRuntimeError(RuntimeError):
    """Bounded runtime error safe for loopback API translation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def persist_held_candidate_evidence(store_root: str | Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Persist one runtime-private held candidate without payload content."""

    candidate_map = _as_candidate(candidate)
    result = preflight_held_governance(
        "apply",
        candidate_map,
        expected_character_id=str(candidate_map["character_id"]),
        expected_namespace=str(candidate_map["namespace"]),
        expected_scope=str(candidate_map["scope"]),
        store_root=store_root,
    )
    if result.status == "invalid_input":
        raise HeldGovernanceRuntimeError(result.reason_code)
    if candidate_map.get("status") != HELD_STATUS:
        raise HeldGovernanceRuntimeError("not_held")

    root = _root(store_root, create=True)
    envelope = {
        "schema": HELD_GOVERNANCE_CANDIDATE_EVIDENCE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "stored_at": _now(),
        "candidate_id": candidate_map["candidate_id"],
        "character_id": candidate_map["character_id"],
        "namespace": candidate_map["namespace"],
        "scope": candidate_map["scope"],
        "candidate_digest": _digest(candidate_map),
        "source_evidence_digest": candidate_map["source_evidence_digest"],
        "source_reference_body_included": False,
        "queue_payload_included": False,
        "candidate": candidate_map,
    }
    _write_json_atomic(_candidate_path(root, str(candidate_map["candidate_id"])), envelope)
    return {
        "schema": "relaylm.lab.held_governance_candidate_admission.v0",
        "status": "stored",
        "candidate_id_short": _short(str(candidate_map["candidate_id"])),
        "content_free": True,
        "runtime_private_evidence_omitted": True,
    }


def preflight_held_governance_decision(
    store_root: str | Path,
    *,
    candidate_id: str,
    action: str,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str = "primary_formation",
    operation_id: str,
    reason: str,
) -> dict[str, Any]:
    """Return a content-free public preflight and mint a bounded token."""

    _validate_inputs(candidate_id, action, expected_character_id, expected_namespace, expected_scope, operation_id, reason)
    root = _root(store_root, create=True)
    candidate = _load_candidate(root, candidate_id)
    existing = _read_decision(root, candidate_id)
    if existing is not None:
        return _project_existing(existing, candidate, action, operation_id, receipt=False)

    result = preflight_held_governance(
        action,
        candidate,
        expected_character_id=expected_character_id,
        expected_namespace=expected_namespace,
        expected_scope=expected_scope,
        store_root=store_root,
    )
    public = result.to_public_dict()
    if public["status"] != "ready":
        return _public_projection(
            schema=HELD_GOVERNANCE_PREFLIGHT_PUBLIC_SCHEMA,
            status=str(public["status"]),
            action=action,
            candidate_id=candidate_id,
            operation_id=operation_id,
            reason_code=str(public["reason_code"]),
            blocked_reasons=tuple(str(item) for item in public["blocked_reason_ids"]),
            read_only=True,
        ) | {"apply_token": None, "expires_at": None}

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=_TOKEN_TTL_SECONDS)).isoformat()
    token = _token_for(root, candidate, action, operation_id, expires_at)
    token_envelope = {
        "schema": HELD_GOVERNANCE_TOKEN_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": candidate_id,
        "action": action,
        "operation_id": operation_id,
        "candidate_digest": _digest(candidate),
        "source_evidence_digest": candidate["source_evidence_digest"],
        "reason_digest": _secret_digest(reason),
        "token_digest": _secret_digest(token),
        "issued_at": _now(),
        "expires_at": expires_at,
    }
    _write_json_atomic(_token_path(root, candidate_id, operation_id), token_envelope)
    return _public_projection(
        schema=HELD_GOVERNANCE_PREFLIGHT_PUBLIC_SCHEMA,
        status="ready",
        action=action,
        candidate_id=candidate_id,
        operation_id=operation_id,
        reason_code="ready",
        blocked_reasons=(),
        read_only=True,
    ) | {"apply_token": token, "expires_at": expires_at}


def apply_held_governance_decision(
    store_root: str | Path,
    *,
    candidate_id: str,
    action: str,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str = "primary_formation",
    operation_id: str,
    reason: str,
    apply_token: str,
) -> dict[str, Any]:
    """Converge one Apply or Discard decision to durable evidence."""

    _validate_inputs(candidate_id, action, expected_character_id, expected_namespace, expected_scope, operation_id, reason)
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > 8192 or any(ch in apply_token for ch in "\n\r\t"):
        raise HeldGovernanceRuntimeError("token_invalid")
    root = _root(store_root, create=True)
    candidate = _load_candidate(root, candidate_id)
    existing = _read_decision(root, candidate_id)
    if existing is not None:
        return _project_existing(existing, candidate, action, operation_id, receipt=True)

    token = _read_token(root, candidate_id, operation_id)
    if token is None:
        raise HeldGovernanceRuntimeError("preflight_required")
    if token.get("action") != action or token.get("operation_id") != operation_id:
        raise HeldGovernanceRuntimeError("token_invalid")
    if token.get("token_digest") != _secret_digest(apply_token):
        raise HeldGovernanceRuntimeError("token_invalid")
    if token.get("candidate_digest") != _digest(candidate):
        return _public_projection(
            schema=HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA,
            status="stale_candidate",
            action=action,
            candidate_id=candidate_id,
            operation_id=operation_id,
            reason_code="stale_candidate",
            blocked_reasons=("stale_candidate",),
            read_only=False,
            receipt=True,
            idempotent_replay=False,
            candidate_generation_stable=False,
        )
    if _parse_time(str(token.get("expires_at"))) < datetime.now(timezone.utc):
        raise HeldGovernanceRuntimeError("token_expired")

    result = preflight_held_governance(
        action,
        candidate,
        expected_character_id=expected_character_id,
        expected_namespace=expected_namespace,
        expected_scope=expected_scope,
        store_root=store_root,
    )
    if result.status != "ready":
        public = result.to_public_dict()
        return _public_projection(
            schema=HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA,
            status=str(public["status"]),
            action=action,
            candidate_id=candidate_id,
            operation_id=operation_id,
            reason_code=str(public["reason_code"]),
            blocked_reasons=tuple(str(item) for item in public["blocked_reason_ids"]),
            read_only=False,
            receipt=True,
            idempotent_replay=False,
            candidate_generation_stable=True,
        )

    decision = {
        "schema": HELD_GOVERNANCE_DECISION_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": candidate_id,
        "action": action,
        "status": _TERMINAL_BY_ACTION[action],
        "operation_id": operation_id,
        "candidate_digest": _digest(candidate),
        "source_evidence_digest": candidate["source_evidence_digest"],
        "reason_digest": _secret_digest(reason),
        "decided_at": _now(),
        "queue_state_mutated": False,
        "primary_mem_mutated": False,
        "worker_started": False,
        "scheduler_started": False,
        "automatic_retry_or_release": False,
    }
    stored = _write_decision_once(root, candidate_id, decision)
    if stored is not decision:
        return _project_existing(stored, candidate, action, operation_id, receipt=True)
    return _public_projection(
        schema=HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA,
        status=_TERMINAL_BY_ACTION[action],
        action=action,
        candidate_id=candidate_id,
        operation_id=operation_id,
        reason_code=_TERMINAL_BY_ACTION[action],
        blocked_reasons=(),
        read_only=False,
        receipt=True,
        idempotent_replay=False,
        candidate_generation_stable=True,
    )


def apply_held_candidate(store_root: str | Path, **kwargs: Any) -> dict[str, Any]:
    return apply_held_governance_decision(store_root, action="apply", **kwargs)


def discard_held_candidate(store_root: str | Path, **kwargs: Any) -> dict[str, Any]:
    return apply_held_governance_decision(store_root, action="discard", **kwargs)


def list_held_governance_history(store_root: str | Path, *, candidate_id: str) -> dict[str, Any]:
    if not _token(candidate_id):
        raise HeldGovernanceRuntimeError("invalid_request")
    root = _root(store_root, create=False)
    decision = _read_decision(root, candidate_id)
    items: list[dict[str, Any]] = []
    if decision is not None:
        items.append({
            "status": str(decision["status"]),
            "action": str(decision["action"]),
            "operation_id_short": _short(str(decision["operation_id"])),
            "decided_at": str(decision["decided_at"]),
            "reason_code": str(decision["status"]),
            "content_free": True,
            "runtime_private_evidence_omitted": True,
        })
    return {
        "schema": HELD_GOVERNANCE_HISTORY_PUBLIC_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "candidate_id_short": _short(candidate_id),
        "count": len(items),
        "items": items,
        "content_free": True,
        "runtime_private_evidence_omitted": True,
    }


def _project_existing(existing: Mapping[str, Any], candidate: Mapping[str, Any], action: str, operation_id: str, *, receipt: bool) -> dict[str, Any]:
    if existing.get("candidate_digest") != _digest(candidate):
        status = reason = "stale_candidate"
        stable = False
        replay = False
    elif existing.get("action") == action and existing.get("operation_id") == operation_id:
        status = _ALREADY_BY_ACTION[action]
        reason = status
        stable = True
        replay = True
    else:
        status = reason = "operation_conflict"
        stable = True
        replay = False
    return _public_projection(
        schema=HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA if receipt else HELD_GOVERNANCE_PREFLIGHT_PUBLIC_SCHEMA,
        status=status,
        action=action,
        candidate_id=str(existing.get("candidate_id", "unknown")),
        operation_id=operation_id,
        reason_code=reason,
        blocked_reasons=(reason,),
        read_only=not receipt,
        receipt=receipt,
        idempotent_replay=replay,
        candidate_generation_stable=stable,
    ) | ({} if receipt else {"apply_token": None, "expires_at": None})


def _public_projection(*, schema: str, status: str, action: str, candidate_id: str, operation_id: str, reason_code: str, blocked_reasons: tuple[str, ...], read_only: bool, receipt: bool = False, idempotent_replay: bool = False, candidate_generation_stable: bool = True) -> dict[str, Any]:
    effects = dict(PUBLIC_EFFECTS[action])
    value: dict[str, Any] = {
        "schema": schema,
        "status": status,
        "action": action,
        "read_only": read_only,
        "candidate_id_short": _short(candidate_id),
        "operation_id_short": _short(operation_id),
        "reason_code": reason_code,
        "blocked_reason_ids": [_reason(item) for item in blocked_reasons if _reason(item)],
        "effects": effects,
        "already_applied": status == "already_applied",
        "already_discarded": status == "already_discarded",
        "content_free": True,
        "runtime_private_evidence_omitted": True,
        "source_body_included": False,
        "model_output_included": False,
        "memory_content_included": False,
        "queue_payload_included": False,
        "primary_page_path_included": False,
        "store_root_included": False,
        "queue_root_included": False,
        "claim_token_included": False,
        "lease_owner_included": False,
        "raw_exception_included": False,
        "queue_state_mutated": False,
        "primary_mem_mutated": False,
        "worker_started": False,
        "scheduler_started": False,
        "automatic_retry_or_release": False,
    }
    if receipt:
        value["idempotent_replay"] = idempotent_replay
        value["candidate_generation_stable"] = candidate_generation_stable
    return value


def _as_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeldGovernanceRuntimeError("invalid_request")
    return dict(value)


def _validate_inputs(candidate_id: str, action: str, character_id: str, namespace: str, scope: str, operation_id: str, reason: str) -> None:
    if action not in _ACTIONS or not all(_token(item) for item in (candidate_id, character_id, namespace, operation_id)) or not _token(scope):
        raise HeldGovernanceRuntimeError("invalid_request")
    if not isinstance(reason, str) or not reason.strip() or reason != reason.strip() or len(reason) > 512 or any(ord(ch) < 32 or ch in "\u2028\u2029" for ch in reason):
        raise HeldGovernanceRuntimeError("invalid_request")


def _root(store_root: str | Path, *, create: bool) -> Path:
    if not isinstance(store_root, (str, Path)):
        raise HeldGovernanceRuntimeError("store_unavailable")
    base = Path(store_root)
    if base.is_symlink():
        raise HeldGovernanceRuntimeError("store_unavailable")
    if create:
        base.mkdir(parents=True, exist_ok=True)
    root = base / _STORE_DIR
    if create:
        for name in ("candidates", "tokens", "decisions"):
            (root / name).mkdir(parents=True, exist_ok=True)
    return root


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / "candidates" / f"{_hash(candidate_id)}.json"


def _token_path(root: Path, candidate_id: str, operation_id: str) -> Path:
    return root / "tokens" / f"{_hash(candidate_id + ':' + operation_id)}.json"


def _decision_path(root: Path, candidate_id: str) -> Path:
    return root / "decisions" / f"{_hash(candidate_id)}.json"


def _load_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    envelope = _read_json(_candidate_path(root, candidate_id))
    if envelope.get("schema") != HELD_GOVERNANCE_CANDIDATE_EVIDENCE_SCHEMA:
        raise HeldGovernanceRuntimeError("source_corrupt")
    candidate = envelope.get("candidate")
    if not isinstance(candidate, Mapping) or candidate.get("candidate_id") != candidate_id:
        raise HeldGovernanceRuntimeError("source_corrupt")
    return dict(candidate)


def _read_token(root: Path, candidate_id: str, operation_id: str) -> dict[str, Any] | None:
    path = _token_path(root, candidate_id, operation_id)
    if not path.exists():
        return None
    value = _read_json(path)
    if value.get("schema") != HELD_GOVERNANCE_TOKEN_SCHEMA:
        raise HeldGovernanceRuntimeError("source_corrupt")
    return value


def _read_decision(root: Path, candidate_id: str) -> dict[str, Any] | None:
    path = _decision_path(root, candidate_id)
    if not path.exists():
        return None
    value = _read_json(path)
    if value.get("schema") != HELD_GOVERNANCE_DECISION_SCHEMA:
        raise HeldGovernanceRuntimeError("source_corrupt")
    return value


def _write_decision_once(root: Path, candidate_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    path = _decision_path(root, candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(decision, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        stored = _read_decision(root, candidate_id)
        if stored is None:
            raise HeldGovernanceRuntimeError("response_lost")
        return stored
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return decision


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > _MAX_FILE_BYTES:
            raise HeldGovernanceRuntimeError("source_corrupt")
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HeldGovernanceRuntimeError("target_not_found") from None
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise HeldGovernanceRuntimeError("source_corrupt") from None
    if not isinstance(value, dict):
        raise HeldGovernanceRuntimeError("source_corrupt")
    return value


def _token(value: object) -> bool:
    return isinstance(value, str) and _TOKEN_RE.fullmatch(value) is not None


def _reason(value: object) -> str | None:
    return value if isinstance(value, str) and _REASON_RE.fullmatch(value) else None


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _digest(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _secret_digest(value: str) -> str:
    return _hash(value)


def _token_for(root: Path, candidate: Mapping[str, Any], action: str, operation_id: str, expires_at: str) -> str:
    seed = f"{root}:{candidate['candidate_id']}:{_digest(candidate)}:{action}:{operation_id}:{expires_at}"
    return _hash(seed)


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HeldGovernanceRuntimeError("token_invalid") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _short(value: str) -> str:
    return value if len(value) <= 24 else f"{value[:12]}...{value[-6:]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "HELD_GOVERNANCE_CANDIDATE_EVIDENCE_SCHEMA",
    "HELD_GOVERNANCE_DECISION_SCHEMA",
    "HELD_GOVERNANCE_HISTORY_PUBLIC_SCHEMA",
    "HELD_GOVERNANCE_PREFLIGHT_PUBLIC_SCHEMA",
    "HELD_GOVERNANCE_RECEIPT_PUBLIC_SCHEMA",
    "HELD_GOVERNANCE_TOKEN_SCHEMA",
    "HeldGovernanceRuntimeError",
    "apply_held_candidate",
    "apply_held_governance_decision",
    "discard_held_candidate",
    "list_held_governance_history",
    "persist_held_candidate_evidence",
    "preflight_held_governance_decision",
]
