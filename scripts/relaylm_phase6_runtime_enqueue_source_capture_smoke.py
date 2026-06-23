"""Functional and leakage smoke for Phase 6 I1-B runtime enqueue wiring."""
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.config import BackendConfig
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_finalized_turn_source import (
    RelayMEMSLPFinalizedTurnSourceResult,
    build_relaymem_slp_finalized_turn_source,
    build_relaymem_slp_finalized_turn_source_node_result,
)
from relaylm.relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_queue_record import record_filename
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    apply_relaymem_slp_runtime_enqueue,
    build_relaymem_slp_runtime_enqueue_node_result,
)
from relaylm.relaymem_slp_runtime_finalization import (
    RelayMEMSLPFinalizedVisibleTextCapture,
    wrap_stream_with_relaymem_slp_finalized_turn_capture,
)
from relaylm.routing import ResolvedRoute

USER_CANARY = "CANARY_RUNTIME_USER_MESSAGE_DO_NOT_LEAK"
ASSISTANT_CANARY = "CANARY_RUNTIME_ASSISTANT_RESPONSE_DO_NOT_LEAK"
SUMMARY_CANARY = "CANARY_RUNTIME_MEMORY_SUMMARY_DO_NOT_LEAK"
NAMESPACE_CANARY = "CANARY_RUNTIME_NAMESPACE_DO_NOT_LEAK"
DISPATCH_CANARY = "CANARY_RUNTIME_DISPATCH_KEY_DO_NOT_LEAK"
LINEAGE_CANARY = "CANARY_RUNTIME_SOURCE_LINEAGE_DO_NOT_LEAK"
CHARACTER_ID = "character-e"
RUN_ID = "run-e-1"
SESSION_ID = "session-e-1"


class ResultLookalike(dict[str, object]):
    pass


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def route() -> ResolvedRoute:
    backend = BackendConfig(base_url="http://127.0.0.1:1234/v1")
    return ResolvedRoute(
        route_model="relay-e",
        backend_name="local",
        backend=backend,
        backend_model="backend-model",
        character_id=CHARACTER_ID,
        mode_requested="memory_light",
        mode_applied="memory_light",
        cache_namespace="cache-e",
        memory_namespace=NAMESPACE_CANARY,
        session_id=SESSION_ID,
        client_history_exclusion_preflight_enabled=True,
    )


def context(*, run_id: str = RUN_ID, request_id: str = "request-e-1") -> PipelineContext:
    payload = {
        "model": "relay-e",
        "messages": [{"role": "user", "content": USER_CANARY}],
    }
    return PipelineContext(
        request_id=request_id,
        run_id=run_id,
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=route(),
        stream_enabled=False,
    )


