"""I-7A/B held outcome governance contract constants.

The contract module is intentionally schema-only.  It does not discover held
items, read queue/source payloads, start workers, or mutate RelayMEM state.
"""
from __future__ import annotations

HELD_OUTCOME_CANDIDATE_SCHEMA = "relaylm.mem.held_outcome_candidate.v0"
HELD_SOURCE_EVIDENCE_REF_SCHEMA = "relaylm.mem.held_source_evidence_ref.v0"
HELD_APPLY_PREFLIGHT_SCHEMA = "relaylm.lab.held_apply_preflight.v0"
HELD_DISCARD_PREFLIGHT_SCHEMA = "relaylm.lab.held_discard_preflight.v0"

HELD_STATUS = "held"
APPLIED_STATUS = "applied"
DISCARDED_STATUS = "discarded"
BLOCKED_STATUS = "blocked"
FAILED_STATUS = "failed"
RECOVERY_REQUIRED_STATUS = "recovery_required"
CORRUPT_STATUS = "corrupt"
TERMINAL_SUCCEEDED_STATUS = "terminal_succeeded"
TERMINAL_FAILED_STATUS = "terminal_failed"

GOVERNABLE_HELD_STATUSES = frozenset({HELD_STATUS})
ALREADY_FINAL_STATUSES = frozenset({APPLIED_STATUS, DISCARDED_STATUS})
NON_HELD_DISTINCTION_STATUSES = frozenset({
    BLOCKED_STATUS,
    FAILED_STATUS,
    RECOVERY_REQUIRED_STATUS,
    CORRUPT_STATUS,
    TERMINAL_SUCCEEDED_STATUS,
    TERMINAL_FAILED_STATUS,
})
HELD_CANDIDATE_STATUSES = (
    GOVERNABLE_HELD_STATUSES | ALREADY_FINAL_STATUSES | NON_HELD_DISTINCTION_STATUSES
)

# B3 queue states are related evidence only. I-7A/B never transitions them.
B3_MUTABLE_QUEUE_STATES = frozenset({"queued", "claimed"})
B3_TERMINAL_QUEUE_STATES = frozenset({"succeeded", "failed", "cancelled", "dead_letter"})
B3_QUEUE_STATES = B3_MUTABLE_QUEUE_STATES | B3_TERMINAL_QUEUE_STATES

HELD_SOURCE_AUTHORITIES = frozenset({
    "primary_worker_outcome",
    "governance_flow",
    "operator_import",
})

RELATED_PRIMARY_BLOCKING_LIFECYCLES = frozenset({"hidden"})
RELATED_PRIMARY_BLOCKING_MUTATIONS = frozenset({
    "prepared", "recovery_required", "corrupt", "forget_prepared"
})

PUBLIC_EFFECTS = {
    "apply": {
        "held_item_adopted_contract": True,
        "held_item_discarded_contract": False,
        "queue_state_mutated": False,
        "primary_mem_mutated": False,
        "worker_started": False,
        "scheduler_started": False,
        "automatic_retry_or_release": False,
        "runtime_private_content_exposed": False,
    },
    "discard": {
        "held_item_adopted_contract": False,
        "held_item_discarded_contract": True,
        "queue_state_mutated": False,
        "primary_mem_mutated": False,
        "worker_started": False,
        "scheduler_started": False,
        "automatic_retry_or_release": False,
        "runtime_private_content_exposed": False,
    },
}

__all__ = [
    "ALREADY_FINAL_STATUSES",
    "APPLIED_STATUS",
    "B3_MUTABLE_QUEUE_STATES",
    "B3_QUEUE_STATES",
    "B3_TERMINAL_QUEUE_STATES",
    "BLOCKED_STATUS",
    "CORRUPT_STATUS",
    "DISCARDED_STATUS",
    "FAILED_STATUS",
    "GOVERNABLE_HELD_STATUSES",
    "HELD_APPLY_PREFLIGHT_SCHEMA",
    "HELD_CANDIDATE_STATUSES",
    "HELD_DISCARD_PREFLIGHT_SCHEMA",
    "HELD_OUTCOME_CANDIDATE_SCHEMA",
    "HELD_SOURCE_AUTHORITIES",
    "HELD_SOURCE_EVIDENCE_REF_SCHEMA",
    "HELD_STATUS",
    "NON_HELD_DISTINCTION_STATUSES",
    "PUBLIC_EFFECTS",
    "RECOVERY_REQUIRED_STATUS",
    "RELATED_PRIMARY_BLOCKING_LIFECYCLES",
    "RELATED_PRIMARY_BLOCKING_MUTATIONS",
    "TERMINAL_FAILED_STATUS",
    "TERMINAL_SUCCEEDED_STATUS",
]
