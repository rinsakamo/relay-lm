"""RT-1C exact selection, canonical-page binding, and runtime-private handoff.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: select the exact current eligible Subjective revisions of exactly
one verified projection generation and prepare the bounded runtime-private
handoff the existing E1-R4 grounding owner already consumes.

Private evidence is bound to canonical authority, not to a caller's word. The
caller supplies bounded canonical page bytes; this owner parses them with the
existing ``relaylm.subjective_mem_markdown`` parser, proves the complete page,
block, and revision identity against the exact projection row and admitted
request scope, and takes ``grounded_content`` and its digest only from that exact
parsed revision. Arbitrary prose plus a matching caller-supplied digest is only
self-consistent, which is not canonical authority, and there is no API through
which it can be admitted. Token estimates are likewise derived from the parsed
prose through the existing deterministic estimator rather than accepted from a
caller.

Nothing here serves memory. A prepared handoff has no admission state and no
release path at all: only the durable usage ledger may build an admitted handoff,
after ``validate_subjective_mem_retrieval_prepared_handoff`` proves the whole
handoff is exactly what those canonical bytes produce. There is no ordinary
request-path call, RelayCTX injection, backend call, response rewrite, projection
repair, filesystem access, path resolution, or Primary MEM access, and E1-R4
grounding behaviour is unchanged — its bounded constants are imported read-only.

Shadow characterization is a separate owner and is never imported here. Every
entry point returns content-free reasons instead of raising.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from relaylm.evidence.common import canonical_digest, dedupe
from relaylm.relaymem_grounded_recall_response import (
    GROUNDED_RECALL_CONTEXT_SCHEMA, MAX_EVIDENCE_ITEMS, MAX_FACT_TEXT_CHARS,
)
from relaylm.subjective_mem_markdown import (
    MAX_CANONICAL_PAGE_BYTES, SubjectiveMemMarkdownBlock, SubjectiveMemMarkdownPage,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION, SubjectiveMemRetrievalProjectionManifest,
    SubjectiveMemRetrievalProjectionRow, SubjectiveMemRetrievalRequest,
    SubjectiveMemRetrievalSelection, subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row, validate_subjective_mem_retrieval_request,
    validate_subjective_mem_retrieval_selection,
)
from relaylm.token_budget import estimate_text_tokens

SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA = "relaylm.subjective_mem_retrieval_private_handoff.v1"
SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA = "relaylm.subjective_mem_retrieval_selection_projection.v1"
SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE = f"{GROUNDED_RECALL_CONTEXT_SCHEMA}.evidence_items"
SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY = "primary_mem"
SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER = "subjective"

RETRIEVAL_SELECTION_STATUSES = frozenset({"prepared", "prepared_empty", "refused"})
RETRIEVAL_HANDOFF_SHAPE_CLASSES = frozenset({"absent", "empty", "bounded_private_items"})
RETRIEVAL_TOKEN_BUDGET_CLASSES = frozenset({"empty", "within_budget", "at_budget", "exceeded"})

SelectionStatus = Literal["prepared", "prepared_empty", "refused"]

_FORMATION_PROVENANCE = {"primary": "user_assertion", "secondary": "other_allowed_source"}
_MAX_BLOCKED_REASONS = 32


@dataclass(frozen=True)
class SubjectiveMemRetrievalCanonicalPageBinding:
    """One bounded canonical page image supplied by the existing canonical owner.

    The bytes are the only authority this owner accepts for memory prose. No
    caller-supplied page identity, digest, block identity, prose, or prose digest
    accompanies them, because every one of those is derived from the parse.
    """

    canonical_page_bytes: bytes = field(repr=False)


@dataclass(frozen=True)
class _SubjectiveMemRetrievalPrivateItem:
    """One immutable private evidence item recovered from canonical page bytes.

    It carries the exact E1-R4 field values, the row and prose digests that bind
    it, and the prose itself. The type is module-private and exports no
    materialization method, so prepared state offers no route to a release-ready
    dictionary; only the ledger-owned admitted handoff builds one, after exact
    durable success.
    """

    row_digest: str
    memory_id: str
    memory_revision: int
    character_id: str
    lifecycle_state: str
    pinned: bool
    current: bool
    memory_layer: str
    provenance_source: str
    grounded_content: str = field(repr=False)
    grounded_content_digest: str
    token_estimate: int


@dataclass(frozen=True)
class SubjectiveMemRetrievalPreparedHandoff:
    """One prepared runtime-private handoff that can never release its evidence.

    There is no admission state to toggle, no accessor that yields grounding
    evidence, and no nested public value that can materialize one, so a prepared
    value cannot self-admit. It retains its canonical page bindings in normalized
    parsed order, so the whole handoff stays revalidatable against canonical
    authority and stays independent of caller input order.
    """

    schema: str
    handoff_shape: str
    shadow: bool
    selected_count: int
    total_token_estimate: int
    selection: SubjectiveMemRetrievalSelection = field(repr=False)
    ranked_row_digests: tuple[str, ...] = field(repr=False)
    _private_items: tuple[_SubjectiveMemRetrievalPrivateItem, ...] = field(repr=False)
    _canonical_pages: tuple[SubjectiveMemRetrievalCanonicalPageBinding, ...] = field(repr=False)


@dataclass(frozen=True)
class SubjectiveMemRetrievalSelectionProjection:
    """One content-free public projection of a selection attempt."""

    status: SelectionStatus
    shadow: bool
    attempted: bool
    projection_generation_ready: bool
    candidate_count: int
    eligible_count: int
    selected_count: int
    not_requested_kind_count: int
    excluded_count_by_reason_class: tuple[tuple[str, int], ...]
    handoff_shape_class: str
    token_budget_class: str
    blocked_reason_classes: tuple[str, ...]
    runtime_private_evidence_omitted: bool = True
    ordinary_route_admitted: bool = False
    usage_event_recorded: bool = False

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = asdict(self)
        body["excluded_count_by_reason_class"] = [
            [reason, count] for reason, count in self.excluded_count_by_reason_class
        ]
        body["blocked_reason_classes"] = list(self.blocked_reason_classes)
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA,
            "content_free": True,
            "served_authority": SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY,
            **body,
        }


def select_subjective_mem_retrieval_handoff(
    *,
    request: object,
    manifest: object,
    rows: object,
    canonical_pages: object,
    shadow: bool = True,
) -> tuple[SubjectiveMemRetrievalPreparedHandoff | None, SubjectiveMemRetrievalSelectionProjection]:
    """Select exact eligible rows and prepare one canonical-bound private handoff.

    ``rows`` is the complete candidate population of ``manifest``. Selection is a
    pure read: it never broadens the query, relaxes a partition, repairs a row,
    fills an empty result, or touches the filesystem. Candidate-limit,
    token-budget, fact-length, and handoff-shape overflow all fail closed rather
    than truncating an oversized handoff.
    """

    if type(shadow) is not bool:
        return None, _refused(("subjective_mem_retrieval_selection_shadow_mode_invalid",), shadow=True)
    reasons = _population_reasons(request, manifest, rows)
    if reasons:
        return None, _refused(reasons, shadow=shadow)
    assert isinstance(request, SubjectiveMemRetrievalRequest)
    assert isinstance(manifest, SubjectiveMemRetrievalProjectionManifest)
    assert isinstance(rows, tuple)

    exclusions, eligible, ranked = _classify_population(request, rows)
    population = (rows, exclusions, eligible, ranked)
    budget = request.token_budget
    items, normalized_pages, reasons = _canonical_private_items(request, ranked, canonical_pages)
    if items is None:
        return None, _refused(reasons, shadow=shadow, population=population, token_budget=budget)
    total = sum(item.token_estimate for item in items)
    if total > budget:
        reasons = ("subjective_mem_retrieval_selection_token_budget_exceeded",)
    elif len(ranked) > MAX_EVIDENCE_ITEMS:
        reasons = ("subjective_mem_retrieval_selection_handoff_shape_oversize",)
    if reasons:
        return None, _refused(
            reasons, shadow=shadow, population=population, total=total, token_budget=budget
        )

    selection = SubjectiveMemRetrievalSelection(
        request_input_digest=request.input_digest,
        projection_generation_id=request.projection_generation_id,
        projection_manifest_digest=manifest.manifest_digest,
        selected_row_digests=tuple(sorted(row.row_digest for row in ranked)),
        candidate_count=len(rows), eligible_count=len(eligible), selected_count=len(ranked),
        total_token_estimate=total, policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    )
    reasons = validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=rows, selection=selection
    )
    if reasons:
        return None, _refused(
            reasons, shadow=shadow, population=population, total=total, token_budget=budget
        )
    handoff = SubjectiveMemRetrievalPreparedHandoff(
        schema=SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA,
        handoff_shape=SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE, shadow=shadow,
        selected_count=len(ranked), total_token_estimate=total, selection=selection,
        ranked_row_digests=tuple(row.row_digest for row in ranked), _private_items=items,
        _canonical_pages=normalized_pages,
    )
    return handoff, _projection(
        "prepared_empty" if not ranked else "prepared", shadow=shadow, blocked=(),
        population=population, total=total, token_budget=budget, prepared=True,
    )


def validate_subjective_mem_retrieval_prepared_handoff(
    *, request: object, manifest: object, rows: object, handoff: object
) -> tuple[str, ...]:
    """Prove one prepared handoff is exactly what its canonical bytes produce.

    The whole handoff — selected order, selection value, private items, canonical
    bindings, and totals — is rebuilt from the retained canonical page bytes and
    compared as one exact value. A caller-authored handoff whose prose and digest
    merely agree with each other cannot survive that comparison, because the
    admitted prose is recovered from the row-bound canonical page rather than
    accepted. Missing, substituted, reordered, duplicated, and extra items or page
    bindings fail the same way. The check is pure and performs no I/O.
    """

    if type(handoff) is not SubjectiveMemRetrievalPreparedHandoff or (
        type(handoff.shadow) is not bool or type(handoff._canonical_pages) is not tuple
    ):
        return ("subjective_mem_retrieval_prepared_handoff_invalid",)
    rebuilt, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows,
        canonical_pages=handoff._canonical_pages, shadow=handoff.shadow,
    )
    if rebuilt is None:
        return projection.blocked_reason_classes or (
            "subjective_mem_retrieval_prepared_handoff_not_reproducible",
        )
    if rebuilt != handoff:
        return ("subjective_mem_retrieval_prepared_handoff_not_canonical",)
    return ()


def _population_reasons(request: object, manifest: object, rows: object) -> tuple[str, ...]:
    """Refuse anything that is not one exact request over one complete generation."""

    reasons = [
        *validate_subjective_mem_retrieval_request(request),
        *validate_subjective_mem_retrieval_projection_manifest(manifest),
    ]
    if type(rows) is not tuple or any(
        type(row) is not SubjectiveMemRetrievalProjectionRow for row in rows
    ):
        reasons.append("subjective_mem_retrieval_selection_rows_invalid")
    if reasons:
        return dedupe(reasons)
    assert isinstance(request, SubjectiveMemRetrievalRequest)
    assert isinstance(manifest, SubjectiveMemRetrievalProjectionManifest)
    assert isinstance(rows, tuple)
    for row in rows:
        reasons.extend(validate_subjective_mem_retrieval_projection_row(row))
        if row.projection_generation_id != request.projection_generation_id:
            reasons.append("subjective_mem_retrieval_selection_row_generation_mismatch")
        if row.character_id != request.character_id:
            reasons.append("subjective_mem_retrieval_selection_row_character_foreign")
        if row.workspace_authority_digest != request.workspace_authority_digest:
            reasons.append("subjective_mem_retrieval_selection_row_workspace_foreign")
        if row.scope_admitted and row.scope_binding_digest != request.admitted_scope_binding_digest:
            reasons.append("subjective_mem_retrieval_selection_row_scope_authority_mismatch")
    if request.projection_generation_id != manifest.projection_generation_id:
        reasons.append("subjective_mem_retrieval_selection_generation_mismatch")
    if request.projection_manifest_digest != manifest.manifest_digest:
        reasons.append("subjective_mem_retrieval_selection_manifest_mismatch")
    digests = tuple(sorted(row.row_digest for row in rows))
    if len(set(digests)) != len(digests):
        reasons.append("subjective_mem_retrieval_selection_rows_duplicated")
    elif digests != manifest.row_digests:
        reasons.append("subjective_mem_retrieval_selection_population_incomplete")
    if len(rows) > request.candidate_limit:
        reasons.append("subjective_mem_retrieval_selection_candidate_limit_exceeded")
    return dedupe(reasons)


def _classify_population(
    request: SubjectiveMemRetrievalRequest,
    rows: tuple[SubjectiveMemRetrievalProjectionRow, ...],
) -> tuple[
    tuple[tuple[str, int], ...],
    tuple[SubjectiveMemRetrievalProjectionRow, ...],
    tuple[SubjectiveMemRetrievalProjectionRow, ...],
]:
    """Split the population into exclusion classes, eligible rows, and ranked rows.

    Eligibility is the RT-1A closed vocabulary alone, so the reported count keeps
    its contract meaning. Requested kinds narrow it, and pinned state orders the
    result only after exact eligibility.
    """

    counts: dict[str, int] = {}
    eligible: list[SubjectiveMemRetrievalProjectionRow] = []
    for row in rows:
        excluded = subjective_mem_retrieval_exclusion_reasons(row)
        for reason in excluded:
            counts[reason] = counts.get(reason, 0) + 1
        if not excluded:
            eligible.append(row)
    ranked = sorted(
        (row for row in eligible if row.memory_kind in request.memory_kinds),
        key=lambda row: (row.lifecycle_state != "pinned", row.row_digest),
    )
    return tuple(sorted(counts.items())), tuple(eligible), tuple(ranked)


def _parse_canonical_pages(
    request: SubjectiveMemRetrievalRequest,
    ranked: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    canonical_pages: object,
) -> tuple[
    dict[str, SubjectiveMemMarkdownPage] | None,
    tuple[SubjectiveMemRetrievalCanonicalPageBinding, ...],
    tuple[str, ...],
]:
    """Parse each supplied page exactly once and index it by its parsed identity.

    The retained binding order is normalized by parsed page ID, never by caller
    tuple order, so the same page set always produces the same prepared handoff.
    A duplicate submission, duplicate parsed identity, duplicate parsed digest,
    extra page no selected row needs, or missing page a selected row needs all
    fail closed. No second parser and no filesystem access is introduced.
    """

    if type(canonical_pages) is not tuple or any(
        type(item) is not SubjectiveMemRetrievalCanonicalPageBinding for item in canonical_pages
    ):
        return None, (), ("subjective_mem_retrieval_selection_canonical_page_invalid",)
    parsed: dict[str, SubjectiveMemMarkdownPage] = {}
    bindings: dict[str, SubjectiveMemRetrievalCanonicalPageBinding] = {}
    digests: set[str] = set()
    for binding in canonical_pages:
        data = binding.canonical_page_bytes
        if type(data) is not bytes or not 1 <= len(data) <= MAX_CANONICAL_PAGE_BYTES:
            return None, (), ("subjective_mem_retrieval_selection_canonical_page_out_of_bounds",)
        page, _reasons = parse_subjective_mem_page_bytes(
            data, expected_character_id=request.character_id
        )
        if page is None:
            return None, (), ("subjective_mem_retrieval_selection_canonical_page_unsupported",)
        if page.page_id in parsed or page.page_digest in digests:
            return None, (), ("subjective_mem_retrieval_selection_canonical_page_duplicated",)
        parsed[page.page_id] = page
        bindings[page.page_id] = binding
        digests.add(page.page_digest)
    required = {row.page_id for row in ranked}
    if required - set(parsed):
        return None, (), ("subjective_mem_retrieval_selection_canonical_page_missing",)
    if set(parsed) - required:
        return None, (), ("subjective_mem_retrieval_selection_canonical_page_extra",)
    normalized = tuple(bindings[page_id] for page_id in sorted(bindings))
    return parsed, normalized, ()


def _canonical_private_items(
    request: SubjectiveMemRetrievalRequest,
    ranked: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    canonical_pages: object,
) -> tuple[
    tuple[_SubjectiveMemRetrievalPrivateItem, ...] | None,
    tuple[SubjectiveMemRetrievalCanonicalPageBinding, ...],
    tuple[str, ...],
]:
    """Recover one private item per selected row from its exact canonical block."""

    parsed, normalized, reasons = _parse_canonical_pages(request, ranked, canonical_pages)
    if parsed is None:
        return None, (), reasons
    items: list[_SubjectiveMemRetrievalPrivateItem] = []
    for row in ranked:
        page = parsed[row.page_id]
        blocks = [item for item in page.blocks if item.block_id == row.block_id]
        if len(blocks) != 1:
            return None, (), ("subjective_mem_retrieval_selection_canonical_block_ambiguous",)
        reasons = _canonical_block_reasons(request, row, page, blocks[0])
        if reasons:
            return None, (), reasons
        revision = blocks[0].revision
        if not 1 <= len(revision.grounded_content) <= MAX_FACT_TEXT_CHARS:
            return None, (), ("subjective_mem_retrieval_selection_canonical_content_out_of_bounds",)
        items.append(
            _build_private_item(row, revision.grounded_content, revision.grounded_content_digest)
        )
    return tuple(items), normalized, ()


def _canonical_block_reasons(
    request: SubjectiveMemRetrievalRequest,
    row: SubjectiveMemRetrievalProjectionRow,
    page: SubjectiveMemMarkdownPage,
    block: SubjectiveMemMarkdownBlock,
) -> tuple[str, ...]:
    """Prove one parsed page and block are exactly the ones ``row`` names."""

    revision = block.revision
    if (
        page.page_id != row.page_id
        or page.character_id != row.character_id
        or page.character_id != request.character_id
        or page.page_digest != row.canonical_page_digest
    ):
        return ("subjective_mem_retrieval_selection_canonical_page_mismatch",)
    if (
        block.block_id != row.block_id
        or revision.memory_id != row.memory_id
        or revision.memory_revision != row.memory_revision
        or block.block_digest.removeprefix("sha256:") != row.block_digest
        or block.revision_digest != row.revision_digest
    ):
        return ("subjective_mem_retrieval_selection_canonical_block_mismatch",)
    scope_digest = canonical_digest(revision.scope_binding.to_dict())
    if (
        scope_digest != row.scope_binding_digest
        or scope_digest != request.admitted_scope_binding_digest
    ):
        return ("subjective_mem_retrieval_selection_canonical_scope_mismatch",)
    if (
        revision.character_id != row.character_id
        or revision.memory_kind != row.memory_kind
        or revision.formation_stage != row.formation_stage
        or revision.lifecycle_state != row.lifecycle_state
        or revision.retrieval_visible != row.retrieval_visible
    ):
        return ("subjective_mem_retrieval_selection_canonical_revision_mismatch",)
    if (
        revision.authorization_id != row.authorization_id
        or _authorization_record_kind(block) != row.authorization_record_kind
    ):
        return ("subjective_mem_retrieval_selection_canonical_authorization_mismatch",)
    return ()


def _authorization_record_kind(block: SubjectiveMemMarkdownBlock) -> str:
    """Map one parsed revision's authorizing operation to its RT-1A record kind."""

    revision = block.revision
    legacy = revision.memory_revision == 1 and (
        revision.authorization_kind == "formation_decision"
    )
    return "subjective_mem_decision" if legacy else "subjective_mem_lifecycle_transition"


