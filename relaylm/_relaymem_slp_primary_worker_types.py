"""Exact types for the Phase 6-C1-2 one-claimed Primary MEM worker."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .relaymem_primary_pipeline import RelayMEMPrimaryPipelineResult
from .relaymem_slp_primary_worker_outcome import RelayMEMSLPPrimaryWorkerOutcome
from .relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
)
from .relaymem_slp_queue_state import RelayMEMSLPQueueStateTransitionResult

REQUEST_SCHEMA = "relaymem.slp_primary_worker_request.v0"
RESULT_SCHEMA = "relaymem.slp_primary_worker_result.v0"
PROJECTION_SCHEMA = "relaymem.slp_primary_worker_projection.v0"

WorkerStatus = Literal[
    "disabled",
    "dry_run_ready",
    "invalid_input",
    "lease_invalid_before_source",
    "source_invalid",
    "pipeline_blocked",
    "pipeline_held",
    "lease_lost_before_m3e",
    "lease_lost_before_m3g",
    "lease_lost_before_transition",
    "retry_released",
    "terminal_succeeded",
    "terminal_failed",
    "transition_failed",
]
CheckpointName = Literal[
    "before_source_consumption",
    "before_m3e_page_writer",
    "before_m3g_reconciliation_apply",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPrimaryWorkerRequest:
    """Exact runtime-private request for one already-claimed B3 job."""

    schema_version: str
    runtime_private: bool
    content_included: bool
    claimed_record: dict[str, object] = field(repr=False)
    worker_source: RelayMEMSLPPrimaryWorkerSource = field(repr=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope = field(repr=False)
    queue_root: str = field(repr=False)
    store_root: str = field(repr=False)
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    lease_duration_seconds: int
    retry_not_before: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerProjection:
    """Deterministic content-free worker projection."""

    status: WorkerStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    initial_lease_valid: bool
    source_checkpoint_passed: bool
    m3e_checkpoint_passed: bool
    m3g_checkpoint_passed: bool
    final_checkpoint_passed: bool
    lease_renewed: bool
    lease_renewal_count: int
    pipeline_status: str | None
    outcome_transition_kind: str | None
    queue_transition_performed: bool
    retryable: bool
    terminal: bool
    succeeded: bool
    failed: bool
    reason_ids: tuple[str, ...]

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "source_body_included": False,
            "page_content_included": False,
            "index_content_included": False,
            "log_content_included": False,
            "queue_root_included": False,
            "store_root_included": False,
            "queue_filename_included": False,
            "namespace_included": False,
            "runtime_identifiers_included": False,
            "lineage_fingerprint_included": False,
            "dispatch_idempotency_key_included": False,
            "memory_idempotency_key_included": False,
            "claim_owner_included": False,
            "lease_token_included": False,
            "record_revision_included": False,
            "claim_generation_included": False,
            "timestamps_included": False,
            "retry_timestamp_included": False,
            "exception_text_included": False,
            "private_pipeline_result_included": False,
            "private_outcome_result_included": False,
            "private_queue_result_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "initial_lease_valid": self.initial_lease_valid,
            "source_checkpoint_passed": self.source_checkpoint_passed,
            "m3e_checkpoint_passed": self.m3e_checkpoint_passed,
            "m3g_checkpoint_passed": self.m3g_checkpoint_passed,
            "final_checkpoint_passed": self.final_checkpoint_passed,
            "lease_renewed": self.lease_renewed,
            "lease_renewal_count": self.lease_renewal_count,
            "pipeline_status": self.pipeline_status,
            "outcome_transition_kind": self.outcome_transition_kind,
            "queue_transition_performed": self.queue_transition_performed,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "reason_ids": list(self.reason_ids),
        }


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPrimaryWorkerResult:
    """Runtime-private execution ledger for one already-claimed job."""

    schema_version: str
    status: WorkerStatus
    runtime_private: bool
    content_included: bool
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    initial_claim_valid: bool
    source_checkpoint_passed: bool
    m3e_checkpoint_passed: bool
    m3g_checkpoint_passed: bool
    final_checkpoint_passed: bool
    lease_renewal_count: int
    pipeline_result: RelayMEMPrimaryPipelineResult | None = field(
        default=None, repr=False
    )
    outcome_result: RelayMEMSLPPrimaryWorkerOutcome | None = field(
        default=None, repr=False
    )
    queue_transition_result: RelayMEMSLPQueueStateTransitionResult | None = field(
        default=None, repr=False
    )
    side_effect_started: bool = False
    queue_transition_performed: bool = False
    reason_ids: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        from .relaymem_slp_primary_worker import project_relaymem_slp_primary_worker

        return project_relaymem_slp_primary_worker(self).to_log_dict()


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "CheckpointName",
    "WorkerStatus",
    "RelayMEMSLPPrimaryWorkerProjection",
    "RelayMEMSLPPrimaryWorkerRequest",
    "RelayMEMSLPPrimaryWorkerResult",
]
