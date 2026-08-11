"""Private RT-1D-R4 ordinary-runtime Subjective projection boundary.

This module owns exactly one responsibility: acquire one fixed canonical
Subjective source snapshot from the existing authorities, derive the projection
through the existing RT-1B builder, install or exact-verify one replace-only
disposable bundle, trusted-read it, and return bounded immutable values.

It orchestrates existing owners and reimplements none of them. It is not a
second current selector, receipt validator, lifecycle evaluator, canonical
parser, projection builder, projection store, journal, serving decision, or
configuration semantics, and it owns no rehearsal-readiness semantics.

The dependency direction is one-way. The cutover facade and the ordinary
Subjective route depend on this module; this module imports only the Evidence
store, the canonical digest helper, the canonical page identity helper, the
RT-1B projection builder, and the projection store. It must never import the
cutover facade, the configuration owner, request-path owners, the selection
owner, the usage ledger, Primary owners, RelayCTX, the R3 rehearsal
coordinator, or the characterization owner.

Roots and identifiers arrive explicitly from the caller. This owner never
decides which requested mode is authorized or which root belongs to it: the
facade supplies the rehearsal root for ``rehearsal`` and the ordinary
projection root for ``subjective_only``.

Every failure is content-free and fails closed. Nothing here mutates canonical
memory, repairs durable state, restores Primary, falls back to a stale
generation, or authorizes serving.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .evidence.common import canonical_digest
from .evidence.store import EvidenceRecordStore
from .subjective_mem.markdown import subjective_mem_page_identity
from .subjective_mem.retrieval_projection import (
    SubjectiveMemRetrievalProjection,
    SubjectiveMemRetrievalProjectionSource,
    SubjectiveMemRetrievalProjectionSourceEntry,
    build_subjective_mem_retrieval_projection,
)
from .subjective_mem_retrieval_projection_store import (
    delete_subjective_mem_retrieval_projection,
    read_subjective_mem_retrieval_projection,
    write_subjective_mem_retrieval_projection,
)

RUNTIME_PROJECTION_SPEC_SCHEMA = "relaylm.subjective_mem_retrieval_runtime_projection.v1"
CURRENT_STATE_LOG_KIND = "subjective_mem_current_state"
MAX_RUNTIME_SOURCE_ENTRIES = 512
_MEMORY_KINDS = ("episodic", "semantic")
_RECEIPT_KINDS = {
    1: "subjective_mem_st1_commit_receipt",
    2: "subjective_mem_lifecycle_receipt",
}
_AUTHORIZATION_KINDS = {
    "formation_decision": "subjective_mem_decision",
    "lifecycle_transition": "subjective_mem_lifecycle_transition",
}


@dataclass(frozen=True)
class SubjectiveMemRetrievalRuntimeProjectionSpec:
    """One explicit, content-free acquisition instruction from the caller."""

    evidence_root: str
    workspace_root: str
    projection_root: str
    evidence_space_id: str
    character_id: str


@dataclass(frozen=True, repr=False)
class SubjectiveMemRetrievalRuntimeProjection:
    """One acquired source and its exact trusted-read projection."""

    source: SubjectiveMemRetrievalProjectionSource
    projection: SubjectiveMemRetrievalProjection
    canonical_page_images: tuple[bytes, ...]

    @property
    def projection_generation_id(self) -> str:
        return self.projection.manifest.projection_generation_id

    @property
    def row_population_digest(self) -> str:
        return canonical_digest([row.row_digest for row in self.projection.rows])

    def __repr__(self) -> str:
        return (
            "SubjectiveMemRetrievalRuntimeProjection(runtime_private_content_omitted=True)"
        )


def subjective_mem_retrieval_runtime_projection_spec(
    *,
    evidence_root: object,
    workspace_root: object,
    projection_root: object,
    evidence_space_id: object,
    character_id: object,
) -> tuple[
    SubjectiveMemRetrievalRuntimeProjectionSpec | None,
    EvidenceRecordStore | None,
    tuple[str, ...],
]:
    """Validate explicit safe roots and identifiers, then open the one store."""

    roots = (evidence_root, workspace_root, projection_root)
    if any(not _safe_root(value) for value in roots):
        return None, None, ("subjective_mem_retrieval_runtime_root_unsupported",)
    if len({str(value) for value in roots}) != len(roots):
        return None, None, ("subjective_mem_retrieval_runtime_root_not_distinct",)
    if not _identifier(evidence_space_id) or not _identifier(character_id):
        return None, None, ("subjective_mem_retrieval_runtime_identifier_invalid",)
    try:
        store = EvidenceRecordStore(str(evidence_root))
    except (OSError, TypeError, ValueError):
        return None, None, ("subjective_mem_retrieval_runtime_store_unsupported",)
    spec = SubjectiveMemRetrievalRuntimeProjectionSpec(
        evidence_root=str(evidence_root),
        workspace_root=str(workspace_root),
        projection_root=str(projection_root),
        evidence_space_id=str(evidence_space_id),
        character_id=str(character_id),
    )
    return spec, store, ()


def acquire_subjective_mem_retrieval_runtime_projection(
    *, store: object, spec: object
) -> tuple[SubjectiveMemRetrievalRuntimeProjection | None, tuple[str, ...]]:
    """Acquire one fixed snapshot and its installed, trusted-read projection."""

    if (
        type(store) is not EvidenceRecordStore
        or type(spec) is not SubjectiveMemRetrievalRuntimeProjectionSpec
    ):
        return None, ("subjective_mem_retrieval_runtime_spec_invalid",)
    source, reasons = _acquire_source(store, spec)
    if source is None:
        return None, reasons
    built, reasons = build_subjective_mem_retrieval_projection(source)
    if built is None:
        return None, reasons or ("subjective_mem_retrieval_runtime_build_failed",)
    trusted, reasons = _install_or_verify(spec, source, built)
    if trusted is None:
        return None, reasons
    images = tuple(entry.canonical_page_bytes for entry in source.entries)
    return (
        SubjectiveMemRetrievalRuntimeProjection(
            source=source, projection=trusted, canonical_page_images=images
        ),
        (),
    )


def verify_subjective_mem_retrieval_runtime_projection(
    *,
    store: object,
    spec: object,
    expected_generation_id: object,
    expected_source_digest: object,
) -> tuple[SubjectiveMemRetrievalRuntimeProjection | None, tuple[str, ...]]:
    """Acquire, then prove the result is the exact expected fixed generation."""

    acquired, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    if acquired is None:
        return None, reasons
    if acquired.source.projection_generation_id != expected_generation_id:
        return None, ("subjective_mem_retrieval_runtime_generation_disagreement",)
    if acquired.source.source_snapshot_digest != expected_source_digest:
        return None, ("subjective_mem_retrieval_runtime_source_disagreement",)
    return acquired, ()


def _acquire_source(
    store: EvidenceRecordStore, spec: SubjectiveMemRetrievalRuntimeProjectionSpec
) -> tuple[SubjectiveMemRetrievalProjectionSource | None, tuple[str, ...]]:
    """Hold one evidence-space lock and read one fixed, self-consistent snapshot."""

    try:
        with store.transaction(spec.evidence_space_id) as transaction:
            selectors, reasons = _selectors(transaction, spec)
            if selectors is None:
                return None, reasons
            entries, reasons = _entries(transaction, spec, selectors)
            if entries is None:
                return None, reasons
    except (OSError, RuntimeError, ValueError):
        return None, ("subjective_mem_retrieval_runtime_store_read_failed",)
    workspace = _declared(selectors, "workspace_authority_digest")
    scopes = _declared(selectors, "scope_binding_digest")
    if len(workspace) != 1 or len(scopes) != 1:
        # Zero means nothing in the snapshot names an authority to bind to; more
        # than one means the snapshot spans authorities. Neither is reconciled.
        return None, ("subjective_mem_retrieval_runtime_authority_ambiguous",)
    return (
        SubjectiveMemRetrievalProjectionSource(
            evidence_space_id=spec.evidence_space_id,
            character_id=spec.character_id,
            workspace_authority_digest=workspace.pop(),
            admitted_scope_binding_digest=scopes.pop(),
            snapshot_taken_at=_snapshot_taken_at(selectors),
            entries=entries,
        ),
        (),
    )


def _selectors(
    transaction: object, spec: SubjectiveMemRetrievalRuntimeProjectionSpec
) -> tuple[list[dict] | None, tuple[str, ...]]:
    """Select this character's complete current-selector population by identity.

    This is identity and location resolution only. Lifecycle state, mutation
    state, retrieval eligibility, revision semantics, and authority exactness
    are never judged here: a held, hidden, mutation-pending, or
    retrieval-ineligible current selector still belongs to the fixed snapshot,
    and the existing RT-1B builder remains the sole semantic evaluator. A
    foreign selector is skipped only once its character identity has been read
    safely; anything else stays in scope so the builder can reject it.
    """

    inventory = transaction.list_logs(
        log_kind=CURRENT_STATE_LOG_KIND, limit=MAX_RUNTIME_SOURCE_ENTRIES + 1
    )
    if len(inventory) > MAX_RUNTIME_SOURCE_ENTRIES:
        return None, ("subjective_mem_retrieval_runtime_source_too_large",)
    selected: list[tuple[str, dict]] = []
    for key, records in inventory:
        if type(records) is not list or len(records) != 1 or type(records[0]) is not dict:
            return None, ("subjective_mem_retrieval_runtime_selector_event_invalid",)
        selector = records[0]
        character = selector.get("character_id")
        if type(character) is str and character != spec.character_id:
            continue
        if selector.get("memory_state_id") != key:
            return None, ("subjective_mem_retrieval_runtime_selector_key_mismatch",)
        selected.append((key, selector))
    if not selected:
        return None, ("subjective_mem_retrieval_runtime_source_empty",)
    return [selector for _key, selector in sorted(selected, key=lambda item: item[0])], ()


def _entries(
    transaction: object,
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    selectors: list[dict],
) -> tuple[tuple[SubjectiveMemRetrievalProjectionSourceEntry, ...] | None, tuple[str, ...]]:
    """Load each selector's exact receipt, authorization, and canonical page."""

    pages: dict[str, bytes] = {}
    entries: list[SubjectiveMemRetrievalProjectionSourceEntry] = []
    for selector in selectors:
        receipt, authorization, reasons = _authority_records(transaction, selector)
        if reasons:
            return None, reasons
        image, reasons = _entry_page(spec, pages, selector)
        if reasons:
            return None, reasons
        entries.append(
            SubjectiveMemRetrievalProjectionSourceEntry(
                canonical_page_bytes=image,
                current_selector_record=selector,
                current_receipt_record=receipt,
                authorization_record=authorization,
            )
        )
    return tuple(entries), ()


