from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_stream_suppression_runtime import (  # noqa: E402
    wrap_stream_with_relayctx_suppression,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_OPEN  # noqa: E402


VISIBLE_PREFIX = "安全な表示テキスト。"
INTERNAL_BODY = '{"ctx_working_update":"private"}'


class DummyPipelineContext:
    def __init__(self) -> None:
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


async def iter_with_error(chunks: list[bytes]) -> Any:
    for chunk in chunks:
        yield chunk
    raise RuntimeError("synthetic backend stream failure")


async def collect(body_iter: Any) -> bytes:
    output = bytearray()
    async for chunk in body_iter:
        output.extend(chunk)
    return bytes(output)


def node_log(ctx: DummyPipelineContext) -> dict[str, Any]:
    require(len(ctx.node_results) == 1, ctx.node_results)
    return ctx.node_results[0].to_log_dict()


def assert_content_free(log: dict[str, Any]) -> None:
    encoded = json.dumps(log, ensure_ascii=False)
    require(VISIBLE_PREFIX not in encoded, encoded)
    require(INTERNAL_BODY not in encoded, encoded)
    require(RELAYCTX_UPDATE_OPEN not in encoded, encoded)


async def assert_default_off_pass_through() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=False,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    require(output == b"".join(chunks), output)
    log = node_log(ctx)
    require(log["node_name"] == "relayctx_stream_suppression_gate", log)
    require(log["decision"] == "disabled", log)
    require(log["diagnostics"]["output_mutated"] is False, log)
    assert_content_free(log)
    print("ok runtime stream wrapper default-off pass-through")


async def assert_dry_run_pass_through_detection() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_content(RELAYCTX_UPDATE_OPEN + INTERNAL_BODY), sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=True,
            pipeline_context=ctx,
        )
    )
    require(output == b"".join(chunks), output)
    log = node_log(ctx)
    require(log["status"] == "blocked", log)
    require(log["decision"] == "dry_run_suppression_candidate", log)
    require(log["diagnostics"]["suppression_would_apply"] is True, log)
    require(log["diagnostics"]["output_mutated"] is False, log)
    assert_content_free(log)
    print("ok runtime stream wrapper dry-run-only pass-through with detection")


async def assert_apply_preserves_visible_prefix() -> None:
    chunks = [sse_content(VISIBLE_PREFIX), sse_content(RELAYCTX_UPDATE_OPEN + INTERNAL_BODY), sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    decoded = output.decode("utf-8")
    require(VISIBLE_PREFIX in decoded, decoded)
    require(RELAYCTX_UPDATE_OPEN not in decoded, decoded)
    require(INTERNAL_BODY not in decoded, decoded)
    require("[DONE]" in decoded, decoded)
    log = node_log(ctx)
    require(log["status"] == "applied", log)
    require(log["decision"] == "suppressed", log)
    require(log["diagnostics"]["suppression_applied"] is True, log)
    assert_content_free(log)
    print("ok runtime stream wrapper apply preserves visible prefix")


async def assert_apply_detects_marker_split_across_sse_frames() -> None:
    split_at = 10
    chunks = [
        sse_content(VISIBLE_PREFIX + RELAYCTX_UPDATE_OPEN[:split_at]),
        sse_content(RELAYCTX_UPDATE_OPEN[split_at:] + INTERNAL_BODY),
        sse_done(),
    ]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    decoded = output.decode("utf-8")
    require(VISIBLE_PREFIX in decoded, decoded)
    require(RELAYCTX_UPDATE_OPEN not in decoded, decoded)
    require(INTERNAL_BODY not in decoded, decoded)
    log = node_log(ctx)
    require(log["diagnostics"]["split_sentinel_detected"] is True, log)
    require(log["diagnostics"]["suppression_applied"] is True, log)
    print("ok runtime stream wrapper detects split marker across SSE frames")


async def assert_apply_detects_marker_split_across_bytes() -> None:
    frame = sse_content(VISIBLE_PREFIX + RELAYCTX_UPDATE_OPEN + INTERNAL_BODY)
    cut = frame.find(RELAYCTX_UPDATE_OPEN.encode("utf-8")) + 7
    chunks = [frame[:cut], frame[cut:], sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    decoded = output.decode("utf-8")
    require(VISIBLE_PREFIX in decoded, decoded)
    require(RELAYCTX_UPDATE_OPEN not in decoded, decoded)
    require(INTERNAL_BODY not in decoded, decoded)
    log = node_log(ctx)
    require(log["diagnostics"]["complete_sentinel_detected"] is True, log)
    print("ok runtime stream wrapper detects marker split across byte chunks")


async def assert_terminal_partial_marker_blocked() -> None:
    partial = RELAYCTX_UPDATE_OPEN[:12]
    chunks = [sse_content(VISIBLE_PREFIX + partial), sse_done()]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes(chunks),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    decoded = output.decode("utf-8")
    require(VISIBLE_PREFIX in decoded, decoded)
    require(partial not in decoded, decoded)
    log = node_log(ctx)
    require(log["decision"] == "partial_blocked", log)
    require(log["diagnostics"]["terminal_partial_sentinel"] is True, log)
    assert_content_free(log)
    print("ok runtime stream wrapper blocks terminal partial marker")


async def assert_invalid_decode_fails_closed() -> None:
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes([b"\xff\xfe\n\n", sse_content(VISIBLE_PREFIX)]),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    require(output == b"", output)
    log = node_log(ctx)
    require(log["status"] == "failed", log)
    require(log["decision"] == "invalid_input", log)
    assert_content_free(log)
    print("ok runtime stream wrapper invalid decode fails closed")


async def assert_multi_content_field_fails_closed() -> None:
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_bytes([sse_multi_content(VISIBLE_PREFIX, RELAYCTX_UPDATE_OPEN + INTERNAL_BODY), sse_done()]),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    require(output == b"", output)
    log = node_log(ctx)
    require(log["status"] == "failed", log)
    require(log["decision"] == "invalid_input", log)
    require("multiple_stream_content_fields" in log["blocked_reasons"], log)
    assert_content_free(log)
    print("ok runtime stream wrapper ambiguous multi-content frame fails closed")


async def assert_backend_iterator_error_has_no_duplicate_replay() -> None:
    chunks = [sse_content(VISIBLE_PREFIX)]
    ctx = DummyPipelineContext()
    output = await collect(
        wrap_stream_with_relayctx_suppression(
            iter_with_error(chunks),
            enabled=True,
            dry_run_only=False,
            pipeline_context=ctx,
        )
    )
    decoded = output.decode("utf-8")
    require(decoded.count(VISIBLE_PREFIX) <= 1, decoded)
    log = node_log(ctx)
    require(log["status"] == "failed", log)
    require("backend_stream_iterator_error" in log["blocked_reasons"], log)
    assert_content_free(log)
    print("ok runtime stream wrapper backend error has no duplicate replay")


async def main_async() -> None:
    await assert_default_off_pass_through()
    await assert_dry_run_pass_through_detection()
    await assert_apply_preserves_visible_prefix()
    await assert_apply_detects_marker_split_across_sse_frames()
    await assert_apply_detects_marker_split_across_bytes()
    await assert_terminal_partial_marker_blocked()
    await assert_invalid_decode_fails_closed()
    await assert_multi_content_field_fails_closed()
    await assert_backend_iterator_error_has_no_duplicate_replay()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
