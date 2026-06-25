#!/usr/bin/env python3
"""Pure I1-GA contract/fault model smoke; imports no RelayLM production code."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Final, Literal

SCHEMA: Final = "relaymem.slp_durable_finalization_fault_model.v0"
PROJECTION_SCHEMA: Final = "relaymem.slp_durable_finalization_projection.v0"
CANARY: Final = "I1G_PROTECTED_CANARY_USER_ASSISTANT_DO_NOT_LEAK_9f4c7a"

Classification = Literal[
    "safe no-op",
    "idempotent continue",
    "retryable replay",
    "cleanup required",
    "manual isolation required",
    "corruption / invariant violation",
]

ALLOWED_PROJECTION_KEYS: Final = frozenset(
    {
        "schema_version",
        "enabled",
        "dry_run_only",
        "apply_enabled",
        "outcome_status",
        "failure_stage",
        "reason_ids",
        "record_present",
        "sealed",
        "replayable",
        "source_present",
        "queue_present",
        "complete",
        "cleanup_required",
        "bounded_segment_count",
        "bounded_attempt_count",
    }
)
FORBIDDEN_TOKENS: Final = (
    CANARY,
    "user_text",
    "assistant_text",
    "governed_summary",
    "namespace",
    "run_id",
    "session_id",
    "job_id",
    "dispatch_idempotency_key",
    "lineage",
    "idempotency_key",
    "filesystem_path",
    "source_integrity_digest",
    "lease_token",
    "created_at",
    "updated_at",
    "raw_exception",
    "/runtime/private/",
)


@dataclass(frozen=True)
class FaultCase:
    number: int
    fault_point: str
    classification: Classification
    status: str
    reason_id: str
    record_present: bool
    sealed: bool
    source_present: bool
    queue_present: bool
    complete: bool
    cleanup_required: bool
    replayable: bool

    def __post_init__(self) -> None:
        if self.complete and not self.sealed:
            raise AssertionError("complete_requires_seal")
        expected_replayable = (
            self.sealed
            and not self.complete
            and self.classification not in {
                "manual isolation required",
                "corruption / invariant violation",
            }
        )
        if self.replayable != expected_replayable:
            raise AssertionError(f"replayable_state_mismatch:{self.number}")
        if self.queue_present and not self.source_present and self.number != 28:
            raise AssertionError(f"queue_without_source_unclassified:{self.number}")
        if self.number == 28 and self.classification != "corruption / invariant violation":
            raise AssertionError("queue_without_source_must_be_invariant_violation")
        for value in (self.status, self.reason_id):
            if not value or len(value) > 96 or not value.isascii():
                raise AssertionError(f"bounded_ascii_status_required:{self.number}")

    def projection(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "enabled": True,
            "dry_run_only": False,
            "apply_enabled": True,
            "outcome_status": self.status,
            "failure_stage": "fault_model",
            "reason_ids": [self.reason_id],
            "record_present": self.record_present,
            "sealed": self.sealed,
            "replayable": self.replayable,
            "source_present": self.source_present,
            "queue_present": self.queue_present,
            "complete": self.complete,
            "cleanup_required": self.cleanup_required,
            "bounded_segment_count": 0,
            "bounded_attempt_count": 1,
        }


CASES: Final = (
    FaultCase(1, "before finalized-turn production", "safe no-op", "not_created", "finalized_turn_unavailable", False, False, False, False, False, False, False),
    FaultCase(2, "before durable record creation", "safe no-op", "publication_failed", "record_not_created", False, False, False, False, False, False, False),
    FaultCase(3, "during record temp write", "cleanup required", "publication_failed", "temp_write_failed", True, False, False, False, False, True, False),
    FaultCase(4, "before or after atomic replace", "retryable replay", "publication_uncertain", "canonical_reread_required", True, False, False, False, False, True, False),
    FaultCase(5, "directory fsync uncertain", "retryable replay", "publication_uncertain", "directory_durability_unconfirmed", True, False, False, False, False, False, False),
    FaultCase(6, "immediately before visible delivery", "idempotent continue", "evidence_ready", "visible_release_pending", True, True, False, False, False, False, True),
    FaultCase(7, "immediately after visible delivery", "retryable replay", "replay_pending", "post_release_interruption", True, True, False, False, False, False, True),
    FaultCase(8, "before protected source publication", "retryable replay", "replay_pending", "source_not_published", True, True, False, False, False, False, True),
    FaultCase(9, "source committed before B2", "idempotent continue", "replay_pending", "queue_not_published", True, True, True, False, False, False, True),
    FaultCase(10, "ambiguous B2 enqueue failure", "retryable replay", "replay_pending", "queue_outcome_uncertain", True, True, True, False, False, False, True),
    FaultCase(11, "B2 enqueued_new before completion", "idempotent continue", "completion_pending", "queue_published", True, True, True, True, False, False, True),
    FaultCase(12, "exact duplicate_existing", "idempotent continue", "completion_pending", "exact_duplicate", True, True, True, True, False, False, True),
    FaultCase(13, "completion marker write", "retryable replay", "completion_uncertain", "completion_reread_required", True, True, True, True, False, True, True),
    FaultCase(14, "after completion before cleanup", "cleanup required", "complete", "cleanup_pending", True, True, True, True, True, True, False),
    FaultCase(15, "cleanup failure", "cleanup required", "complete", "cleanup_failed", True, True, True, True, True, True, False),
    FaultCase(16, "restart with double replay", "idempotent continue", "converged", "concurrent_replay", True, True, True, True, False, False, True),
    FaultCase(17, "original finalizer and replay race", "idempotent continue", "converged", "finalizer_replay_race", True, True, True, True, False, False, True),
    FaultCase(18, "two concurrent replay processes", "retryable replay", "retryable", "replay_lock_busy", True, True, False, False, False, False, True),
    FaultCase(19, "same identity different content", "manual isolation required", "isolated", "content_collision", True, True, False, False, False, False, False),
    FaultCase(20, "corrupt or truncated record", "corruption / invariant violation", "corrupt", "record_invalid", True, False, False, False, False, False, False),
    FaultCase(21, "unsupported schema", "manual isolation required", "isolated", "schema_unsupported", True, False, False, False, False, False, False),
    FaultCase(22, "symlink path escape unsafe type", "corruption / invariant violation", "corrupt", "unsafe_path_or_type", True, False, False, False, False, False, False),
    FaultCase(23, "root missing", "manual isolation required", "blocked", "root_missing", False, False, False, False, False, False, False),
    FaultCase(24, "permission denied", "manual isolation required", "blocked", "permission_denied", True, False, False, False, False, False, False),
    FaultCase(25, "disk full capacity exhausted", "retryable replay", "retryable", "capacity_exhausted", True, False, False, False, False, True, False),
    FaultCase(26, "stale record retention expiry", "cleanup required", "retention", "classified_at_expiry", True, False, False, False, False, True, False),
    FaultCase(27, "source exists queue absent", "idempotent continue", "replay_pending", "orphan_source", True, True, True, False, False, False, True),
    FaultCase(28, "queue exists source absent", "corruption / invariant violation", "invariant_violation", "queue_without_source", True, True, False, True, False, False, False),
    FaultCase(29, "stale replay against terminal B3", "safe no-op", "converged", "downstream_terminal", True, True, True, True, False, False, True),
    FaultCase(30, "content leakage canary", "safe no-op", "projection_valid", "content_free", True, True, True, True, False, False, True),
)


def main() -> None:
    assert SCHEMA.endswith(".v0")
    assert len(CASES) == 30
    assert tuple(case.number for case in CASES) == tuple(range(1, 31))
    assert len({case.fault_point for case in CASES}) == 30
    assert {case.classification for case in CASES} == {
        "safe no-op",
        "idempotent continue",
        "retryable replay",
        "cleanup required",
        "manual isolation required",
        "corruption / invariant violation",
    }

    serialized: list[str] = []
    for case in CASES:
        projection = case.projection()
        assert frozenset(projection) == ALLOWED_PROJECTION_KEYS
        encoded = json.dumps(projection, sort_keys=True, ensure_ascii=True)
        serialized.append(encoded)
        lowered = encoded.lower()
        assert all(token.lower() not in lowered for token in FORBIDDEN_TOKENS)
        assert CANARY not in repr(case)

    private_record = {
        "runtime_private": True,
        "content_included": True,
        "protected_capture": CANARY,
        "filesystem_path": "/runtime/private/i1g/record.json",
        "source_integrity_digest": "d" * 64,
    }
    assert CANARY in json.dumps(private_record)
    assert CANARY not in "".join(serialized)
    assert all("protected_capture" not in item for item in serialized)

    print("RelayLM I1-GA pre-enqueue fault model smoke passed.")


if __name__ == "__main__":
    main()
