"""RT-1C exact selection, runtime-private handoff, and shadow characterization.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: select the exact current eligible Subjective revisions of exactly
one verified projection generation, prepare the bounded runtime-private handoff
the existing E1-R4 grounding owner already consumes, and characterize the
Primary served path against the Subjective shadow path without combining them.

Nothing here serves memory. The prepared handoff is shadow by default and is
never ordinary-route admitted: only the durable usage ledger may return an
admitted handoff, and it depends on this owner rather than the other way round.
There is no ordinary request-path call, RelayCTX injection, backend call,
response rewrite, projection repair, canonical read, path resolution, or Primary
MEM access, and E1-R4 grounding behaviour is unchanged — its bounded constants
are imported read-only so no second copy of its limits exists.

Canonical Subjective prose reaches this owner only as bounded content bindings
supplied by the canonical owner. Selected prose and opaque lineage stay out of
``repr``, out of the public projection, and out of characterization. Every entry
point returns content-free reasons instead of raising.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal

from relaylm.evidence_common import dedupe, utf8_text_digest
from relaylm.relaymem_grounded_recall_response import (
    GROUNDED_RECALL_CONTEXT_SCHEMA, MAX_EVIDENCE_ITEMS, MAX_FACT_TEXT_CHARS,
)
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION, SubjectiveMemRetrievalProjectionManifest,
    SubjectiveMemRetrievalProjectionRow, SubjectiveMemRetrievalRequest,
    SubjectiveMemRetrievalSelection, subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row, validate_subjective_mem_retrieval_request,
    validate_subjective_mem_retrieval_selection,
)

SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA = "relaylm.subjective_mem_retrieval_private_handoff.v1"
SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA = "relaylm.subjective_mem_retrieval_selection_projection.v1"
SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA = "relaylm.subjective_mem_retrieval_shadow_characterization.v1"
SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE = f"{GROUNDED_RECALL_CONTEXT_SCHEMA}.evidence_items"
SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY = "primary_mem"

RETRIEVAL_LATENCY_CLASSES = frozenset({"unmeasured", "within_bound", "exceeded_bound"})

SelectionStatus = Literal["prepared", "prepared_empty", "refused"]

_FORMATION_PROVENANCE = {"primary": "user_assertion", "secondary": "other_allowed_source"}
_MAX_TOKEN_ESTIMATE = 8192


@dataclass(frozen=True)
class SubjectiveMemRetrievalContentBinding:
    """One bounded canonical-content binding for exactly one projection row.

    The canonical owner supplies the prose, its exact digest, and the bounded
    token estimate. This owner never scans a workspace, resolves a path, reads a
    file, reconstructs a selector, receipt or authorization, or repairs a row.
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
class SubjectiveMemRetrievalPreparedHandoff:
    """One prepared runtime-private handoff that is not ordinary-route admitted.

    ``shadow`` marks an explicit shadow-only result that can never be admitted.
    ``admitted`` becomes true only through the durable usage ledger, after the
    exact usage events are finalized.
    """

    schema: str
    handoff_shape: str
    shadow: bool
    admitted: bool
    selected_count: int
    total_token_estimate: int
    selection: SubjectiveMemRetrievalSelection = field(repr=False)
    ranked_row_digests: tuple[str, ...] = field(repr=False)
    evidence_items: tuple[Mapping[str, object], ...] = field(repr=False)

    def admitted_grounding_evidence(
        self,
    ) -> tuple[tuple[Mapping[str, object], ...] | None, tuple[str, ...]]:
        """Release the private evidence only for a finalized non-shadow handoff."""

        if self.shadow:
            return None, ("subjective_mem_retrieval_handoff_shadow_not_admitted",)
        if not self.admitted:
            return None, ("subjective_mem_retrieval_handoff_not_finalized",)
        return self.evidence_items, ()


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
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA,
            "content_free": True,
            "status": self.status,
            "shadow": self.shadow,
            "attempted": self.attempted,
            "projection_generation_ready": self.projection_generation_ready,
            "candidate_count": self.candidate_count,
            "eligible_count": self.eligible_count,
            "selected_count": self.selected_count,
            "not_requested_kind_count": self.not_requested_kind_count,
            "excluded_count_by_reason_class": [
                [reason, count] for reason, count in self.excluded_count_by_reason_class
            ],
            "handoff_shape_class": self.handoff_shape_class,
            "token_budget_class": self.token_budget_class,
            "blocked_reason_classes": list(self.blocked_reason_classes),
            "runtime_private_evidence_omitted": self.runtime_private_evidence_omitted,
            "ordinary_route_admitted": self.ordinary_route_admitted,
            "usage_event_recorded": self.usage_event_recorded,
            "served_authority": SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY,
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
    bindings, reasons = _bound_content(request, ranked, content_bindings)
    if bindings is None:
        return None, _refused(reasons, shadow=shadow, population=population, token_budget=budget)
    total = sum(binding.token_estimate for binding in bindings)
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
        handoff_shape=SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE, shadow=shadow, admitted=False,
        selected_count=len(ranked), total_token_estimate=total, selection=selection,
        ranked_row_digests=tuple(row.row_digest for row in ranked),
        evidence_items=tuple(_evidence_item(row, bindings[index]) for index, row in enumerate(ranked)),
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

    Eligibility is the RT-1A closed vocabulary alone, so the reported eligible
    count keeps its contract meaning. Requested memory kinds narrow the eligible
    rows afterwards, and pinned state orders them only after exact eligibility.
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
    exclusions = tuple(sorted(counts.items()))
    return exclusions, tuple(eligible), tuple(ranked)


