"""One-record I1-GC durable-finalization replay and completion convergence."""
from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import secrets
import stat
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Literal

from ._relaymem_slp_protected_source_artifact import (
    artifact_filename,
    build_artifact,
    canonical_json_bytes as source_json_bytes,
    validate_artifact,
)
from ._relaymem_slp_protected_source_fs import (
    acquire_lock as acquire_source_lock,
    open_store_root as open_source_root,
    read_artifact,
    release_lock as release_source_lock,
)
from .config import RelayLMConfig
from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .relaymem_slp_durable_enqueue import (
    RelayMEMSLPDurableEnqueueResult,
    enqueue_relaymem_slp_durable_job,
)
from .relaymem_slp_durable_finalization_record import (
    RECORD_REVISION,
    RECORD_SCHEMA,
    RelayMEMSLPDurableFinalizationEvidence,
    canonical_json_bytes,
    decode_canonical_json,
    validate_finalized_source_mapping,
)
from .relaymem_slp_durable_finalization_store import (
    RelayMEMSLPDurableFinalizationStore,
    _open_store_root,
    _read_bounded,
    _rename_noreplace,
    _write_all,
)
from .relaymem_slp_durable_runtime_enqueue import (
    RelayMEMSLPDurableRuntimeEnqueueResult,
)
from .relaymem_slp_finalized_turn_source import (
    FINALIZED_TURN_SOURCE_SCHEMA,
    RelayMEMSLPFinalizedTurnSource,
    RelayMEMSLPFinalizedTurnSourceResult,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
    RelayMEMSLPProtectedSourceStoreResult,
)
from .relaymem_slp_queue_record import TERMINAL_STATES, dedupe
from .relaymem_slp_runtime_enqueue import (
    RelayMEMSLPRuntimeEnqueueResult,
    apply_relaymem_slp_runtime_enqueue,
    prepare_relaymem_slp_runtime_enqueue,
)

COMPLETION_SCHEMA = "relaymem.slp_durable_finalization_completion.v0"
COMPLETION_REVISION = 0
REPLAY_PROJECTION_SCHEMA = "relaymem.slp_durable_finalization_replay_projection.v0"
COMPLETION_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_included", "record_kind",
    "record_revision", "locator_digest", "sealed_record_schema",
    "sealed_record_revision", "seal_digest", "durable_job_digest",
    "protected_source_integrity_digest", "completion_digest",
})
_COMPLETION_PREFIX = "durable-finalization-completion-v0-"
_LOCK_PREFIX = ".durable-finalization-replay-v0-"
_MAX_COMPLETION_BYTES = 16 * 1024
_MAX_REASONS = 32

ReplayStatus = Literal[
    "disabled", "dry_run_ready", "invalid_input", "record_missing",
    "not_replayable", "already_complete", "replay_lock_busy",
    "source_pending", "queue_pending", "completion_pending", "completed",
    "exact_duplicate", "content_collision", "corrupt", "schema_unsupported",
    "unsafe_path_or_type", "invariant_violation", "blocked", "ambiguous",
    "failed",
]
FaultStage = Literal[
    "none", "after_lock_before_reread", "after_source_commit_before_queue",
    "after_queue_commit_before_completion", "during_queue_outcome_ambiguity",
    "during_completion_publish", "after_completion_publish_before_return",
]
FaultInjector = Callable[[str], None]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationReplayProjection:
    status: ReplayStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    record_present: bool = False
    sealed: bool = False
    replayable: bool = False
    source_present: bool = False
    queue_present: bool = False
    queue_terminal: bool = False
    completion_present: bool = False
    source_created: bool = False
    queue_created: bool = False
    completion_created: bool = False
    exact_duplicate: bool = False
    lock_acquired: bool = False
    failure_stage: FaultStage = "none"
    reason_ids: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationReplayProjection("
            f"status={self.status!r}, sealed={self.sealed!r}, "
            f"complete={self.completion_present!r}, protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": REPLAY_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "locator_value_included": False,
            "digest_values_included": False,
            "path_values_included": False,
            "timestamp_values_included": False,
            "lease_token_included": False,
            "exception_text_included": False,
            "nested_protected_result_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "record_present": self.record_present,
            "sealed": self.sealed,
            "replayable": self.replayable,
            "source_present": self.source_present,
            "queue_present": self.queue_present,
            "queue_terminal": self.queue_terminal,
            "completion_present": self.completion_present,
            "source_created": self.source_created,
            "queue_created": self.queue_created,
            "completion_created": self.completion_created,
            "exact_duplicate": self.exact_duplicate,
            "lock_acquired": self.lock_acquired,
            "failure_stage": self.failure_stage,
            "worker_invoked": False,
            "b3_transition_performed": False,
            "c2_invoked": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "cleanup_performed": False,
            "reason_ids": list(self.reason_ids),
        }


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationReplayResult:
    status: ReplayStatus
    projection: RelayMEMSLPDurableFinalizationReplayProjection
    finalized_turn_source_result: RelayMEMSLPFinalizedTurnSourceResult | None = field(
        default=None, repr=False, compare=False
    )
    runtime_preparation: RelayMEMSLPRuntimeEnqueueResult | None = field(
        default=None, repr=False, compare=False
    )
    source_store_result: RelayMEMSLPProtectedSourceStoreResult | None = field(
        default=None, repr=False, compare=False
    )
    queue_result: RelayMEMSLPDurableEnqueueResult | None = field(
        default=None, repr=False, compare=False
    )
    durable_runtime_result: RelayMEMSLPDurableRuntimeEnqueueResult | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationReplayResult("
            f"status={self.status!r}, sealed={self.projection.sealed!r}, "
            f"complete={self.projection.completion_present!r}, "
            "protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return self.projection.to_log_dict()


@dataclass
class _State:
    enabled: bool
    dry: bool
    apply: bool
    record_present: bool = False
    sealed: bool = False
    replayable: bool = False
    source_present: bool = False
    queue_present: bool = False
    queue_terminal: bool = False
    completion_present: bool = False
    source_created: bool = False
    queue_created: bool = False
    completion_created: bool = False
    exact_duplicate: bool = False
    lock_acquired: bool = False
    failure_stage: FaultStage = "none"
    source_result: RelayMEMSLPFinalizedTurnSourceResult | None = None
    preparation: RelayMEMSLPRuntimeEnqueueResult | None = None
    source_store_result: RelayMEMSLPProtectedSourceStoreResult | None = None
    queue_result: RelayMEMSLPDurableEnqueueResult | None = None
    durable_runtime_result: RelayMEMSLPDurableRuntimeEnqueueResult | None = None


@dataclass(frozen=True)
class _Inspect:
    kind: Literal["absent", "exact", "created", "collision", "corrupt", "retryable"]
    reasons: tuple[str, ...] = ()
    digest: str | None = None


@dataclass
class _Fence:
    root_fd: int
    lock_fd: int

    def close(self) -> None:
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self.lock_fd)
        os.close(self.root_fd)