def _build_private_item(
    row: SubjectiveMemRetrievalProjectionRow, content: str, content_digest: str
) -> _SubjectiveMemRetrievalPrivateItem:
    """Build the private item ``row`` admits from its exact canonical prose.

    Formation stage classifies the already authorized revision into E1-R4's
    support vocabulary, and the token estimate comes from the existing
    deterministic estimator rather than from a caller. No lineage is invented and
    no grounding policy changes.
    """

    return _SubjectiveMemRetrievalPrivateItem(
        row_digest=row.row_digest, memory_id=row.memory_id, memory_revision=row.memory_revision,
        character_id=row.character_id, lifecycle_state=row.lifecycle_state,
        pinned=row.lifecycle_state == "pinned", current=True,
        memory_layer=SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER,
        provenance_source=_FORMATION_PROVENANCE.get(row.formation_stage, ""),
        grounded_content=content, grounded_content_digest=content_digest,
        token_estimate=estimate_text_tokens(content).estimated_tokens,
    )


def _refused(
    reasons: tuple[str, ...],
    *,
    shadow: bool,
    population: tuple[object, ...] | None = None,
    total: int = 0,
    token_budget: int = 0,
) -> SubjectiveMemRetrievalSelectionProjection:
    """Report one refusal; an unverified generation reports no population at all."""

    return _projection(
        "refused", shadow=shadow, blocked=reasons[:_MAX_BLOCKED_REASONS],
        population=population or ((), (), (), ()), total=total, token_budget=token_budget,
        prepared=False, generation_ready=population is not None,
    )


