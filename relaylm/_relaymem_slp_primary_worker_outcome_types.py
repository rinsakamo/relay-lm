"""Exact frozen types for the Phase 6-C1 Primary MEM outcome classifier."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OUTCOME_SCHEMA = "relaymem.slp_primary_worker_outcome.v0"
PROJECTION_SCHEMA = "relaymem.slp_primary_worker_outcome_projection.v0"
M3E_SCHEMA = "relaymem.primary_page_write_apply.v0"
M3G_SCHEMA = "relaymem.primary_index_log_reconciliation_apply.v0"
M3H_SCHEMA = "relaymem.primary_index_log_reconciliation_recovery_audit_result.v0"
POLICY_SCHEMA = "relaymem.slp_primary_worker_policy_outcome.v0"
SOURCE_CORRELATION_SCHEMA = "relaymem.slp_primary_worker_source_correlation.v0"

TransitionKind = Literal[
    "commit_succeeded", "retry_release", "commit_failed", "blocked_invalid_input"
]
OutcomeStatus = Literal["classified", "invalid_input"]
TerminalState = Literal["", "succeeded", "failed"]
RetryClass = Literal["none", "transient_lock_contention", "primary_reconciliation_retry"]
FailureClass = Literal[
    "none",
    "resource_contention",
    "partial_progress_verified",
    "memory_policy_held",
    "memory_policy_blocked",
    "manual_confirmation_required",
    "recovery_isolation_required",
    "store_conflict",
    "store_corruption",
    "source_correlation_invalid",
    "invalid_input",
]


@dataclass(frozen=True)
class RelayMEMSLPPrimaryPageWriteOutcome:
    """Exact classification snapshot of one RelayMEM M3e result."""

    schema_version: str
    status: str
    handoff_valid: bool
    writes_memory: bool
    page_applied: bool
    idempotent_noop: bool
    durability_confirmed: bool
    cleanup_complete: bool
    blocked_reason_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelayMEMSLPPrimaryReconciliationOutcome:
    """Exact classification snapshot of one RelayMEM M3g result."""

    schema_version: str
    status: str
    plan_valid: bool
    page_verified: bool
    writes_memory: bool
    index_reconciled: bool
    log_reconciled: bool
    index_updated: bool
    log_updated: bool
    index_idempotent_noop: bool
    log_idempotent_noop: bool
    durability_confirmed: bool
    cleanup_complete: bool
    blocked_reason_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelayMEMSLPPrimaryRecoveryAuditOutcome:
    """Exact classification snapshot of one RelayMEM M3h result."""

    schema_version: str
    status: str
    receipt_valid: bool
    source_status: str
    store_state: str
    page_verified: bool
    index_state: str
    log_state: str
    cleanup_artifacts_present: bool
    recovery_classification: str
    blocked_reason_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelayMEMSLPPrimaryPolicyOutcome:
    """RelayMEM-owned policy result, without redefining its meaning."""

    schema_version: str
    status: Literal["held", "blocked"]
    reason_id: str


@dataclass(frozen=True)
class RelayMEMSLPPrimarySourceCorrelationOutcome:
    """Classification-only result owned by the separate source boundary."""

    schema_version: str
    status: Literal["verified", "invalid"]


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerOutcomeProjection:
    """Strict content-free public projection."""

    status: OutcomeStatus
    transition_kind: TransitionKind
    terminal_state: TerminalState
    retry_class: RetryClass
    failure_class: FailureClass
    terminal_reason_id: str
    retryable: bool
    terminal: bool
    policy_held: bool
    manual_confirmation_required: bool
    recovery_isolation_required: bool
    durable_success_verified: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "status": self.status,
            "transition_kind": self.transition_kind,
            "terminal_state": self.terminal_state,
            "retry_class": self.retry_class,
            "failure_class": self.failure_class,
            "terminal_reason_id": self.terminal_reason_id,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "policy_held": self.policy_held,
            "manual_confirmation_required": self.manual_confirmation_required,
            "recovery_isolation_required": self.recovery_isolation_required,
            "durable_success_verified": self.durable_success_verified,
        }


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerOutcome:
    """Pure runtime-private B3 transition intent with public projection."""

    status: OutcomeStatus
    transition_kind: TransitionKind
    terminal_state: TerminalState
    retry_class: RetryClass
    failure_class: FailureClass
    terminal_reason_id: str
    retryable: bool
    terminal: bool
    policy_held: bool
    manual_confirmation_required: bool
    recovery_isolation_required: bool
    durable_success_verified: bool
    blocked_reason_ids: tuple[str, ...] = ()

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": OUTCOME_SCHEMA,
            "status": self.status,
            "transition_kind": self.transition_kind,
            "terminal_state": self.terminal_state,
            "retry_class": self.retry_class,
            "failure_class": self.failure_class,
            "terminal_reason_id": self.terminal_reason_id,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "policy_held": self.policy_held,
            "manual_confirmation_required": self.manual_confirmation_required,
            "recovery_isolation_required": self.recovery_isolation_required,
            "durable_success_verified": self.durable_success_verified,
            "blocked_reason_ids": list(self.blocked_reason_ids),
        }

    def to_log_dict(self) -> dict[str, object]:
        return RelayMEMSLPPrimaryWorkerOutcomeProjection(
            status=self.status,
            transition_kind=self.transition_kind,
            terminal_state=self.terminal_state,
            retry_class=self.retry_class,
            failure_class=self.failure_class,
            terminal_reason_id=self.terminal_reason_id,
            retryable=self.retryable,
            terminal=self.terminal,
            policy_held=self.policy_held,
            manual_confirmation_required=self.manual_confirmation_required,
            recovery_isolation_required=self.recovery_isolation_required,
            durable_success_verified=self.durable_success_verified,
        ).to_log_dict()
