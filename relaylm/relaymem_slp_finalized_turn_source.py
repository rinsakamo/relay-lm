"""Exact request-local finalized-turn source for Phase 6 I1-B.

This boundary owns only the protected evidence captured from one ordinary managed
turn after its visible assistant response is final.  It uses the existing
current-user preflight, RelayMEM source-lineage constructor, and governed-
experience constructor.  It does not enqueue, claim, execute a worker, or invoke
any M3a-M3h stage.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal

from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
)
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
)
from relaylm.relaymem_slp_primary_worker_source import SOURCE_SCHEMA
from relaylm.relaymem_slp_queue_record import dedupe, is_token, strict_bool

FINALIZED_TURN_SOURCE_SCHEMA = "relaymem.slp_finalized_turn_source.v0"
FINALIZED_TURN_SOURCE_PROJECTION_SCHEMA = (
    "relaymem.slp_finalized_turn_source_projection.v0"
)
_MAX_MESSAGE_CHARS = 32_768
_MAX_SUMMARY_CHARS = 2_048
_MAX_TITLE_CHARS = 160
_MAX_REASONS = 32
_WHITESPACE_RE = re.compile(r"\s+")

FinalizedTurnSourceStatus = Literal[
    "disabled",
    "invalid_input",
    "blocked",
    "ready",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPFinalizedTurnSource:
    """Protected exact source parts captured before B1 assigns queue identity."""

    schema_version: str
    character_id: str
    run_id: str
    turn_index: int
    session_id: str | None
    namespace: str
    source_event_kind: str
    source_count: int
    persistence_policy_status: str
    source_lineage_artifact: Mapping[str, object] = field(repr=False)
    relayscn_scene_policy_artifact: Mapping[str, object] = field(repr=False)
    relayemo_artifact: Mapping[str, object] | None = field(repr=False)
    governed_messages: tuple[Mapping[str, object], ...] = field(repr=False)
    governed_experience_artifact: Mapping[str, object] = field(repr=False)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPFinalizedTurnSource("
            "runtime_private=True, content_included=True, "
            "protected_content_omitted=True)"
        )

    @property
    def source_lineage_fingerprint(self) -> str:
        return str(self.source_lineage_artifact["lineage_fingerprint"])

    def to_protected_source_payload(
        self,
        *,
        job_id: str,
        dispatch_idempotency_key: str,
    ) -> dict[str, object]:
        """Add B1-owned identities to the exact C1-0 16-field payload."""

        return {
            "schema_version": SOURCE_SCHEMA,
            "runtime_private": True,
            "content_included": True,
            "job_id": job_id,
            "dispatch_idempotency_key": dispatch_idempotency_key,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "session_id": self.session_id,
            "namespace": self.namespace,
            "source_event_kind": self.source_event_kind,
            "source_count": self.source_count,
            "source_lineage_fingerprint": self.source_lineage_fingerprint,
            "relayscn_scene_policy_artifact": deepcopy(
                dict(self.relayscn_scene_policy_artifact)
            ),
            "relayemo_artifact": (
                deepcopy(dict(self.relayemo_artifact))
                if self.relayemo_artifact is not None
                else None
            ),
            "governed_messages": [deepcopy(dict(item)) for item in self.governed_messages],
            "governed_experience_artifact": deepcopy(
                dict(self.governed_experience_artifact)
            ),
        }


@dataclass(frozen=True)
class RelayMEMSLPFinalizedTurnSourceResult:
    status: FinalizedTurnSourceStatus
    enabled: bool
    response_finalized: bool
    source_ready: bool
    blocked_reasons: tuple[str, ...]
    source: RelayMEMSLPFinalizedTurnSource | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": FINALIZED_TURN_SOURCE_PROJECTION_SCHEMA,
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
            "status": self.status,
            "enabled": self.enabled,
            "response_finalized": self.response_finalized,
            "source_ready": self.source_ready,
            "source_count": self.source.source_count if self.source is not None else 0,
            "current_user_present": self.source is not None,
            "assistant_response_present": self.source is not None,
            "scene_policy_present": self.source is not None,
            "relayemo_present": (
                self.source is not None and self.source.relayemo_artifact is not None
            ),
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def build_relaymem_slp_finalized_turn_source(
    pipeline_context: object,
    *,
    assistant_visible_text: object,
    status_code: object,
    resolved_session_id: object,
    relayscn_scene_policy_artifact: object,
    relayemo_artifact: object,
    response_finalized: bool,
    enabled: bool = False,
) -> RelayMEMSLPFinalizedTurnSourceResult:
    """Capture one exact ordinary managed turn after visible finalization."""

    enabled_value, enabled_errors = strict_bool(enabled, "enabled_invalid")
    finalized_value, finalized_errors = strict_bool(
        response_finalized,
        "response_finalized_invalid",
    )
    gate_errors = dedupe((*enabled_errors, *finalized_errors))
    if gate_errors:
        return _result(
            "invalid_input",
            enabled=enabled_value,
            response_finalized=finalized_value,
            blocked_reasons=gate_errors,
        )
    if not enabled_value:
        return _result("disabled", enabled=False, response_finalized=finalized_value)
    if type(pipeline_context) is not PipelineContext:
        return _result(
            "invalid_input",
            enabled=True,
            response_finalized=finalized_value,
            blocked_reasons=("exact_pipeline_context_required",),
        )
    context = pipeline_context
    reasons: list[str] = []
    if context.route.mode_applied == "pass_through":
        reasons.append("pass_through_route_exempt")
    if not finalized_value:
        reasons.append("visible_response_not_finalized")
    if type(status_code) is not int or isinstance(status_code, bool):
        reasons.append("backend_status_invalid")
    elif not 200 <= status_code < 300:
        reasons.append("backend_status_not_success")

    character_id = context.route.character_id
    namespace = context.route.memory_namespace
    if not is_token(character_id):
        reasons.append("character_id_invalid")
    if not is_token(namespace):
        reasons.append("namespace_invalid")
    if not is_token(context.run_id):
        reasons.append("run_id_invalid")
    if type(context.turn_index) is not int or context.turn_index < 0:
        reasons.append("turn_index_invalid")
    session_id: str | None
    if resolved_session_id is None:
        session_id = None
    elif is_token(resolved_session_id):
        session_id = str(resolved_session_id)
    else:
        session_id = None
        reasons.append("session_id_invalid")

    assistant_text, assistant_errors = _bounded_text(
        assistant_visible_text,
        max_chars=_MAX_MESSAGE_CHARS,
        reason="assistant_visible_text_invalid",
    )
    reasons.extend(assistant_errors)
    user_text, user_errors = _current_user_text(
        context.client_history_exclusion_preflight_result
    )
    reasons.extend(user_errors)

    scene, scene_errors = _scene_artifact(relayscn_scene_policy_artifact)
    reasons.extend(scene_errors)
    emo, emo_errors = _relayemo_artifact(relayemo_artifact)
    reasons.extend(emo_errors)
    reasons = list(dedupe(tuple(reasons)))[:_MAX_REASONS]
    if reasons:
        return _result(
            "blocked",
            enabled=True,
            response_finalized=finalized_value,
            blocked_reasons=reasons,
        )

    assert character_id is not None and namespace is not None
    assert assistant_text is not None and user_text is not None and scene is not None
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id=context.request_id,
        run_id=context.run_id,
        session_id=session_id,
        turn_index=context.turn_index,
        namespace=namespace,
    )
    if lineage.get("valid") is not True:
        return _result(
            "blocked",
            enabled=True,
            response_finalized=True,
            blocked_reasons=("source_lineage_build_failed",),
        )

    candidate_id = _candidate_id(
        run_id=context.run_id,
        turn_index=context.turn_index,
        lineage_fingerprint=str(lineage.get("lineage_fingerprint", "")),
    )
    title = _title(user_text)
    summary = _summary(user_text, assistant_text)
    experience = build_relaymem_governed_experience_summary(
        candidate_id=candidate_id,
        source_event_kind="turn",
        namespace=namespace,
        title=title,
        summary_text=summary,
    )
    if experience.get("valid") is not True:
        return _result(
            "blocked",
            enabled=True,
            response_finalized=True,
            blocked_reasons=("governed_experience_build_failed",),
        )

    persistence_status = (
        "blocked" if scene.get("persistence_block") is True else "allowed"
    )
    source = RelayMEMSLPFinalizedTurnSource(
        schema_version=FINALIZED_TURN_SOURCE_SCHEMA,
        character_id=character_id,
        run_id=context.run_id,
        turn_index=context.turn_index,
        session_id=session_id,
        namespace=namespace,
        source_event_kind="turn",
        source_count=1,
        persistence_policy_status=persistence_status,
        source_lineage_artifact=deepcopy(lineage),
        relayscn_scene_policy_artifact=scene,
        relayemo_artifact=emo,
        governed_messages=(
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ),
        governed_experience_artifact=deepcopy(experience),
    )
    return _result(
        "ready",
        enabled=True,
        response_finalized=True,
        source=source,
    )


def build_relaymem_slp_finalized_turn_source_node_result(
    result: RelayMEMSLPFinalizedTurnSourceResult,
) -> PipelineNodeResult:
    status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
    }.get(result.status, "diagnostic_only")
    return build_pipeline_node_result(
        node_name="relaymem_slp_finalized_turn_source",
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[{
            "artifact_name": "relaymem_slp_finalized_turn_source",
            "schema_version": FINALIZED_TURN_SOURCE_SCHEMA,
            "present": result.source is not None,
            "content_free": True,
            "runtime_private": True,
            "source_omitted": True,
            "raw_messages_included": False,
            "governed_experience_included": False,
            "identifier_values_included": False,
            "lineage_fingerprint_included": False,
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "changes_visible_response": False,
        }],
    )


def _current_user_text(
    value: object,
) -> tuple[str | None, tuple[str, ...]]:
    if type(value) is not ClientHistoryExclusionPreflightResult:
        return None, ("exact_current_user_preflight_required",)
    if value.status not in {"ready", "pending"}:
        return None, ("current_user_preflight_not_ready",)
    message = value.current_user_message
    if type(message) is not dict:
        return None, ("exact_current_user_message_required",)
    if message.get("role") != "user":
        return None, ("current_user_role_invalid",)
    return _bounded_text(
        message.get("content"),
        max_chars=_MAX_MESSAGE_CHARS,
        reason="current_user_text_invalid",
    )


def _scene_artifact(
    value: object,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("relayscn_scene_policy_artifact_invalid",)
    if type(value.get("scene_state")) is not dict:
        return None, ("relayscn_scene_state_invalid",)
    if type(value.get("scene_policy")) is not dict:
        return None, ("relayscn_scene_policy_invalid",)
    if type(value.get("persistence_block")) is not bool:
        return None, ("relayscn_persistence_block_invalid",)
    blocked = value.get("persistence_block_reasons")
    if type(blocked) is not list or any(type(item) is not str for item in blocked):
        return None, ("relayscn_persistence_reasons_invalid",)
    try:
        return deepcopy(value), ()
    except Exception:
        return None, ("relayscn_scene_policy_snapshot_failed",)


def _relayemo_artifact(
    value: object,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if value is None:
        return None, ()
    if type(value) is not dict:
        return None, ("relayemo_artifact_invalid",)
    if type(value.get("assistant_emotion_state")) is not dict:
        return None, ("relayemo_assistant_state_invalid",)
    if type(value.get("user_affect_estimate")) is not dict:
        return None, ("relayemo_user_affect_invalid",)
    try:
        return deepcopy(value), ()
    except Exception:
        return None, ("relayemo_artifact_snapshot_failed",)


def _bounded_text(
    value: object,
    *,
    max_chars: int,
    reason: str,
) -> tuple[str | None, tuple[str, ...]]:
    if type(value) is not str or not value or len(value) > max_chars:
        return None, (reason,)
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        return None, (reason,)
    if any(ord(character) == 127 for character in value):
        return None, (reason,)
    return value, ()


def _candidate_id(*, run_id: str, turn_index: int, lineage_fingerprint: str) -> str:
    encoded = (
        FINALIZED_TURN_SOURCE_SCHEMA
        + "\0"
        + run_id
        + "\0"
        + str(turn_index)
        + "\0"
        + lineage_fingerprint
    ).encode("utf-8")
    return "primary_candidate:" + hashlib.sha256(encoded).hexdigest()


def _normalise_summary_text(value: str, max_chars: int) -> str:
    normalised = _WHITESPACE_RE.sub(" ", value).strip()
    if len(normalised) <= max_chars:
        return normalised
    return normalised[: max(1, max_chars - 1)].rstrip() + "…"


def _title(user_text: str) -> str:
    return _normalise_summary_text(user_text, _MAX_TITLE_CHARS)


def _summary(user_text: str, assistant_text: str) -> str:
    prefix_user = "User turn: "
    separator = "\nAssistant response: "
    available = _MAX_SUMMARY_CHARS - len(prefix_user) - len(separator)
    user_budget = min(768, max(1, available // 3))
    assistant_budget = max(1, available - user_budget)
    return (
        prefix_user
        + _normalise_summary_text(user_text, user_budget)
        + separator
        + _normalise_summary_text(assistant_text, assistant_budget)
    )


def _result(
    status: FinalizedTurnSourceStatus,
    *,
    enabled: bool,
    response_finalized: bool,
    blocked_reasons: Sequence[str] = (),
    source: RelayMEMSLPFinalizedTurnSource | None = None,
) -> RelayMEMSLPFinalizedTurnSourceResult:
    return RelayMEMSLPFinalizedTurnSourceResult(
        status=status,
        enabled=enabled,
        response_finalized=response_finalized,
        source_ready=source is not None,
        blocked_reasons=dedupe(tuple(blocked_reasons))[:_MAX_REASONS],
        source=source,
    )


__all__ = [
    "FINALIZED_TURN_SOURCE_PROJECTION_SCHEMA",
    "FINALIZED_TURN_SOURCE_SCHEMA",
    "RelayMEMSLPFinalizedTurnSource",
    "RelayMEMSLPFinalizedTurnSourceResult",
    "build_relaymem_slp_finalized_turn_source",
    "build_relaymem_slp_finalized_turn_source_node_result",
]