def _bound_content(
    request: SubjectiveMemRetrievalRequest,
    ranked: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    content_bindings: object,
) -> tuple[tuple[SubjectiveMemRetrievalContentBinding, ...] | None, tuple[str, ...]]:
    """Bind exactly one supplied content item to each selected row, or fail closed."""

    if type(content_bindings) is not tuple or any(
        type(item) is not SubjectiveMemRetrievalContentBinding for item in content_bindings
    ):
        return None, ("subjective_mem_retrieval_selection_content_binding_invalid",)
    by_digest: dict[str, SubjectiveMemRetrievalContentBinding] = {}
    for binding in content_bindings:
        if binding.row_digest in by_digest:
            return None, ("subjective_mem_retrieval_selection_content_binding_duplicated",)
        by_digest[binding.row_digest] = binding
    selected = {row.row_digest for row in ranked}
    if set(by_digest) - selected:
        return None, ("subjective_mem_retrieval_selection_content_binding_unselected",)
    bound: list[SubjectiveMemRetrievalContentBinding] = []
    for row in ranked:
        binding = by_digest.get(row.row_digest)
        if binding is None:
            return None, ("subjective_mem_retrieval_selection_content_binding_missing",)
        reasons = _content_binding_reasons(request, row, binding)
        if reasons:
            return None, reasons
        bound.append(binding)
    return tuple(bound), ()


def _content_binding_reasons(
    request: SubjectiveMemRetrievalRequest,
    row: SubjectiveMemRetrievalProjectionRow,
    binding: SubjectiveMemRetrievalContentBinding,
) -> tuple[str, ...]:
    """Reject a foreign, stale, malformed, oversized or mismatched content binding."""

    if (
        binding.memory_id != row.memory_id
        or binding.memory_revision != row.memory_revision
        or binding.character_id != request.character_id
        or binding.workspace_authority_digest != request.workspace_authority_digest
        or binding.scope_binding_digest != request.admitted_scope_binding_digest
    ):
        return ("subjective_mem_retrieval_selection_content_binding_mismatch",)
    if type(binding.grounded_content) is not str or not 1 <= len(
        binding.grounded_content
    ) <= MAX_FACT_TEXT_CHARS:
        return ("subjective_mem_retrieval_selection_content_binding_malformed",)
    if utf8_text_digest(binding.grounded_content) != binding.grounded_content_digest:
        return ("subjective_mem_retrieval_selection_content_binding_digest_mismatch",)
    if type(binding.token_estimate) is not int or not 1 <= binding.token_estimate <= _MAX_TOKEN_ESTIMATE:
        return ("subjective_mem_retrieval_selection_content_binding_token_estimate_invalid",)
    return ()


def _evidence_item(
    row: SubjectiveMemRetrievalProjectionRow, binding: SubjectiveMemRetrievalContentBinding
) -> dict[str, object]:
    """Build the bounded private input shape the existing E1-R4 owner consumes.

    Formation stage classifies the already authorized revision into E1-R4's
    support vocabulary; no lineage is invented and no grounding policy changes.
    """

    return {
        "memory_layer": "subjective",
        "memory_id": row.memory_id,
        "revision": row.memory_revision,
        "character_id": row.character_id,
        "lifecycle_state": row.lifecycle_state,
        "current": True,
        "pinned": row.lifecycle_state == "pinned",
        "provenance_source": _FORMATION_PROVENANCE[row.formation_stage],
        "fact_text": binding.grounded_content,
    }


