from __future__ import annotations

import copy
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_slp_primary_worker_source import (
    SOURCE_FIELDS,
    SOURCE_SCHEMA,
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
    build_relaymem_slp_primary_worker_source,
    build_relaymem_slp_primary_worker_source_node_result,
    consume_relaymem_slp_primary_worker_source,
    validate_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import (
    DISPATCH_KEY_VERSION,
    DURABLE_JOB_SCHEMA,
    derive_dispatch_key,
    derive_job_id,
    format_timestamp,
)

RAW_USER = "remember the cobalt observatory launch plan"
RAW_ASSISTANT = "I will track the launch dependencies."
RAW_TITLE = "Cobalt observatory launch"
RAW_SUMMARY = "The user is coordinating the cobalt observatory launch plan."
NAMESPACE = "character:relay:primary"
RUN_ID = "run-c1-0"
SESSION_ID = "session-c1-0"
LINEAGE = "a" * 64
LEASE_TOKEN = "lease-c1-0-secret"


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def claimed_record(*, run_id: str = RUN_ID) -> dict[str, object]:
    now = datetime(2026, 6, 23, 0, 0, 0, tzinfo=timezone.utc)
    record: dict[str, object] = {
        "schema_version": DURABLE_JOB_SCHEMA,
        "job_id": "",
        "dispatch_idempotency_key": "",
        "dispatch_key_version": DISPATCH_KEY_VERSION,
        "candidate_schema_version": "relaymem.slp_enqueue_candidate.v0",
        "candidate_kind": "relayslp_deferred_job",
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "source_event_kind": "turn",
        "run_id": run_id,
        "turn_index": 7,
        "session_id": SESSION_ID,
        "namespace": NAMESPACE,
        "source_count": 1,
        "source_lineage_fingerprint": LINEAGE,
        "source_admission_status": "admitted_dry_run",
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
        "state": "claimed",
        "record_revision": 1,
        "created_at": format_timestamp(now),
        "updated_at": format_timestamp(now),
        "attempt_count": 1,
        "claim_generation": 1,
        "claim_owner": "worker-c1-0",
        "lease_token": LEASE_TOKEN,
        "lease_acquired_at": format_timestamp(now),
        "lease_expires_at": format_timestamp(now + timedelta(minutes=5)),
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_reason_id": "",
    }
    record["dispatch_idempotency_key"] = derive_dispatch_key(record)
    record["job_id"] = derive_job_id(str(record["dispatch_idempotency_key"]))
    return record


def source_payload(record: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": SOURCE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "run_id": record["run_id"],
        "turn_index": record["turn_index"],
        "session_id": record["session_id"],
        "namespace": record["namespace"],
        "source_event_kind": record["source_event_kind"],
        "source_count": record["source_count"],
        "source_lineage_fingerprint": record["source_lineage_fingerprint"],
        "relayscn_scene_policy_artifact": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.92,
                "stability": 0.89,
            },
            "scene_policy": {
                "relaymem_retrieval_scope": "project_context",
                "persistence_block": False,
                "persistence_block_reasons": [],
            },
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "relayemo_artifact": {
            "assistant_emotion_state": {"intensity": 0.67},
            "user_affect_estimate": {"confidence": 0.71, "mode": "engaged"},
        },
        "governed_messages": [
            {"role": "system", "content": "governed system context"},
            {"role": "user", "content": RAW_USER},
            {"role": "assistant", "content": RAW_ASSISTANT},
        ],
        "governed_experience_artifact": {
            "schema_version": "relaymem.governed_experience_summary.v0",
            "runtime_private": True,
            "content_included": True,
            "raw_source_text_included": False,
            "raw_message_history_included": False,
            "raw_affect_estimates_included": False,
            "summary_origin": "trusted_in_process_summary",
            "candidate_id": "primary_candidate:0",
            "source_event_kind": "turn",
            "namespace": NAMESPACE,
            "title": RAW_TITLE,
            "summary_text": RAW_SUMMARY,
            "summary_chars": len(RAW_SUMMARY),
            "valid": True,
            "blocked_reasons": [],
        },
    }


def build(
    payload: object,
    record: dict[str, object],
    scope: RelayMEMSLPPrimaryWorkerSourceScope,
):
    return build_relaymem_slp_primary_worker_source(
        payload,
        claimed_record=record,
        request_scope=scope,
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
    )


def assert_reason(result: object, reason: str) -> None:
    reasons = getattr(result, "blocked_reasons")
    require(reason in reasons, reasons)
    assert_content_free(getattr(result, "to_log_dict")())


