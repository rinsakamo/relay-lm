"""LAT-2 stream timing smoke: perceived-latency wrapper and trace wiring.

Verifies (measurement-only, no behavior assertions):
1. Wrapper unit level: the LAT-2 stream-timing wrapper passes chunk bytes
   through unchanged and in order, and reports a non-negative int
   ``time_to_first_chunk_ms``/``stream_drain_ms``, a correct
   ``stream_chunk_count``, and ``stream_completed`` true when the upstream
   iterator finishes normally.
2. Error paths: an upstream exception and an early ``aclose()`` (simulating
   client disconnect / generator close) each produce the matching fixed
   ``stream_error_reason_id`` and ``stream_completed`` false, without
   swallowing the original exception.
3. Full request through a fake streaming backend: the streamed body is
   byte-for-byte unaffected, and the persisted (content-free-projected)
   trace carries a second record with a numeric ``stream_timing`` artifact.
4. A non-streaming request through the same fixture is unaffected: its
   trace record has LAT-1's ``timing_summary`` and no ``stream_timing`` key.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
from collections.abc import AsyncIterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.relayrun_stream_timing import (
    STREAM_TIMING_SCHEMA_VERSION,
    wrap_stream_with_relayrun_stream_timing,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


async def _iter_bytes(chunks: list[bytes], *, delay_seconds: float = 0.0) -> AsyncIterator[bytes]:
    for chunk in chunks:
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        yield chunk


async def _collect(body_iter: AsyncIterator[bytes]) -> bytes:
    output = bytearray()
    async for chunk in body_iter:
        output.extend(chunk)
    return bytes(output)


async def check_wrapper_passthrough_and_timing() -> None:
    chunks = [b"chunk-one", b"chunk-two", b"chunk-three"]
    finalized: list[dict[str, Any]] = []
    wrapped = wrap_stream_with_relayrun_stream_timing(
        _iter_bytes(chunks, delay_seconds=0.001),
        stream_open_start_monotonic=_monotonic(),
        stream_open_ms=12,
        on_finalize=finalized.append,
    )
    output = await _collect(wrapped)
    require(output == b"".join(chunks), output)
    require(len(finalized) == 1, finalized)
    artifact = finalized[0]
    require(artifact["schema_version"] == STREAM_TIMING_SCHEMA_VERSION, artifact)
    require(artifact["content_free"] is True, artifact)
    require(artifact["stream"] is True, artifact)
    require(artifact["stream_open_ms"] == 12, artifact)
    for key in ("time_to_first_chunk_ms", "stream_drain_ms"):
        value = artifact[key]
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, artifact)
    require(artifact["stream_drain_ms"] >= artifact["time_to_first_chunk_ms"], artifact)
    require(artifact["stream_chunk_count"] == 3, artifact)
    require(artifact["stream_completed"] is True, artifact)
    require(artifact["stream_error_reason_id"] is None, artifact)
    require(artifact["raw_chunk_included"] is False, artifact)
    require(artifact["prompt_included"] is False, artifact)
    require(artifact["response_body_included"] is False, artifact)
    print("ok wrapper passes chunk bytes through unchanged and reports non-negative timing")


def _monotonic() -> float:
    import time

    return time.monotonic()


async def check_wrapper_empty_stream() -> None:
    finalized: list[dict[str, Any]] = []
    wrapped = wrap_stream_with_relayrun_stream_timing(
        _iter_bytes([]),
        stream_open_start_monotonic=_monotonic(),
        stream_open_ms=None,
        on_finalize=finalized.append,
    )
    output = await _collect(wrapped)
    require(output == b"", output)
    artifact = finalized[0]
    require(artifact["stream_chunk_count"] == 0, artifact)
    require(artifact["time_to_first_chunk_ms"] is None, artifact)
    require(artifact["stream_completed"] is True, artifact)
    require(artifact["stream_open_ms"] is None, artifact)
    print("ok wrapper handles a zero-chunk stream without a first-chunk timestamp")


async def check_wrapper_upstream_error() -> None:
    async def _raising_iter() -> AsyncIterator[bytes]:
        yield b"partial"
        raise RuntimeError("backend blew up mid-stream")

    finalized: list[dict[str, Any]] = []
    wrapped = wrap_stream_with_relayrun_stream_timing(
        _raising_iter(),
        stream_open_start_monotonic=_monotonic(),
        stream_open_ms=5,
        on_finalize=finalized.append,
    )
    raised = None
    collected = bytearray()
    try:
        async for chunk in wrapped:
            collected.extend(chunk)
    except RuntimeError as exc:
        raised = exc
    require(raised is not None and str(raised) == "backend blew up mid-stream", raised)
    require(bytes(collected) == b"partial", collected)
    require(len(finalized) == 1, finalized)
    artifact = finalized[0]
    require(artifact["stream_completed"] is False, artifact)
    require(artifact["stream_error_reason_id"] == "backend_stream_error", artifact)
    require(artifact["stream_chunk_count"] == 1, artifact)
    print("ok wrapper re-raises upstream exceptions and records backend_stream_error")


async def check_wrapper_generator_close() -> None:
    finalized: list[dict[str, Any]] = []
    wrapped = wrap_stream_with_relayrun_stream_timing(
        _iter_bytes([b"a", b"b", b"c"], delay_seconds=0.01),
        stream_open_start_monotonic=_monotonic(),
        stream_open_ms=None,
        on_finalize=finalized.append,
    )
    first = await wrapped.__anext__()
    require(first == b"a", first)
    await wrapped.aclose()
    require(len(finalized) == 1, finalized)
    artifact = finalized[0]
    require(artifact["stream_completed"] is False, artifact)
    require(artifact["stream_error_reason_id"] == "generator_close", artifact)
    require(artifact["stream_chunk_count"] == 1, artifact)
    print("ok wrapper records generator_close when the consumer closes early")


STREAM_FRAMES = (
    'data: {"id":"chatcmpl-lat2-smoke","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"hel"}}]}\n\n',
    'data: {"id":"chatcmpl-lat2-smoke","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"lo"}}]}\n\n',
    "data: [DONE]\n\n",
)
STREAM_BODY = "".join(STREAM_FRAMES).encode("utf-8")

NON_STREAM_BODY = json.dumps(
    {
        "id": "chatcmpl-lat2-smoke",
        "object": "chat.completion",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
        ],
    }
).encode("utf-8")


class _BackendHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        self.send_response(200)
        if payload.get("stream") is True:
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(STREAM_BODY)))
            self.end_headers()
            self.wfile.write(STREAM_BODY)
            return
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(NON_STREAM_BODY)))
        self.end_headers()
        self.wfile.write(NON_STREAM_BODY)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _trace_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def check_full_request_stream_timing_trace() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)
            cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
            cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
            trace_path = root / "trace.jsonl"
            cfg["trace"] = {"enabled": True, "path": str(trace_path)}
            cfg_path = root / "config.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

            with TestClient(create_app(str(cfg_path))) as client:
                with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": True,
                    },
                ) as response:
                    require(response.status_code == 200, response.status_code)
                    streamed = "".join(response.iter_text())
                require(streamed == STREAM_BODY.decode("utf-8"), streamed)

            records = _trace_records(trace_path)
            stream_response_records = [
                record
                for record in records
                if record.get("metadata", {}).get("event") == "backend_stream_response"
            ]
            require(len(stream_response_records) == 2, records)
            timing_records = [
                record
                for record in stream_response_records
                if "stream_timing" in record.get("metadata", {})
            ]
            require(len(timing_records) == 1, stream_response_records)
            stream_timing = timing_records[0]["metadata"]["stream_timing"]
            require(stream_timing["schema_version"] == STREAM_TIMING_SCHEMA_VERSION, stream_timing)
            require(stream_timing["stream"] is True, stream_timing)
            require(stream_timing["stream_completed"] is True, stream_timing)
            require(stream_timing["stream_chunk_count"] >= 1, stream_timing)
            # Optional numeric/reason fields are omitted (not null) by the
            # content-free projector when unset -- .get() covers both.
            require(stream_timing.get("stream_error_reason_id") is None, stream_timing)
            for key in ("stream_open_ms", "time_to_first_chunk_ms", "stream_drain_ms"):
                value = stream_timing.get(key)
                require(
                    value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0),
                    (key, stream_timing),
                )
            print("ok fake streaming backend produces numeric stream_timing via projected trace record")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def check_non_stream_request_untouched() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)
            cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
            cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
            trace_path = root / "trace.jsonl"
            cfg["trace"] = {"enabled": True, "path": str(trace_path)}
            cfg_path = root / "config.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

            with TestClient(create_app(str(cfg_path))) as client:
                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": False,
                    },
                )
            require(response.status_code == 200, response.text)

            records = _trace_records(trace_path)
            require(len(records) == 1, records)
            metadata = records[-1]["metadata"]
            require(metadata.get("event") == "backend_response", metadata)
            require("stream_timing" not in metadata, metadata)
            require(isinstance(metadata.get("relayrun_artifact", {}).get("timing_summary"), dict), metadata)
            print("ok non-stream request trace is unaffected: no stream_timing, LAT-1 timing_summary intact")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> int:
    asyncio.run(check_wrapper_passthrough_and_timing())
    asyncio.run(check_wrapper_empty_stream())
    asyncio.run(check_wrapper_upstream_error())
    asyncio.run(check_wrapper_generator_close())
    check_full_request_stream_timing_trace()
    check_non_stream_request_untouched()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