def _authority_records(
    transaction: object, selector: dict
) -> tuple[dict, dict, tuple[str, ...]]:
    """Resolve the exact records this selector names, by location only.

    A selector that names no resolvable receipt or authorization carries empty
    material, so the builder rejects it as unbound rather than this owner
    judging it. A named record that is absent or not a record is a dangling
    durable reference, which is a location failure and fails closed here.
    """

    reference = _located(selector)
    if reference is None:
        return {}, {}, ()
    receipt_kind, receipt_id, authorization_kind, authorization_id = reference
    receipt = transaction.read_record(record_kind=receipt_kind, record_id=receipt_id)
    authorization = transaction.read_record(
        record_kind=authorization_kind, record_id=authorization_id
    )
    if type(receipt) is not dict or type(authorization) is not dict:
        return {}, {}, ("subjective_mem_retrieval_runtime_authority_missing",)
    return receipt, authorization, ()


def _located(selector: dict) -> tuple[str, str, str, str] | None:
    """Return the four exact record coordinates this selector names, if any."""

    binding = selector.get("authority_binding")
    if type(binding) is not dict:
        return None
    reference = binding.get("authorization_ref")
    revision = selector.get("current_revision")
    if type(reference) is not dict or type(revision) is not int:
        return None
    authorization_kind = _AUTHORIZATION_KINDS.get(reference.get("authority_kind"))
    receipt_id = binding.get("current_receipt_id")
    authorization_id = reference.get("authority_id")
    if (
        authorization_kind is None
        or not _identifier(receipt_id)
        or not _identifier(authorization_id)
    ):
        return None
    return (
        _RECEIPT_KINDS[1 if revision == 1 else 2],
        receipt_id,
        authorization_kind,
        authorization_id,
    )


