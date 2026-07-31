"""Validation and token ownership for Primary correction."""
from __future__ import annotations
import base64, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping
from ._relaymem_primary_page_writer_common import MAX_SUMMARY, MAX_TITLE, bad_text, is_sha256

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
_TOKEN_SECRET = secrets.token_bytes(32)

class PreflightDependencies:
    def __init__(self, *, load_state: Callable[..., Any], load_target: Callable[..., dict[str, Any]]):
        self.load_state = load_state
        self.load_target = load_target



class PrimaryCorrectionError(RuntimeError):
    """Bounded correction failure safe for API mapping."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


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
    _dependencies: PreflightDependencies,
) -> dict[str, Any]:
    """Validate one real formed Primary MEM and issue a short-lived opaque token."""

    _validate_scope_tokens(character_id, namespace, memory_id, operation_id)
    title = _semantic_text(corrected_title, MAX_TITLE, allow_empty=True)
    summary = _semantic_text(corrected_summary, MAX_SUMMARY, allow_empty=False)
    bounded_reason = _semantic_text(reason, _MAX_REASON, allow_empty=False)
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryCorrectionError("invalid_request")

    root = _safe_store_root(store_root)
    state = _dependencies.load_state(root, namespace=namespace)
    target = _dependencies.load_target(
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


def _safe_store_root(value: str) -> Path:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise PrimaryCorrectionError("store_unavailable")
    root = Path(value)
    if _path_has_symlink(root):
        raise PrimaryCorrectionError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryCorrectionError("store_unavailable")
    return root


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _shared_error_code(code: str) -> str:
    return {
        "target_not_found": "not_found_or_wrong_scope",
        "target_not_active": "target_not_active",
        "target_corrupt": "target_corrupt",
        "stale_revision": "stale_revision",
        "operation_conflict": "operation_conflict",
        "store_unavailable": "store_unavailable",
        "invalid_request": "invalid_request",
    }.get(code, "target_corrupt")


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
