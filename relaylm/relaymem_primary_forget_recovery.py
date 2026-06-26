"""Phase I-4C2 exact Forget recovery, convergence, and finalization."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from ._relaymem_primary_forget_impl import PrimaryForgetError
from ._relaymem_primary_index_log_apply_io import apply_or_inspect_reconciliation
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_current_state import resolve_primary_current_state
from .relaymem_primary_forget_artifact import (
    PrimaryForgetArtifactError,
    forget_operation_key,
    read_forget_prepared,
)
from .relaymem_primary_forget_commit import apply_primary_memory_forget_hidden_successor
from .relaymem_primary_forget_control_convergence import (
    PrimaryForgetControlConvergenceError,
    build_hidden_control_reconciliation_plan,
    controls_are_exactly_converged,
    converge_hidden_primary_controls,
)
from .relaymem_primary_forget_finalization_artifact import (
    build_forget_tombstone,
    publish_forget_tombstone,
    read_forget_tombstone,
    tombstone_matches_prepared,
)
from .relaymem_primary_forget_hidden_resume import (
    PrimaryForgetHiddenResumeError,
    resume_prepared_forget_hidden_successor_locked,
)
from .relaymem_primary_lifecycle_page import (
    resolve_forget_current_state,
    verify_hidden_page_against_prepared,
)
from .relaymem_primary_mutation_coordinator import (
    PrimaryMutationCoordinatorError,
    primary_memory_mutation_lock,
)

FORGET_APPLY_RESULT_SCHEMA = "relaylm.mem.forget_apply_result.v0"
FORGET_RECOVERY_RESULT_SCHEMA = "relaylm.mem.forget_recovery_result.v0"

_ALLOWED_FAULTS = {
    None,
    "after_lock_before_operation_reread",
    "after_prepared_reread_before_hidden_resume",
    "after_hidden_successor_publish_before_reread",
    "after_hidden_reread_before_m3f",
    "after_m3f_plan_before_m3g",
    "after_m3g_index_before_log",
    "after_m3g_before_control_reread",
    "after_controls_reread_before_tombstone",
    "during_tombstone_publish",
    "after_tombstone_publish_before_reread",
    "after_tombstone_reread_before_applied_receipt",
    "after_finalization_before_return",
}


@dataclass(frozen=True, repr=False)
class _PrimaryForgetResult:
    status: str
    prepared_present: bool
    hidden_successor_present: bool
    page_converged: bool
    index_converged: bool
    log_converged: bool
    tombstone_present: bool
    tombstone_created: bool
    applied_receipt_present: bool
    idempotent_replay: bool
    lifecycle_state: str
    mutation_state: str
    retrieval_eligible: bool
    prior_revision: int
    result_revision: int
    recovery_required: bool
    reason_ids: tuple[str, ...]
    _tombstone: Mapping[str, Any] | None = field(default=None, repr=False)

    @property
    def schema(self) -> str:
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"status={self.status!r}, "
            f"prepared_present={self.prepared_present!r}, "
            f"hidden_successor_present={self.hidden_successor_present!r}, "
            f"page_converged={self.page_converged!r}, "
            f"index_converged={self.index_converged!r}, "
            f"log_converged={self.log_converged!r}, "
            f"tombstone_present={self.tombstone_present!r}, "
            f"tombstone_created={self.tombstone_created!r}, "
            f"applied_receipt_present={self.applied_receipt_present!r}, "
            f"idempotent_replay={self.idempotent_replay!r}, "
            f"lifecycle_state={self.lifecycle_state!r}, "
            f"mutation_state={self.mutation_state!r}, "
            f"retrieval_eligible={self.retrieval_eligible!r}, "
            f"prior_revision={self.prior_revision!r}, "
            f"result_revision={self.result_revision!r}, "
            f"recovery_required={self.recovery_required!r}, "
            f"reason_ids={self.reason_ids!r})"
        )

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "prepared_present": self.prepared_present,
            "hidden_successor_present": self.hidden_successor_present,
            "page_converged": self.page_converged,
            "index_converged": self.index_converged,
            "log_converged": self.log_converged,
            "tombstone_present": self.tombstone_present,
            "tombstone_created": self.tombstone_created,
            "applied_receipt_present": self.applied_receipt_present,
            "idempotent_replay": self.idempotent_replay,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "prior_revision": self.prior_revision,
            "result_revision": self.result_revision,
            "recovery_required": self.recovery_required,
            "reason_ids": list(self.reason_ids),
            "content_included": False,
            "path_included": False,
            "identifier_included": False,
            "digest_included": False,
            "timestamp_included": False,
            "exception_included": False,
        }


@dataclass(frozen=True, repr=False)
class PrimaryForgetApplyResult(_PrimaryForgetResult):
    @property
    def schema(self) -> str:
        return FORGET_APPLY_RESULT_SCHEMA


@dataclass(frozen=True, repr=False)
class PrimaryForgetRecoveryResult(_PrimaryForgetResult):
    @property
    def schema(self) -> str:
        return FORGET_RECOVERY_RESULT_SCHEMA


def apply_primary_memory_forget(
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
    fault_at: str | None = None,
) -> PrimaryForgetApplyResult:
    """Apply or exactly replay one Forget operation through tombstone finalization."""

    _validate_apply_request(
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
    )
    root = Path(store_root)
    operation_key = _operation_key(operation_id)
    token_digest = sha256(apply_token.encode("utf-8")).hexdigest()
    reason_digest = sha256(reason.encode("utf-8")).hexdigest()

    try:
        with primary_memory_mutation_lock(root, memory_id):
            _fault(fault_at, "after_lock_before_operation_reread")
            tombstone = read_forget_tombstone(
                root, memory_id=memory_id, operation_key=operation_key
            )
            prepared = read_forget_prepared(
                root, memory_id=memory_id, operation_key=operation_key
            )
            if tombstone is not None:
                _validate_external_tombstone_replay(
                    tombstone,
                    prepared=prepared,
                    character_id=character_id,
                    namespace=namespace,
                    memory_id=memory_id,
                    expected_revision=expected_revision,
                    reason=reason,
                    reason_digest=reason_digest,
                    operation_id=operation_id,
                    token_digest=token_digest,
                    root=root,
                )
                return _apply_result_from_tombstone(
                    tombstone, idempotent_replay=True, tombstone_created=False
                )
            if prepared is not None:
                _validate_external_prepared_replay(
                    prepared,
                    character_id=character_id,
                    namespace=namespace,
                    memory_id=memory_id,
                    expected_revision=expected_revision,
                    reason=reason,
                    reason_digest=reason_digest,
                    operation_id=operation_id,
                    token_digest=token_digest,
                )
                _fault(fault_at, "after_prepared_reread_before_hidden_resume")
                return _finalize_locked(
                    root,
                    prepared=prepared,
                    result_type=PrimaryForgetApplyResult,
                    now=now,
                    fault_at=fault_at,
                )

        # No durable operation exists for this exact key.  The completed I-4C1
        # boundary performs live-token validation and the shared revision claim
        # under the same canonical lock.  Releasing and reacquiring here cannot
        # create a second winner because I-4C1 owns the no-clobber prepare commit.
        i4c1_fault = (
            "after_hidden_successor_publication_before_reread"
            if fault_at == "after_hidden_successor_publish_before_reread"
            else None
        )
        try:
            apply_primary_memory_forget_hidden_successor(
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
                fault_at=i4c1_fault,
            )
        except PrimaryForgetError as exc:
            if exc.code in {"target_not_active", "operation_conflict"}:
                state = resolve_primary_current_state(
                    root, namespace=namespace, memory_id=memory_id
                )
                if state.lifecycle_state == "hidden" and state.mutation_state == "none":
                    return _already_hidden_apply_result(
                        expected_revision=expected_revision,
                        result_revision=state.current_revision,
                    )
            raise

        with primary_memory_mutation_lock(root, memory_id):
            prepared = read_forget_prepared(
                root, memory_id=memory_id, operation_key=operation_key
            )
            if prepared is None:
                raise PrimaryForgetError("reconciliation_required")
            _validate_external_prepared_replay(
                prepared,
                character_id=character_id,
                namespace=namespace,
                memory_id=memory_id,
                expected_revision=expected_revision,
                reason=reason,
                reason_digest=reason_digest,
                operation_id=operation_id,
                token_digest=token_digest,
            )
            return _finalize_locked(
                root,
                prepared=prepared,
                result_type=PrimaryForgetApplyResult,
                now=now,
                fault_at=fault_at,
            )
    except PrimaryForgetError:
        raise
    except (
        PrimaryForgetArtifactError,
        PrimaryMutationCoordinatorError,
        PrimaryForgetHiddenResumeError,
        PrimaryForgetControlConvergenceError,
    ) as exc:
        raise PrimaryForgetError(_map_error(getattr(exc, "code", "failed"))) from exc
    except OSError as exc:
        raise PrimaryForgetError("store_unavailable") from exc


def recover_primary_memory_forget(
    *,
    store_root: str,
    namespace: str,
    memory_id: str,
    operation_id: str,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> PrimaryForgetRecoveryResult:
    """Recover one caller-selected durable Forget operation; never scan a directory."""

    _validate_recovery_request(
        store_root=store_root,
        namespace=namespace,
        memory_id=memory_id,
        operation_id=operation_id,
        fault_at=fault_at,
    )
    root = Path(store_root)
    operation_key = _operation_key(operation_id)
    try:
        with primary_memory_mutation_lock(root, memory_id):
            _fault(fault_at, "after_lock_before_operation_reread")
            tombstone = read_forget_tombstone(
                root, memory_id=memory_id, operation_key=operation_key
            )
            prepared = read_forget_prepared(
                root, memory_id=memory_id, operation_key=operation_key
            )
            if tombstone is not None:
                _validate_internal_tombstone(
                    tombstone,
                    prepared=prepared,
                    namespace=namespace,
                    memory_id=memory_id,
                    operation_id=operation_id,
                    root=root,
                )
                return _recovery_result_from_tombstone(
                    tombstone, idempotent_replay=True, tombstone_created=False
                )
            if prepared is None:
                return PrimaryForgetRecoveryResult(
                    status="not_recoverable",
                    prepared_present=False,
                    hidden_successor_present=False,
                    page_converged=False,
                    index_converged=False,
                    log_converged=False,
                    tombstone_present=False,
                    tombstone_created=False,
                    applied_receipt_present=False,
                    idempotent_replay=False,
                    lifecycle_state="unknown",
                    mutation_state="none",
                    retrieval_eligible=False,
                    prior_revision=0,
                    result_revision=0,
                    recovery_required=False,
                    reason_ids=("forget_operation_not_found",),
                )
            if (
                prepared.get("namespace") != namespace
                or prepared.get("memory_id") != memory_id
                or prepared.get("operation_id") != operation_id
                or prepared.get("operation_key") != operation_key
            ):
                raise PrimaryForgetError("operation_conflict")
            _fault(fault_at, "after_prepared_reread_before_hidden_resume")
            return _finalize_locked(
                root,
                prepared=prepared,
                result_type=PrimaryForgetRecoveryResult,
                now=now,
                fault_at=fault_at,
            )
    except PrimaryForgetError:
        raise
    except (
        PrimaryForgetArtifactError,
        PrimaryMutationCoordinatorError,
        PrimaryForgetHiddenResumeError,
        PrimaryForgetControlConvergenceError,
    ) as exc:
        raise PrimaryForgetError(_map_error(getattr(exc, "code", "failed"))) from exc
    except OSError as exc:
        raise PrimaryForgetError("store_unavailable") from exc


def _finalize_locked(
    root: Path,
    *,
    prepared: Mapping[str, Any],
    result_type: type[PrimaryForgetApplyResult] | type[PrimaryForgetRecoveryResult],
    now: datetime | None,
    fault_at: str | None,
) -> PrimaryForgetApplyResult | PrimaryForgetRecoveryResult:
    state = resolve_forget_current_state(
        root,
        namespace=str(prepared["namespace"]),
        memory_id=str(prepared["memory_id"]),
    )
    if state is None or state.mutation_state == "corrupt":
        raise PrimaryForgetError("target_corrupt")
    if state.lifecycle_state == "active":
        resume_prepared_forget_hidden_successor_locked(root, prepared=prepared)
        _fault(fault_at, "after_hidden_successor_publish_before_reread")
    if not verify_hidden_page_against_prepared(root, prepared=prepared):
        raise PrimaryForgetError("target_corrupt")
    _fault(fault_at, "after_hidden_reread_before_m3f")

    plan = build_hidden_control_reconciliation_plan(root, prepared=prepared)
    _fault(fault_at, "after_m3f_plan_before_m3g")
    if fault_at == "after_m3g_index_before_log":
        converge_hidden_primary_controls(
            root, prepared=prepared, fault_after_index=True
        )
        raise PrimaryForgetError("reconciliation_required")
    if fault_at == "after_m3g_before_control_reread":
        direct = apply_or_inspect_reconciliation(
            root_path=str(root), plan=plan, apply_requested=True
        )
        if (
            direct.get("index_reconciled") is not True
            or direct.get("log_reconciled") is not True
        ):
            raise PrimaryForgetError("reconciliation_required")
        raise PrimaryForgetError("reconciliation_required")

    converge_hidden_primary_controls(root, prepared=prepared)
    if not controls_are_exactly_converged(root, prepared=prepared):
        raise PrimaryForgetError("reconciliation_required")
    _fault(fault_at, "after_controls_reread_before_tombstone")

    existing = read_forget_tombstone(
        root,
        memory_id=str(prepared["memory_id"]),
        operation_key=str(prepared["operation_key"]),
    )
    if existing is not None:
        if not tombstone_matches_prepared(existing, prepared):
            raise PrimaryForgetError("target_corrupt")
        return _result_from_tombstone(
            result_type,
            existing,
            idempotent_replay=True,
            tombstone_created=False,
        )

    # The final timestamp is derived from already-durable prepare evidence so an
    # ambiguous tombstone publication can be rebuilt byte-for-byte on restart.
    # It is audit metadata, never identity authority.
    del now
    tombstone = build_forget_tombstone(
        prepared=prepared,
        result_canonical_digest=str(prepared["successor_expected_canonical_digest"]),
        applied_at=str(prepared["prepared_at"]),
    )
    _fault(fault_at, "during_tombstone_publish")
    publication = publish_forget_tombstone(root, tombstone=tombstone)
    _fault(fault_at, "after_tombstone_publish_before_reread")
    reread = read_forget_tombstone(
        root,
        memory_id=str(prepared["memory_id"]),
        operation_key=str(prepared["operation_key"]),
    )
    if reread != tombstone or not tombstone_matches_prepared(reread, prepared):
        raise PrimaryForgetError("target_corrupt")
    _fault(fault_at, "after_tombstone_reread_before_applied_receipt")
    result = _result_from_tombstone(
        result_type,
        reread,
        idempotent_replay=publication == "existing",
        tombstone_created=publication == "new",
    )
    if fault_at == "after_finalization_before_return":
        raise PrimaryForgetError("response_lost")
    return result


def _validate_external_prepared_replay(
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
) -> None:
    expected = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "result_revision": expected_revision + 1,
        "prior_lifecycle_state": "active",
        "result_lifecycle_state": "hidden",
        "reason": reason,
        "reason_digest": reason_digest,
        "operation_id": operation_id,
        "operation_key": _operation_key(operation_id),
        "token_digest": token_digest,
    }
    if any(prepared.get(key) != value for key, value in expected.items()):
        raise PrimaryForgetError("operation_conflict")


def _validate_external_tombstone_replay(
    tombstone: Mapping[str, Any],
    *,
    prepared: Mapping[str, Any] | None,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    reason: str,
    reason_digest: str,
    operation_id: str,
    token_digest: str,
    root: Path,
) -> None:
    if prepared is None or not tombstone_matches_prepared(tombstone, prepared):
        raise PrimaryForgetError("target_corrupt")
    expected = {
        "character_id": character_id,
        "namespace": namespace,
        "memory_id": memory_id,
        "prior_revision": expected_revision,
        "result_revision": expected_revision + 1,
        "reason": reason,
        "reason_digest": reason_digest,
        "operation_id": operation_id,
        "operation_key": _operation_key(operation_id),
        "token_digest": token_digest,
    }
    if any(tombstone.get(key) != value for key, value in expected.items()):
        raise PrimaryForgetError("operation_conflict")
    if (
        not verify_hidden_page_against_prepared(root, prepared=prepared)
        or not controls_are_exactly_converged(root, prepared=prepared)
    ):
        raise PrimaryForgetError("target_corrupt")


def _validate_internal_tombstone(
    tombstone: Mapping[str, Any],
    *,
    prepared: Mapping[str, Any] | None,
    namespace: str,
    memory_id: str,
    operation_id: str,
    root: Path,
) -> None:
    if prepared is None or not tombstone_matches_prepared(tombstone, prepared):
        raise PrimaryForgetError("target_corrupt")
    if (
        tombstone.get("namespace") != namespace
        or tombstone.get("memory_id") != memory_id
        or tombstone.get("operation_id") != operation_id
        or tombstone.get("operation_key") != _operation_key(operation_id)
        or not verify_hidden_page_against_prepared(root, prepared=prepared)
        or not controls_are_exactly_converged(root, prepared=prepared)
    ):
        raise PrimaryForgetError("target_corrupt")


def _result_from_tombstone(
    result_type: type[PrimaryForgetApplyResult] | type[PrimaryForgetRecoveryResult],
    tombstone: Mapping[str, Any],
    *,
    idempotent_replay: bool,
    tombstone_created: bool,
) -> PrimaryForgetApplyResult | PrimaryForgetRecoveryResult:
    return result_type(
        status="applied",
        prepared_present=True,
        hidden_successor_present=True,
        page_converged=True,
        index_converged=True,
        log_converged=True,
        tombstone_present=True,
        tombstone_created=tombstone_created,
        applied_receipt_present=False,
        idempotent_replay=idempotent_replay,
        lifecycle_state="hidden",
        mutation_state="none",
        retrieval_eligible=False,
        prior_revision=int(tombstone["prior_revision"]),
        result_revision=int(tombstone["result_revision"]),
        recovery_required=False,
        reason_ids=(),
        _tombstone=tombstone,
    )


def _apply_result_from_tombstone(
    tombstone: Mapping[str, Any], *, idempotent_replay: bool, tombstone_created: bool
) -> PrimaryForgetApplyResult:
    result = _result_from_tombstone(
        PrimaryForgetApplyResult,
        tombstone,
        idempotent_replay=idempotent_replay,
        tombstone_created=tombstone_created,
    )
    assert isinstance(result, PrimaryForgetApplyResult)
    return result


def _recovery_result_from_tombstone(
    tombstone: Mapping[str, Any], *, idempotent_replay: bool, tombstone_created: bool
) -> PrimaryForgetRecoveryResult:
    result = _result_from_tombstone(
        PrimaryForgetRecoveryResult,
        tombstone,
        idempotent_replay=idempotent_replay,
        tombstone_created=tombstone_created,
    )
    assert isinstance(result, PrimaryForgetRecoveryResult)
    return result


def _already_hidden_apply_result(
    *, expected_revision: int, result_revision: int
) -> PrimaryForgetApplyResult:
    return PrimaryForgetApplyResult(
        status="already_hidden",
        prepared_present=False,
        hidden_successor_present=True,
        page_converged=True,
        index_converged=True,
        log_converged=True,
        tombstone_present=True,
        tombstone_created=False,
        applied_receipt_present=False,
        idempotent_replay=False,
        lifecycle_state="hidden",
        mutation_state="none",
        retrieval_eligible=False,
        prior_revision=expected_revision,
        result_revision=result_revision,
        recovery_required=False,
        reason_ids=("target_already_hidden",),
    )


def _validate_apply_request(
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
) -> None:
    if not _bounded_store_root(store_root):
        raise PrimaryForgetError("store_unavailable")
    for value in (character_id, namespace, operation_id):
        if not _bounded(value, 128, multiline=False):
            raise PrimaryForgetError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryForgetError("target_not_found")
    if type(expected_revision) is not int or expected_revision < 1:
        raise PrimaryForgetError("invalid_request")
    if expected_lifecycle_state != "active":
        raise PrimaryForgetError("invalid_request")
    if not _bounded(reason, 512, multiline=True):
        raise PrimaryForgetError("invalid_request")
    if not isinstance(apply_token, str) or not apply_token or len(apply_token) > 8192:
        raise PrimaryForgetError("token_invalid")
    if fault_at not in _ALLOWED_FAULTS:
        raise PrimaryForgetError("invalid_request")


def _validate_recovery_request(
    *,
    store_root: str,
    namespace: str,
    memory_id: str,
    operation_id: str,
    fault_at: str | None,
) -> None:
    if not _bounded_store_root(store_root):
        raise PrimaryForgetError("store_unavailable")
    for value in (namespace, operation_id):
        if not _bounded(value, 128, multiline=False):
            raise PrimaryForgetError("invalid_request")
    if not is_sha256(memory_id):
        raise PrimaryForgetError("target_not_found")
    if fault_at not in _ALLOWED_FAULTS:
        raise PrimaryForgetError("invalid_request")


def _operation_key(operation_id: str) -> str:
    try:
        return forget_operation_key(operation_id)
    except PrimaryForgetArtifactError as exc:
        raise PrimaryForgetError(_map_error(exc.code)) from exc


def _fault(selected: str | None, seam: str) -> None:
    if selected == seam:
        raise PrimaryForgetError("reconciliation_required")


def _bounded_store_root(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and "\x00" not in value
    )


def _bounded(value: object, limit: int, *, multiline: bool) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and len(value) <= limit
        and "\x00" not in value
        and all(
            ord(char) not in {0x2028, 0x2029}
            and not 0xD800 <= ord(char) <= 0xDFFF
            for char in value
        )
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
        "invalid_request": "invalid_request",
        "target_not_found": "target_not_found",
        "target_corrupt": "target_corrupt",
        "target_not_active": "target_not_active",
        "already_hidden": "already_hidden",
        "stale_revision": "stale_revision",
        "operation_conflict": "operation_conflict",
        "token_invalid": "token_invalid",
        "token_expired": "token_expired",
        "store_unavailable": "store_unavailable",
        "publication_ambiguous": "reconciliation_required",
        "reconciliation_required": "reconciliation_required",
        "response_lost": "response_lost",
    }.get(code, "reconciliation_required")


__all__ = [
    "FORGET_APPLY_RESULT_SCHEMA",
    "FORGET_RECOVERY_RESULT_SCHEMA",
    "PrimaryForgetApplyResult",
    "PrimaryForgetRecoveryResult",
    "apply_primary_memory_forget",
    "recover_primary_memory_forget",
]
