from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig  # noqa: E402
from relaylm.diagnostics import RequestDiagnostics  # noqa: E402
from relaylm.relayctx_tts_adapter_handoff_runtime import (  # noqa: E402
    wrap_stream_with_tts_adapter_handoff,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN  # noqa: E402
from relaylm.trace_runtime import trace_runtime_event  # noqa: E402

VISIBLE_PREFIX = "安全な表示テキスト。"
VISIBLE_SECOND = "次の文です。"
INTERNAL_BODY = '{"ctx_working_update":"private"}'


class DummyPipelineContext:
    def __init__(self, *, request_id: str = "relayctx-tts-runtime-smoke") -> None:
        self.request_id = request_id
        self.node_results: list[Any] = []

    def record_node_result(self, result: Any) -> None:
        self.node_results.append(result)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def sse_content(content: str) -> bytes:
    body = {
        "id": "chatcmpl-smoke",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content}}],
    }
    return ("data: " + json.dumps(body, ensure_ascii=False) + "\n\n").encode("utf-8")


def sse_multi_content(first: str, second: str) -> bytes:
    body = {
        "id": "chatcmpl-smoke",
        "object": "chat.completion.chunk",
        "choices": [
            {"index": 0, "delta": {"content": first}},
            {"index": 1, "delta": {"content": second}},
        ],
    }
    return ("data: " + json.dumps(body, ensure_ascii=False) + "\n\n").encode("utf-8")


def sse_done() -> bytes:
    return b"data: [DONE]\n\n"


async def iter_bytes(chunks: list[bytes]) -> Any:
    for chunk in chunks:
        yield chunk


async def collect(body_iter: Any) -> bytes:
    output = bytearray()
    async for chunk in body_iter:
        output.extend(chunk)
    return bytes(output)


def node_names(node_results: list[Any] | tuple[Any, ...]) -> list[str]:
    return [result.node_name for result in node_results]


def log_by_node(ctx: DummyPipelineContext, node_name: str) -> dict[str, Any]:
    matches = [result for result in ctx.node_results if result.node_name == node_name]
    require(len(matches) == 1, [result.node_name for result in ctx.node_results])
    return matches[0].to_log_dict()


def assert_content_free(log: dict[str, Any]) -> None:
    encoded = json.dumps(log, ensure_ascii=False)
    require(VISIBLE_PREFIX not in encoded, encoded)
    require(VISIBLE_SECOND not in encoded, encoded)
    require(INTERNAL_BODY not in encoded, encoded)
    require(RELAYCTX_UPDATE_OPEN not in encoded, encoded)
    require("handoff_items" not in log.get("diagnostics", {}), log)
    require("hints" not in log.get("diagnostics", {}), log)


def assert_c2_node_names(actual_node_names: list[str]) -> None:
    require(
        actual_node_names
        == [
            "relayctx_tts_segmentation_hints",
            "relayctx_tts_adapter_handoff",
        ],
        actual_node_names,
    )


def assert_c2_nodes_only(ctx: DummyPipelineContext) -> None:
    assert_c2_node_names(node_names(ctx.node_results))


async def assert_runtime_handoff_dry_run_from_safe_visible_output() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_content(VISIBLE_SECOND), sse_done()]
    ctx = DummyPipelineContext()
    finalized: list[tuple[Any, ...]] = []
    c2_iter = wrap_stream_with_tts_adapter_handoff(
        iter_bytes(chunks),
        enabled=True,
        dry_run_only=True,
        b2_safe_visible_output_available=True,
        pipeline_context=ctx,
        on_finalize=finalized.append,
    )
    output = await collect(c2_iter)
    require(output == b"".join(chunks), output)
    assert_c2_nodes_only(ctx)
    require(len(finalized) == 1, finalized)
    assert_c2_node_names(node_names(finalized[0]))
    hint_log = log_by_node(ctx, "relayctx_tts_segmentation_hints")
    handoff_log = log_by_node(ctx, "relayctx_tts_adapter_handoff")
    require(hint_log["decision"] == "dry_run_ready", hint_log)
    require(hint_log["diagnostics"]["candidate_hint_count"] > 0, hint_log)
    require(hint_log["diagnostics"]["emitted_hint_count"] == 0, hint_log)
    require(handoff_log["decision"] == "dry_run_ready", handoff_log)
    require(handoff_log["diagnostics"]["handoff_candidate_count"] > 0, handoff_log)
    require(handoff_log["diagnostics"]["emitted_handoff_count"] == 0, handoff_log)
    assert_content_free(hint_log)
    assert_content_free(handoff_log)
    print("ok runtime TTS handoff dry-run consumes safe visible output")