def replay_relaymem_slp_durable_finalization_record(
    config: object,
    *,
    locator_digest: object,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    fault_injector: FaultInjector | None = None,
) -> RelayMEMSLPDurableFinalizationReplayResult:
    """Converge one caller-selected locator without discovery, retry, or execution."""
    if type(config) is not RelayLMConfig:
        return _finish(_State(False, True, False), "invalid_input", (
            "exact_relaylm_config_required",
        ))
    cfg = config
    state = _State(
        cfg.relaymem_slp_durable_finalization_enabled,
        cfg.relaymem_slp_durable_finalization_dry_run_only,
        cfg.relaymem_slp_durable_finalization_apply_enabled,
    )
    if not state.enabled:
        return _finish(state, "disabled")
    if not _digest(locator_digest):
        return _finish(state, "invalid_input", ("durable_finalization_locator_invalid",))
    if fault_injector is not None and not callable(fault_injector):
        return _finish(state, "invalid_input", (
            "durable_finalization_replay_fault_injector_invalid",
        ))
    gates = _gate_reasons(cfg)
    if gates:
        return _finish(state, "blocked", gates)
    store = _finalization_store(cfg)
    if store is None:
        return _finish(state, "invalid_input", (
            "durable_finalization_store_config_invalid",
        ))
    locator = str(locator_digest)
    if state.dry:
        return _converge(cfg, locator, store, registry, state, fault_injector)
    fence, busy, reasons = _acquire_fence(
        cfg.relaymem_slp_durable_finalization_root, locator
    )
    if fence is None:
        return _finish(
            state,
            "replay_lock_busy" if busy else _reason_status(reasons, "failed"),
            reasons,
        )
    state.lock_acquired = True
    try:
        injected = _fault(fault_injector, "after_lock_before_reread")
        if injected:
            state.failure_stage = "after_lock_before_reread"
            return _finish(state, "failed", (injected,))
        return _converge(cfg, locator, store, registry, state, fault_injector)
    finally:
        fence.close()


