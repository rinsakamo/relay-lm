"""RT-1B disposable Subjective MEM retrieval projection builder and rebuild.

This module owns one responsibility accepted by ``docs/architecture/subjective-
mem-retrieval-projection-hard-cutover.md``: deriving one complete,
single-generation, content-free retrieval projection from one fixed source
snapshot of canonical Subjective MEM authority, and persisting it as one
disposable replace-only local bundle.

It does not acquire the snapshot: enumerating an evidence space or workspace,
locking, and loading canonical pages, selectors, receipts, and authorization
records stay with their existing owners. It performs no ordinary Retrieval,
ranking, query matching, grounding handoff, durable usage write, Primary MEM
access, characterization comparison, request-path wiring, or background rebuild.

Every fact reported here is read through its current owner: canonical Markdown
parsing, the ``SubjectiveMemCurrentState`` round-trip, the authorization record
schemas, and the merged RT-1A row/manifest identity and validation. No second
selector, receipt evaluator, lifecycle evaluator, or canonical representation is
introduced; this module verifies only that the exact records named by the exact
canonical revision are present and mutually bound, reports each outcome as one
RT-1A row flag, and returns ``(value_or_none, reasons)`` instead of raising.
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, fields
from pathlib import Path

from relaylm.evidence_common import canonical_digest, canonical_json_bytes, dedupe, sha256_hex
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_CURRENT_STATE_SCHEMA, SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA,
    SUBJECTIVE_MEM_DECISION_SCHEMA, SUBJECTIVE_MEM_REVISION_SCHEMA, SubjectiveMemCurrentState,
)
from relaylm.subjective_mem_lifecycle import LIFECYCLE_TRANSITION_SCHEMA
from relaylm.subjective_mem_markdown import (
    BLOCK_SCHEMA, LIFECYCLE_BLOCK_SCHEMA, MAX_CANONICAL_PAGE_BYTES, PAGE_PARTITION_REVISION,
    PAGE_SCHEMA, RENDERER_REVISION, SubjectiveMemMarkdownBlock, SubjectiveMemMarkdownPage,
    canonical_page_digest, parse_subjective_mem_page_bytes, subjective_mem_block_identity,
)
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
)

SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA = "relaylm.subjective_mem_retrieval_projection_source.v1"
SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA = "relaylm.subjective_mem_retrieval_projection_bundle.v1"
PROJECTION_BUNDLE_FILENAME = "subjective-mem-retrieval-projection.json"
PROJECTION_GENERATION_PREFIX = "smretrievalgen_"
MAX_PROJECTION_SOURCE_ENTRIES = 512
MAX_PROJECTION_BUNDLE_BYTES = 4 * 1024 * 1024

SUPPORTED_CURRENT_STATE_SCHEMAS = (SUBJECTIVE_MEM_CURRENT_STATE_SCHEMA, SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA)
SUPPORTED_SOURCE_REVISIONS: dict[str, object] = {
    "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA,
    "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
    "current_state_schemas": list(SUPPORTED_CURRENT_STATE_SCHEMAS),
    "page_schema": PAGE_SCHEMA,
    "block_schemas": [BLOCK_SCHEMA, LIFECYCLE_BLOCK_SCHEMA],
    "renderer_revision": RENDERER_REVISION,
    "partition_revision": PAGE_PARTITION_REVISION,
    "decision_schema": SUBJECTIVE_MEM_DECISION_SCHEMA,
    "transition_schema": LIFECYCLE_TRANSITION_SCHEMA,
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
_MANIFEST_FIELDS = tuple(item.name for item in fields(SubjectiveMemRetrievalProjectionManifest))
_ROW_FIELDS = tuple(item.name for item in fields(SubjectiveMemRetrievalProjectionRow))


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjectionSourceEntry:
    """One candidate memory's complete canonical authority material.

    The entry carries the canonical page image the revision lives in rather than
    a workspace or page path, so the snapshot stays a fixed value and the builder
    never resolves a filesystem location.
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

    ``snapshot_taken_at`` binds build time to the snapshot, so a rebuild reproduces
    the same manifest identity and no wall clock enters projection identity.
    """

    character_id: str
    workspace_authority_digest: str
    admitted_scope_binding_digest: str
    snapshot_taken_at: str
    entries: tuple[SubjectiveMemRetrievalProjectionSourceEntry, ...]

    def to_digest_input(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA,
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

    def to_dict(self) -> dict[str, object]:
        """Serialize the content-free bundle with its own authentication tag."""

        body = {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA,
            "manifest": self.manifest.to_digest_input(),
            "rows": [row.to_digest_input() for row in self.rows],
            "canonical_authority": False,
            "rebuildable": True,
        }
        return {**body, "bundle_digest": canonical_digest(body)}


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
        _derive_row(item, source=source, generation_id=generation_id, unresolved_pages=unresolved_pages)
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
    """Reject a snapshot that is not one bounded, well-formed fixed value."""
    if type(source) is not SubjectiveMemRetrievalProjectionSource:
        return ("subjective_mem_retrieval_projection_source_invalid",)
    reasons: list[str] = []
    if not isinstance(source.character_id, str) or not source.character_id:
        reasons.append("subjective_mem_retrieval_projection_source_identifier_invalid")
    if not _digest(source.workspace_authority_digest) or not _digest(source.admitted_scope_binding_digest):
        reasons.append("subjective_mem_retrieval_projection_source_digest_invalid")
    if not isinstance(source.snapshot_taken_at, str) or not source.snapshot_taken_at:
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
    return dedupe(reasons)


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
            reasons.append("subjective_mem_retrieval_projection_source_selector_duplicated")
            continue
        seen.add(logical)
        resolved.append(candidate)
    return (None, dedupe(reasons)) if reasons else (tuple(resolved), ())


def _resolve_candidate(
    entry: SubjectiveMemRetrievalProjectionSourceEntry,
    *,
    source: SubjectiveMemRetrievalProjectionSource,
) -> tuple[_Candidate | None, tuple[str, ...]]:
    """Bind one selector to its exact canonical revision inside one exact page."""
    raw = entry.current_selector_record
    state = _current_state(raw)
    if state is None or raw.get("schema") not in SUPPORTED_CURRENT_STATE_SCHEMAS:
        return None, ("subjective_mem_retrieval_projection_source_selector_invalid",)
    if state.character_id != source.character_id:
        return None, ("subjective_mem_retrieval_projection_source_character_foreign",)
    if state.authority_bound and state.workspace_authority_digest != source.workspace_authority_digest:
        return None, ("subjective_mem_retrieval_projection_source_workspace_foreign",)
    page, _parse_reasons = parse_subjective_mem_page_bytes(
        entry.canonical_page_bytes, expected_character_id=source.character_id
    )
    if page is None:
        return None, ("subjective_mem_retrieval_projection_source_page_unsupported",)
    blocks = [item for item in page.blocks if item.revision.memory_id == state.memory_id]
    current = [item for item in blocks if item.revision.memory_revision == state.current_revision]
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
    legacy = revision.authorization_kind == "formation_decision"
    scope_digest = canonical_digest(revision.scope_binding.to_dict())
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
        current_receipt_id=_text(receipt.get("receipt_id")),
        current_receipt_digest=_text(receipt.get("receipt_digest")),
        authorization_record_kind=(
            "subjective_mem_decision" if legacy else "subjective_mem_lifecycle_transition"
        ),
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
        finalized_receipt_verified=_receipt_verified(candidate),
        authorization_verified=_authorization_verified(candidate),
        canonical_binding_verified=_canonical_binding_verified(candidate),
        scope_admitted=scope_digest == source.admitted_scope_binding_digest,
        unresolved_intent_present=page.page_id in unresolved_pages,
        source_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        source_current_state_schema=_text(candidate.entry.current_selector_record.get("schema")),
        source_page_schema=PAGE_SCHEMA,
        source_block_schema=(
            BLOCK_SCHEMA if legacy and revision.memory_revision == 1 else LIFECYCLE_BLOCK_SCHEMA
        ),
        source_renderer_revision=RENDERER_REVISION,
        source_partition_revision=PAGE_PARTITION_REVISION,
        source_platform_revision=_text(receipt.get("platform_revision")),
        projection_policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )


def _receipt_verified(candidate: _Candidate) -> bool:
    """Bind the finalized receipt to this exact selector state and revision.

    The receipt's published page image is the page as it stood at its own
    commit and changes whenever a later memory is appended to the same
    canonical page, so currentness binds through the exact selector digest and
    memory reference instead. Transition legality stays with its owner.
    """

    receipt = candidate.entry.current_receipt_record
    memory_ref = receipt.get("memory_ref")
    state, revision = candidate.state, candidate.block.revision
    return (
        _self_digest_exact(receipt)
        and receipt.get("operation_outcome") == "committed"
        and receipt.get("character_id") == revision.character_id
        and isinstance(memory_ref, dict)
        and memory_ref.get("memory_id") == revision.memory_id
        and memory_ref.get("memory_revision") == revision.memory_revision
        and receipt.get("current_state_digest") == candidate.selector_digest
        and (not state.authority_bound or receipt.get("receipt_id") == state.current_receipt_id)
    )


def _authorization_verified(candidate: _Candidate) -> bool:
    """Bind the authorizing decision or transition to this exact revision."""
    record = candidate.entry.authorization_record
    receipt = candidate.entry.current_receipt_record
    revision = candidate.block.revision
    if revision.authorization_kind == "formation_decision":
        result = record.get("result_memory_ref_or_null")
        return (
            record.get("schema") == SUBJECTIVE_MEM_DECISION_SCHEMA
            and record.get("decision_id") == revision.authorization_id
            and receipt.get("decision_id") == revision.authorization_id
            and record.get("character_id") == revision.character_id
            and isinstance(result, dict)
            and result.get("memory_id") == revision.memory_id
            and result.get("memory_revision") == 1
        )
    return (
        record.get("schema") == LIFECYCLE_TRANSITION_SCHEMA
        and record.get("transition_id") == revision.authorization_id
        and receipt.get("transition_id") == revision.authorization_id
        and record.get("character_id") == revision.character_id
        and record.get("memory_id") == revision.memory_id
        and record.get("to_revision") == revision.memory_revision
        and record.get("to_lifecycle_state") == revision.lifecycle_state
    )


def _canonical_binding_verified(candidate: _Candidate) -> bool:
    """Bind the selector to the exact canonical block it declares as current."""
    state, block, page = candidate.state, candidate.block, candidate.page
    revision = block.revision
    expected_block_id, _anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    if block.block_id != expected_block_id or revision.lifecycle_state != state.lifecycle_state:
        return False
    if not state.authority_bound:
        return True
    return (
        state.page_id == page.page_id
        and state.block_id == block.block_id
        and state.authorization_kind == revision.authorization_kind
        and state.authorization_id == revision.authorization_id
        and state.scope_binding_digest == canonical_digest(revision.scope_binding.to_dict())
    )


def load_subjective_mem_retrieval_projection(
    payload: object, *, source: object = None
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Authenticate and fully revalidate one serialized projection bundle.

    No serialized derived field is trusted: every row digest and the manifest
    population are recomputed from the deserialized bodies, and a supplied
    ``source`` must be the exact snapshot the bundle was built from. There is no
    repair-on-read, partial acceptance, or stale-generation fallback.
    """

    body = _authenticated_bundle_body(payload)
    if body is None:
        return None, ("subjective_mem_retrieval_projection_bundle_tampered",)
    manifest = _manifest_from_body(body.get("manifest"))
    raw_rows = body.get("rows")
    if manifest is None or not isinstance(raw_rows, list):
        return None, ("subjective_mem_retrieval_projection_bundle_shape_invalid",)
    rows: list[SubjectiveMemRetrievalProjectionRow] = []
    for raw in raw_rows:
        row = _row_from_body(raw)
        if row is None:
            return None, ("subjective_mem_retrieval_projection_bundle_shape_invalid",)
        rows.append(row)

    reasons = list(validate_subjective_mem_retrieval_projection_manifest(manifest))
    for row in rows:
        reasons.extend(validate_subjective_mem_retrieval_projection_row(row))
    if any(row.projection_generation_id != manifest.projection_generation_id for row in rows):
        reasons.append("subjective_mem_retrieval_projection_mixed_generation")
    digests = tuple(row.row_digest for row in rows)
    if len(set(digests)) != len(digests):
        reasons.append("subjective_mem_retrieval_projection_row_duplicated")
    elif digests != tuple(sorted(digests)) or digests != manifest.row_digests:
        reasons.append("subjective_mem_retrieval_projection_population_mismatch")
    if manifest.source_schema_revision_digest != SOURCE_SCHEMA_REVISION_DIGEST:
        reasons.append("subjective_mem_retrieval_projection_source_revision_unsupported")
    reasons.extend(_source_binding_reasons(manifest, source))
    if reasons:
        return None, dedupe(reasons)
    return SubjectiveMemRetrievalProjection(manifest=manifest, rows=tuple(rows)), ()


