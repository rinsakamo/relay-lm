"""RT-1C temporary content-free Primary-vs-Subjective shadow characterization.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md`` under the RT-1C P1 amendment, which authorized this owner as the
third RT-1C production responsibility file.

It owns exactly two things: the strict admission validation of the public
selection projection, and the deterministic content-free comparison built from
already-bounded values. It owns no selection, private evidence, canonical
parsing, durability, admission, E1-R4 policy, Primary reader, ordinary route,
fallback, or authority, and it performs no I/O.

Only values proven to come from the selection owner's closed vocabularies cross
this boundary, so a forged content-bearing projection is refused rather than
copied into the output. No prepared or admitted handoff, private item, canonical
page byte, prose, path, query, prompt, or durability value is accepted.

This surface is temporary. It and its focused tests are removed or disabled by
the RT-1D one-authority transfer, after exact post-transfer validation. The
selection owner and the durable usage ledger never import it, so the dependency
stays one-way.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from relaylm.evidence_common import dedupe
from relaylm.subjective_mem_retrieval import RETRIEVAL_EXCLUSION_REASONS
from relaylm.subjective_mem_retrieval_selection import (
    RETRIEVAL_HANDOFF_SHAPE_CLASSES, RETRIEVAL_SELECTION_STATUSES,
    RETRIEVAL_TOKEN_BUDGET_CLASSES, SUBJECTIVE_MEM_RETRIEVAL_SERVED_AUTHORITY,
    SubjectiveMemRetrievalSelectionProjection,
)

SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA = "relaylm.subjective_mem_retrieval_shadow_characterization.v1"
RETRIEVAL_LATENCY_CLASSES = frozenset({"unmeasured", "within_bound", "exceeded_bound"})
RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED = "no_leakage_detected"

_MAX_BLOCKED_REASONS = 32
_REASON_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+\Z")


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


def validate_subjective_mem_retrieval_selection_projection(projection: object) -> tuple[str, ...]:
    """Return why ``projection`` is not one exact owner-produced public projection.

    Every reported value must come from the selection owner's closed
    vocabularies, so no caller-supplied prose can be admitted here and copied
    onward. Anything outside them fails closed rather than being sanitized.
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

    A forged content-bearing projection is refused rather than copied into the
    output. That admission check is what ``leakage_outcome`` reports, and the two
    paths' runtime-private content is never combined or even accepted.
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
    "RETRIEVAL_LATENCY_CLASSES", "RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED",
    "SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA",
    "SubjectiveMemRetrievalPrimaryServedMetrics",
    "SubjectiveMemRetrievalShadowCharacterization",
    "characterize_subjective_mem_retrieval_shadow",
    "validate_subjective_mem_retrieval_selection_projection",
]
