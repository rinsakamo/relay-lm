"""Internal Primary Forget apply and exact-replay orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Collection, ContextManager, Mapping

from ._relaymem_primary_forget_impl import PrimaryForgetError
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_forget_artifact import (
    PrimaryForgetArtifactError,
    forget_operation_key,
)
from .relaymem_primary_forget_control_convergence import (
    PrimaryForgetControlConvergenceError,
)
from .relaymem_primary_forget_hidden_resume import PrimaryForgetHiddenResumeError
from .relaymem_primary_mutation_coordinator import PrimaryMutationCoordinatorError
from .subjective_mem_retrieval_cutover import primary_writer_decision_permits_write

Result = Any


@dataclass(frozen=True)
class PrimaryForgetApplyDependencies:
    """Facade-owned callables resolved afresh for every public apply call."""

    error_type: type[PrimaryForgetError]
    mutation_lock: Callable[[Path, str], ContextManager[None]]
    read_prepared: Callable[..., Mapping[str, Any] | None]
    read_tombstone: Callable[..., Mapping[str, Any] | None]
    tombstone_matches_prepared: Callable[[Mapping[str, Any], Mapping[str, Any]], bool]
    verify_hidden_page: Callable[..., bool]
    controls_are_converged: Callable[..., bool]
    hidden_successor_apply: Callable[..., Any]
    resolve_current_state: Callable[..., Any]
    finalize_locked: Callable[..., Result]
    result_from_tombstone: Callable[..., Result]
    already_hidden_result: Callable[..., Result]
    result_type: type[Any]
    allowed_faults: Collection[str | None]


def apply_primary_memory_forget(
    *,
    dependencies: PrimaryForgetApplyDependencies,
    store_root: str,
    character_id: str,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    expected_lifecycle_state: str,
    reason: str,
    operation_id: str,
    apply_token: str,
    primary_writer_decision: object,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> Result:
    """Apply or exactly replay through facade-owned finalization."""
    try:
        permitted = primary_writer_decision_permits_write(primary_writer_decision)
    except Exception:  # noqa: BLE001 - malformed authority must fail closed
        permitted = False
    if not permitted:
        raise dependencies.error_type("reconciliation_required")
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
        allowed_faults=dependencies.allowed_faults,
    )
    operation_key = _operation_key(operation_id)
    token_digest = sha256(apply_token.encode("utf-8")).hexdigest()
    reason_digest = sha256(reason.encode("utf-8")).hexdigest()
    binding = _ApplyBinding(
        store_root=store_root,
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
        reason=reason,
        reason_digest=reason_digest,
        operation_id=operation_id,
        operation_key=operation_key,
        token_digest=token_digest,
    )
    try:
        return _apply_validated(
            dependencies,
            root=Path(store_root),
            binding=binding,
            expected_lifecycle_state=expected_lifecycle_state,
            apply_token=apply_token,
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
        raise dependencies.error_type(_map_error(getattr(exc, "code", "failed"))) from exc
    except OSError as exc:
        raise dependencies.error_type("store_unavailable") from exc


@dataclass(frozen=True)
class _ApplyBinding:
    store_root: str
    character_id: str
    namespace: str
    memory_id: str
    expected_revision: int
    reason: str
    reason_digest: str
    operation_id: str
    operation_key: str
    token_digest: str


def _apply_validated(
    dependencies: PrimaryForgetApplyDependencies,
    *,
    root: Path,
    binding: _ApplyBinding,
    expected_lifecycle_state: str,
    apply_token: str,
    now: datetime | None,
    fault_at: str | None,
) -> Result:
    existing = _read_existing_operation(
        dependencies, root=root, binding=binding, now=now, fault_at=fault_at
    )
    if existing is not None:
        return existing
    hidden_result = _apply_hidden_successor(
        dependencies,
        root=root,
        binding=binding,
        expected_lifecycle_state=expected_lifecycle_state,
        apply_token=apply_token,
        now=now,
        fault_at=fault_at,
    )
    if hidden_result is not None:
        return hidden_result
    return _reread_and_finalize(
        dependencies, root=root, binding=binding, now=now, fault_at=fault_at
    )


def _read_existing_operation(
    dependencies: PrimaryForgetApplyDependencies,
    *,
    root: Path,
    binding: _ApplyBinding,
    now: datetime | None,
    fault_at: str | None,
) -> Result | None:
    with dependencies.mutation_lock(root, binding.memory_id):
        _fault(fault_at, "after_lock_before_operation_reread")
        tombstone = dependencies.read_tombstone(
            root, memory_id=binding.memory_id, operation_key=binding.operation_key
        )
        prepared = dependencies.read_prepared(
            root, memory_id=binding.memory_id, operation_key=binding.operation_key
        )
        if tombstone is not None:
            _validate_external_tombstone_replay(
                dependencies, tombstone, prepared=prepared, binding=binding, root=root
            )
            return dependencies.result_from_tombstone(
                tombstone, idempotent_replay=True, tombstone_created=False
            )
        if prepared is not None:
            _validate_external_prepared_replay(prepared, binding=binding)
            _fault(fault_at, "after_prepared_reread_before_hidden_resume")
            return dependencies.finalize_locked(
                root,
                prepared=prepared,
                result_type=dependencies.result_type,
                now=now,
                fault_at=fault_at,
            )
    return None


def _apply_hidden_successor(
    dependencies: PrimaryForgetApplyDependencies,
    *,
    root: Path,
    binding: _ApplyBinding,
    expected_lifecycle_state: str,
    apply_token: str,
    now: datetime | None,
    fault_at: str | None,
) -> Result | None:
    translated_fault = (
        "after_hidden_successor_publication_before_reread"
        if fault_at == "after_hidden_successor_publish_before_reread"
        else None
    )
    try:
        dependencies.hidden_successor_apply(
            store_root=binding.store_root,
            character_id=binding.character_id,
            namespace=binding.namespace,
            memory_id=binding.memory_id,
            expected_revision=binding.expected_revision,
            expected_lifecycle_state=expected_lifecycle_state,
            reason=binding.reason,
            operation_id=binding.operation_id,
            apply_token=apply_token,
            now=now,
            fault_at=translated_fault,
        )
    except PrimaryForgetError as exc:
        if exc.code not in {"target_not_active", "operation_conflict"}:
            raise
        state = dependencies.resolve_current_state(
            root, namespace=binding.namespace, memory_id=binding.memory_id
        )
        if state.lifecycle_state == "hidden" and state.mutation_state == "none":
            return dependencies.already_hidden_result(
                expected_revision=binding.expected_revision,
                result_revision=state.current_revision,
            )
        raise
    return None


def _reread_and_finalize(
    dependencies: PrimaryForgetApplyDependencies,
    *,
    root: Path,
    binding: _ApplyBinding,
    now: datetime | None,
    fault_at: str | None,
) -> Result:
    with dependencies.mutation_lock(root, binding.memory_id):
        prepared = dependencies.read_prepared(
            root, memory_id=binding.memory_id, operation_key=binding.operation_key
        )
        if prepared is None:
            raise dependencies.error_type("reconciliation_required")
        _validate_external_prepared_replay(prepared, binding=binding)
        return dependencies.finalize_locked(
            root,
            prepared=prepared,
            result_type=dependencies.result_type,
            now=now,
            fault_at=fault_at,
        )


def _validate_external_prepared_replay(
    prepared: Mapping[str, Any], *, binding: _ApplyBinding
) -> None:
    expected = {
        "character_id": binding.character_id,
        "namespace": binding.namespace,
        "memory_id": binding.memory_id,
        "prior_revision": binding.expected_revision,
        "result_revision": binding.expected_revision + 1,
        "prior_lifecycle_state": "active",
        "result_lifecycle_state": "hidden",
        "reason": binding.reason,
        "reason_digest": binding.reason_digest,
        "operation_id": binding.operation_id,
        "operation_key": binding.operation_key,
        "token_digest": binding.token_digest,
    }
    if any(prepared.get(key) != value for key, value in expected.items()):
        raise PrimaryForgetError("operation_conflict")


def _validate_external_tombstone_replay(
    dependencies: PrimaryForgetApplyDependencies,
    tombstone: Mapping[str, Any],
    *,
    prepared: Mapping[str, Any] | None,
    binding: _ApplyBinding,
    root: Path,
) -> None:
    if prepared is None or not dependencies.tombstone_matches_prepared(
        tombstone, prepared
    ):
        raise PrimaryForgetError("target_corrupt")
    expected = {
        "character_id": binding.character_id,
        "namespace": binding.namespace,
        "memory_id": binding.memory_id,
        "prior_revision": binding.expected_revision,
        "result_revision": binding.expected_revision + 1,
        "reason": binding.reason,
        "reason_digest": binding.reason_digest,
        "operation_id": binding.operation_id,
        "operation_key": binding.operation_key,
        "token_digest": binding.token_digest,
    }
    if any(tombstone.get(key) != value for key, value in expected.items()):
        raise PrimaryForgetError("operation_conflict")
    if (
        not dependencies.verify_hidden_page(root, prepared=prepared)
        or not dependencies.controls_are_converged(root, prepared=prepared)
    ):
        raise PrimaryForgetError("target_corrupt")


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
    allowed_faults: Collection[str | None],
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
    if fault_at not in allowed_faults:
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