def _source_binding_reasons(
    manifest: SubjectiveMemRetrievalProjectionManifest, source: object
) -> tuple[str, ...]:
    """Refuse any generation that is not the one this exact snapshot builds."""
    if source is None:
        return ()
    if type(source) is not SubjectiveMemRetrievalProjectionSource or _validate_source(source):
        return ("subjective_mem_retrieval_projection_source_invalid",)
    if (
        manifest.projection_generation_id != source.projection_generation_id
        or manifest.source_snapshot_digest != source.source_snapshot_digest
    ):
        return ("subjective_mem_retrieval_projection_stale_generation",)
    return ()


def write_subjective_mem_retrieval_projection(
    *, projection_root: str, projection: object
) -> tuple[str, ...]:
    """Replace the one disposable projection bundle stored under this root."""
    target, reasons = _bundle_path(projection_root)
    if target is None:
        return reasons
    if type(projection) is not SubjectiveMemRetrievalProjection:
        return ("subjective_mem_retrieval_projection_invalid",)
    payload = projection.to_dict()
    loaded, reasons = load_subjective_mem_retrieval_projection(payload)
    if loaded is None:
        return reasons
    data = canonical_json_bytes(payload)
    if len(data) > MAX_PROJECTION_BUNDLE_BYTES:
        return ("subjective_mem_retrieval_projection_bundle_oversize",)
    return _atomic_replace(target, data)