async def assert_runtime_handoff_ready_without_tts_execution() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_done()]
    ctx = DummyPipelineContext()
    finalized: list[tuple[Any, ...]] = []
    c2_iter = wrap_stream_with_tts_adapter_handoff(
        iter_bytes(chunks),
        enabled=True,
        dry_run_only=False,
        b2_safe_visible_output_available=True,
        pipeline_context=ctx,
        on_finalize=finalized.append,
    )
    output = await collect(c2_iter)
    require(output == b"".join(chunks), output)
    assert_c2_nodes_only(ctx)
    require(len(finalized) == 1, finalized)
    assert_c2_node_names(node_names(finalized[0]))
    hint_log = log_by_node(ctx, "relayctx_tts_segmentation_hints")
    handoff_log = log_by_node(ctx, "relayctx_tts_adapter_handoff")
    require(hint_log["decision"] == "ready", hint_log)
    require(handoff_log["decision"] == "ready", handoff_log)
    require(handoff_log["diagnostics"]["emitted_handoff_count"] > 0, handoff_log)
    require(handoff_log["diagnostics"]["tts_execution_requested"] is False, handoff_log)
    require(handoff_log["diagnostics"]["audio_generation_requested"] is False, handoff_log)
    require(handoff_log["diagnostics"]["avatar_control_requested"] is False, handoff_log)
    require(handoff_log["diagnostics"]["persistence_allowed"] is False, handoff_log)
    assert_content_free(hint_log)
    assert_content_free(handoff_log)
    print("ok runtime TTS handoff ready records handoff without execution")


async def assert_stream_final_trace_records_c2_node_results() -> None:
    request_id = "relayctx-tts-runtime-final-trace-smoke"
    chunks = [sse_content(VISIBLE_PREFIX), sse_done()]
    with TemporaryDirectory() as tmp_dir:
        trace_path = Path(tmp_dir) / "trace.jsonl"
        config = RelayLMConfig(
            trace={"enabled": True, "path": str(trace_path)},
            backends={"default": {"base_url": "http://127.0.0.1:1234/v1"}},
            model_routes={"relaylm-companion": {"backend": "default"}},
        )
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model="relaylm-companion",
            mode_applied="memory_light",
            character_id="trace-smoke-character",
            stream_enabled=True,
            trace_enabled=True,
        )
        require(
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                message_count=1,
                response_present=False,
                metadata={
                    "event": "backend_stream_response",
                    "status_code": 200,
                    "content_type": "text/event-stream",
                },
            ),
            "failed to seed stream response trace",
        )
        ctx = DummyPipelineContext(request_id=request_id)
        output = await collect(
            wrap_stream_with_tts_adapter_handoff(
                iter_bytes(chunks),
                enabled=True,
                dry_run_only=False,
                b2_safe_visible_output_available=True,
                pipeline_context=ctx,
            )
        )
        require(output == b"".join(chunks), output)
        records = [
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        require(len(records) == 2, records)
        events = [record.get("metadata", {}).get("event") for record in records]
        require(events == ["backend_stream_response", "backend_stream_finalize"], events)
        final_nodes = records[1].get("metadata", {}).get("pipeline_node_results")
        require(isinstance(final_nodes, list), records[1])
        assert_c2_node_names([str(node.get("node_name")) for node in final_nodes])
        for node in final_nodes:
            require(isinstance(node, dict), node)
            assert_content_free(node)
        print("ok stream-final trace records C2 node results content-free")


async def assert_no_handoff_without_b2_safe_output() -> None:
    chunks = [
        sse_content(VISIBLE_PREFIX),
        sse_content(RELAYCTX_UPDATE_OPEN + INTERNAL_BODY),
        sse_done(),
    ]
    ctx = DummyPipelineContext()
    c2_iter = wrap_stream_with_tts_adapter_handoff(
        iter_bytes(chunks),
        enabled=True,
        dry_run_only=False,
        b2_safe_visible_output_available=False,
        pipeline_context=ctx,
    )
    output = await collect(c2_iter)
    require(output == b"".join(chunks), output)
    require(ctx.node_results == [], [result.node_name for result in ctx.node_results])
    print("ok runtime TTS handoff does not run without B2 safe output")


async def assert_no_handoff_when_disabled() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_done()]
    ctx = DummyPipelineContext()
    c2_iter = wrap_stream_with_tts_adapter_handoff(
        iter_bytes(chunks),
        enabled=False,
        dry_run_only=False,
        b2_safe_visible_output_available=True,
        pipeline_context=ctx,
    )
    output = await collect(c2_iter)
    require(output == b"".join(chunks), output)
    require(ctx.node_results == [], [result.node_name for result in ctx.node_results])
    print("ok runtime TTS handoff disabled mode is pass-through")


async def assert_invalid_safe_output_observation_blocks_handoff() -> None:
    chunks = [sse_multi_content(VISIBLE_PREFIX, VISIBLE_SECOND), sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_tts_adapter_handoff(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=False,
            b2_safe_visible_output_available=True,
            pipeline_context=ctx,
        )
    )
    require(output == b"".join(chunks), output)
    assert_c2_nodes_only(ctx)
    hint_log = log_by_node(ctx, "relayctx_tts_segmentation_hints")
    handoff_log = log_by_node(ctx, "relayctx_tts_adapter_handoff")
    require(hint_log["decision"] == "invalid_input", hint_log)
    require(handoff_log["decision"] == "invalid_input", handoff_log)
    require(handoff_log["diagnostics"]["emitted_handoff_count"] == 0, handoff_log)
    assert_content_free(hint_log)
    assert_content_free(handoff_log)
    print("ok runtime TTS handoff invalid observation blocks handoff")


async def main_async() -> None:
    await assert_runtime_handoff_dry_run_from_safe_visible_output()
    await assert_runtime_handoff_ready_without_tts_execution()
    await assert_stream_final_trace_records_c2_node_results()
    await assert_no_handoff_without_b2_safe_output()
    await assert_no_handoff_when_disabled()
    await assert_invalid_safe_output_observation_blocks_handoff()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