def _entry_page(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    pages: dict[str, bytes],
    selector: dict,
) -> tuple[bytes, tuple[str, ...]]:
    """Read the canonical page this selector names, by location only."""

    binding = selector.get("authority_binding")
    page_id = binding.get("page_id") if type(binding) is dict else None
    if not _identifier(page_id):
        return b"", ()
    return _page_bytes(spec, pages, str(page_id))


def _declared(selectors: list[dict], field: str) -> set[str]:
    """Collect the distinct authority values the bound selectors declare."""

    values: set[str] = set()
    for selector in selectors:
        binding = selector.get("authority_binding")
        value = binding.get(field) if type(binding) is dict else None
        if _digest(value):
            values.add(str(value))
    return values


def _page_bytes(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    pages: dict[str, bytes],
    page_id: str,
) -> tuple[bytes, tuple[str, ...]]:
    """Read one canonical page exactly once per acquisition, by location only.

    A page identity this workspace layout cannot name carries empty material so
    the builder refuses the selector. A named page that is missing, symlinked,
    or unreadable is a dangling location and fails closed here.
    """

    if page_id in pages:
        return pages[page_id], ()
    relative = _page_path(spec.character_id, page_id)
    if relative is None:
        return b"", ()
    target = Path(spec.workspace_root) / spec.character_id / relative
    try:
        if target.is_symlink() or not target.is_file():
            return b"", ("subjective_mem_retrieval_runtime_page_unsupported",)
        image = target.read_bytes()
    except OSError:
        return b"", ("subjective_mem_retrieval_runtime_page_unreadable",)
    pages[page_id] = image
    return image, ()


