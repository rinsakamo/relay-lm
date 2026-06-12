from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import BackendConfig
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_node_result import build_pipeline_node_result
from relaylm.routing import ResolvedRoute


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _route() -> ResolvedRoute:
    return ResolvedRoute(
        route_model="relaylm-default",
        backend_name="local_backend",
        backend=BackendConfig(base_url="http://127.0.0.1:1234/v1"),
        backend_model="local-model",
        character_id=None,
        mode_requested="pass_through",
        mode_applied="pass_through",
        cache_namespace=None,
        memory_namespace=None,
    )


def _context(*, request_id: str, run_id: str) -> PipelineContext:
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    return PipelineContext(
        request_id=request_id,
        run_id=run_id,
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=_route(),
        stream_enabled=False,
    )


def _assert_request_local_default_collection() -> None:
    first = _context(request_id="request-1", run_id="run-1")
    second = _context(request_id="request-2", run_id="run-2")

    require(first.node_results == [], first.node_results)
    require(second.node_results == [], second.node_results)
    require(first.node_results is not second.node_results, "node_results must be request-local")

    first.record_node_result(
        build_pipeline_node_result(
            node_name="relayint_reference_repair",
            status="diagnostic_only",
            decision="record_only",
        )
    )

    require(len(first.node_results) == 1, first.node_results)
    require(second.node_results == [], second.node_results)
    print("ok PipelineContext node_results collection is request-local")


def _assert_recording_order_and_serialization() -> None:
    context = _context(request_id="request-order", run_id="run-order")
    first = build_pipeline_node_result(
        node_name="relayint_reference_repair",
        status="diagnostic_only",
        decision="inspect_reference",
        diagnostics={"unresolved_reference_detected": True},
    )
    second = build_pipeline_node_result(
        node_name="relayctx_repack",
        status="applied",
        decision="payload_repacked",
        artifacts=({"schema_version": "relayctx.repack.v0"},),
    )

    context.record_node_result(first)
    context.record_node_result(second)

    require(context.node_results == [first, second], context.node_results)
    serialized = context.node_results_to_log_dicts()
    require([item["node_name"] for item in serialized] == [
        "relayint_reference_repair",
        "relayctx_repack",
    ], serialized)
    require(serialized[0]["decision"] == "inspect_reference", serialized)
    require(serialized[1]["status"] == "applied", serialized)

    serialized[0]["diagnostics"]["serialized_mutation"] = True
    serialized[1]["artifacts"][0]["serialized_mutation"] = True
    require(
        context.node_results[0].diagnostics
        == {"unresolved_reference_detected": True},
        context.node_results[0],
    )
    require(
        context.node_results[1].artifacts
        == [{"schema_version": "relayctx.repack.v0"}],
        context.node_results[1],
    )
    print("ok PipelineContext preserves node result order and detached logs")


def _assert_recording_does_not_mutate_payload_state() -> None:
    context = _context(request_id="request-payload", run_id="run-payload")
    original_forwarded = dict(context.forwarded_payload)
    original_last_mutating_step = context.last_mutating_step

    context.record_node_result(
        build_pipeline_node_result(
            node_name="backend_forward",
            status="diagnostic_only",
            decision="not_routed",
        )
    )

    require(context.forwarded_payload == original_forwarded, context.forwarded_payload)
    require(context.last_mutating_step == original_last_mutating_step, context.last_mutating_step)
    require(len(context.node_results) == 1, context.node_results)
    print("ok PipelineContext recording does not mutate payload routing state")


def _assert_ctx_candidate_is_detached_and_request_local() -> None:
    first = _context(request_id="request-candidate-1", run_id="run-candidate-1")
    second = _context(request_id="request-candidate-2", run_id="run-candidate-2")
    candidate = {
        "current_topic": "RelayCTX Unpack",
        "referable_items": [{"label": "candidate", "kind": "component"}],
    }

    first.set_ctx_working_update_candidate(candidate)
    candidate["current_topic"] = "caller mutation"
    candidate["referable_items"][0]["label"] = "caller mutation"

    require(
        first.ctx_working_update_candidate
        == {
            "current_topic": "RelayCTX Unpack",
            "referable_items": [{"label": "candidate", "kind": "component"}],
        },
        first.ctx_working_update_candidate,
    )
    require(second.ctx_working_update_candidate is None, second.ctx_working_update_candidate)

    first.set_ctx_working_update_candidate(None)
    require(first.ctx_working_update_candidate is None, first.ctx_working_update_candidate)
    print("ok PipelineContext RelayCTX candidate is detached and request-local")


def main() -> None:
    _assert_request_local_default_collection()
    _assert_recording_order_and_serialization()
    _assert_recording_does_not_mutate_payload_state()
    _assert_ctx_candidate_is_detached_and_request_local()


if __name__ == "__main__":
    main()
