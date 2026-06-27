"""Read-only Phase I-5A Primary MEM Pin / Unpin contracts and tokens."""
from __future__ import annotations

import base64
import binascii
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError,
    ensure_primary_memory_mutation_available,
    inspect_primary_memory_operations,
)

PIN_PREFLIGHT_REQUEST_SCHEMA = "relaylm.lab.memory_pin_preflight_request.v0"
PIN_PREFLIGHT_RESPONSE_SCHEMA = "relaylm.lab.memory_pin_preflight.v0"
PIN_APPLY_REQUEST_SCHEMA = "relaylm.lab.memory_pin_apply_request.v0"
PIN_HISTORY_SCHEMA = "relaylm.lab.memory_pin_history.v0"
PIN_TOKEN_DOMAIN = "relaylm.primary_pin_apply_token.v0"

UNPIN_PREFLIGHT_REQUEST_SCHEMA = "relaylm.lab.memory_unpin_preflight_request.v0"
UNPIN_PREFLIGHT_RESPONSE_SCHEMA = "relaylm.lab.memory_unpin_preflight.v0"
UNPIN_APPLY_REQUEST_SCHEMA = "relaylm.lab.memory_unpin_apply_request.v0"
UNPIN_HISTORY_SCHEMA = "relaylm.lab.memory_unpin_history.v0"
UNPIN_TOKEN_DOMAIN = "relaylm.primary_unpin_apply_token.v0"

_MAX_REASON = 512
_MAX_OPERATION_ID = 128
_MAX_TOKEN = 8192
_TOKEN_TTL = timedelta(minutes=5)
_TOKEN_SECRET = secrets.token_bytes(32)

_EFFECTS_BY_KIND: dict[str, dict[str, bool]] = {
    "pin": {
        "ordinary_retrieval_deleted": False,
        "ordinary_retrieval_excluded": False,
        "future_priority_hint_contract": True,
        "semantic_content_changed": False,
        "physical_deletion": False,
        "audit_evidence_retained": True,
    },
    "unpin": {
        "ordinary_retrieval_deleted": False,
        "ordinary_retrieval_excluded": False,
        "future_priority_hint_removed_contract": True,
        "semantic_content_changed": False,
        "physical_deletion": False,
        "audit_evidence_retained": True,
    },
}


class PrimaryPinError(RuntimeError):
    """Bounded Pin / Unpin failure safe for later API translation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def preflight_primary_memory_pin(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one current active memory and issue a read-only Pin token."""

    return _preflight_primary_memory_pin_operation(
        operation_kind="pin",
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        reason=reason,
        operation_id=operation_id,
        now=now,
    )


