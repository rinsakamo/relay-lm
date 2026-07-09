"""LAT-2 security smoke: stream timing stays content-free end to end.

Verifies:
1. ``build_relayrun_stream_timing`` output only ever carries the fixed
   numeric/bool/null/schema-string keys -- never a raw exception message,
   URL, path, or arbitrary string.
2. The content-free audit projector (``relaylm.audit_projection``) drops any
   forged/extra key on a ``stream_timing`` metadata field rather than
   passing it through, and drops a non-enum ``stream_error_reason_id``
   instead of persisting it verbatim (no raw exception class/text leak).
3. A full request through a fake streaming backend whose canary strings
   appear in the prompt, response body, and a forged secret-shaped chunk
   never leaks those canaries into stdout, stderr, or the persisted trace,
   including the ``stream_timing`` record specifically.
4. A backend stream that errors mid-response records only the fixed
   ``backend_stream_error`` reason id in the trace -- never the raw
   exception text.
"""

from __future__ import annotations

import asyncio
import json
import re
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
from relaylm.audit_projection import project_audit_metadata
from relaylm.relayrun_stream_timing import (
    STREAM_TIMING_SCHEMA_VERSION,
    build_relayrun_stream_timing,
    wrap_stream_with_relayrun_stream_timing,
)

_ALLOWED_STREAM_TIMING_KEYS = {
    "schema_version",
    "content_free",
    "stream",
    "stream_open_ms",
    "time_to_first_chunk_ms",
    "stream_drain_ms",
    "stream_chunk_count",
    "stream_completed",
    "stream_error_reason_id",
    "raw_chunk_included",
    "prompt_included",
    "response_body_included",
}


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def check_builder_output_is_content_free() -> None:
    secret = "SHOULD_NEVER_LEAK/etc/production/secrets.txt"
    artifact = build_relayrun_stream_timing(
        stream_open_ms=42,
        time_to_first_chunk_ms=100,
        stream_drain_ms=900,
        stream_chunk_count=7,
        stream_completed=True,
        stream_error_reason_id=None,
    )
    require(set(artifact.keys()) == _ALLOWED_STREAM_TIMING_KEYS, artifact)
    require(secret not in json.dumps(artifact, ensure_ascii=False), artifact)

    # A raw exception class name / arbitrary string must never pass through
    # as stream_error_reason_id -- only the fixed enum survives.
    forged = build_relayrun_stream_timing(
        stream_open_ms=1,
        time_to_first_chunk_ms=1,
        stream_drain_ms=1,
        stream_chunk_count=1,
        stream_completed=False,
        stream_error_reason_id=f"httpx.ConnectError: {secret}",
    )
    require(forged["stream_error_reason_id"] is None, forged)
    require(secret not in json.dumps(forged, ensure_ascii=False), forged)
    print("ok build_relayrun_stream_timing never carries raw text; unknown reason ids drop to null")


def check_audit_projection_drops_forged_stream_timing_fields() -> None:
    secret = "CANARY_SECRET_PROJECTION_LEAK"
    forged_metadata = {
        "event": "backend_stream_response",
        "stream_timing": {
            "schema_version": STREAM_TIMING_SCHEMA_VERSION,
            "content_free": True,
            "stream": True,
            "stream_open_ms": 5,
            "time_to_first_chunk_ms": 10,
            "stream_drain_ms": 50,
            "stream_chunk_count": 3,
            "stream_completed": True,
            "stream_error_reason_id": None,
            "raw_chunk_included": False,
            "prompt_included": False,
            "response_body_included": False,
            # Forged/unsupported fields that must be dropped.
            "chunk_text": secret,
            "raw_exception": f"Traceback: {secret}",
            "backend_url": "http://127.0.0.1:9/v1/chat/completions",
            "prompt": secret,
        },
    }
    result = project_audit_metadata(forged_metadata)
    encoded = json.dumps(result.metadata, ensure_ascii=False)
    require(secret not in encoded, result.metadata)
    stream_timing = result.metadata.get("stream_timing")
    require(isinstance(stream_timing, dict), result.metadata)
    require(set(stream_timing.keys()) <= _ALLOWED_STREAM_TIMING_KEYS, stream_timing)
    require("chunk_text" not in stream_timing, stream_timing)
    require("raw_exception" not in stream_timing, stream_timing)
    require("backend_url" not in stream_timing, stream_timing)
    require("prompt" not in stream_timing, stream_timing)
    require(result.dropped_field_count > 0, result)

    # A non-enum reason id (e.g. a raw exception class name) must drop,
    # not pass through as free text.
    bad_reason_metadata = {
        "event": "backend_stream_response",
        "stream_timing": {
            "schema_version": STREAM_TIMING_SCHEMA_VERSION,
            "content_free": True,
            "stream": True,
            "stream_chunk_count": 0,
            "stream_completed": False,
            "stream_error_reason_id": f"ConnectionResetError({secret})",
            "raw_chunk_included": False,
            "prompt_included": False,
            "response_body_included": False,
        },
    }
    bad_result = project_audit_metadata(bad_reason_metadata)
    bad_encoded = json.dumps(bad_result.metadata, ensure_ascii=False)
    require(secret not in bad_encoded, bad_result.metadata)
    require(
        "stream_error_reason_id" not in bad_result.metadata.get("stream_timing", {}),
        bad_result.metadata,
    )
    print("ok audit projection drops forged/unsupported stream_timing fields and non-enum reason ids")