def read_subjective_mem_retrieval_projection(
    *, projection_root: str, source: object = None
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Read, authenticate, and revalidate the persisted projection bundle."""
    target, reasons = _bundle_path(projection_root)
    if target is None:
        return None, reasons
    try:
        info = target.lstat()
    except FileNotFoundError:
        return None, ("subjective_mem_retrieval_projection_absent",)
    except OSError:
        return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return None, ("subjective_mem_retrieval_projection_bundle_unsafe",)
    if info.st_size > MAX_PROJECTION_BUNDLE_BYTES:
        return None, ("subjective_mem_retrieval_projection_bundle_oversize",)
    try:
        payload = json.loads(target.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
    return load_subjective_mem_retrieval_projection(payload, source=source)


def delete_subjective_mem_retrieval_projection(*, projection_root: str) -> tuple[str, ...]:
    """Delete the disposable projection bundle, touching no canonical authority."""
    target, reasons = _bundle_path(projection_root)
    if target is None:
        return reasons
    try:
        os.unlink(target)
    except FileNotFoundError:
        return ()
    except OSError:
        return ("subjective_mem_retrieval_projection_delete_failed",)
    return ()


def _bundle_path(projection_root: object) -> tuple[Path | None, tuple[str, ...]]:
    """Resolve the one bundle path under a bounded, non-symlinked absolute root."""
    if type(projection_root) is not str or not projection_root:
        return None, ("subjective_mem_retrieval_projection_root_missing",)
    path = Path(projection_root)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts[1:]):
        return None, ("subjective_mem_retrieval_projection_root_invalid",)
    try:
        if path.is_symlink() or not path.is_dir():
            return None, ("subjective_mem_retrieval_projection_root_unsafe",)
    except OSError:
        return None, ("subjective_mem_retrieval_projection_root_unsafe",)
    return path / PROJECTION_BUNDLE_FILENAME, ()


def _atomic_replace(target: Path, data: bytes) -> tuple[str, ...]:
    """Install the bundle atomically so no partial generation is ever readable."""
    temp = target.with_name(f".{target.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(temp, flags, 0o600)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temp, target)
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        return ("subjective_mem_retrieval_projection_write_failed",)
    return ()


def _authenticated_bundle_body(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    body = {key: value for key, value in payload.items() if key != "bundle_digest"}
    if (
        body.get("schema") != SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA
        or body.get("canonical_authority") is not False
        or body.get("rebuildable") is not True
    ):
        return None
    try:
        expected = canonical_digest(body)
    except (TypeError, ValueError):
        return None
    return body if payload.get("bundle_digest") == expected else None


def _manifest_from_body(body: object) -> SubjectiveMemRetrievalProjectionManifest | None:
    if not isinstance(body, dict) or not isinstance(body.get("row_digests"), (list, tuple)):
        return None
    values = {**body, "row_digests": tuple(body["row_digests"])}
    try:
        manifest = SubjectiveMemRetrievalProjectionManifest(
            **{name: values[name] for name in _MANIFEST_FIELDS}
        )
    except (KeyError, TypeError):
        return None
    return manifest if manifest.to_digest_input() == values else None


def _row_from_body(body: object) -> SubjectiveMemRetrievalProjectionRow | None:
    if not isinstance(body, dict):
        return None
    try:
        row = SubjectiveMemRetrievalProjectionRow(**{name: body[name] for name in _ROW_FIELDS})
    except (KeyError, TypeError):
        return None
    return row if row.to_digest_input() == body else None


def _current_state(raw: object) -> SubjectiveMemCurrentState | None:
    """Reconstruct one selector, keeping the domain object the sole authority.

    The exact ``to_dict()`` round-trip means every invariant, including the
    lifecycle/mutation/eligibility triple and the authority-binding
    completeness rule, is enforced by ``SubjectiveMemCurrentState`` itself.
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


def _self_digest_exact(record: dict[str, object]) -> bool:
    digest = record.get("receipt_digest")
    body = {key: value for key, value in record.items() if key != "receipt_digest"}
    try:
        return isinstance(digest, str) and digest == canonical_digest(body)
    except (TypeError, ValueError):
        return False


def _record(value: object) -> bool:
    return isinstance(value, dict) and bool(value)


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


__all__ = [
    "MAX_PROJECTION_BUNDLE_BYTES", "MAX_PROJECTION_SOURCE_ENTRIES", "PROJECTION_BUNDLE_FILENAME",
    "PROJECTION_GENERATION_PREFIX", "SOURCE_SCHEMA_REVISION_DIGEST",
    "SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_SOURCE_SCHEMA", "SUPPORTED_CURRENT_STATE_SCHEMAS",
    "SUPPORTED_SOURCE_REVISIONS", "SubjectiveMemRetrievalProjection",
    "SubjectiveMemRetrievalProjectionSource", "SubjectiveMemRetrievalProjectionSourceEntry",
    "build_subjective_mem_retrieval_projection", "delete_subjective_mem_retrieval_projection",
    "load_subjective_mem_retrieval_projection", "read_subjective_mem_retrieval_projection",
    "write_subjective_mem_retrieval_projection",
]