def preflight_primary_memory_unpin(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one current active memory and issue a read-only Unpin token."""

    return _preflight_primary_memory_pin_operation(
        operation_kind="unpin",
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        reason=reason,
        operation_id=operation_id,
        now=now,
    )


def validate_primary_memory_pin_token(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read-only exact Pin token validation for a future apply boundary."""

    return _validate_primary_memory_pin_operation_token(
        operation_kind="pin",
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        reason=reason,
        operation_id=operation_id,
        apply_token=apply_token,
        now=now,
    )


def validate_primary_memory_unpin_token(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read-only exact Unpin token validation for a future apply boundary."""

    return _validate_primary_memory_pin_operation_token(
        operation_kind="unpin",
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        reason=reason,
        operation_id=operation_id,
        apply_token=apply_token,
        now=now,
    )


def list_primary_memory_pin_history(
    *,
    store_root: str,
    namespace: str,
    memory_id: str,
) -> dict[str, Any]:
    """Return a bounded zero-item Pin history until apply artifacts exist."""

    return _list_primary_memory_pin_operation_history(
        operation_kind="pin",
        store_root=store_root,
        namespace=namespace,
        memory_id=memory_id,
    )


def list_primary_memory_unpin_history(
    *,
    store_root: str,
    namespace: str,
    memory_id: str,
) -> dict[str, Any]:
    """Return a bounded zero-item Unpin history until apply artifacts exist."""

    return _list_primary_memory_pin_operation_history(
        operation_kind="unpin",
        store_root=store_root,
        namespace=namespace,
        memory_id=memory_id,
    )


def _preflight_primary_memory_pin_operation(
    *,
    operation_kind: str,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    now: datetime | None,
) -> dict[str, Any]:
    _validate_operation_kind(operation_kind)
    _validate_scope(character_id, namespace, memory_id, operation_id)
    _validate_revision(expected_revision)
    bounded_reason = _semantic_text(reason, _MAX_REASON)
    reason_digest = sha256(bounded_reason.encode("utf-8")).hexdigest()

    current = _resolve(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    _require_active_none_target(current)
    binding_digest = _binding_digest(
        operation_kind=operation_kind,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=current.current_physical_id,
        current_revision=current.current_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
    )
    try:
        _ensure_pin_unpin_fence(
            store_root,
            memory_id=memory_id,
            operation_kind=operation_kind,
            operation_id=operation_id,
            binding_digest=binding_digest,
        )
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryPinError(_map_error(exc.code)) from exc

    issued_at = _utc(now)
    expires_at = issued_at + _TOKEN_TTL
    public_claims = {
        "domain": _token_domain(operation_kind),
        "version": 0,
        "issued_at": _iso(issued_at),
        "expires_at": _iso(expires_at),
        "nonce": secrets.token_urlsafe(24),
    }
    private_claims = _private_claims(
        operation_kind=operation_kind,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=current.current_physical_id,
        current_revision=current.current_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
        binding_digest=binding_digest,
    )
    token = _encode_token(public_claims, private_claims)
    return {
        "schema": _preflight_schema(operation_kind),
        "status": "ready",
        "operation_kind": operation_kind,
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": current.current_revision,
        "current_lifecycle_state": "active",
        "current_mutation_state": "none",
        "current_pin_state": _prior_pin_state(operation_kind),
        "target_pin_state": _target_pin_state(operation_kind),
        "pin_state_contract_only": True,
        "effects": dict(_EFFECTS_BY_KIND[operation_kind]),
        "apply_token": token,
        "expires_at": _iso(expires_at),
    }


def _validate_primary_memory_pin_operation_token(
    *,
    operation_kind: str,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    operation_id: str,
    apply_token: str,
    now: datetime | None,
) -> dict[str, Any]:
    _validate_operation_kind(operation_kind)
    _validate_scope(character_id, namespace, memory_id, operation_id)
    _validate_revision(expected_revision)
    bounded_reason = _semantic_text(reason, _MAX_REASON)
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > _MAX_TOKEN:
        raise PrimaryPinError("token_invalid")

    public_claims = _decode_public_claims(apply_token)
    required_public = {"domain", "version", "issued_at", "expires_at", "nonce"}
    if set(public_claims) != required_public:
        raise PrimaryPinError("token_invalid")
    if public_claims.get("domain") != _token_domain(operation_kind):
        raise PrimaryPinError("token_invalid")
    if public_claims.get("version") != 0:
        raise PrimaryPinError("token_invalid")
    nonce = public_claims.get("nonce")
    if (
        not isinstance(nonce, str)
        or not nonce
        or len(nonce) > 96
        or any(char.isspace() for char in nonce)
    ):
        raise PrimaryPinError("token_invalid")

    issued_at = _parse_time(public_claims.get("issued_at"))
    expires_at = _parse_time(public_claims.get("expires_at"))
    if expires_at - issued_at != _TOKEN_TTL:
        raise PrimaryPinError("token_invalid")
    if _utc(now) >= expires_at:
        raise PrimaryPinError("token_expired")

    current = _resolve(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    if (
        current.lifecycle_state != "active"
        or current.mutation_state != "none"
        or not current.controls_valid
        or not current.page_valid
    ):
        raise PrimaryPinError("stale_revision")

    reason_digest = sha256(bounded_reason.encode("utf-8")).hexdigest()
    binding_digest = _binding_digest(
        operation_kind=operation_kind,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=current.current_physical_id,
        current_revision=current.current_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
    )
    private_claims = _private_claims(
        operation_kind=operation_kind,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=current.current_physical_id,
        current_revision=current.current_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
        binding_digest=binding_digest,
    )
    _verify_token_signature(apply_token, public_claims, private_claims)
    try:
        _ensure_pin_unpin_fence(
            store_root,
            memory_id=memory_id,
            operation_kind=operation_kind,
            operation_id=operation_id,
            binding_digest=binding_digest,
        )
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryPinError(_map_error(exc.code)) from exc

    return {
        "valid": True,
        "domain": _token_domain(operation_kind),
        "operation_kind": operation_kind,
        "memory_id": memory_id,
        "current_revision": expected_revision,
        "current_lifecycle_state": "active",
        "current_mutation_state": "none",
        "current_pin_state": _prior_pin_state(operation_kind),
        "target_pin_state": _target_pin_state(operation_kind),
        "pin_state_contract_only": True,
        "operation_id": operation_id,
        "expires_at": _iso(expires_at),
    }


def _list_primary_memory_pin_operation_history(
    *,
    operation_kind: str,
    store_root: str,
    namespace: str,
    memory_id: str,
) -> dict[str, Any]:
    _validate_operation_kind(operation_kind)
    if not isinstance(namespace, str) or not namespace or namespace != namespace.strip():
        raise PrimaryPinError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryPinError("target_not_found")
    current = _resolve(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=None,
    )
    if current.mutation_state == "corrupt" or not current.controls_valid or not current.page_valid:
        raise PrimaryPinError("target_corrupt")
    count_name = "pin_count" if operation_kind == "pin" else "unpin_count"
    return {
        "schema": PIN_HISTORY_SCHEMA if operation_kind == "pin" else UNPIN_HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": current.current_revision,
        "current_lifecycle_state": current.lifecycle_state,
        "pin_state_contract_only": True,
        count_name: 0,
        "items": [],
    }


def _ensure_pin_unpin_fence(
    store_root: str,
    *,
    memory_id: str,
    operation_kind: str,
    operation_id: str,
    binding_digest: str,
) -> str:
    try:
        return ensure_primary_memory_mutation_available(
            store_root,
            memory_id=memory_id,
            operation_kind=operation_kind,
            operation_id=operation_id,
            binding_digest=binding_digest,
        )
    except PrimaryMutationCoordinatorError as exc:
        if exc.code != "invalid_request":
            raise

    inspection = inspect_primary_memory_operations(store_root, memory_id=memory_id)
    if inspection.corrupt:
        raise PrimaryMutationCoordinatorError("target_corrupt")
    for operation in inspection.operations:
        if operation.operation_id == operation_id:
            raise PrimaryMutationCoordinatorError("operation_conflict")
    if inspection.pending:
        raise PrimaryMutationCoordinatorError("operation_conflict")
    return "absent"


def _resolve(
    store_root: str,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int | None,
):
    try:
        return resolve_primary_current_state(
            store_root,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=expected_revision,
        )
    except PrimaryCurrentStateError as exc:
        raise PrimaryPinError(_map_error(exc.code)) from exc


def _require_active_none_target(current: Any) -> None:
    if current.lifecycle_state != "active":
        raise PrimaryPinError("target_not_active")
    if current.mutation_state == "corrupt" or not current.controls_valid or not current.page_valid:
        raise PrimaryPinError("target_corrupt")
    if current.mutation_state == "recovery_required":
        raise PrimaryPinError("recovery_required")
    if current.mutation_state != "none":
        raise PrimaryPinError("operation_conflict")
    if not current.retrieval_eligible:
        raise PrimaryPinError("target_corrupt")


def _validate_operation_kind(operation_kind: str) -> None:
    if operation_kind not in {"pin", "unpin"}:
        raise PrimaryPinError("invalid_request")


def _validate_scope(
    character_id: str, namespace: str, memory_id: str, operation_id: str
) -> None:
    for value in (character_id, namespace, operation_id):
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value) > _MAX_OPERATION_ID
            or "\x00" in value
            or any(char in value for char in "\r\n\t")
        ):
            raise PrimaryPinError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryPinError("target_not_found")


def _validate_revision(expected_revision: int) -> None:
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryPinError("invalid_request")


def _semantic_text(value: object, limit: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
        or "\x00" in value
        or any(ord(char) in {0x2028, 0x2029} for char in value)
    ):
        raise PrimaryPinError("invalid_request")
    return value


def _binding_digest(
    *,
    operation_kind: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    physical_id: str,
    current_revision: int,
    reason_digest: str,
    operation_id: str,
) -> str:
    return sha256(
        _canonical_json(
            {
                "domain": f"relaylm.primary_{operation_kind}_binding.v0",
                "operation_kind": operation_kind,
                "character_id": character_id,
                "namespace": namespace,
                "memory_id": memory_id,
                "current_physical_id": physical_id,
                "current_revision": current_revision,
                "current_lifecycle_state": "active",
                "current_mutation_state": "none",
                "current_pin_state": _prior_pin_state(operation_kind),
                "target_pin_state": _target_pin_state(operation_kind),
                "reason_digest": reason_digest,
                "operation_id": operation_id,
            }
        )
    ).hexdigest()


def _private_claims(
    *,
    operation_kind: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    physical_id: str,
    current_revision: int,
    reason_digest: str,
    operation_id: str,
    binding_digest: str,
) -> dict[str, Any]:
    return {
        "operation_kind": operation_kind,
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "current_physical_id": physical_id,
        "current_revision": current_revision,
        "current_lifecycle_state": "active",
        "current_mutation_state": "none",
        "current_pin_state": _prior_pin_state(operation_kind),
        "target_pin_state": _target_pin_state(operation_kind),
        "reason_digest": reason_digest,
        "operation_id": operation_id,
        "binding_digest": binding_digest,
    }


def _encode_token(public_claims: Mapping[str, Any], private_claims: Mapping[str, Any]) -> str:
    payload = _canonical_json(dict(public_claims))
    signature = hmac.new(
        _TOKEN_SECRET,
        _canonical_json({"public": dict(public_claims), "private": dict(private_claims)}),
        sha256,
    ).digest()
    return f"{_b64(payload)}.{_b64(signature)}"


def _decode_public_claims(token: str) -> dict[str, Any]:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        raise PrimaryPinError("token_invalid") from None
    _require_canonical_base64url(payload_part)
    _require_canonical_base64url(signature_part)
    try:
        payload = _unb64(payload_part)
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        raise PrimaryPinError("token_invalid") from None
    if not isinstance(value, dict) or _canonical_json(value) != payload:
        raise PrimaryPinError("token_invalid")
    return value


def _verify_token_signature(
    token: str, public_claims: Mapping[str, Any], private_claims: Mapping[str, Any]
) -> None:
    try:
        payload_part, signature_part = token.split(".", 1)
        signature = _unb64(signature_part)
    except (ValueError, binascii.Error):
        raise PrimaryPinError("token_invalid") from None
    expected = hmac.new(
        _TOKEN_SECRET,
        _canonical_json({"public": dict(public_claims), "private": dict(private_claims)}),
        sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise PrimaryPinError("token_invalid")
    if payload_part != _b64(_canonical_json(dict(public_claims))):
        raise PrimaryPinError("token_invalid")


def _require_canonical_base64url(part: str) -> None:
    if not part or "=" in part or any(char.isspace() for char in part):
        raise PrimaryPinError("token_invalid")
    try:
        raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    except (ValueError, binascii.Error):
        raise PrimaryPinError("token_invalid") from None
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != part:
        raise PrimaryPinError("token_invalid")


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise PrimaryPinError("token_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PrimaryPinError("token_invalid") from None
    if parsed.tzinfo is None:
        raise PrimaryPinError("token_invalid")
    return parsed.astimezone(timezone.utc)


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _preflight_schema(operation_kind: str) -> str:
    return PIN_PREFLIGHT_RESPONSE_SCHEMA if operation_kind == "pin" else UNPIN_PREFLIGHT_RESPONSE_SCHEMA


def _token_domain(operation_kind: str) -> str:
    return PIN_TOKEN_DOMAIN if operation_kind == "pin" else UNPIN_TOKEN_DOMAIN


def _prior_pin_state(operation_kind: str) -> str:
    return "unpinned" if operation_kind == "pin" else "pinned"


def _target_pin_state(operation_kind: str) -> str:
    return "pinned" if operation_kind == "pin" else "unpinned"


def _map_error(code: str) -> str:
    return {
        "target_not_found": "target_not_found",
        "not_found_or_wrong_scope": "target_not_found",
        "target_corrupt": "target_corrupt",
        "store_unavailable": "store_unavailable",
        "stale_revision": "stale_revision",
        "target_not_active": "target_not_active",
        "operation_conflict": "operation_conflict",
        "recovery_required": "recovery_required",
        "invalid_request": "invalid_request",
    }.get(code, "target_corrupt")


__all__ = [
    "PIN_APPLY_REQUEST_SCHEMA",
    "PIN_HISTORY_SCHEMA",
    "PIN_PREFLIGHT_REQUEST_SCHEMA",
    "PIN_PREFLIGHT_RESPONSE_SCHEMA",
    "PIN_TOKEN_DOMAIN",
    "UNPIN_APPLY_REQUEST_SCHEMA",
    "UNPIN_HISTORY_SCHEMA",
    "UNPIN_PREFLIGHT_REQUEST_SCHEMA",
    "UNPIN_PREFLIGHT_RESPONSE_SCHEMA",
    "UNPIN_TOKEN_DOMAIN",
    "PrimaryPinError",
    "list_primary_memory_pin_history",
    "list_primary_memory_unpin_history",
    "preflight_primary_memory_pin",
    "preflight_primary_memory_unpin",
    "validate_primary_memory_pin_token",
    "validate_primary_memory_unpin_token",
]
