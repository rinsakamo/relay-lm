"""RT-1C exact selection, runtime-private handoff, and shadow characterization.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: select the exact current eligible Subjective revisions of exactly
one verified projection generation, prepare the bounded runtime-private handoff
the existing E1-R4 grounding owner already consumes, and characterize the
Primary served path against the Subjective shadow path without combining them.

Nothing here serves memory. A prepared handoff has no admission state and no
release path at all: only the durable usage ledger may build an admitted handoff,
from a prepared value it has revalidated after exact durable finalization. This
owner therefore cannot be talked into releasing evidence, and the ledger depends
on it rather than the other way round. There is no ordinary request-path call,
RelayCTX injection, backend call, response rewrite, projection repair, canonical
read, path resolution, or Primary MEM access, and E1-R4 grounding behaviour is
unchanged — its bounded constants are imported read-only so no second copy of
its limits exists.

Canonical prose arrives only as bounded content bindings from the canonical
owner and is held as immutable typed private items, so no mutable mapping is
ever exposed on a prepared handoff. Public projections carry only values from
this module's closed vocabularies, which is what lets characterization copy a
few of them without copying caller text. Every entry point returns content-free
reasons instead of raising.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Literal

from relaylm.evidence_common import dedupe, utf8_text_digest
from relaylm.relaymem_grounded_recall_response import (
    GROUNDED_RECALL_CONTEXT_SCHEMA, MAX_EVIDENCE_ITEMS, MAX_FACT_TEXT_CHARS,
)
from relaylm.subjective_mem_retrieval import (
    RETRIEVAL_EXCLUSION_REASONS, SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest, SubjectiveMemRetrievalSelection,
    subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row, validate_subjective_mem_retrieval_request,
    validate_subjective_mem_retrieval_selection,
)

SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA = "relaylm.subjective_mem_retrieval_private_handoff.v1"
SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA = "relaylm.subjective_mem_retrieval_selection_projection.v1"
SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA = "relaylm.subjective_mem_retrieval_shadow_characterization.v1"
SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE = f"{GROUNDED_RECALL_CONTEXT_SCHEMA}.evidence_items"
SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY = "primary_mem"
SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER = "subjective"

RETRIEVAL_LATENCY_CLASSES = frozenset({"unmeasured", "within_bound", "exceeded_bound"})
RETRIEVAL_SELECTION_STATUSES = frozenset({"prepared", "prepared_empty", "refused"})
RETRIEVAL_HANDOFF_SHAPE_CLASSES = frozenset({"absent", "empty", "bounded_private_items"})
RETRIEVAL_TOKEN_BUDGET_CLASSES = frozenset({"empty", "within_budget", "at_budget", "exceeded"})
RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED = "no_leakage_detected"

SelectionStatus = Literal["prepared", "prepared_empty", "refused"]

_FORMATION_PROVENANCE = {"primary": "user_assertion", "secondary": "other_allowed_source"}
_MAX_TOKEN_ESTIMATE = 8192
_MAX_BLOCKED_REASONS = 32
_REASON_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+\Z")


@dataclass(frozen=True)
class SubjectiveMemRetrievalContentBinding:
    """One bounded canonical-content binding for exactly one projection row.

    The canonical owner supplies the prose, its exact digest, and the bounded
    token estimate; this owner resolves no path and repairs no row.
    """

    row_digest: str
    memory_id: str
    memory_revision: int
    character_id: str
    workspace_authority_digest: str
    scope_binding_digest: str
    grounded_content: str = field(repr=False)
    grounded_content_digest: str
    token_estimate: int


@dataclass(frozen=True)
class SubjectiveMemRetrievalPrivateItem:
    """One immutable private evidence item bound to exactly one selected row.

    It carries the exact E1-R4 fields, the row and prose digests that bind it,
    and the prose itself. Only an admitted handoff materializes dictionaries.
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

    def to_grounding_dict(self) -> dict[str, object]:
        """A fresh plain dict in the shape the existing E1-R4 owner consumes."""

        return {
            "memory_layer": self.memory_layer,
            "memory_id": self.memory_id,
            "revision": self.memory_revision,
            "character_id": self.character_id,
            "lifecycle_state": self.lifecycle_state,
            "current": self.current,
            "pinned": self.pinned,
            "provenance_source": self.provenance_source,
            "fact_text": self.grounded_content,
        }


