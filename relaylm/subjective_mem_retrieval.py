"""RT-1A storage-neutral Subjective MEM Retrieval contracts.

This module owns the pure contract and canonical-digest foundation accepted by
``docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md``: the
retrieval request and its strict boundary, the projection row and manifest, the
closed exclusion vocabulary, the bounded selection, and the content-free usage
event. It is storage-neutral and holds no runtime state: no projection rebuild,
no cache access, no ordinary Retrieval, no RelayCTX or E1-R4 handoff, no usage
persistence, no Primary MEM read or write.

Following the rest of the codebase's idiom, validators return content-free
blocked-reason tuples instead of raising, so callers can accumulate reasons.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from relaylm.evidence_common import canonical_digest, sha256_hex

SUBJECTIVE_MEM_RETRIEVAL_REQUEST_SCHEMA = "relaylm.subjective_mem_retrieval_request.v1"
SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_ROW_SCHEMA = "relaylm.subjective_mem_retrieval_projection_row.v1"
SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_MANIFEST_SCHEMA = "relaylm.subjective_mem_retrieval_projection_manifest.v1"
SUBJECTIVE_MEM_RETRIEVAL_EXCLUSION_SCHEMA = "relaylm.subjective_mem_retrieval_exclusion.v1"
SUBJECTIVE_MEM_RETRIEVAL_SELECTION_SCHEMA = "relaylm.subjective_mem_retrieval_selection.v1"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_SCHEMA = "relaylm.subjective_mem_retrieval_usage_event.v1"
SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION = "relaylm.subjective_mem_retrieval_policy.v1"
SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION = "relaylm.subjective_mem_retrieval_projection_policy.v1"

RETRIEVAL_MEMORY_KINDS = frozenset({"episodic", "semantic"})
RETRIEVAL_FORMATION_STAGES = frozenset({"primary", "secondary"})
RETRIEVAL_LIFECYCLE_STATES = frozenset({"active", "pinned", "held", "hidden", "superseded", "purged"})
RETRIEVAL_SELECTABLE_LIFECYCLE_STATES = frozenset({"active", "pinned"})
RETRIEVAL_MUTATION_STATES = frozenset({"none", "prepared", "recovery_required", "corrupt"})
RETRIEVAL_AUTHORIZATION_RECORD_KINDS = frozenset(
    {"subjective_mem_decision", "subjective_mem_lifecycle_transition"}
)
RETRIEVAL_USAGE_EVENT_KIND = "grounded_context_admitted"
RETRIEVAL_EXCLUSION_REASONS = frozenset({
    "projection_row_invalid", "current_selector_ambiguous", "not_latest_persisted_revision",
    "canonical_binding_unverified", "receipt_unverified", "authorization_unverified",
    "scope_not_admitted", "unresolved_intent", "lifecycle_held", "lifecycle_hidden",
    "lifecycle_superseded", "lifecycle_purged", "lifecycle_unsupported", "mutation_prepared",
    "mutation_recovery_required", "mutation_corrupt", "mutation_unsupported",
    "retrieval_not_eligible", "retrieval_not_visible",
})

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")


def _body(value: object, schema: str, **extra: object) -> dict[str, object]:
    return {"schema": schema, **asdict(value), **extra}


@dataclass(frozen=True)
class SubjectiveMemRetrievalBoundary:
    """Immutable declaration of what RT-1A retrieval must never do."""

    subject_class: str = "personal_subjective_memory"
    exact_current_revision_only: bool = True
    canonical_markdown_authoritative: bool = True
    projection_rebuildable_noncanonical: bool = True
    lifecycle_and_mutation_fail_closed: bool = True
    exact_scope_required: bool = True
    primary_mem_fallback_prohibited: bool = True
    raw_query_not_persisted: bool = True
    memory_content_not_projected: bool = True
    ordinary_runtime_not_wired: bool = True
    usage_event_not_written: bool = True
    cutover_not_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SubjectiveMemRetrievalRequest:
    """One content-free request bound to exactly one projection generation."""

    character_id: str
    workspace_authority_digest: str
    admitted_scope_binding_digest: str
    query_plan_digest: str
    request_correlation_digest: str
    projection_generation_id: str
    projection_manifest_digest: str
    memory_kinds: tuple[str, ...]
    candidate_limit: int
    token_budget: int
    policy_revision: str
    boundary: SubjectiveMemRetrievalBoundary

    def to_digest_input(self) -> dict[str, object]:
        return _body(self, SUBJECTIVE_MEM_RETRIEVAL_REQUEST_SCHEMA)

    @property
    def input_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def request_id(self) -> str:
        return _opaque("smretrievalrequest", self.input_digest)


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjectionRow:
    """One content-free projection row binding every exact authority family."""

    projection_generation_id: str
    character_id: str
    memory_id: str
    memory_revision: int
    page_id: str
    block_id: str
    canonical_page_digest: str
    block_digest: str
    revision_digest: str
    current_selector_id: str
    current_selector_digest: str
    current_receipt_id: str
    current_receipt_digest: str
    authorization_record_kind: str
    authorization_id: str
    authorization_digest: str
    workspace_authority_digest: str
    scope_binding_digest: str
    lifecycle_state: str
    mutation_state: str
    retrieval_eligible: bool
    retrieval_visible: bool
    memory_kind: str
    formation_stage: str
    current_selector_unambiguous: bool
    latest_persisted_revision: bool
    finalized_receipt_verified: bool
    authorization_verified: bool
    canonical_binding_verified: bool
    scope_admitted: bool
    unresolved_intent_present: bool
    source_revision_schema: str
    source_current_state_schema: str
    source_page_schema: str
    source_block_schema: str
    source_renderer_revision: str
    source_partition_revision: str
    source_platform_revision: str
    projection_policy_revision: str

    def to_digest_input(self) -> dict[str, object]:
        return _body(self, SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_ROW_SCHEMA)

    @property
    def row_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def row_id(self) -> str:
        return _opaque("smretrievalrow", self.row_digest)


@dataclass(frozen=True)
class SubjectiveMemRetrievalProjectionManifest:
    """One complete, single-generation, rebuildable and noncanonical projection view."""

    projection_generation_id: str
    source_snapshot_digest: str
    source_schema_revision_digest: str
    row_digests: tuple[str, ...]
    built_at: str
    complete: bool
    mixed_generation: bool
    policy_revision: str

    def to_digest_input(self) -> dict[str, object]:
        return _body(
            self, SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_MANIFEST_SCHEMA,
            row_count=len(self.row_digests), canonical_authority=False, rebuildable=True,
        )

    @property
    def manifest_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def manifest_id(self) -> str:
        return _opaque("smretrievalmanifest", self.manifest_digest)


@dataclass(frozen=True)
class SubjectiveMemRetrievalExclusion:
    """One content-free record of why an exact candidate revision was not selectable."""

    projection_generation_id: str
    request_input_digest: str
    memory_id: str
    memory_revision: int
    row_digest_or_null: str | None
    reason: str

    def to_digest_input(self) -> dict[str, object]:
        return _body(self, SUBJECTIVE_MEM_RETRIEVAL_EXCLUSION_SCHEMA, content_free=True)

    @property
    def exclusion_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def exclusion_id(self) -> str:
        return _opaque("smretrievalexclusion", self.exclusion_digest)


@dataclass(frozen=True)
class SubjectiveMemRetrievalSelection:
    """One bounded selection reported over an exact candidate population."""

    request_input_digest: str
    projection_generation_id: str
    projection_manifest_digest: str
    selected_row_digests: tuple[str, ...]
    candidate_count: int
    eligible_count: int
    selected_count: int
    total_token_estimate: int
    policy_revision: str

    def to_digest_input(self) -> dict[str, object]:
        return _body(
            self, SUBJECTIVE_MEM_RETRIEVAL_SELECTION_SCHEMA,
            runtime_handoff_performed=False, usage_event_written=False, content_free=True,
        )

    @property
    def selection_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def selection_id(self) -> str:
        return _opaque("smretrievalselection", self.selection_digest)


@dataclass(frozen=True)
class SubjectiveMemRetrievalUsageEvent:
    """One content-free durable usage event for an exact consumed selected row."""

    projection_generation_id: str
    request_input_digest: str
    request_correlation_digest: str
    selection_digest: str
    row_digest: str
    memory_id: str
    memory_revision: int
    event_kind: str
    occurred_at: str
    idempotency_key_digest: str
    policy_revision: str

    def to_digest_input(self) -> dict[str, object]:
        return _body(self, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_SCHEMA, content_free=True)

    @property
    def input_digest(self) -> str:
        return canonical_digest(self.to_digest_input())

    @property
    def usage_slot_id(self) -> str:
        parts = (self.request_correlation_digest, self.row_digest, self.idempotency_key_digest)
        return _opaque("smretrievalusekey", "\x00".join(parts))

    @property
    def usage_event_id(self) -> str:
        return _opaque("smretrievalusage", self.usage_slot_id + "\x00" + self.input_digest)

    @property
    def result_id(self) -> str:
        return _opaque("smretrievaluseresult", self.usage_slot_id)

    def to_dict(self) -> dict[str, object]:
        return {
            **self.to_digest_input(), "usage_slot_id": self.usage_slot_id,
            "usage_event_id": self.usage_event_id, "result_id": self.result_id,
            "event_digest": self.input_digest,
        }


def validate_subjective_mem_retrieval_request(request: object) -> tuple[str, ...]:
    """Return content-free reasons why ``request`` is not an exact retrieval request."""
    if type(request) is not SubjectiveMemRetrievalRequest:
        return ("subjective_mem_retrieval_request_invalid",)

    digests = (
        request.workspace_authority_digest, request.admitted_scope_binding_digest,
        request.query_plan_digest, request.request_correlation_digest,
        request.projection_manifest_digest,
    )
    reasons: list[str] = []
    if not _tokens((request.character_id, request.projection_generation_id)):
        reasons.append("subjective_mem_retrieval_request_identifier_invalid")
    if not _digests(digests):
        reasons.append("subjective_mem_retrieval_request_digest_invalid")
    if (
        type(request.memory_kinds) is not tuple
        or not request.memory_kinds
        or request.memory_kinds != tuple(sorted(set(request.memory_kinds)))
        or any(value not in RETRIEVAL_MEMORY_KINDS for value in request.memory_kinds)
    ):
        reasons.append("subjective_mem_retrieval_request_memory_kinds_invalid")
    if type(request.candidate_limit) is not int or not 1 <= request.candidate_limit <= 64:
        reasons.append("subjective_mem_retrieval_candidate_limit_invalid")
    if type(request.token_budget) is not int or not 1 <= request.token_budget <= 8192:
        reasons.append("subjective_mem_retrieval_token_budget_invalid")
    if request.policy_revision != SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION:
        reasons.append("subjective_mem_retrieval_policy_revision_invalid")
    if type(request.boundary) is not SubjectiveMemRetrievalBoundary or (
        request.boundary.to_dict() != SubjectiveMemRetrievalBoundary().to_dict()
    ):
        reasons.append("subjective_mem_retrieval_boundary_invalid")
    return _dedupe(reasons)


def validate_subjective_mem_retrieval_projection_row(row: object) -> tuple[str, ...]:
    """Return content-free reasons why ``row`` is not an exact projection row."""
    if type(row) is not SubjectiveMemRetrievalProjectionRow:
        return ("subjective_mem_retrieval_projection_row_invalid",)

    tokens = (
        row.projection_generation_id, row.character_id, row.memory_id, row.page_id, row.block_id,
        row.current_selector_id, row.current_receipt_id, row.authorization_id,
        row.source_revision_schema, row.source_current_state_schema, row.source_page_schema,
        row.source_block_schema, row.source_renderer_revision, row.source_partition_revision,
        row.source_platform_revision,
    )
    digests = (
        row.block_digest, row.revision_digest, row.current_selector_digest,
        row.current_receipt_digest, row.authorization_digest, row.workspace_authority_digest,
        row.scope_binding_digest,
    )
    reasons: list[str] = []
    if not _tokens(tokens):
        reasons.append("subjective_mem_retrieval_projection_identifier_invalid")
    if type(row.memory_revision) is not int or row.memory_revision < 1:
        reasons.append("subjective_mem_retrieval_projection_revision_invalid")
    if not _digest(row.canonical_page_digest, prefixed=True) or not _digests(digests):
        reasons.append("subjective_mem_retrieval_projection_digest_invalid")
    if row.authorization_record_kind not in RETRIEVAL_AUTHORIZATION_RECORD_KINDS:
        reasons.append("subjective_mem_retrieval_projection_authorization_kind_invalid")
    if row.lifecycle_state not in RETRIEVAL_LIFECYCLE_STATES:
        reasons.append("subjective_mem_retrieval_projection_lifecycle_invalid")
    if row.mutation_state not in RETRIEVAL_MUTATION_STATES:
        reasons.append("subjective_mem_retrieval_projection_mutation_invalid")
    if row.memory_kind not in RETRIEVAL_MEMORY_KINDS:
        reasons.append("subjective_mem_retrieval_projection_memory_kind_invalid")
    if row.formation_stage not in RETRIEVAL_FORMATION_STAGES:
        reasons.append("subjective_mem_retrieval_projection_formation_stage_invalid")
    reasons.extend(_projection_row_state_reasons(row))
    if row.projection_policy_revision != SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION:
        reasons.append("subjective_mem_retrieval_projection_policy_revision_invalid")
    return _dedupe(reasons)


def _projection_row_state_reasons(row: SubjectiveMemRetrievalProjectionRow) -> list[str]:
    """Reject non-boolean state flags and eligibility that disagrees with exact state."""
    bools = (
        row.retrieval_eligible, row.retrieval_visible, row.current_selector_unambiguous,
        row.latest_persisted_revision, row.finalized_receipt_verified, row.authorization_verified,
        row.canonical_binding_verified, row.scope_admitted, row.unresolved_intent_present,
    )
    if any(type(value) is not bool for value in bools):
        return ["subjective_mem_retrieval_projection_boolean_invalid"]
    if row.lifecycle_state not in RETRIEVAL_LIFECYCLE_STATES or (
        row.mutation_state not in RETRIEVAL_MUTATION_STATES
    ):
        return []
    expected = row.mutation_state == "none" and row.lifecycle_state in RETRIEVAL_SELECTABLE_LIFECYCLE_STATES
    if row.retrieval_eligible is not expected:
        return ["subjective_mem_retrieval_projection_eligibility_pair_invalid"]
    return []


def subjective_mem_retrieval_exclusion_reasons(row: object) -> tuple[str, ...]:
    """Return the closed, content-free exclusion reasons for one candidate row."""
    if validate_subjective_mem_retrieval_projection_row(row):
        return ("projection_row_invalid",)
    assert isinstance(row, SubjectiveMemRetrievalProjectionRow)

    checks = (
        (row.current_selector_unambiguous, "current_selector_ambiguous"),
        (row.latest_persisted_revision, "not_latest_persisted_revision"),
        (row.canonical_binding_verified, "canonical_binding_unverified"),
        (row.finalized_receipt_verified, "receipt_unverified"),
        (row.authorization_verified, "authorization_unverified"), (row.scope_admitted, "scope_not_admitted"),
    )
    reasons = [reason for value, reason in checks if not value]
    if row.unresolved_intent_present:
        reasons.append("unresolved_intent")
    if row.lifecycle_state not in RETRIEVAL_SELECTABLE_LIFECYCLE_STATES:
        closed = row.lifecycle_state in {"held", "hidden", "superseded", "purged"}
        reasons.append(f"lifecycle_{row.lifecycle_state}" if closed else "lifecycle_unsupported")
    if row.mutation_state != "none":
        closed = row.mutation_state in {"prepared", "recovery_required", "corrupt"}
        reasons.append(f"mutation_{row.mutation_state}" if closed else "mutation_unsupported")
    if not row.retrieval_eligible:
        reasons.append("retrieval_not_eligible")
    if not row.retrieval_visible:
        reasons.append("retrieval_not_visible")
    return _dedupe(reasons)


def validate_subjective_mem_retrieval_projection_manifest(manifest: object) -> tuple[str, ...]:
    """Return content-free reasons why ``manifest`` is not one complete current view."""
    if type(manifest) is not SubjectiveMemRetrievalProjectionManifest:
        return ("subjective_mem_retrieval_projection_manifest_invalid",)

    reasons: list[str] = []
    if not _token(manifest.projection_generation_id):
        reasons.append("subjective_mem_retrieval_projection_manifest_identifier_invalid")
    if not _digests((manifest.source_snapshot_digest, manifest.source_schema_revision_digest)):
        reasons.append("subjective_mem_retrieval_projection_manifest_digest_invalid")
    if (
        type(manifest.row_digests) is not tuple
        or manifest.row_digests != tuple(sorted(set(manifest.row_digests)))
        or not _digests(manifest.row_digests)
    ):
        reasons.append("subjective_mem_retrieval_projection_manifest_rows_invalid")
    if _canonical_timestamp(manifest.built_at) is None:
        reasons.append("subjective_mem_retrieval_projection_manifest_time_invalid")
    if manifest.complete is not True or manifest.mixed_generation is not False:
        reasons.append("subjective_mem_retrieval_projection_manifest_state_invalid")
    if manifest.policy_revision != SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION:
        reasons.append("subjective_mem_retrieval_projection_policy_revision_invalid")
    return _dedupe(reasons)


def validate_subjective_mem_retrieval_exclusion(exclusion: object) -> tuple[str, ...]:
    """Return content-free reasons why ``exclusion`` is not a closed exclusion record."""
    if type(exclusion) is not SubjectiveMemRetrievalExclusion:
        return ("subjective_mem_retrieval_exclusion_invalid",)

    reasons: list[str] = []
    if not _tokens((exclusion.projection_generation_id, exclusion.memory_id)):
        reasons.append("subjective_mem_retrieval_exclusion_identifier_invalid")
    if type(exclusion.memory_revision) is not int or exclusion.memory_revision < 1:
        reasons.append("subjective_mem_retrieval_exclusion_revision_invalid")
    if not _digest(exclusion.request_input_digest) or (
        exclusion.row_digest_or_null is not None and not _digest(exclusion.row_digest_or_null)
    ):
        reasons.append("subjective_mem_retrieval_exclusion_digest_invalid")
    if exclusion.reason not in RETRIEVAL_EXCLUSION_REASONS:
        reasons.append("subjective_mem_retrieval_exclusion_reason_invalid")
    return _dedupe(reasons)


def validate_subjective_mem_retrieval_selection(
    *, request: object, manifest: object, rows: object, selection: object
) -> tuple[str, ...]:
    """Bind one selection to its exact request, manifest and candidate population.

    ``rows`` is the complete candidate population the selection was computed over.
    Every supplied row is validated, generation-bound and manifest-bound whether or
    not it was selected, and every reported count must equal that exact population.
    """
    reasons = [
        *validate_subjective_mem_retrieval_request(request),
        *validate_subjective_mem_retrieval_projection_manifest(manifest),
    ]
    if type(selection) is not SubjectiveMemRetrievalSelection:
        return _dedupe((*reasons, "subjective_mem_retrieval_selection_invalid"))
    if type(request) is not SubjectiveMemRetrievalRequest or (
        type(manifest) is not SubjectiveMemRetrievalProjectionManifest
    ):
        return _dedupe(reasons)
    if type(rows) is not tuple or any(
        type(row) is not SubjectiveMemRetrievalProjectionRow for row in rows
    ):
        return _dedupe((*reasons, "subjective_mem_retrieval_selection_rows_invalid"))

    reasons.extend(_selection_binding_reasons(request, manifest, selection))
    reasons.extend(_selection_population_reasons(request, manifest, rows, selection))
    return _dedupe(reasons)


def _selection_binding_reasons(
    request: SubjectiveMemRetrievalRequest,
    manifest: SubjectiveMemRetrievalProjectionManifest,
    selection: SubjectiveMemRetrievalSelection,
) -> list[str]:
    """Bind the selection header to exactly one request, generation, manifest and budget."""
    selected = selection.selected_row_digests
    counts = (
        selection.candidate_count, selection.eligible_count,
        selection.selected_count, selection.total_token_estimate,
    )
    reasons: list[str] = []
    if selection.request_input_digest != request.input_digest:
        reasons.append("subjective_mem_retrieval_selection_request_mismatch")
    if selection.projection_generation_id != request.projection_generation_id or (
        request.projection_generation_id != manifest.projection_generation_id
    ):
        reasons.append("subjective_mem_retrieval_selection_generation_mismatch")
    if selection.projection_manifest_digest != request.projection_manifest_digest or (
        request.projection_manifest_digest != manifest.manifest_digest
    ):
        reasons.append("subjective_mem_retrieval_selection_manifest_mismatch")
    if type(selected) is not tuple or selected != tuple(sorted(set(selected))) or not _digests(selected):
        reasons.append("subjective_mem_retrieval_selection_row_digests_invalid")
    if any(type(value) is not int or value < 0 for value in counts):
        reasons.append("subjective_mem_retrieval_selection_counts_invalid")
        return reasons
    if not selection.candidate_count >= selection.eligible_count >= selection.selected_count:
        reasons.append("subjective_mem_retrieval_selection_count_order_invalid")
    if (
        selection.candidate_count > request.candidate_limit
        or selection.selected_count > request.candidate_limit
        or selection.total_token_estimate > request.token_budget
    ):
        reasons.append("subjective_mem_retrieval_selection_budget_invalid")
    return reasons


def _selection_population_reasons(
    request: SubjectiveMemRetrievalRequest,
    manifest: SubjectiveMemRetrievalProjectionManifest,
    rows: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    selection: SubjectiveMemRetrievalSelection,
) -> list[str]:
    """Bind the complete supplied candidate population to the reported selection."""
    generation = {
        request.projection_generation_id, manifest.projection_generation_id,
        selection.projection_generation_id,
    }
    manifest_digests = frozenset(manifest.row_digests)
    supplied: dict[str, int] = {}
    eligible: set[str] = set()
    eligible_rows = 0
    reasons: list[str] = []
    for row in rows:
        supplied[row.row_digest] = supplied.get(row.row_digest, 0) + 1
        reasons.extend(validate_subjective_mem_retrieval_projection_row(row))
        if {row.projection_generation_id} != generation:
            reasons.append("subjective_mem_retrieval_selection_row_generation_mismatch")
        if row.row_digest not in manifest_digests:
            reasons.append("subjective_mem_retrieval_selection_row_unmanifested")
        if not subjective_mem_retrieval_exclusion_reasons(row):
            eligible.add(row.row_digest)
            eligible_rows += 1
    if len(supplied) != len(rows):
        reasons.append("subjective_mem_retrieval_selection_rows_duplicated")
    if len(rows) > request.candidate_limit:
        reasons.append("subjective_mem_retrieval_selection_candidate_limit_exceeded")
    if selection.candidate_count != len(rows):
        reasons.append("subjective_mem_retrieval_selection_candidate_count_mismatch")
    if selection.eligible_count != eligible_rows:
        reasons.append("subjective_mem_retrieval_selection_eligible_count_mismatch")

    selected = _unique_selected_digests(selection.selected_row_digests)
    if selection.selected_count != len(selected):
        reasons.append("subjective_mem_retrieval_selection_selected_count_mismatch")
    by_digest = {row.row_digest: row for row in rows}
    for digest in selected:
        row = by_digest.get(digest)
        if row is None or supplied.get(digest, 0) != 1 or digest not in manifest_digests:
            reasons.append("subjective_mem_retrieval_selection_row_missing")
        elif {row.projection_generation_id} != generation or digest not in eligible:
            reasons.append("subjective_mem_retrieval_selection_row_ineligible")
    return reasons


def derive_subjective_mem_retrieval_usage_event(
    *, request: SubjectiveMemRetrievalRequest,
    manifest: SubjectiveMemRetrievalProjectionManifest,
    rows: tuple[SubjectiveMemRetrievalProjectionRow, ...],
    selection: SubjectiveMemRetrievalSelection, row: SubjectiveMemRetrievalProjectionRow,
    event_kind: str, occurred_at: str, idempotency_key: str,
) -> tuple[SubjectiveMemRetrievalUsageEvent | None, tuple[str, ...]]:
    """Derive one content-free usage event for an exact selected eligible row."""
    reasons = list(validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=rows, selection=selection
    ))
    if validate_subjective_mem_retrieval_projection_row(row):
        reasons.append("subjective_mem_retrieval_usage_row_invalid")
    if event_kind != RETRIEVAL_USAGE_EVENT_KIND:
        reasons.append("subjective_mem_retrieval_usage_event_kind_invalid")
    canonical_time = _canonical_timestamp(occurred_at)
    if canonical_time is None:
        reasons.append("subjective_mem_retrieval_usage_time_invalid")
    if not _token(idempotency_key):
        reasons.append("subjective_mem_retrieval_usage_idempotency_key_invalid")
    if reasons:
        return (None, _dedupe(reasons))

    if row.row_digest not in selection.selected_row_digests or (
        subjective_mem_retrieval_exclusion_reasons(row)
    ):
        return (None, ("subjective_mem_retrieval_usage_binding_invalid",))
    assert canonical_time is not None
    event = SubjectiveMemRetrievalUsageEvent(
        projection_generation_id=request.projection_generation_id,
        request_input_digest=request.input_digest,
        request_correlation_digest=request.request_correlation_digest,
        selection_digest=selection.selection_digest, row_digest=row.row_digest,
        memory_id=row.memory_id, memory_revision=row.memory_revision,
        event_kind=event_kind, occurred_at=canonical_time,
        idempotency_key_digest=sha256_hex(idempotency_key.encode("utf-8")),
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    )
    return (event, ())


def validate_subjective_mem_retrieval_usage_event(event: object) -> tuple[str, ...]:
    """Return content-free reasons why ``event`` is not a durable usage event."""
    if type(event) is not SubjectiveMemRetrievalUsageEvent:
        return ("subjective_mem_retrieval_usage_event_invalid",)

    digests = (
        event.request_input_digest, event.request_correlation_digest,
        event.selection_digest, event.row_digest, event.idempotency_key_digest,
    )
    reasons: list[str] = []
    if not _tokens((event.projection_generation_id, event.memory_id)):
        reasons.append("subjective_mem_retrieval_usage_identifier_invalid")
    if type(event.memory_revision) is not int or event.memory_revision < 1:
        reasons.append("subjective_mem_retrieval_usage_revision_invalid")
    if not _digests(digests):
        reasons.append("subjective_mem_retrieval_usage_digest_invalid")
    if event.event_kind != RETRIEVAL_USAGE_EVENT_KIND:
        reasons.append("subjective_mem_retrieval_usage_event_kind_invalid")
    if _canonical_timestamp(event.occurred_at) != event.occurred_at:
        reasons.append("subjective_mem_retrieval_usage_time_invalid")
    if event.policy_revision != SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION:
        reasons.append("subjective_mem_retrieval_policy_revision_invalid")
    return _dedupe(reasons)


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _token(value: object, max_length: int = 256) -> bool:
    if not isinstance(value, str) or not 1 <= len(value) <= max_length:
        return False
    return _TOKEN_RE.fullmatch(value) is not None


def _tokens(values: Iterable[object]) -> bool:
    return all(_token(value) for value in values)


def _digest(value: object, *, prefixed: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if prefixed:
        return len(value) == 71 and value.startswith("sha256:") and _is_hex(value[7:])
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdef" for char in value)


def _digests(values: Iterable[object]) -> bool:
    return all(_digest(value) for value in values)


def _unique_selected_digests(values: object) -> tuple[str, ...]:
    """Collapse repeated selected digests while preserving their declared order."""
    if type(values) is not tuple:
        return ()
    return tuple(dict.fromkeys(values))


def _canonical_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


__all__ = [name for name in globals() if name.startswith(("SUBJECTIVE_MEM_RETRIEVAL_", "RETRIEVAL_"))]
__all__ += [
    "SubjectiveMemRetrievalBoundary", "SubjectiveMemRetrievalExclusion",
    "SubjectiveMemRetrievalProjectionManifest", "SubjectiveMemRetrievalProjectionRow",
    "SubjectiveMemRetrievalRequest", "SubjectiveMemRetrievalSelection",
    "SubjectiveMemRetrievalUsageEvent", "derive_subjective_mem_retrieval_usage_event",
    "subjective_mem_retrieval_exclusion_reasons", "validate_subjective_mem_retrieval_exclusion",
    "validate_subjective_mem_retrieval_projection_manifest",
    "validate_subjective_mem_retrieval_projection_row", "validate_subjective_mem_retrieval_request",
    "validate_subjective_mem_retrieval_selection", "validate_subjective_mem_retrieval_usage_event",
]