def _refused(
    reasons: tuple[str, ...],
    *,
    shadow: bool,
    population: tuple[object, ...] | None = None,
    total: int = 0,
    token_budget: int = 0,
) -> SubjectiveMemRetrievalSelectionProjection:
    """Report one refusal; an unverified generation reports no population at all."""

    if population is None:
        return SubjectiveMemRetrievalSelectionProjection(
            status="refused", shadow=shadow, attempted=True, projection_generation_ready=False,
            candidate_count=0, eligible_count=0, selected_count=0, not_requested_kind_count=0,
            excluded_count_by_reason_class=(), handoff_shape_class="absent",
            token_budget_class="empty", blocked_reason_classes=reasons,
        )
    return _projection(
        "refused", shadow=shadow, blocked=reasons, population=population, total=total,
        token_budget=token_budget, prepared=False,
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
) -> SubjectiveMemRetrievalSelectionProjection:
    rows, exclusions, eligible, ranked = population
    return SubjectiveMemRetrievalSelectionProjection(
        status=status, shadow=shadow, attempted=True, projection_generation_ready=True,
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


def characterize_subjective_mem_retrieval_shadow(
    *,
    primary: object,
    shadow: object,
    replay: object | None = None,
    subjective_latency_class: str = "unmeasured",
    projection_rebuild_equivalent: bool | None = None,
) -> tuple[SubjectiveMemRetrievalShadowCharacterization | None, tuple[str, ...]]:
    """Compare two already content-free result projections deterministically.

    Only bounded classes cross the boundary: no raw prose, private handoff,
    digest, path, or correlation material is accepted or reported, and the two
    paths' runtime-private content is never combined.
    """

    reasons = _characterization_input_reasons(
        primary, shadow, replay, subjective_latency_class, projection_rebuild_equivalent
    )
    if reasons:
        return None, reasons
    assert isinstance(primary, SubjectiveMemRetrievalPrimaryServedMetrics)
    assert isinstance(shadow, SubjectiveMemRetrievalSelectionProjection)
    leaked = not _content_free(shadow) or (replay is not None and not _content_free(replay))
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
            leakage_outcome="leakage_detected" if leaked else "no_leakage_detected",
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
    """Accept only bounded content-free inputs describing an explicit shadow run."""

    reasons: list[str] = []
    if type(primary) is not SubjectiveMemRetrievalPrimaryServedMetrics or (
        primary.latency_class not in RETRIEVAL_LATENCY_CLASSES
    ):
        reasons.append("subjective_mem_retrieval_characterization_primary_metrics_invalid")
    if type(shadow) is not SubjectiveMemRetrievalSelectionProjection or (
        replay is not None and type(replay) is not SubjectiveMemRetrievalSelectionProjection
    ):
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


def _content_free(projection: SubjectiveMemRetrievalSelectionProjection) -> bool:
    """Prove one public projection carries no digest, path, or unbounded text."""

    for value in _flatten(projection.to_dict()):
        if type(value) is not str:
            continue
        if len(value) > 128 or "/" in value or value.startswith("sha256:"):
            return False
        if len(value) >= 32 and all(char in "0123456789abcdef" for char in value):
            return False
    return True


def _flatten(value: object) -> list[object]:
    if isinstance(value, dict):
        return [item for pair in value.items() for item in _flatten(list(pair))]
    if isinstance(value, list):
        return [item for entry in value for item in _flatten(entry)]
    return [value]


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
    "RETRIEVAL_LATENCY_CLASSES",
    "SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE",
    "SUBJECTIVE_MEM_RETRIEVAL_SELECTION_PROJECTION_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY",
    "SubjectiveMemRetrievalContentBinding",
    "SubjectiveMemRetrievalPreparedHandoff",
    "SubjectiveMemRetrievalPrimaryServedMetrics",
    "SubjectiveMemRetrievalSelectionProjection",
    "SubjectiveMemRetrievalShadowCharacterization",
    "characterize_subjective_mem_retrieval_shadow",
    "select_subjective_mem_retrieval_handoff",
]