@dataclass(frozen=True)
class SubjectiveMemRetrievalPreparedHandoff:
    """One prepared runtime-private handoff that can never release its evidence.

    There is no admission state to toggle and no accessor that yields grounding
    evidence, so a prepared value cannot self-admit.
    """

    schema: str
    handoff_shape: str
    shadow: bool
    selected_count: int
    total_token_estimate: int
    selection: SubjectiveMemRetrievalSelection = field(repr=False)
    ranked_row_digests: tuple[str, ...] = field(repr=False)
    private_items: tuple[SubjectiveMemRetrievalPrivateItem, ...] = field(repr=False)


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


@dataclass(frozen=True)
class SubjectiveMemRetrievalPrimaryServedMetrics:
    """Bounded content-free metrics of the Primary served path for one request."""

    attempted: bool
    candidate_count: int
    selected_count: int
    latency_class: str = "unmeasured"


@dataclass(frozen=True)
class SubjectiveMemRetrievalShadowCharacterization:
    """One deterministic content-free Primary-vs-Subjective comparison."""

    primary_attempt_class: str
    subjective_attempt_class: str
    primary_candidate_count_class: str
    subjective_candidate_count_class: str
    subjective_eligible_count_class: str
    primary_selected_count_class: str
    subjective_selected_count_class: str
    exclusion_reason_class_counts: tuple[tuple[str, int], ...]
    outcome_agreement_class: str
    handoff_shape_class: str
    token_budget_class: str
    deterministic_replay_class: str
    primary_latency_class: str
    subjective_latency_class: str
    projection_rebuild_equivalence_class: str
    leakage_outcome: str
    runtime_private_content_combined: bool = False

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = asdict(self)
        body["exclusion_reason_class_counts"] = [
            [reason, count] for reason, count in self.exclusion_reason_class_counts
        ]
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA,
            "content_free": True,
            "temporary_characterization": True,
            "served_authority": SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY,
            **body,
        }


