"""Retry-safe and restart-complete bridge from protected capture to C1-2.

A process-local registry remains an optional hot cache.  When it is empty after
restart, the adapter loads the claim-independent durable capture and always
builds a fresh C1-0 source and fresh one-shot scope for the current exact claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
    build_relaymem_slp_primary_worker_source,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
    _correlation_reasons,
    _record_key,
    _thaw_json,
    _validate_record,
)
from .relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
    RelayMEMSLPProtectedSourceStoreResult,
)
from .relaymem_slp_queue_record import TERMINAL_STATES, dedupe, is_token

PREPARED_SOURCE_PROJECTION_SCHEMA = (
    "relaymem.slp_primary_worker_prepared_source_projection.v0"
)
RELEASE_PROJECTION_SCHEMA = "relaymem.slp_primary_worker_source_release_projection.v0"
PreparedSourceStatus = Literal[
    "prepared", "source_unavailable", "retryable", "blocked"
]
ReleaseStatus = Literal["released", "cleanup_required", "blocked"]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPreparedWorkerSourceResult:
    status: PreparedSourceStatus
    retained: bool
    source_available: bool
    restart_rehydrated: bool
    blocked_reasons: tuple[str, ...]
    source: RelayMEMSLPPrimaryWorkerSource | None = field(default=None, repr=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = field(
        default=None, repr=False
    )
    store_result: RelayMEMSLPProtectedSourceStoreResult | None = field(
        default=None, repr=False, compare=False
    )

    def release_prepared_scope(self) -> None:
        if self.request_scope is not None:
            self.request_scope.close()

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PREPARED_SOURCE_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_messages_included": False,
            "governed_summary_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "claim_fence_included": False,
            "source_digest_included": False,
            "protected_source_path_included": False,
            "exception_text_included": False,
            "status": self.status,
            "retained": self.retained,
            "source_available": self.source_available,
            "source_prepared": self.source is not None,
            "source_consumed": False,
            "restart_rehydrated": self.restart_rehydrated,
            "fresh_scope_created": self.request_scope is not None,
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


@dataclass(frozen=True)
class RelayMEMSLPProtectedSourceReleaseResult:
    status: ReleaseStatus
    process_local_released: bool
    durable_removed: bool
    cleanup_required: bool
    blocked_reasons: tuple[str, ...]
    store_result: RelayMEMSLPProtectedSourceStoreResult | None = field(
        default=None, repr=False, compare=False
    )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": RELEASE_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "identifier_values_included": False,
            "protected_source_path_included": False,
            "exception_text_included": False,
            "status": self.status,
            "terminal_transition_already_committed": True,
            "process_local_released": self.process_local_released,
            "durable_removed": self.durable_removed,
            "cleanup_required": self.cleanup_required,
            "queue_transition_reverted": False,
            "retry_authority_created": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def prepare_relaymem_slp_primary_worker_source_for_claim(
    registry: object,
    *,
    claimed_record: object,
    character_id: object,
    source_store: object | None = None,
) -> RelayMEMSLPPreparedWorkerSourceResult:
    """Build one fresh unconsumed source for the exact current claim."""

    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _result("blocked", ("exact_source_registry_required",))
    record, reasons = _validate_record(claimed_record, required_state="claimed")
    if not is_token(character_id):
        reasons = dedupe((*reasons, "character_id_invalid"))
    if reasons or record is None:
        return _result("blocked", reasons)

    key = _record_key(record)
    capture = None
    with registry._lock:
        registry._purge_expired_locked(registry._now())
        capture = registry._entries.get(key)
        if capture is not None:
            if capture.character_id != character_id:
                return _result(
                    "blocked",
                    ("protected_source_character_mismatch",),
                    retained=True,
                    source_available=True,
                )
            correlation = _correlation_reasons(capture.payload, record)
            if correlation:
                return _result(
                    "blocked",
                    correlation,
                    retained=True,
                    source_available=True,
                )
            try:
                payload = _thaw_json(capture.payload)
            except (TypeError, ValueError, RecursionError, OverflowError):
                return _result(
                    "blocked",
                    ("protected_source_capture_invalid",),
                    retained=True,
                    source_available=True,
                )
            assert type(payload) is dict
            return _build_fresh(
                payload,
                record,
                retained=True,
                restart_rehydrated=False,
            )

    if type(source_store) is not RelayMEMSLPDurableProtectedSourceStore:
        return _result(
            "source_unavailable", ("protected_source_unavailable",)
        )
    loaded = source_store.load_for_claim(
        claimed_record=record,
        character_id=character_id,
    )
    if loaded.status == "missing":
        return _result(
            "source_unavailable",
            loaded.blocked_reasons or ("protected_source_unavailable",),
            store_result=loaded,
        )
    if loaded.status == "retryable":
        return _result(
            "retryable",
            loaded.blocked_reasons,
            retained=True,
            source_available=loaded.source_available,
            store_result=loaded,
        )
    if loaded.status != "loaded" or type(loaded.protected_capture) is not dict:
        return _result(
            "blocked",
            loaded.blocked_reasons or ("protected_source_rehydrate_failed",),
            retained=True,
            source_available=loaded.source_available,
            store_result=loaded,
        )
    return _build_fresh(
        loaded.protected_capture,
        record,
        retained=True,
        restart_rehydrated=True,
        store_result=loaded,
    )


def release_relaymem_slp_primary_worker_source_after_terminal(
    registry: object,
    *,
    terminal_record: object,
    character_id: object,
    source_store: object,
) -> RelayMEMSLPProtectedSourceReleaseResult:
    """Release only after terminal B3 commit; cleanup failure never rewinds B3."""

    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _release_result("blocked", ("exact_source_registry_required",))
    if type(source_store) is not RelayMEMSLPDurableProtectedSourceStore:
        return _release_result(
            "blocked", ("exact_durable_protected_source_store_required",)
        )
    record, reasons = _validate_record(terminal_record, required_state=None)
    if record is not None and record.get("state") not in TERMINAL_STATES:
        reasons = dedupe((*reasons, "terminal_queue_record_required"))
    if not is_token(character_id):
        reasons = dedupe((*reasons, "character_id_invalid"))
    if reasons or record is None:
        return _release_result("blocked", reasons)

    local = registry.release(durable_record=record, character_id=character_id)
    local_released = local.status in {"released", "source_unavailable"}
    durable = source_store.cleanup_after_terminal(
        terminal_record=record,
        character_id=character_id,
    )
    if durable.status in {"removed", "already_removed"}:
        return _release_result(
            "released",
            (),
            process_local_released=local_released,
            durable_removed=True,
            store_result=durable,
        )
    return _release_result(
        "cleanup_required",
        durable.blocked_reasons or ("protected_source_cleanup_required",),
        process_local_released=local_released,
        durable_removed=False,
        cleanup_required=True,
        store_result=durable,
    )


def _build_fresh(
    payload: dict[str, object],
    record: dict[str, object],
    *,
    retained: bool,
    restart_rehydrated: bool,
    store_result: RelayMEMSLPProtectedSourceStoreResult | None = None,
) -> RelayMEMSLPPreparedWorkerSourceResult:
    scope = RelayMEMSLPPrimaryWorkerSourceScope()
    built = build_relaymem_slp_primary_worker_source(
        payload,
        claimed_record=record,
        request_scope=scope,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    if built.status != "ready" or built.source is None:
        scope.close()
        return _result(
            "blocked",
            dedupe((*built.blocked_reasons, "protected_source_build_failed")),
            retained=retained,
            source_available=True,
            restart_rehydrated=restart_rehydrated,
            store_result=store_result,
        )
    return _result(
        "prepared",
        (),
        retained=retained,
        source_available=True,
        restart_rehydrated=restart_rehydrated,
        source=built.source,
        request_scope=scope,
        store_result=store_result,
    )


def _result(
    status: PreparedSourceStatus,
    reasons: tuple[str, ...],
    *,
    retained: bool = False,
    source_available: bool = False,
    restart_rehydrated: bool = False,
    source: RelayMEMSLPPrimaryWorkerSource | None = None,
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = None,
    store_result: RelayMEMSLPProtectedSourceStoreResult | None = None,
) -> RelayMEMSLPPreparedWorkerSourceResult:
    return RelayMEMSLPPreparedWorkerSourceResult(
        status=status,
        retained=retained,
        source_available=source_available,
        restart_rehydrated=restart_rehydrated,
        blocked_reasons=dedupe(reasons),
        source=source,
        request_scope=request_scope,
        store_result=store_result,
    )


def _release_result(
    status: ReleaseStatus,
    reasons: tuple[str, ...],
    *,
    process_local_released: bool = False,
    durable_removed: bool = False,
    cleanup_required: bool = False,
    store_result: RelayMEMSLPProtectedSourceStoreResult | None = None,
) -> RelayMEMSLPProtectedSourceReleaseResult:
    return RelayMEMSLPProtectedSourceReleaseResult(
        status=status,
        process_local_released=process_local_released,
        durable_removed=durable_removed,
        cleanup_required=cleanup_required,
        blocked_reasons=dedupe(reasons),
        store_result=store_result,
    )


__all__ = [
    "PREPARED_SOURCE_PROJECTION_SCHEMA",
    "RELEASE_PROJECTION_SCHEMA",
    "RelayMEMSLPPreparedWorkerSourceResult",
    "RelayMEMSLPProtectedSourceReleaseResult",
    "prepare_relaymem_slp_primary_worker_source_for_claim",
    "release_relaymem_slp_primary_worker_source_after_terminal",
]
