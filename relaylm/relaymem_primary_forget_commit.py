"""Phase I-4C1 exact Forget prepare and hidden-successor commit boundary."""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import KIND_TARGET, is_sha256, stable_hash
from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_forget_artifact import (
    FORGET_PREPARED_SCHEMA,
    PrimaryForgetArtifactError,
    forget_operation_key,
    publish_forget_prepared,
    read_forget_prepared,
)
from .relaymem_primary_lifecycle_page import (
    build_hidden_primary_page_markdown,
    hidden_relative_path,
    verify_hidden_page_against_prepared,
)
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError,
    primary_memory_mutation_lock,
    reread_primary_memory_for_mutation,
)
from .relaymem_primary_page_candidate import (
    build_relaymem_primary_hidden_page_candidate,
)
from .relaymem_primary_page_writer import apply_relaymem_primary_page_write
from .relaymem_primary_write_preflight import (
    build_relaymem_primary_write_preflight_dry_run,
)
from .relaymem_primary_writer_handoff import (
    build_relaymem_primary_lifecycle_writer_handoff_preflight,
)

FORGET_COMMIT_RESULT_SCHEMA = "relaylm.mem.forget_hidden_commit_result.v0"
_ALLOWED_FAULTS = {
    None,
    "after_lock_before_revision_reread",
    "after_revision_claim_before_prepared",
    "after_prepared_publication",
    "before_hidden_successor_publication",
    "after_hidden_successor_publication_before_reread",
    "after_hidden_successor_reread_before_return",
}


@dataclass(frozen=True, repr=False)
class PrimaryForgetCommitResult:
    status: str
    prepared_new: bool
    prepared_existing: bool
    hidden_successor_published: bool
    hidden_successor_existing: bool
    lifecycle_state: str
    mutation_state: str
    retrieval_eligible: bool
    prior_revision: int
    result_revision: int
    recovery_required: bool
    _prepared: Mapping[str, Any] | None = field(default=None, repr=False)
    _receipt: Mapping[str, Any] | None = field(default=None, repr=False)

    @property
    def schema(self) -> str:
        return FORGET_COMMIT_RESULT_SCHEMA

    def __repr__(self) -> str:
        return (
            "PrimaryForgetCommitResult("
            f"status={self.status!r}, prepared_new={self.prepared_new!r}, "
            f"prepared_existing={self.prepared_existing!r}, "
            f"hidden_successor_published={self.hidden_successor_published!r}, "
            f"hidden_successor_existing={self.hidden_successor_existing!r}, "
            f"lifecycle_state={self.lifecycle_state!r}, "
            f"mutation_state={self.mutation_state!r}, "
            f"retrieval_eligible={self.retrieval_eligible!r}, "
            f"prior_revision={self.prior_revision!r}, "
            f"result_revision={self.result_revision!r}, "
            f"recovery_required={self.recovery_required!r})"
        )

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema": FORGET_COMMIT_RESULT_SCHEMA,
            "status": self.status,
            "prepared_new": self.prepared_new,
            "prepared_existing": self.prepared_existing,
            "hidden_successor_published": self.hidden_successor_published,
            "hidden_successor_existing": self.hidden_successor_existing,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "prior_revision": self.prior_revision,
            "result_revision": self.result_revision,
            "recovery_required": self.recovery_required,
            "content_included": False,
            "path_included": False,
            "identifier_included": False,
            "digest_included": False,
            "exception_included": False,
        }


