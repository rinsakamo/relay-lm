"""RelayMEM-owned Phase 6-C1-1 Primary MEM M3a-M3h composition boundary.

The compose helper consumes one exact C1-0 protected worker source, fixes the
canonical M3 stage order, and returns a runtime-private ledger plus a
content-free projection. Queue control, lease fencing, retry policy, and B3
transitions remain outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .reason_ids import normalize_reason_ids
from .relaymem_primary_formation import build_relaymem_primary_formation_dry_run
from .relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from .relaymem_primary_index_log_reconciliation import (
    build_relaymem_primary_index_log_reconciliation_preflight,
)
from .relaymem_primary_index_log_recovery_audit import (
    audit_relaymem_primary_index_log_reconciliation_recovery,
)
from .relaymem_primary_page_candidate import (
    build_relaymem_primary_page_candidate_dry_run,
)
from .relaymem_primary_page_writer import apply_relaymem_primary_page_write
from .relaymem_primary_write_preflight import (
    build_relaymem_primary_write_preflight_dry_run,
)
from .relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)
from .relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
    consume_relaymem_slp_primary_worker_source,
)

REQUEST_SCHEMA = "relaymem.primary_pipeline_request.v0"
RESULT_SCHEMA = "relaymem.primary_pipeline_result.v0"
PROJECTION_SCHEMA = "relaymem.primary_pipeline_projection.v0"
LINEAGE_SCHEMA = "relaymem.primary_source_lineage.v0"

StageName = Literal[
    "m3a_formation",
    "m3b_write_preflight",
    "m3c_page_candidate",
    "m3d_writer_handoff",
    "m3e_page_writer",
    "m3f_reconciliation_preflight",
    "m3g_reconciliation_apply",
    "m3h_recovery_audit",
]
StageStatus = Literal[
    "not_run",
    "completed",
    "blocked",
    "held",
    "retryable",
    "skipped_dry_run",
]
PipelineStatus = Literal[
    "disabled",
    "invalid_input",
    "blocked",
    "held",
    "dry_run_ready",
    "recovery_not_required",
    "retry_reconciliation",
    "manual_confirmation_required",
    "journaled_recovery_candidate",
]
RecoveryClassification = Literal[
    "not_evaluated",
    "recovery_not_required",
    "retry_reconciliation",
    "manual_confirmation_required",
    "journaled_recovery_candidate",
]

STAGES: tuple[StageName, ...] = (
    "m3a_formation",
    "m3b_write_preflight",
    "m3c_page_candidate",
    "m3d_writer_handoff",
    "m3e_page_writer",
    "m3f_reconciliation_preflight",
    "m3g_reconciliation_apply",
    "m3h_recovery_audit",
)
_M3G_LOCK_REASON = "primary_reconciliation_apply_lock_unavailable"
_M3H_LOCK_REASONS = frozenset(
    {
        "primary_reconciliation_recovery_lock_unavailable",
        "primary_reconciliation_recovery_audit_lock_unavailable",
    }
)

_M3A_FIELDS = frozenset(
    {
        "schema_version", "diagnostics_only", "helper_only", "read_only",
        "enabled", "dry_run_only", "apply_enabled", "apply_allowed",
        "writes_memory", "mutates_soul", "invokes_slp", "lab_api_exposed",
        "source_event_kind", "scene_type", "source_summary", "candidate_count",
        "candidates", "blocked_reasons", "projection",
    }
)
_M3B_FIELDS = frozenset(
    {
        "schema_version", "diagnostics_only", "helper_only", "read_only",
        "enabled", "dry_run_only", "apply_enabled", "write_apply_supported",
        "apply_allowed", "writes_memory", "mutates_soul", "invokes_slp",
        "lab_api_exposed", "source_lineage_valid", "candidate_count",
        "candidate_limit", "candidate_limit_exceeded", "operation_count",
        "operations", "blocked_reasons", "projection",
    }
)
_M3C_FIELDS = frozenset(
    {
        "schema_version", "diagnostics_only", "helper_only", "read_only",
        "runtime_private_candidates", "enabled", "dry_run_only",
        "apply_enabled", "write_apply_supported", "apply_allowed",
        "writes_memory", "mutates_soul", "invokes_slp", "lab_api_exposed",
        "page_candidate_count", "page_candidates", "blocked_reasons", "projection",
    }
)
_M3D_FIELDS = frozenset(
    {
        "schema_version", "diagnostics_only", "helper_only", "read_only",
        "runtime_private_handoffs", "enabled", "dry_run_only", "apply_enabled",
        "write_apply_supported", "apply_allowed", "writes_memory", "updates_index",
        "updates_log", "mutates_soul", "invokes_slp", "lab_api_exposed",
        "runtime_wired", "visible_response_changed", "store_root_configured",
        "page_candidate_valid", "handoff_count", "handoffs", "blocked_reasons",
        "projection",
    }
)
_M3E_FIELDS = frozenset(
    {
        "schema_version", "helper_only", "runtime_private_receipt", "enabled",
        "dry_run_only", "apply_enabled", "write_apply_supported", "apply_requested",
        "handoff_valid", "status", "writes_memory", "page_applied",
        "idempotent_noop", "durability_confirmed", "cleanup_complete",
        "updates_index", "updates_log", "mutates_soul", "invokes_slp",
        "lab_api_exposed", "runtime_wired", "visible_response_changed", "receipt",
        "blocked_reasons", "projection",
    }
)
_M3F_FIELDS = frozenset(
    {
        "schema_version", "diagnostics_only", "helper_only", "read_only",
        "runtime_private_plan", "enabled", "dry_run_only", "receipt_valid",
        "page_verified", "status", "preflight_status", "index_update_required",
        "log_update_required", "writes_memory", "updates_index", "updates_log",
        "mutates_soul", "invokes_slp", "runtime_wired", "visible_response_changed",
        "plan", "blocked_reasons", "projection",
    }
)
_M3G_FIELDS = frozenset(
    {
        "schema_version", "helper_only", "runtime_private_receipt", "enabled",
        "dry_run_only", "apply_enabled", "apply_supported", "apply_requested",
        "plan_valid", "page_verified", "status", "writes_memory",
        "index_reconciled", "log_reconciled", "index_updated", "log_updated",
        "index_idempotent_noop", "log_idempotent_noop", "durability_confirmed",
        "cleanup_complete", "updates_index", "updates_log", "mutates_soul",
        "invokes_slp", "runtime_wired", "lab_api_exposed",
        "visible_response_changed", "receipt", "blocked_reasons", "projection",
    }
)
_M3H_FIELDS = frozenset(
    {
        "schema_version", "helper_only", "runtime_private_audit", "enabled",
        "dry_run_only", "read_only", "audit_supported", "receipt_valid", "status",
        "source_status", "store_state", "recovery_classification", "writes_memory",
        "updates_index", "updates_log", "creates_journal", "mutates_soul",
        "invokes_slp", "runtime_wired", "lab_api_exposed",
        "visible_response_changed", "audit", "blocked_reasons", "projection",
    }
)


@dataclass(frozen=True, repr=False)
class RelayMEMPrimaryPipelineRequest:
    """Exact runtime-private request for one RelayMEM compose invocation."""

    schema_version: str
    runtime_private: bool
    content_included: bool
    worker_source: RelayMEMSLPPrimaryWorkerSource = field(repr=False)
    claimed_record: dict[str, object] = field(repr=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope = field(repr=False)
    store_root: str = field(repr=False)
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool


@dataclass(frozen=True, repr=False)
class RelayMEMPrimaryPipelineStageResult:
    stage: StageName
    status: StageStatus
    executed: bool
    completed: bool
    blocked: bool
    held: bool
    retryable: bool
    terminal: bool
    reason_ids: tuple[str, ...]
    private_result: dict[str, Any] | None = field(default=None, repr=False)


@dataclass(frozen=True)
class RelayMEMPrimaryPipelineProjection:
    status: PipelineStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    current_stage: StageName | None
    last_completed_stage: StageName | None
    completed_stage_count: int
    blocked: bool
    held: bool
    retryable: bool
    page_candidate_ready: bool
    page_applied: bool
    page_exact_existing: bool
    reconciliation_planned: bool
    index_applied: bool
    log_applied: bool
    recovery_audit_completed: bool
    recovery_classification: RecoveryClassification
    reason_ids: tuple[str, ...]

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_messages_included": False,
            "governed_experience_included": False,
            "page_content_included": False,
            "index_content_included": False,
            "log_content_included": False,
            "store_root_path_included": False,
            "target_paths_included": False,
            "namespace_included": False,
            "runtime_identifiers_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "hash_values_included": False,
            "exception_text_included": False,
            "private_results_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "current_stage": self.current_stage,
            "last_completed_stage": self.last_completed_stage,
            "completed_stage_count": self.completed_stage_count,
            "blocked": self.blocked,
            "held": self.held,
            "retryable": self.retryable,
            "page_candidate_ready": self.page_candidate_ready,
            "page_applied": self.page_applied,
            "page_exact_existing": self.page_exact_existing,
            "reconciliation_planned": self.reconciliation_planned,
            "index_applied": self.index_applied,
            "log_applied": self.log_applied,
            "recovery_audit_completed": self.recovery_audit_completed,
            "recovery_classification": self.recovery_classification,
            "reason_ids": list(self.reason_ids),
            "queue_io_performed": False,
            "queue_transition_performed": False,
            "lease_operation_performed": False,
            "retry_sleep_performed": False,
            "mutates_soul": False,
            "secondary_mem_processed": False,
        }


@dataclass(frozen=True, repr=False)
class RelayMEMPrimaryPipelineResult:
    schema_version: str
    status: PipelineStatus
    runtime_private: bool
    content_included: bool
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    completed_stage_count: int
    last_stage: StageName | None
    last_completed_stage: StageName | None
    stage_results: tuple[RelayMEMPrimaryPipelineStageResult, ...] = field(repr=False)
    m3a_result: dict[str, Any] | None = field(default=None, repr=False)
    m3b_result: dict[str, Any] | None = field(default=None, repr=False)
    m3c_result: dict[str, Any] | None = field(default=None, repr=False)
    m3d_result: dict[str, Any] | None = field(default=None, repr=False)
    m3e_result: dict[str, Any] | None = field(default=None, repr=False)
    m3f_result: dict[str, Any] | None = field(default=None, repr=False)
    m3g_result: dict[str, Any] | None = field(default=None, repr=False)
    m3h_result: dict[str, Any] | None = field(default=None, repr=False)
    reason_ids: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_primary_pipeline(self).to_log_dict()


class _Ledger:
    def __init__(self) -> None:
        self._items: dict[StageName, RelayMEMPrimaryPipelineStageResult] = {
            stage: _stage(stage) for stage in STAGES
        }

    def record(
        self,
        stage: StageName,
        *,
        status: StageStatus,
        completed: bool,
        blocked: bool = False,
        held: bool = False,
        retryable: bool = False,
        terminal: bool = False,
        reasons: tuple[str, ...] = (),
        result: dict[str, Any] | None = None,
    ) -> None:
        self._items[stage] = _stage(
            stage,
            status=status,
            executed=status != "not_run" and status != "skipped_dry_run",
            completed=completed,
            blocked=blocked,
            held=held,
            retryable=retryable,
            terminal=terminal,
            reasons=reasons,
            result=result,
        )

    def skip_dry_run(self, stage: StageName) -> None:
        self._items[stage] = _stage(stage, status="skipped_dry_run")

    def tuple(self) -> tuple[RelayMEMPrimaryPipelineStageResult, ...]:
        return tuple(self._items[stage] for stage in STAGES)


class _Artifacts:
    def __init__(self) -> None:
        self.values: dict[StageName, dict[str, Any] | None] = {
            stage: None for stage in STAGES
        }

    def set(self, stage: StageName, value: dict[str, Any]) -> None:
        self.values[stage] = value


def execute_relaymem_primary_pipeline(request: object) -> RelayMEMPrimaryPipelineResult:
    """Execute the exact protected source through the canonical RelayMEM stages."""

    ledger = _Ledger()
    artifacts = _Artifacts()
    request_value, request_reasons = _validate_request(request)
    if request_value is None:
        return _finish(
            status="invalid_input",
            enabled=False,
            dry_run_only=True,
            apply_enabled=False,
            ledger=ledger,
            artifacts=artifacts,
            reasons=request_reasons,
        )
    if not request_value.enabled:
        return _finish(
            status="disabled",
            enabled=False,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
            ledger=ledger,
            artifacts=artifacts,
            reasons=(),
        )

    source, source_reasons = consume_relaymem_slp_primary_worker_source(
        request_value.worker_source,
        claimed_record=request_value.claimed_record,
        request_scope=request_value.request_scope,
    )
    if source is None:
        return _finish(
            status="invalid_input",
            enabled=True,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
            ledger=ledger,
            artifacts=artifacts,
            reasons=_reasons(source_reasons or ("worker_source_invalid",)),
        )
    protected = source.to_protected_runtime_dict()

    try:
        m3a = build_relaymem_primary_formation_dry_run(
            relayscn_scene_policy_artifact=protected["relayscn_scene_policy_artifact"],
            relayemo_artifact=protected["relayemo_artifact"],
            messages=protected["governed_messages"],
            enabled=True,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
            source_event_kind=source.source_event_kind,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3a_formation", "m3a_execution_failed")
    m3a_errors = _validate_result(m3a, "relaymem.primary_formation_dry_run.v0", _M3A_FIELDS)
    if m3a_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3a_formation", m3a, m3a_errors)
    artifacts.set("m3a_formation", m3a)
    candidates = m3a.get("candidates")
    candidate_count = m3a.get("candidate_count")
    if type(candidate_count) is not int or type(candidates) is not list or candidate_count != len(candidates):
        return _stage_invalid(request_value, ledger, artifacts, "m3a_formation", m3a, ("m3a_candidate_shape_invalid",))
    if candidate_count != 1 or type(candidates[0]) is not dict:
        reasons = _artifact_reasons(m3a) or ("m3a_candidate_not_formed",)
        ledger.record("m3a_formation", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3a)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    candidate = candidates[0]
    promotion = candidate.get("promotion_policy")
    safety_scope = candidate.get("safety_scope")
    if promotion == "review_required" or safety_scope == "held_for_review":
        reasons = ("primary_memory_candidate_held_for_review",)
        ledger.record("m3a_formation", status="held", completed=False, held=True, terminal=True, reasons=reasons, result=m3a)
        return _finish_from_request("held", request_value, ledger, artifacts, reasons)
    if promotion != "free_to_update" or safety_scope != "ordinary_memory":
        reasons = _artifact_reasons(m3a) or ("m3a_candidate_policy_blocked",)
        ledger.record("m3a_formation", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3a)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3a_formation", status="completed", completed=True, result=m3a)

    lineage = _source_lineage(source)

    try:
        m3b = build_relaymem_primary_write_preflight_dry_run(
            candidates=m3a["candidates"],
            source_lineage_artifact=lineage,
            enabled=True,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3b_write_preflight", "m3b_execution_failed")
    m3b_errors = _validate_result(m3b, "relaymem.primary_write_preflight_dry_run.v0", _M3B_FIELDS)
    if m3b_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3b_write_preflight", m3b, m3b_errors)
    artifacts.set("m3b_write_preflight", m3b)
    operations = m3b.get("operations")
    operation_count = m3b.get("operation_count")
    if type(operation_count) is not int or type(operations) is not list or operation_count != len(operations) or operation_count != 1 or type(operations[0]) is not dict:
        reasons = _artifact_reasons(m3b) or ("m3b_operation_shape_invalid",)
        ledger.record("m3b_write_preflight", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3b)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    preflight_status = operations[0].get("preflight_status")
    if preflight_status == "held":
        reasons = _artifact_reasons(m3b) or ("primary_memory_write_held",)
        ledger.record("m3b_write_preflight", status="held", completed=False, held=True, terminal=True, reasons=reasons, result=m3b)
        return _finish_from_request("held", request_value, ledger, artifacts, reasons)
    if preflight_status != "eligible":
        reasons = _artifact_reasons(m3b) or ("primary_memory_write_preflight_blocked",)
        ledger.record("m3b_write_preflight", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3b)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3b_write_preflight", status="completed", completed=True, result=m3b)

    try:
        m3c = build_relaymem_primary_page_candidate_dry_run(
            preflight_artifact=m3b,
            source_lineage_artifact=lineage,
            governed_experience_artifact=protected["governed_experience_artifact"],
            enabled=True,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3c_page_candidate", "m3c_execution_failed")
    m3c_errors = _validate_result(m3c, "relaymem.primary_page_candidate_dry_run.v0", _M3C_FIELDS)
    if m3c_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3c_page_candidate", m3c, m3c_errors)
    artifacts.set("m3c_page_candidate", m3c)
    pages = m3c.get("page_candidates")
    page_count = m3c.get("page_candidate_count")
    if type(page_count) is not int or type(pages) is not list or page_count != len(pages) or page_count != 1 or type(pages[0]) is not dict:
        reasons = _artifact_reasons(m3c) or ("m3c_page_candidate_invalid",)
        ledger.record("m3c_page_candidate", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3c)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3c_page_candidate", status="completed", completed=True, result=m3c)

    try:
        m3d = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=m3c,
            root_path=request_value.store_root,
            enabled=True,
            dry_run_only=request_value.dry_run_only,
            apply_enabled=request_value.apply_enabled,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3d_writer_handoff", "m3d_execution_failed")
    m3d_errors = _validate_result(m3d, "relaymem.primary_writer_handoff_preflight.v0", _M3D_FIELDS)
    if m3d_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3d_writer_handoff", m3d, m3d_errors)
    artifacts.set("m3d_writer_handoff", m3d)
    handoffs = m3d.get("handoffs")
    handoff_count = m3d.get("handoff_count")
    if type(handoff_count) is not int or type(handoffs) is not list or handoff_count != len(handoffs) or handoff_count != 1 or type(handoffs[0]) is not dict:
        reasons = _artifact_reasons(m3d) or ("m3d_writer_handoff_invalid",)
        ledger.record("m3d_writer_handoff", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3d)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    handoff_status = handoffs[0].get("preflight_status")
    if handoff_status not in {"ready", "already_applied"}:
        reasons = _artifact_reasons(m3d) or ("m3d_writer_handoff_not_ready",)
        ledger.record("m3d_writer_handoff", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3d)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3d_writer_handoff", status="completed", completed=True, result=m3d)

    if request_value.dry_run_only:
        ledger.skip_dry_run("m3e_page_writer")
        ledger.skip_dry_run("m3g_reconciliation_apply")
        return _finish_from_request("dry_run_ready", request_value, ledger, artifacts, ())

    try:
        m3e = apply_relaymem_primary_page_write(
            writer_handoff_artifact=m3d,
            root_path=request_value.store_root,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3e_page_writer", "m3e_execution_failed")
    m3e_errors = _validate_result(m3e, "relaymem.primary_page_write_apply.v0", _M3E_FIELDS)
    if m3e_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3e_page_writer", m3e, m3e_errors)
    artifacts.set("m3e_page_writer", m3e)
    m3e_status = m3e.get("status")
    m3e_receipt = m3e.get("receipt")
    if m3e_status not in {"applied", "already_applied"}:
        reasons = _artifact_reasons(m3e) or ("m3e_page_write_not_exact",)
        ledger.record("m3e_page_writer", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3e)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    if type(m3e_receipt) is not dict:
        return _stage_invalid(request_value, ledger, artifacts, "m3e_page_writer", m3e, ("m3e_receipt_missing",))
    ledger.record("m3e_page_writer", status="completed", completed=True, result=m3e)

    try:
        m3f = build_relaymem_primary_index_log_reconciliation_preflight(
            receipt=m3e_receipt,
            root_path=request_value.store_root,
            enabled=True,
            dry_run_only=True,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3f_reconciliation_preflight", "m3f_execution_failed")
    m3f_errors = _validate_result(m3f, "relaymem.primary_index_log_reconciliation_preflight.v0", _M3F_FIELDS)
    if m3f_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3f_reconciliation_preflight", m3f, m3f_errors)
    artifacts.set("m3f_reconciliation_preflight", m3f)
    plan = m3f.get("plan")
    if m3f.get("preflight_status") != "ready" or type(plan) is not dict:
        reasons = _artifact_reasons(m3f) or ("m3f_reconciliation_plan_unavailable",)
        ledger.record("m3f_reconciliation_preflight", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3f)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3f_reconciliation_preflight", status="completed", completed=True, result=m3f)

    try:
        m3g = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=request_value.store_root,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3g_reconciliation_apply", "m3g_execution_failed")
    m3g_errors = _validate_result(m3g, "relaymem.primary_index_log_reconciliation_apply.v0", _M3G_FIELDS)
    if m3g_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3g_reconciliation_apply", m3g, m3g_errors)
    artifacts.set("m3g_reconciliation_apply", m3g)
    m3g_reasons = _artifact_reasons(m3g)
    if _M3G_LOCK_REASON in m3g_reasons:
        ledger.record("m3g_reconciliation_apply", status="retryable", completed=False, blocked=True, retryable=True, terminal=False, reasons=m3g_reasons, result=m3g)
        return _finish_from_request("blocked", request_value, ledger, artifacts, m3g_reasons)
    m3g_receipt = m3g.get("receipt")
    if type(m3g_receipt) is not dict:
        reasons = m3g_reasons or ("m3g_reconciliation_receipt_missing",)
        ledger.record("m3g_reconciliation_apply", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3g)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    ledger.record("m3g_reconciliation_apply", status="completed", completed=True, result=m3g)

    try:
        m3h = audit_relaymem_primary_index_log_reconciliation_recovery(
            receipt=m3g_receipt,
            root_path=request_value.store_root,
            enabled=True,
            dry_run_only=True,
        )
    except Exception:
        return _stage_failure(request_value, ledger, artifacts, "m3h_recovery_audit", "m3h_execution_failed")
    m3h_errors = _validate_result(m3h, "relaymem.primary_index_log_reconciliation_recovery_audit_result.v0", _M3H_FIELDS)
    if m3h_errors:
        return _stage_invalid(request_value, ledger, artifacts, "m3h_recovery_audit", m3h, m3h_errors)
    artifacts.set("m3h_recovery_audit", m3h)
    classification = m3h.get("recovery_classification")
    reasons = _artifact_reasons(m3h)
    if reasons and any(reason in _M3H_LOCK_REASONS or "lock_unavailable" in reason for reason in reasons):
        ledger.record("m3h_recovery_audit", status="retryable", completed=False, blocked=True, retryable=True, reasons=reasons, result=m3h)
        return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)
    if classification == "recovery_not_required" and m3h.get("status") == "recovery_not_required":
        ledger.record("m3h_recovery_audit", status="completed", completed=True, result=m3h)
        return _finish_from_request("recovery_not_required", request_value, ledger, artifacts, ())
    if classification == "retry_reconciliation":
        ledger.record("m3h_recovery_audit", status="retryable", completed=True, retryable=True, reasons=reasons, result=m3h)
        return _finish_from_request("retry_reconciliation", request_value, ledger, artifacts, reasons)
    if classification == "manual_confirmation_required":
        ledger.record("m3h_recovery_audit", status="blocked", completed=True, blocked=True, terminal=True, reasons=reasons, result=m3h)
        return _finish_from_request("manual_confirmation_required", request_value, ledger, artifacts, reasons)
    if classification == "journaled_recovery_candidate":
        ledger.record("m3h_recovery_audit", status="blocked", completed=True, blocked=True, terminal=True, reasons=reasons, result=m3h)
        return _finish_from_request("journaled_recovery_candidate", request_value, ledger, artifacts, reasons)
    reasons = reasons or ("m3h_recovery_classification_invalid",)
    ledger.record("m3h_recovery_audit", status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=m3h)
    return _finish_from_request("blocked", request_value, ledger, artifacts, reasons)


def project_relaymem_primary_pipeline(
    result: RelayMEMPrimaryPipelineResult,
) -> RelayMEMPrimaryPipelineProjection:
    if type(result) is not RelayMEMPrimaryPipelineResult:
        raise TypeError("exact RelayMEMPrimaryPipelineResult required")
    items = result.stage_results
    current = next((item.stage for item in reversed(items) if item.executed), None)
    m3c = result.m3c_result or {}
    m3e = result.m3e_result or {}
    m3f = result.m3f_result or {}
    m3g = result.m3g_result or {}
    m3h = result.m3h_result or {}
    classification = m3h.get("recovery_classification", "not_evaluated")
    if classification not in {
        "not_evaluated", "recovery_not_required", "retry_reconciliation",
        "manual_confirmation_required", "journaled_recovery_candidate",
    }:
        classification = "not_evaluated"
    return RelayMEMPrimaryPipelineProjection(
        status=result.status,
        enabled=result.enabled,
        dry_run_only=result.dry_run_only,
        apply_enabled=result.apply_enabled,
        current_stage=current,
        last_completed_stage=result.last_completed_stage,
        completed_stage_count=result.completed_stage_count,
        blocked=any(item.blocked for item in items),
        held=any(item.held for item in items),
        retryable=any(item.retryable for item in items),
        page_candidate_ready=(m3c.get("page_candidate_count") == 1),
        page_applied=(m3e.get("status") == "applied" and m3e.get("page_applied") is True),
        page_exact_existing=(m3e.get("status") == "already_applied" and m3e.get("idempotent_noop") is True),
        reconciliation_planned=(type(m3f.get("plan")) is dict),
        index_applied=(m3g.get("index_reconciled") is True),
        log_applied=(m3g.get("log_reconciled") is True),
        recovery_audit_completed=(result.m3h_result is not None),
        recovery_classification=classification,
        reason_ids=result.reason_ids,
    )


def build_relaymem_primary_pipeline_node_result(
    result: RelayMEMPrimaryPipelineResult,
) -> PipelineNodeResult:
    projection = project_relaymem_primary_pipeline(result)
    node_status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
        "held": "blocked",
        "dry_run_ready": "diagnostic_only",
        "recovery_not_required": "applied",
        "retry_reconciliation": "blocked",
        "manual_confirmation_required": "blocked",
        "journaled_recovery_candidate": "blocked",
    }[result.status]
    return build_pipeline_node_result(
        node_name="relaymem_primary_pipeline",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.reason_ids,
        diagnostics=projection.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relaymem_primary_pipeline_result",
                "schema_version": RESULT_SCHEMA,
                "present": True,
                "content_free": True,
                "runtime_private": True,
                "private_result_omitted": True,
                "queue_io_performed": False,
                "queue_transition_performed": False,
                "mutates_soul": False,
                "secondary_mem_processed": False,
            }
        ],
    )


def _validate_request(
    value: object,
) -> tuple[RelayMEMPrimaryPipelineRequest | None, tuple[str, ...]]:
    if type(value) is not RelayMEMPrimaryPipelineRequest:
        return None, ("exact_primary_pipeline_request_required",)
    reasons: list[str] = []
    if value.schema_version != REQUEST_SCHEMA:
        reasons.append("primary_pipeline_request_schema_mismatch")
    if value.runtime_private is not True:
        reasons.append("primary_pipeline_request_runtime_private_required")
    if value.content_included is not True:
        reasons.append("primary_pipeline_request_content_required")
    for field_name in ("enabled", "dry_run_only", "apply_enabled"):
        if type(getattr(value, field_name)) is not bool:
            reasons.append(f"primary_pipeline_request_{field_name}_invalid")
    if type(value.worker_source) is not RelayMEMSLPPrimaryWorkerSource:
        reasons.append("exact_worker_source_required")
    if type(value.request_scope) is not RelayMEMSLPPrimaryWorkerSourceScope:
        reasons.append("exact_request_scope_required")
    if type(value.claimed_record) is not dict:
        reasons.append("exact_claimed_record_required")
    if type(value.store_root) is not str:
        reasons.append("primary_pipeline_store_root_invalid")
    if type(value.enabled) is bool and value.enabled:
        if value.dry_run_only:
            if value.apply_enabled:
                reasons.append("primary_pipeline_dry_run_apply_gate_invalid")
        elif not value.apply_enabled:
            reasons.append("primary_pipeline_apply_gate_incomplete")
    return (value, ()) if not reasons else (None, _reasons(reasons))


def _source_lineage(source: RelayMEMSLPPrimaryWorkerSource) -> dict[str, Any]:
    return {
        "schema_version": LINEAGE_SCHEMA,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": source.source_event_kind,
        "namespace": source.namespace,
        "valid": True,
        "lineage_fingerprint": source.source_lineage_fingerprint,
        "lineage_shape": {
            "source_event_id_present": False,
            "run_id_present": True,
            "session_id_present": source.session_id is not None,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }


def _validate_result(
    value: object, schema: str, fields: frozenset[str]
) -> tuple[str, ...]:
    reasons: list[str] = []
    if type(value) is not dict:
        return ("stage_result_exact_dict_required",)
    if set(value) != fields:
        reasons.append("stage_result_fields_mismatch")
    if value.get("schema_version") != schema:
        reasons.append("stage_result_schema_mismatch")
    blocked = value.get("blocked_reasons")
    if type(blocked) is not list or any(type(item) is not str for item in blocked):
        reasons.append("stage_result_reason_ids_invalid")
    return _reasons(reasons)


def _artifact_reasons(value: Mapping[str, Any]) -> tuple[str, ...]:
    blocked = value.get("blocked_reasons")
    if type(blocked) is not list:
        return ()
    return _reasons(item for item in blocked if type(item) is str)


def _reasons(values: Any) -> tuple[str, ...]:
    return normalize_reason_ids(values, invalid="marker", output="tuple")


def _stage(
    stage: StageName,
    *,
    status: StageStatus = "not_run",
    executed: bool = False,
    completed: bool = False,
    blocked: bool = False,
    held: bool = False,
    retryable: bool = False,
    terminal: bool = False,
    reasons: tuple[str, ...] = (),
    result: dict[str, Any] | None = None,
) -> RelayMEMPrimaryPipelineStageResult:
    return RelayMEMPrimaryPipelineStageResult(
        stage=stage,
        status=status,
        executed=executed,
        completed=completed,
        blocked=blocked,
        held=held,
        retryable=retryable,
        terminal=terminal,
        reason_ids=_reasons(reasons),
        private_result=result,
    )


def _stage_failure(
    request: RelayMEMPrimaryPipelineRequest,
    ledger: _Ledger,
    artifacts: _Artifacts,
    stage: StageName,
    reason: str,
) -> RelayMEMPrimaryPipelineResult:
    reasons = (reason,)
    ledger.record(stage, status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons)
    return _finish_from_request("blocked", request, ledger, artifacts, reasons)


def _stage_invalid(
    request: RelayMEMPrimaryPipelineRequest,
    ledger: _Ledger,
    artifacts: _Artifacts,
    stage: StageName,
    result: object,
    reasons: tuple[str, ...],
) -> RelayMEMPrimaryPipelineResult:
    exact = result if type(result) is dict else None
    if exact is not None:
        artifacts.set(stage, exact)
    ledger.record(stage, status="blocked", completed=False, blocked=True, terminal=True, reasons=reasons, result=exact)
    return _finish_from_request("blocked", request, ledger, artifacts, reasons)


def _finish_from_request(
    status: PipelineStatus,
    request: RelayMEMPrimaryPipelineRequest,
    ledger: _Ledger,
    artifacts: _Artifacts,
    reasons: tuple[str, ...],
) -> RelayMEMPrimaryPipelineResult:
    return _finish(
        status=status,
        enabled=request.enabled,
        dry_run_only=request.dry_run_only,
        apply_enabled=request.apply_enabled,
        ledger=ledger,
        artifacts=artifacts,
        reasons=reasons,
    )


def _finish(
    *,
    status: PipelineStatus,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    ledger: _Ledger,
    artifacts: _Artifacts,
    reasons: tuple[str, ...],
) -> RelayMEMPrimaryPipelineResult:
    items = ledger.tuple()
    completed = tuple(item.stage for item in items if item.completed)
    executed = tuple(item.stage for item in items if item.executed)
    values = artifacts.values
    return RelayMEMPrimaryPipelineResult(
        schema_version=RESULT_SCHEMA,
        status=status,
        runtime_private=True,
        content_included=True,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        completed_stage_count=len(completed),
        last_stage=executed[-1] if executed else None,
        last_completed_stage=completed[-1] if completed else None,
        stage_results=items,
        m3a_result=values["m3a_formation"],
        m3b_result=values["m3b_write_preflight"],
        m3c_result=values["m3c_page_candidate"],
        m3d_result=values["m3d_writer_handoff"],
        m3e_result=values["m3e_page_writer"],
        m3f_result=values["m3f_reconciliation_preflight"],
        m3g_result=values["m3g_reconciliation_apply"],
        m3h_result=values["m3h_recovery_audit"],
        reason_ids=_reasons(reasons),
    )


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "STAGES",
    "RelayMEMPrimaryPipelineProjection",
    "RelayMEMPrimaryPipelineRequest",
    "RelayMEMPrimaryPipelineResult",
    "RelayMEMPrimaryPipelineStageResult",
    "build_relaymem_primary_pipeline_node_result",
    "execute_relaymem_primary_pipeline",
    "project_relaymem_primary_pipeline",
]
