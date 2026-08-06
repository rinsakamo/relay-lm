"""RT-1C durable content-free Subjective MEM retrieval usage ledger.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: durably finalize the exact content-free usage events of one
prepared runtime-private handoff, and only then build the admitted handoff that
can release that evidence.

```text
prepared pure handoff from the selection owner
  -> the selection owner revalidates the whole handoff against canonical bytes
  -> exact event+result pairs are read, then atomically finalized
  -> only then a sealed admitted handoff type is constructed and returned
```

Canonical revalidation is delegated, not reimplemented: this ledger calls the
selection owner's ``validate_subjective_mem_retrieval_prepared_handoff`` before
opening durable records, so it never becomes a parser or a canonical content
authority.

Admission is a sealed type, not a flag. The prepared handoff carries no admission
state and no release path, the admitted type's public constructor always raises,
and release re-checks a module-private seal, so nothing outside this boundary can
mint, modify, or smuggle an admitted handoff. This boundary applies the seal only
for exact finalized or exact duplicate-finalized durable state. The dependency is one-way: the selection
owner never imports this module.

All durability is the existing ``EvidenceRecordStore`` per-evidence-space
transaction with its create-or-verify and prepared-transaction recovery
semantics — no second lock, durable root, atomic writer, or recovery model is
introduced here, and a partial or divergent durable pair is never repaired or
overwritten.

Nothing durable is written for a shadow comparison, a considered candidate, an
exclusion, or an empty result, and a validation or commit failure returns a
bounded content-free outcome with no admitted handoff and no fallback to Primary
MEM, a stale projection, or a cache-only counter. Durable usage records carry the
exact opaque RT-1A identities and digests the contract requires; they carry no
prose, query, prompt, or path. The records outlive the disposable projection
bundle and survive its deterministic rebuild.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from relaylm.evidence_common import canonical_digest, dedupe
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem_retrieval import (
    RETRIEVAL_USAGE_EVENT_KIND, SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest, SubjectiveMemRetrievalSelection,
    SubjectiveMemRetrievalUsageEvent, derive_subjective_mem_retrieval_usage_event,
    validate_subjective_mem_retrieval_usage_event,
)
from relaylm.subjective_mem_retrieval_selection import (
    SubjectiveMemRetrievalPreparedHandoff, _SubjectiveMemRetrievalPrivateItem,
    validate_subjective_mem_retrieval_prepared_handoff,
)

SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND = "subjective_mem_retrieval_usage_event"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND = "subjective_mem_retrieval_usage_result"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA = "relaylm.subjective_mem_retrieval_usage_result.v1"
SUBJECTIVE_MEM_RETRIEVAL_ADMITTED_HANDOFF_SCHEMA = "relaylm.subjective_mem_retrieval_admitted_handoff.v1"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX = "smretrievalusetx_"

UsageStatus = Literal["finalized", "duplicate_finalized", "refused", "conflict", "failed"]
SlotState = Literal["absent", "exact", "incomplete", "divergent"]
FinalizationStatus = Literal["finalized", "duplicate_finalized"]

_ADMISSION_SEAL = object()
"""The one admission witness. Only ``_seal_admitted_handoff`` ever applies it."""


@dataclass(frozen=True, init=False)
class SubjectiveMemRetrievalAdmittedHandoff:
    """One admitted handoff, constructible only after exact durable finalization.

    The public constructor always raises, so neither a direct call nor
    ``dataclasses.replace`` can mint or modify an admitted value; only this
    module's private factory can, and only from the exact ``finalized`` or exact
    ``duplicate_finalized`` branch of ``_finalize_locked``. Release additionally
    re-checks the module-private admission seal, so an object smuggled in through
    ``object.__new__`` releases nothing.

    ``finalization_status`` records which exact durable state authorized it.
    Releasing evidence materializes fresh plain dictionaries every time, because
    the existing E1-R4 owner requires ``type(raw) is dict``; mutating a released
    dictionary therefore cannot affect the immutable private items or any later
    release.
    """

    schema: str
    handoff_shape: str
    finalization_status: FinalizationStatus
    selected_count: int
    total_token_estimate: int
    selection: SubjectiveMemRetrievalSelection = field(repr=False)
    ranked_row_digests: tuple[str, ...] = field(repr=False)
    _private_items: tuple[_SubjectiveMemRetrievalPrivateItem, ...] = field(repr=False)
    _admission_seal: object = field(repr=False, compare=False)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("subjective_mem_retrieval_admitted_handoff_not_directly_constructible")

    def release_grounding_evidence(self) -> tuple[dict[str, object], ...]:
        """Materialize fresh E1-R4 dictionaries, but only for a sealed admission."""

        if getattr(self, "_admission_seal", None) is not _ADMISSION_SEAL:
            raise RuntimeError("subjective_mem_retrieval_admitted_handoff_unsealed")
        return tuple(_grounding_dict(item) for item in self._private_items)


def _grounding_dict(item: _SubjectiveMemRetrievalPrivateItem) -> dict[str, object]:
    """One fresh plain dict in the shape the existing E1-R4 owner consumes."""

    return {
        "memory_layer": item.memory_layer,
        "memory_id": item.memory_id,
        "revision": item.memory_revision,
        "character_id": item.character_id,
        "lifecycle_state": item.lifecycle_state,
        "current": item.current,
        "pinned": item.pinned,
        "provenance_source": item.provenance_source,
        "fact_text": item.grounded_content,
    }


@dataclass(frozen=True)
class SubjectiveMemRetrievalUsageOutcome:
    """One bounded content-free public outcome of a durable finalization attempt."""

    status: UsageStatus
    admitted: bool
    event_count: int
    duplicate_count: int
    blocked_reason_classes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA,
            "content_free": True,
            "status": self.status,
            "admitted": self.admitted,
            "event_count": self.event_count,
            "duplicate_count": self.duplicate_count,
            "blocked_reason_classes": list(self.blocked_reason_classes),
            "raw_query_persisted": False,
            "memory_content_persisted": False,
            "runtime_private_evidence_omitted": True,
        }


def finalize_subjective_mem_retrieval_usage(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    request: object,
    manifest: object,
    rows: object,
    handoff: object,
    occurred_at: str,
    idempotency_key: str,
) -> tuple[SubjectiveMemRetrievalAdmittedHandoff | None, SubjectiveMemRetrievalUsageOutcome]:
    """Atomically finalize every usage event of one handoff before admitting it."""

    events, reasons = _derive_events(
        request=request, manifest=manifest, rows=rows, handoff=handoff,
        occurred_at=occurred_at, idempotency_key=idempotency_key,
    )
    if events is None:
        return None, _outcome("refused", reasons=reasons)
    assert isinstance(handoff, SubjectiveMemRetrievalPreparedHandoff)
    try:
        with store.transaction(evidence_space_id) as transaction:
            return _finalize_locked(transaction, handoff=handoff, events=events)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, _outcome("failed", reasons=("subjective_mem_retrieval_usage_store_unavailable",))


def _finalize_locked(
    transaction: EvidenceStoreTransaction,
    *,
    handoff: SubjectiveMemRetrievalPreparedHandoff,
    events: tuple[SubjectiveMemRetrievalUsageEvent, ...],
) -> tuple[SubjectiveMemRetrievalAdmittedHandoff | None, SubjectiveMemRetrievalUsageOutcome]:
    """Resolve every exact event+result pair, then commit or report what blocked it."""

    states = tuple(_slot_state(transaction, event) for event in events)
    if "divergent" in states:
        return None, _outcome(
            "conflict", reasons=("subjective_mem_retrieval_usage_slot_integrity_conflict",)
        )
    if "incomplete" in states:
        return None, _outcome(
            "conflict", reasons=("subjective_mem_retrieval_usage_pair_incomplete",)
        )
    if "exact" in states and "absent" in states:
        return None, _outcome(
            "conflict", reasons=("subjective_mem_retrieval_usage_partial_existing_result",)
        )
    if "exact" in states:
        return _seal_admitted_handoff(handoff, "duplicate_finalized"), _outcome(
            "duplicate_finalized", admitted=True, duplicates=len(events)
        )

    result = transaction.commit(
        transaction_id=_transaction_id(events),
        records=tuple(
            item
            for event in events
            for item in (
                (
                    SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
                    event.usage_event_id,
                    event.to_dict(),
                ),
                (
                    SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
                    event.result_id,
                    _result_body(event),
                ),
            )
        ),
        logs=(),
    )
    if result.status == "collision":
        return None, _outcome(
            "conflict",
            reasons=result.reasons or ("subjective_mem_retrieval_usage_slot_integrity_conflict",),
        )
    if result.status not in {"created", "duplicate_existing"}:
        return None, _outcome(
            "failed",
            reasons=result.reasons or ("subjective_mem_retrieval_usage_finalization_failed",),
        )
    return _seal_admitted_handoff(handoff, "finalized"), _outcome(
        "finalized", admitted=True, events=len(events)
    )


def _slot_state(
    transaction: EvidenceStoreTransaction, event: SubjectiveMemRetrievalUsageEvent
) -> SlotState:
    """Classify one usage slot from its exact durable event and result pair.

    The stable result slot is authoritative and is resolved first, because
    ``result_id`` binds only the request correlation, selected row, and
    idempotency identity. The result names the original ``usage_event_id``, and
    that original event is what the replay is judged against.

    The first finalization owns the occurrence time. A response-lost replay
    arriving in a later wall-clock second is therefore still the same slot: the
    newly supplied occurrence is the only value not compared, and every
    immutable slot-bearing field must still agree exactly. Substituting the
    stored occurrence and re-deriving the whole event compares all of them at
    once -- generation, request input and correlation digests, selection digest,
    row digest, memory identity and revision, event kind, idempotency-key
    digest, and policy revision -- and simultaneously proves the stored pair is
    internally exact.

    A slot is occupied only when both records exist and agree. One record alone
    is partial durable state, and any divergent body is an integrity conflict;
    neither is ever repaired or overwritten.
    """

    stored_result = transaction.read_record(
        record_kind=SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
        record_id=event.result_id,
    )
    if stored_result is None:
        stored_event = transaction.read_record(
            record_kind=SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
            record_id=event.usage_event_id,
        )
        return "absent" if stored_event is None else "incomplete"
    if type(stored_result) is not dict:
        return "divergent"
    original_id = stored_result.get("usage_event_id")
    if type(original_id) is not str or not original_id:
        return "divergent"
    stored_event = transaction.read_record(
        record_kind=SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
        record_id=original_id,
    )
    if stored_event is None:
        return "incomplete"
    if type(stored_event) is not dict:
        return "divergent"
    occurred_at = stored_event.get("occurred_at")
    if type(occurred_at) is not str:
        return "divergent"
    original = replace(event, occurred_at=occurred_at)
    if validate_subjective_mem_retrieval_usage_event(original):
        return "divergent"
    if original.usage_event_id != original_id:
        return "divergent"
    if original.to_dict() != stored_event or _result_body(original) != stored_result:
        return "divergent"
    return "exact"


def _derive_events(
    *,
    request: object,
    manifest: object,
    rows: object,
    handoff: object,
    occurred_at: str,
    idempotency_key: str,
) -> tuple[tuple[SubjectiveMemRetrievalUsageEvent, ...] | None, tuple[str, ...]]:
    """Derive one exact event per selected row of a non-shadow prepared handoff."""

    reasons = _handoff_reasons(request, manifest, rows, handoff)
    if reasons:
        return None, reasons
    assert isinstance(request, SubjectiveMemRetrievalRequest)
    assert isinstance(manifest, SubjectiveMemRetrievalProjectionManifest)
    assert isinstance(rows, tuple)
    assert isinstance(handoff, SubjectiveMemRetrievalPreparedHandoff)

    reasons = validate_subjective_mem_retrieval_prepared_handoff(
        request=request, manifest=manifest, rows=rows, handoff=handoff
    )
    if reasons:
        return None, reasons
    by_digest = {row.row_digest: row for row in rows}
    derived: list[SubjectiveMemRetrievalUsageEvent] = []
    collected: list[str] = []
    for digest in handoff.ranked_row_digests:
        event, event_reasons = derive_subjective_mem_retrieval_usage_event(
            request=request, manifest=manifest, rows=rows, selection=handoff.selection,
            row=by_digest[digest], event_kind=RETRIEVAL_USAGE_EVENT_KIND,
            occurred_at=occurred_at, idempotency_key=idempotency_key,
        )
        if event is None:
            collected.extend(event_reasons)
            continue
        collected.extend(validate_subjective_mem_retrieval_usage_event(event))
        derived.append(event)
    if collected:
        return None, dedupe(collected)
    if len({event.usage_slot_id for event in derived}) != len(derived):
        return None, ("subjective_mem_retrieval_usage_slot_duplicated",)
    return tuple(derived), ()


def _handoff_reasons(
    request: object, manifest: object, rows: object, handoff: object
) -> tuple[str, ...]:
    """Refuse a shadow, empty, unbound, or internally disagreeing prepared handoff."""

    if type(handoff) is not SubjectiveMemRetrievalPreparedHandoff:
        return ("subjective_mem_retrieval_usage_handoff_invalid",)
    if handoff.shadow:
        return ("subjective_mem_retrieval_usage_shadow_not_admissible",)
    if type(request) is not SubjectiveMemRetrievalRequest or (
        type(manifest) is not SubjectiveMemRetrievalProjectionManifest
    ):
        return ("subjective_mem_retrieval_usage_request_invalid",)
    if type(rows) is not tuple or any(
        type(row) is not SubjectiveMemRetrievalProjectionRow for row in rows
    ):
        return ("subjective_mem_retrieval_usage_rows_invalid",)

    selection = handoff.selection
    if type(selection) is not SubjectiveMemRetrievalSelection:
        return ("subjective_mem_retrieval_usage_handoff_invalid",)
    if not handoff.ranked_row_digests:
        return ("subjective_mem_retrieval_usage_selection_empty",)
    if (
        tuple(sorted(handoff.ranked_row_digests)) != selection.selected_row_digests
        or len(set(handoff.ranked_row_digests)) != len(handoff.ranked_row_digests)
        or handoff.selected_count != selection.selected_count
        or handoff.total_token_estimate != selection.total_token_estimate
        or selection.request_input_digest != request.input_digest
        or selection.policy_revision != SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION
    ):
        return ("subjective_mem_retrieval_usage_handoff_selection_mismatch",)
    if any(digest not in {row.row_digest for row in rows} for digest in handoff.ranked_row_digests):
        return ("subjective_mem_retrieval_usage_selected_row_missing",)
    return ()


def _seal_admitted_handoff(
    handoff: SubjectiveMemRetrievalPreparedHandoff, finalization_status: FinalizationStatus
) -> SubjectiveMemRetrievalAdmittedHandoff:
    """Seal one admitted handoff; reached only from exact durable success.

    The public constructor raises, so the fields are installed directly and the
    admission seal is applied last. This is the only site that applies it.
    """

    admitted = object.__new__(SubjectiveMemRetrievalAdmittedHandoff)
    for name, value in (
        ("schema", SUBJECTIVE_MEM_RETRIEVAL_ADMITTED_HANDOFF_SCHEMA),
        ("handoff_shape", handoff.handoff_shape),
        ("finalization_status", finalization_status),
        ("selected_count", handoff.selected_count),
        ("total_token_estimate", handoff.total_token_estimate),
        ("selection", handoff.selection),
        ("ranked_row_digests", handoff.ranked_row_digests),
        ("_private_items", handoff._private_items),
        ("_admission_seal", _ADMISSION_SEAL),
    ):
        object.__setattr__(admitted, name, value)
    return admitted


def _result_body(event: SubjectiveMemRetrievalUsageEvent) -> dict[str, object]:
    """The stable, content-free idempotency result for exactly one usage slot."""

    return {
        "schema": SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA,
        "content_free": True,
        "usage_slot_id": event.usage_slot_id,
        "usage_event_id": event.usage_event_id,
        "event_digest": event.input_digest,
        "event_kind": event.event_kind,
        "projection_generation_id": event.projection_generation_id,
        "policy_revision": event.policy_revision,
        "status": "finalized",
    }


def _transaction_id(events: tuple[SubjectiveMemRetrievalUsageEvent, ...]) -> str:
    """One stable content-free transaction identity for this exact slot set.

    The identity binds the stable ``result_id`` slots, never ``usage_event_id``,
    because the latter folds ``occurred_at``. A response-lost replay in a later
    wall-clock second therefore presents the same transaction identity as the
    original finalization, so an attempted second write for the same slots
    collides and fails closed instead of creating a parallel pair beside an
    orphaned event.
    """

    return SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX + canonical_digest(
        {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA,
            "usage_result_slot_ids": sorted(event.result_id for event in events),
        }
    )


def _outcome(
    status: UsageStatus,
    *,
    admitted: bool = False,
    events: int = 0,
    duplicates: int = 0,
    reasons: tuple[str, ...] = (),
) -> SubjectiveMemRetrievalUsageOutcome:
    return SubjectiveMemRetrievalUsageOutcome(
        status=status, admitted=admitted, event_count=events, duplicate_count=duplicates,
        blocked_reason_classes=dedupe(reasons),
    )


__all__ = [
    "SUBJECTIVE_MEM_RETRIEVAL_ADMITTED_HANDOFF_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX",
    "SubjectiveMemRetrievalAdmittedHandoff",
    "SubjectiveMemRetrievalUsageOutcome",
    "finalize_subjective_mem_retrieval_usage",
]
