"""Read-only current-state projection for finalized I-4C2 Forget evidence."""
from __future__ import annotations

from pathlib import Path

from ._relaymem_primary_current_state_impl import PrimaryCurrentState
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_forget_artifact import (
    MUTATION_ROOT,
    PrimaryForgetArtifactError,
    read_forget_prepared,
)
from .relaymem_primary_forget_control_convergence import controls_are_exactly_converged
from .relaymem_primary_forget_finalization_artifact import (
    PrimaryForgetArtifactError as _ArtifactAlias,
    read_forget_tombstone,
    tombstone_matches_prepared,
)
from .relaymem_primary_lifecycle_page import resolve_forget_current_state


def resolve_finalized_forget_current_state(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
) -> PrimaryCurrentState | None:
    """Return hidden/none/false only for one exact tombstone-backed chain."""

    del _ArtifactAlias  # imported alias documents the shared bounded error authority
    root = Path(store_root)
    directory = root / MUTATION_ROOT / memory_id
    if not directory.exists() and not directory.is_symlink():
        return None
    if directory.is_symlink() or not directory.is_dir():
        return _corrupt(memory_id, "primary_forget_finalization_dir_invalid")
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError:
        return _corrupt(memory_id, "primary_forget_finalization_dir_unreadable")
    tombstone_keys: list[str] = []
    for path in entries:
        if not path.name.endswith(".tombstone.json"):
            continue
        key = path.name.removesuffix(".tombstone.json")
        if not is_sha256(key) or path.is_symlink() or not path.is_file():
            return _corrupt(memory_id, "primary_forget_tombstone_invalid")
        tombstone_keys.append(key)
    if not tombstone_keys:
        return None
    if len(tombstone_keys) != 1:
        return _corrupt(memory_id, "primary_forget_tombstone_ambiguous")

    operation_key = tombstone_keys[0]
    try:
        tombstone = read_forget_tombstone(
            root, memory_id=memory_id, operation_key=operation_key
        )
        prepared = read_forget_prepared(
            root, memory_id=memory_id, operation_key=operation_key
        )
    except PrimaryForgetArtifactError:
        return _corrupt(memory_id, "primary_forget_tombstone_invalid")
    if tombstone is None or prepared is None:
        return _corrupt(memory_id, "primary_forget_tombstone_chain_missing")
    if (
        tombstone.get("namespace") != namespace
        or tombstone.get("memory_id") != memory_id
        or not tombstone_matches_prepared(tombstone, prepared)
    ):
        return _corrupt(
            memory_id,
            "primary_forget_tombstone_chain_mismatch",
            current_physical=str(tombstone.get("result_physical_id", memory_id)),
            current_revision=int(tombstone.get("result_revision", 1)),
        )
    hidden = resolve_forget_current_state(
        root, namespace=namespace, memory_id=memory_id
    )
    if (
        hidden is None
        or hidden.lifecycle_state != "hidden"
        or hidden.page_valid is not True
        or hidden.current_physical_id != tombstone["result_physical_id"]
        or hidden.current_revision != tombstone["result_revision"]
        or hidden.page_digest != tombstone["result_canonical_digest"]
        or not controls_are_exactly_converged(root, prepared=prepared)
    ):
        return _corrupt(
            memory_id,
            "primary_forget_finalization_correlation_invalid",
            current_physical=str(tombstone["result_physical_id"]),
            current_revision=int(tombstone["result_revision"]),
        )
    return PrimaryCurrentState(
        lifecycle_state="hidden",
        mutation_state="none",
        retrieval_eligible=False,
        memory_id=memory_id,
        current_physical_id=str(tombstone["result_physical_id"]),
        current_revision=int(tombstone["result_revision"]),
        controls_valid=True,
        page_valid=True,
        bounded_reason_ids=("primary_forget_finalized",),
        title=hidden.title,
        summary=hidden.summary,
        metadata=dict(hidden.metadata),
        page_digest=hidden.page_digest,
        relative_path=hidden.relative_path,
    )


def _corrupt(
    memory_id: str,
    reason: str,
    *,
    current_physical: str | None = None,
    current_revision: int = 1,
) -> PrimaryCurrentState:
    return PrimaryCurrentState(
        lifecycle_state="hidden",
        mutation_state="corrupt",
        retrieval_eligible=False,
        memory_id=memory_id,
        current_physical_id=current_physical or memory_id,
        current_revision=current_revision,
        controls_valid=False,
        page_valid=False,
        bounded_reason_ids=(reason,),
        title="",
        summary="",
        metadata={},
        page_digest="",
        relative_path="",
    )


__all__ = ["resolve_finalized_forget_current_state"]
