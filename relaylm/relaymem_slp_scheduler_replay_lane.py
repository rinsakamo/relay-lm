"""O1B bounded sealed I1-G discovery and one I1-GC delegation.

One call inventories the server-owned durable-finalization root once, classifies
bounded logical records with the existing I1-G validators, selects at most one
sealed pending record deterministically, performs a canonical reread, delegates
to I1-GC at most once, and returns an O1A ``LaneOutcome``.  It never polls,
sleeps, executes queue work, or mutates I1-G evidence directly.
"""
from __future__ import annotations

import hashlib
import importlib
import os
import re
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, Literal

from . import _relaymem_slp_durable_finalization_replay_impl as _replay_impl
from .config import RelayLMConfig
from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .relaymem_slp_durable_finalization_record import (
    decode_canonical_json,
    validate_base_record,
    validate_seal_record,
    validate_segment_chain,
    validate_segment_record,
)
from .relaymem_slp_durable_finalization_replay import (
    replay_relaymem_slp_durable_finalization_record,
    validate_completion_marker,
)
from .relaymem_slp_durable_finalization_store import (
    _open_store_root,
    _read_bounded,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_scheduler_contract import LaneOutcome, SchedulerGates

REPLAY_LANE_NODE_NAME: Final = "relaymem_slp_scheduler_replay_lane"
DEFAULT_DISCOVERY_MAX_ENTRIES: Final = 256
MAX_DISCOVERY_MAX_ENTRIES: Final = 4096
_MAX_REASON_IDS: Final = 8
_PREFIX: Final = "durable-finalization-v0-"
_DIGEST_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_BASE_RE: Final = re.compile(r"^durable-finalization-v0-([0-9a-f]{64})\.base\.json$")
_SEGMENT_RE: Final = re.compile(
    r"^durable-finalization-v0-([0-9a-f]{64})\.segment-([0-9]{6})\.json$"
)
_SEAL_RE: Final = re.compile(r"^durable-finalization-v0-([0-9a-f]{64})\.seal\.json$")
_COMPLETION_RE: Final = re.compile(
    r"^durable-finalization-completion-v0-([0-9a-f]{64})\.json$"
)
_REPLAY_LOCK_RE: Final = re.compile(
    rf"^{re.escape(_replay_impl._LOCK_PREFIX)}([0-9a-f]{{64}})\.lock$"
)
_PUBLICATION_TEMP_RE: Final = re.compile(r"^\.durable-finalization-[0-9a-f]{32}\.tmp$")
_COMPLETION_TEMP_RE: Final = re.compile(
    r"^\.durable-finalization-completion-[0-9a-f]{32}\.tmp$"
)

FaultInjector = Callable[[str], None]
_ComponentKind = Literal["base", "segment", "seal", "completion", "isolation"]
_GroupState = Literal[
    "incomplete", "sealed_pending", "complete", "isolated", "corrupt", "unsupported", "unsafe"
]


@dataclass(frozen=True, repr=False)
class _EntrySnapshot:
    name: str = field(repr=False)
    kind: _ComponentKind = field(repr=False)
    locator: str = field(repr=False)
    sequence: int | None = field(default=None, repr=False)
    device: int = field(default=0, repr=False)
    inode: int = field(default=0, repr=False)
    size: int = field(default=0, repr=False)
    mtime_ns: int = field(default=0, repr=False)
    mode: int = field(default=0, repr=False)


@dataclass(frozen=True, repr=False)
class _GroupSnapshot:
    locator: str = field(repr=False)
    entries: tuple[_EntrySnapshot, ...] = field(repr=False)
    state: _GroupState
    content_signature: tuple[tuple[str, int, int, int, str], ...] = field(
        default=(), repr=False, compare=False
    )


@dataclass(frozen=True, repr=False)
class _Inventory:
    complete: bool
    entry_count: int
    groups: Mapping[str, tuple[_EntrySnapshot, ...]] = field(repr=False)
    unsafe: bool
    reason_ids: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class _ComponentRead:
    status: Literal["ok", "corrupt", "unsupported", "unsafe"]
    value: dict[str, object] | None = field(default=None, repr=False, compare=False)
    digest: str | None = field(default=None, repr=False, compare=False)
    reason_ids: tuple[str, ...] = ()


@dataclass(frozen=True, repr=False)
class _PrivateReplayLaneDetails:
    candidate: _GroupSnapshot | None = field(default=None, repr=False, compare=False)
    delegate_result: object = field(default=None, repr=False, compare=False)


def run_relaymem_slp_scheduler_replay_lane_once(
    *,
    config: RelayLMConfig,
    gates: SchedulerGates,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    discovery_max_entries: int | None = None,
    fault_injector: FaultInjector | None = None,
) -> LaneOutcome:
    """Run one bounded replay-lane opportunity and return immediately."""

    if type(config) is not RelayLMConfig:
        return _outcome(
            "dependency_unavailable",
            enabled=False,
            reason_ids=("exact_relaylm_config_required",),
        )
    if type(gates) is not SchedulerGates:
        return _outcome(
            "dependency_unavailable",
            enabled=False,
            reason_ids=("exact_scheduler_gates_required",),
        )
    gate_reasons = gates.validation_reason_ids()
    if gate_reasons:
        reason = (
            "scheduler_dependency_unavailable"
            if gate_reasons == ("required_dependency_unavailable",)
            else "scheduler_gate_invalid"
        )
        return _outcome(
            "dependency_unavailable",
            enabled=bool(gates.enabled and gates.replay_lane_enabled),
            retryable=gate_reasons == ("required_dependency_unavailable",),
            reason_ids=(reason,),
        )
    if gates.mode == "disabled":
        return _outcome(
            "no_eligible_work",
            enabled=False,
            no_immediate_work=True,
            reason_ids=("scheduler_disabled",),
        )
    if not gates.replay_lane_enabled:
        return _outcome(
            "no_eligible_work",
            enabled=False,
            no_immediate_work=True,
            reason_ids=("replay_lane_disabled",),
        )
    if not gates.required_dependency_available:
        return _outcome(
            "dependency_unavailable",
            enabled=True,
            retryable=True,
            reason_ids=("scheduler_dependency_unavailable",),
        )
    limit = DEFAULT_DISCOVERY_MAX_ENTRIES if discovery_max_entries is None else discovery_max_entries
    if type(limit) is not int or not 1 <= limit <= MAX_DISCOVERY_MAX_ENTRIES:
        return _outcome(
            "unsafe_state",
            enabled=True,
            attempted=True,
            unsafe=True,
            no_immediate_work=True,
            reason_ids=("replay_inventory_limit_invalid",),
        )
    if fault_injector is not None and not callable(fault_injector):
        return _outcome(
            "unsafe_state",
            enabled=True,
            attempted=True,
            unsafe=True,
            no_immediate_work=True,
            reason_ids=("replay_fault_injector_invalid",),
        )
    delegate_mode = _i1gc_mode(config)
    if delegate_mode == "invalid":
        return _outcome(
            "dependency_unavailable", enabled=True, attempted=True,
            no_immediate_work=True, reason_ids=("replay_delegate_gate_invalid",),
        )
    if gates.mode == "dry_run" and delegate_mode == "apply":
        return _outcome(
            "dependency_unavailable", enabled=True, attempted=True,
            no_immediate_work=True,
            reason_ids=("scheduler_dry_run_blocks_replay_apply",),
        )

    try:
        inventory = _inventory_root(
            config, limit, fault_injector=fault_injector, inject_root_open_stage=True
        )
    except Exception:
        return _outcome(
            "failed",
            enabled=True,
            attempted=True,
            retryable=True,
            no_immediate_work=True,
            reason_ids=("replay_inventory_failed",),
        )
    if not inventory.complete:
        return _outcome(
            "unsafe_state",
            enabled=True,
            attempted=True,
            candidate_observed=bool(inventory.groups),
            unsafe=True,
            no_immediate_work=True,
            reason_ids=inventory.reason_ids or ("replay_inventory_incomplete",),
        )
    if inventory.unsafe:
        return _outcome(
            "unsafe_state",
            enabled=True,
            attempted=True,
            candidate_observed=bool(inventory.groups),
            unsafe=True,
            no_immediate_work=True,
            reason_ids=inventory.reason_ids or ("replay_root_integrity_unsafe",),
        )

    try:
        _fault(fault_injector, "after_inventory_before_classification")
        classified = _classify_inventory(config, inventory)
    except Exception:
        return _outcome(
            "failed",
            enabled=True,
            attempted=True,
            candidate_observed=bool(inventory.groups),
            retryable=True,
            no_immediate_work=True,
            reason_ids=("replay_classification_failed",),
        )
    unsafe_group = next(
        (item for item in classified if item.state in {"corrupt", "unsupported", "unsafe"}),
        None,
    )
    if unsafe_group is not None:
        return _outcome(
            "unsafe_state",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            unsafe=True,
            no_immediate_work=True,
            reason_ids=("replay_record_unsafe",),
            private=_PrivateReplayLaneDetails(candidate=unsafe_group),
        )
    try:
        _fault(fault_injector, "after_classification_before_selection")
    except Exception:
        return _outcome(
            "failed",
            enabled=True,
            attempted=True,
            candidate_observed=bool(classified),
            retryable=True,
            no_immediate_work=True,
            reason_ids=("replay_fault_injected",),
        )

    eligible = sorted(
        (item for item in classified if item.state == "sealed_pending"),
        key=lambda item: item.locator,
    )
    if not eligible:
        reason = "replay_no_eligible_record"
        if any(item.state == "isolated" for item in classified):
            reason = "replay_records_isolated"
        elif any(item.state == "complete" for item in classified):
            reason = "replay_records_complete"
        elif classified:
            reason = "replay_records_incomplete"
        return _outcome(
            "no_eligible_work",
            enabled=True,
            attempted=True,
            candidate_observed=bool(classified),
            no_immediate_work=True,
            reason_ids=(reason,),
        )
    selected = eligible[0]
    try:
        _fault(fault_injector, "after_selection_before_reread")
        current, reread_status = _canonical_reread(config, selected, limit, fault_injector)
    except Exception:
        return _outcome(
            "failed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            retryable=True,
            no_immediate_work=True,
            reason_ids=("replay_reread_failed",),
            private=_PrivateReplayLaneDetails(candidate=selected),
        )
    if current is None:
        if reread_status == "unsafe":
            return _outcome(
                "unsafe_state",
                enabled=True,
                attempted=True,
                candidate_observed=True,
                candidate_selected=True,
                canonical_reread_performed=True,
                unsafe=True,
                no_immediate_work=True,
                reason_ids=("replay_reread_unsafe",),
                private=_PrivateReplayLaneDetails(candidate=selected),
            )
        if reread_status == "isolated":
            return _outcome(
                "isolated",
                enabled=True,
                attempted=True,
                candidate_observed=True,
                candidate_selected=True,
                canonical_reread_performed=True,
                unsafe=True,
                no_immediate_work=True,
                reason_ids=("replay_candidate_isolated",),
                private=_PrivateReplayLaneDetails(candidate=selected),
            )
        return _outcome(
            "candidate_changed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            retryable=True,
            reason_ids=("replay_candidate_changed",),
            private=_PrivateReplayLaneDetails(candidate=selected),
        )

    exact_registry = registry
    if exact_registry is None:
        try:
            exact_registry = RelayMEMSLPPrimaryWorkerSourceRegistry(
                max_entries=config.relaymem_slp_source_registry_max_entries,
                ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,
            )
        except (TypeError, ValueError):
            return _outcome(
                "dependency_unavailable",
                enabled=True,
                attempted=True,
                candidate_observed=True,
                candidate_selected=True,
                canonical_reread_performed=True,
                retryable=False,
                no_immediate_work=True,
                reason_ids=("source_registry_unavailable",),
                private=_PrivateReplayLaneDetails(candidate=current),
            )
    elif type(exact_registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _outcome(
            "dependency_unavailable",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            no_immediate_work=True,
            reason_ids=("exact_source_registry_required",),
            private=_PrivateReplayLaneDetails(candidate=current),
        )

    try:
        _fault(fault_injector, "after_reread_before_delegation")
    except Exception:
        return _outcome(
            "failed", enabled=True, attempted=True, candidate_observed=True,
            candidate_selected=True, canonical_reread_performed=True,
            retryable=True, no_immediate_work=True,
            reason_ids=("replay_fault_injected",),
            private=_PrivateReplayLaneDetails(candidate=current),
        )
    try:
        delegate = replay_relaymem_slp_durable_finalization_record(
            config, locator_digest=current.locator, registry=exact_registry
        )
    except Exception:
        return _outcome(
            "failed", enabled=True, attempted=True, candidate_observed=True,
            candidate_selected=True, canonical_reread_performed=True,
            delegation_attempted=True, retryable=True, no_immediate_work=True,
            reason_ids=("replay_delegate_failed",),
            private=_PrivateReplayLaneDetails(candidate=current),
        )
    try:
        _fault(fault_injector, "after_delegation_before_lane_mapping")
    except Exception:
        return _outcome(
            "failed", enabled=True, attempted=True, candidate_observed=True,
            candidate_selected=True, canonical_reread_performed=True,
            delegation_attempted=True, delegation_completed=True,
            mutation_may_have_occurred=_delegate_mutation(delegate),
            retryable=True, no_immediate_work=True,
            reason_ids=("replay_fault_injected",),
            private=_PrivateReplayLaneDetails(candidate=current, delegate_result=delegate),
        )
    return _map_delegate_result(current, delegate)


def build_relaymem_slp_scheduler_replay_lane_node_result(
    outcome: LaneOutcome,
) -> PipelineNodeResult:
    if type(outcome) is not LaneOutcome or outcome.lane_kind != "replay":
        raise TypeError("exact_replay_lane_outcome_required")
    status = (
        "failed"
        if outcome.status == "failed"
        else "blocked"
        if outcome.status in {"dependency_unavailable", "busy", "not_replayable", "isolated", "unsafe_state"}
        else "diagnostic_only"
    )
    return build_pipeline_node_result(
        node_name=REPLAY_LANE_NODE_NAME,
        status=status,
        decision=outcome.status,
        blocked_reasons=outcome.bounded_reason_ids,
        diagnostics={
            "schema_version": outcome.schema_version,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "identifier_values_included": False,
            "path_values_included": False,
            "digest_values_included": False,
            "timestamp_values_included": False,
            "exception_text_included": False,
            "nested_delegate_result_included": False,
            "lane_kind": outcome.lane_kind,
            "status": outcome.status,
            "enabled": outcome.enabled,
            "attempted": outcome.attempted,
            "candidate_observed": outcome.candidate_observed,
            "candidate_selected": outcome.candidate_selected,
            "canonical_reread_performed": outcome.canonical_reread_performed,
            "delegation_attempted": outcome.delegation_attempted,
            "delegation_completed": outcome.delegation_completed,
            "mutation_may_have_occurred": outcome.mutation_may_have_occurred,
            "no_immediate_work": outcome.no_immediate_work,
            "contention_observed": outcome.contention_observed,
            "retryable": outcome.retryable,
            "unsafe": outcome.unsafe,
            "terminal_for_candidate": outcome.terminal_for_candidate,
            "reason_ids": list(outcome.bounded_reason_ids),
        },
        artifacts=[{
            "artifact_name": REPLAY_LANE_NODE_NAME,
            "candidate_observed": outcome.candidate_observed,
            "candidate_selected": outcome.candidate_selected,
            "delegation_attempted": outcome.delegation_attempted,
            "delegation_completed": outcome.delegation_completed,
            "completion_observed_by_delegate": outcome.status in {"completed", "already_complete"},
            "content_free": True,
            "private": True,
        }],
    )


def _inventory_root(
    config: RelayLMConfig,
    limit: int,
    *,
    fault_injector: FaultInjector | None,
    inject_root_open_stage: bool,
) -> _Inventory:
    root_fd, root_reasons = _open_store_root(
        config.relaymem_slp_durable_finalization_root
    )
    if root_fd is None:
        return _Inventory(False, 0, {}, True, _reasons(root_reasons) or ("replay_root_unavailable",))
    groups: dict[str, list[_EntrySnapshot]] = {}
    reasons: list[str] = []
    count = 0
    try:
        if inject_root_open_stage:
            _fault(fault_injector, "after_root_open_before_inventory")
        try:
            iterator = os.scandir(root_fd)
        except OSError:
            return _Inventory(False, 0, {}, True, ("replay_inventory_failed",))
        with iterator:
            for entry in iterator:
                count += 1
                if count > limit:
                    return _Inventory(
                        False, limit,
                        {key: tuple(value) for key, value in groups.items()},
                        True, ("replay_inventory_limit_exceeded",),
                    )
                _fault(fault_injector, "during_inventory")
                name = entry.name
                if type(name) is not str:
                    reasons.append("replay_root_integrity_unsafe")
                    continue
                parsed = _parse_component_name(name)
                control = _control_kind(name)
                try:
                    info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                except OSError:
                    reasons.append("replay_root_integrity_unsafe")
                    continue
                if (
                    stat.S_ISLNK(info.st_mode)
                    or not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                ):
                    reasons.append("replay_root_integrity_unsafe")
                    continue
                if parsed is None:
                    if control is None:
                        reasons.append("replay_unknown_root_entry")
                        continue
                    maximum = (
                        4096
                        if control == "lock"
                        else max(
                            config.relaymem_slp_durable_finalization_max_record_bytes,
                            _replay_impl._MAX_COMPLETION_BYTES,
                            _isolation_max_bytes(),
                        )
                    )
                    if info.st_size > maximum:
                        reasons.append("replay_control_object_unsafe")
                    continue
                kind, locator, sequence = parsed
                groups.setdefault(locator, []).append(
                    _EntrySnapshot(
                        name=name, kind=kind, locator=locator, sequence=sequence,
                        device=info.st_dev, inode=info.st_ino, size=info.st_size,
                        mtime_ns=info.st_mtime_ns, mode=info.st_mode,
                    )
                )
    finally:
        os.close(root_fd)
    return _Inventory(
        True, count,
        {key: tuple(sorted(value, key=lambda item: item.name)) for key, value in groups.items()},
        bool(reasons), _reasons(reasons),
    )

def _classify_inventory(config: RelayLMConfig, inventory: _Inventory) -> tuple[_GroupSnapshot, ...]:
    output: list[_GroupSnapshot] = []
    for locator in sorted(inventory.groups):
        output.append(_classify_group(config, locator, inventory.groups[locator]))
    return tuple(output)


def _classify_group(
    config: RelayLMConfig,
    locator: str,
    entries: Sequence[_EntrySnapshot],
) -> _GroupSnapshot:
    by_kind: dict[str, list[_EntrySnapshot]] = {
        "base": [], "segment": [], "seal": [], "completion": [], "isolation": []
    }
    for entry in entries:
        by_kind[entry.kind].append(entry)
    if any(len(by_kind[kind]) > 1 for kind in ("base", "seal", "completion", "isolation")):
        return _GroupSnapshot(locator, tuple(entries), "unsafe")
    sequences = [entry.sequence for entry in by_kind["segment"]]
    if any(value is None for value in sequences) or len(set(sequences)) != len(sequences):
        return _GroupSnapshot(locator, tuple(entries), "unsafe")
    numeric = sorted(int(value) for value in sequences if value is not None)
    if numeric != list(range(len(numeric))):
        return _GroupSnapshot(locator, tuple(entries), "corrupt")
    if len(numeric) > config.relaymem_slp_durable_finalization_max_segment_count:
        return _GroupSnapshot(locator, tuple(entries), "corrupt")

    if by_kind["isolation"]:
        isolation = _read_isolation(config, locator)
        if isolation == "loaded":
            signature = _capture_signature(config, entries)
            return _GroupSnapshot(
                locator, tuple(entries), "isolated", signature or ()
            ) if signature is not None else _GroupSnapshot(locator, tuple(entries), "unsafe")
        return _GroupSnapshot(locator, tuple(entries), "unsafe")

    root_fd, root_reasons = _open_store_root(
        config.relaymem_slp_durable_finalization_root
    )
    if root_fd is None:
        return _GroupSnapshot(locator, tuple(entries), "unsafe")
    decoded: dict[str, dict[str, object]] = {}
    segment_values: list[tuple[int, dict[str, object]]] = []
    signature_rows: list[tuple[str, int, int, int, str]] = []
    evidence_bytes = 0
    try:
        for entry in sorted(entries, key=lambda item: item.name):
            read = _read_component(config, root_fd, entry)
            if read.status != "ok" or read.value is None or read.digest is None:
                state: _GroupState = (
                    "unsupported" if read.status == "unsupported"
                    else "corrupt" if read.status == "corrupt"
                    else "unsafe"
                )
                return _GroupSnapshot(locator, tuple(entries), state, tuple(signature_rows))
            signature_rows.append(
                (entry.name, entry.device, entry.inode, entry.size, read.digest)
            )
            if entry.kind in {"base", "segment", "seal"}:
                evidence_bytes += entry.size
            if entry.kind == "segment":
                assert entry.sequence is not None
                segment_values.append((entry.sequence, read.value))
            else:
                decoded[entry.kind] = read.value
    finally:
        os.close(root_fd)

    if evidence_bytes > config.relaymem_slp_durable_finalization_max_record_bytes:
        return _GroupSnapshot(locator, tuple(entries), "corrupt", tuple(signature_rows))
    base = decoded.get("base")
    seal = decoded.get("seal")
    completion = decoded.get("completion")
    if base is None:
        return _GroupSnapshot(locator, tuple(entries), "corrupt", tuple(signature_rows))
    valid_base, base_reasons = validate_base_record(base, expected_locator=locator)
    if valid_base is None or base_reasons:
        return _GroupSnapshot(locator, tuple(entries), _schema_state(base_reasons), tuple(signature_rows))
    ordered_segments = [value for _, value in sorted(segment_values)]
    valid_segments, segment_reasons = validate_segment_chain(valid_base, ordered_segments)
    if segment_reasons:
        return _GroupSnapshot(locator, tuple(entries), _schema_state(segment_reasons), tuple(signature_rows))
    valid_seal: dict[str, object] | None = None
    if seal is not None:
        valid_seal, seal_reasons = validate_seal_record(
            seal, expected_base=valid_base, expected_segments=valid_segments
        )
        if valid_seal is None or seal_reasons:
            return _GroupSnapshot(locator, tuple(entries), _schema_state(seal_reasons), tuple(signature_rows))
    if completion is not None:
        valid_completion, completion_reasons = validate_completion_marker(
            completion, expected_locator=locator
        )
        if (
            valid_completion is None
            or completion_reasons
            or valid_seal is None
            or valid_completion.get("seal_digest") != valid_seal.get("seal_digest")
        ):
            return _GroupSnapshot(
                locator, tuple(entries),
                _schema_state(completion_reasons) if completion_reasons else "corrupt",
                tuple(signature_rows),
            )
        return _GroupSnapshot(locator, tuple(entries), "complete", tuple(signature_rows))
    if valid_seal is None:
        return _GroupSnapshot(locator, tuple(entries), "incomplete", tuple(signature_rows))
    return _GroupSnapshot(locator, tuple(entries), "sealed_pending", tuple(signature_rows))

def _canonical_reread(
    config: RelayLMConfig,
    selected: _GroupSnapshot,
    limit: int,
    fault_injector: FaultInjector | None,
) -> tuple[_GroupSnapshot | None, str]:
    _fault(fault_injector, "during_selected_reread")
    inventory = _inventory_root(
        config, limit, fault_injector=None, inject_root_open_stage=False
    )
    if not inventory.complete or inventory.unsafe:
        return None, "unsafe"
    entries = inventory.groups.get(selected.locator)
    if entries is None:
        return None, "changed"
    current = _classify_group(config, selected.locator, entries)
    if current.state == "isolated":
        return None, "isolated"
    if current.state in {"corrupt", "unsupported", "unsafe"}:
        return None, "unsafe"
    if current.state != "sealed_pending":
        return None, "changed"
    if _entry_identity(current.entries) != _entry_identity(selected.entries):
        return None, "changed"
    if current.content_signature != selected.content_signature:
        return None, "changed"
    return current, "ok"


def _read_component(
    config: RelayLMConfig,
    root_fd: int,
    entry: _EntrySnapshot,
) -> _ComponentRead:
    maximum = _component_max_bytes(config, entry.kind)
    try:
        before = os.stat(entry.name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return _ComponentRead("unsafe", reason_ids=("replay_component_unreadable",))
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (entry.device, entry.inode, entry.size, entry.mtime_ns)
        or before.st_size > maximum
    ):
        return _ComponentRead("unsafe", reason_ids=("replay_component_identity_unsafe",))
    try:
        fd = os.open(
            entry.name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except OSError:
        return _ComponentRead("unsafe", reason_ids=("replay_component_unreadable",))
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (info.st_dev, info.st_ino, info.st_size)
            != (entry.device, entry.inode, entry.size)
        ):
            return _ComponentRead("unsafe", reason_ids=("replay_component_identity_unsafe",))
        data = _read_bounded(fd, maximum)
    except OSError:
        return _ComponentRead("unsafe", reason_ids=("replay_component_unreadable",))
    finally:
        os.close(fd)
    if data is None:
        return _ComponentRead("corrupt", reason_ids=("replay_component_size_exceeded",))
    try:
        after = os.stat(entry.name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return _ComponentRead("unsafe", reason_ids=("replay_component_changed",))
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1
        or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        != (entry.device, entry.inode, entry.size, entry.mtime_ns)
    ):
        return _ComponentRead("unsafe", reason_ids=("replay_component_changed",))
    value, decode_reason = decode_canonical_json(data)
    if value is None or decode_reason is not None or type(value) is not dict:
        return _ComponentRead("corrupt", reason_ids=("replay_component_decode_invalid",))
    if entry.kind == "base":
        validated, reasons = validate_base_record(value, expected_locator=entry.locator)
    elif entry.kind == "segment":
        validated, reasons = validate_segment_record(value)
    elif entry.kind == "seal":
        validated, reasons = validate_seal_record(value)
    elif entry.kind == "completion":
        validated, reasons = validate_completion_marker(
            value, expected_locator=entry.locator
        )
    else:
        return _ComponentRead("unsafe", reason_ids=("replay_component_kind_invalid",))
    if validated is None or reasons:
        return _ComponentRead(
            _schema_state(reasons), reason_ids=_reasons(reasons)
        )
    return _ComponentRead(
        "ok", value=validated, digest=hashlib.sha256(data).hexdigest()
    )

def _capture_signature(
    config: RelayLMConfig,
    entries: Sequence[_EntrySnapshot],
) -> tuple[tuple[str, int, int, int, str], ...] | None:
    root_fd, reasons = _open_store_root(config.relaymem_slp_durable_finalization_root)
    if root_fd is None:
        return None
    rows: list[tuple[str, int, int, int, str]] = []
    try:
        for entry in sorted(entries, key=lambda item: item.name):
            if entry.kind == "isolation":
                digest = _read_raw_digest(root_fd, entry, _isolation_max_bytes())
                if digest is None:
                    return None
            else:
                read = _read_component(config, root_fd, entry)
                digest = read.digest
                if read.status != "ok" or digest is None:
                    return None
            rows.append((entry.name, entry.device, entry.inode, entry.size, digest))
    finally:
        os.close(root_fd)
    return tuple(rows)


def _read_raw_digest(root_fd: int, entry: _EntrySnapshot, maximum: int) -> str | None:
    try:
        before = os.stat(entry.name, dir_fd=root_fd, follow_symlinks=False)
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (entry.device, entry.inode, entry.size, entry.mtime_ns)
            or before.st_size > maximum
        ):
            return None
        fd = os.open(
            entry.name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or (info.st_dev, info.st_ino, info.st_size)
                != (entry.device, entry.inode, entry.size)
            ):
                return None
            data = _read_bounded(fd, maximum)
        finally:
            os.close(fd)
        after = os.stat(entry.name, dir_fd=root_fd, follow_symlinks=False)
        if (
            stat.S_ISLNK(after.st_mode)
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (entry.device, entry.inode, entry.size, entry.mtime_ns)
        ):
            return None
        return None if data is None else hashlib.sha256(data).hexdigest()
    except OSError:
        return None


def _parse_component_name(name: str) -> tuple[_ComponentKind, str, int | None] | None:
    for kind, pattern in (
        ("base", _BASE_RE),
        ("segment", _SEGMENT_RE),
        ("seal", _SEAL_RE),
        ("completion", _COMPLETION_RE),
    ):
        match = pattern.fullmatch(name)
        if match:
            sequence = int(match.group(2)) if kind == "segment" else None
            return kind, match.group(1), sequence
    isolation = _isolation_module()
    if isolation is not None and name.startswith(_PREFIX):
        candidate = name[len(_PREFIX): len(_PREFIX) + 64]
        if _DIGEST_RE.fullmatch(candidate):
            try:
                if isolation.isolation_filename(candidate) == name:
                    return "isolation", candidate, None
            except (AttributeError, TypeError, ValueError):
                return None
    return None


def _control_kind(name: str) -> Literal["lock", "temp"] | None:
    if _REPLAY_LOCK_RE.fullmatch(name):
        return "lock"
    if _PUBLICATION_TEMP_RE.fullmatch(name) or _COMPLETION_TEMP_RE.fullmatch(name):
        return "temp"
    if _isolation_module() is not None and re.fullmatch(
        r"^\.durable-finalization-isolation-[0-9a-f]{32}\.tmp$", name
    ):
        return "temp"
    return None

def _isolation_module():
    try:
        return importlib.import_module(
            ".relaymem_slp_durable_finalization_isolation", package=__package__
        )
    except ImportError:
        return None


def _read_isolation(config: RelayLMConfig, locator: str) -> str:
    module = _isolation_module()
    if module is None:
        return "unsupported"
    root_fd, reasons = _open_store_root(config.relaymem_slp_durable_finalization_root)
    if root_fd is None:
        return "unsafe"
    try:
        result = module.read_relaymem_slp_durable_finalization_isolation_fd(root_fd, locator)
    except Exception:
        return "unsafe"
    finally:
        os.close(root_fd)
    return "loaded" if getattr(result, "status", None) == "loaded" else "unsafe"


def _isolation_max_bytes() -> int:
    module = _isolation_module()
    value = getattr(module, "ISOLATION_MAX_BYTES", 16 * 1024) if module else 16 * 1024
    return value if type(value) is int and value > 0 else 16 * 1024


def _component_max_bytes(config: RelayLMConfig, kind: _ComponentKind) -> int:
    if kind == "segment":
        return config.relaymem_slp_durable_finalization_max_segment_bytes
    if kind == "completion":
        return _replay_impl._MAX_COMPLETION_BYTES
    if kind == "isolation":
        return _isolation_max_bytes()
    return config.relaymem_slp_durable_finalization_max_record_bytes


def _schema_state(reasons: Sequence[str]) -> _GroupState:
    return "unsupported" if any("schema" in reason or "revision" in reason for reason in reasons) else "corrupt"


def _entry_identity(entries: Sequence[_EntrySnapshot]) -> tuple[tuple[str, str, int | None, int, int, int, int], ...]:
    return tuple(
        (entry.name, entry.kind, entry.sequence, entry.device, entry.inode, entry.size, entry.mtime_ns)
        for entry in sorted(entries, key=lambda item: item.name)
    )


def _i1gc_mode(config: RelayLMConfig) -> Literal["disabled", "dry_run", "apply", "invalid"]:
    triple = (
        config.relaymem_slp_durable_finalization_enabled,
        config.relaymem_slp_durable_finalization_dry_run_only,
        config.relaymem_slp_durable_finalization_apply_enabled,
    )
    return {
        (False, True, False): "disabled",
        (True, True, False): "dry_run",
        (True, False, True): "apply",
    }.get(triple, "invalid")


def _delegate_mutation(delegate: object) -> bool:
    projection = getattr(delegate, "projection", None)
    return bool(
        projection
        and (
            getattr(projection, "source_created", False)
            or getattr(projection, "queue_created", False)
            or getattr(projection, "completion_created", False)
        )
    )


def _map_delegate_result(candidate: _GroupSnapshot, delegate: object) -> LaneOutcome:
    status = getattr(delegate, "status", None)
    projection = getattr(delegate, "projection", None)
    common = dict(
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=True,
        private=_PrivateReplayLaneDetails(candidate=candidate, delegate_result=delegate),
    )
    if status == "disabled":
        return _outcome(
            "dependency_unavailable",
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            retryable=False,
            terminal_for_candidate=False,
            reason_ids=("replay_delegate_disabled",),
            **common,
        )
    if status == "dry_run_ready":
        return _outcome(
            "delegated",
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            retryable=False,
            terminal_for_candidate=False,
            reason_ids=("replay_delegate_dry_run",),
            **common,
        )
    if status in {"completed", "exact_duplicate"}:
        return _outcome(
            "completed",
            mutation_may_have_occurred=True,
            terminal_for_candidate=True,
            reason_ids=("replay_delegate_completed",),
            **common,
        )
    if status == "already_complete":
        return _outcome(
            "already_complete",
            mutation_may_have_occurred=False,
            terminal_for_candidate=True,
            reason_ids=("replay_delegate_already_complete",),
            **common,
        )
    if status == "replay_lock_busy":
        return _outcome(
            "busy",
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            contention_observed=True,
            retryable=True,
            terminal_for_candidate=False,
            reason_ids=("replay_delegate_busy",),
            **common,
        )
    if status in {"record_missing", "not_replayable"}:
        return _outcome(
            "not_replayable",
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            retryable=True,
            terminal_for_candidate=False,
            reason_ids=("replay_delegate_not_replayable",),
            **common,
        )
    if status in {
        "corrupt", "schema_unsupported", "unsafe_path_or_type", "content_collision", "invariant_violation"
    }:
        return _outcome(
            "unsafe_state",
            mutation_may_have_occurred=_delegate_mutation(delegate),
            no_immediate_work=True,
            retryable=False,
            unsafe=True,
            terminal_for_candidate=False,
            reason_ids=("replay_delegate_unsafe",),
            **common,
        )
    mutation = _delegate_mutation(delegate)
    return _outcome(
        "failed",
        mutation_may_have_occurred=mutation,
        no_immediate_work=True,
        retryable=status in {
            "source_pending", "queue_pending", "completion_pending", "ambiguous", "failed"
        },
        terminal_for_candidate=False,
        reason_ids=("replay_delegate_pending" if status in {
            "source_pending", "queue_pending", "completion_pending", "ambiguous"
        } else "replay_delegate_failed",),
        **common,
    )


def _outcome(
    status: str,
    *,
    enabled: bool,
    attempted: bool = False,
    candidate_observed: bool = False,
    candidate_selected: bool = False,
    canonical_reread_performed: bool = False,
    delegation_attempted: bool = False,
    delegation_completed: bool = False,
    mutation_may_have_occurred: bool = False,
    no_immediate_work: bool = False,
    future_work_hint_present: bool = False,
    contention_observed: bool = False,
    retryable: bool = False,
    unsafe: bool = False,
    terminal_for_candidate: bool = False,
    reason_ids: Sequence[str] = (),
    private: object = None,
) -> LaneOutcome:
    return LaneOutcome(
        lane_kind="replay",
        status=status,
        enabled=enabled,
        attempted=attempted,
        candidate_observed=candidate_observed,
        candidate_selected=candidate_selected,
        canonical_reread_performed=canonical_reread_performed,
        delegation_attempted=delegation_attempted,
        delegation_completed=delegation_completed,
        mutation_may_have_occurred=mutation_may_have_occurred,
        no_immediate_work=no_immediate_work,
        future_work_hint_present=future_work_hint_present,
        contention_observed=contention_observed,
        retryable=retryable,
        unsafe=unsafe,
        terminal_for_candidate=terminal_for_candidate,
        bounded_reason_ids=_reasons(reason_ids),
        private_delegate_result=private,
    )


def _reasons(values: Sequence[str]) -> tuple[str, ...]:
    approved = []
    for value in values:
        token = value if type(value) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) else "replay_reason_invalid"
        if token not in approved:
            approved.append(token)
        if len(approved) >= _MAX_REASON_IDS:
            break
    return tuple(approved)


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = [
    "DEFAULT_DISCOVERY_MAX_ENTRIES",
    "MAX_DISCOVERY_MAX_ENTRIES",
    "REPLAY_LANE_NODE_NAME",
    "build_relaymem_slp_scheduler_replay_lane_node_result",
    "run_relaymem_slp_scheduler_replay_lane_once",
]
