"""Canonical private I1-GB durable-finalization record model.

The logical record is one immutable base, zero or more immutable ordered stream
segments, and one immutable seal.  It is evidence for later I1-GC replay; it is
not a queue, a completion marker, or a memory lifecycle record.
"""
from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .relaymem_slp_dispatch_preflight import RelayMEMSLPDurableJobCandidate
from .relaymem_slp_finalized_turn_source import (
    FINALIZED_TURN_SOURCE_SCHEMA,
    RelayMEMSLPFinalizedTurnSource,
    RelayMEMSLPFinalizedTurnSourceResult,
)
from .relaymem_slp_queue_record import (
    DURABLE_JOB_FIELDS,
    DISPATCH_KEY_VERSION,
    DURABLE_JOB_SCHEMA,
    dedupe,
    derive_dispatch_key,
    derive_job_id,
    is_sha256,
    is_token,
)
from .relaymem_slp_runtime_enqueue import RelayMEMSLPRuntimeEnqueueResult

RECORD_SCHEMA = "relaymem.slp_durable_finalization.v0"
PROJECTION_SCHEMA = "relaymem.slp_durable_finalization_projection.v0"
RECORD_REVISION = 0
LOCATOR_VERSION = "relaymem.slp_durable_finalization_locator.v0"
ZERO_DIGEST = "0" * 64

BASE_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_included", "record_kind",
    "record_revision", "locator_digest", "run_id", "turn_index",
    "character_id", "request_correlation", "stream_mode",
    "static_finalized_turn_inputs", "base_digest",
})
SEGMENT_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_included", "record_kind",
    "record_revision", "locator_digest", "run_id", "turn_index",
    "character_id", "segment_sequence", "previous_segment_digest",
    "content_byte_count", "content_b64", "segment_digest",
})
SEAL_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_included", "record_kind",
    "record_revision", "locator_digest", "run_id", "turn_index",
    "character_id", "base_digest", "segment_count", "final_segment_digest",
    "visible_content_byte_count", "visible_content_b64",
    "finalized_turn_source", "durable_job", "job_id",
    "dispatch_idempotency_key", "seal_digest",
})
FINALIZED_SOURCE_FIELDS = frozenset({
    "schema_version", "character_id", "run_id", "turn_index", "session_id",
    "namespace", "source_event_kind", "source_count",
    "persistence_policy_status", "source_lineage_artifact",
    "relayscn_scene_policy_artifact", "relayemo_artifact",
    "governed_messages", "governed_experience_artifact",
    "formation_summary_artifact",
})

RecordKind = Literal["base", "segment", "seal"]


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def decode_canonical_json(data: bytes) -> tuple[dict[str, object] | None, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "durable_finalization_malformed_utf8"
    duplicate = False

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        nonlocal duplicate
        result: dict[str, object] = {}
        for key, value in pairs:
            duplicate = duplicate or key in result
            result[key] = value
        return result

    def reject_nonfinite(_: str) -> object:
        raise ValueError("non-finite JSON")

    try:
        value = json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=reject_nonfinite,
        )
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None, "durable_finalization_malformed_json"
    if duplicate:
        return None, "durable_finalization_duplicate_json_key"
    if type(value) is not dict:
        return None, "durable_finalization_json_not_object"
    try:
        if canonical_json_bytes(value) != data:
            return None, "durable_finalization_noncanonical_json"
    except (TypeError, ValueError, RecursionError, OverflowError):
        return None, "durable_finalization_malformed_json"
    return value, None


