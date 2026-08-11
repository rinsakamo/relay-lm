"""RT-1B disposable Subjective MEM retrieval projection builder and rebuild.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: derive one complete, single-generation, content-free retrieval
projection from one fixed source snapshot of canonical Subjective MEM authority.

The snapshot is not acquired here; evidence-space or workspace enumeration,
locking, and record loading stay with their owners. There is no ordinary
Retrieval, ranking, grounding handoff, durable usage write, Primary MEM access,
characterization, request-path wiring, or background rebuild.

Every fact is read through its current owner, and committed receipt and
authorization exactness is delegated to
``relaylm.subjective_mem.lifecycle_authority`` so exactly one committed-authority
evaluator exists. No lifecycle, receipt, or authorization semantics are
evaluated here: this module resolves which exact records a selector names, asks
the owner whether they are exact, and reports each answer as one RT-1A row flag.

This module derives the projection value only. Disposable persistence, bundle
decoding, and source-bound trusted loading live in
``relaylm.subjective_mem.retrieval_projection_store``, which depends on this
owner and never the other way round. Nothing here raises for rejected input.
"""
from __future__ import annotations

from dataclasses import dataclass

from relaylm.evidence.common import canonical_digest, canonical_json_bytes, dedupe, sha256_hex
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA, SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCurrentState,
)
from relaylm.subjective_mem.lifecycle_authority import (
    SubjectiveMemPredecessorExpectation, subjective_mem_committed_authorization_ref,
    validate_subjective_mem_committed_authorization, validate_subjective_mem_committed_receipt,
)
from relaylm.subjective_mem.markdown import (
    BLOCK_SCHEMA, LIFECYCLE_BLOCK_SCHEMA, MAX_CANONICAL_PAGE_BYTES, PAGE_PARTITION_REVISION,
    PAGE_SCHEMA, RENDERER_REVISION, SubjectiveMemMarkdownBlock, SubjectiveMemMarkdownPage,
    canonical_page_digest, parse_subjective_mem_page_bytes, subjective_mem_block_identity,
)
from relaylm.subjective_mem.retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
)

SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA = "relaylm.subjective_mem_retrieval_projection_source.v1"
PROJECTION_GENERATION_PREFIX = "smretrievalgen_"
MAX_PROJECTION_SOURCE_ENTRIES = 512

SUPPORTED_SOURCE_REVISIONS: dict[str, object] = {
    "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA,
    "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
    "current_state_schema": SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA,
    "page_schema": PAGE_SCHEMA,
    "block_schemas": [BLOCK_SCHEMA, LIFECYCLE_BLOCK_SCHEMA],
    "renderer_revision": RENDERER_REVISION,
    "partition_revision": PAGE_PARTITION_REVISION,
    "projection_policy_revision": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
}
SOURCE_SCHEMA_REVISION_DIGEST = canonical_digest(SUPPORTED_SOURCE_REVISIONS)

