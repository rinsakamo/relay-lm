"""I1-GB pre-release durable-finalization publication orchestration."""
from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Literal

from .config import RelayLMConfig
from .pipeline_context import PipelineContext
from .relaymem_slp_durable_finalization_record import (
    RelayMEMSLPDurableFinalizationProjection,
    ZERO_DIGEST,
    build_base_record,
    build_seal_record,
    build_segment_record,
    canonical_json_bytes,
)
from .relaymem_slp_durable_finalization_store import (
    RelayMEMSLPDurableFinalizationStore,
    RelayMEMSLPDurableFinalizationStoreResult,
)
from .relaymem_slp_finalized_turn_source import (
    RelayMEMSLPFinalizedTurnSourceResult,
    build_relaymem_slp_finalized_turn_source,
)
from .relaymem_slp_queue_record import dedupe, is_token
from .relaymem_slp_runtime_enqueue import (
    RelayMEMSLPRuntimeEnqueueResult,
    prepare_relaymem_slp_runtime_enqueue,
)

PublicationStatus = Literal[
    "disabled",
    "dry_run_ready",
    "published",
    "duplicate_existing",
    "blocked",
    "failed",
]
_MAX_REASONS = 32


class RelayMEMSLPDurableFinalizationError(RuntimeError):
    """Content-free bounded failure raised before unprotected response release."""

    def __init__(self, reason_id: str) -> None:
        safe = (
            reason_id
            if _ascii_token(reason_id)
            else "durable_finalization_publication_failed"
        )
        self.reason_id = safe
        super().__init__(safe)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationError("
            f"reason_id={self.reason_id!r}, protected_content_omitted=True)"
        )


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationPreparedTurn:
    source_result: RelayMEMSLPFinalizedTurnSourceResult = field(
        repr=False, compare=False
    )
    runtime_preparation: RelayMEMSLPRuntimeEnqueueResult = field(
        repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationPreparedTurn("
            "exact_identity_prepared=True, protected_content_omitted=True)"
        )


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationPublicationResult:
    status: PublicationStatus
    projection: RelayMEMSLPDurableFinalizationProjection
    prepared_turn: RelayMEMSLPDurableFinalizationPreparedTurn | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationPublicationResult("
            f"status={self.status!r}, sealed={self.projection.sealed!r}, "
            "protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return self.projection.to_log_dict()


@dataclass(repr=False)
class RelayMEMSLPDurableFinalizationPreparedTurnHolder:
    """Request-local handoff set only after the seal is canonically reread."""

    _prepared: RelayMEMSLPDurableFinalizationPreparedTurn | None = field(
        default=None, init=False, repr=False
    )
    _failed: bool = field(default=False, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __repr__(self) -> str:
        with self._lock:
            return (
                "RelayMEMSLPDurableFinalizationPreparedTurnHolder("
                f"ready={self._prepared is not None}, failed={self._failed}, "
                "protected_content_omitted=True)"
            )

    def publish(self, prepared: RelayMEMSLPDurableFinalizationPreparedTurn) -> None:
        if type(prepared) is not RelayMEMSLPDurableFinalizationPreparedTurn:
            raise TypeError("exact_durable_finalization_prepared_turn_required")
        with self._lock:
            if self._failed:
                raise RelayMEMSLPDurableFinalizationError(
                    "durable_finalization_holder_failed"
                )
            if self._prepared is not None and self._prepared is not prepared:
                raise RelayMEMSLPDurableFinalizationError(
                    "durable_finalization_holder_collision"
                )
            self._prepared = prepared

    def fail(self) -> None:
        with self._lock:
            if self._prepared is None:
                self._failed = True

    def get(self) -> RelayMEMSLPDurableFinalizationPreparedTurn | None:
        with self._lock:
            return self._prepared


@dataclass(repr=False)
class RelayMEMSLPDurableFinalizationStreamSession:
    config: RelayLMConfig = field(repr=False)
    pipeline_context: PipelineContext = field(repr=False)
    status_code: int
    resolved_session_id: str | None
    relayscn_scene_policy_artifact: dict[str, object] = field(repr=False)
    relayemo_artifact: dict[str, object] | None = field(repr=False)
    store: RelayMEMSLPDurableFinalizationStore = field(repr=False)
    base: dict[str, object] = field(repr=False)
    holder: RelayMEMSLPDurableFinalizationPreparedTurnHolder = field(repr=False)
    _segments: list[dict[str, object]] = field(default_factory=list, repr=False)
    _content_parts: list[bytes] = field(default_factory=list, repr=False)
    _sealed: bool = field(default=False, repr=False)
    _failed: bool = field(default=False, repr=False)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationStreamSession("
            f"segment_count={len(self._segments)}, sealed={self._sealed}, "
            f"failed={self._failed}, protected_content_omitted=True)"
        )

    @property
    def sealed(self) -> bool:
        return self._sealed

    def publish_content_unit(self, content_text: str) -> None:
        if self._failed or self._sealed:
            raise RelayMEMSLPDurableFinalizationError(
                "durable_finalization_stream_state_invalid"
            )
        if type(content_text) is not str or not content_text:
            raise RelayMEMSLPDurableFinalizationError(
                "durable_finalization_stream_content_invalid"
            )
        content = content_text.encode("utf-8")
        previous = (
            str(self._segments[-1]["segment_digest"])
            if self._segments
            else ZERO_DIGEST
        )
        try:
            segment = build_segment_record(
                base=self.base,
                sequence=len(self._segments),
                previous_segment_digest=previous,
                content=content,
            )
        except (TypeError, ValueError, UnicodeError):
            self.abort()
            raise RelayMEMSLPDurableFinalizationError(
                "durable_finalization_segment_build_failed"
            )
        result = self.store.publish_segment(segment)
        if result.status not in {"published_new", "duplicate_existing"}:
            self.abort()
            raise RelayMEMSLPDurableFinalizationError(
                _store_reason(result, "durable_finalization_segment_publish_failed")
            )
        reread = self.store.read_evidence(str(self.base["locator_digest"]))
        if (
            reread.status != "loaded"
            or reread.evidence is None
            or len(reread.evidence.segments) != len(self._segments) + 1
            or canonical_json_bytes(reread.evidence.segments[-1])
            != canonical_json_bytes(segment)
        ):
            self.abort()
            raise RelayMEMSLPDurableFinalizationError(
                "durable_finalization_segment_canonical_reread_failed"
            )
        self._segments.append(segment)
        self._content_parts.append(content)

    def seal(self) -> RelayMEMSLPDurableFinalizationPublicationResult:
        if self._sealed:
            prepared = self.holder.get()
            if prepared is None:
                raise RelayMEMSLPDurableFinalizationError(
                    "durable_finalization_seal_state_invalid"
                )
            return _success_result(
                self.config,
                status="duplicate_existing",
                record_present=True,
                sealed=True,
                replayable=True,
                segment_count=len(self._segments),
                prepared=prepared,
            )
        if self._failed:
            raise RelayMEMSLPDurableFinalizationError(
                "durable_finalization_incomplete_stream"
            )
        visible_bytes = b"".join(self._content_parts)
        result = _prepare_and_publish_seal(
            config=self.config,
            pipeline_context=self.pipeline_context,
            status_code=self.status_code,
            resolved_session_id=self.resolved_session_id,
            relayscn_scene_policy_artifact=self.relayscn_scene_policy_artifact,
            relayemo_artifact=self.relayemo_artifact,
            store=self.store,
            base=self.base,
            segments=tuple(self._segments),
            visible_content=visible_bytes,
        )
        if result.status not in {"published", "duplicate_existing"}:
            self.abort()
            raise RelayMEMSLPDurableFinalizationError(
                _projection_reason(
                    result.projection, "durable_finalization_seal_publish_failed"
                )
            )
        assert result.prepared_turn is not None
        self.holder.publish(result.prepared_turn)
        self._sealed = True
        return result

    def abort(self) -> None:
        self._failed = True
        self.holder.fail()


def start_relaymem_slp_durable_finalization_stream(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: Mapping[str, object],
    relayemo_artifact: Mapping[str, object] | None,
    holder: RelayMEMSLPDurableFinalizationPreparedTurnHolder,
) -> tuple[
    RelayMEMSLPDurableFinalizationStreamSession | None,
    RelayMEMSLPDurableFinalizationPublicationResult,
]:
    gate = _validate_gate(config)
    if gate is not None:
        return None, gate
    if not config.relaymem_slp_durable_finalization_enabled:
        return None, _simple_result(config, "disabled")
    base, build_reason = _build_base(
        pipeline_context=pipeline_context,
        status_code=status_code,
        resolved_session_id=resolved_session_id,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=relayemo_artifact,
        stream_mode=True,
    )
    if base is None:
        return None, _failure_result(config, "base", build_reason)
    if config.relaymem_slp_durable_finalization_dry_run_only:
        return None, _simple_result(config, "dry_run_ready")
    store, store_reason = _build_store(config)
    if store is None:
        return None, _failure_result(config, "store", store_reason)
    published = store.publish_base(base)
    if published.status not in {"published_new", "duplicate_existing"}:
        return None, _store_failure_result(config, "base", published)
    reread = store.read_evidence(str(base["locator_digest"]))
    if (
        reread.status != "loaded"
        or reread.evidence is None
        or canonical_json_bytes(reread.evidence.base) != canonical_json_bytes(base)
    ):
        return None, _failure_result(
            config,
            "base",
            "durable_finalization_base_canonical_reread_failed",
            store_result=reread,
        )
    session = RelayMEMSLPDurableFinalizationStreamSession(
        config=config,
        pipeline_context=pipeline_context,
        status_code=status_code,
        resolved_session_id=resolved_session_id,
        relayscn_scene_policy_artifact=deepcopy(dict(relayscn_scene_policy_artifact)),
        relayemo_artifact=(
            deepcopy(dict(relayemo_artifact))
            if relayemo_artifact is not None
            else None
        ),
        store=store,
        base=base,
        holder=holder,
    )
    return session, _success_result(
        config,
        status=(
            "published"
            if published.status == "published_new"
            else "duplicate_existing"
        ),
        record_present=True,
        sealed=False,
        replayable=False,
        segment_count=0,
    )


def admit_relaymem_slp_durable_finalization_nonstream(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: Mapping[str, object],
    relayemo_artifact: Mapping[str, object] | None,
    assistant_visible_text: str,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    gate = _validate_gate(config)
    if gate is not None:
        return gate
    if not config.relaymem_slp_durable_finalization_enabled:
        return _simple_result(config, "disabled")
    if type(assistant_visible_text) is not str or not assistant_visible_text:
        return _failure_result(
            config,
            "source",
            "durable_finalization_visible_text_invalid",
        )
    base, build_reason = _build_base(
        pipeline_context=pipeline_context,
        status_code=status_code,
        resolved_session_id=resolved_session_id,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=relayemo_artifact,
        stream_mode=False,
    )
    if base is None:
        return _failure_result(config, "base", build_reason)
    prepared, prepare_reason = _prepare_turn(
        pipeline_context=pipeline_context,
        status_code=status_code,
        resolved_session_id=resolved_session_id,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=relayemo_artifact,
        assistant_visible_text=assistant_visible_text,
    )
    if prepared is None:
        return _failure_result(config, "preparation", prepare_reason)
    if config.relaymem_slp_durable_finalization_dry_run_only:
        return _success_result(
            config,
            status="dry_run_ready",
            record_present=False,
            sealed=False,
            replayable=False,
            segment_count=0,
            prepared=prepared,
        )
    store, store_reason = _build_store(config)
    if store is None:
        return _failure_result(config, "store", store_reason)
    base_result = store.publish_base(base)
    if base_result.status not in {"published_new", "duplicate_existing"}:
        return _store_failure_result(config, "base", base_result)
    return _publish_prepared_seal(
        config=config,
        store=store,
        base=base,
        segments=(),
        visible_content=assistant_visible_text.encode("utf-8"),
        prepared=prepared,
    )


def _prepare_and_publish_seal(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: Mapping[str, object],
    relayemo_artifact: Mapping[str, object] | None,
    store: RelayMEMSLPDurableFinalizationStore,
    base: Mapping[str, object],
    segments: tuple[Mapping[str, object], ...],
    visible_content: bytes,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    try:
        text = visible_content.decode("utf-8")
    except UnicodeDecodeError:
        return _failure_result(
            config,
            "source",
            "durable_finalization_visible_content_utf8_invalid",
        )
    if not text:
        return _failure_result(
            config,
            "source",
            "durable_finalization_visible_text_invalid",
        )
    prepared, prepare_reason = _prepare_turn(
        pipeline_context=pipeline_context,
        status_code=status_code,
        resolved_session_id=resolved_session_id,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=relayemo_artifact,
        assistant_visible_text=text,
    )
    if prepared is None:
        return _failure_result(config, "preparation", prepare_reason)
    return _publish_prepared_seal(
        config=config,
        store=store,
        base=base,
        segments=segments,
        visible_content=visible_content,
        prepared=prepared,
    )


def _publish_prepared_seal(
    *,
    config: RelayLMConfig,
    store: RelayMEMSLPDurableFinalizationStore,
    base: Mapping[str, object],
    segments: tuple[Mapping[str, object], ...],
    visible_content: bytes,
    prepared: RelayMEMSLPDurableFinalizationPreparedTurn,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    try:
        seal = build_seal_record(
            base=base,
            segments=segments,
            visible_content=visible_content,
            finalized_turn_source_result=prepared.source_result,
            prepared_runtime_enqueue=prepared.runtime_preparation,
        )
    except (TypeError, ValueError, UnicodeError):
        return _failure_result(
            config,
            "seal",
            "durable_finalization_seal_build_failed",
        )
    store_result = store.publish_seal(seal)
    if store_result.status not in {"published_new", "duplicate_existing"}:
        return _store_failure_result(config, "seal", store_result)
    reread = store.read_evidence(str(base["locator_digest"]))
    if (
        reread.status != "loaded"
        or reread.evidence is None
        or reread.evidence.seal is None
        or canonical_json_bytes(reread.evidence.seal) != canonical_json_bytes(seal)
        or reread.replayable is not True
    ):
        return _failure_result(
            config,
            "seal",
            "durable_finalization_seal_canonical_reread_failed",
            store_result=reread,
        )
    return _success_result(
        config,
        status=(
            "published"
            if store_result.status == "published_new"
            else "duplicate_existing"
        ),
        record_present=True,
        sealed=True,
        replayable=True,
        segment_count=len(segments),
        prepared=prepared,
    )


def _prepare_turn(
    *,
    pipeline_context: PipelineContext,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: Mapping[str, object],
    relayemo_artifact: Mapping[str, object] | None,
    assistant_visible_text: str,
) -> tuple[RelayMEMSLPDurableFinalizationPreparedTurn | None, str]:
    try:
        source_result = build_relaymem_slp_finalized_turn_source(
            pipeline_context,
            assistant_visible_text=assistant_visible_text,
            status_code=status_code,
            resolved_session_id=resolved_session_id,
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayemo_artifact=relayemo_artifact,
            response_finalized=True,
            enabled=True,
        )
        if (
            source_result.status != "ready"
            or source_result.source_ready is not True
            or source_result.source is None
        ):
            return None, (
                source_result.blocked_reasons[0]
                if source_result.blocked_reasons
                else "durable_finalization_finalized_source_not_ready"
            )
        preparation = prepare_relaymem_slp_runtime_enqueue(source_result)
        if (
            preparation.status != "dry_run_ready"
            or preparation.dispatch_result is None
            or preparation.dispatch_result.durable_job is None
            or type(preparation.protected_source_payload) is not dict
        ):
            return None, (
                preparation.blocked_reasons[0]
                if preparation.blocked_reasons
                else "durable_finalization_b1_preparation_failed"
            )
        return (
            RelayMEMSLPDurableFinalizationPreparedTurn(
                source_result=source_result,
                runtime_preparation=preparation,
            ),
            "",
        )
    except Exception:
        return None, "durable_finalization_preparation_failed"


def _build_base(
    *,
    pipeline_context: PipelineContext,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: Mapping[str, object],
    relayemo_artifact: Mapping[str, object] | None,
    stream_mode: bool,
) -> tuple[dict[str, object] | None, str]:
    if type(pipeline_context) is not PipelineContext:
        return None, "exact_pipeline_context_required"
    route = pipeline_context.route
    character_id = route.character_id
    namespace = route.memory_namespace
    if not is_token(pipeline_context.run_id):
        return None, "durable_finalization_run_id_invalid"
    if not is_token(pipeline_context.request_id):
        return None, "durable_finalization_request_correlation_invalid"
    if not is_token(character_id):
        return None, "durable_finalization_character_id_invalid"
    if not is_token(namespace):
        return None, "durable_finalization_namespace_invalid"
    if type(status_code) is not int or isinstance(status_code, bool):
        return None, "durable_finalization_status_code_invalid"
    if resolved_session_id is not None and not is_token(resolved_session_id):
        return None, "durable_finalization_session_id_invalid"
    preflight = pipeline_context.client_history_exclusion_preflight_result
    current_user = (
        deepcopy(dict(preflight.current_user_message))
        if preflight is not None and preflight.current_user_message is not None
        else None
    )
    static = {
        "status_code": status_code,
        "resolved_session_id": resolved_session_id,
        "namespace": namespace,
        "source_event_kind": "turn",
        "source_count": 1,
        "persistence_policy_status": "allowed",
        "current_user_message": current_user,
        "relayscn_scene_policy_artifact": deepcopy(
            dict(relayscn_scene_policy_artifact)
        ),
        "relayemo_artifact": (
            deepcopy(dict(relayemo_artifact))
            if relayemo_artifact is not None
            else None
        ),
    }
    try:
        # Force finite, canonical, JSON-only protected input before filesystem use.
        json.loads(canonical_json_bytes(static).decode("utf-8"))
        return (
            build_base_record(
                run_id=pipeline_context.run_id,
                turn_index=0,
                character_id=character_id,
                request_correlation=pipeline_context.request_id,
                stream_mode=stream_mode,
                static_finalized_turn_inputs=static,
            ),
            "",
        )
    except Exception:
        return None, "durable_finalization_base_build_failed"


def _build_store(
    config: RelayLMConfig,
) -> tuple[RelayMEMSLPDurableFinalizationStore | None, str]:
    root = config.relaymem_slp_durable_finalization_root
    if type(root) is not str or not root:
        return None, "durable_finalization_root_missing"
    try:
        return (
            RelayMEMSLPDurableFinalizationStore(
                root,
                max_record_bytes=(
                    config.relaymem_slp_durable_finalization_max_record_bytes
                ),
                max_segment_bytes=(
                    config.relaymem_slp_durable_finalization_max_segment_bytes
                ),
                max_segment_count=(
                    config.relaymem_slp_durable_finalization_max_segment_count
                ),
                max_record_count=(
                    config.relaymem_slp_durable_finalization_max_record_count
                ),
                operation_timeout_ms=(
                    config.relaymem_slp_durable_finalization_publication_timeout_ms
                ),
            ),
            "",
        )
    except (TypeError, ValueError):
        return None, "durable_finalization_store_config_invalid"


def _validate_gate(
    config: RelayLMConfig,
) -> RelayMEMSLPDurableFinalizationPublicationResult | None:
    enabled = config.relaymem_slp_durable_finalization_enabled
    dry = config.relaymem_slp_durable_finalization_dry_run_only
    apply = config.relaymem_slp_durable_finalization_apply_enabled
    if not enabled:
        if apply:
            return _failure_result(
                config, "gate", "durable_finalization_apply_without_enabled"
            )
        if not dry:
            return _failure_result(
                config, "gate", "durable_finalization_disabled_gate_invalid"
            )
        return None
    if dry and apply:
        return _failure_result(
            config, "gate", "durable_finalization_apply_enabled_in_dry_run"
        )
    if not dry and not apply:
        return _failure_result(
            config, "gate", "durable_finalization_apply_gate_incomplete"
        )
    if apply and (
        not config.relaymem_slp_runtime_enqueue_enabled
        or config.relaymem_slp_runtime_enqueue_dry_run_only
        or not config.relaymem_slp_runtime_enqueue_apply_enabled
    ):
        return _failure_result(
            config,
            "gate",
            "durable_finalization_runtime_enqueue_apply_required",
        )
    if (
        config.relaymem_slp_durable_finalization_max_segment_bytes
        > config.relaymem_slp_durable_finalization_max_record_bytes
    ):
        return _failure_result(
            config,
            "gate",
            "durable_finalization_segment_bound_exceeds_record_bound",
        )
    return None


def _simple_result(
    config: RelayLMConfig, status: PublicationStatus
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    return RelayMEMSLPDurableFinalizationPublicationResult(
        status=status,
        projection=RelayMEMSLPDurableFinalizationProjection(
            enabled=config.relaymem_slp_durable_finalization_enabled,
            dry_run_only=config.relaymem_slp_durable_finalization_dry_run_only,
            apply_enabled=config.relaymem_slp_durable_finalization_apply_enabled,
            outcome_status=status,
            failure_stage="none",
            reason_ids=(),
            record_present=False,
            sealed=False,
            replayable=False,
        ),
    )


def _success_result(
    config: RelayLMConfig,
    *,
    status: PublicationStatus,
    record_present: bool,
    sealed: bool,
    replayable: bool,
    segment_count: int,
    prepared: RelayMEMSLPDurableFinalizationPreparedTurn | None = None,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    return RelayMEMSLPDurableFinalizationPublicationResult(
        status=status,
        projection=RelayMEMSLPDurableFinalizationProjection(
            enabled=config.relaymem_slp_durable_finalization_enabled,
            dry_run_only=config.relaymem_slp_durable_finalization_dry_run_only,
            apply_enabled=config.relaymem_slp_durable_finalization_apply_enabled,
            outcome_status=status,
            failure_stage="none",
            reason_ids=(),
            record_present=record_present,
            sealed=sealed,
            replayable=replayable,
            source_present=False,
            queue_present=False,
            complete=False,
            cleanup_required=False,
            bounded_segment_count=segment_count,
            bounded_attempt_count=1 if record_present else 0,
        ),
        prepared_turn=prepared,
    )


def _failure_result(
    config: RelayLMConfig,
    stage: str,
    reason: str,
    *,
    store_result: RelayMEMSLPDurableFinalizationStoreResult | None = None,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    reason_id = reason if _ascii_token(reason) else "durable_finalization_failed"
    return RelayMEMSLPDurableFinalizationPublicationResult(
        status="blocked" if stage in {"gate", "source", "preparation"} else "failed",
        projection=RelayMEMSLPDurableFinalizationProjection(
            enabled=config.relaymem_slp_durable_finalization_enabled,
            dry_run_only=config.relaymem_slp_durable_finalization_dry_run_only,
            apply_enabled=config.relaymem_slp_durable_finalization_apply_enabled,
            outcome_status=(
                "blocked" if stage in {"gate", "source", "preparation"} else "failed"
            ),
            failure_stage=stage if _ascii_token(stage) else "publication",
            reason_ids=(reason_id,),
            record_present=bool(store_result and store_result.record_present),
            sealed=bool(store_result and store_result.sealed),
            replayable=bool(store_result and store_result.replayable),
            source_present=False,
            queue_present=False,
            complete=False,
            cleanup_required=bool(store_result and store_result.cleanup_required),
            bounded_segment_count=(
                store_result.bounded_segment_count if store_result else 0
            ),
            bounded_attempt_count=(
                store_result.bounded_attempt_count if store_result else 0
            ),
        ),
    )


def _store_failure_result(
    config: RelayLMConfig,
    stage: str,
    result: RelayMEMSLPDurableFinalizationStoreResult,
) -> RelayMEMSLPDurableFinalizationPublicationResult:
    return _failure_result(
        config,
        stage,
        _store_reason(result, "durable_finalization_publication_failed"),
        store_result=result,
    )


def _store_reason(
    result: RelayMEMSLPDurableFinalizationStoreResult, fallback: str
) -> str:
    return result.blocked_reasons[0] if result.blocked_reasons else fallback


def _projection_reason(
    projection: RelayMEMSLPDurableFinalizationProjection, fallback: str
) -> str:
    return projection.reason_ids[0] if projection.reason_ids else fallback


def _ascii_token(value: object) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= 128
        and all(character.isascii() and (character.isalnum() or character in "_-.") for character in value)
    )


__all__ = [
    "RelayMEMSLPDurableFinalizationError",
    "RelayMEMSLPDurableFinalizationPreparedTurn",
    "RelayMEMSLPDurableFinalizationPreparedTurnHolder",
    "RelayMEMSLPDurableFinalizationPublicationResult",
    "RelayMEMSLPDurableFinalizationStreamSession",
    "admit_relaymem_slp_durable_finalization_nonstream",
    "start_relaymem_slp_durable_finalization_stream",
]