def assert_content_free(value: object) -> None:
    text = repr(value)
    forbidden = {
        RAW_USER,
        RAW_ASSISTANT,
        RAW_TITLE,
        RAW_SUMMARY,
        NAMESPACE,
        RUN_ID,
        SESSION_ID,
        LINEAGE,
        LEASE_TOKEN,
        "slp-dispatch-v0:",
        "slp-job-v0:",
        "memory/mem/",
    }
    for token in forbidden:
        require(token not in text, (token, text))


def main() -> int:
    record = claimed_record()
    payload = source_payload(record)

    # 1. Valid exact source bundle and immutable snapshot.
    scope = RelayMEMSLPPrimaryWorkerSourceScope()
    valid = build(payload, record, scope)
    require(valid.status == "dry_run_ready", valid)
    require(type(valid.source) is RelayMEMSLPPrimaryWorkerSource, valid)
    require(set(valid.source.to_protected_runtime_dict()) == SOURCE_FIELDS, valid)
    payload["governed_messages"][1]["content"] = "mutated after build"
    require(
        valid.source.to_protected_runtime_dict()["governed_messages"][1]["content"]
        == RAW_USER,
        "source snapshot must be detached and immutable",
    )
    exact, errors = validate_relaymem_slp_primary_worker_source(
        valid.source,
        claimed_record=record,
        request_scope=scope,
    )
    require(exact is valid.source and not errors, errors)
    print("ok valid exact request-local source bundle")

    # 2. Unknown source field rejected.
    unknown = source_payload(record)
    unknown["unexpected_content_field"] = RAW_USER
    assert_reason(build(unknown, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_shape_mismatch")
    print("ok unknown source field rejected")

    # 3. bool/int confusion rejected for both counters.
    bool_turn = source_payload(record)
    bool_turn["turn_index"] = True
    assert_reason(build(bool_turn, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_turn_index_invalid")
    bool_count = source_payload(record)
    bool_count["source_count"] = True
    assert_reason(build(bool_count, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_count_invalid")
    print("ok bool and int remain distinct")

    # 4. Missing field rejected.
    missing = source_payload(record)
    del missing["relayemo_artifact"]
    assert_reason(build(missing, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_shape_mismatch")
    print("ok missing source field rejected")

    # 5-7. Fixed schema and private/content markers fail closed.
    wrong_schema = source_payload(record)
    wrong_schema["schema_version"] = "relaymem.slp_primary_worker_source.v1"
    assert_reason(build(wrong_schema, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_schema_mismatch")
    not_private = source_payload(record)
    not_private["runtime_private"] = False
    assert_reason(build(not_private, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_runtime_private_required")
    no_content = source_payload(record)
    no_content["content_included"] = False
    assert_reason(build(no_content, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_content_required")
    print("ok schema and private content markers are exact")

    # 8. Job identity mismatch.
    other = claimed_record(run_id="run-other-job")
    bad_job = source_payload(record)
    bad_job["job_id"] = other["job_id"]
    assert_reason(build(bad_job, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_job_dispatch_identity_mismatch")
    print("ok job mismatch rejected")

    # 9. Dispatch identity mismatch with an internally matching foreign pair.
    bad_dispatch = source_payload(record)
    bad_dispatch["dispatch_idempotency_key"] = other["dispatch_idempotency_key"]
    bad_dispatch["job_id"] = other["job_id"]
    dispatch_result = build(bad_dispatch, record, RelayMEMSLPPrimaryWorkerSourceScope())
    require(
        "worker_source_dispatch_key_mismatch" in dispatch_result.blocked_reasons
        and "worker_source_job_id_mismatch" in dispatch_result.blocked_reasons,
        dispatch_result,
    )
    print("ok dispatch mismatch rejected")

    # 10-14. Exact claimed-record correlation.
    correlation_cases = (
        ("run_id", "run-foreign", "worker_source_run_id_mismatch"),
        ("turn_index", 8, "worker_source_turn_index_mismatch"),
        ("session_id", "session-foreign", "worker_source_session_id_mismatch"),
        ("namespace", "character:foreign:primary", "worker_source_namespace_mismatch"),
        ("source_lineage_fingerprint", "b" * 64, "worker_source_lineage_mismatch"),
    )
    for field_name, replacement, reason in correlation_cases:
        case = source_payload(record)
        case[field_name] = replacement
        if field_name == "namespace":
            case["governed_experience_artifact"]["namespace"] = replacement
        result = build(case, record, RelayMEMSLPPrimaryWorkerSourceScope())
        assert_reason(result, reason)
    print("ok run turn session namespace and lineage correlation are exact")

    # 15. Governed message shape mismatch.
    bad_message = source_payload(record)
    bad_message["governed_messages"][1]["name"] = "unknown"
    assert_reason(build(bad_message, record, RelayMEMSLPPrimaryWorkerSourceScope()), "governed_message_field_set_mismatch")
    print("ok governed message boundary is exact")

    # 16. Governed experience shape and cross-field mismatch.
    bad_experience = source_payload(record)
    bad_experience["governed_experience_artifact"]["summary_chars"] = True
    assert_reason(build(bad_experience, record, RelayMEMSLPPrimaryWorkerSourceScope()), "governed_experience_summary_chars_mismatch")
    bad_experience_namespace = source_payload(record)
    bad_experience_namespace["governed_experience_artifact"]["namespace"] = "character:other:primary"
    assert_reason(build(bad_experience_namespace, record, RelayMEMSLPPrimaryWorkerSourceScope()), "worker_source_experience_namespace_mismatch")
    print("ok governed experience boundary is exact")

    # 17. Cross-request, consumed, and stale sources are rejected.
    cross_scope = RelayMEMSLPPrimaryWorkerSourceScope()
    _, cross_errors = validate_relaymem_slp_primary_worker_source(
        valid.source,
        claimed_record=record,
        request_scope=cross_scope,
    )
    require(cross_errors == ("cross_request_source_rejected",), cross_errors)
    consumed, consume_errors = consume_relaymem_slp_primary_worker_source(
        valid.source,
        claimed_record=record,
        request_scope=scope,
    )
    require(consumed is valid.source and not consume_errors, consume_errors)
    _, reused_errors = validate_relaymem_slp_primary_worker_source(
        valid.source,
        claimed_record=record,
        request_scope=scope,
    )
    require(reused_errors == ("worker_source_already_consumed",), reused_errors)
    stale_scope = RelayMEMSLPPrimaryWorkerSourceScope()
    stale_result = build(source_payload(record), record, stale_scope)
    require(stale_result.source is not None, stale_result)
    stale_scope.close()
    _, stale_errors = validate_relaymem_slp_primary_worker_source(
        stale_result.source,
        claimed_record=record,
        request_scope=stale_scope,
    )
    require(stale_errors == ("request_scope_stale",), stale_errors)
    generic, generic_errors = validate_relaymem_slp_primary_worker_source(
        stale_result.source.to_protected_runtime_dict(),
        claimed_record=record,
        request_scope=RelayMEMSLPPrimaryWorkerSourceScope(),
    )
    require(generic is None and generic_errors == ("exact_worker_source_required",), generic_errors)
    print("ok stale consumed cross-request and generic lookalike sources rejected")

    # 18-19. Public projection, result and PipelineNodeResult stay content-free.
    assert_content_free(valid.to_log_dict())
    assert_content_free(valid.to_runtime_dict())
    node = build_relaymem_slp_primary_worker_source_node_result(valid)
    assert_content_free(node.to_log_dict())
    require(node.artifacts[0]["source_omitted"] is True, node)
    malformed_secret = source_payload(record)
    malformed_secret["governed_messages"] = [{"role": "user", "content": RAW_USER, "secret": RAW_SUMMARY}]
    secret_result = build(malformed_secret, record, RelayMEMSLPPrimaryWorkerSourceScope())
    assert_content_free(secret_result.to_log_dict())
    require(RAW_USER not in repr(secret_result.blocked_reasons), secret_result)
    print("ok public trace node and errors contain no protected content")

    # 20. Default-off/dry-run-first and no I/O/worker/memory side effect.
    disabled = build_relaymem_slp_primary_worker_source(
        source_payload(record),
        claimed_record=record,
        request_scope=RelayMEMSLPPrimaryWorkerSourceScope(),
    )
    require(disabled.status == "disabled" and disabled.source is None, disabled)
    blocked_apply = build_relaymem_slp_primary_worker_source(
        source_payload(record),
        claimed_record=record,
        request_scope=RelayMEMSLPPrimaryWorkerSourceScope(),
        enabled=True,
        dry_run_only=False,
        apply_enabled=False,
    )
    require(blocked_apply.status == "blocked", blocked_apply)
    with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
        no_io = build(
            source_payload(record), record, RelayMEMSLPPrimaryWorkerSourceScope()
        )
    runtime = no_io.to_runtime_dict()
    require(runtime["queue_io_performed"] is False, runtime)
    require(runtime["worker_invoked"] is False, runtime)
    require(runtime["writes_memory"] is False, runtime)
    require(runtime["mutates_soul"] is False, runtime)
    require(runtime["changes_visible_response"] is False, runtime)
    print("ok default-off dry-run-first and side-effect-free C1-0 boundary")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