def select_subjective_mem_retrieval_handoff(
    *,
    request: object,
    manifest: object,
    rows: object,
    content_bindings: object,
    shadow: bool = True,
) -> tuple[SubjectiveMemRetrievalPreparedHandoff | None, SubjectiveMemRetrievalSelectionProjection]:
    """Select exact eligible rows and prepare one bounded runtime-private handoff.

    ``rows`` is the complete candidate population of ``manifest``. Selection is a
    pure read: it never broadens the query, relaxes a partition, repairs a row,
    or fills an empty result. Candidate-limit, token-budget and handoff-shape
    overflow all fail closed rather than truncating an oversized handoff.
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
    items, total, reasons = _private_items(request, ranked, content_bindings)
    if items is None:
        return None, _refused(reasons, shadow=shadow, population=population, token_budget=budget)
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
        ranked_row_digests=tuple(row.row_digest for row in ranked), private_items=items,
    )
    return handoff, _projection(
        "prepared_empty" if not ranked else "prepared", shadow=shadow, blocked=(),
        population=population, total=total, token_budget=budget, prepared=True,
    )


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


def _private_items(
    request: SubjectiveMemRetrievalRequest,
    ranked: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    content_bindings: object,
) -> tuple[tuple[SubjectiveMemRetrievalPrivateItem, ...] | None, int, tuple[str, ...]]:
    """Bind exactly one supplied content item to each selected row, or fail closed."""

    if type(content_bindings) is not tuple or any(
        type(item) is not SubjectiveMemRetrievalContentBinding for item in content_bindings
    ):
        return None, 0, ("subjective_mem_retrieval_selection_content_binding_invalid",)
    by_digest: dict[str, SubjectiveMemRetrievalContentBinding] = {}
    for binding in content_bindings:
        if binding.row_digest in by_digest:
            return None, 0, ("subjective_mem_retrieval_selection_content_binding_duplicated",)
        by_digest[binding.row_digest] = binding
    if set(by_digest) - {row.row_digest for row in ranked}:
        return None, 0, ("subjective_mem_retrieval_selection_content_binding_unselected",)
    items: list[SubjectiveMemRetrievalPrivateItem] = []
    total = 0
    for row in ranked:
        binding = by_digest.get(row.row_digest)
        if binding is None:
            return None, 0, ("subjective_mem_retrieval_selection_content_binding_missing",)
        reasons = _content_binding_reasons(request, row, binding)
        if reasons:
            return None, 0, reasons
        item = _expected_private_item(
            row, binding.grounded_content, binding.grounded_content_digest
        )
        reasons = subjective_mem_retrieval_private_item_reasons(request=request, row=row, item=item)
        if reasons:
            return None, 0, reasons
        items.append(item)
        total += binding.token_estimate
    return tuple(items), total, ()


def _content_binding_reasons(
    request: SubjectiveMemRetrievalRequest,
    row: SubjectiveMemRetrievalProjectionRow,
    binding: SubjectiveMemRetrievalContentBinding,
) -> tuple[str, ...]:
    """Reject a binding foreign to this exact row, scope, or token budget.

    Prose bounds and the prose digest belong to the private item's exactness rule.
    """

    if (
        binding.memory_id != row.memory_id
        or binding.memory_revision != row.memory_revision
        or binding.character_id != request.character_id
        or binding.workspace_authority_digest != request.workspace_authority_digest
        or binding.scope_binding_digest != request.admitted_scope_binding_digest
    ):
        return ("subjective_mem_retrieval_selection_content_binding_mismatch",)
    if type(binding.token_estimate) is not int or not 1 <= binding.token_estimate <= _MAX_TOKEN_ESTIMATE:
        return ("subjective_mem_retrieval_selection_content_binding_token_estimate_invalid",)
    return ()


def _expected_private_item(
    row: SubjectiveMemRetrievalProjectionRow, content: str, content_digest: str
) -> SubjectiveMemRetrievalPrivateItem:
    """The one private item ``row`` admits for this prose; build and check agree.

    Formation stage classifies the already authorized revision into E1-R4's
    support vocabulary; no lineage is invented and no grounding policy changes.
    """

    return SubjectiveMemRetrievalPrivateItem(
        row_digest=row.row_digest, memory_id=row.memory_id, memory_revision=row.memory_revision,
        character_id=row.character_id, lifecycle_state=row.lifecycle_state,
        pinned=row.lifecycle_state == "pinned", current=True,
        memory_layer=SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER,
        provenance_source=_FORMATION_PROVENANCE.get(row.formation_stage, ""),
        grounded_content=content, grounded_content_digest=content_digest,
    )


def subjective_mem_retrieval_private_item_reasons(
    *, request: object, row: object, item: object
) -> tuple[str, ...]:
    """Return why ``item`` is not the exact private item of ``row`` for ``request``.

    This owner builds the private item, so it also owns the exactness rule the
    durable ledger re-applies before any write. The rule is one exact-value
    comparison against the item ``row`` admits, so no field can be forgotten:
    a substituted, re-identified, re-classified, or re-worded item never matches.
    """

    if type(item) is not SubjectiveMemRetrievalPrivateItem:
        return ("subjective_mem_retrieval_private_item_invalid",)
    if type(row) is not SubjectiveMemRetrievalProjectionRow or (
        type(request) is not SubjectiveMemRetrievalRequest
    ):
        return ("subjective_mem_retrieval_private_item_binding_invalid",)
    if type(item.grounded_content) is not str or not 1 <= len(
        item.grounded_content
    ) <= MAX_FACT_TEXT_CHARS:
        return ("subjective_mem_retrieval_private_item_content_out_of_bounds",)
    if utf8_text_digest(item.grounded_content) != item.grounded_content_digest:
        return ("subjective_mem_retrieval_private_item_content_digest_mismatch",)
    if row.character_id != request.character_id:
        return ("subjective_mem_retrieval_private_item_request_scope_mismatch",)
    if item != _expected_private_item(
        row, item.grounded_content, item.grounded_content_digest
    ):
        return ("subjective_mem_retrieval_private_item_row_mismatch",)
    return ()


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


def validate_subjective_mem_retrieval_selection_projection(projection: object) -> tuple[str, ...]:
    """Return why ``projection`` is not one exact owner-produced public projection.

    Every reported value must come from this owner's closed vocabularies, so no
    caller-supplied prose can be copied onward. Anything outside them fails
    closed rather than being sanitized or truncated.
    """

    if type(projection) is not SubjectiveMemRetrievalSelectionProjection:
        return ("subjective_mem_retrieval_selection_projection_invalid",)
    reasons: list[str] = []
    if projection.status not in RETRIEVAL_SELECTION_STATUSES:
        reasons.append("subjective_mem_retrieval_selection_projection_status_invalid")
    boundary = (
        projection.runtime_private_evidence_omitted, projection.ordinary_route_admitted,
        projection.usage_event_recorded,
    )
    if any(
        type(value) is not bool
        for value in (projection.shadow, projection.attempted,
                      projection.projection_generation_ready, *boundary)
    ):
        reasons.append("subjective_mem_retrieval_selection_projection_boolean_invalid")
    elif boundary != (True, False, False):
        reasons.append("subjective_mem_retrieval_selection_projection_boundary_invalid")
    reasons.extend(_projection_count_reasons(projection))
    reasons.extend(_projection_vocabulary_reasons(projection))
    if projection.to_dict().get("served_authority") != SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY:
        reasons.append("subjective_mem_retrieval_selection_projection_served_authority_invalid")
    return dedupe(reasons)


def _projection_count_reasons(
    projection: SubjectiveMemRetrievalSelectionProjection,
) -> list[str]:
    """Reject counts that are not exact non-negative ints in the owner's relation."""

    counts = (
        projection.candidate_count, projection.eligible_count,
        projection.selected_count, projection.not_requested_kind_count,
    )
    if any(type(value) is not int or value < 0 for value in counts):
        return ["subjective_mem_retrieval_selection_projection_counts_invalid"]
    if not projection.candidate_count >= projection.eligible_count >= projection.selected_count:
        return ["subjective_mem_retrieval_selection_projection_count_order_invalid"]
    if projection.not_requested_kind_count != projection.eligible_count - projection.selected_count:
        return ["subjective_mem_retrieval_selection_projection_count_relation_invalid"]
    return []


