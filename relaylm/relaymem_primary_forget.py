"""Public Phase I-4B Forget boundary with canonical token encoding checks."""
from __future__ import annotations

import base64
import binascii
from datetime import datetime

from . import _relaymem_primary_forget_impl as _impl

PREFLIGHT_REQUEST_SCHEMA = _impl.PREFLIGHT_REQUEST_SCHEMA
PREFLIGHT_RESPONSE_SCHEMA = _impl.PREFLIGHT_RESPONSE_SCHEMA
HISTORY_SCHEMA = _impl.HISTORY_SCHEMA
TOKEN_DOMAIN = _impl.TOKEN_DOMAIN
PrimaryForgetError = _impl.PrimaryForgetError
preflight_primary_memory_forget = _impl.preflight_primary_memory_forget
list_primary_memory_forget_history = _impl.list_primary_memory_forget_history


def _require_canonical_base64url(part: str) -> None:
    if not part or "=" in part or any(char.isspace() for char in part):
        raise PrimaryForgetError("token_invalid")
    try:
        raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    except (ValueError, binascii.Error):
        raise PrimaryForgetError("token_invalid") from None
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if canonical != part:
        raise PrimaryForgetError("token_invalid")


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
):
    """Validate exact Forget token claims and require canonical base64url form."""

    if not isinstance(apply_token, str):
        raise PrimaryForgetError("token_invalid")
    try:
        payload_part, signature_part = apply_token.split(".")
    except ValueError:
        raise PrimaryForgetError("token_invalid") from None
    _require_canonical_base64url(payload_part)
    _require_canonical_base64url(signature_part)
    return _impl.validate_primary_memory_forget_token(
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        expected_lifecycle_state=expected_lifecycle_state,
        reason=reason,
        operation_id=operation_id,
        apply_token=apply_token,
        now=now,
    )


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
