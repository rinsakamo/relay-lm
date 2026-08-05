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

from .evidence_common import canonical_digest
from .evidence_store import EvidenceRecordStore
from .subjective_mem_markdown import subjective_mem_page_identity
from .subjective_mem_retrieval_projection import (
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
CURRENT_STATE_V2_SCHEMA = "relaylm.subjective_mem_current_state.v2"
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
    workspace = {selector["authority_binding"]["workspace_authority_digest"] for selector in selectors}
    scopes = {selector["authority_binding"]["scope_binding_digest"] for selector in selectors}
    if len(workspace) != 1 or len(scopes) != 1:
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
    """Enumerate this character's exact retrieval-eligible current selectors."""

    inventory = transaction.list_logs(
        log_kind=CURRENT_STATE_LOG_KIND, limit=MAX_RUNTIME_SOURCE_ENTRIES + 1
    )
    if len(inventory) > MAX_RUNTIME_SOURCE_ENTRIES:
        return None, ("subjective_mem_retrieval_runtime_source_too_large",)
    selected: list[dict] = []
    logical: set[str] = set()
    for _key, records in inventory:
        if type(records) is not list or len(records) != 1:
            return None, ("subjective_mem_retrieval_runtime_selector_ambiguous",)
        selector = records[0]
        if not _eligible(selector, spec.character_id):
            continue
        memory_id = selector["memory_id"]
        if memory_id in logical:
            return None, ("subjective_mem_retrieval_runtime_selector_duplicated",)
        logical.add(memory_id)
        selected.append(selector)
    if not selected:
        return None, ("subjective_mem_retrieval_runtime_source_empty",)
    return sorted(selected, key=lambda item: item["memory_state_id"]), ()


def _eligible(selector: object, character_id: str) -> bool:
    """Admit only an exact, authority-bound, retrieval-eligible V2 selector."""

    if type(selector) is not dict or selector.get("schema") != CURRENT_STATE_V2_SCHEMA:
        return False
    binding = selector.get("authority_binding")
    if type(binding) is not dict:
        return False
    reference = binding.get("authorization_ref")
    if type(reference) is not dict:
        return False
    return (
        selector.get("character_id") == character_id
        and selector.get("retrieval_eligible") is True
        and selector.get("mutation_state") == "none"
        and _identifier(selector.get("memory_id"))
        and _identifier(selector.get("memory_state_id"))
        and type(selector.get("current_revision")) is int
        and selector["current_revision"] >= 1
        and _identifier(binding.get("page_id"))
        and _digest(binding.get("workspace_authority_digest"))
        and _digest(binding.get("scope_binding_digest"))
        and _identifier(binding.get("current_receipt_id"))
        and reference.get("authority_kind") in _AUTHORIZATION_KINDS
        and _identifier(reference.get("authority_id"))
    )


def _entries(
    transaction: object,
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    selectors: list[dict],
) -> tuple[tuple[SubjectiveMemRetrievalProjectionSourceEntry, ...] | None, tuple[str, ...]]:
    """Load each selector's exact receipt, authorization, and canonical page."""

    pages: dict[str, bytes] = {}
    entries: list[SubjectiveMemRetrievalProjectionSourceEntry] = []
    for selector in selectors:
        binding = selector["authority_binding"]
        reference = binding["authorization_ref"]
        receipt_kind = _RECEIPT_KINDS[1 if selector["current_revision"] == 1 else 2]
        receipt = transaction.read_record(
            record_kind=receipt_kind, record_id=binding["current_receipt_id"]
        )
        authorization = transaction.read_record(
            record_kind=_AUTHORIZATION_KINDS[reference["authority_kind"]],
            record_id=reference["authority_id"],
        )
        if type(receipt) is not dict or type(authorization) is not dict:
            return None, ("subjective_mem_retrieval_runtime_authority_missing",)
        image, reasons = _page_bytes(spec, pages, binding["page_id"])
        if image is None:
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


def _page_bytes(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    pages: dict[str, bytes],
    page_id: str,
) -> tuple[bytes | None, tuple[str, ...]]:
    """Read one supported canonical page exactly once per acquisition."""

    if page_id in pages:
        return pages[page_id], ()
    relative = _page_path(spec.character_id, page_id)
    if relative is None:
        return None, ("subjective_mem_retrieval_runtime_page_unsupported",)
    target = Path(spec.workspace_root) / spec.character_id / relative
    try:
        if target.is_symlink() or not target.is_file():
            return None, ("subjective_mem_retrieval_runtime_page_unsupported",)
        image = target.read_bytes()
    except OSError:
        return None, ("subjective_mem_retrieval_runtime_page_unreadable",)
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
