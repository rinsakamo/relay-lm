"""I1-GD bounded retention, isolation, and cleanup authority.

One call performs one deterministic, non-recursive maintenance pass.  It never
polls, sleeps, invokes I1-GC replay, mutates downstream queue/source state, or
executes a worker.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import stat
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .config import RelayLMConfig
from .relaymem_slp_durable_finalization_fence import (
    acquire_relaymem_slp_durable_finalization_fence,
)
from .relaymem_slp_durable_finalization_isolation import (
    ISOLATION_MAX_BYTES,
    RelayMEMSLPDurableFinalizationIsolationResult,
    build_isolation_marker,
    isolation_filename,
    publish_relaymem_slp_durable_finalization_isolation,
    read_relaymem_slp_durable_finalization_isolation_fd,
)
from .relaymem_slp_durable_finalization_record import (
    RECORD_SCHEMA,
    canonical_json_bytes,
    decode_canonical_json,
    validate_base_record,
    validate_seal_record,
    validate_segment_chain,
    validate_segment_record,
)
from .relaymem_slp_durable_finalization_replay import (
    COMPLETION_SCHEMA,
    completion_filename,
    validate_completion_marker,
)
from .relaymem_slp_durable_finalization_store import (
    _open_store_root,
    _read_bounded,
)
from .relaymem_slp_queue_record import dedupe

RETENTION_PROJECTION_SCHEMA = (
    "relaymem.slp_durable_finalization_retention_projection.v0"
)
_MAX_REASONS = 32
_MAX_ENTRY_LIMIT = 1_000_000
_BASE_RE = re.compile(r"^durable-finalization-v0-([0-9a-f]{64})\.base\.json$")
_SEGMENT_RE = re.compile(
    r"^durable-finalization-v0-([0-9a-f]{64})\.segment-([0-9]{6})\.json$"
)
_SEAL_RE = re.compile(r"^durable-finalization-v0-([0-9a-f]{64})\.seal\.json$")
_COMPLETION_RE = re.compile(
    r"^durable-finalization-completion-v0-([0-9a-f]{64})\.json$"
)
_ISOLATION_RE = re.compile(
    r"^durable-finalization-v0-([0-9a-f]{64})\.segment-isolation\.json$"
)
_LOCK_RE = re.compile(
    r"^\.durable-finalization-replay-v0-([0-9a-f]{64})\.lock$"
)
_KNOWN_TEMP_RE = re.compile(
    r"^\.durable-finalization(?:-completion|-isolation)?-[0-9a-f]{32}\.tmp$"
)
_RELAXED_LOCATOR_RE = re.compile(r"([0-9a-f]{64})")

RetentionStatus = Literal[
    "disabled",
    "dry_run_ready",
    "maintenance_complete",
    "invalid_input",
    "blocked",
    "capacity_exceeded",
    "timeout_reached",
    "failed",
]

Classification = Literal[
    "fresh_incomplete",
    "expired_incomplete_orphan",
    "sealed_pending",
    "complete_retained",
    "complete_retention_expired",
    "isolated_retained",
    "isolated_retention_expired",
    "corrupt_known_locator",
    "unsupported_known_locator",
    "unsafe_or_unclassifiable",
    "ambiguous",
]

FaultInjector = Callable[[str], None]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationRetentionResult:
    status: RetentionStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    inventory_complete: bool
    bounded_entry_count: int
    bounded_record_count: int
    processed_record_count: int
    retained_count: int
    isolated_count: int
    cleaned_component_count: int
    removed_isolation_count: int
    lock_busy_count: int
    blocked_count: int
    capacity_exceeded: bool
    timeout_reached: bool
    reason_ids: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationRetentionResult("
            f"status={self.status!r}, processed_record_count="
            f"{self.processed_record_count!r}, content_free=True, "
            "identifier_values_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": RETENTION_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "locator_value_included": False,
            "digest_values_included": False,
            "path_values_included": False,
            "timestamp_values_included": False,
            "exception_text_included": False,
            "nested_protected_result_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "inventory_complete": self.inventory_complete,
            "bounded_entry_count": self.bounded_entry_count,
            "bounded_record_count": self.bounded_record_count,
            "processed_record_count": self.processed_record_count,
            "retained_count": self.retained_count,
            "isolated_count": self.isolated_count,
            "cleaned_component_count": self.cleaned_component_count,
            "removed_isolation_count": self.removed_isolation_count,
            "lock_busy_count": self.lock_busy_count,
            "blocked_count": self.blocked_count,
            "capacity_exceeded": self.capacity_exceeded,
            "timeout_reached": self.timeout_reached,
            "reason_ids": list(self.reason_ids),
            "replay_invoked": False,
            "protected_source_mutated": False,
            "queue_mutated": False,
            "b3_transition_performed": False,
            "c2_invoked": False,
            "worker_invoked": False,
            "writes_memory": False,
            "polling_performed": False,
            "sleep_performed": False,
        }


@dataclass
class _Counters:
    processed: int = 0
    retained: int = 0
    isolated: int = 0
    cleaned: int = 0
    removed_isolation: int = 0
    lock_busy: int = 0
    blocked: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Inventory:
    complete: bool
    entry_count: int
    groups: dict[str, tuple[str, ...]]
    reason_ids: tuple[str, ...]
    capacity_exceeded: bool


@dataclass(frozen=True)
class _Read:
    status: Literal[
        "absent", "ok", "corrupt", "unsupported", "unsafe", "failed"
    ]
    value: dict[str, object] | None = field(default=None, repr=False)
    info: os.stat_result | None = field(default=None, repr=False)
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Classified:
    classification: Classification
    reason_id: str
    flags: dict[str, bool]
    component_names: tuple[str, ...]
    isolation: RelayMEMSLPDurableFinalizationIsolationResult
    age_seconds: float | None
    should_isolate: bool
    should_cleanup: bool
    should_remove_isolation: bool
    blocked: bool


@dataclass(frozen=True)
class _Settings:
    enabled: bool
    dry: bool
    apply: bool
    root: str
    completed_retention: int
    orphan_grace: int
    isolated_retention: int
    max_records_per_pass: int
    timeout_ms: int
    max_record_bytes: int
    max_segment_bytes: int
    max_segment_count: int
    max_record_count: int



def maintain_relaymem_slp_durable_finalization_retention(
    *,
    config: RelayLMConfig,
    now_provider: Callable[[], float] = time.time,
    fault_injector: FaultInjector | None = None,
) -> RelayMEMSLPDurableFinalizationRetentionResult:
    """Run one bounded, deterministic maintenance pass and return immediately."""

    if type(config) is not RelayLMConfig:
        return _empty_result(
            "invalid_input",
            False,
            True,
            False,
            ("exact_relaylm_config_required",),
        )
    settings, setting_reasons = _settings(config)
    if settings is None:
        return _empty_result(
            "invalid_input",
            bool(getattr(config, "relaymem_slp_durable_finalization_retention_enabled", False)),
            bool(getattr(config, "relaymem_slp_durable_finalization_retention_dry_run_only", True)),
            bool(getattr(config, "relaymem_slp_durable_finalization_retention_apply_enabled", False)),
            setting_reasons,
        )
    if not settings.enabled:
        return _empty_result(
            "disabled",
            settings.enabled,
            settings.dry,
            settings.apply,
            (),
        )
    gate_reasons = _gate_reasons(settings)
    if gate_reasons:
        return _empty_result(
            "blocked",
            settings.enabled,
            settings.dry,
            settings.apply,
            gate_reasons,
        )
    if not callable(now_provider):
        return _empty_result(
            "invalid_input",
            settings.enabled,
            settings.dry,
            settings.apply,
            ("durable_finalization_retention_now_provider_invalid",),
        )
    if fault_injector is not None and not callable(fault_injector):
        return _empty_result(
            "invalid_input",
            settings.enabled,
            settings.dry,
            settings.apply,
            ("durable_finalization_retention_fault_injector_invalid",),
        )
    try:
        now = float(now_provider())
    except (TypeError, ValueError, OverflowError):
        return _empty_result(
            "invalid_input",
            settings.enabled,
            settings.dry,
            settings.apply,
            ("durable_finalization_retention_clock_invalid",),
        )
    if not math.isfinite(now):
        return _empty_result(
            "invalid_input",
            settings.enabled,
            settings.dry,
            settings.apply,
            ("durable_finalization_retention_clock_invalid",),
        )

    deadline = time.monotonic() + (settings.timeout_ms / 1000.0)
    root_fd, root_reasons = _open_store_root(settings.root)
    if root_fd is None:
        return _empty_result(
            "invalid_input",
            settings.enabled,
            settings.dry,
            settings.apply,
            root_reasons,
        )
    try:
        inventory = _inventory(root_fd, settings)
    finally:
        os.close(root_fd)
    if not inventory.complete:
        return RelayMEMSLPDurableFinalizationRetentionResult(
            status="capacity_exceeded" if inventory.capacity_exceeded else "blocked",
            enabled=settings.enabled,
            dry_run_only=settings.dry,
            apply_enabled=settings.apply,
            inventory_complete=False,
            bounded_entry_count=inventory.entry_count,
            bounded_record_count=len(inventory.groups),
            processed_record_count=0,
            retained_count=0,
            isolated_count=0,
            cleaned_component_count=0,
            removed_isolation_count=0,
            lock_busy_count=0,
            blocked_count=1,
            capacity_exceeded=inventory.capacity_exceeded,
            timeout_reached=False,
            reason_ids=inventory.reason_ids,
        )

    _fault(fault_injector, "after_inventory_before_lock")
    counters = _Counters(reasons=list(inventory.reason_ids))
    selected = sorted(inventory.groups)[: settings.max_records_per_pass]
    timeout_reached = False
    for locator in selected:
        if time.monotonic() > deadline:
            timeout_reached = True
            counters.reasons.append("durable_finalization_retention_timeout")
            break
        counters.processed += 1
        if settings.dry:
            root_fd, reasons = _open_store_root(settings.root)
            if root_fd is None:
                counters.blocked += 1
                counters.reasons.extend(reasons)
                continue
            try:
                classified = _classify_locator(
                    root_fd,
                    locator,
                    settings,
                    now,
                )
            finally:
                os.close(root_fd)
            _count_dry_run(classified, counters)
            continue

        fence, busy, reasons = acquire_relaymem_slp_durable_finalization_fence(
            settings.root,
            locator,
        )
        if fence is None:
            if busy:
                counters.lock_busy += 1
            else:
                counters.blocked += 1
            counters.reasons.extend(reasons)
            continue
        try:
            _fault(fault_injector, "after_lock_before_reread")
            classified = _classify_locator(
                fence.root_fd,
                locator,
                settings,
                now,
            )
            _apply_classified(
                settings,
                locator,
                classified,
                fence.root_fd,
                now,
                counters,
                fault_injector,
            )
        finally:
            fence.close()

    status: RetentionStatus
    if timeout_reached:
        status = "timeout_reached"
    elif counters.blocked:
        status = "blocked"
    elif settings.dry:
        status = "dry_run_ready"
    else:
        status = "maintenance_complete"
    return RelayMEMSLPDurableFinalizationRetentionResult(
        status=status,
        enabled=settings.enabled,
        dry_run_only=settings.dry,
        apply_enabled=settings.apply,
        inventory_complete=True,
        bounded_entry_count=inventory.entry_count,
        bounded_record_count=len(inventory.groups),
        processed_record_count=counters.processed,
        retained_count=counters.retained,
        isolated_count=counters.isolated,
        cleaned_component_count=counters.cleaned,
        removed_isolation_count=counters.removed_isolation,
        lock_busy_count=counters.lock_busy,
        blocked_count=counters.blocked,
        capacity_exceeded=False,
        timeout_reached=timeout_reached,
        reason_ids=dedupe(tuple(counters.reasons))[:_MAX_REASONS],
    )


def _settings(config: RelayLMConfig) -> tuple[_Settings | None, tuple[str, ...]]:
    values = {
        "enabled": getattr(
            config,
            "relaymem_slp_durable_finalization_retention_enabled",
            False,
        ),
        "dry": getattr(
            config,
            "relaymem_slp_durable_finalization_retention_dry_run_only",
            True,
        ),
        "apply": getattr(
            config,
            "relaymem_slp_durable_finalization_retention_apply_enabled",
            False,
        ),
        "root": config.relaymem_slp_durable_finalization_root,
        "completed_retention": getattr(
            config,
            "relaymem_slp_durable_finalization_completed_retention_seconds",
            604800,
        ),
        "orphan_grace": getattr(
            config,
            "relaymem_slp_durable_finalization_orphan_grace_seconds",
            86400,
        ),
        "isolated_retention": getattr(
            config,
            "relaymem_slp_durable_finalization_isolated_retention_seconds",
            2592000,
        ),
        "max_records_per_pass": getattr(
            config,
            "relaymem_slp_durable_finalization_cleanup_max_records_per_pass",
            64,
        ),
        "timeout_ms": getattr(
            config,
            "relaymem_slp_durable_finalization_cleanup_timeout_ms",
            5000,
        ),
        "max_record_bytes": config.relaymem_slp_durable_finalization_max_record_bytes,
        "max_segment_bytes": config.relaymem_slp_durable_finalization_max_segment_bytes,
        "max_segment_count": config.relaymem_slp_durable_finalization_max_segment_count,
        "max_record_count": config.relaymem_slp_durable_finalization_max_record_count,
    }
    reasons: list[str] = []
    for key in ("enabled", "dry", "apply"):
        if type(values[key]) is not bool:
            reasons.append(f"durable_finalization_retention_{key}_invalid")
    if type(values["root"]) is not str:
        reasons.append("durable_finalization_root_invalid")
    for key in (
        "completed_retention",
        "orphan_grace",
        "isolated_retention",
        "max_records_per_pass",
        "timeout_ms",
        "max_record_bytes",
        "max_segment_bytes",
        "max_segment_count",
        "max_record_count",
    ):
        if type(values[key]) is not int or values[key] < 1:
            reasons.append(f"durable_finalization_retention_{key}_invalid")
    if reasons:
        return None, dedupe(tuple(reasons))
    return _Settings(**values), ()


def _gate_reasons(settings: _Settings) -> tuple[str, ...]:
    reasons: list[str] = []
    if settings.dry and settings.apply:
        reasons.append("durable_finalization_retention_apply_enabled_in_dry_run")
    if not settings.dry and not settings.apply:
        reasons.append("durable_finalization_retention_apply_gate_incomplete")
    return dedupe(tuple(reasons))


def _entry_limit(settings: _Settings) -> int:
    per_record = min(settings.max_segment_count, 4096) + 6
    return min(
        _MAX_ENTRY_LIMIT,
        max(64, settings.max_record_count * per_record + 128),
    )


def _inventory(root_fd: int, settings: _Settings) -> _Inventory:
    groups: dict[str, set[str]] = {}
    reasons: list[str] = []
    count = 0
    limit = _entry_limit(settings)
    try:
        with os.scandir(root_fd) as entries:
            for entry in entries:
                count += 1
                if count > limit:
                    return _Inventory(
                        False,
                        limit,
                        {key: tuple(sorted(value)) for key, value in groups.items()},
                        ("durable_finalization_retention_inventory_capacity_exceeded",),
                        True,
                    )
                name = entry.name
                parsed = _parse_name(name)
                if parsed is None:
                    if _KNOWN_TEMP_RE.fullmatch(name):
                        reasons.append("durable_finalization_known_temp_retained")
                        continue
                    relaxed = _RELAXED_LOCATOR_RE.search(name)
                    if relaxed and name.startswith(("durable-finalization", ".durable-finalization")):
                        groups.setdefault(relaxed.group(1), set()).add(name)
                    else:
                        reasons.append("durable_finalization_unrecognized_object_retained")
                    continue
                kind, locator = parsed
                if kind == "lock":
                    continue
                groups.setdefault(locator, set()).add(name)
    except OSError:
        return _Inventory(
            False,
            count,
            {},
            ("durable_finalization_retention_inventory_failed",),
            False,
        )
    return _Inventory(
        True,
        count,
        {key: tuple(sorted(value)) for key, value in groups.items()},
        dedupe(tuple(reasons))[:_MAX_REASONS],
        False,
    )


def _parse_name(name: str) -> tuple[str, str] | None:
    for kind, pattern in (
        ("base", _BASE_RE),
        ("segment", _SEGMENT_RE),
        ("seal", _SEAL_RE),
        ("completion", _COMPLETION_RE),
        ("isolation", _ISOLATION_RE),
        ("lock", _LOCK_RE),
    ):
        match = pattern.fullmatch(name)
        if match:
            return kind, match.group(1)
    return None


def _scan_locator_names(
    root_fd: int,
    locator: str,
    settings: _Settings,
) -> tuple[tuple[str, ...] | None, tuple[str, ...]]:
    names: list[str] = []
    count = 0
    limit = _entry_limit(settings)
    try:
        with os.scandir(root_fd) as entries:
            for entry in entries:
                count += 1
                if count > limit:
                    return None, (
                        "durable_finalization_retention_inventory_capacity_exceeded",
                    )
                name = entry.name
                parsed = _parse_name(name)
                if parsed is not None and parsed[1] == locator and parsed[0] != "lock":
                    names.append(name)
                    continue
                if locator in name and name.startswith(("durable-finalization", ".durable-finalization")):
                    if not _LOCK_RE.fullmatch(name) and not _KNOWN_TEMP_RE.fullmatch(name):
                        names.append(name)
    except OSError:
        return None, ("durable_finalization_retention_inventory_failed",)
    return tuple(sorted(set(names))), ()


def _classify_locator(
    root_fd: int,
    locator: str,
    settings: _Settings,
    now: float,
) -> _Classified:
    names, scan_reasons = _scan_locator_names(root_fd, locator, settings)
    empty_flags = _flags(False, False, False, False, False, False)
    absent_isolation = RelayMEMSLPDurableFinalizationIsolationResult(
        status="absent", present=False, durable=False
    )
    if names is None:
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            scan_reasons[0],
            empty_flags,
            (),
            absent_isolation,
        )
    parsed_names: dict[str, list[tuple[str, int | None]]] = {
        "base": [],
        "segment": [],
        "seal": [],
        "completion": [],
        "isolation": [],
        "unknown": [],
    }
    for name in names:
        parsed = _parse_name(name)
        if parsed is None or parsed[1] != locator:
            parsed_names["unknown"].append((name, None))
            continue
        kind = parsed[0]
        sequence = None
        if kind == "segment":
            match = _SEGMENT_RE.fullmatch(name)
            sequence = int(match.group(2)) if match else None
        parsed_names[kind].append((name, sequence))
    if parsed_names["unknown"]:
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            "durable_finalization_noncanonical_filename",
            empty_flags,
            names,
            absent_isolation,
        )
    if any(len(parsed_names[key]) > 1 for key in ("base", "seal", "completion", "isolation")):
        return _blocked_classification(
            "ambiguous",
            "durable_finalization_component_identity_ambiguous",
            empty_flags,
            names,
            absent_isolation,
        )

    isolation = read_relaymem_slp_durable_finalization_isolation_fd(
        root_fd,
        locator,
    )
    base_present = bool(parsed_names["base"])
    segment_present = bool(parsed_names["segment"])
    seal_present = bool(parsed_names["seal"])
    completion_present = bool(parsed_names["completion"])
    flags = _flags(
        base_present,
        segment_present,
        seal_present,
        completion_present,
        False,
        False,
    )
    if isolation.status not in {"absent", "loaded"}:
        return _blocked_classification(
            "ambiguous" if isolation.status == "collision" else "unsafe_or_unclassifiable",
            isolation.reason_ids[0]
            if isolation.reason_ids
            else "durable_finalization_isolation_invalid",
            flags,
            names,
            isolation,
        )
    if isolation.status == "loaded":
        component_names = tuple(
            name for name in names if name != isolation_filename(locator)
        )
        unsafe_reason = _preflight_cleanup_names(root_fd, component_names, settings)
        if unsafe_reason:
            return _blocked_classification(
                "unsafe_or_unclassifiable",
                unsafe_reason,
                flags,
                component_names,
                isolation,
            )
        age, age_reason = _age_from_ns(isolation.mtime_ns, now)
        if age_reason:
            return _blocked_classification(
                "unsafe_or_unclassifiable",
                age_reason,
                flags,
                component_names,
                isolation,
            )
        expired = age is not None and age >= settings.isolated_retention
        return _Classified(
            classification=(
                "isolated_retention_expired" if expired else "isolated_retained"
            ),
            reason_id=(
                "isolated_retention_expired" if expired else "isolated_retained"
            ),
            flags=flags,
            component_names=component_names,
            isolation=isolation,
            age_seconds=age,
            should_isolate=False,
            should_cleanup=bool(component_names),
            should_remove_isolation=expired,
            blocked=False,
        )

    reads: dict[str, _Read] = {}
    stats: list[os.stat_result] = []
    for kind in ("base", "seal", "completion"):
        if parsed_names[kind]:
            name = parsed_names[kind][0][0]
            read = _read_component(root_fd, name, kind, settings)
            reads[kind] = read
            if read.info is not None:
                stats.append(read.info)
    segment_reads: list[tuple[int, str, _Read]] = []
    for name, sequence in sorted(
        parsed_names["segment"], key=lambda item: (-1 if item[1] is None else item[1])
    ):
        if sequence is None or sequence >= settings.max_segment_count:
            return _blocked_classification(
                "unsafe_or_unclassifiable",
                "durable_finalization_segment_count_overflow",
                flags,
                names,
                isolation,
            )
        read = _read_component(root_fd, name, "segment", settings)
        segment_reads.append((sequence, name, read))
        if read.info is not None:
            stats.append(read.info)

    all_reads = list(reads.values()) + [item[2] for item in segment_reads]
    unsafe = next((item for item in all_reads if item.status in {"unsafe", "failed"}), None)
    if unsafe is not None:
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            unsafe.reasons[0]
            if unsafe.reasons
            else "durable_finalization_component_unsafe",
            flags,
            names,
            isolation,
        )
    unsupported = any(item.status == "unsupported" for item in all_reads)
    corrupt = any(item.status == "corrupt" for item in all_reads)
    if unsupported or corrupt:
        flags = _flags(
            base_present,
            segment_present,
            seal_present,
            completion_present,
            corrupt,
            unsupported,
        )
        return _Classified(
            classification=(
                "unsupported_known_locator" if unsupported else "corrupt_known_locator"
            ),
            reason_id=(
                "unsupported_known_schema" if unsupported else "corrupt_known_record"
            ),
            flags=flags,
            component_names=names,
            isolation=isolation,
            age_seconds=None,
            should_isolate=True,
            should_cleanup=True,
            should_remove_isolation=False,
            blocked=False,
        )

    base = reads.get("base")
    seal = reads.get("seal")
    completion = reads.get("completion")
    if base is None or base.value is None:
        if names:
            flags["corrupt_observed"] = True
            return _Classified(
                classification="corrupt_known_locator",
                reason_id="base_missing_corrupt_orphan",
                flags=flags,
                component_names=names,
                isolation=isolation,
                age_seconds=None,
                should_isolate=True,
                should_cleanup=True,
                should_remove_isolation=False,
                blocked=False,
            )
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            "durable_finalization_record_missing",
            flags,
            names,
            isolation,
        )

    sequences = [item[0] for item in segment_reads]
    if sequences != list(range(len(sequences))):
        flags["corrupt_observed"] = True
        return _Classified(
            classification="corrupt_known_locator",
            reason_id="segment_order_corrupt_orphan",
            flags=flags,
            component_names=names,
            isolation=isolation,
            age_seconds=None,
            should_isolate=True,
            should_cleanup=True,
            should_remove_isolation=False,
            blocked=False,
        )
    segment_values = [item[2].value for item in segment_reads]
    if any(value is None for value in segment_values):
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            "durable_finalization_segment_unreadable",
            flags,
            names,
            isolation,
        )
    validated_segments, chain_reasons = validate_segment_chain(
        base.value,
        [value for value in segment_values if value is not None],
    )
    if chain_reasons:
        flags["corrupt_observed"] = True
        return _Classified(
            classification="corrupt_known_locator",
            reason_id="segment_chain_corrupt_orphan",
            flags=flags,
            component_names=names,
            isolation=isolation,
            age_seconds=None,
            should_isolate=True,
            should_cleanup=True,
            should_remove_isolation=False,
            blocked=False,
        )

    if seal is not None and seal.value is not None:
        strict_seal, seal_reasons = validate_seal_record(
            seal.value,
            expected_base=base.value,
            expected_segments=validated_segments,
        )
        if strict_seal is None or seal_reasons:
            flags["corrupt_observed"] = True
            return _Classified(
                classification="corrupt_known_locator",
                reason_id="seal_evidence_mismatch",
                flags=flags,
                component_names=names,
                isolation=isolation,
                age_seconds=None,
                should_isolate=True,
                should_cleanup=True,
                should_remove_isolation=False,
                blocked=False,
            )
        if completion is None or completion.value is None:
            return _Classified(
                classification="sealed_pending",
                reason_id="sealed_pending_replay_required",
                flags=flags,
                component_names=names,
                isolation=isolation,
                age_seconds=_safe_age(stats, now)[0],
                should_isolate=False,
                should_cleanup=False,
                should_remove_isolation=False,
                blocked=False,
            )
        collision_reason = _completion_collision_reason(
            completion.value,
            strict_seal,
        )
        if collision_reason:
            return _blocked_classification(
                "ambiguous",
                collision_reason,
                flags,
                names,
                isolation,
            )
        age, age_reason = _safe_age(stats, now)
        if age_reason:
            return _blocked_classification(
                "unsafe_or_unclassifiable",
                age_reason,
                flags,
                names,
                isolation,
            )
        expired = age is not None and age >= settings.completed_retention
        return _Classified(
            classification=(
                "complete_retention_expired" if expired else "complete_retained"
            ),
            reason_id=(
                "completed_retention_expired" if expired else "completed_retained"
            ),
            flags=flags,
            component_names=names,
            isolation=isolation,
            age_seconds=age,
            should_isolate=expired,
            should_cleanup=expired,
            should_remove_isolation=False,
            blocked=False,
        )

    if completion is not None:
        flags["corrupt_observed"] = True
        return _Classified(
            classification="corrupt_known_locator",
            reason_id="completion_without_valid_seal",
            flags=flags,
            component_names=names,
            isolation=isolation,
            age_seconds=None,
            should_isolate=True,
            should_cleanup=True,
            should_remove_isolation=False,
            blocked=False,
        )

    age, age_reason = _safe_age(stats, now)
    if age_reason:
        return _blocked_classification(
            "unsafe_or_unclassifiable",
            age_reason,
            flags,
            names,
            isolation,
        )
    expired = age is not None and age >= settings.orphan_grace
    return _Classified(
        classification=(
            "expired_incomplete_orphan" if expired else "fresh_incomplete"
        ),
        reason_id=(
            "incomplete_orphan_expired" if expired else "fresh_incomplete_retained"
        ),
        flags=flags,
        component_names=names,
        isolation=isolation,
        age_seconds=age,
        should_isolate=expired,
        should_cleanup=expired,
        should_remove_isolation=False,
        blocked=False,
    )


def _read_component(
    root_fd: int,
    name: str,
    kind: str,
    settings: _Settings,
) -> _Read:
    try:
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _Read("absent")
    except OSError:
        return _Read("failed", reasons=("durable_finalization_component_unreadable",))
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        return _Read(
            "unsafe",
            info=before,
            reasons=("durable_finalization_unsafe_file_type",),
        )
    if before.st_nlink != 1:
        return _Read(
            "unsafe",
            info=before,
            reasons=("durable_finalization_hardlink_invalid",),
        )
    maximum = (
        settings.max_segment_bytes
        if kind == "segment"
        else 16 * 1024
        if kind == "completion"
        else settings.max_record_bytes
    )
    if before.st_size > maximum:
        return _Read(
            "unsafe",
            info=before,
            reasons=(f"durable_finalization_{kind}_size_exceeded",),
        )
    try:
        fd = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except OSError:
        return _Read(
            "failed",
            info=before,
            reasons=("durable_finalization_component_unreadable",),
        )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
            or before.st_size != info.st_size
            or before.st_mtime_ns != info.st_mtime_ns
        ):
            return _Read(
                "unsafe",
                info=info,
                reasons=("durable_finalization_file_changed_during_read",),
            )
        data = _read_bounded(fd, maximum)
    finally:
        os.close(fd)
    if data is None:
        return _Read(
            "unsafe",
            info=info,
            reasons=(f"durable_finalization_{kind}_size_exceeded",),
        )
    try:
        after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return _Read(
            "unsafe",
            info=info,
            reasons=("durable_finalization_file_changed_during_read",),
        )
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1
        or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        or after.st_size != info.st_size
        or after.st_mtime_ns != info.st_mtime_ns
    ):
        return _Read(
            "unsafe",
            info=info,
            reasons=("durable_finalization_file_changed_during_read",),
        )
    value, decode_reason = decode_canonical_json(data)
    if value is None or decode_reason:
        return _Read(
            "corrupt",
            info=info,
            reasons=(decode_reason or "durable_finalization_decode_failed",),
        )
    expected_schema = COMPLETION_SCHEMA if kind == "completion" else RECORD_SCHEMA
    if value.get("schema_version") != expected_schema:
        return _Read(
            "unsupported",
            value=value,
            info=info,
            reasons=(f"durable_finalization_{kind}_schema_unsupported",),
        )
    if kind == "base":
        validated, reasons = validate_base_record(value)
    elif kind == "segment":
        validated, reasons = validate_segment_record(value)
    elif kind == "seal":
        validated, reasons = validate_seal_record(value)
    else:
        validated, reasons = validate_completion_marker(value)
    if validated is None or reasons:
        return _Read("corrupt", value=value, info=info, reasons=reasons)
    return _Read("ok", value=validated, info=info)


def _completion_collision_reason(
    completion: Mapping[str, object],
    seal: Mapping[str, object],
) -> str | None:
    if completion.get("seal_digest") != seal.get("seal_digest"):
        return "durable_finalization_completion_identity_collision"
    durable_job = seal.get("durable_job")
    if type(durable_job) is not dict:
        return "durable_finalization_completion_identity_collision"
    expected_job_digest = hashlib.sha256(
        canonical_json_bytes(durable_job)
    ).hexdigest()
    if completion.get("durable_job_digest") != expected_job_digest:
        return "durable_finalization_completion_identity_collision"
    return None


def _safe_age(
    stats: Sequence[os.stat_result],
    now: float,
) -> tuple[float | None, str | None]:
    if not stats:
        return None, "durable_finalization_retention_clock_unavailable"
    newest_ns = max(item.st_mtime_ns for item in stats)
    return _age_from_ns(newest_ns, now)


def _age_from_ns(mtime_ns: int | None, now: float) -> tuple[float | None, str | None]:
    if type(mtime_ns) is not int or mtime_ns < 0:
        return None, "durable_finalization_retention_mtime_invalid"
    mtime = mtime_ns / 1_000_000_000
    if not math.isfinite(mtime):
        return None, "durable_finalization_retention_mtime_invalid"
    age = now - mtime
    if not math.isfinite(age) or age < 0:
        return None, "durable_finalization_retention_clock_not_monotonic"
    return age, None


def _flags(
    base: bool,
    segment: bool,
    seal: bool,
    completion: bool,
    corrupt: bool,
    unsupported: bool,
) -> dict[str, bool]:
    return {
        "base_present": base,
        "segment_present": segment,
        "seal_present": seal,
        "completion_present": completion,
        "corrupt_observed": corrupt,
        "unsupported_observed": unsupported,
    }


def _blocked_classification(
    classification: Classification,
    reason: str,
    flags: dict[str, bool],
    names: Sequence[str],
    isolation: RelayMEMSLPDurableFinalizationIsolationResult,
) -> _Classified:
    return _Classified(
        classification=classification,
        reason_id=reason,
        flags=flags,
        component_names=tuple(names),
        isolation=isolation,
        age_seconds=None,
        should_isolate=False,
        should_cleanup=False,
        should_remove_isolation=False,
        blocked=True,
    )


def _count_dry_run(classified: _Classified, counters: _Counters) -> None:
    counters.reasons.append(classified.reason_id)
    if classified.blocked:
        counters.blocked += 1
    else:
        counters.retained += 1


def _apply_classified(
    settings: _Settings,
    locator: str,
    classified: _Classified,
    root_fd: int,
    now: float,
    counters: _Counters,
    fault_injector: FaultInjector | None,
) -> None:
    counters.reasons.append(classified.reason_id)
    if classified.blocked:
        counters.blocked += 1
        return
    isolation = classified.isolation
    if classified.should_isolate:
        try:
            marker = build_isolation_marker(
                locator_digest=locator,
                classification=classified.classification,
                reason_id=classified.reason_id,
                observed_component_flags=classified.flags,
            )
        except ValueError:
            counters.blocked += 1
            counters.reasons.append("durable_finalization_isolation_build_failed")
            return
        published = publish_relaymem_slp_durable_finalization_isolation(
            settings.root,
            marker,
        )
        if published.status not in {"published_new", "duplicate_existing"}:
            counters.blocked += 1
            counters.reasons.extend(published.reason_ids)
            return
        if published.status == "published_new":
            counters.isolated += 1
        _fault(fault_injector, "after_isolation_publish_before_reread")
        isolation = read_relaymem_slp_durable_finalization_isolation_fd(
            root_fd,
            locator,
            expected=marker,
        )
        if isolation.status != "loaded":
            counters.blocked += 1
            counters.reasons.extend(
                isolation.reason_ids
                or ("durable_finalization_isolation_canonical_reread_failed",)
            )
            return
    if isolation.status == "loaded" and classified.should_cleanup:
        _fault(fault_injector, "after_isolation_reread_before_first_unlink")
        for name in _cleanup_order(classified.component_names, locator):
            _fault(fault_injector, "during_component_cleanup")
            removed, reason = _secure_unlink(root_fd, name, settings)
            if reason:
                counters.blocked += 1
                counters.reasons.append(reason)
                return
            if removed:
                counters.cleaned += 1
        _fault(fault_injector, "after_component_cleanup_before_directory_fsync")
        try:
            os.fsync(root_fd)
        except OSError:
            counters.blocked += 1
            counters.reasons.append(
                "durable_finalization_cleanup_directory_fsync_ambiguous"
            )
            return
        _fault(fault_injector, "after_directory_fsync_before_return")

    marker_age, marker_age_reason = _age_from_ns(isolation.mtime_ns, now)
    remove_marker = (
        isolation.status == "loaded"
        and classified.should_remove_isolation
        and marker_age_reason is None
        and marker_age is not None
        and marker_age >= settings.isolated_retention
    )
    if remove_marker:
        remaining, scan_reasons = _scan_locator_names(root_fd, locator, settings)
        if remaining is None:
            counters.blocked += 1
            counters.reasons.extend(scan_reasons)
            return
        expected_marker = isolation_filename(locator)
        non_marker = [name for name in remaining if name != expected_marker]
        if non_marker:
            counters.retained += 1
            counters.reasons.append(
                "durable_finalization_isolation_components_remain"
            )
            return
        _fault(fault_injector, "during_isolation_marker_delete")
        removed, reason = _secure_unlink(
            root_fd,
            expected_marker,
            settings,
            isolation=True,
        )
        if reason:
            counters.blocked += 1
            counters.reasons.append(reason)
            return
        _fault(fault_injector, "after_isolation_marker_delete_before_directory_fsync")
        try:
            os.fsync(root_fd)
        except OSError:
            reread = read_relaymem_slp_durable_finalization_isolation_fd(
                root_fd,
                locator,
            )
            counters.blocked += 1
            counters.reasons.append(
                "durable_finalization_isolation_delete_fsync_ambiguous"
                if reread.status == "absent"
                else "durable_finalization_isolation_delete_failed"
            )
            return
        if removed:
            counters.removed_isolation += 1
        return
    counters.retained += 1


def _cleanup_order(names: Sequence[str], locator: str) -> tuple[str, ...]:
    marker = isolation_filename(locator)
    components = [name for name in names if name != marker and not _LOCK_RE.fullmatch(name)]
    def key(name: str) -> tuple[int, str]:
        parsed = _parse_name(name)
        rank = {
            "segment": 0,
            "base": 1,
            "seal": 2,
            "completion": 3,
        }.get(parsed[0] if parsed else "unknown", 4)
        return rank, name
    return tuple(sorted(components, key=key))


def _preflight_cleanup_names(
    root_fd: int,
    names: Sequence[str],
    settings: _Settings,
) -> str | None:
    for name in names:
        parsed = _parse_name(name)
        if parsed is None:
            return "durable_finalization_noncanonical_filename"
        kind = parsed[0]
        maximum = (
            settings.max_segment_bytes
            if kind == "segment"
            else 16 * 1024
            if kind == "completion"
            else settings.max_record_bytes
        )
        try:
            info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            return "durable_finalization_component_unreadable"
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            return "durable_finalization_unsafe_file_type"
        if info.st_nlink != 1:
            return "durable_finalization_hardlink_invalid"
        if info.st_size > maximum:
            return f"durable_finalization_{kind}_size_exceeded"
    return None


def _secure_unlink(
    root_fd: int,
    name: str,
    settings: _Settings,
    *,
    isolation: bool = False,
) -> tuple[bool, str | None]:
    parsed = _parse_name(name)
    if isolation:
        maximum = ISOLATION_MAX_BYTES
    elif parsed is None:
        return False, "durable_finalization_noncanonical_filename"
    elif parsed[0] == "segment":
        maximum = settings.max_segment_bytes
    elif parsed[0] == "completion":
        maximum = 16 * 1024
    else:
        maximum = settings.max_record_bytes
    try:
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False, None
    except OSError:
        return False, "durable_finalization_cleanup_stat_failed"
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > maximum
    ):
        return False, "durable_finalization_cleanup_unsafe_file"
    try:
        fd = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except OSError:
        return False, "durable_finalization_cleanup_open_failed"
    try:
        info = os.fstat(fd)
    finally:
        os.close(fd)
    try:
        after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return False, "durable_finalization_cleanup_changed_before_unlink"
    stable = (
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and (before.st_dev, before.st_ino) == (info.st_dev, info.st_ino)
        and (after.st_dev, after.st_ino) == (info.st_dev, info.st_ino)
        and after.st_nlink == 1
        and after.st_size == info.st_size == before.st_size
        and after.st_mtime_ns == info.st_mtime_ns == before.st_mtime_ns
    )
    if not stable:
        return False, "durable_finalization_cleanup_changed_before_unlink"
    try:
        os.unlink(name, dir_fd=root_fd)
    except OSError:
        try:
            os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return True, None
        except OSError:
            return False, "durable_finalization_cleanup_unlink_ambiguous"
        return False, "durable_finalization_cleanup_unlink_failed"
    try:
        os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True, None
    except OSError:
        return False, "durable_finalization_cleanup_unlink_ambiguous"
    return False, "durable_finalization_cleanup_unlink_failed"


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


def _empty_result(
    status: RetentionStatus,
    enabled: bool,
    dry: bool,
    apply: bool,
    reasons: Sequence[str],
) -> RelayMEMSLPDurableFinalizationRetentionResult:
    return RelayMEMSLPDurableFinalizationRetentionResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry,
        apply_enabled=apply,
        inventory_complete=False,
        bounded_entry_count=0,
        bounded_record_count=0,
        processed_record_count=0,
        retained_count=0,
        isolated_count=0,
        cleaned_component_count=0,
        removed_isolation_count=0,
        lock_busy_count=0,
        blocked_count=1 if status in {"invalid_input", "blocked", "failed"} else 0,
        capacity_exceeded=False,
        timeout_reached=False,
        reason_ids=dedupe(tuple(reasons))[:_MAX_REASONS],
    )


__all__ = [
    "RETENTION_PROJECTION_SCHEMA",
    "RelayMEMSLPDurableFinalizationRetentionResult",
    "maintain_relaymem_slp_durable_finalization_retention",
]