def _converge(
    cfg: RelayLMConfig,
    locator: str,
    store: RelayMEMSLPDurableFinalizationStore,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    state: _State,
    fault_injector: FaultInjector | None,
) -> RelayMEMSLPDurableFinalizationReplayResult:
    loaded = store.read_evidence(locator)
    state.record_present = loaded.record_present
    state.sealed = loaded.sealed
    state.replayable = loaded.replayable
    if loaded.status == "missing":
        return _finish(state, "record_missing", loaded.blocked_reasons)
    if loaded.status != "loaded" or loaded.evidence is None:
        return _finish(state, _store_status(loaded.status, loaded.blocked_reasons), loaded.blocked_reasons)
    if loaded.evidence.seal is None:
        return _finish(state, "not_replayable", ("durable_finalization_seal_missing",))
    state.record_present = state.sealed = state.replayable = True

    source_result, reasons = _reconstruct_source(loaded.evidence)
    if source_result is None:
        return _finish(state, _reason_status(reasons, "corrupt"), reasons)
    state.source_result = source_result
    preparation = prepare_relaymem_slp_runtime_enqueue(source_result)
    state.preparation = preparation
    reasons = _verify_identity(loaded.evidence, preparation)
    if reasons:
        return _finish(state, "invariant_violation", reasons)
    dispatch = preparation.dispatch_result
    source = source_result.source
    payload = preparation.protected_source_payload
    if (
        preparation.status != "dry_run_ready" or dispatch is None
        or dispatch.durable_job is None or source is None or type(payload) is not dict
    ):
        return _finish(state, "blocked", preparation.blocked_reasons or (
            "durable_finalization_replay_preparation_invalid",
        ))
    source_store = _source_store(cfg)
    if source_store is None:
        return _finish(state, "invalid_input", (
            "exact_durable_protected_source_store_required",
        ))

    source_before = _inspect_source(
        source_store, payload, dispatch.durable_job, source.character_id
    )
    if source_before.kind not in {"absent", "exact"}:
        return _finish(state, _inspect_status(source_before, "source_pending"), source_before.reasons)
    state.source_present = source_before.kind == "exact"
    queue_before = _inspect_queue(preparation, cfg.relaymem_slp_queue_root)
    state.queue_result = queue_before
    queue_kind = _queue_kind(queue_before)
    if queue_kind not in {"absent", "exact"}:
        return _finish(state, _queue_status(queue_kind), queue_before.blocked_reasons)
    state.queue_present = queue_kind == "exact"
    state.queue_terminal = _terminal(queue_before)
    if state.queue_present and not state.source_present:
        return _finish(state, "invariant_violation", (
            "durable_finalization_queue_without_protected_source",
        ))

    expected_digest = source_before.digest or _source_digest(
        payload, dispatch.durable_job, source.character_id
    )
    marker = _completion_marker(locator, loaded.evidence.seal, preparation, expected_digest)
    completion = _read_completion(
        cfg.relaymem_slp_durable_finalization_root, locator, marker
    )
    if completion.kind not in {"absent", "exact"}:
        return _finish(state, _inspect_status(completion, "completion_pending"), completion.reasons)
    state.completion_present = completion.kind == "exact"
    if state.completion_present:
        if not state.source_present or not state.queue_present:
            return _finish(state, "invariant_violation", (
                "durable_finalization_completion_without_downstream_proof",
            ))
        state.exact_duplicate = True
        state.durable_runtime_result = _duplicate_runtime(preparation)
        return _finish(state, "already_complete")
    if state.dry:
        return _finish(state, "dry_run_ready")
    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _finish(state, "invalid_input", ("exact_source_registry_required",))

    persisted = source_store.persist(
        source_payload=payload,
        durable_job=dispatch.durable_job,
        character_id=source.character_id,
    )
    state.source_store_result = persisted
    state.source_created = persisted.status == "published_new"
    source_after = _inspect_source(
        source_store, payload, dispatch.durable_job, source.character_id
    )
    state.source_present = source_after.kind == "exact"
    if not state.source_present:
        return _finish(
            state,
            _inspect_status(source_after, "source_pending"),
            dedupe((*persisted.blocked_reasons, *source_after.reasons)),
        )
    injected = _fault(fault_injector, "after_source_commit_before_queue")
    if injected:
        state.failure_stage = "after_source_commit_before_queue"
        return _finish(state, "queue_pending", (injected,))

    applied = apply_relaymem_slp_runtime_enqueue(
        source_result,
        registry=registry,
        queue_root=cfg.relaymem_slp_queue_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        prepared_result=preparation,
    )
    queue_apply = applied.enqueue_result
    state.queue_created = bool(queue_apply and queue_apply.status == "enqueued_new")
    if queue_apply is not None and queue_apply.status == "write_failed":
        injected = _fault(fault_injector, "during_queue_outcome_ambiguity")
        if injected:
            state.failure_stage = "during_queue_outcome_ambiguity"
            return _finish(state, "ambiguous", (injected,))
    queue_after = _inspect_queue(preparation, cfg.relaymem_slp_queue_root)
    state.queue_result = queue_after
    queue_kind = _queue_kind(queue_after)
    state.queue_present = queue_kind == "exact"
    state.queue_terminal = _terminal(queue_after)
    source_final = _inspect_source(
        source_store, payload, dispatch.durable_job, source.character_id
    )
    state.source_present = source_final.kind == "exact"
    state.durable_runtime_result = _wrap_runtime(applied, persisted, state.queue_present)
    if not state.source_present:
        return _finish(state, "invariant_violation", dedupe((
            *source_final.reasons, "durable_finalization_source_before_queue_lost",
        )))
    if not state.queue_present:
        return _finish(
            state,
            _queue_status(queue_kind),
            queue_after.blocked_reasons or applied.blocked_reasons or (
                "durable_finalization_queue_canonical_reread_failed",
            ),
        )
    injected = _fault(fault_injector, "after_queue_commit_before_completion")
    if injected:
        state.failure_stage = "after_queue_commit_before_completion"
        return _finish(state, "completion_pending", (injected,))

    marker = _completion_marker(
        locator, loaded.evidence.seal, preparation, str(source_final.digest)
    )
    injected = _fault(fault_injector, "during_completion_publish")
    if injected:
        state.failure_stage = "during_completion_publish"
        return _finish(state, "completion_pending", (injected,))
    published = _publish_completion(
        cfg.relaymem_slp_durable_finalization_root, locator, marker
    )
    if published.kind not in {"created", "exact"}:
        status = "content_collision" if published.kind == "collision" else (
            "ambiguous" if published.kind == "retryable" else "completion_pending"
        )
        return _finish(state, status, published.reasons)
    state.completion_created = published.kind == "created"
    state.exact_duplicate = published.kind == "exact"
    reread = _read_completion(
        cfg.relaymem_slp_durable_finalization_root, locator, marker
    )
    state.completion_present = reread.kind == "exact"
    if not state.completion_present:
        return _finish(state, _inspect_status(reread, "completion_pending"), reread.reasons or (
            "durable_finalization_completion_canonical_reread_failed",
        ))
    injected = _fault(fault_injector, "after_completion_publish_before_return")
    if injected:
        state.failure_stage = "after_completion_publish_before_return"
        return _finish(state, "completed", (injected,))
    return _finish(state, "exact_duplicate" if state.exact_duplicate else "completed")


