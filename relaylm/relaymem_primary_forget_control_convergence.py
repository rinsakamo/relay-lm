"""I-4C2 operation-scoped hidden-page control convergence.

This adapter keeps M3f/M3g ownership intact: it uses the existing deterministic
index/log plan builders and the existing ordered atomic control-file apply IO.
Only hidden lifecycle page verification is specialized, because the ordinary
M3f/M3g public verifier intentionally accepts active evidence pages only.
"""
from __future__ import annotations

import stat
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ._relaymem_primary_index_log_apply_io import apply_or_inspect_reconciliation
from ._relaymem_primary_index_log_reconciliation_contract import parse_m3e_receipt
from ._relaymem_primary_index_log_reconciliation_io import read_store_file
from ._relaymem_primary_index_log_reconciliation_plan import (
    INDEX_PATH,
    LOG_PATH,
    MAX_INDEX_LOG_BYTES,
    build_index_plan,
    build_log_plan,
    operation,
)
from ._relaymem_primary_page_writer_common import KIND_TARGET, MAX_PAGE_BYTES
from .relaymem_primary_forget_artifact import validate_forget_prepared
from .relaymem_primary_lifecycle_page import resolve_forget_current_state

_PLAN_SCHEMA = "relaymem.primary_index_log_reconciliation_plan.v0"
_RECEIPT_SCHEMA = "relaymem.primary_page_write_receipt.v0"


class PrimaryForgetControlConvergenceError(RuntimeError):
    """Bounded convergence failure safe for translation by I-4C2."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, repr=False)
class PrimaryForgetControlConvergenceResult:
    index_converged: bool
    log_converged: bool
    index_updated: bool
    log_updated: bool
    durability_confirmed: bool
    _receipt: Mapping[str, Any] = field(repr=False)

    def __repr__(self) -> str:
        return (
            "PrimaryForgetControlConvergenceResult("
            f"index_converged={self.index_converged!r}, "
            f"log_converged={self.log_converged!r}, "
            f"index_updated={self.index_updated!r}, "
            f"log_updated={self.log_updated!r}, "
            f"durability_confirmed={self.durability_confirmed!r})"
        )


def reconstruct_hidden_m3e_receipt(
    store_root: str | Path, *, prepared: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct exact M3e receipt-equivalent evidence by canonical reread."""

    if not validate_forget_prepared(prepared):
        raise PrimaryForgetControlConvergenceError("target_corrupt")
    root = _safe_root(store_root)
    state = resolve_forget_current_state(
        root,
        namespace=str(prepared["namespace"]),
        memory_id=str(prepared["memory_id"]),
    )
    if (
        state is None
        or state.lifecycle_state != "hidden"
        or state.page_valid is not True
        or state.current_physical_id != prepared["successor_physical_id"]
        or state.current_revision != prepared["result_revision"]
        or state.page_digest != prepared["successor_expected_canonical_digest"]
        or state.relative_path != prepared["successor_relative_path"]
    ):
        raise PrimaryForgetControlConvergenceError("target_corrupt")

    relative = PurePosixPath(str(prepared["successor_relative_path"]))
    path = root / relative
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > MAX_PAGE_BYTES
        ):
            raise PrimaryForgetControlConvergenceError("target_corrupt")
        raw = path.read_bytes()
        after = path.lstat()
    except PrimaryForgetControlConvergenceError:
        raise
    except OSError as exc:
        raise PrimaryForgetControlConvergenceError("store_unavailable") from exc
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_mode != after.st_mode
        or before.st_nlink != after.st_nlink
        or before.st_size != after.st_size
        or sha256(raw).hexdigest() != prepared["successor_expected_canonical_digest"]
    ):
        raise PrimaryForgetControlConvergenceError("target_corrupt")

    memory_kind = str(prepared["memory_kind"])
    category = KIND_TARGET.get(memory_kind)
    if category is None:
        raise PrimaryForgetControlConvergenceError("target_corrupt")
    receipt = {
        "schema_version": _RECEIPT_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": str(prepared["successor_candidate_id"]),
        "namespace": str(prepared["namespace"]),
        "source_event_kind": str(prepared["source_event_kind"]),
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": category,
        "target_relative_path": str(prepared["successor_relative_path"]),
        "lineage_fingerprint": str(prepared["lineage_fingerprint"]),
        "idempotency_key": str(prepared["successor_physical_id"]),
        "page_bytes": len(raw),
        "page_digest": sha256(raw).hexdigest(),
        "status": "already_applied",
        "writes_memory": False,
        "page_applied": False,
        "idempotent_noop": True,
        "durability_confirmed": False,
        "cleanup_complete": True,
        "updates_index": False,
        "updates_log": False,
    }
    parsed = parse_m3e_receipt(receipt)
    if parsed.get("valid") is not True:
        raise PrimaryForgetControlConvergenceError("target_corrupt")
    return receipt


