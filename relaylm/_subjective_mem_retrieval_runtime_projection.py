"""Private RT-1D-R4 ordinary-runtime Subjective MEM projection boundary.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: acquire one exact current ``SubjectiveMemRetrievalProjectionSource``
by orchestrating the existing canonical workspace, Evidence-store, selector,
receipt, and authorization owners; derive the exact projection through the
existing RT-1B builder; install or exact-verify one disposable live bundle in a
dedicated projection root through the existing projection store; trusted-read
that bundle against the same exact source; and return one immutable source,
projection, request, and canonical-page value.

No semantics are reimplemented here. This owner resolves which exact records a
selector names and hands them to their existing owners: the RT-1B builder alone
evaluates selector, receipt, authorization, lifecycle, and canonical-binding
exactness, and RT-1A alone owns the eligibility vocabulary. This module owns no
cutover semantics, transfer intent, fence, receipt, selection rule, usage-event
rule, canonical parser, lifecycle evaluator, Primary fallback, RelayCTX policy,
or retirement behaviour, and it is never a second current selector, receipt
validator, authorization evaluator, projection builder, projection store,
selection owner, usage ledger, or cutover authority.

The dependency direction is one-way: the ordinary route and the cutover facade
depend on this module; this module depends on the existing canonical source
authorities, ``relaylm.subjective_mem_retrieval_projection``, and
``relaylm.subjective_mem_retrieval_projection_store``. It imports neither the
cutover facade nor the configuration owner, and nothing imports it in reverse.

Every entry point returns bounded content-free reasons instead of raising, and
every missing, foreign, stale, mixed, corrupt, unsafe, unreadable, incomplete,
or source-disagreeing state fails closed with no repair-on-read and no fallback.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._subjective_mem_commit_io import inspect_canonical_page
from .evidence_common import canonical_digest
from .evidence_store import EvidenceRecordStore
from .subjective_mem import SubjectiveMemScopeBinding
from .subjective_mem_lifecycle_engine import CURRENT_STATE_LOG_KIND
from .subjective_mem_markdown import subjective_mem_page_identity
from .subjective_mem_retrieval import (
    RETRIEVAL_MEMORY_KINDS,
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalRequest,
    subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_request,
)
from .subjective_mem_retrieval_projection import (
    MAX_PROJECTION_SOURCE_ENTRIES,
    SubjectiveMemRetrievalProjection,
    SubjectiveMemRetrievalProjectionSource,
    SubjectiveMemRetrievalProjectionSourceEntry,
    build_subjective_mem_retrieval_projection,
)
from .subjective_mem_retrieval_projection_store import (
    read_subjective_mem_retrieval_projection,
    write_subjective_mem_retrieval_projection,
)

RUNTIME_PROJECTION_EMPTY_SNAPSHOT_AT = "1970-01-01T00:00:00Z"
RUNTIME_PROJECTION_EMPTY_WORKSPACE_DIGEST = canonical_digest(
    {"schema": "relaylm.subjective_mem_retrieval_runtime_empty_workspace.v1"}
)
ADMITTED_SCOPE_BINDING_DIGEST = canonical_digest(SubjectiveMemScopeBinding().to_dict())
RUNTIME_PROJECTION_MEMORY_KINDS = ("episodic", "semantic")

_ST1_RECEIPT_RECORD_KIND = "subjective_mem_st1_commit_receipt"
_LIFECYCLE_RECEIPT_RECORD_KIND = "subjective_mem_lifecycle_receipt"
_AUTHORIZATION_RECORD_KINDS = {
    "formation_decision": "subjective_mem_decision",
    "lifecycle_transition": "subjective_mem_lifecycle_transition",
}
_PROJECTION_ABSENT = ("subjective_mem_retrieval_projection_absent",)


@dataclass(frozen=True)
class SubjectiveMemRetrievalRuntimeProjectionSpec:
    """One immutable content-free instruction for the ordinary projection boundary."""

    evidence_space_id: str
    workspace_root: str
    projection_root: str
    character_id: str
    query_plan_digest: str
    request_correlation_digest: str
    memory_kinds: tuple[str, ...]
    candidate_limit: int
    token_budget: int


@dataclass(frozen=True, repr=False)
class SubjectiveMemRetrievalRuntimeProjection:
    """One exact acquired source, projection, request, and canonical page set.

    ``canonical_page_images`` holds exactly the bounded canonical page bytes the
    selection owner needs for this request. The set is a loader result, never an
    authority: the selection owner independently proves each selected row
    against the page it names and fails closed on any disagreement.
    """

    source: SubjectiveMemRetrievalProjectionSource
    projection: SubjectiveMemRetrievalProjection
    request: SubjectiveMemRetrievalRequest
    canonical_page_images: tuple[bytes, ...]

    def __repr__(self) -> str:
        return (
            "SubjectiveMemRetrievalRuntimeProjection("
            "runtime_private_evidence_omitted=True)"
        )


def acquire_subjective_mem_retrieval_runtime_projection(
    *, store: object, spec: object
) -> tuple[SubjectiveMemRetrievalRuntimeProjection | None, tuple[str, ...]]:
    """Acquire the exact current source and its trusted live projection bundle."""

    reasons = _spec_reasons(store, spec)
    if reasons:
        return None, reasons
    assert isinstance(store, EvidenceRecordStore)
    assert isinstance(spec, SubjectiveMemRetrievalRuntimeProjectionSpec)
    source, reasons = _acquire_source(store, spec)
    if source is None:
        return None, reasons
    built, reasons = build_subjective_mem_retrieval_projection(source)
    if built is None:
        return None, reasons
    projection, reasons = _trusted_bundle(spec.projection_root, source, built)
    if projection is None:
        return None, reasons
    request = _request(spec, source, projection)
    reasons = validate_subjective_mem_retrieval_request(request)
    if reasons:
        return None, reasons
    return (
        SubjectiveMemRetrievalRuntimeProjection(
            source=source,
            projection=projection,
            request=request,
            canonical_page_images=_required_page_images(spec, source, projection),
        ),
        (),
    )


def subjective_mem_retrieval_runtime_projection_spec(
    *,
    evidence_root: object,
    workspace_root: object,
    projection_root: object,
    evidence_space_id: object,
    character_id: object,
    query_plan_digest: str,
    request_correlation_digest: str,
    candidate_limit: int,
    token_budget: int,
) -> tuple[
    SubjectiveMemRetrievalRuntimeProjectionSpec | None,
    EvidenceRecordStore | None,
    tuple[str, ...],
]:
    """Build the one bounded acquisition request from explicit safe locators.

    Locators are passed as plain values, never read from a configuration object,
    so this owner stays independent of the configuration owner. Locating inputs
    grants no serving authority: only the exact finalized transfer receipt does.
    """

    locators = (
        evidence_root, workspace_root, projection_root, evidence_space_id, character_id
    )
    if any(not _text(value) for value in locators):
        return None, None, ("subjective_mem_retrieval_route_locator_missing",)
    try:
        store = EvidenceRecordStore(str(evidence_root))
    except (OSError, TypeError, ValueError):
        return None, None, ("subjective_mem_retrieval_route_store_unavailable",)
    return (
        SubjectiveMemRetrievalRuntimeProjectionSpec(
            evidence_space_id=str(evidence_space_id),
            workspace_root=str(workspace_root),
            projection_root=str(projection_root),
            character_id=str(character_id),
            query_plan_digest=query_plan_digest,
            request_correlation_digest=request_correlation_digest,
            memory_kinds=RUNTIME_PROJECTION_MEMORY_KINDS,
            candidate_limit=max(1, min(64, int(candidate_limit))),
            token_budget=max(1, min(8192, int(token_budget))),
        ),
        store,
        (),
    )


def verify_subjective_mem_retrieval_runtime_projection(
    *,
    store: object,
    spec: object,
    expected_generation_id: object,
    expected_source_digest: object,
) -> tuple[SubjectiveMemRetrievalRuntimeProjection | None, tuple[str, ...]]:
    """Acquire, then require the exact expected generation and source snapshot.

    The expected identities are supplied by the caller and compared here; no
    cutover semantics are evaluated. A source that no longer reproduces them
    fails closed rather than rebinding the live projection to a newer snapshot.
    """

    acquired, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    if acquired is None:
        return None, reasons
    manifest = acquired.projection.manifest
    population = tuple(row.row_digest for row in acquired.projection.rows)
    if (
        manifest.projection_generation_id != expected_generation_id
        or acquired.source.projection_generation_id != expected_generation_id
        or manifest.source_snapshot_digest != expected_source_digest
        or acquired.source.source_snapshot_digest != expected_source_digest
        or population != manifest.row_digests
    ):
        return None, ("subjective_mem_retrieval_runtime_generation_disagreement",)
    return acquired, ()


def _spec_reasons(store: object, spec: object) -> tuple[str, ...]:
    """Refuse anything that is not one bounded, well-formed acquisition request."""

    if type(store) is not EvidenceRecordStore:
        return ("subjective_mem_retrieval_runtime_store_invalid",)
    if type(spec) is not SubjectiveMemRetrievalRuntimeProjectionSpec:
        return ("subjective_mem_retrieval_runtime_spec_invalid",)
    if not all(
        _text(getattr(spec, name))
        for name in ("evidence_space_id", "workspace_root", "projection_root", "character_id")
    ):
        return ("subjective_mem_retrieval_runtime_locator_invalid",)
    if not _digest(spec.query_plan_digest) or not _digest(spec.request_correlation_digest):
        return ("subjective_mem_retrieval_runtime_request_digest_invalid",)
    if (
        type(spec.memory_kinds) is not tuple
        or not spec.memory_kinds
        or spec.memory_kinds != tuple(sorted(set(spec.memory_kinds)))
        or any(kind not in RETRIEVAL_MEMORY_KINDS for kind in spec.memory_kinds)
    ):
        return ("subjective_mem_retrieval_runtime_memory_kinds_invalid",)
    if (
        type(spec.candidate_limit) is not int
        or not 1 <= spec.candidate_limit <= 64
        or type(spec.token_budget) is not int
        or not 1 <= spec.token_budget <= 8192
    ):
        return ("subjective_mem_retrieval_runtime_bounds_invalid",)
    return ()


def _acquire_source(
    store: EvidenceRecordStore, spec: SubjectiveMemRetrievalRuntimeProjectionSpec
) -> tuple[SubjectiveMemRetrievalProjectionSource | None, tuple[str, ...]]:
    """Load one fixed snapshot under exactly one evidence-space lock.

    The canonical pages are read inside the same lock, so the selectors,
    receipts, authorization records, and page images that reach the RT-1B
    builder are one consistent snapshot rather than a drifting mixture.
    """

    try:
        with store.transaction(spec.evidence_space_id) as transaction:
            inventory = transaction.list_logs(
                log_kind=CURRENT_STATE_LOG_KIND, limit=MAX_PROJECTION_SOURCE_ENTRIES
            )
            selectors, reasons = _character_selectors(inventory, spec.character_id)
            if selectors is None:
                return None, reasons
            pages, reasons = _canonical_pages(spec, selectors)
            if pages is None:
                return None, reasons
            entries, reasons = _source_entries(transaction, selectors, pages)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_retrieval_runtime_source_unavailable",)
    if entries is None:
        return None, reasons
    workspace = {_binding(raw).get("workspace_authority_digest") for raw in selectors}
    if len(workspace) > 1 or not all(_digest(value) for value in workspace):
        return None, ("subjective_mem_retrieval_runtime_workspace_authority_mixed",)
    return (
        SubjectiveMemRetrievalProjectionSource(
            evidence_space_id=spec.evidence_space_id,
            character_id=spec.character_id,
            workspace_authority_digest=(
                workspace.pop() if workspace else RUNTIME_PROJECTION_EMPTY_WORKSPACE_DIGEST
            ),
            admitted_scope_binding_digest=ADMITTED_SCOPE_BINDING_DIGEST,
            snapshot_taken_at=_snapshot_taken_at(selectors),
            entries=entries,
        ),
        (),
    )


def _character_selectors(
    inventory: tuple[tuple[str, list[dict]], ...], character_id: str
) -> tuple[tuple[dict[str, object], ...] | None, tuple[str, ...]]:
    """Select this character's exact one-event current selectors, deterministically.

    Only the named identity fields are read here, to resolve which canonical
    page and which receipt and authorization records each selector points at.
    ``SubjectiveMemCurrentState`` inside the RT-1B builder remains the sole
    evaluator of what those records mean.
    """

    selectors: list[dict[str, object]] = []
    for key, events in inventory:
        if type(events) is not list or len(events) != 1 or type(events[0]) is not dict:
            return None, ("subjective_mem_retrieval_runtime_selector_corrupt",)
        raw = events[0]
        if raw.get("character_id") != character_id:
            continue
        if raw.get("memory_state_id") != key:
            return None, ("subjective_mem_retrieval_runtime_selector_identity_mismatch",)
        selectors.append(raw)
    ordered = tuple(sorted(selectors, key=canonical_digest))
    if len(ordered) > MAX_PROJECTION_SOURCE_ENTRIES:
        return None, ("subjective_mem_retrieval_runtime_source_oversize",)
    return ordered, ()


def _canonical_pages(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    selectors: tuple[dict[str, object], ...],
) -> tuple[dict[str, bytes] | None, tuple[str, ...]]:
    """Read each named canonical page once through the existing canonical reader.

    The page location comes from the existing ``subjective_mem_page_identity``
    owner, so no path is invented and no second workspace layout exists.
    """

    locations = {
        page_id: relative_path
        for page_id, relative_path, _partition in (
            subjective_mem_page_identity(character_id=spec.character_id, memory_kind=kind)
            for kind in sorted(RETRIEVAL_MEMORY_KINDS)
        )
    }
    pages: dict[str, bytes] = {}
    for raw in selectors:
        page_id = _binding(raw).get("page_id")
        if type(page_id) is not str or page_id not in locations:
            return None, ("subjective_mem_retrieval_runtime_page_unresolvable",)
        if page_id in pages:
            continue
        result = inspect_canonical_page(
            workspace_root=spec.workspace_root,
            character_id=spec.character_id,
            relative_path=locations[page_id],
        )
        snapshot = result.snapshot
        if snapshot is None or snapshot.state != "present" or type(snapshot.data) is not bytes:
            return None, ("subjective_mem_retrieval_runtime_page_unreadable",)
        pages[page_id] = snapshot.data
    return pages, ()


def _source_entries(
    transaction: object,
    selectors: tuple[dict[str, object], ...],
    pages: dict[str, bytes],
) -> tuple[tuple[SubjectiveMemRetrievalProjectionSourceEntry, ...] | None, tuple[str, ...]]:
    """Resolve the exact receipt and authorization record each selector names."""

    entries: list[SubjectiveMemRetrievalProjectionSourceEntry] = []
    for raw in selectors:
        binding = _binding(raw)
        receipt_kind = (
            _ST1_RECEIPT_RECORD_KIND
            if raw.get("current_revision") == 1
            else _LIFECYCLE_RECEIPT_RECORD_KIND
        )
        reference = binding.get("authorization_ref")
        reference = reference if isinstance(reference, dict) else {}
        authorization_kind = _AUTHORIZATION_RECORD_KINDS.get(
            reference.get("authority_kind")  # type: ignore[arg-type]
        )
        receipt_id, authorization_id = binding.get("current_receipt_id"), reference.get(
            "authority_id"
        )
        if authorization_kind is None or not _text(receipt_id) or not _text(authorization_id):
            return None, ("subjective_mem_retrieval_runtime_authority_reference_invalid",)
        receipt = transaction.read_record(record_kind=receipt_kind, record_id=receipt_id)
        authorization = transaction.read_record(
            record_kind=authorization_kind, record_id=authorization_id
        )
        if not isinstance(receipt, dict) or not isinstance(authorization, dict):
            return None, ("subjective_mem_retrieval_runtime_authority_record_missing",)
        entries.append(
            SubjectiveMemRetrievalProjectionSourceEntry(
                canonical_page_bytes=pages[binding["page_id"]],
                current_selector_record=raw,
                current_receipt_record=receipt,
                authorization_record=authorization,
            )
        )
    return tuple(entries), ()


def _trusted_bundle(
    projection_root: str,
    source: SubjectiveMemRetrievalProjectionSource,
    built: SubjectiveMemRetrievalProjection,
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Install or exact-verify the one live bundle, then trusted-read it.

    An absent bundle is installed once. Every other non-exact state — foreign,
    stale, mixed, corrupt, unsafe, unreadable, incomplete, or source-disagreeing
    — fails closed with no repair-on-read, no overwrite, and no fallback, so a
    drifted source never silently rebinds the live projection.
    """

    stored, reasons = read_subjective_mem_retrieval_projection(
        projection_root=projection_root, source=source
    )
    if stored is None and reasons != _PROJECTION_ABSENT:
        return None, reasons
    if stored is None:
        reasons = write_subjective_mem_retrieval_projection(
            projection_root=projection_root, source=source, projection=built
        )
        if reasons:
            return None, reasons
        stored, reasons = read_subjective_mem_retrieval_projection(
            projection_root=projection_root, source=source
        )
    if stored is None or reasons or stored != built:
        return None, reasons or ("subjective_mem_retrieval_runtime_bundle_disagreement",)
    return stored, ()