def build_relaymem_slp_durable_finalization_replay_node_result(
    result: RelayMEMSLPDurableFinalizationReplayResult,
) -> PipelineNodeResult:
    status = {
        "disabled": "skipped", "record_missing": "skipped",
        "not_replayable": "blocked", "replay_lock_busy": "blocked",
        "content_collision": "blocked", "corrupt": "blocked",
        "schema_unsupported": "blocked", "unsafe_path_or_type": "blocked",
        "invariant_violation": "blocked", "blocked": "blocked",
        "invalid_input": "failed", "ambiguous": "failed", "failed": "failed",
    }.get(result.status, "diagnostic_only")
    return build_pipeline_node_result(
        node_name="relaymem_slp_durable_finalization_replay",
        status=status,
        decision=result.status,
        blocked_reasons=result.projection.reason_ids,
        diagnostics=result.to_log_dict(),
        artifacts=[{
            "artifact_name": "relaymem_slp_durable_finalization_completion",
            "schema_version": COMPLETION_SCHEMA,
            "present": result.projection.completion_present,
            "content_free": True,
            "runtime_private": True,
            "marker_omitted": True,
            "identifier_values_included": False,
            "digest_values_included": False,
            "path_values_included": False,
            "worker_invoked": False,
            "b3_transition_performed": False,
            "writes_memory": False,
            "changes_visible_response": False,
        }],
    )


def completion_filename(locator_digest: str) -> str:
    if not _digest(locator_digest):
        raise ValueError("durable_finalization_locator_invalid")
    return f"{_COMPLETION_PREFIX}{locator_digest}.json"