def _projection_vocabulary_reasons(
    projection: SubjectiveMemRetrievalSelectionProjection,
) -> list[str]:
    """Reject any class or reason name outside the exact closed vocabularies."""

    entries = projection.excluded_count_by_reason_class
    reasons: list[str] = []
    if type(entries) is not tuple or any(
        type(entry) is not tuple or len(entry) != 2 or entry[0] not in RETRIEVAL_EXCLUSION_REASONS
        or type(entry[1]) is not int or entry[1] < 1
        for entry in entries
    ):
        reasons.append("subjective_mem_retrieval_selection_projection_exclusion_class_invalid")
    else:
        names = [entry[0] for entry in entries]
        if names != sorted(set(names)):
            reasons.append("subjective_mem_retrieval_selection_projection_exclusion_class_invalid")
    if projection.handoff_shape_class not in RETRIEVAL_HANDOFF_SHAPE_CLASSES:
        reasons.append("subjective_mem_retrieval_selection_projection_handoff_shape_class_invalid")
    if projection.token_budget_class not in RETRIEVAL_TOKEN_BUDGET_CLASSES:
        reasons.append("subjective_mem_retrieval_selection_projection_token_budget_class_invalid")
    blocked = projection.blocked_reason_classes
    if type(blocked) is not tuple or len(blocked) > _MAX_BLOCKED_REASONS or any(
        type(value) is not str or len(value) > 96 or _REASON_TOKEN_RE.fullmatch(value) is None
        for value in blocked
    ):
        reasons.append("subjective_mem_retrieval_selection_projection_blocked_reason_invalid")
    elif bool(blocked) is not (projection.status == "refused"):
        reasons.append("subjective_mem_retrieval_selection_projection_blocked_reason_state_invalid")
    return reasons