def derive_locator_digest(
    *, run_id: object, turn_index: object, character_id: object
) -> str:
    reasons = validate_correlation(run_id, turn_index, character_id)
    if reasons:
        raise ValueError(reasons[0])
    body = {
        "schema_version": RECORD_SCHEMA,
        "locator_version": LOCATOR_VERSION,
        "run_id": run_id,
        "turn_index": turn_index,
        "character_id": character_id,
    }
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def validate_correlation(
    run_id: object, turn_index: object, character_id: object
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not is_token(run_id):
        reasons.append("durable_finalization_run_id_invalid")
    if type(turn_index) is not int or turn_index < 0:
        reasons.append("durable_finalization_turn_index_invalid")
    if not is_token(character_id):
        reasons.append("durable_finalization_character_id_invalid")
    return dedupe(tuple(reasons))


def base_filename(locator_digest: str) -> str:
    _require_digest(locator_digest)
    return f"durable-finalization-v0-{locator_digest}.base.json"


def segment_filename(locator_digest: str, sequence: int) -> str:
    _require_digest(locator_digest)
    if type(sequence) is not int or sequence < 0 or sequence > 999_999:
        raise ValueError("durable_finalization_segment_sequence_invalid")
    return f"durable-finalization-v0-{locator_digest}.segment-{sequence:06d}.json"


def seal_filename(locator_digest: str) -> str:
    _require_digest(locator_digest)
    return f"durable-finalization-v0-{locator_digest}.seal.json"


def build_base_record(
    *,
    run_id: str,
    turn_index: int,
    character_id: str,
    request_correlation: str,
    stream_mode: bool,
    static_finalized_turn_inputs: Mapping[str, object],
) -> dict[str, object]:
    locator = derive_locator_digest(
        run_id=run_id, turn_index=turn_index, character_id=character_id
    )
    body: dict[str, object] = {
        "schema_version": RECORD_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "record_kind": "base",
        "record_revision": RECORD_REVISION,
        "locator_digest": locator,
        "run_id": run_id,
        "turn_index": turn_index,
        "character_id": character_id,
        "request_correlation": request_correlation,
        "stream_mode": stream_mode,
        "static_finalized_turn_inputs": _copy_json_mapping(
            static_finalized_turn_inputs
        ),
    }
    body["base_digest"] = _digest_without(body, "base_digest")
    validated, reasons = validate_base_record(body)
    if validated is None or reasons:
        raise ValueError(reasons[0] if reasons else "durable_finalization_base_invalid")
    return validated


def build_segment_record(
    *,
    base: Mapping[str, object],
    sequence: int,
    previous_segment_digest: str,
    content: bytes,
) -> dict[str, object]:
    validated_base, reasons = validate_base_record(base)
    if validated_base is None or reasons:
        raise ValueError(reasons[0] if reasons else "durable_finalization_base_invalid")
    if type(content) is not bytes or not content:
        raise ValueError("durable_finalization_segment_content_invalid")
    content.decode("utf-8")
    body: dict[str, object] = {
        "schema_version": RECORD_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "record_kind": "segment",
        "record_revision": RECORD_REVISION,
        "locator_digest": validated_base["locator_digest"],
        "run_id": validated_base["run_id"],
        "turn_index": validated_base["turn_index"],
        "character_id": validated_base["character_id"],
        "segment_sequence": sequence,
        "previous_segment_digest": previous_segment_digest,
        "content_byte_count": len(content),
        "content_b64": base64.b64encode(content).decode("ascii"),
    }
    body["segment_digest"] = _digest_without(body, "segment_digest")
    validated, segment_reasons = validate_segment_record(
        body,
        expected_base=validated_base,
        expected_sequence=sequence,
        expected_previous_digest=previous_segment_digest,
    )
    if validated is None or segment_reasons:
        raise ValueError(
            segment_reasons[0]
            if segment_reasons
            else "durable_finalization_segment_invalid"
        )
    return validated


def finalized_source_to_mapping(
    source: RelayMEMSLPFinalizedTurnSource,
) -> dict[str, object]:
    if type(source) is not RelayMEMSLPFinalizedTurnSource:
        raise TypeError("exact_finalized_turn_source_required")
    value: dict[str, object] = {
        "schema_version": source.schema_version,
        "character_id": source.character_id,
        "run_id": source.run_id,
        "turn_index": source.turn_index,
        "session_id": source.session_id,
        "namespace": source.namespace,
        "source_event_kind": source.source_event_kind,
        "source_count": source.source_count,
        "persistence_policy_status": source.persistence_policy_status,
        "source_lineage_artifact": _copy_json_mapping(source.source_lineage_artifact),
        "relayscn_scene_policy_artifact": _copy_json_mapping(
            source.relayscn_scene_policy_artifact
        ),
        "relayemo_artifact": (
            _copy_json_mapping(source.relayemo_artifact)
            if source.relayemo_artifact is not None
            else None
        ),
        "governed_messages": [
            _copy_json_mapping(item) for item in source.governed_messages
        ],
        "governed_experience_artifact": _copy_json_mapping(
            source.governed_experience_artifact
        ),
        "formation_summary_artifact": _copy_json_mapping(
            source.formation_summary_artifact
        ),
    }
    reasons = validate_finalized_source_mapping(value)
    if reasons:
        raise ValueError(reasons[0])
    return value


def build_seal_record(
    *,
    base: Mapping[str, object],
    segments: Sequence[Mapping[str, object]],
    visible_content: bytes,
    finalized_turn_source_result: RelayMEMSLPFinalizedTurnSourceResult,
    prepared_runtime_enqueue: RelayMEMSLPRuntimeEnqueueResult,
) -> dict[str, object]:
    validated_base, base_reasons = validate_base_record(base)
    if validated_base is None or base_reasons:
        raise ValueError(base_reasons[0] if base_reasons else "durable_finalization_base_invalid")
    validated_segments, segment_reasons = validate_segment_chain(
        validated_base, segments
    )
    if segment_reasons:
        raise ValueError(segment_reasons[0])
    if type(visible_content) is not bytes:
        raise TypeError("durable_finalization_visible_content_bytes_required")
    try:
        visible_content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("durable_finalization_visible_content_utf8_invalid") from None
    if type(finalized_turn_source_result) is not RelayMEMSLPFinalizedTurnSourceResult:
        raise TypeError("exact_finalized_turn_source_result_required")
    source = finalized_turn_source_result.source
    if (
        finalized_turn_source_result.status != "ready"
        or finalized_turn_source_result.source_ready is not True
        or type(source) is not RelayMEMSLPFinalizedTurnSource
    ):
        raise ValueError("durable_finalization_finalized_source_not_ready")
    if type(prepared_runtime_enqueue) is not RelayMEMSLPRuntimeEnqueueResult:
        raise TypeError("exact_runtime_enqueue_preparation_required")
    dispatch = prepared_runtime_enqueue.dispatch_result
    if (
        prepared_runtime_enqueue.status != "dry_run_ready"
        or dispatch is None
        or type(dispatch.durable_job) is not RelayMEMSLPDurableJobCandidate
    ):
        raise ValueError("durable_finalization_dispatch_not_ready")
    job = dispatch.durable_job
    source_mapping = finalized_source_to_mapping(source)
    job_mapping = job.to_runtime_dict()
    final_digest = (
        str(validated_segments[-1]["segment_digest"])
        if validated_segments
        else ZERO_DIGEST
    )
    body: dict[str, object] = {
        "schema_version": RECORD_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "record_kind": "seal",
        "record_revision": RECORD_REVISION,
        "locator_digest": validated_base["locator_digest"],
        "run_id": validated_base["run_id"],
        "turn_index": validated_base["turn_index"],
        "character_id": validated_base["character_id"],
        "base_digest": validated_base["base_digest"],
        "segment_count": len(validated_segments),
        "final_segment_digest": final_digest,
        "visible_content_byte_count": len(visible_content),
        "visible_content_b64": base64.b64encode(visible_content).decode("ascii"),
        "finalized_turn_source": source_mapping,
        "durable_job": job_mapping,
        "job_id": job.job_id,
        "dispatch_idempotency_key": job.dispatch_idempotency_key,
    }
    body["seal_digest"] = _digest_without(body, "seal_digest")
    validated, seal_reasons = validate_seal_record(
        body, expected_base=validated_base, expected_segments=validated_segments
    )
    if validated is None or seal_reasons:
        raise ValueError(seal_reasons[0] if seal_reasons else "durable_finalization_seal_invalid")
    return validated


def validate_base_record(
    value: object,
    *,
    expected_locator: str | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("durable_finalization_base_shape_invalid",)
    reasons = list(_validate_common(value, BASE_FIELDS, "base"))
    request = value.get("request_correlation")
    if not is_token(request):
        reasons.append("durable_finalization_request_correlation_invalid")
    if type(value.get("stream_mode")) is not bool:
        reasons.append("durable_finalization_stream_mode_invalid")
    if type(value.get("static_finalized_turn_inputs")) is not dict:
        reasons.append("durable_finalization_static_inputs_invalid")
    if expected_locator is not None and value.get("locator_digest") != expected_locator:
        reasons.append("durable_finalization_locator_mismatch")
    if value.get("base_digest") != _digest_without(value, "base_digest"):
        reasons.append("durable_finalization_base_digest_mismatch")
    return (dict(value), ()) if not reasons else (None, dedupe(tuple(reasons)))


def validate_segment_record(
    value: object,
    *,
    expected_base: Mapping[str, object] | None = None,
    expected_sequence: int | None = None,
    expected_previous_digest: str | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("durable_finalization_segment_shape_invalid",)
    reasons = list(_validate_common(value, SEGMENT_FIELDS, "segment"))
    sequence = value.get("segment_sequence")
    if type(sequence) is not int or sequence < 0:
        reasons.append("durable_finalization_segment_sequence_invalid")
    if expected_sequence is not None and sequence != expected_sequence:
        reasons.append("durable_finalization_segment_order_mismatch")
    previous = value.get("previous_segment_digest")
    if not _is_digest(previous):
        reasons.append("durable_finalization_previous_digest_invalid")
    if expected_previous_digest is not None and previous != expected_previous_digest:
        reasons.append("durable_finalization_segment_chain_mismatch")
    content, content_reasons = _decode_b64_content(
        value.get("content_b64"),
        value.get("content_byte_count"),
        "segment",
        allow_empty=False,
    )
    reasons.extend(content_reasons)
    if expected_base is not None:
        reasons.extend(_correlation_mismatch(value, expected_base))
    if value.get("segment_digest") != _digest_without(value, "segment_digest"):
        reasons.append("durable_finalization_segment_digest_mismatch")
    if content is None:
        return None, dedupe(tuple(reasons))
    return (dict(value), ()) if not reasons else (None, dedupe(tuple(reasons)))


def validate_segment_chain(
    base: Mapping[str, object],
    segments: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    if type(segments) not in {list, tuple}:
        return [], ("durable_finalization_segments_shape_invalid",)
    validated: list[dict[str, object]] = []
    previous = ZERO_DIGEST
    for sequence, item in enumerate(segments):
        segment, reasons = validate_segment_record(
            item,
            expected_base=base,
            expected_sequence=sequence,
            expected_previous_digest=previous,
        )
        if segment is None or reasons:
            return [], reasons or ("durable_finalization_segment_invalid",)
        validated.append(segment)
        previous = str(segment["segment_digest"])
    return validated, ()


def validate_seal_record(
    value: object,
    *,
    expected_base: Mapping[str, object] | None = None,
    expected_segments: Sequence[Mapping[str, object]] | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("durable_finalization_seal_shape_invalid",)
    reasons = list(_validate_common(value, SEAL_FIELDS, "seal"))
    if expected_base is not None:
        reasons.extend(_correlation_mismatch(value, expected_base))
        if value.get("base_digest") != expected_base.get("base_digest"):
            reasons.append("durable_finalization_seal_base_mismatch")
    count = value.get("segment_count")
    if type(count) is not int or count < 0:
        reasons.append("durable_finalization_seal_segment_count_invalid")
    if not _is_digest(value.get("final_segment_digest")):
        reasons.append("durable_finalization_final_segment_digest_invalid")
    if expected_segments is not None:
        expected_count = len(expected_segments)
        expected_digest = (
            str(expected_segments[-1]["segment_digest"])
            if expected_segments
            else ZERO_DIGEST
        )
        if count != expected_count:
            reasons.append("durable_finalization_seal_segment_count_mismatch")
        if value.get("final_segment_digest") != expected_digest:
            reasons.append("durable_finalization_seal_chain_mismatch")
    visible, visible_reasons = _decode_b64_content(
        value.get("visible_content_b64"),
        value.get("visible_content_byte_count"),
        "visible_content",
        allow_empty=False,
    )
    reasons.extend(visible_reasons)
    source = value.get("finalized_turn_source")
    reasons.extend(validate_finalized_source_mapping(source))
    job = value.get("durable_job")
    reasons.extend(_validate_b1_job_mapping(job))
    if type(job) is dict:
        if job.get("job_id") != value.get("job_id"):
            reasons.append("durable_finalization_job_id_mismatch")
        if job.get("dispatch_idempotency_key") != value.get(
            "dispatch_idempotency_key"
        ):
            reasons.append("durable_finalization_dispatch_identity_mismatch")
        if source is not None and type(source) is dict:
            for key in ("run_id", "turn_index", "namespace", "source_count"):
                if job.get(key) != source.get(key):
                    reasons.append(f"durable_finalization_job_source_{key}_mismatch")
    if type(source) is dict:
        for key in ("run_id", "turn_index", "character_id"):
            if source.get(key) != value.get(key):
                reasons.append(f"durable_finalization_seal_source_{key}_mismatch")
        messages = source.get("governed_messages")
        if type(messages) is list and len(messages) == 2 and type(messages[1]) is dict:
            assistant = messages[1]
            if assistant.get("role") != "assistant" or assistant.get("content") != (
                visible.decode("utf-8") if visible is not None else None
            ):
                reasons.append("durable_finalization_visible_source_mismatch")
        else:
            reasons.append("durable_finalization_governed_messages_invalid")
    if expected_base is not None and expected_segments is not None and visible is not None:
        if expected_base.get("stream_mode") is True:
            chain_content = b"".join(
                record_content_bytes(segment, "content")
                for segment in expected_segments
            )
            if chain_content != visible:
                reasons.append("durable_finalization_visible_segment_chain_mismatch")
        elif expected_segments:
            reasons.append("durable_finalization_nonstream_segments_forbidden")
    if value.get("seal_digest") != _digest_without(value, "seal_digest"):
        reasons.append("durable_finalization_seal_digest_mismatch")
    if visible is None:
        return None, dedupe(tuple(reasons))
    return (dict(value), ()) if not reasons else (None, dedupe(tuple(reasons)))


def validate_finalized_source_mapping(value: object) -> tuple[str, ...]:
    if type(value) is not dict:
        return ("durable_finalization_finalized_source_shape_invalid",)
    reasons: list[str] = []
    fields = frozenset(value)
    if fields != FINALIZED_SOURCE_FIELDS:
        reasons.append("durable_finalization_finalized_source_shape_mismatch")
    if value.get("schema_version") != FINALIZED_TURN_SOURCE_SCHEMA:
        reasons.append("durable_finalization_finalized_source_schema_mismatch")
    reasons.extend(
        validate_correlation(
            value.get("run_id"), value.get("turn_index"), value.get("character_id")
        )
    )
    if not is_token(value.get("namespace")):
        reasons.append("durable_finalization_finalized_source_namespace_invalid")
    if value.get("source_event_kind") != "turn":
        reasons.append("durable_finalization_finalized_source_event_invalid")
    if type(value.get("source_count")) is not int or value.get("source_count") < 1:
        reasons.append("durable_finalization_finalized_source_count_invalid")
    if type(value.get("governed_messages")) is not list:
        reasons.append("durable_finalization_governed_messages_invalid")
    for key in (
        "source_lineage_artifact",
        "relayscn_scene_policy_artifact",
        "governed_experience_artifact",
    ):
        if type(value.get(key)) is not dict:
            reasons.append(f"durable_finalization_{key}_invalid")
    if type(value.get("formation_summary_artifact")) is not dict:
        reasons.append("durable_finalization_formation_summary_artifact_invalid")
    if value.get("relayemo_artifact") is not None and type(
        value.get("relayemo_artifact")
    ) is not dict:
        reasons.append("durable_finalization_relayemo_artifact_invalid")
    return dedupe(tuple(reasons))


def record_content_bytes(value: Mapping[str, object], field_prefix: str) -> bytes:
    content, reasons = _decode_b64_content(
        value.get(f"{field_prefix}_b64"),
        value.get(f"{field_prefix}_byte_count"),
        field_prefix,
        allow_empty=False,
    )
    if content is None or reasons:
        raise ValueError(reasons[0] if reasons else "durable_finalization_content_invalid")
    return content


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationProjection:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    outcome_status: str
    failure_stage: str
    reason_ids: tuple[str, ...]
    record_present: bool
    sealed: bool
    replayable: bool
    source_present: bool = False
    queue_present: bool = False
    complete: bool = False
    cleanup_required: bool = False
    bounded_segment_count: int = 0
    bounded_attempt_count: int = 0

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationProjection("
            f"outcome_status={self.outcome_status!r}, sealed={self.sealed!r}, "
            "protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "outcome_status": self.outcome_status,
            "failure_stage": self.failure_stage,
            "reason_ids": list(self.reason_ids),
            "record_present": self.record_present,
            "sealed": self.sealed,
            "replayable": self.replayable,
            "source_present": self.source_present,
            "queue_present": self.queue_present,
            "complete": self.complete,
            "cleanup_required": self.cleanup_required,
            "bounded_segment_count": self.bounded_segment_count,
            "bounded_attempt_count": self.bounded_attempt_count,
        }


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationEvidence:
    base: dict[str, object] = field(repr=False)
    segments: tuple[dict[str, object], ...] = field(repr=False)
    seal: dict[str, object] | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationEvidence("
            f"segment_count={len(self.segments)}, sealed={self.seal is not None}, "
            "protected_content_omitted=True)"
        )

    @property
    def replayable(self) -> bool:
        return self.seal is not None


def _validate_b1_job_mapping(value: object) -> tuple[str, ...]:
    if type(value) is not dict:
        return ("durable_finalization_job_shape_invalid",)
    reasons: list[str] = []
    if len(value) != len(DURABLE_JOB_FIELDS) or set(value) != DURABLE_JOB_FIELDS:
        reasons.append("durable_finalization_job_shape_mismatch")
    fixed = {
        "schema_version": DURABLE_JOB_SCHEMA,
        "dispatch_key_version": DISPATCH_KEY_VERSION,
        "candidate_schema_version": "relaymem.slp_enqueue_candidate.v0",
        "candidate_kind": "relayslp_deferred_job",
        "trigger_mode": "turn_end",
        "source_event_kind": "turn",
        "state": "queued",
        "record_revision": 0,
        "attempt_count": 0,
        "claim_generation": 0,
        "claim_owner": "",
        "lease_token": "",
        "retry_class": "unclassified",
        "failure_class": "none",
        "terminal_reason_id": "",
    }
    for key, expected in fixed.items():
        if value.get(key) != expected:
            reasons.append(f"durable_finalization_job_{key}_mismatch")
    for key in (
        "created_at", "updated_at", "lease_acquired_at", "lease_expires_at",
        "retry_not_before",
    ):
        if value.get(key) is not None:
            reasons.append(f"durable_finalization_job_{key}_invalid")
    for key in (
        "run_id", "namespace", "source_admission_status",
        "runtime_terminal_status", "persistence_policy_status",
    ):
        if not is_token(value.get(key)):
            reasons.append(f"durable_finalization_job_{key}_invalid")
    session_id = value.get("session_id")
    if session_id is not None and not is_token(session_id):
        reasons.append("durable_finalization_job_session_id_invalid")
    if type(value.get("turn_index")) is not int or value.get("turn_index", -1) < 0:
        reasons.append("durable_finalization_job_turn_index_invalid")
    if type(value.get("source_count")) is not int or not 1 <= value.get("source_count", 0) <= 32:
        reasons.append("durable_finalization_job_source_count_invalid")
    if not is_sha256(value.get("source_lineage_fingerprint")):
        reasons.append("durable_finalization_job_lineage_invalid")
    try:
        dispatch = value.get("dispatch_idempotency_key")
        if dispatch != derive_dispatch_key(value):
            reasons.append("durable_finalization_dispatch_identity_mismatch")
        if value.get("job_id") != derive_job_id(str(dispatch)):
            reasons.append("durable_finalization_job_id_mismatch")
    except (KeyError, TypeError, ValueError):
        reasons.append("durable_finalization_job_identity_invalid")
    return dedupe(tuple(reasons))


def _validate_common(
    value: Mapping[str, object], fields: frozenset[str], kind: RecordKind
) -> tuple[str, ...]:
    reasons: list[str] = []
    if len(value) != len(fields) or set(value) != fields:
        reasons.append(f"durable_finalization_{kind}_shape_mismatch")
    if value.get("schema_version") != RECORD_SCHEMA:
        reasons.append("durable_finalization_schema_unsupported")
    if value.get("runtime_private") is not True:
        reasons.append("durable_finalization_runtime_private_required")
    if value.get("content_included") is not True:
        reasons.append("durable_finalization_content_required")
    if value.get("record_kind") != kind:
        reasons.append("durable_finalization_record_kind_mismatch")
    if value.get("record_revision") != RECORD_REVISION:
        reasons.append("durable_finalization_revision_mismatch")
    reasons.extend(
        validate_correlation(
            value.get("run_id"), value.get("turn_index"), value.get("character_id")
        )
    )
    locator = value.get("locator_digest")
    if not _is_digest(locator):
        reasons.append("durable_finalization_locator_invalid")
    else:
        try:
            expected = derive_locator_digest(
                run_id=value.get("run_id"),
                turn_index=value.get("turn_index"),
                character_id=value.get("character_id"),
            )
        except ValueError:
            expected = None
        if expected is not None and locator != expected:
            reasons.append("durable_finalization_locator_correlation_mismatch")
    return dedupe(tuple(reasons))


def _correlation_mismatch(
    value: Mapping[str, object], base: Mapping[str, object]
) -> tuple[str, ...]:
    reasons: list[str] = []
    for key in (
        "record_revision", "locator_digest", "run_id", "turn_index", "character_id"
    ):
        if value.get(key) != base.get(key):
            reasons.append(f"durable_finalization_{key}_mismatch")
    return dedupe(tuple(reasons))


def _decode_b64_content(
    value: object,
    byte_count: object,
    prefix: str,
    *,
    allow_empty: bool,
) -> tuple[bytes | None, tuple[str, ...]]:
    reasons: list[str] = []
    if type(value) is not str:
        return None, (f"durable_finalization_{prefix}_encoding_invalid",)
    try:
        content = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError):
        return None, (f"durable_finalization_{prefix}_encoding_invalid",)
    if (not allow_empty and not content) or type(byte_count) is not int or byte_count < 0:
        reasons.append(f"durable_finalization_{prefix}_byte_count_invalid")
    elif len(content) != byte_count:
        reasons.append(f"durable_finalization_{prefix}_byte_count_mismatch")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        reasons.append(f"durable_finalization_{prefix}_utf8_invalid")
    return (content, ()) if not reasons else (None, dedupe(tuple(reasons)))


def _digest_without(value: Mapping[str, object], digest_field: str) -> str:
    body = {key: item for key, item in value.items() if key != digest_field}
    try:
        return hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    except (TypeError, ValueError, RecursionError, OverflowError):
        return ""


def _copy_json_mapping(value: Mapping[str, object]) -> dict[str, object]:
    try:
        encoded = canonical_json_bytes(value)
        decoded, reason = decode_canonical_json(encoded)
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise ValueError("durable_finalization_protected_mapping_invalid") from None
    if decoded is None or reason is not None:
        raise ValueError(reason or "durable_finalization_protected_mapping_invalid")
    return decoded


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_digest(value: object) -> None:
    if not _is_digest(value):
        raise ValueError("durable_finalization_locator_invalid")


__all__ = [
    "BASE_FIELDS",
    "FINALIZED_SOURCE_FIELDS",
    "LOCATOR_VERSION",
    "PROJECTION_SCHEMA",
    "RECORD_REVISION",
    "RECORD_SCHEMA",
    "SEGMENT_FIELDS",
    "SEAL_FIELDS",
    "ZERO_DIGEST",
    "RelayMEMSLPDurableFinalizationEvidence",
    "RelayMEMSLPDurableFinalizationProjection",
    "base_filename",
    "build_base_record",
    "build_seal_record",
    "build_segment_record",
    "canonical_json_bytes",
    "decode_canonical_json",
    "derive_locator_digest",
    "finalized_source_to_mapping",
    "record_content_bytes",
    "seal_filename",
    "segment_filename",
    "validate_base_record",
    "validate_finalized_source_mapping",
    "validate_seal_record",
    "validate_segment_chain",
    "validate_segment_record",
]