def validate_completion_marker(
    value: object,
    *,
    expected_locator: str | None = None,
    expected: Mapping[str, object] | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("durable_finalization_completion_shape_invalid",)
    reasons: list[str] = []
    if len(value) != len(COMPLETION_FIELDS) or set(value) != COMPLETION_FIELDS:
        reasons.append("durable_finalization_completion_shape_mismatch")
    checks = {
        "schema_version": COMPLETION_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "record_kind": "completion",
        "record_revision": COMPLETION_REVISION,
        "sealed_record_schema": RECORD_SCHEMA,
        "sealed_record_revision": RECORD_REVISION,
    }
    for key, wanted in checks.items():
        if value.get(key) != wanted:
            reasons.append(f"durable_finalization_completion_{key}_mismatch")
    if not _digest(value.get("locator_digest")):
        reasons.append("durable_finalization_completion_locator_invalid")
    if expected_locator is not None and value.get("locator_digest") != expected_locator:
        reasons.append("durable_finalization_completion_locator_mismatch")
    for key in (
        "seal_digest", "durable_job_digest", "protected_source_integrity_digest"
    ):
        if not _digest(value.get(key)):
            reasons.append(f"durable_finalization_completion_{key}_invalid")
    if value.get("completion_digest") != _hash_without(value, "completion_digest"):
        reasons.append("durable_finalization_completion_digest_mismatch")
    if expected is not None:
        try:
            if canonical_json_bytes(value) != canonical_json_bytes(expected):
                reasons.append("durable_finalization_completion_identity_collision")
        except (TypeError, ValueError, RecursionError, OverflowError):
            reasons.append("durable_finalization_completion_compare_failed")
    return (dict(value), ()) if not reasons else (None, dedupe(tuple(reasons)))


def _gate_reasons(cfg: RelayLMConfig) -> tuple[str, ...]:
    reasons = []
    if cfg.relaymem_slp_durable_finalization_dry_run_only and cfg.relaymem_slp_durable_finalization_apply_enabled:
        reasons.append("durable_finalization_apply_enabled_in_dry_run")
    if not cfg.relaymem_slp_durable_finalization_dry_run_only and not cfg.relaymem_slp_durable_finalization_apply_enabled:
        reasons.append("durable_finalization_apply_gate_incomplete")
    if cfg.relaymem_slp_durable_finalization_apply_enabled and (
        not cfg.relaymem_slp_runtime_enqueue_enabled
        or cfg.relaymem_slp_runtime_enqueue_dry_run_only
        or not cfg.relaymem_slp_runtime_enqueue_apply_enabled
    ):
        reasons.append("durable_finalization_runtime_enqueue_apply_required")
    for value, reason in (
        (cfg.relaymem_slp_durable_finalization_root, "durable_finalization_root_invalid"),
        (cfg.relaymem_slp_protected_source_root, "protected_source_root_invalid"),
        (cfg.relaymem_slp_queue_root, "queue_root_invalid"),
    ):
        if type(value) is not str:
            reasons.append(reason)
    return dedupe(tuple(reasons))


def _finalization_store(cfg: RelayLMConfig) -> RelayMEMSLPDurableFinalizationStore | None:
    try:
        return RelayMEMSLPDurableFinalizationStore(
            str(cfg.relaymem_slp_durable_finalization_root),
            max_record_bytes=cfg.relaymem_slp_durable_finalization_max_record_bytes,
            max_segment_bytes=cfg.relaymem_slp_durable_finalization_max_segment_bytes,
            max_segment_count=cfg.relaymem_slp_durable_finalization_max_segment_count,
            max_record_count=cfg.relaymem_slp_durable_finalization_max_record_count,
            operation_timeout_ms=cfg.relaymem_slp_durable_finalization_publication_timeout_ms,
        )
    except (TypeError, ValueError):
        return None


def _source_store(cfg: RelayLMConfig) -> RelayMEMSLPDurableProtectedSourceStore | None:
    try:
        root = cfg.relaymem_slp_protected_source_root
        return None if type(root) is not str else RelayMEMSLPDurableProtectedSourceStore(
            root, max_artifact_bytes=cfg.relaymem_slp_protected_source_max_artifact_bytes
        )
    except (TypeError, ValueError):
        return None


def _reconstruct_source(
    evidence: RelayMEMSLPDurableFinalizationEvidence,
) -> tuple[RelayMEMSLPFinalizedTurnSourceResult | None, tuple[str, ...]]:
    seal = evidence.seal
    mapping = seal.get("finalized_turn_source") if type(seal) is dict else None
    reasons = validate_finalized_source_mapping(mapping)
    if reasons or type(mapping) is not dict:
        return None, reasons or ("durable_finalization_finalized_source_invalid",)
    try:
        messages = mapping["governed_messages"]
        if type(messages) is not list:
            raise TypeError
        source = RelayMEMSLPFinalizedTurnSource(
            schema_version=str(mapping["schema_version"]),
            character_id=str(mapping["character_id"]),
            run_id=str(mapping["run_id"]),
            turn_index=int(mapping["turn_index"]),
            session_id=None if mapping["session_id"] is None else str(mapping["session_id"]),
            namespace=str(mapping["namespace"]),
            source_event_kind=str(mapping["source_event_kind"]),
            source_count=int(mapping["source_count"]),
            persistence_policy_status=str(mapping["persistence_policy_status"]),
            source_lineage_artifact=deepcopy(dict(mapping["source_lineage_artifact"])),
            relayscn_scene_policy_artifact=deepcopy(dict(mapping["relayscn_scene_policy_artifact"])),
            relayemo_artifact=None if mapping["relayemo_artifact"] is None else deepcopy(dict(mapping["relayemo_artifact"])),
            governed_messages=tuple(deepcopy(dict(item)) for item in messages),
            governed_experience_artifact=deepcopy(dict(mapping["governed_experience_artifact"])),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, ("durable_finalization_finalized_source_reconstruction_failed",)
    if source.schema_version != FINALIZED_TURN_SOURCE_SCHEMA:
        return None, ("durable_finalization_finalized_source_schema_mismatch",)
    return RelayMEMSLPFinalizedTurnSourceResult(
        status="ready", enabled=True, response_finalized=True, source_ready=True,
        blocked_reasons=(), source=source,
    ), ()


def _verify_identity(
    evidence: RelayMEMSLPDurableFinalizationEvidence,
    preparation: RelayMEMSLPRuntimeEnqueueResult,
) -> tuple[str, ...]:
    seal = evidence.seal
    dispatch = preparation.dispatch_result
    if type(seal) is not dict or dispatch is None or dispatch.durable_job is None:
        return preparation.blocked_reasons or ("durable_finalization_b1_reconstruction_failed",)
    reasons = []
    try:
        if canonical_json_bytes(dispatch.durable_job.to_runtime_dict()) != canonical_json_bytes(seal.get("durable_job")):
            reasons.append("durable_finalization_rebuilt_job_identity_mismatch")
        if dispatch.durable_job.job_id != seal.get("job_id"):
            reasons.append("durable_finalization_rebuilt_job_id_mismatch")
        if dispatch.durable_job.dispatch_idempotency_key != seal.get("dispatch_idempotency_key"):
            reasons.append("durable_finalization_rebuilt_dispatch_identity_mismatch")
    except (TypeError, ValueError, RecursionError, OverflowError):
        reasons.append("durable_finalization_rebuilt_identity_compare_failed")
    return dedupe(tuple(reasons))


def _inspect_source(
    store: RelayMEMSLPDurableProtectedSourceStore,
    payload: dict[str, object],
    durable_job: object,
    character_id: str,
) -> _Inspect:
    try:
        runtime = durable_job.to_runtime_dict()
        expected, wanted_digest = build_artifact(
            payload,
            job_id=str(runtime["job_id"]),
            dispatch_key=str(runtime["dispatch_idempotency_key"]),
            character_id=character_id,
        )
        name = artifact_filename(str(runtime["job_id"]), str(runtime["dispatch_idempotency_key"]))
    except (AttributeError, KeyError, TypeError, ValueError):
        return _Inspect("corrupt", ("durable_finalization_protected_source_identity_invalid",))
    root_fd, reasons = open_source_root(store._root_path)
    if root_fd is None:
        return _Inspect("retryable", reasons)
    try:
        lock_reason = acquire_source_lock(root_fd, exclusive=False)
        if lock_reason:
            return _Inspect("retryable", (lock_reason,))
        artifact, status, reasons = read_artifact(
            root_fd, name, max_bytes=store.max_artifact_bytes
        )
        if status == "missing":
            return _Inspect("absent")
        if status == "retryable":
            return _Inspect("retryable", reasons)
        if status != "ok" or artifact is None:
            return _Inspect("corrupt", reasons)
        _, digest, reasons = validate_artifact(
            artifact, expected_record=runtime, expected_character_id=character_id
        )
        if reasons or digest is None:
            return _Inspect("corrupt", reasons)
        if source_json_bytes(artifact) != source_json_bytes(expected) or digest != wanted_digest:
            return _Inspect("collision", (
                "durable_finalization_protected_source_content_collision",
            ), digest)
        return _Inspect("exact", digest=digest)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return _Inspect("corrupt", ("durable_finalization_protected_source_compare_failed",))
    finally:
        release_source_lock(root_fd)
        os.close(root_fd)


def _inspect_queue(
    preparation: RelayMEMSLPRuntimeEnqueueResult,
    root: str | None,
) -> RelayMEMSLPDurableEnqueueResult:
    if preparation.dispatch_result is None:
        raise RuntimeError("durable_finalization_dispatch_unavailable")
    return enqueue_relaymem_slp_durable_job(
        preparation.dispatch_result,
        queue_root=root,
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
    )


def _queue_kind(result: RelayMEMSLPDurableEnqueueResult) -> str:
    return {
        "dry_run_ready": "absent",
        "duplicate_existing": "exact",
        "blocked_collision": "collision",
        "blocked_corrupt": "corrupt",
        "invalid_input": "corrupt",
        "blocked": "corrupt",
    }.get(result.status, "retryable")


def _terminal(result: RelayMEMSLPDurableEnqueueResult | None) -> bool:
    return bool(
        result and type(result.durable_record) is dict
        and result.durable_record.get("state") in TERMINAL_STATES
    )


def _source_digest(payload: dict[str, object], durable_job: object, character_id: str) -> str:
    runtime = durable_job.to_runtime_dict()
    return build_artifact(
        payload,
        job_id=str(runtime["job_id"]),
        dispatch_key=str(runtime["dispatch_idempotency_key"]),
        character_id=character_id,
    )[1]


def _completion_marker(
    locator: str,
    seal: Mapping[str, object],
    preparation: RelayMEMSLPRuntimeEnqueueResult,
    source_digest: str,
) -> dict[str, object]:
    dispatch = preparation.dispatch_result
    if dispatch is None or dispatch.durable_job is None:
        raise ValueError("durable_finalization_dispatch_unavailable")
    marker: dict[str, object] = {
        "schema_version": COMPLETION_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "record_kind": "completion",
        "record_revision": COMPLETION_REVISION,
        "locator_digest": locator,
        "sealed_record_schema": seal.get("schema_version"),
        "sealed_record_revision": seal.get("record_revision"),
        "seal_digest": seal.get("seal_digest"),
        "durable_job_digest": hashlib.sha256(
            canonical_json_bytes(dispatch.durable_job.to_runtime_dict())
        ).hexdigest(),
        "protected_source_integrity_digest": source_digest,
    }
    marker["completion_digest"] = _hash_without(marker, "completion_digest")
    value, reasons = validate_completion_marker(marker, expected_locator=locator)
    if value is None or reasons:
        raise ValueError(reasons[0] if reasons else "durable_finalization_completion_invalid")
    return value


def _read_completion(root: str, locator: str, expected: Mapping[str, object]) -> _Inspect:
    root_fd, reasons = _open_store_root(root)
    if root_fd is None:
        return _Inspect("retryable", reasons)
    try:
        return _read_completion_fd(root_fd, locator, expected)
    finally:
        os.close(root_fd)


def _read_completion_fd(root_fd: int, locator: str, expected: Mapping[str, object]) -> _Inspect:
    name = completion_filename(locator)
    try:
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _Inspect("absent")
    except OSError:
        return _Inspect("retryable", ("durable_finalization_completion_unreadable",))
    if stat.S_ISLNK(before.st_mode):
        return _Inspect("corrupt", ("durable_finalization_completion_symlink_blocked",))
    if not stat.S_ISREG(before.st_mode):
        return _Inspect("corrupt", ("durable_finalization_completion_unsafe_file_type",))
    if before.st_nlink != 1:
        return _Inspect("corrupt", ("durable_finalization_completion_hardlink_invalid",))
    if before.st_size > _MAX_COMPLETION_BYTES:
        return _Inspect("corrupt", ("durable_finalization_completion_size_exceeded",))
    try:
        fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except FileNotFoundError:
        return _Inspect("absent")
    except OSError:
        return _Inspect("retryable", ("durable_finalization_completion_unreadable",))
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
        ):
            return _Inspect("corrupt", ("durable_finalization_completion_changed_during_read",))
        data = _read_bounded(fd, _MAX_COMPLETION_BYTES)
    finally:
        os.close(fd)
    if data is None:
        return _Inspect("corrupt", ("durable_finalization_completion_size_exceeded",))
    try:
        after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return _Inspect("corrupt", ("durable_finalization_completion_changed_during_read",))
    if (
        stat.S_ISLNK(after.st_mode) or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1 or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        or after.st_size != info.st_size
    ):
        return _Inspect("corrupt", ("durable_finalization_completion_changed_during_read",))
    value, reason = decode_canonical_json(data)
    if value is None or reason:
        return _Inspect("corrupt", (reason or "durable_finalization_completion_decode_failed",))
    _, reasons = validate_completion_marker(
        value, expected_locator=locator, expected=expected
    )
    if reasons:
        return _Inspect(
            "collision" if "durable_finalization_completion_identity_collision" in reasons else "corrupt",
            reasons,
        )
    return _Inspect("exact")


def _publish_completion(root: str, locator: str, expected: Mapping[str, object]) -> _Inspect:
    data = canonical_json_bytes(expected)
    if len(data) > _MAX_COMPLETION_BYTES:
        return _Inspect("corrupt", ("durable_finalization_completion_size_exceeded",))
    root_fd, reasons = _open_store_root(root)
    if root_fd is None:
        return _Inspect("retryable", reasons)
    temp = f".durable-finalization-completion-{secrets.token_hex(16)}.tmp"
    temp_exists = False
    try:
        current = _read_completion_fd(root_fd, locator, expected)
        if current.kind == "exact":
            return current
        if current.kind != "absent":
            return current
        try:
            fd = os.open(
                temp,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=root_fd,
            )
            temp_exists = True
        except OSError:
            return _Inspect("retryable", ("durable_finalization_completion_temp_create_failed",))
        try:
            _write_all(fd, data)
            os.fsync(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != len(data):
                raise OSError(errno.EIO, "unsafe completion temp")
        except OSError:
            return _Inspect("retryable", ("durable_finalization_completion_temp_write_failed",))
        finally:
            os.close(fd)
        outcome = _rename_noreplace(root_fd, temp, completion_filename(locator))
        if outcome == "published":
            temp_exists = False
            try:
                os.fsync(root_fd)
            except OSError:
                return _Inspect("retryable", (
                    "durable_finalization_completion_directory_fsync_ambiguous",
                ))
            reread = _read_completion_fd(root_fd, locator, expected)
            return _Inspect("created") if reread.kind == "exact" else reread
        if outcome == "exists":
            return _read_completion_fd(root_fd, locator, expected)
        reread = _read_completion_fd(root_fd, locator, expected)
        if reread.kind == "exact":
            try:
                os.fsync(root_fd)
            except OSError:
                return _Inspect("retryable", (
                    "durable_finalization_completion_directory_fsync_ambiguous",
                ))
            return reread
        return _Inspect("retryable", reread.reasons or (
            "durable_finalization_completion_atomic_publish_ambiguous",
        ))
    finally:
        if temp_exists:
            try:
                os.unlink(temp, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                pass
        os.close(root_fd)


def _acquire_fence(root: str, locator: str) -> tuple[_Fence | None, bool, tuple[str, ...]]:
    root_fd, reasons = _open_store_root(root)
    if root_fd is None:
        return None, False, reasons
    name = f"{_LOCK_PREFIX}{locator}.lock"
    try:
        try:
            before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            before = None
        if before is not None and (
            stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            os.close(root_fd)
            return None, False, ("durable_finalization_replay_lock_unsafe_file_type",)
        lock_fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=root_fd,
        )
        info = os.fstat(lock_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (
            before is not None and (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
        ):
            os.close(lock_fd)
            os.close(root_fd)
            return None, False, ("durable_finalization_replay_lock_unsafe_file_type",)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            os.close(root_fd)
            return None, True, ("durable_finalization_replay_lock_busy",)
        if before is None:
            os.fsync(lock_fd)
            os.fsync(root_fd)
        return _Fence(root_fd, lock_fd), False, ()
    except OSError:
        try:
            os.close(root_fd)
        except OSError:
            pass
        return None, False, ("durable_finalization_replay_lock_failed",)


def _fault(injector: FaultInjector | None, stage: str) -> str | None:
    if injector is None:
        return None
    try:
        injector(stage)
    except BaseException:
        return f"durable_finalization_replay_fault_injected_{stage}"
    return None


def _wrap_runtime(
    applied: RelayMEMSLPRuntimeEnqueueResult,
    persisted: RelayMEMSLPProtectedSourceStoreResult,
    restart_complete: bool,
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    enqueue = applied.enqueue_result
    if enqueue is not None and enqueue.status == "enqueued_new":
        status = "enqueued"
    elif applied.status == "source_retention_failed" and enqueue is not None and enqueue.status == "duplicate_existing":
        status = "process_local_cache_degraded"
    elif enqueue is not None and enqueue.status == "duplicate_existing":
        status = "duplicate_existing"
    else:
        status = "enqueue_failed"
    reasons = applied.blocked_reasons if status in {
        "process_local_cache_degraded", "enqueue_failed"
    } else ()
    return RelayMEMSLPDurableRuntimeEnqueueResult(
        status=status,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        restart_complete=restart_complete,
        source_persisted_before_enqueue=True,
        blocked_reasons=dedupe(tuple(reasons)),
        runtime_result=applied,
        source_store_result=persisted,
        orphan_cleanup_result=None,
    )


def _duplicate_runtime(
    preparation: RelayMEMSLPRuntimeEnqueueResult,
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    runtime = replace(
        preparation,
        status="duplicate_existing",
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        failure_stage="none",
        blocked_reasons=(),
        source_scope=None,
    )
    return RelayMEMSLPDurableRuntimeEnqueueResult(
        status="duplicate_existing",
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        restart_complete=True,
        source_persisted_before_enqueue=True,
        blocked_reasons=(),
        runtime_result=runtime,
        source_store_result=None,
        orphan_cleanup_result=None,
    )


def _finish(
    state: _State,
    status: ReplayStatus,
    reasons: Sequence[str] = (),
) -> RelayMEMSLPDurableFinalizationReplayResult:
    projection = RelayMEMSLPDurableFinalizationReplayProjection(
        status=status,
        enabled=state.enabled,
        dry_run_only=state.dry,
        apply_enabled=state.apply,
        record_present=state.record_present,
        sealed=state.sealed,
        replayable=state.replayable,
        source_present=state.source_present,
        queue_present=state.queue_present,
        queue_terminal=state.queue_terminal,
        completion_present=state.completion_present,
        source_created=state.source_created,
        queue_created=state.queue_created,
        completion_created=state.completion_created,
        exact_duplicate=state.exact_duplicate,
        lock_acquired=state.lock_acquired,
        failure_stage=state.failure_stage,
        reason_ids=dedupe(tuple(reasons))[:_MAX_REASONS],
    )
    return RelayMEMSLPDurableFinalizationReplayResult(
        status=status,
        projection=projection,
        finalized_turn_source_result=state.source_result,
        runtime_preparation=state.preparation,
        source_store_result=state.source_store_result,
        queue_result=state.queue_result,
        durable_runtime_result=state.durable_runtime_result,
    )


def _inspect_status(value: _Inspect, pending: ReplayStatus) -> ReplayStatus:
    return {
        "absent": pending,
        "collision": "content_collision",
        "corrupt": _reason_status(value.reasons, "corrupt"),
        "retryable": "ambiguous",
    }.get(value.kind, "failed")


def _queue_status(kind: str) -> ReplayStatus:
    return {
        "absent": "queue_pending",
        "collision": "content_collision",
        "corrupt": "corrupt",
        "retryable": "ambiguous",
    }.get(kind, "failed")


def _store_status(status: str, reasons: Sequence[str]) -> ReplayStatus:
    return {
        "collision": "content_collision",
        "corrupt": _reason_status(reasons, "corrupt"),
        "ambiguous": "ambiguous",
        "blocked": _reason_status(reasons, "blocked"),
    }.get(status, "failed")


def _reason_status(reasons: Sequence[str], fallback: ReplayStatus) -> ReplayStatus:
    text = " ".join(reasons)
    if "schema" in text:
        return "schema_unsupported"
    if any(word in text for word in (
        "symlink", "hardlink", "unsafe_file", "not_regular", "path"
    )):
        return "unsafe_path_or_type"
    return fallback


def _hash_without(value: Mapping[str, object], key: str) -> str:
    try:
        return hashlib.sha256(canonical_json_bytes({
            field: item for field, item in value.items() if field != key
        })).hexdigest()
    except (TypeError, ValueError, RecursionError, OverflowError):
        return ""


def _digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


__all__ = [
    "COMPLETION_FIELDS", "COMPLETION_REVISION", "COMPLETION_SCHEMA",
    "REPLAY_PROJECTION_SCHEMA",
    "RelayMEMSLPDurableFinalizationReplayProjection",
    "RelayMEMSLPDurableFinalizationReplayResult",
    "build_relaymem_slp_durable_finalization_replay_node_result",
    "completion_filename", "replay_relaymem_slp_durable_finalization_record",
    "validate_completion_marker",
]