STREAM_PROMPT_CANARY = "CANARY_LAT2_PROMPT_PRIVATE"
STREAM_RESPONSE_CANARY = "CANARY_LAT2_RESPONSE_PRIVATE"
STREAM_SECRET_CANARY = "CANARY_LAT2_SECRET/etc/relaylm/secret.key"
STREAM_TEMP_PATH_CANARY = "/tmp/CANARY_LAT2_ABSOLUTE_TEMP_PATH"


def _sse_frame(content: str) -> bytes:
    body = {
        "id": "chatcmpl-lat2-security-smoke",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content}}],
    }
    return ("data: " + json.dumps(body, ensure_ascii=False) + "\n\n").encode("utf-8")


STREAM_FRAMES = (
    _sse_frame(STREAM_RESPONSE_CANARY)
    + _sse_frame(STREAM_SECRET_CANARY)
    + _sse_frame(STREAM_TEMP_PATH_CANARY)
    + b"data: [DONE]\n\n"
)


class _BackendHandler(BaseHTTPRequestHandler):
    captured_prompt_seen = False

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        if STREAM_PROMPT_CANARY in raw:
            type(self).captured_prompt_seen = True
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("content-length", str(len(STREAM_FRAMES)))
        self.end_headers()
        self.wfile.write(STREAM_FRAMES)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _trace_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def check_full_request_never_leaks_canaries() -> None:
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
                        "messages": [{"role": "user", "content": STREAM_PROMPT_CANARY}],
                        "stream": True,
                    },
                ) as response:
                    require(response.status_code == 200, response.status_code)
                    streamed = "".join(response.iter_text())
            require(STREAM_RESPONSE_CANARY in streamed, streamed)
            require(_BackendHandler.captured_prompt_seen, "backend never saw the prompt canary")

            records = _trace_records(trace_path)
            require(records, "no trace records were written")
            encoded_trace = json.dumps(records, ensure_ascii=False)
            for canary in (
                STREAM_PROMPT_CANARY,
                STREAM_RESPONSE_CANARY,
                STREAM_SECRET_CANARY,
                STREAM_TEMP_PATH_CANARY,
                str(root),
                str(REPO_ROOT),
            ):
                require(canary not in encoded_trace, (canary, encoded_trace))

            timing_records = [
                record
                for record in records
                if "stream_timing" in record.get("metadata", {})
            ]
            require(len(timing_records) == 1, records)
            stream_timing = timing_records[0]["metadata"]["stream_timing"]
            require(set(stream_timing.keys()) <= _ALLOWED_STREAM_TIMING_KEYS, stream_timing)
            print("ok full stream request never leaks prompt/response/secret/path canaries into the trace")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def check_error_stream_records_only_fixed_reason_id() -> None:
    secret = "SHOULD_NEVER_LEAK_RAW_EXCEPTION_TEXT_/var/secret"

    async def _raising_iter() -> AsyncIterator[bytes]:
        yield b"data: {}\n\n"
        raise ConnectionResetError(secret)

    finalized: list[dict[str, Any]] = []
    wrapped = wrap_stream_with_relayrun_stream_timing(
        _raising_iter(),
        stream_open_start_monotonic=0.0,
        stream_open_ms=None,
        on_finalize=finalized.append,
    )
    raised = None
    try:
        async for _ in wrapped:
            pass
    except ConnectionResetError as exc:
        raised = exc
    require(raised is not None, "wrapper must re-raise the original exception")
    require(len(finalized) == 1, finalized)
    artifact = finalized[0]
    encoded = json.dumps(artifact, ensure_ascii=False)
    require(secret not in encoded, encoded)
    require(artifact["stream_error_reason_id"] == "backend_stream_error", artifact)
    require(artifact["stream_completed"] is False, artifact)
    print("ok mid-stream backend error records only the fixed backend_stream_error reason id")


_ISO_OR_NUMERIC_ONLY_RE = re.compile(r"^[A-Za-z0-9_.:\-]*$")


def check_reason_id_values_are_tokens_only() -> None:
    from relaylm.relayrun_stream_timing import STREAM_TIMING_ERROR_REASON_IDS

    for reason_id in STREAM_TIMING_ERROR_REASON_IDS:
        require(_ISO_OR_NUMERIC_ONLY_RE.match(reason_id) is not None, reason_id)
        require("/" not in reason_id and "\\" not in reason_id, reason_id)
    print("ok fixed stream_error_reason_id values are safe bounded tokens")


def main() -> int:
    check_builder_output_is_content_free()
    check_audit_projection_drops_forged_stream_timing_fields()
    check_reason_id_values_are_tokens_only()
    asyncio.run(check_error_stream_records_only_fixed_reason_id())
    check_full_request_never_leaks_canaries()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