def _projection(
    status: SelectionStatus,
    *,
    shadow: bool,
    blocked: tuple[str, ...],
    population: tuple[object, ...],
    total: int,
    token_budget: int,
    prepared: bool,
    generation_ready: bool = True,
) -> SubjectiveMemRetrievalSelectionProjection:
    rows, exclusions, eligible, ranked = population
    return SubjectiveMemRetrievalSelectionProjection(
        status=status, shadow=shadow, attempted=True,
        projection_generation_ready=generation_ready,
        candidate_count=len(rows), eligible_count=len(eligible), selected_count=len(ranked),
        not_requested_kind_count=len(eligible) - len(ranked),
        excluded_count_by_reason_class=exclusions,
        handoff_shape_class=(
            ("bounded_private_items" if ranked else "empty") if prepared else "absent"
        ),
        token_budget_class=_token_budget_class(total, token_budget),
        blocked_reason_classes=blocked,
    )


def _token_budget_class(total: int, token_budget: int) -> str:
    if total <= 0:
        return "empty"
    if token_budget <= 0 or total > token_budget:
        return "exceeded"
    return "at_budget" if total == token_budget else "within_budget"


__all__ = [
    "RETRIEVAL_HANDOFF_SHAPE_CLASSES", "RETRIEVAL_SELECTION_STATUSES",
    "RETRIEVAL_TOKEN_BUDGET_CLASSES", "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE", "SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER",
    "SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY",
    "SubjectiveMemRetrievalCanonicalPageBinding", "SubjectiveMemRetrievalPreparedHandoff",
    "SubjectiveMemRetrievalSelectionProjection",
    "select_subjective_mem_retrieval_handoff",
    "validate_subjective_mem_retrieval_prepared_handoff",
]
