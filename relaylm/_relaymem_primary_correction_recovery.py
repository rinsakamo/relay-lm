"""Caller-invoked recovery for prepared Primary corrections."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from typing import Any
from ._relaymem_primary_page_writer_common import is_sha256
from ._relaymem_primary_correction_preflight import PrimaryCorrectionError, _iso, _safe_store_root, _utc
from ._relaymem_primary_correction_history import load_primary_correction_state
from ._relaymem_primary_correction_publication import PublicationDependencies, publish_prepared_successor
from ._relaymem_primary_correction_apply import (_memory_lock, _operation_path, _read_json, _valid_prepared, _write_immutable_json, build_applied_receipt)
from .subjective_mem_retrieval_cutover import primary_writer_decision_permits_write
_CORRECTION_ROOT = PurePosixPath("memory/mem/corrections/v0")


def recover_primary_memory_corrections(
    *, store_root: str, namespace: str, primary_writer_decision: object,
    _publication_dependencies: PublicationDependencies
) -> dict[str, int]:
    """Converge prepared operations without exposing an HTTP mutation shortcut."""

    try:
        permitted = primary_writer_decision_permits_write(primary_writer_decision)
    except Exception:  # noqa: BLE001 - malformed authority must fail closed
        permitted = False
    if not permitted:
        raise PrimaryCorrectionError("reconciliation_required")
    root = _safe_store_root(store_root)
    base = root / _CORRECTION_ROOT
    if not base.exists() or base.is_symlink() or not base.is_dir():
        return {"recovered": 0, "failed": 0}
    recovered = 0
    failed = 0
    for memory_dir in sorted(base.iterdir(), key=lambda item: item.name):
        logical = memory_dir.name
        if not is_sha256(logical) or memory_dir.is_symlink() or not memory_dir.is_dir():
            failed += 1
            continue
        for prepared_path in sorted(memory_dir.glob("*.prepared.json")):
            operation_key = prepared_path.name.removesuffix(".prepared.json")
            applied_path = _operation_path(root, logical, operation_key, "applied")
            if applied_path.exists():
                continue
            prepared = _read_json(prepared_path)
            if not _valid_prepared(prepared, namespace=namespace, memory_id=logical):
                failed += 1
                continue
            try:
                with _memory_lock(root, logical):
                    current_state = load_primary_correction_state(
                        root, namespace=namespace
                    )
                    current = current_state.current_by_logical.get(
                        logical, (logical, 1)
                    )
                    if current != (
                        str(prepared["prior_physical_id"]),
                        int(prepared["prior_revision"]),
                    ):
                        failed += 1
                        continue
                    result = publish_prepared_successor(root, prepared, fault_at=None, dependencies=_publication_dependencies)
                    applied = build_applied_receipt(
                        prepared=prepared, result=result, applied_at=_iso(_utc(None))
                    )
                    _write_immutable_json(applied_path, applied)
                    recovered += 1
            except PrimaryCorrectionError:
                failed += 1
    return {"recovered": recovered, "failed": failed}