def apply_primary_memory_forget_hidden_successor(
    *,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    expected_lifecycle_state: str = "active",
    reason: str,
    operation_id: str,
    apply_token: str,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> PrimaryForgetCommitResult:
    """Commit one exact immutable hidden successor and stop before M3f/M3g."""

    PrimaryForgetError = _forget_error_type()
    _validate_request(
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        expected_lifecycle_state=expected_lifecycle_state,
        reason=reason,
        operation_id=operation_id,
        apply_token=apply_token,
        fault_at=fault_at,
        error_type=PrimaryForgetError,
    )
    root = Path(store_root)
    operation_key = forget_operation_key(operation_id)
    token_digest = sha256(apply_token.encode("utf-8")).hexdigest()
    reason_digest = sha256(reason.encode("utf-8")).hexdigest()

    try:
        with primary_memory_mutation_lock(root, memory_id):
            _fault(fault_at, "after_lock_before_revision_reread", PrimaryForgetError)

            existing = read_forget_prepared(
                root,
                memory_id=memory_id,
                operation_key=operation_key,
            )
            if existing is not None:
                _validate_existing_prepare(
                    existing,
                    character_id=character_id,
                    namespace=namespace,
                    memory_id=memory_id,
                    expected_revision=expected_revision,
                    reason=reason,
                    reason_digest=reason_digest,
                    operation_id=operation_id,
                    token_digest=token_digest,
                    error_type=PrimaryForgetError,
                )
                if verify_hidden_page_against_prepared(root, prepared=existing):
                    return _hidden_result(
                        existing,
                        status="hidden_successor_existing",
                        prepared_new=False,
                        prepared_existing=True,
                        hidden_new=False,
                        hidden_existing=True,
                    )
                state = resolve_primary_current_state(
                    root,
                    namespace=namespace,
                    memory_id=memory_id,
                )
                if state.mutation_state == "corrupt":
                    raise PrimaryForgetError("target_corrupt")
                return PrimaryForgetCommitResult(
                    status="prepared_existing",
                    prepared_new=False,
                    prepared_existing=True,
                    hidden_successor_published=False,
                    hidden_successor_existing=False,
                    lifecycle_state="active",
                    mutation_state="prepared",
                    retrieval_eligible=False,
                    prior_revision=int(existing["prior_revision"]),
                    result_revision=int(existing["result_revision"]),
                    recovery_required=True,
                    _prepared=existing,
                )

            claims = _validate_and_decode_token(
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
                error_type=PrimaryForgetError,
            )
            binding_digest = _binding_digest(
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                physical_id=str(claims["current_physical_id"]),
                current_revision=expected_revision,
                reason_digest=reason_digest,
                operation_id=operation_id,
            )
            if claims.get("binding_digest") != binding_digest:
                raise PrimaryForgetError("token_invalid")
            try:
                current = reread_primary_memory_for_mutation(
                    root,
                    namespace=namespace,
                    memory_id=memory_id,
                    expected_revision=expected_revision,
                    expected_lifecycle_state="active",
                    operation_kind="forget",
                    operation_id=operation_id,
                    binding_digest=binding_digest,
                )
            except PrimaryMutationCoordinatorError as exc:
                raise PrimaryForgetError(_map_error(exc.code)) from exc
            if current.current_physical_id != claims["current_physical_id"]:
                raise PrimaryForgetError("stale_revision")
            _fault(
                fault_at,
                "after_revision_claim_before_prepared",
                PrimaryForgetError,
                code="failed",
            )

            prepared = _build_prepared(
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=expected_revision,
                reason=reason,
                reason_digest=reason_digest,
                operation_id=operation_id,
                operation_key=operation_key,
                binding_digest=binding_digest,
                token_digest=token_digest,
                claims=claims,
                current=current,
                prepared_at=_iso(_utc(now)),
            )
            publication = publish_forget_prepared(root, artifact=prepared)
            if publication != "new":
                raise PrimaryForgetError("operation_conflict")
            _fault(fault_at, "after_prepared_publication", PrimaryForgetError)
            _fault(fault_at, "before_hidden_successor_publication", PrimaryForgetError)

            receipt, hidden_existing = _publish_hidden(root, prepared, PrimaryForgetError)
            _fault(
                fault_at,
                "after_hidden_successor_publication_before_reread",
                PrimaryForgetError,
            )
            if not verify_hidden_page_against_prepared(root, prepared=prepared):
                raise PrimaryForgetError("publication_ambiguous")
            _fault(
                fault_at,
                "after_hidden_successor_reread_before_return",
                PrimaryForgetError,
            )
            return _hidden_result(
                prepared,
                status=(
                    "hidden_successor_existing"
                    if hidden_existing
                    else "hidden_successor_published"
                ),
                prepared_new=True,
                prepared_existing=False,
                hidden_new=not hidden_existing,
                hidden_existing=hidden_existing,
                receipt=receipt,
            )
    except PrimaryForgetError:
        raise
    except PrimaryForgetArtifactError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc
    except PrimaryCurrentStateError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc
    except PrimaryMutationCoordinatorError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc


def _publish_hidden(
    root: Path,
    prepared: Mapping[str, Any],
    error_type: type[RuntimeError],
) -> tuple[Mapping[str, Any], bool]:
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
    page_candidate = build_relaymem_primary_hidden_page_candidate(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        prepared_artifact=prepared,
    )
    if page_candidate.get("page_candidate_count") != 1:
        raise error_type("target_corrupt")
    handoff = build_relaymem_primary_lifecycle_writer_handoff_preflight(
        page_candidate_artifact=page_candidate,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    if handoff.get("handoff_count") != 1 or handoff.get("blocked_reasons"):
        raise error_type("publication_ambiguous")
    result = apply_relaymem_primary_page_write(
        writer_handoff_artifact=handoff,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    receipt = result.get("receipt")
    if not isinstance(receipt, Mapping):
        raise error_type("publication_ambiguous")
    new = (
        result.get("durability_confirmed") is True
        and result.get("status") == "applied"
        and result.get("page_applied") is True
    )
    existing = (
        result.get("status") == "already_applied"
        and result.get("idempotent_noop") is True
        and receipt.get("status") == "already_applied"
        and receipt.get("idempotent_noop") is True
    )
    if not new and not existing:
        raise error_type("publication_ambiguous")
    expected = {
        "idempotency_key": prepared["successor_physical_id"],
        "target_relative_path": prepared["successor_relative_path"],
        "page_digest": prepared["successor_expected_canonical_digest"],
        "namespace": prepared["namespace"],
        "lineage_fingerprint": prepared["lineage_fingerprint"],
        "updates_index": False,
        "updates_log": False,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise error_type("publication_ambiguous")
    if result.get("updates_index") is not False or result.get("updates_log") is not False:
        raise error_type("publication_ambiguous")
    return receipt, existing


def _build_prepared(
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    reason_digest: str,
    operation_id: str,
    operation_key: str,
    binding_digest: str,
    token_digest: str,
    claims: Mapping[str, Any],
    current: Any,
    prepared_at: str,
) -> dict[str, Any]:
    successor_candidate_id = stable_hash(
        (
            "relaymem-primary-forget-hidden-candidate-v0",
            memory_id,
            str(current.current_physical_id),
            str(expected_revision),
            str(expected_revision + 1),
            namespace,
            character_id,
            operation_key,
            binding_digest,
            "hidden",
            str(current.metadata["source_event_kind"]),
            str(current.metadata["memory_kind"]),
            str(current.metadata["lineage_fingerprint"]),
        )
    )
    successor_physical_id = stable_hash(
        (
            "relaymem-primary-write-preflight-v0",
            namespace,
            str(current.metadata["source_event_kind"]),
            str(current.metadata["lineage_fingerprint"]),
            successor_candidate_id,
            str(current.metadata["source_event_kind"]),
            "primary",
            str(current.metadata["memory_kind"]),
            "free_to_update",
        )
    )
    relative = hidden_relative_path(
        memory_kind=str(current.metadata["memory_kind"]),
        physical_id=successor_physical_id,
    )
    markdown = build_hidden_primary_page_markdown(
        memory_kind=str(current.metadata["memory_kind"]),
        source_event_kind=str(current.metadata["source_event_kind"]),
        namespace=namespace,
        lineage_fingerprint=str(current.metadata["lineage_fingerprint"]),
        successor_physical_id=successor_physical_id,
        memory_id=memory_id,
        revision=expected_revision + 1,
        prior_revision=expected_revision,
        prior_physical_id=str(current.current_physical_id),
        operation_key=operation_key,
        binding_digest=binding_digest,
    )
    successor_digest = sha256(markdown.encode("utf-8")).hexdigest()
    return {
        "schema_version": FORGET_PREPARED_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "operation_kind": "forget",
        "operation_id": operation_id,
        "operation_key": operation_key,
        "binding_digest": binding_digest,
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "result_revision": expected_revision + 1,
        "prior_lifecycle_state": "active",
        "result_lifecycle_state": "hidden",
        "prior_physical_id": str(current.current_physical_id),
        "successor_physical_id": successor_physical_id,
        "successor_candidate_id": successor_candidate_id,
        "successor_relative_path": relative,
        "prior_canonical_digest": str(current.page_digest),
        "successor_expected_canonical_digest": successor_digest,
        "source_event_kind": str(current.metadata["source_event_kind"]),
        "memory_kind": str(current.metadata["memory_kind"]),
        "lineage_fingerprint": str(current.metadata["lineage_fingerprint"]),
        "reason": reason,
        "reason_digest": reason_digest,
        "token_digest": token_digest,
        "requested_at": str(claims["issued_at"]),
        "prepared_at": prepared_at,
        "status": "prepared",
        "recovery_required": True,
    }


def _validate_existing_prepare(
    prepared: Mapping[str, Any],
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    reason_digest: str,
    operation_id: str,
    token_digest: str,
    error_type: type[RuntimeError],
) -> None:
    expected = {
        "schema_version": FORGET_PREPARED_SCHEMA,
        "operation_kind": "forget",
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "result_revision": expected_revision + 1,
        "prior_lifecycle_state": "active",
        "result_lifecycle_state": "hidden",
        "operation_id": operation_id,
        "reason": reason,
        "reason_digest": reason_digest,
        "token_digest": token_digest,
    }
    if any(prepared.get(key) != value for key, value in expected.items()):
        raise error_type("operation_conflict")


def _validate_and_decode_token(
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
    now: datetime | None,
    error_type: type[RuntimeError],
) -> dict[str, Any]:
    from .relaymem_primary_forget import validate_primary_memory_forget_token

    validate_primary_memory_forget_token(
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
    try:
        payload_part, signature_part = apply_token.split(".")
        _canonical_b64(payload_part)
        _canonical_b64(signature_part)
        payload = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4))
        claims = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        raise error_type("token_invalid") from None
    canonical = json.dumps(
        claims, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if not isinstance(claims, dict) or canonical != payload:
        raise error_type("token_invalid")
    return claims


def _binding_digest(
    *,
    character_id: str,
    namespace: str,
    memory_id: str,
    physical_id: str,
    current_revision: int,
    reason_digest: str,
    operation_id: str,
) -> str:
    value = {
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
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _hidden_result(
    prepared: Mapping[str, Any],
    *,
    status: str,
    prepared_new: bool,
    prepared_existing: bool,
    hidden_new: bool,
    hidden_existing: bool,
    receipt: Mapping[str, Any] | None = None,
) -> PrimaryForgetCommitResult:
    return PrimaryForgetCommitResult(
        status=status,
        prepared_new=prepared_new,
        prepared_existing=prepared_existing,
        hidden_successor_published=hidden_new,
        hidden_successor_existing=hidden_existing,
        lifecycle_state="hidden",
        mutation_state="recovery_required",
        retrieval_eligible=False,
        prior_revision=int(prepared["prior_revision"]),
        result_revision=int(prepared["result_revision"]),
        recovery_required=True,
        _prepared=prepared,
        _receipt=receipt,
    )


def _validate_request(
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
    fault_at: str | None,
    error_type: type[RuntimeError],
) -> None:
    if not isinstance(store_root, str) or not store_root or store_root != store_root.strip() or "\x00" in store_root:
        raise error_type("store_unavailable")
    for value in (character_id, namespace, operation_id):
        if not _bounded(value, 128, multiline=False):
            raise error_type("invalid_request")
    if not is_sha256(memory_id):
        raise error_type("target_not_found")
    if type(expected_revision) is not int or expected_revision < 1:
        raise error_type("invalid_request")
    if expected_lifecycle_state != "active":
        raise error_type("invalid_request")
    if not _bounded(reason, 512, multiline=True):
        raise error_type("invalid_request")
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > 8192:
        raise error_type("token_invalid")
    if fault_at not in _ALLOWED_FAULTS:
        raise error_type("invalid_request")


def _fault(
    selected: str | None,
    seam: str,
    error_type: type[RuntimeError],
    *,
    code: str = "reconciliation_required",
) -> None:
    if selected == seam:
        raise error_type(code)


def _canonical_b64(value: str) -> bytes:
    if not value or "=" in value or any(char.isspace() for char in value):
        raise ValueError("noncanonical")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value:
        raise ValueError("noncanonical")
    return raw


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _bounded(value: object, limit: int, *, multiline: bool) -> bool:
    return (
        isinstance(value, str)
        and value
        and value == value.strip()
        and len(value) <= limit
        and "\x00" not in value
        and all(ord(char) not in {0x2028, 0x2029} and not 0xD800 <= ord(char) <= 0xDFFF for char in value)
        and (multiline or not any(char in value for char in "\r\n\t"))
    )


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _map_error(code: str) -> str:
    return {
        "target_not_found": "target_not_found",
        "target_not_active": "target_not_active",
        "target_corrupt": "target_corrupt",
        "stale_revision": "stale_revision",
        "operation_conflict": "operation_conflict",
        "token_invalid": "token_invalid",
        "token_expired": "token_expired",
        "store_unavailable": "store_unavailable",
        "publication_ambiguous": "publication_ambiguous",
        "reconciliation_required": "reconciliation_required",
        "invalid_request": "invalid_request",
    }.get(code, "failed")


def _forget_error_type() -> type[RuntimeError]:
    from .relaymem_primary_forget import PrimaryForgetError

    return PrimaryForgetError


__all__ = [
    "FORGET_COMMIT_RESULT_SCHEMA",
    "PrimaryForgetCommitResult",
    "apply_primary_memory_forget_hidden_successor",
]