_SELECTOR_FIELDS = (
    "memory_state_id", "memory_id", "character_id", "current_revision",
    "lifecycle_state", "mutation_state", "retrieval_eligible", "updated_at",
)
_SELECTOR_BINDING_FIELDS = (
    "workspace_authority_digest", "scope_binding_digest", "page_id", "block_id",
    "canonical_page_digest", "current_receipt_id",
)


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjectionSourceEntry:
    """One candidate memory's complete canonical authority material.

    The entry carries the canonical page image rather than a workspace or page
    path, so the snapshot stays a fixed value and no location is resolved.
    """

    canonical_page_bytes: bytes
    current_selector_record: dict[str, object]
    current_receipt_record: dict[str, object]
    authorization_record: dict[str, object]

    def to_digest_input(self) -> dict[str, object]:
        return {
            "canonical_page_digest": canonical_page_digest(self.canonical_page_bytes),
            "current_selector_record": self.current_selector_record,
            "current_receipt_record": self.current_receipt_record,
            "authorization_record": self.authorization_record,
        }

    @property
    def entry_digest(self) -> str:
        return canonical_digest(self.to_digest_input())


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjectionSource:
    """One fixed supported source snapshot for exactly one projection generation.

    ``snapshot_taken_at`` binds build time to the snapshot, so no wall clock
    enters projection identity. ``evidence_space_id`` is the partition the
    receipts were finalized in and is checked by the shared authority owner.
    """

    evidence_space_id: str
    character_id: str
    workspace_authority_digest: str
    admitted_scope_binding_digest: str
    snapshot_taken_at: str
    entries: tuple[SubjectiveMemRetrievalProjectionSourceEntry, ...]

    def to_digest_input(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA,
            "evidence_space_id": self.evidence_space_id,
            "character_id": self.character_id,
            "workspace_authority_digest": self.workspace_authority_digest,
            "admitted_scope_binding_digest": self.admitted_scope_binding_digest,
            "snapshot_taken_at": self.snapshot_taken_at,
            "entry_digests": sorted(item.entry_digest for item in self.entries),
            "source_schema_revision_digest": SOURCE_SCHEMA_REVISION_DIGEST,
        }

    @property
    def source_snapshot_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def projection_generation_id(self) -> str:
        material = self.source_snapshot_digest + "\x00" + SOURCE_SCHEMA_REVISION_DIGEST
        return PROJECTION_GENERATION_PREFIX + sha256_hex(material.encode("utf-8"))


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjection:
    """One complete, single-generation, disposable and noncanonical projection."""

    manifest: SubjectiveMemRetrievalProjectionManifest
    rows: tuple[SubjectiveMemRetrievalProjectionRow, ...]


@dataclass(frozen=True)
class _Candidate:
    """One resolved entry whose selector and canonical revision were located."""

    entry: SubjectiveMemRetrievalProjectionSourceEntry
    state: SubjectiveMemCurrentState
    selector_digest: str
    page: SubjectiveMemMarkdownPage
    block: SubjectiveMemMarkdownBlock
    latest_revision: int