def _page_path(character_id: str, page_id: str) -> str | None:
    """Map one exact page identity back to its canonical workspace location."""

    for memory_kind in _MEMORY_KINDS:
        identity, relative, _partition = subjective_mem_page_identity(
            character_id=character_id, memory_kind=memory_kind
        )
        if identity == page_id:
            return relative
    return None


def _install_or_verify(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    source: SubjectiveMemRetrievalProjectionSource,
    built: SubjectiveMemRetrievalProjection,
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Install or exact-verify one replace-only bundle, then trusted-read it.

    A bundle that already matches this exact source is reused unchanged. Any
    other pre-existing bundle belongs to a different generation and is replaced
    only after it fails the exact source-bound trusted read, so no foreign,
    stale, or corrupt bundle is ever admitted and none is repaired in place.
    """

    existing, reasons = read_subjective_mem_retrieval_projection(
        projection_root=spec.projection_root, source=source
    )
    if existing is not None and not reasons and existing == built:
        return existing, ()
    if existing is None and reasons and reasons != (
        "subjective_mem_retrieval_projection_absent",
    ):
        deletion = delete_subjective_mem_retrieval_projection(
            projection_root=spec.projection_root
        )
        if deletion:
            return None, deletion
    reasons = write_subjective_mem_retrieval_projection(
        projection_root=spec.projection_root, source=source, projection=built
    )
    if reasons:
        return None, reasons
    trusted, reasons = read_subjective_mem_retrieval_projection(
        projection_root=spec.projection_root, source=source
    )
    if trusted is None or reasons:
        return None, reasons or ("subjective_mem_retrieval_runtime_bundle_unreadable",)
    if trusted != built or trusted.manifest != built.manifest:
        return None, ("subjective_mem_retrieval_runtime_bundle_disagreement",)
    return trusted, ()


def _snapshot_taken_at(selectors: list[dict]) -> str:
    """Bind build time to the snapshot itself; no wall clock enters identity."""

    return max(str(selector.get("updated_at", "")) for selector in selectors)


def _safe_root(value: object) -> bool:
    """Only an absolute, normalized, non-symlinked directory path is supported."""

    if type(value) is not str or not value:
        return False
    path = Path(value)
    if not path.is_absolute() or os.path.normpath(value) != value.rstrip("/") or "\x00" in value:
        return False
    try:
        return not path.is_symlink()
    except OSError:
        return False


def _identifier(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and all(character.isalnum() or character in "._-" for character in value)
    )


def _digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "MAX_RUNTIME_SOURCE_ENTRIES",
    "RUNTIME_PROJECTION_SPEC_SCHEMA",
    "SubjectiveMemRetrievalRuntimeProjection",
    "SubjectiveMemRetrievalRuntimeProjectionSpec",
    "acquire_subjective_mem_retrieval_runtime_projection",
    "subjective_mem_retrieval_runtime_projection_spec",
    "verify_subjective_mem_retrieval_runtime_projection",
]
