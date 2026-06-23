"""Smoke coverage for Phase 6 I1-B enqueue and protected source capture."""
from __future__ import annotations

import hashlib
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
)
from relaylm.relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_queue_record import (
    canonical_json_bytes,
    record_filename,
)
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    apply_relaymem_slp_runtime_enqueue,
    build_relaymem_slp_runtime_enqueue_node_result,
)

USER_CANARY = "CANARY_RUNTIME_USER_MESSAGE_DO_NOT_LEAK"
ASSISTANT_CANARY = "CANARY_RUNTIME_ASSISTANT_RESPONSE_DO_NOT_LEAK"
SUMMARY_CANARY = "CANARY_RUNTIME_MEMORY_SUMMARY_DO_NOT_LEAK"
NAMESPACE_CANARY = "CANARY_RUNTIME_NAMESPACE_DO_NOT_LEAK"
DISPATCH_CANARY = "CANARY_RUNTIME_DISPATCH_KEY_DO_NOT_LEAK"
LINEAGE_CANARY = "CANARY_RUNTIME_SOURCE_LINEAGE_DO_NOT_LEAK"
LINEAGE = hashlib.sha256(LINEAGE_CANARY.encode("utf-8")).hexdigest()
CHARACTER_ID = "character-e"


class PayloadLookalike(dict[str, object]):
    pass


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def lineage(*, namespace: str = NAMESPACE_CANARY, value: str = LINEAGE) -> dict[str, object]:
    return {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": "turn",
        "namespace": namespace,
        "valid": True,
        "lineage_fingerprint": value,
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": True,
            "session_id_present": True,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }


def experience(*, summary: str = SUMMARY_CANARY) -> dict[str, object]:
    return build_relaymem_governed_experience_summary(
        candidate_id="primary_candidate:e",
        source_event_kind="turn",
        namespace=NAMESPACE_CANARY,
        title="Protected runtime memory",
        summary_text=summary,
    )