def build_subjective_mem_retrieval_projection(
    source: object,
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Derive one complete projection generation from one fixed source snapshot."""

    invalid = _validate_source(source)
    if invalid:
        return None, invalid
    assert isinstance(source, SubjectiveMemRetrievalProjectionSource)
    candidates, unresolvable = _resolve_candidates(source)
    if candidates is None:
        return None, unresolvable

    unresolved_pages = {
        item.page.page_id for item in candidates if item.state.mutation_state != "none"
    }
    generation_id = source.projection_generation_id
    rows = tuple(
        _derive_row(
            item,
            source=source,
            generation_id=generation_id,
            unresolved_pages=unresolved_pages,
        )
        for item in candidates
    )
    reasons: list[str] = []
    for row in rows:
        reasons.extend(validate_subjective_mem_retrieval_projection_row(row))
    digests = tuple(row.row_digest for row in rows)
    if len(set(digests)) != len(digests):
        reasons.append("subjective_mem_retrieval_projection_row_duplicated")
    if reasons:
        return None, dedupe(reasons)

    manifest = SubjectiveMemRetrievalProjectionManifest(
        projection_generation_id=generation_id,
        source_snapshot_digest=source.source_snapshot_digest,
        source_schema_revision_digest=SOURCE_SCHEMA_REVISION_DIGEST,
        row_digests=tuple(sorted(digests)),
        built_at=source.snapshot_taken_at,
        complete=True,
        mixed_generation=False,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )
    invalid = validate_subjective_mem_retrieval_projection_manifest(manifest)
    if invalid:
        return None, invalid
    ordered = tuple(sorted(rows, key=lambda item: item.row_digest))
    return SubjectiveMemRetrievalProjection(manifest=manifest, rows=ordered), ()


def _validate_source(source: object) -> tuple[str, ...]:
    """Reject a snapshot that is not one bounded, well-formed, canonical value."""

    if type(source) is not SubjectiveMemRetrievalProjectionSource:
        return ("subjective_mem_retrieval_projection_source_invalid",)
    reasons: list[str] = []
    if not _text_value(source.evidence_space_id) or not _text_value(source.character_id):
        reasons.append("subjective_mem_retrieval_projection_source_identifier_invalid")
    if not _digest(source.workspace_authority_digest) or not _digest(
        source.admitted_scope_binding_digest
    ):
        reasons.append("subjective_mem_retrieval_projection_source_digest_invalid")
    if not _text_value(source.snapshot_taken_at):
        reasons.append("subjective_mem_retrieval_projection_source_time_invalid")
    entries = source.entries
    if type(entries) is not tuple or len(entries) > MAX_PROJECTION_SOURCE_ENTRIES or any(
        type(entry) is not SubjectiveMemRetrievalProjectionSourceEntry
        or type(entry.canonical_page_bytes) is not bytes
        or len(entry.canonical_page_bytes) > MAX_CANONICAL_PAGE_BYTES
        or not _record(entry.current_selector_record)
        or not _record(entry.current_receipt_record)
        or not _record(entry.authorization_record)
        for entry in entries
    ):
        reasons.append("subjective_mem_retrieval_projection_source_entries_invalid")
    if reasons:
        return dedupe(reasons)
    return _canonicalizable(source)


def _canonicalizable(source: SubjectiveMemRetrievalProjectionSource) -> tuple[str, ...]:
    """Prove every identity-bearing source value encodes before any digest use.

    ``canonical_json_bytes`` rejects unsupported types on serialization,
    non-finite numbers on the finite check, and text that cannot be encoded —
    invalid lone surrogates in particular — on the trailing UTF-8 encode.
    ``UnicodeEncodeError`` names that last stage explicitly; it is already a
    ``ValueError`` subclass, so listing it widens nothing and only records which
    failure each caught class stands for. No malformed source value can escape
    as an exception from a later sort or digest.
    """

    try:
        for entry in source.entries:
            canonical_json_bytes(entry.to_digest_input())
        canonical_json_bytes(source.to_digest_input())
    except (TypeError, UnicodeEncodeError, ValueError):
        return ("subjective_mem_retrieval_projection_source_not_canonical",)
    return ()


def _resolve_candidates(
    source: SubjectiveMemRetrievalProjectionSource,
) -> tuple[tuple[_Candidate, ...] | None, tuple[str, ...]]:
    """Resolve every entry deterministically and fail closed on any conflict."""

    resolved: list[_Candidate] = []
    reasons: list[str] = []
    seen: set[tuple[str, str]] = set()
    for entry in sorted(source.entries, key=lambda item: item.entry_digest):
        candidate, entry_reasons = _resolve_candidate(entry, source=source)
        if candidate is None:
            reasons.extend(entry_reasons)
            continue
        logical = (candidate.state.character_id, candidate.state.memory_id)
        if logical in seen:
            reasons.append(
                "subjective_mem_retrieval_projection_source_selector_duplicated"
            )
            continue
        seen.add(logical)
        resolved.append(candidate)
    return (None, dedupe(reasons)) if reasons else (tuple(resolved), ())


def _resolve_candidate(
    entry: SubjectiveMemRetrievalProjectionSourceEntry,
    *,
    source: SubjectiveMemRetrievalProjectionSource,
) -> tuple[_Candidate | None, tuple[str, ...]]:
    """Bind one selector to its exact canonical revision inside one exact page.

    Only a complete RT-1 authority-bound selector is supported; a legacy unbound
    selector cannot name its page, block, receipt, and authorization, so it is
    refused rather than projected as exact.
    """

    raw = entry.current_selector_record
    state = _current_state(raw)
    if state is None:
        return None, ("subjective_mem_retrieval_projection_source_selector_invalid",)
    if not state.authority_bound or (
        raw.get("schema") != SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA
    ):
        return None, ("subjective_mem_retrieval_projection_source_selector_unbound",)
    if state.character_id != source.character_id:
        return None, ("subjective_mem_retrieval_projection_source_character_foreign",)
    if state.workspace_authority_digest != source.workspace_authority_digest:
        return None, ("subjective_mem_retrieval_projection_source_workspace_foreign",)
    page, _parse_reasons = parse_subjective_mem_page_bytes(
        entry.canonical_page_bytes, expected_character_id=source.character_id
    )
    if page is None:
        return None, ("subjective_mem_retrieval_projection_source_page_unsupported",)
    blocks = [
        item for item in page.blocks if item.revision.memory_id == state.memory_id
    ]
    current = [
        item
        for item in blocks
        if item.revision.memory_revision == state.current_revision
    ]
    if not blocks or len(current) != 1:
        return None, ("subjective_mem_retrieval_projection_source_revision_missing",)
    return (
        _Candidate(
            entry=entry,
            state=state,
            selector_digest=canonical_digest(raw),
            page=page,
            block=current[0],
            latest_revision=max(item.revision.memory_revision for item in blocks),
        ),
        (),
    )


def _derive_row(
    candidate: _Candidate,
    *,
    source: SubjectiveMemRetrievalProjectionSource,
    generation_id: str,
    unresolved_pages: set[str],
) -> SubjectiveMemRetrievalProjectionRow:
    """Project one candidate as one content-free RT-1A row.

    Nothing content-bearing crosses the boundary: grounded content, subjective
    meaning, page paths, and workspace locations stay in the canonical sources,
    and only opaque identifiers, digests, and bounded state reach the row.
    """

    state, page, block = candidate.state, candidate.page, candidate.block
    revision = block.revision
    receipt = candidate.entry.current_receipt_record
    scope_digest = canonical_digest(revision.scope_binding.to_dict())
    record_kind, receipt_exact, authorization_exact = _committed_authority(
        candidate, source=source
    )
    return SubjectiveMemRetrievalProjectionRow(
        projection_generation_id=generation_id,
        character_id=source.character_id,
        memory_id=revision.memory_id,
        memory_revision=revision.memory_revision,
        page_id=page.page_id,
        block_id=block.block_id,
        canonical_page_digest=page.page_digest,
        block_digest=block.block_digest.removeprefix("sha256:"),
        revision_digest=block.revision_digest,
        current_selector_id=state.memory_state_id,
        current_selector_digest=candidate.selector_digest,
        current_receipt_id=_text(state.current_receipt_id),
        current_receipt_digest=_text(receipt.get("receipt_digest")),
        authorization_record_kind=record_kind,
        authorization_id=revision.authorization_id,
        authorization_digest=canonical_digest(candidate.entry.authorization_record),
        workspace_authority_digest=source.workspace_authority_digest,
        scope_binding_digest=scope_digest,
        lifecycle_state=state.lifecycle_state,
        mutation_state=state.mutation_state,
        retrieval_eligible=state.retrieval_eligible,
        retrieval_visible=revision.retrieval_visible,
        memory_kind=revision.memory_kind,
        formation_stage=revision.formation_stage,
        current_selector_unambiguous=True,
        latest_persisted_revision=state.current_revision == candidate.latest_revision,
        finalized_receipt_verified=receipt_exact,
        authorization_verified=authorization_exact,
        canonical_binding_verified=_canonical_binding_verified(candidate),
        scope_admitted=scope_digest == source.admitted_scope_binding_digest,
        unresolved_intent_present=page.page_id in unresolved_pages,
        source_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        source_current_state_schema=SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA,
        source_page_schema=PAGE_SCHEMA,
        source_block_schema=_block_schema(candidate),
        source_renderer_revision=RENDERER_REVISION,
        source_partition_revision=PAGE_PARTITION_REVISION,
        source_platform_revision=_text(receipt.get("platform_revision")),
        projection_policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )


def _committed_authority(
    candidate: _Candidate, *, source: SubjectiveMemRetrievalProjectionSource
) -> tuple[str, bool, bool]:
    """Ask the shared committed-authority owner whether the named records are exact."""

    receipt = candidate.entry.current_receipt_record
    revision = candidate.block.revision
    receipt_reasons = validate_subjective_mem_committed_receipt(
        receipt=receipt,
        evidence_space_id=source.evidence_space_id,
        character_id=source.character_id,
        predecessor=revision,
        expectation=_expectation(candidate),
    )
    record_kind, identifier = subjective_mem_committed_authorization_ref(
        predecessor=revision, receipt=receipt
    )
    authorization_reasons = validate_subjective_mem_committed_authorization(
        authorization=candidate.entry.authorization_record,
        receipt=receipt,
        predecessor=revision,
    )
    named = identifier is not None and receipt.get("receipt_id") == (
        candidate.state.current_receipt_id
    )
    return record_kind, not receipt_reasons and named, not authorization_reasons


def _expectation(candidate: _Candidate) -> SubjectiveMemPredecessorExpectation:
    """Describe the exact committed publication the current selector declares.

    ``page_digest`` is the selector's recorded page image, which the owner
    compares with the receipt's post-image. Both are written by the same commit,
    so the pair binds exactly and survives later appends to the same page.
    """

    state, receipt = candidate.state, candidate.entry.current_receipt_record
    return SubjectiveMemPredecessorExpectation(
        receipt_id=_text(state.current_receipt_id),
        receipt_digest=_text(receipt.get("receipt_digest")),
        current_state_digest=candidate.selector_digest,
        page_id=candidate.page.page_id,
        block_id=candidate.block.block_id,
        page_digest=_text(state.canonical_page_digest),
        revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        page_schema=PAGE_SCHEMA,
        block_schema=_block_schema(candidate),
        renderer_revision=RENDERER_REVISION,
        partition_revision=PAGE_PARTITION_REVISION,
        platform_revision=_text(receipt.get("platform_revision")),
    )


def _block_schema(candidate: _Candidate) -> str:
    revision = candidate.block.revision
    legacy = revision.memory_revision == 1 and (
        revision.authorization_kind == "formation_decision"
    )
    return BLOCK_SCHEMA if legacy else LIFECYCLE_BLOCK_SCHEMA


def _canonical_binding_verified(candidate: _Candidate) -> bool:
    """Bind the selector to the exact canonical block it declares as current."""

    state, block, page = candidate.state, candidate.block, candidate.page
    revision = block.revision
    expected_block_id, _anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    return (
        block.block_id == expected_block_id
        and revision.lifecycle_state == state.lifecycle_state
        and state.page_id == page.page_id
        and state.block_id == block.block_id
        and state.authorization_kind == revision.authorization_kind
        and state.authorization_id == revision.authorization_id
        and state.scope_binding_digest
        == canonical_digest(revision.scope_binding.to_dict())
    )


def _current_state(raw: object) -> SubjectiveMemCurrentState | None:
    """Reconstruct one selector, keeping the domain object the sole authority.

    The exact ``to_dict()`` round-trip leaves every invariant, including the
    lifecycle/mutation/eligibility triple and the authority-binding rule, to
    ``SubjectiveMemCurrentState`` itself.
    """

    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    if binding is not None and not isinstance(binding, dict):
        return None
    reference = binding.get("authorization_ref") if isinstance(binding, dict) else None
    if reference is not None and not isinstance(reference, dict):
        return None
    bound = binding if isinstance(binding, dict) else {}
    authorization = reference if isinstance(reference, dict) else {}
    try:
        state = SubjectiveMemCurrentState(
            **{name: raw[name] for name in _SELECTOR_FIELDS},
            **{name: bound.get(name) for name in _SELECTOR_BINDING_FIELDS},
            authorization_kind=authorization.get("authority_kind"),
            authorization_id=authorization.get("authority_id"),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None


def _record(value: object) -> bool:
    return isinstance(value, dict) and bool(value)


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _text_value(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


__all__ = [
    "MAX_PROJECTION_SOURCE_ENTRIES", "PROJECTION_GENERATION_PREFIX",
    "SOURCE_SCHEMA_REVISION_DIGEST", "SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA",
    "SUPPORTED_SOURCE_REVISIONS", "SubjectiveMemRetrievalProjection",
    "SubjectiveMemRetrievalProjectionSource", "SubjectiveMemRetrievalProjectionSourceEntry",
    "build_subjective_mem_retrieval_projection",
]
