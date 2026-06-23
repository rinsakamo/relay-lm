"""Retry-safe bridge from the I1-B protected registry to the C1-2 worker.

The existing registry ``consume_for_claim`` remains backward compatible. This
adapter prepares a fresh, unconsumed C1-0 source for one exact claim while
leaving the protected capture retained. The worker owns one-shot source
consumption. Callers release the retained capture only after a terminal queue
transition; retry release and lease loss keep it available for a later claim.
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
from .relaymem_slp_queue_record import dedupe, is_token

PREPARED_SOURCE_PROJECTION_SCHEMA = (
    "relaymem.slp_primary_worker_prepared_source_projection.v0"
)
PreparedSourceStatus = Literal["prepared", "source_unavailable", "blocked"]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPreparedWorkerSourceResult:
    status: PreparedSourceStatus
    retained: bool
    source_available: bool
    blocked_reasons: tuple[str, ...]
    source: RelayMEMSLPPrimaryWorkerSource | None = field(default=None, repr=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = field(
        default=None, repr=False
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
            "exception_text_included": False,
            "status": self.status,
            "retained": self.retained,
            "source_available": self.source_available,
            "source_prepared": self.source is not None,
            "source_consumed": False,
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def prepare_relaymem_slp_primary_worker_source_for_claim(
    registry: object,
    *,
    claimed_record: object,
    character_id: object,
) -> RelayMEMSLPPreparedWorkerSourceResult:
    """Prepare one fresh unconsumed source while retaining the registry capture."""

    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _result("blocked", ("exact_source_registry_required",))
    record, reasons = _validate_record(claimed_record, required_state="claimed")
    if not is_token(character_id):
        reasons = dedupe((*reasons, "character_id_invalid"))
    if reasons or record is None:
        return _result("blocked", reasons)

    now = registry._now()
    key = _record_key(record)
    with registry._lock:
        registry._purge_expired_locked(now)
        capture = registry._entries.get(key)
        if capture is None:
            return _result(
                "source_unavailable", ("protected_source_unavailable",)
            )
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
                retained=True,
                source_available=True,
            )
        return _result(
            "prepared",
            (),
            retained=True,
            source_available=True,
            source=built.source,
            request_scope=scope,
        )


def _result(
    status: PreparedSourceStatus,
    reasons: tuple[str, ...],
    *,
    retained: bool = False,
    source_available: bool = False,
    source: RelayMEMSLPPrimaryWorkerSource | None = None,
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = None,
) -> RelayMEMSLPPreparedWorkerSourceResult:
    return RelayMEMSLPPreparedWorkerSourceResult(
        status=status,
        retained=retained,
        source_available=source_available,
        blocked_reasons=dedupe(reasons),
        source=source,
        request_scope=request_scope,
    )


__all__ = [
    "PREPARED_SOURCE_PROJECTION_SCHEMA",
    "RelayMEMSLPPreparedWorkerSourceResult",
    "prepare_relaymem_slp_primary_worker_source_for_claim",
]