def source_inputs(*, summary: str = SUMMARY_CANARY) -> dict[str, object]:
    return {
        "relayscn_scene_policy_artifact": {
            "scene_state": {
                "scene_type": "implementation_work",
                "private_note": DISPATCH_CANARY,
            },
            "scene_policy": {
                "persistence_block": False,
                "persistence_block_reasons": [],
            },
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "relayemo_artifact": {
            "assistant_emotion_state": {"intensity": 0.2},
            "user_affect_estimate": {"confidence": 0.8},
        },
        "governed_messages": [
            {"role": "user", "content": USER_CANARY},
            {"role": "assistant", "content": ASSISTANT_CANARY},
        ],
        "governed_experience_artifact": experience(summary=summary),
    }


def run_enqueue(
    root: Path,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    *,
    run_id: str = "run-e-1",
    turn_index: int = 1,
    session_id: str = "session-e-1",
    enabled: bool = True,
    dry_run_only: bool = False,
    apply_enabled: bool = True,
    summary: str = SUMMARY_CANARY,
):
    return apply_relaymem_slp_runtime_enqueue(
        registry=registry,
        queue_root=str(root),
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        character_id=CHARACTER_ID,
        run_id=run_id,
        turn_index=turn_index,
        session_id=session_id,
        namespace=NAMESPACE_CANARY,
        source_lineage_artifact=lineage(),
        source_count=1,
        visible_response_finalized=True,
        **source_inputs(summary=summary),
    )


def assert_content_free(value: object) -> None:
    text = repr(value)
    forbidden = {
        USER_CANARY,
        ASSISTANT_CANARY,
        SUMMARY_CANARY,
        NAMESPACE_CANARY,
        DISPATCH_CANARY,
        LINEAGE_CANARY,
        LINEAGE,
        "slp-dispatch-v0:",
        "slp-job-v0:",
        "session-e-1",
        "run-e-1",
    }
    for token in forbidden:
        require(token not in text, (token, text))


def claim(root: Path, queued: dict[str, object]) -> dict[str, object]:
    request = RelayMEMSLPQueueTransitionRequest(
        transition_kind="claim",
        job_id=str(queued["job_id"]),
        dispatch_idempotency_key=str(queued["dispatch_idempotency_key"]),
        expected_record_revision=int(queued["record_revision"]),
        expected_state="queued",
        claim_owner="worker-e",
        claim_generation=int(queued["claim_generation"]),
        lease_duration_seconds=60,
    )
    result = transition_relaymem_slp_queue_state(
        request,
        queue_root=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(result.status == "applied", result.to_log_dict())
    require(type(result.durable_record) is dict, result.to_log_dict())
    return result.durable_record


def test_disabled_and_dry_run() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        disabled = run_enqueue(
            root,
            registry,
            enabled=False,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(disabled.status == "disabled", disabled.to_log_dict())
        require(not list(root.iterdir()), root)
        require(registry.size == 0, registry)
        require(disabled.protected_source_payload is None, disabled.to_log_dict())

        dry_run = run_enqueue(
            root,
            registry,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(dry_run.status == "dry_run_ready", dry_run.to_log_dict())
        require(dry_run.protected_source_payload is not None, dry_run.to_log_dict())
        require(dry_run.enqueue_result is None, dry_run.to_log_dict())
        require(not list(root.iterdir()), root)
        require(registry.size == 0, registry)
        projection = dry_run.to_log_dict()
        require(projection["source_capture_built"] is True, projection)
        require(projection["typed_source_built"] is False, projection)
        require(projection["worker_ready"] is False, projection)
        assert_content_free(projection)
        assert_content_free(dry_run)
        if dry_run.source_scope is not None:
            dry_run.source_scope.close()


def test_apply_duplicate_mismatch_and_consume() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        applied = run_enqueue(root, registry)
        require(applied.status == "enqueued", applied.to_log_dict())
        require(applied.enqueue_result is not None, applied.to_log_dict())
        require(applied.enqueue_result.status == "enqueued_new", applied.to_log_dict())
        require(applied.source_retention_result is not None, applied.to_log_dict())
        require(applied.source_retention_result.status == "published_new", applied.to_log_dict())
        require(registry.size == 1, registry)
        require(len(list(root.glob("slp-dispatch-v0-*.json"))) == 1, root)
        projection = applied.to_log_dict()
        require(projection["source_retained"] is True, projection)
        require(projection["worker_ready"] is False, projection)
        assert_content_free(projection)
        assert_content_free(applied)
        assert_content_free(build_relaymem_slp_runtime_enqueue_node_result(applied).to_log_dict())
        assert_content_free(registry)

        duplicate = run_enqueue(root, registry)
        require(duplicate.status == "duplicate_existing", duplicate.to_log_dict())
        require(duplicate.enqueue_result is not None, duplicate.to_log_dict())
        require(duplicate.enqueue_result.status == "duplicate_existing", duplicate.to_log_dict())
        require(duplicate.source_retention_result is not None, duplicate.to_log_dict())
        require(
            duplicate.source_retention_result.status == "duplicate_existing",
            duplicate.to_log_dict(),
        )
        require(registry.size == 1, registry)

        mismatch = run_enqueue(root, registry, summary="different protected source")
        require(mismatch.status == "source_retention_failed", mismatch.to_log_dict())
        require(mismatch.failure_stage == "source_retention", mismatch.to_log_dict())
        require(
            "protected_source_capture_collision" in mismatch.blocked_reasons,
            mismatch.to_log_dict(),
        )
        require(registry.size == 1, registry)

        queued = applied.enqueue_result.durable_record
        require(type(queued) is dict, applied.to_log_dict())
        claimed = claim(root, queued)
        wrong_character = registry.consume_for_claim(
            claimed_record=claimed,
            character_id="character-wrong",
        )
        require(wrong_character.status == "blocked", wrong_character.to_log_dict())
        require(registry.size == 1, registry)

        consumed = registry.consume_for_claim(
            claimed_record=claimed,
            character_id=CHARACTER_ID,
        )
        require(consumed.status == "consumed", consumed.to_log_dict())
        require(type(consumed.source) is RelayMEMSLPPrimaryWorkerSource, consumed.to_log_dict())
        require(registry.size == 0, registry)
        protected = consumed.source.to_protected_runtime_dict()
        require(protected["governed_messages"][0]["content"] == USER_CANARY, "source mismatch")
        require(
            protected["governed_experience_artifact"]["summary_text"] == SUMMARY_CANARY,
            "summary mismatch",
        )
        assert_content_free(consumed)
        assert_content_free(consumed.to_log_dict())
        consumed.release_transferred_scope()

        unavailable = registry.consume_for_claim(
            claimed_record=claimed,
            character_id=CHARACTER_ID,
        )
        require(unavailable.status == "source_unavailable", unavailable.to_log_dict())


def test_correlation_lookalike_release_and_lifetime() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        applied = run_enqueue(root, registry, run_id="run-e-correlation")
        require(applied.status == "enqueued", applied.to_log_dict())
        require(applied.enqueue_result is not None, applied.to_log_dict())
        record = applied.enqueue_result.durable_record
        payload = applied.protected_source_payload
        require(type(record) is dict and type(payload) is dict, applied.to_log_dict())

        fields = {
            "run_id": "run-wrong",
            "turn_index": 999,
            "session_id": "session-wrong",
            "namespace": "namespace-wrong",
            "source_count": 2,
            "source_lineage_fingerprint": "b" * 64,
        }
        for field_name, wrong_value in fields.items():
            modified = dict(payload)
            modified[field_name] = wrong_value
            isolated = RelayMEMSLPPrimaryWorkerSourceRegistry()
            result = isolated.publish(
                source_payload=modified,
                durable_record=record,
                request_scope=applied.source_scope,
                character_id=CHARACTER_ID,
            )
            require(result.status == "blocked", (field_name, result.to_log_dict()))
            require(
                f"protected_source_{field_name}_mismatch" in result.blocked_reasons,
                (field_name, result.to_log_dict()),
            )
            require(isolated.size == 0, isolated)

        lookalike = RelayMEMSLPPrimaryWorkerSourceRegistry().publish(
            source_payload=PayloadLookalike(payload),
            durable_record=record,
            request_scope=applied.source_scope,
            character_id=CHARACTER_ID,
        )
        require(lookalike.status == "blocked", lookalike.to_log_dict())
        require(
            "exact_protected_source_payload_required" in lookalike.blocked_reasons,
            lookalike.to_log_dict(),
        )

        released = registry.release(
            durable_record=record,
            character_id=CHARACTER_ID,
        )
        require(released.status == "released", released.to_log_dict())
        require(registry.size == 0, registry)
        require(applied.source_scope is not None and not applied.source_scope.active, registry)

    clock = [10.0]
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        ttl_registry = RelayMEMSLPPrimaryWorkerSourceRegistry(
            ttl_seconds=5,
            clock=lambda: clock[0],
        )
        retained = run_enqueue(root, ttl_registry, run_id="run-e-ttl")
        require(retained.status == "enqueued", retained.to_log_dict())
        require(ttl_registry.size == 1, ttl_registry)
        clock[0] = 16.0
        require(ttl_registry.size == 0, ttl_registry)
        require(retained.source_scope is not None and not retained.source_scope.active, ttl_registry)


def test_enqueue_failures_and_retention_failure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        dry = run_enqueue(
            root,
            RelayMEMSLPPrimaryWorkerSourceRegistry(),
            dry_run_only=True,
            apply_enabled=False,
            run_id="run-e-corrupt",
        )
        require(dry.dispatch_result is not None, dry.to_log_dict())
        require(dry.dispatch_result.durable_job is not None, dry.to_log_dict())
        dispatch_key = dry.dispatch_result.durable_job.dispatch_idempotency_key
        (root / record_filename(dispatch_key)).write_bytes(b"not canonical json")
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        corrupt = run_enqueue(root, registry, run_id="run-e-corrupt")
        require(corrupt.status == "enqueue_failed", corrupt.to_log_dict())
        require(corrupt.failure_stage == "enqueue", corrupt.to_log_dict())
        require(registry.size == 0, registry)
        if dry.source_scope is not None:
            dry.source_scope.close()

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry(max_entries=1)
        first = run_enqueue(root, registry, run_id="run-e-capacity-1", turn_index=1)
        require(first.status == "enqueued", first.to_log_dict())
        second = run_enqueue(
            root,
            registry,
            run_id="run-e-capacity-2",
            turn_index=2,
            session_id="session-e-2",
        )
        require(second.status == "source_retention_failed", second.to_log_dict())
        require(second.failure_stage == "source_retention", second.to_log_dict())
        require(
            "protected_source_registry_capacity_reached" in second.blocked_reasons,
            second.to_log_dict(),
        )
        require(second.enqueue_result is not None, second.to_log_dict())
        require(second.enqueue_result.status == "enqueued_new", second.to_log_dict())
        require(second.to_log_dict()["source_retained"] is False, second.to_log_dict())
        require(second.to_log_dict()["worker_ready"] is False, second.to_log_dict())
        require(len(list(root.glob("slp-dispatch-v0-*.json"))) == 2, root)
        assert_content_free(second)
        assert_content_free(second.to_log_dict())

    missing_root = Path("/definitely/missing/relaylm-phase6-e")
    registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
    failed = run_enqueue(missing_root, registry, run_id="run-e-write-failure")
    require(failed.status == "enqueue_failed", failed.to_log_dict())
    require(registry.size == 0, registry)
    assert_content_free(failed.to_log_dict())


def run_all() -> None:
    test_disabled_and_dry_run()
    test_apply_duplicate_mismatch_and_consume()
    test_correlation_lookalike_release_and_lifetime()
    test_enqueue_failures_and_retention_failure()


def main() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        run_all()
    assert_content_free(stdout.getvalue())
    assert_content_free(stderr.getvalue())
    print("Phase 6 runtime enqueue source capture smoke passed")


if __name__ == "__main__":
    main()
