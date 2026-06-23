"""Process-local protected source capture registry for Phase 6 I1-B.

The request runtime cannot construct ``RelayMEMSLPPrimaryWorkerSource`` before a
real B3 claim because the canonical C1-0 builder intentionally requires one
exact claimed record.  This module therefore retains the exact protected
16-field source payload after B2 enqueue and invokes the canonical C1-0 builder
only when a later worker presents the exact claimed record.

The registry is intentionally process-local and restart-incomplete.  It never
serializes protected content, emits identifiers in public projections, starts a
worker, claims a queue record, or invokes RelayMEM persistence.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic
from types import MappingProxyType
from typing import Callable, Literal

from relaylm.relaymem_slp_primary_worker_source import (
    SOURCE_FIELDS,
    SOURCE_SCHEMA,
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
    build_relaymem_slp_primary_worker_source,
    consume_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import (
    DISPATCH_KEY_PREFIX,
    JOB_ID_PREFIX,
    dedupe,
    has_prefixed_digest,
    is_token,
    validate_record_mapping,
)

REGISTRY_PROJECTION_SCHEMA = "relaymem.slp_primary_worker_source_registry_projection.v0"
_MAX_REASONS = 32
_IDENTITY_FIELDS = (
    "job_id",
    "dispatch_idempotency_key",
    "run_id",
    "turn_index",
    "session_id",
    "namespace",
    "source_event_kind",
    "source_count",
    "source_lineage_fingerprint",
)

RegistryStatus = Literal[
    "published_new",
    "duplicate_existing",
    "consumed",
    "released",
    "source_unavailable",
    "blocked",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPProtectedSourceCapture:
    """One immutable protected payload retained only inside the live process."""

    character_id: str = field(repr=False)
    payload: Mapping[str, object] = field(repr=False, compare=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope = field(
        repr=False,
        compare=False,
    )
    created_at_monotonic: float = field(repr=False, compare=False)
    expires_at_monotonic: float = field(repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPProtectedSourceCapture("
            "process_local=True, content_included=True, protected_content_omitted=True)"
        )


@dataclass(frozen=True)
class RelayMEMSLPSourceRegistryResult:
    """Content-free registry result with optional protected ownership transfer."""

    status: RegistryStatus
    retained: bool
    duplicate_existing: bool
    source_available: bool
    consumed: bool
    released: bool
    process_local: bool
    restart_complete: bool
    blocked_reasons: tuple[str, ...]
    source: RelayMEMSLPPrimaryWorkerSource | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def release_transferred_scope(self) -> None:
        """Explicitly close ownership transferred by a successful consume."""

        if self.request_scope is not None:
            self.request_scope.close()

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": REGISTRY_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "queue_path_included": False,
            "timestamp_values_included": False,
            "exception_text_included": False,
            "status": self.status,
            "retained": self.retained,
            "duplicate_existing": self.duplicate_existing,
            "source_available": self.source_available,
            "consumed": self.consumed,
            "released": self.released,
            "process_local": self.process_local,
            "restart_complete": self.restart_complete,
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "mutates_soul": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


class RelayMEMSLPPrimaryWorkerSourceRegistry:
    """Thread-safe bounded owner for exact protected source captures."""

    def __init__(
        self,
        *,
        max_entries: int = 256,
        ttl_seconds: float = 1800.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if type(max_entries) is not int or max_entries < 1:
            raise ValueError("source_registry_max_entries_invalid")
        if (
            type(ttl_seconds) not in {int, float}
            or isinstance(ttl_seconds, bool)
            or ttl_seconds <= 0
        ):
            raise ValueError("source_registry_ttl_invalid")
        if not callable(clock):
            raise ValueError("source_registry_clock_invalid")
        self._max_entries = max_entries
        self._ttl_seconds = float(ttl_seconds)
        self._clock = clock
        self._lock = RLock()
        self._entries: dict[tuple[str, str], RelayMEMSLPProtectedSourceCapture] = {}

    def __repr__(self) -> str:
        with self._lock:
            size = len(self._entries)
        return (
            "RelayMEMSLPPrimaryWorkerSourceRegistry("
            f"size={size}, max_entries={self._max_entries}, "
            "process_local=True, protected_content_omitted=True)"
        )

    @property
    def size(self) -> int:
        with self._lock:
            self._purge_expired_locked(self._now())
            return len(self._entries)

    def publish(
        self,
        *,
        source_payload: object,
        durable_record: object,
        request_scope: object,
        character_id: object,
    ) -> RelayMEMSLPSourceRegistryResult:
        """Publish one queued source capture without constructing a C1 source."""

        record, reasons = _validate_record(durable_record, required_state="queued")
        payload, payload_reasons = _validate_capture_payload(source_payload, record)
        reasons = dedupe((*reasons, *payload_reasons))
        if type(request_scope) is not RelayMEMSLPPrimaryWorkerSourceScope:
            reasons = dedupe((*reasons, "exact_request_scope_required"))
        elif not request_scope.active:
            reasons = dedupe((*reasons, "request_scope_stale"))
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if reasons or record is None or payload is None:
            return _result("blocked", blocked_reasons=reasons)

        try:
            frozen_payload = _freeze_json(payload)
        except (TypeError, ValueError, RecursionError, OverflowError):
            return _result(
                "blocked",
                blocked_reasons=("protected_source_capture_invalid",),
            )
        assert isinstance(frozen_payload, Mapping)
        now = self._now()
        capture = RelayMEMSLPProtectedSourceCapture(
            character_id=str(character_id),
            payload=frozen_payload,
            request_scope=request_scope,
            created_at_monotonic=now,
            expires_at_monotonic=now + self._ttl_seconds,
        )
        key = _record_key(record)
        with self._lock:
            self._purge_expired_locked(now)
            existing = self._entries.get(key)
            if existing is not None:
                if _captures_equivalent(existing, capture):
                    return _result(
                        "duplicate_existing",
                        retained=True,
                        duplicate_existing=True,
                        source_available=True,
                    )
                return _result(
                    "blocked",
                    retained=True,
                    source_available=True,
                    blocked_reasons=("protected_source_capture_collision",),
                )
            if len(self._entries) >= self._max_entries:
                return _result(
                    "blocked",
                    blocked_reasons=("protected_source_registry_capacity_reached",),
                )
            self._entries[key] = capture
        return _result("published_new", retained=True, source_available=True)

    def consume_for_claim(
        self,
        *,
        claimed_record: object,
        character_id: object,
    ) -> RelayMEMSLPSourceRegistryResult:
        """Build and consume the exact C1-0 source for one real claimed record."""

        record, reasons = _validate_record(claimed_record, required_state="claimed")
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if reasons or record is None:
            return _result("blocked", blocked_reasons=reasons)

        now = self._now()
        key = _record_key(record)
        with self._lock:
            self._purge_expired_locked(now)
            capture = self._entries.get(key)
            if capture is None:
                return _result(
                    "source_unavailable",
                    blocked_reasons=("protected_source_unavailable",),
                )
            if capture.character_id != character_id:
                return _result(
                    "blocked",
                    retained=True,
                    source_available=True,
                    blocked_reasons=("protected_source_character_mismatch",),
                )
            correlation = _correlation_reasons(capture.payload, record)
            if correlation:
                return _result(
                    "blocked",
                    retained=True,
                    source_available=True,
                    blocked_reasons=correlation,
                )
            try:
                payload = _thaw_json(capture.payload)
            except (TypeError, ValueError, RecursionError, OverflowError):
                self._entries.pop(key, None)
                capture.request_scope.close()
                return _result(
                    "blocked",
                    blocked_reasons=("protected_source_capture_invalid",),
                )
            build_result = build_relaymem_slp_primary_worker_source(
                payload,
                claimed_record=record,
                request_scope=capture.request_scope,
                enabled=True,
                dry_run_only=False,
                apply_enabled=True,
            )
            if build_result.status != "ready" or build_result.source is None:
                self._entries.pop(key, None)
                capture.request_scope.close()
                return _result(
                    "blocked",
                    blocked_reasons=dedupe(
                        (*build_result.blocked_reasons, "protected_source_build_failed")
                    ),
                )
            source, consume_reasons = consume_relaymem_slp_primary_worker_source(
                build_result.source,
                claimed_record=record,
                request_scope=capture.request_scope,
            )
            if source is None:
                return _result(
                    "blocked",
                    retained=True,
                    source_available=True,
                    blocked_reasons=dedupe(
                        (*consume_reasons, "protected_source_consume_failed")
                    ),
                )
            self._entries.pop(key, None)
        return _result(
            "consumed",
            source_available=True,
            consumed=True,
            source=source,
            request_scope=capture.request_scope,
        )

    def release(
        self,
        *,
        durable_record: object,
        character_id: object,
    ) -> RelayMEMSLPSourceRegistryResult:
        """Explicitly remove and invalidate one retained source capture."""

        record, reasons = _validate_record(durable_record, required_state=None)
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if reasons or record is None:
            return _result("blocked", blocked_reasons=reasons)
        key = _record_key(record)
        with self._lock:
            self._purge_expired_locked(self._now())
            capture = self._entries.get(key)
            if capture is None:
                return _result(
                    "source_unavailable",
                    blocked_reasons=("protected_source_unavailable",),
                )
            if capture.character_id != character_id:
                return _result(
                    "blocked",
                    retained=True,
                    source_available=True,
                    blocked_reasons=("protected_source_character_mismatch",),
                )
            self._entries.pop(key, None)
            capture.request_scope.close()
        return _result("released", released=True)

    def _purge_expired_locked(self, now: float) -> None:
        expired = [
            key
            for key, capture in self._entries.items()
            if capture.expires_at_monotonic <= now or not capture.request_scope.active
        ]
        for key in expired:
            capture = self._entries.pop(key)
            capture.request_scope.close()

    def _now(self) -> float:
        value = self._clock()
        if type(value) not in {int, float} or isinstance(value, bool):
            raise RuntimeError("source_registry_clock_invalid")
        return float(value)


def _validate_record(
    value: object,
    *,
    required_state: str | None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("exact_durable_record_required",)
    reasons = validate_record_mapping(value)
    if reasons:
        return None, reasons
    if required_state is not None and value.get("state") != required_state:
        return None, (f"durable_record_{required_state}_required",)
    return value, ()


def _validate_capture_payload(
    value: object,
    record: Mapping[str, object] | None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("exact_protected_source_payload_required",)
    reasons: list[str] = []
    if len(value) != len(SOURCE_FIELDS) or set(value) != SOURCE_FIELDS:
        reasons.append("protected_source_payload_shape_mismatch")
    if value.get("schema_version") != SOURCE_SCHEMA:
        reasons.append("protected_source_payload_schema_mismatch")
    if value.get("runtime_private") is not True:
        reasons.append("protected_source_payload_runtime_private_required")
    if value.get("content_included") is not True:
        reasons.append("protected_source_payload_content_required")
    if record is not None:
        reasons.extend(_correlation_reasons(value, record))
    return (value, ()) if not reasons else (None, dedupe(reasons))


def _correlation_reasons(
    payload: Mapping[str, object],
    record: Mapping[str, object],
) -> tuple[str, ...]:
    return dedupe(
        tuple(
            f"protected_source_{field_name}_mismatch"
            for field_name in _IDENTITY_FIELDS
            if payload.get(field_name) != record.get(field_name)
        )
    )


def _record_key(record: Mapping[str, object]) -> tuple[str, str]:
    job_id = record.get("job_id")
    dispatch_key = record.get("dispatch_idempotency_key")
    assert has_prefixed_digest(job_id, JOB_ID_PREFIX)
    assert has_prefixed_digest(dispatch_key, DISPATCH_KEY_PREFIX)
    return str(job_id), str(dispatch_key)


def _captures_equivalent(
    left: RelayMEMSLPProtectedSourceCapture,
    right: RelayMEMSLPProtectedSourceCapture,
) -> bool:
    if left.character_id != right.character_id:
        return False
    try:
        return _thaw_json(left.payload) == _thaw_json(right.payload)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return False


def _freeze_json(value: object, *, depth: int = 0) -> object:
    if depth > 16:
        raise ValueError("protected_source_capture_depth_exceeded")
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item, depth=depth + 1) for key, item in value.items()}
        )
    if type(value) in {list, tuple}:
        return tuple(_freeze_json(item, depth=depth + 1) for item in value)
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise TypeError("protected_source_capture_value_invalid")


def _thaw_json(value: object, *, depth: int = 0) -> object:
    if depth > 16:
        raise ValueError("protected_source_capture_depth_exceeded")
    if isinstance(value, Mapping):
        return {
            key: _thaw_json(item, depth=depth + 1)
            for key, item in value.items()
        }
    if type(value) is tuple:
        return [_thaw_json(item, depth=depth + 1) for item in value]
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise TypeError("protected_source_capture_value_invalid")


def _result(
    status: RegistryStatus,
    *,
    retained: bool = False,
    duplicate_existing: bool = False,
    source_available: bool = False,
    consumed: bool = False,
    released: bool = False,
    blocked_reasons: Sequence[str] = (),
    source: RelayMEMSLPPrimaryWorkerSource | None = None,
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = None,
) -> RelayMEMSLPSourceRegistryResult:
    return RelayMEMSLPSourceRegistryResult(
        status=status,
        retained=retained,
        duplicate_existing=duplicate_existing,
        source_available=source_available,
        consumed=consumed,
        released=released,
        process_local=True,
        restart_complete=False,
        blocked_reasons=dedupe(tuple(blocked_reasons))[:_MAX_REASONS],
        source=source,
        request_scope=request_scope,
    )


__all__ = [
    "REGISTRY_PROJECTION_SCHEMA",
    "RelayMEMSLPPrimaryWorkerSourceRegistry",
    "RelayMEMSLPProtectedSourceCapture",
    "RelayMEMSLPSourceRegistryResult",
]