def _request(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    source: SubjectiveMemRetrievalProjectionSource,
    projection: SubjectiveMemRetrievalProjection,
) -> SubjectiveMemRetrievalRequest:
    """Bind one ordinary request to exactly this acquired generation."""

    return SubjectiveMemRetrievalRequest(
        character_id=spec.character_id,
        workspace_authority_digest=source.workspace_authority_digest,
        admitted_scope_binding_digest=source.admitted_scope_binding_digest,
        query_plan_digest=spec.query_plan_digest,
        request_correlation_digest=spec.request_correlation_digest,
        projection_generation_id=projection.manifest.projection_generation_id,
        projection_manifest_digest=projection.manifest.manifest_digest,
        memory_kinds=spec.memory_kinds,
        candidate_limit=spec.candidate_limit,
        token_budget=spec.token_budget,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
        boundary=SubjectiveMemRetrievalBoundary(),
    )


def _required_page_images(
    spec: SubjectiveMemRetrievalRuntimeProjectionSpec,
    source: SubjectiveMemRetrievalProjectionSource,
    projection: SubjectiveMemRetrievalProjection,
) -> tuple[bytes, ...]:
    """Return exactly the canonical pages this request's admitted rows name.

    Admission is asked of the one RT-1A eligibility evaluator; no second
    vocabulary is defined here. The result is only which pages to load, and the
    selection owner still proves the whole handoff, so any disagreement between
    this loader hint and selection fails closed instead of serving.
    """

    admitted = {
        row.page_id
        for row in projection.rows
        if not subjective_mem_retrieval_exclusion_reasons(row)
        and row.memory_kind in spec.memory_kinds
    }
    by_page: dict[str, bytes] = {}
    for entry in source.entries:
        page_id = _binding(entry.current_selector_record).get("page_id")
        if type(page_id) is str:
            by_page.setdefault(page_id, entry.canonical_page_bytes)
    return tuple(by_page[page_id] for page_id in sorted(admitted) if page_id in by_page)


def _snapshot_taken_at(selectors: tuple[dict[str, object], ...]) -> str:
    """Bind build time to the snapshot rather than to an uncontrolled wall clock."""

    stamps = sorted(
        str(raw["updated_at"]) for raw in selectors if _text(raw.get("updated_at"))
    )
    return stamps[-1] if stamps else RUNTIME_PROJECTION_EMPTY_SNAPSHOT_AT


def _binding(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    binding = raw.get("authority_binding")
    return binding if isinstance(binding, dict) else {}


def _text(value: object) -> bool:
    return type(value) is str and bool(value)


def _digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "ADMITTED_SCOPE_BINDING_DIGEST",
    "RUNTIME_PROJECTION_EMPTY_SNAPSHOT_AT",
    "RUNTIME_PROJECTION_MEMORY_KINDS",
    "SubjectiveMemRetrievalRuntimeProjection",
    "SubjectiveMemRetrievalRuntimeProjectionSpec",
    "acquire_subjective_mem_retrieval_runtime_projection",
    "subjective_mem_retrieval_runtime_projection_spec",
    "verify_subjective_mem_retrieval_runtime_projection",
]