def characterize_subjective_mem_retrieval_shadow(
    *,
    primary: object,
    shadow: object,
    replay: object | None = None,
    subjective_latency_class: str = "unmeasured",
    projection_rebuild_equivalent: bool | None = None,
) -> tuple[SubjectiveMemRetrievalShadowCharacterization | None, tuple[str, ...]]:
    """Compare two exact content-free result projections deterministically.

    Only values proven to come from this owner's closed vocabularies cross the
    boundary, so a forged content-bearing projection is refused rather than
    copied into the output. That admission check is what ``leakage_outcome``
    reports, and the two paths' runtime-private content is never combined.
    """

    reasons = _characterization_input_reasons(
        primary, shadow, replay, subjective_latency_class, projection_rebuild_equivalent
    )
    if reasons:
        return None, reasons
    assert isinstance(primary, SubjectiveMemRetrievalPrimaryServedMetrics)
    assert isinstance(shadow, SubjectiveMemRetrievalSelectionProjection)
    return (
        SubjectiveMemRetrievalShadowCharacterization(
            primary_attempt_class=_attempt_class(primary.attempted),
            subjective_attempt_class=_attempt_class(shadow.attempted),
            primary_candidate_count_class=_count_class(primary.candidate_count),
            subjective_candidate_count_class=_count_class(shadow.candidate_count),
            subjective_eligible_count_class=_count_class(shadow.eligible_count),
            primary_selected_count_class=_count_class(primary.selected_count),
            subjective_selected_count_class=_count_class(shadow.selected_count),
            exclusion_reason_class_counts=shadow.excluded_count_by_reason_class,
            outcome_agreement_class=_agreement_class(
                primary.selected_count, shadow.selected_count
            ),
            handoff_shape_class=shadow.handoff_shape_class,
            token_budget_class=shadow.token_budget_class,
            deterministic_replay_class=(
                "not_evaluated" if replay is None
                else "deterministic" if replay.to_dict() == shadow.to_dict()
                else "non_deterministic"
            ),
            primary_latency_class=primary.latency_class,
            subjective_latency_class=subjective_latency_class,
            projection_rebuild_equivalence_class=(
                "not_evaluated" if projection_rebuild_equivalent is None
                else "equivalent" if projection_rebuild_equivalent else "not_equivalent"
            ),
            leakage_outcome=RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED,
        ),
        (),
    )


def _characterization_input_reasons(
    primary: object,
    shadow: object,
    replay: object | None,
    subjective_latency_class: object,
    projection_rebuild_equivalent: object,
) -> tuple[str, ...]:
    """Accept only exact content-free inputs describing an explicit shadow run."""

    reasons: list[str] = []
    if type(primary) is not SubjectiveMemRetrievalPrimaryServedMetrics or (
        primary.latency_class not in RETRIEVAL_LATENCY_CLASSES
    ) or any(
        type(value) is not int or value < 0
        for value in (primary.candidate_count, primary.selected_count)
    ) or type(primary.attempted) is not bool:
        reasons.append("subjective_mem_retrieval_characterization_primary_metrics_invalid")
    projection_reasons = validate_subjective_mem_retrieval_selection_projection(shadow)
    if replay is not None:
        projection_reasons += validate_subjective_mem_retrieval_selection_projection(replay)
    if projection_reasons:
        reasons.append("subjective_mem_retrieval_characterization_projection_invalid")
    elif not shadow.shadow or (replay is not None and not replay.shadow):
        reasons.append("subjective_mem_retrieval_characterization_shadow_mode_required")
    if subjective_latency_class not in RETRIEVAL_LATENCY_CLASSES:
        reasons.append("subjective_mem_retrieval_characterization_latency_class_invalid")
    if projection_rebuild_equivalent is not None and (
        type(projection_rebuild_equivalent) is not bool
    ):
        reasons.append("subjective_mem_retrieval_characterization_rebuild_flag_invalid")
    return dedupe(reasons)


def _attempt_class(attempted: bool) -> str:
    return "attempted" if attempted else "not_attempted"


def _count_class(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "one"
    return "few" if count <= 8 else "many"


def _agreement_class(primary_selected: int, subjective_selected: int) -> str:
    if primary_selected <= 0 and subjective_selected <= 0:
        return "both_empty"
    if primary_selected > 0 and subjective_selected > 0:
        return "both_non_empty"
    return "primary_only" if primary_selected > 0 else "subjective_only"


__all__ = [
    "RETRIEVAL_HANDOFF_SHAPE_CLASSES", "RETRIEVAL_LATENCY_CLASSES",
    "RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED", "RETRIEVAL_SELECTION_STATUSES",
    "RETRIEVAL_TOKEN_BUDGET_CLASSES", "SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA", "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE",
    "SUBJECTIVE_MEM_RETRIEVAL_MEMORY_LAYER",
    "SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY", "SubjectiveMemRetrievalContentBinding",
    "SubjectiveMemRetrievalPreparedHandoff", "SubjectiveMemRetrievalPrimaryServedMetrics",
    "SubjectiveMemRetrievalPrivateItem", "SubjectiveMemRetrievalSelectionProjection",
    "SubjectiveMemRetrievalShadowCharacterization",
    "characterize_subjective_mem_retrieval_shadow", "select_subjective_mem_retrieval_handoff",
    "subjective_mem_retrieval_private_item_reasons",
    "validate_subjective_mem_retrieval_selection_projection",
]
