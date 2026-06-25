"""Read-only Phase I-4B Primary MEM Forget contracts and token issuance."""
from __future__ import annotations

import base64
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    load_primary_current_target,
    resolve_primary_current_state,
)
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError,
    ensure_primary_memory_mutation_available,
)

PREFLIGHT_REQUEST_SCHEMA = "relaylm.lab.memory_forget_preflight_request.v0"
PREFLIGHT_RESPONSE_SCHEMA = "relaylm.lab.memory_forget_preflight.v0"
HISTORY_SCHEMA = "relaylm.lab.memory_forget_history.v0"
TOKEN_DOMAIN = "relaylm.primary_forget_apply_token.v0"

_MAX_REASON = 512
_MAX_OPERATION_ID = 128
_MAX_TITLE = 160
_MAX_SUMMARY = 512
_TOKEN_TTL = timedelta(minutes=5)
_TOKEN_SECRET = secrets.token_bytes(32)


class PrimaryForgetError(RuntimeError):
    """Bounded Forget failure safe for later API translation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def preflight_primary_memory_forget(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    expected_lifecycle_state: str,
    reason: str,
    operation_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one current active memory and issue a read-only apply token."""

    _validate_scope(character_id, namespace, memory_id, operation_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryForgetError("invalid_request")
    if (
        not isinstance(expected_lifecycle_state, str)
        or expected_lifecycle_state != "active"
    ):
        raise PrimaryForgetError("invalid_request")
    bounded_reason = _semantic_text(reason, _MAX_REASON)
    reason_digest = sha256(bounded_reason.encode("utf-8")).hexdigest()

    current = _resolve(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    if current.lifecycle_state != "active":
        raise PrimaryForgetError("target_not_active")
    if current.mutation_state == "corrupt":
        raise PrimaryForgetError("target_corrupt")
    if current.mutation_state != "none":
        raise PrimaryForgetError("operation_conflict")
    if (
        not current.controls_valid
        or not current.page_valid
        or not current.retrieval_eligible
    ):
        raise PrimaryForgetError("target_corrupt")

    binding_digest = _forget_binding_digest(
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=current.current_physical_id,
        current_revision=current.current_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
    )
    try:
        ensure_primary_memory_mutation_available(
            store_root,
            memory_id=memory_id,
            operation_kind="forget",
            operation_id=operation_id,
            binding_digest=binding_digest,
        )
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc

    target = _load_target(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    issued_at = _utc(now)
    expires_at = issued_at + _TOKEN_TTL
    claims = {
        "domain": TOKEN_DOMAIN,
        "version": 0,
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "current_physical_id": current.current_physical_id,
        "current_revision": current.current_revision,
        "current_lifecycle_state": "active",
        "target_revision": current.current_revision + 1,
        "target_lifecycle_state": "hidden",
        "reason_digest": reason_digest,
        "operation_id": operation_id,
        "binding_digest": binding_digest,
        "issued_at": _iso(issued_at),
        "expires_at": _iso(expires_at),
    }
    token = _encode_token(claims)
    return {
        "schema": PREFLIGHT_RESPONSE_SCHEMA,
        "status": "ready",
        "read_only": True,
        "memory_id": memory_id,
        "memory_title": _bounded(str(target["metadata"]["title"]), _MAX_TITLE),
        "bounded_summary": _bounded(
            str(target["metadata"]["summary"]), _MAX_SUMMARY
        ),
        "current_revision": current.current_revision,
        "current_lifecycle_state": "active",
        "target_revision": current.current_revision + 1,
        "target_lifecycle_state": "hidden",
        "effects": {
            "ordinary_retrieval_excluded": True,
            "relayctx_injection_excluded": True,
            "physical_deletion": False,
            "audit_evidence_retained": True,
            "historical_used_memory_unchanged": True,
        },
        "apply_token": token,
        "expires_at": _iso(expires_at),
    }


def validate_primary_memory_forget_token(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    expected_lifecycle_state: str,
    reason: str,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read-only exact token validation for the future I-4C apply boundary."""

    _validate_scope(character_id, namespace, memory_id, operation_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryForgetError("invalid_request")
    if expected_lifecycle_state != "active":
        raise PrimaryForgetError("invalid_request")
    if (
        not isinstance(apply_token, str)
        or not apply_token
        or len(apply_token) > 8192
    ):
        raise PrimaryForgetError("token_invalid")
    bounded_reason = _semantic_text(reason, _MAX_REASON)
    claims = _decode_token(apply_token)
    required = {
        "domain",
        "version",
        "character_id",
        "namespace",
        "memory_id",
        "current_physical_id",
        "current_revision",
        "current_lifecycle_state",
        "target_revision",
        "target_lifecycle_state",
        "reason_digest",
        "operation_id",
        "binding_digest",
        "issued_at",
        "expires_at",
    }
    if set(claims) != required:
        raise PrimaryForgetError("token_invalid")
    if claims.get("domain") != TOKEN_DOMAIN or claims.get("version") != 0:
        raise PrimaryForgetError("token_invalid")
    exact = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "current_revision": expected_revision,
        "current_lifecycle_state": "active",
        "target_revision": expected_revision + 1,
        "target_lifecycle_state": "hidden",
        "operation_id": operation_id,
    }
    if any(claims.get(key) != value for key, value in exact.items()):
        raise PrimaryForgetError("token_invalid")
    reason_digest = sha256(bounded_reason.encode("utf-8")).hexdigest()
    if claims.get("reason_digest") != reason_digest:
        raise PrimaryForgetError("token_invalid")
    if not is_sha256(claims.get("current_physical_id")):
        raise PrimaryForgetError("token_invalid")
    if not is_sha256(claims.get("binding_digest")):
        raise PrimaryForgetError("token_invalid")
    expected_binding = _forget_binding_digest(
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        physical_id=str(claims["current_physical_id"]),
        current_revision=expected_revision,
        reason_digest=reason_digest,
        operation_id=operation_id,
    )
    if not hmac.compare_digest(
        str(claims["binding_digest"]), expected_binding
    ):
        raise PrimaryForgetError("token_invalid")

    issued_at = _parse_time(claims.get("issued_at"))
    expires_at = _parse_time(claims.get("expires_at"))
    if expires_at - issued_at != _TOKEN_TTL:
        raise PrimaryForgetError("token_invalid")
    current_time = _utc(now)
    if current_time >= expires_at:
        raise PrimaryForgetError("token_expired")

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
        or current.current_physical_id != claims["current_physical_id"]
    ):
        raise PrimaryForgetError("stale_revision")
    try:
        ensure_primary_memory_mutation_available(
            store_root,
            memory_id=memory_id,
            operation_kind="forget",
            operation_id=operation_id,
            binding_digest=expected_binding,
        )
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc

    return {
        "valid": True,
        "domain": TOKEN_DOMAIN,
        "memory_id": memory_id,
        "current_revision": expected_revision,
        "target_revision": expected_revision + 1,
        "current_lifecycle_state": "active",
        "target_lifecycle_state": "hidden",
        "operation_id": operation_id,
        "expires_at": _iso(expires_at),
    }


def list_primary_memory_forget_history(
    *,
    store_root: str,
    namespace: str,
    memory_id: str,
) -> dict[str, Any]:
    """Return a valid bounded zero-item history until I-4C tombstones exist."""

    current = _resolve(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=None,
    )
    if current.mutation_state == "corrupt":
        raise PrimaryForgetError("target_corrupt")
    return {
        "schema": HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": current.current_revision,
        "current_lifecycle_state": current.lifecycle_state,
        "forget_count": 0,
        "items": [],
    }


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
        raise PrimaryForgetError(_map_error(exc.code)) from exc


def _load_target(
    store_root: str,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int,
) -> dict[str, Any]:
    try:
        return load_primary_current_target(
            store_root,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=expected_revision,
        )
    except PrimaryCurrentStateError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc


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
            raise PrimaryForgetError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryForgetError("target_not_found")


def _semantic_text(value: object, limit: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
        or "\x00" in value
        or any(ord(char) in {0x2028, 0x2029} for char in value)
    ):
        raise PrimaryForgetError("invalid_request")
    return value


def _forget_binding_digest(
    *,
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
                "domain": "relaylm.primary_forget_binding.v0",
                "character_id": character_id,
                "namespace": namespace,
                "memory_id": memory_id,
                "current_physical_id": physical_id,
                "current_revision": current_revision,
                "current_lifecycle_state": "active",
                "target_revision": current_revision + 1,
                "target_lifecycle_state": "hidden",
                "reason_digest": reason_digest,
                "operation_id": operation_id,
            }
        )
    ).hexdigest()


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
        raise PrimaryForgetError("token_invalid") from None
    expected = hmac.new(_TOKEN_SECRET, payload, sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise PrimaryForgetError("token_invalid")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PrimaryForgetError("token_invalid") from None
    if not isinstance(value, dict) or _canonical_json(value) != payload:
        raise PrimaryForgetError("token_invalid")
    return value


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise PrimaryForgetError("token_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PrimaryForgetError("token_invalid") from None
    if parsed.tzinfo is None:
        raise PrimaryForgetError("token_invalid")
    return parsed.astimezone(timezone.utc)


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any] | dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _bounded(value: str, maximum: int) -> str:
    return value if len(value) <= maximum else value[: maximum - 1] + "…"


def _map_error(code: str) -> str:
    return {
        "target_not_found": "target_not_found",
        "not_found_or_wrong_scope": "target_not_found",
        "target_corrupt": "target_corrupt",
        "store_unavailable": "store_unavailable",
        "stale_revision": "stale_revision",
        "target_not_active": "target_not_active",
        "operation_conflict": "operation_conflict",
        "invalid_request": "invalid_request",
    }.get(code, "target_corrupt")


__all__ = [
    "HISTORY_SCHEMA",
    "PREFLIGHT_REQUEST_SCHEMA",
    "PREFLIGHT_RESPONSE_SCHEMA",
    "TOKEN_DOMAIN",
    "PrimaryForgetError",
    "list_primary_memory_forget_history",
    "preflight_primary_memory_forget",
    "validate_primary_memory_forget_token",
]