def build_hidden_control_reconciliation_plan(
    store_root: str | Path, *, prepared: Mapping[str, Any]
) -> dict[str, Any]:
    """Build one exact M3f-compatible plan after hidden-page canonical reread."""

    root = _safe_root(store_root)
    receipt = reconstruct_hidden_m3e_receipt(root, prepared=prepared)
    index_file = read_store_file(
        root_path=str(root),
        relative_path=INDEX_PATH,
        max_bytes=MAX_INDEX_LOG_BYTES,
        role="index",
    )
    log_file = read_store_file(
        root_path=str(root),
        relative_path=LOG_PATH,
        max_bytes=MAX_INDEX_LOG_BYTES,
        role="log",
    )
    if index_file.get("valid") is not True or log_file.get("valid") is not True:
        raise PrimaryForgetControlConvergenceError("reconciliation_required")
    index_plan = build_index_plan(receipt, index_file["content"])
    log_plan = build_log_plan(receipt, log_file["content"], index_plan["entry_identity"])
    if index_plan.get("conflict") or log_plan.get("conflict"):
        raise PrimaryForgetControlConvergenceError("target_corrupt")

    index_required = not bool(index_plan["idempotent_noop"])
    log_required = not bool(log_plan["idempotent_noop"])
    if index_required and log_required:
        state = "index_and_log_update_required"
    elif index_required:
        state = "index_update_required"
    elif log_required:
        state = "log_update_required"
    else:
        state = "already_reconciled"
    operations: list[dict[str, Any]] = []
    if index_required:
        operations.append(operation(index_plan, len(operations)))
    if log_required:
        operations.append(operation(log_plan, len(operations)))
    return {
        "schema_version": _PLAN_SCHEMA,
        "runtime_private": True,
        "read_only": True,
        "dry_run_only": True,
        "reconciliation_state": state,
        "plan_ready": True,
        "page": {
            "target_relative_path": receipt["target_relative_path"],
            "page_bytes": receipt["page_bytes"],
            "page_digest": receipt["page_digest"],
            "idempotency_key": receipt["idempotency_key"],
            "memory_kind": receipt["memory_kind"],
            "target_category": receipt["target_category"],
        },
        "index_plan": index_plan,
        "log_plan": log_plan,
        "ordered_operations": operations,
        "operation_count": len(operations),
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
    }


def converge_hidden_primary_controls(
    store_root: str | Path,
    *,
    prepared: Mapping[str, Any],
    fault_after_index: bool = False,
) -> PrimaryForgetControlConvergenceResult:
    """Apply index-before-log and prove convergence by a fresh canonical plan."""

    root = _safe_root(store_root)
    plan = build_hidden_control_reconciliation_plan(root, prepared=prepared)
    if fault_after_index and plan["reconciliation_state"] == "index_and_log_update_required":
        partial = dict(plan)
        partial["ordered_operations"] = [dict(plan["ordered_operations"][0])]
        partial["operation_count"] = 1
        apply_or_inspect_reconciliation(
            root_path=str(root), plan=partial, apply_requested=True
        )
        raise PrimaryForgetControlConvergenceError("reconciliation_required")

    result = apply_or_inspect_reconciliation(
        root_path=str(root), plan=plan, apply_requested=True
    )
    if (
        result.get("index_reconciled") is not True
        or result.get("log_reconciled") is not True
        or result.get("durability_confirmed") is not True
    ):
        raise PrimaryForgetControlConvergenceError("reconciliation_required")

    reread_plan = build_hidden_control_reconciliation_plan(root, prepared=prepared)
    if (
        reread_plan.get("reconciliation_state") != "already_reconciled"
        or reread_plan["index_plan"].get("idempotent_noop") is not True
        or reread_plan["log_plan"].get("idempotent_noop") is not True
        or reread_plan.get("operation_count") != 0
    ):
        raise PrimaryForgetControlConvergenceError("reconciliation_required")
    receipt = reconstruct_hidden_m3e_receipt(root, prepared=prepared)
    return PrimaryForgetControlConvergenceResult(
        index_converged=True,
        log_converged=True,
        index_updated=bool(result.get("index_updated")),
        log_updated=bool(result.get("log_updated")),
        durability_confirmed=True,
        _receipt=receipt,
    )


def controls_are_exactly_converged(
    store_root: str | Path, *, prepared: Mapping[str, Any]
) -> bool:
    try:
        plan = build_hidden_control_reconciliation_plan(store_root, prepared=prepared)
    except PrimaryForgetControlConvergenceError:
        return False
    return (
        plan.get("reconciliation_state") == "already_reconciled"
        and plan["index_plan"].get("idempotent_noop") is True
        and plan["log_plan"].get("idempotent_noop") is True
        and plan.get("operation_count") == 0
    )


def _safe_root(value: str | Path) -> Path:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value and value == value.strip() and "\x00" not in value:
        root = Path(value)
    else:
        raise PrimaryForgetControlConvergenceError("store_unavailable")
    current = Path(root.anchor) if root.is_absolute() else Path()
    for part in root.parts[1:] if root.is_absolute() else root.parts:
        current = current / part
        if current.is_symlink():
            raise PrimaryForgetControlConvergenceError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryForgetControlConvergenceError("store_unavailable")
    return root


__all__ = [
    "PrimaryForgetControlConvergenceError",
    "PrimaryForgetControlConvergenceResult",
    "build_hidden_control_reconciliation_plan",
    "controls_are_exactly_converged",
    "converge_hidden_primary_controls",
    "reconstruct_hidden_m3e_receipt",
]
