"""Shared Primary MEM mutation lock, operation fence, and revision reread.

Correct and Forget deliberately share the Phase I-3 correction directory and
``.lock`` path.  This module recognizes both exact artifact families and fails
closed on unknown, unsafe, ambiguous, or impossible operation evidence.
"""
from __future__ import annotations

import json
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from ._relaymem_primary_page_writer_common import is_sha256
from .portable_lock import portable_lock
from . import _relaymem_primary_current_state_impl as _current_impl
from .relaymem_primary_current_state import (
    CORRECTION_PREPARED_SCHEMA,
    CORRECTION_RECEIPT_SCHEMA,
    CORRECTION_ROOT,
    PrimaryCurrentState,
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_forget_artifact import (
    FORGET_PREPARED_SCHEMA,
    validate_forget_prepared,
)
from .relaymem_primary_forget_finalization_artifact import (
    FORGET_TOMBSTONE_SCHEMA,
    validate_forget_tombstone,
)

_MAX_ARTIFACT_BYTES = 32_768
_MUTATION_KINDS = frozenset({"correct", "forget"})


class PrimaryMutationCoordinatorError(RuntimeError):
    """Bounded shared-fence failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, repr=False)
class PrimaryMutationOperation:
    operation_id: str
    operation_kind: str
    operation_key: str
    binding_digest: str
    state: str
    prior_revision: int
    result_revision: int

    def __repr__(self) -> str:
        return (
            "PrimaryMutationOperation("
            f"operation_kind={self.operation_kind!r}, "
            f"state={self.state!r}, "
            f"prior_revision={self.prior_revision!r}, "
            f"result_revision={self.result_revision!r})"
        )


@dataclass(frozen=True, repr=False)
class PrimaryMutationInspection:
    operations: tuple[PrimaryMutationOperation, ...]
    pending: tuple[PrimaryMutationOperation, ...]
    corrupt: bool
    bounded_reason_ids: tuple[str, ...]

    def __repr__(self) -> str:
        return (
            "PrimaryMutationInspection("
            f"operation_count={len(self.operations)!r}, "
            f"pending_count={len(self.pending)!r}, "
            f"corrupt={self.corrupt!r}, "
            f"bounded_reason_ids={self.bounded_reason_ids!r})"
        )

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "operation_count": len(self.operations),
            "pending_count": len(self.pending),
            "corrupt": self.corrupt,
            "bounded_reason_ids": list(self.bounded_reason_ids),
            "content_included": False,
            "path_included": False,
            "digest_included": False,
            "physical_id_included": False,
        }


def primary_memory_mutation_lock_path(
    store_root: str | Path, memory_id: str
) -> Path:
    root = _safe_root(store_root)
    _validate_memory_id(memory_id)
    return root / CORRECTION_ROOT / memory_id / ".lock"


@contextmanager
def primary_memory_mutation_lock(
    store_root: str | Path, memory_id: str
) -> Iterator[None]:
    """Acquire the sole per-memory Correct/Forget mutation lock."""

    root = _safe_root(store_root)
    _validate_memory_id(memory_id)
    memory_dir = root / CORRECTION_ROOT / memory_id
    _ensure_private_dir(root, memory_dir)
    lock_path = memory_dir / ".lock"
    if lock_path.is_symlink():
        raise PrimaryMutationCoordinatorError("target_corrupt")
    try:
        with lock_path.open("a+b") as handle:
            with portable_lock(handle, mode="exclusive", blocking=True):
                yield
    except PrimaryMutationCoordinatorError:
        raise
    except OSError as exc:
        raise PrimaryMutationCoordinatorError("store_unavailable") from exc


def inspect_primary_memory_operations(
    store_root: str | Path, *, memory_id: str
) -> PrimaryMutationInspection:
    """Inspect exact known mutation artifacts without mutating the store."""

    root = _safe_root(store_root)
    _validate_memory_id(memory_id)
    memory_dir = root / CORRECTION_ROOT / memory_id
    if not memory_dir.exists() and not memory_dir.is_symlink():
        return PrimaryMutationInspection((), (), False, ())
    if memory_dir.is_symlink() or not memory_dir.is_dir():
        return PrimaryMutationInspection((), (), True, ("primary_mutation_dir_invalid",))

    operations: list[PrimaryMutationOperation] = []
    corrupt = False
    reasons: list[str] = []
    try:
        entries = sorted(memory_dir.iterdir(), key=lambda item: item.name)
    except OSError:
        return PrimaryMutationInspection((), (), True, ("primary_mutation_dir_unreadable",))

    for path in entries:
        if path.name == ".lock":
            if path.is_symlink() or (path.exists() and not path.is_file()):
                corrupt = True
                reasons.append("primary_mutation_lock_invalid")
            continue
        value = _read_json(path)
        operation = _operation_from_artifact(value)
        if operation is None:
            corrupt = True
            reasons.append("primary_mutation_artifact_invalid")
            continue
        expected_suffix = (
            ".prepared.json"
            if operation.state == "prepared"
            else ".tombstone.json"
            if operation.operation_kind == "forget"
            else ".applied.json"
        )
        if not path.name.endswith(expected_suffix) or path.name != (
            f"{operation.operation_key}{expected_suffix}"
        ):
            corrupt = True
            reasons.append("primary_mutation_artifact_name_invalid")
            continue
        operations.append(operation)

    by_kind_id: dict[tuple[str, str], list[PrimaryMutationOperation]] = {}
    seen_state: set[tuple[str, str, str]] = set()
    for operation in operations:
        state_key = (operation.operation_kind, operation.operation_id, operation.state)
        if state_key in seen_state:
            corrupt = True
            reasons.append("primary_mutation_operation_ambiguous")
        seen_state.add(state_key)
        by_kind_id.setdefault((operation.operation_kind, operation.operation_id), []).append(
            operation
        )

    pending: list[PrimaryMutationOperation] = []
    applied: list[PrimaryMutationOperation] = []
    for grouped in by_kind_id.values():
        prepared = [item for item in grouped if item.state == "prepared"]
        completed = [item for item in grouped if item.state == "applied"]
        if len(prepared) > 1 or len(completed) > 1:
            corrupt = True
            reasons.append("primary_mutation_operation_ambiguous")
            continue
        if prepared and completed:
            if (
                prepared[0].operation_key != completed[0].operation_key
                or prepared[0].binding_digest != completed[0].binding_digest
                or prepared[0].prior_revision != completed[0].prior_revision
                or prepared[0].result_revision != completed[0].result_revision
            ):
                corrupt = True
                reasons.append("primary_mutation_operation_conflicting_artifacts")
            applied.append(completed[0])
        elif completed:
            applied.append(completed[0])
        elif prepared:
            pending.append(prepared[0])

    # There can be only one operation ID meaning.  A repeated ID with a different
    # kind or binding is a conflict at lookup time, not a second valid operation.
    by_id: dict[str, list[PrimaryMutationOperation]] = {}
    for operation in operations:
        by_id.setdefault(operation.operation_id, []).append(operation)
    for grouped in by_id.values():
        meanings = {
            (item.operation_kind, item.operation_key, item.binding_digest)
            for item in grouped
        }
        if len(meanings) > 1:
            reasons.append("primary_mutation_operation_id_conflict")

    applied.sort(key=lambda item: (item.result_revision, item.operation_key))
    expected_prior = 1
    for operation in applied:
        if operation.prior_revision != expected_prior:
            corrupt = True
            reasons.append("primary_mutation_revision_chain_impossible")
            break
        expected_prior = operation.result_revision
    if len(pending) > 1:
        corrupt = True
        reasons.append("primary_mutation_pending_ambiguous")
    elif pending and pending[0].prior_revision != expected_prior:
        corrupt = True
        reasons.append("primary_mutation_pending_revision_impossible")

    operations.sort(
        key=lambda item: (
            item.prior_revision,
            item.result_revision,
            item.operation_kind,
            item.operation_id,
            item.state,
        )
    )
    pending.sort(
        key=lambda item: (item.prior_revision, item.operation_kind, item.operation_id)
    )
    return PrimaryMutationInspection(
        tuple(operations),
        tuple(pending),
        corrupt,
        tuple(dict.fromkeys(reasons))[:32],
    )


def lookup_primary_memory_operation(
    store_root: str | Path,
    *,
    memory_id: str,
    operation_kind: str,
    operation_id: str,
    binding_digest: str,
) -> str:
    """Return ``absent``/``exact``/``conflict`` for one operation identity."""

    _validate_operation_request(operation_kind, operation_id, binding_digest)
    inspection = inspect_primary_memory_operations(store_root, memory_id=memory_id)
    if inspection.corrupt:
        raise PrimaryMutationCoordinatorError("target_corrupt")
    matches = [item for item in inspection.operations if item.operation_id == operation_id]
    if not matches:
        return "absent"
    if any(
        item.operation_kind != operation_kind
        or item.binding_digest != binding_digest
        for item in matches
    ):
        return "conflict"
    return "exact"


def ensure_primary_memory_mutation_available(
    store_root: str | Path,
    *,
    memory_id: str,
    operation_kind: str,
    operation_id: str,
    binding_digest: str,
) -> str:
    """Apply the shared operation-ID and pending-operation fence."""

    state = lookup_primary_memory_operation(
        store_root,
        memory_id=memory_id,
        operation_kind=operation_kind,
        operation_id=operation_id,
        binding_digest=binding_digest,
    )
    if state == "conflict":
        raise PrimaryMutationCoordinatorError("operation_conflict")
    inspection = inspect_primary_memory_operations(store_root, memory_id=memory_id)
    if inspection.corrupt:
        raise PrimaryMutationCoordinatorError("target_corrupt")
    for pending in inspection.pending:
        if (
            pending.operation_kind == operation_kind
            and pending.operation_id == operation_id
            and pending.binding_digest == binding_digest
        ):
            continue
        raise PrimaryMutationCoordinatorError("operation_conflict")
    return state


def reread_primary_memory_for_mutation(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int,
    expected_lifecycle_state: str,
    operation_kind: str,
    operation_id: str,
    binding_digest: str,
) -> PrimaryCurrentState:
    """Reread and claim one exact revision under the canonical lock."""

    ensure_primary_memory_mutation_available(
        store_root,
        memory_id=memory_id,
        operation_kind=operation_kind,
        operation_id=operation_id,
        binding_digest=binding_digest,
    )
    try:
        current = resolve_primary_current_state(
            store_root,
            namespace=namespace,
            memory_id=memory_id,
            expected_revision=expected_revision,
        )
    except PrimaryCurrentStateError as exc:
        raise PrimaryMutationCoordinatorError(exc.code) from exc
    if current.mutation_state == "corrupt":
        raise PrimaryMutationCoordinatorError("target_corrupt")
    if current.lifecycle_state != expected_lifecycle_state:
        raise PrimaryMutationCoordinatorError("target_not_active")
    if current.mutation_state != "none":
        raise PrimaryMutationCoordinatorError("operation_conflict")
    return current


def _operation_from_artifact(
    value: Mapping[str, Any] | None,
) -> PrimaryMutationOperation | None:
    if not isinstance(value, Mapping):
        return None
    schema = value.get("schema_version")
    namespace = value.get("namespace")
    memory_id = value.get("memory_id")
    if schema == CORRECTION_PREPARED_SCHEMA:
        if not isinstance(namespace, str) or not isinstance(memory_id, str):
            return None
        if not _current_impl._valid_prepared(
            dict(value), namespace=namespace, memory_id=memory_id
        ):
            return None
        kind = "correct"
        state = "prepared"
        binding = value.get("candidate_digest")
    elif schema == CORRECTION_RECEIPT_SCHEMA:
        if not isinstance(namespace, str) or not isinstance(memory_id, str):
            return None
        if not _current_impl._valid_applied(
            dict(value), namespace=namespace, memory_id=memory_id
        ):
            return None
        kind = "correct"
        state = "applied"
        binding = value.get("candidate_digest")
    elif schema == FORGET_PREPARED_SCHEMA:
        if not validate_forget_prepared(value):
            return None
        kind = "forget"
        state = "prepared"
        binding = value.get("binding_digest")
    elif schema == FORGET_TOMBSTONE_SCHEMA:
        if not validate_forget_tombstone(value):
            return None
        kind = "forget"
        state = "applied"
        binding = value.get("binding_digest")
    else:
        return None
    operation_id = value.get("operation_id")
    operation_key = value.get("operation_key")
    prior_revision = value.get("prior_revision")
    result_revision = value.get("result_revision")
    if (
        not isinstance(operation_id, str)
        or not operation_id
        or operation_id != operation_id.strip()
        or len(operation_id) > 128
        or not is_sha256(operation_key)
        or not is_sha256(binding)
        or type(prior_revision) is not int
        or type(result_revision) is not int
        or prior_revision < 1
        or result_revision != prior_revision + 1
    ):
        return None
    return PrimaryMutationOperation(
        operation_id=operation_id,
        operation_kind=kind,
        operation_key=str(operation_key),
        binding_digest=str(binding),
        state=state,
        prior_revision=prior_revision,
        result_revision=result_revision,
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size <= 0
            or info.st_size > _MAX_ARTIFACT_BYTES
        ):
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if not isinstance(value, dict) or canonical + b"\n" != raw:
        return None
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _validate_operation_request(
    operation_kind: str, operation_id: str, binding_digest: str
) -> None:
    if operation_kind not in _MUTATION_KINDS:
        raise PrimaryMutationCoordinatorError("invalid_request")
    if (
        not isinstance(operation_id, str)
        or not operation_id
        or operation_id != operation_id.strip()
        or len(operation_id) > 128
        or "\x00" in operation_id
    ):
        raise PrimaryMutationCoordinatorError("invalid_request")
    if not is_sha256(binding_digest):
        raise PrimaryMutationCoordinatorError("invalid_request")


def _validate_memory_id(memory_id: str) -> None:
    if not is_sha256(memory_id):
        raise PrimaryMutationCoordinatorError("target_not_found")


def _safe_root(value: str | Path) -> Path:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value and value == value.strip() and "\x00" not in value:
        root = Path(value)
    else:
        raise PrimaryMutationCoordinatorError("store_unavailable")
    if _path_has_symlink(root):
        raise PrimaryMutationCoordinatorError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryMutationCoordinatorError("store_unavailable")
    return root


def _ensure_private_dir(root: Path, directory: Path) -> None:
    try:
        relative = directory.relative_to(root)
    except ValueError:
        raise PrimaryMutationCoordinatorError("target_corrupt") from None
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PrimaryMutationCoordinatorError("target_corrupt")
        if current.exists() and not current.is_dir():
            raise PrimaryMutationCoordinatorError("target_corrupt")
        current.mkdir(mode=0o700, exist_ok=True)


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


__all__ = [
    "PrimaryMutationCoordinatorError",
    "PrimaryMutationInspection",
    "PrimaryMutationOperation",
    "ensure_primary_memory_mutation_available",
    "inspect_primary_memory_operations",
    "lookup_primary_memory_operation",
    "primary_memory_mutation_lock",
    "primary_memory_mutation_lock_path",
    "reread_primary_memory_for_mutation",
]
