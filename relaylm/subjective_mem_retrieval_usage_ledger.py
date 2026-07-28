"""RT-1C durable content-free Subjective MEM retrieval usage ledger.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: durably finalize the exact content-free usage events of one
prepared runtime-private handoff, and only then release that handoff as
admitted.

```text
prepared pure handoff from the selection owner
  -> this ledger validates and atomically finalizes the exact usage events
  -> only then an admitted private handoff is returned
```

The dependency is one-way: the selection owner never imports this module. All
durability is the existing ``EvidenceRecordStore`` per-evidence-space
transaction with its create-or-verify and prepared-journal recovery semantics —
no second lock, journal, durable root, atomic writer, or recovery model is
introduced here.

Nothing durable is written for a shadow comparison, a considered candidate, an
exclusion, or an empty result, and a validation or commit failure returns a
bounded content-free outcome with no admitted handoff and no fallback to
Primary MEM, a stale projection, or a cache-only counter. The durable records
outlive the disposable projection bundle and survive its deterministic rebuild.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from relaylm.evidence_common import canonical_digest, dedupe
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem_retrieval import (
    RETRIEVAL_USAGE_EVENT_KIND, SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest, SubjectiveMemRetrievalUsageEvent,
    derive_subjective_mem_retrieval_usage_event, validate_subjective_mem_retrieval_usage_event,
)
from relaylm.subjective_mem_retrieval_selection import SubjectiveMemRetrievalPreparedHandoff

SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND = "subjective_mem_retrieval_usage_event"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND = "subjective_mem_retrieval_usage_result"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA = "relaylm.subjective_mem_retrieval_usage_result.v1"
SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX = "smretrievalusetx_"

UsageStatus = Literal["finalized", "duplicate_finalized", "refused", "conflict", "failed"]


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
) -> tuple[SubjectiveMemRetrievalPreparedHandoff | None, SubjectiveMemRetrievalUsageOutcome]:
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
) -> tuple[SubjectiveMemRetrievalPreparedHandoff | None, SubjectiveMemRetrievalUsageOutcome]:
    """Resolve the exact usage slots, then commit or report why nothing was written."""

    occupied = 0
    for event in events:
        stored = transaction.read_record(
            record_kind=SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
            record_id=event.result_id,
        )
        if stored is None:
            continue
        if stored != _result_body(event):
            return None, _outcome(
                "conflict", reasons=("subjective_mem_retrieval_usage_slot_integrity_conflict",)
            )
        occupied += 1
    if occupied and occupied != len(events):
        return None, _outcome(
            "conflict", reasons=("subjective_mem_retrieval_usage_partial_existing_result",)
        )
    if occupied:
        return replace(handoff, admitted=True), _outcome(
            "duplicate_finalized", admitted=True, events=0, duplicates=len(events)
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
            "conflict", reasons=result.reasons or ("subjective_mem_retrieval_usage_slot_integrity_conflict",)
        )
    if result.status not in {"created", "duplicate_existing"}:
        return None, _outcome(
            "failed", reasons=result.reasons or ("subjective_mem_retrieval_usage_finalization_failed",)
        )
    return replace(handoff, admitted=True), _outcome(
        "finalized", admitted=True, events=len(events)
    )


def _derive_events(
    *,
    request: object,
    manifest: object,
    rows: object,
    handoff: object,
    occurred_at: str,
    idempotency_key: str,
) -> tuple[tuple[SubjectiveMemRetrievalUsageEvent, ...] | None, tuple[str, ...]]:
    """Derive one exact event per selected row of a non-shadow, unadmitted handoff."""

    reasons = _handoff_reasons(request, manifest, rows, handoff)
    if reasons:
        return None, reasons
    assert isinstance(request, SubjectiveMemRetrievalRequest)
    assert isinstance(manifest, SubjectiveMemRetrievalProjectionManifest)
    assert isinstance(rows, tuple)
    assert isinstance(handoff, SubjectiveMemRetrievalPreparedHandoff)

    by_digest = {row.row_digest: row for row in rows}
    derived: list[SubjectiveMemRetrievalUsageEvent] = []
    collected: list[str] = []
    for digest in handoff.ranked_row_digests:
        row = by_digest.get(digest)
        if row is None:
            return None, ("subjective_mem_retrieval_usage_selected_row_missing",)
        event, event_reasons = derive_subjective_mem_retrieval_usage_event(
            request=request, manifest=manifest, rows=rows, selection=handoff.selection, row=row,
            event_kind=RETRIEVAL_USAGE_EVENT_KIND, occurred_at=occurred_at,
            idempotency_key=idempotency_key,
        )
        if event is None:
            collected.extend(event_reasons)
            continue
        collected.extend(validate_subjective_mem_retrieval_usage_event(event))
        derived.append(event)
    if collected:
        return None, dedupe(collected)
    slots = {event.usage_slot_id for event in derived}
    if len(slots) != len(derived):
        return None, ("subjective_mem_retrieval_usage_slot_duplicated",)
    return tuple(derived), ()


def _handoff_reasons(
    request: object, manifest: object, rows: object, handoff: object
) -> tuple[str, ...]:
    """Refuse a shadow, already-admitted, empty, or internally disagreeing handoff."""

    if type(handoff) is not SubjectiveMemRetrievalPreparedHandoff:
        return ("subjective_mem_retrieval_usage_handoff_invalid",)
    if handoff.shadow:
        return ("subjective_mem_retrieval_usage_shadow_not_admissible",)
    if handoff.admitted:
        return ("subjective_mem_retrieval_usage_handoff_already_admitted",)
    if type(request) is not SubjectiveMemRetrievalRequest or (
        type(manifest) is not SubjectiveMemRetrievalProjectionManifest
    ):
        return ("subjective_mem_retrieval_usage_request_invalid",)
    if type(rows) is not tuple or any(
        type(row) is not SubjectiveMemRetrievalProjectionRow for row in rows
    ):
        return ("subjective_mem_retrieval_usage_rows_invalid",)

    selection = handoff.selection
    if not handoff.ranked_row_digests:
        return ("subjective_mem_retrieval_usage_selection_empty",)
    if (
        tuple(sorted(handoff.ranked_row_digests)) != selection.selected_row_digests
        or handoff.selected_count != selection.selected_count
        or handoff.total_token_estimate != selection.total_token_estimate
        or len(handoff.evidence_items) != selection.selected_count
        or selection.request_input_digest != request.input_digest
        or selection.policy_revision != SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION
    ):
        return ("subjective_mem_retrieval_usage_handoff_selection_mismatch",)
    return ()


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
    """One stable content-free transaction identity for this exact event set."""

    return SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX + canonical_digest(
        {
            "schema": SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA,
            "usage_event_ids": sorted(event.usage_event_id for event in events),
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
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_SCHEMA",
    "SUBJECTIVE_MEM_RETRIEVAL_USAGE_TRANSACTION_PREFIX",
    "SubjectiveMemRetrievalUsageOutcome",
    "finalize_subjective_mem_retrieval_usage",
]