def scene() -> dict[str, object]:
    return {
        "scene_state": {
            "scene_type": "implementation_work",
            "confidence": 0.99,
            "stability": 0.99,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def emo() -> dict[str, object]:
    return {
        "assistant_emotion_state": {"intensity": 0.2},
        "user_affect_estimate": {"confidence": 0.8, "mode": "engaged"},
    }


def finalized(
    *,
    assistant_text: str = ASSISTANT_CANARY,
    run_id: str = RUN_ID,
    request_id: str = "request-e-1",
) -> RelayMEMSLPFinalizedTurnSourceResult:
    return build_relaymem_slp_finalized_turn_source(
        context(run_id=run_id, request_id=request_id),
        assistant_visible_text=assistant_text,
        status_code=200,
        resolved_session_id=SESSION_ID,
        relayscn_scene_policy_artifact=scene(),
        relayemo_artifact=emo(),
        response_finalized=True,
        enabled=True,
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
        RUN_ID,
        SESSION_ID,
        "slp-dispatch-v0:",
        "slp-job-v0:",
    }
    for token in forbidden:
        require(token not in text, (token, text))


def claim(root: Path, queued: dict[str, object]) -> dict[str, object]:
    result = transition_relaymem_slp_queue_state(
        RelayMEMSLPQueueTransitionRequest(
            transition_kind="claim",
            job_id=str(queued["job_id"]),
            dispatch_idempotency_key=str(queued["dispatch_idempotency_key"]),
            expected_record_revision=int(queued["record_revision"]),
            expected_state="queued",
            claim_owner="worker-e",
            claim_generation=int(queued["claim_generation"]),
            lease_duration_seconds=60,
        ),
        queue_root=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(result.status == "applied", result.to_log_dict())
    require(type(result.durable_record) is dict, result.to_log_dict())
    return result.durable_record


def test_source_and_modes() -> None:
    source = finalized()
    require(source.status == "ready", source.to_log_dict())
    require(source.source is not None, source.to_log_dict())
    require(source.source.turn_index == 0, source.source)
    require(source.source.persistence_policy_status == "allowed", source.source)
    protected = source.source.governed_experience_artifact
    require(USER_CANARY in str(protected["title"]), protected)
    require(ASSISTANT_CANARY in str(protected["summary_text"]), protected)
    assert_content_free(source)
    assert_content_free(source.to_log_dict())
    assert_content_free(build_relaymem_slp_finalized_turn_source_node_result(source).to_log_dict())

    disabled = apply_relaymem_slp_runtime_enqueue(
        ResultLookalike(), registry=None, queue_root=None
    )
    require(disabled.status == "disabled", disabled.to_log_dict())

    invalid = apply_relaymem_slp_runtime_enqueue(
        source.to_log_dict(),
        registry=None,
        queue_root=None,
        enabled=True,
    )
    require(invalid.status == "blocked", invalid.to_log_dict())
    require(
        "exact_finalized_turn_source_result_required" in invalid.blocked_reasons,
        invalid.to_log_dict(),
    )

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        dry = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(dry.status == "dry_run_ready", dry.to_log_dict())
        require(not list(root.iterdir()), root)
        require(registry.size == 0, registry)
        require(dry.protected_source_payload is not None, dry.to_log_dict())
        require(dry.to_log_dict()["typed_source_built"] is False, dry.to_log_dict())
        require(dry.to_log_dict()["worker_ready"] is False, dry.to_log_dict())
        assert_content_free(dry)
        assert_content_free(dry.to_log_dict())
        assert_content_free(build_relaymem_slp_runtime_enqueue_node_result(dry).to_log_dict())
        if dry.source_scope is not None:
            dry.source_scope.close()


def test_apply_duplicate_collision_and_consume() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        source = finalized()
        applied = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(applied.status == "enqueued", applied.to_log_dict())
        require(applied.enqueue_result is not None, applied.to_log_dict())
        require(applied.enqueue_result.status == "enqueued_new", applied.to_log_dict())
        require(applied.source_retention_result is not None, applied.to_log_dict())
        require(applied.source_retention_result.status == "published_new", applied.to_log_dict())
        require(registry.size == 1, registry)
        require(len(list(root.glob("slp-dispatch-v0-*.json"))) == 1, root)
        require(applied.to_log_dict()["source_retained"] is True, applied.to_log_dict())
        require(applied.to_log_dict()["worker_ready"] is False, applied.to_log_dict())

        duplicate = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(duplicate.status == "duplicate_existing", duplicate.to_log_dict())
        require(registry.size == 1, registry)

        different = finalized(assistant_text="different protected assistant body")
        collision = apply_relaymem_slp_runtime_enqueue(
            different,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(collision.status == "source_retention_failed", collision.to_log_dict())
        require(
            "protected_source_capture_collision" in collision.blocked_reasons,
            collision.to_log_dict(),
        )
        require(registry.size == 1, registry)

        queued = applied.enqueue_result.durable_record
        require(type(queued) is dict, applied.to_log_dict())
        claimed = claim(root, queued)
        consumed = registry.consume_for_claim(
            claimed_record=claimed,
            character_id=CHARACTER_ID,
        )
        require(consumed.status == "consumed", consumed.to_log_dict())
        require(type(consumed.source) is RelayMEMSLPPrimaryWorkerSource, consumed.to_log_dict())
        require(registry.size == 0, registry)
        runtime = consumed.source.to_protected_runtime_dict()
        require(runtime["governed_messages"][0]["content"] == USER_CANARY, runtime)
        require(runtime["governed_messages"][1]["content"] == ASSISTANT_CANARY, runtime)
        assert_content_free(consumed)
        assert_content_free(consumed.to_log_dict())
        consumed.release_transferred_scope()
        unavailable = registry.consume_for_claim(
            claimed_record=claimed,
            character_id=CHARACTER_ID,
        )
        require(unavailable.status == "source_unavailable", unavailable.to_log_dict())


def test_correlation_failure_and_lifetime() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        source = finalized()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        applied = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(applied.enqueue_result is not None, applied.to_log_dict())
        record = applied.enqueue_result.durable_record
        payload = applied.protected_source_payload
        require(type(record) is dict and type(payload) is dict, applied.to_log_dict())
        for field_name, wrong_value in {
            "run_id": "run-wrong",
            "turn_index": 9,
            "session_id": "session-wrong",
            "namespace": "namespace-wrong",
            "source_count": 2,
            "source_lineage_fingerprint": "b" * 64,
        }.items():
            modified = dict(payload)
            modified[field_name] = wrong_value
            isolated = RelayMEMSLPPrimaryWorkerSourceRegistry()
            scope = RelayMEMSLPPrimaryWorkerSourceScope()
            result = isolated.publish(
                source_payload=modified,
                durable_record=record,
                request_scope=scope,
                character_id=CHARACTER_ID,
            )
            require(result.status == "blocked", (field_name, result.to_log_dict()))
            require(
                f"protected_source_{field_name}_mismatch" in result.blocked_reasons,
                (field_name, result.to_log_dict()),
            )
            scope.close()

        released = registry.release(
            durable_record=record,
            character_id=CHARACTER_ID,
        )
        require(released.status == "released", released.to_log_dict())
        require(registry.size == 0, registry)

    clock = [1.0]
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry(
            ttl_seconds=2,
            clock=lambda: clock[0],
        )
        applied = apply_relaymem_slp_runtime_enqueue(
            finalized(run_id="run-ttl", request_id="request-ttl"),
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(applied.status == "enqueued", applied.to_log_dict())
        clock[0] = 4.0
        require(registry.size == 0, registry)


def test_enqueue_and_retention_failures() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        source = finalized(run_id="run-corrupt", request_id="request-corrupt")
        dry = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
            queue_root=str(root),
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(dry.dispatch_result is not None and dry.dispatch_result.durable_job is not None, dry.to_log_dict())
        dispatch_key = dry.dispatch_result.durable_job.dispatch_idempotency_key
        (root / record_filename(dispatch_key)).write_bytes(b"not canonical json")
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        failed = apply_relaymem_slp_runtime_enqueue(
            source,
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(failed.status == "enqueue_failed", failed.to_log_dict())
        require(registry.size == 0, registry)
        if dry.source_scope is not None:
            dry.source_scope.close()

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry(max_entries=1)
        first = apply_relaymem_slp_runtime_enqueue(
            finalized(run_id="run-cap-1", request_id="request-cap-1"),
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(first.status == "enqueued", first.to_log_dict())
        second = apply_relaymem_slp_runtime_enqueue(
            finalized(run_id="run-cap-2", request_id="request-cap-2"),
            registry=registry,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(second.status == "source_retention_failed", second.to_log_dict())
        require(
            "protected_source_registry_capacity_reached" in second.blocked_reasons,
            second.to_log_dict(),
        )
        require(second.enqueue_result is not None, second.to_log_dict())
        require(second.enqueue_result.status == "enqueued_new", second.to_log_dict())
        require(second.to_log_dict()["worker_ready"] is False, second.to_log_dict())
        assert_content_free(second)
        assert_content_free(second.to_log_dict())


def test_stream_observer() -> None:
    frames = (
        b'data: {"choices":[{"delta":{"content":"hello "}}]}\n\n',
        b'data: {"choices":[{"delta":{"content":"world"}}]}\n\n',
        b"data: [DONE]\n\n",
    )

    async def body():
        for frame in frames:
            yield frame

    async def collect():
        capture = RelayMEMSLPFinalizedVisibleTextCapture()
        output = []
        async for frame in wrap_stream_with_relaymem_slp_finalized_turn_capture(
            body(), capture=capture
        ):
            output.append(frame)
        return output, capture

    output, capture = asyncio.run(collect())
    require(tuple(output) == frames, output)
    require(capture.finalized_text() == "hello world", capture)
    assert_content_free(capture)


def run_all() -> None:
    test_source_and_modes()
    test_apply_duplicate_collision_and_consume()
    test_correlation_failure_and_lifetime()
    test_enqueue_and_retention_failures()
    test_stream_observer()


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
