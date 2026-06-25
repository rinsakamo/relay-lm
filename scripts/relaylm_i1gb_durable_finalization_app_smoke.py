"""I1-GB ASGI response-ordering, stream admission, and leakage smoke."""
from __future__ import annotations

import asyncio
import base64
import json
import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import yaml

import relaylm.app as app_module
from relaylm.app import create_app
from relaylm.config import BackendConfig, ModelRoute, RelayLMConfig
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_durable_finalization_publication import (
    RelayMEMSLPDurableFinalizationError,
    RelayMEMSLPDurableFinalizationPreparedTurnHolder,
    start_relaymem_slp_durable_finalization_stream,
)
from relaylm.relaymem_slp_durable_finalization_store import (
    RelayMEMSLPDurableFinalizationStoreResult,
)
from relaylm.relaymem_slp_runtime_finalization import (
    RelayMEMSLPFinalizedVisibleTextCapture,
    wrap_stream_with_relaymem_slp_finalized_turn_capture,
)
from relaylm.routing import ResolvedRoute

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_CANARY = "CANARY_I1GB_APP_USER_DO_NOT_LEAK"
ASSISTANT_CANARY = "CANARY_I1GB_APP_ASSISTANT_DO_NOT_LEAK"
NAMESPACE_CANARY = "CANARY_I1GB_APP_NAMESPACE_DO_NOT_LEAK"
PATH_CANARY = "CANARY_I1GB_APP_PATH_DO_NOT_LEAK"

NON_STREAM_BODY = {
    "id": "chatcmpl-i1gb",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": ASSISTANT_CANARY},
            "finish_reason": "stop",
        }
    ],
}
LF_FRAMES = (
    'data: {"id":"chatcmpl-i1gb","choices":[{"delta":{"content":"hello "}}]}\n\n',
    ': keepalive\n\n',
    'data: {"id":"chatcmpl-i1gb","choices":[{"delta":{"content":"world"}}]}\n\n',
    "data: [DONE]\n\n",
)
LF_STREAM_BODY = "".join(LF_FRAMES).encode("utf-8")


class _BackendHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if payload.get("stream") is True:
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-cache")
            self.end_headers()
            # Deliberately split inside frames and combine later frames.
            raw = LF_STREAM_BODY
            for part in (raw[:11], raw[11:67], raw[67:121], raw[121:]):
                self.wfile.write(part)
                self.wfile.flush()
            return
        encoded = json.dumps(NON_STREAM_BODY).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("x-backend-i1gb", "preserved")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    backend_port: int,
    mode: str,
    queue_root: Path,
    protected_root: Path,
    finalization_root: Path | None,
    pass_through: bool = False,
    relayemo: bool = False,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text("utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = (
        f"http://127.0.0.1:{backend_port}/v1"
    )
    cfg["trace"] = {"enabled": False, "path": None}
    cfg["model_routes"]["relaylm-default"].update(
        {
            "mode": "pass_through" if pass_through else "memory_light",
            "character_id": "default",
            "memory_namespace": NAMESPACE_CANARY,
            "session_id": "session-i1gb-app",
        }
    )
    cfg["relaymem_slp_queue_root"] = str(queue_root.resolve())
    cfg["relaymem_slp_protected_source_root"] = str(protected_root.resolve())
    cfg["relaymem_slp_runtime_enqueue_enabled"] = mode == "apply"
    cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = mode != "apply"
    cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = mode == "apply"
    cfg["relaymem_slp_durable_finalization_enabled"] = mode in {"dry-run", "apply"}
    cfg["relaymem_slp_durable_finalization_dry_run_only"] = mode != "apply"
    cfg["relaymem_slp_durable_finalization_apply_enabled"] = mode == "apply"
    cfg["relaymem_slp_durable_finalization_root"] = (
        str(finalization_root.resolve()) if finalization_root is not None else None
    )
    cfg["relayemo_enabled"] = relayemo
    cfg["relayemo_text_marker_enabled"] = relayemo
    cfg["relayemo_text_marker_apply_mode"] = "apply" if relayemo else "diagnostics_only"
    cfg["memory"].update(
        {
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(*, stream: bool, user: str = USER_CANARY) -> dict[str, object]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": user}],
        "stream": stream,
        "metadata": {
            "scene_state": {
                "schema_version": "relayscn.scene_state.v0",
                "scene_type": "design_talk",
                "confidence": 0.99,
                "stability": 0.99,
                "signals": [],
            }
        },
    }


async def _invoke_asgi(
    app: Any,
    payload: dict[str, object],
    *,
    before_send: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> list[dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    events: list[dict[str, Any]] = []
    request_sent = False
    blocker = asyncio.Event()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await blocker.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if before_send is not None:
            await before_send(message)
        events.append(dict(message))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/chat/completions",
        "raw_path": b"/v1/chat/completions",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
        "state": {},
    }
    await app(scope, receive, send)
    return events


def _response(events: list[dict[str, Any]]) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    starts = [event for event in events if event.get("type") == "http.response.start"]
    require(len(starts) == 1, events)
    bodies = [event for event in events if event.get("type") == "http.response.body"]
    return (
        int(starts[0]["status"]),
        list(starts[0].get("headers", [])),
        b"".join(event.get("body", b"") for event in bodies),
    )


def _files(root: Path, suffix: str) -> list[Path]:
    return sorted(root.glob(f"durable-finalization-v0-*.{suffix}.json"))


def _seal(root: Path) -> dict[str, object]:
    seals = _files(root, "seal")
    require(len(seals) == 1, list(root.iterdir()))
    return json.loads(seals[0].read_text("utf-8"))


def _visible_text(seal: dict[str, object]) -> str:
    return base64.b64decode(str(seal["visible_content_b64"])).decode("utf-8")


def _assert_public_content_free(value: object) -> None:
    text = repr(value)
    for canary in (
        USER_CANARY,
        ASSISTANT_CANARY,
        NAMESPACE_CANARY,
        PATH_CANARY,
        "slp-job-v0:",
        "slp-dispatch-v0:",
    ):
        require(canary not in text, (canary, text))


def test_nonstream_app(backend_port: int) -> None:
    with TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)

        async def run_mode(mode: str) -> tuple[bytes, list[tuple[bytes, bytes]], Path]:
            mode_root = root / mode
            queue = mode_root / "queue"
            protected = mode_root / "protected"
            finalization = mode_root / "finalization"
            for item in (queue, protected, finalization):
                item.mkdir(parents=True, exist_ok=True)
            config = mode_root / "config.yaml"
            _write_config(
                config,
                backend_port=backend_port,
                mode=mode,
                queue_root=queue,
                protected_root=protected,
                finalization_root=finalization,
            )
            app = create_app(str(config))
            first_body_seen = False

            async def observe(message: dict[str, Any]) -> None:
                nonlocal first_body_seen
                if message.get("type") != "http.response.body" or first_body_seen:
                    return
                first_body_seen = True
                if mode == "apply":
                    # 3. valid seal exists before first body; C1-5/B2 do not yet.
                    require(len(_files(finalization, "seal")) == 1, list(finalization.iterdir()))
                    require(not list(queue.iterdir()), list(queue.iterdir()))
                    require(not list(protected.iterdir()), list(protected.iterdir()))

            events = await _invoke_asgi(app, _payload(stream=False), before_send=observe)
            status, headers, body = _response(events)
            require(status == 200, (mode, status, body))
            if mode == "disabled":
                # 1. disabled unchanged.
                require(not list(finalization.iterdir()), list(finalization.iterdir()))
            elif mode == "dry-run":
                # 2. dry-run no file mutation and body is unchanged.
                require(not list(finalization.iterdir()), list(finalization.iterdir()))
            else:
                # 9-11. background remains C1-5 then B2 with exact B1 identity.
                seal = _seal(finalization)
                queue_files = list(queue.glob("slp-dispatch-v0-*.json"))
                source_files = list(protected.glob("protected-source-v0-*.json"))
                require(len(queue_files) == 1, list(queue.iterdir()))
                require(len(source_files) == 1, list(protected.iterdir()))
                queue_record = json.loads(queue_files[0].read_text("utf-8"))
                source_record = json.loads(source_files[0].read_text("utf-8"))
                require(queue_record["job_id"] == seal["job_id"], (queue_record, seal))
                require(
                    queue_record["dispatch_idempotency_key"]
                    == seal["dispatch_idempotency_key"],
                    (queue_record, seal),
                )
                require(source_record["job_id"] == seal["job_id"], source_record)
                require(
                    source_record["schema_version"]
                    == "relaymem.slp_protected_source_artifact.v0",
                    source_record,
                )
                require(
                    queue_record["schema_version"] == "relaymem.slp_durable_job.v0",
                    queue_record,
                )
            return body, headers, finalization

        disabled_body, disabled_headers, _ = asyncio.run(run_mode("disabled"))
        dry_body, dry_headers, _ = asyncio.run(run_mode("dry-run"))
        apply_body, apply_headers, apply_root = asyncio.run(run_mode("apply"))
        # 4-5. body bytes, status, and normal headers are preserved across gates.
        require(disabled_body == dry_body == apply_body, (disabled_body, dry_body, apply_body))
        require(json.loads(apply_body) == NON_STREAM_BODY, apply_body)
        header_sets = []
        for headers in (disabled_headers, dry_headers, apply_headers):
            values = dict(headers)
            require(values.get(b"content-type") == b"application/json", headers)
            require(values.get(b"x-relaylm-mode") == b"memory_light", headers)
            header_sets.append(
                set(values)
                - {b"x-relaylm-request-id", b"x-relaylm-run-id"}
            )
        require(header_sets[0] == header_sets[1] == header_sets[2], header_sets)
        require(_visible_text(_seal(apply_root)) == ASSISTANT_CANARY, _seal(apply_root))

        # 6. seal observes the final RelayEMO-transformed visible body.
        emo_root = root / "emo"
        queue = emo_root / "queue"
        protected = emo_root / "protected"
        finalization = emo_root / "finalization"
        for item in (queue, protected, finalization):
            item.mkdir(parents=True)
        config = emo_root / "config.yaml"
        _write_config(
            config,
            backend_port=backend_port,
            mode="apply",
            queue_root=queue,
            protected_root=protected,
            finalization_root=finalization,
            relayemo=True,
        )
        marker = "✨"
        with patch.object(
            app_module,
            "_build_relayemo_text_marker_preview",
            return_value={
                "gate_open": True,
                "marker": marker,
                "marker_count": 1,
                "placement": "postfix_replace_punctuation",
                "applied_to_text": False,
                "suppression_reason": None,
            },
        ):
            events = asyncio.run(_invoke_asgi(create_app(str(config)), _payload(stream=False)))
        status, _, body = _response(events)
        require(status == 200, body)
        transformed = json.loads(body)["choices"][0]["message"]["content"]
        require(marker in transformed, transformed)
        require(_visible_text(_seal(finalization)) == transformed, _seal(finalization))

        # 7-8. pre-body publication failure sends no original assistant byte and leaks nothing.
        failure_root = root / "failure"
        queue = failure_root / "queue"
        protected = failure_root / "protected"
        queue.mkdir(parents=True)
        protected.mkdir()
        missing = failure_root / PATH_CANARY
        config = failure_root / "config.yaml"
        _write_config(
            config,
            backend_port=backend_port,
            mode="apply",
            queue_root=queue,
            protected_root=protected,
            finalization_root=missing,
        )
        events = asyncio.run(_invoke_asgi(create_app(str(config)), _payload(stream=False)))
        status, headers, body = _response(events)
        require(status == 500, (status, body))
        public = body.decode("utf-8") + repr(headers)
        for forbidden in (
            USER_CANARY,
            ASSISTANT_CANARY,
            NAMESPACE_CANARY,
            PATH_CANARY,
            "slp-job-v0:",
            "slp-dispatch-v0:",
            "Traceback",
        ):
            require(forbidden not in public, (forbidden, public))
        require(not list(queue.iterdir()), list(queue.iterdir()))
        require(not list(protected.iterdir()), list(protected.iterdir()))

        # Invalid gate combinations fail closed before the original body is released.
        invalid_root = root / "invalid-gate"
        queue = invalid_root / "queue"
        protected = invalid_root / "protected"
        finalization = invalid_root / "finalization"
        for item in (queue, protected, finalization):
            item.mkdir(parents=True)
        config = invalid_root / "config.yaml"
        _write_config(
            config,
            backend_port=backend_port,
            mode="disabled",
            queue_root=queue,
            protected_root=protected,
            finalization_root=finalization,
        )
        cfg = yaml.safe_load(config.read_text("utf-8"))
        cfg["relaymem_slp_durable_finalization_dry_run_only"] = False
        config.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        events = asyncio.run(_invoke_asgi(create_app(str(config)), _payload(stream=False)))
        status, _, body = _response(events)
        require(status == 500, (status, body))
        require(ASSISTANT_CANARY.encode("utf-8") not in body, body)
        require(not list(finalization.iterdir()), list(finalization.iterdir()))

        # 12. pass-through route retains its exemption and creates no private record.
        pass_root = root / "pass"
        queue = pass_root / "queue"
        protected = pass_root / "protected"
        finalization = pass_root / "finalization"
        for item in (queue, protected, finalization):
            item.mkdir(parents=True)
        config = pass_root / "config.yaml"
        _write_config(
            config,
            backend_port=backend_port,
            mode="apply",
            queue_root=queue,
            protected_root=protected,
            finalization_root=finalization,
            pass_through=True,
        )
        events = asyncio.run(_invoke_asgi(create_app(str(config)), _payload(stream=False)))
        status, _, body = _response(events)
        require(status == 200 and json.loads(body) == NON_STREAM_BODY, body)
        require(not list(finalization.iterdir()), list(finalization.iterdir()))


def _direct_route() -> ResolvedRoute:
    return ResolvedRoute(
        route_model="relay-direct-i1gb",
        backend_name="local",
        backend=BackendConfig(base_url="http://127.0.0.1:1234/v1"),
        backend_model="backend",
        character_id="default",
        mode_requested="memory_light",
        mode_applied="memory_light",
        cache_namespace="cache-i1gb",
        memory_namespace=NAMESPACE_CANARY,
        session_id="session-i1gb-direct",
        client_history_exclusion_preflight_enabled=True,
    )


def _direct_context() -> PipelineContext:
    payload = {
        "model": "relay-direct-i1gb",
        "messages": [{"role": "user", "content": USER_CANARY}],
    }
    return PipelineContext(
        request_id="request-i1gb-direct",
        run_id="run-i1gb-direct",
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=_direct_route(),
        stream_enabled=True,
    )


def _direct_config(root: Path, **overrides: int) -> RelayLMConfig:
    values: dict[str, object] = {
        "backends": {"local": BackendConfig(base_url="http://127.0.0.1:1234/v1")},
        "model_routes": {"relay-direct-i1gb": ModelRoute(backend="local")},
        "relaymem_slp_runtime_enqueue_enabled": True,
        "relaymem_slp_runtime_enqueue_dry_run_only": False,
        "relaymem_slp_runtime_enqueue_apply_enabled": True,
        "relaymem_slp_queue_root": str((root / "queue").resolve()),
        "relaymem_slp_protected_source_root": str((root / "protected").resolve()),
        "relaymem_slp_durable_finalization_enabled": True,
        "relaymem_slp_durable_finalization_dry_run_only": False,
        "relaymem_slp_durable_finalization_apply_enabled": True,
        "relaymem_slp_durable_finalization_root": str((root / "finalization").resolve()),
    }
    values.update(overrides)
    return RelayLMConfig(**values)


def _direct_scene() -> dict[str, object]:
    return {
        "scene_state": {"scene_type": "design_talk", "confidence": 0.9},
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _failed_store_result(reason: str) -> RelayMEMSLPDurableFinalizationStoreResult:
    return RelayMEMSLPDurableFinalizationStoreResult(
        status="failed",
        durable=False,
        record_present=True,
        sealed=False,
        replayable=False,
        duplicate_existing=False,
        cleanup_required=False,
        bounded_segment_count=0,
        bounded_attempt_count=1,
        blocked_reasons=(reason,),
    )


async def _run_direct_stream(
    chunks: list[bytes],
    *,
    setup: Callable[[Any], None] | None = None,
    backend_error: BaseException | None = None,
    config_overrides: dict[str, int] | None = None,
) -> tuple[bytes, Path, Any, list[int]]:
    temp = TemporaryDirectory()
    root = Path(temp.name)
    for name in ("queue", "protected", "finalization"):
        (root / name).mkdir()
    config = _direct_config(root, **(config_overrides or {}))
    holder = RelayMEMSLPDurableFinalizationPreparedTurnHolder()
    session, result = start_relaymem_slp_durable_finalization_stream(
        config=config,
        pipeline_context=_direct_context(),
        status_code=200,
        resolved_session_id="session-i1gb-direct",
        relayscn_scene_policy_artifact=_direct_scene(),
        relayemo_artifact=None,
        holder=holder,
    )
    require(result.status == "published" and session is not None, result)
    if setup is not None:
        setup(session)

    async def source() -> AsyncIterator[bytes]:
        for index, chunk in enumerate(chunks):
            yield chunk
            if backend_error is not None and index == 0:
                raise backend_error

    capture = RelayMEMSLPFinalizedVisibleTextCapture()
    output = bytearray()
    segment_counts: list[int] = []
    try:
        async for part in wrap_stream_with_relaymem_slp_finalized_turn_capture(
            source(), capture=capture, durable_session=session
        ):
            output.extend(part)
            segment_counts.append(len(_files(root / "finalization", "segment-*")))
    finally:
        # Keep the TemporaryDirectory alive by attaching it to the session.
        session._smoke_temp = temp  # type: ignore[attr-defined]  # noqa: SLF001
    return bytes(output), root, session, segment_counts


def test_stream_app_and_direct(backend_port: int) -> None:
    # Actual ASGI send boundary: base/segments/seal exist at each body event.
    with TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        queue = root / "queue"
        protected = root / "protected"
        finalization = root / "finalization"
        for item in (queue, protected, finalization):
            item.mkdir()
        config = root / "config.yaml"
        _write_config(
            config,
            backend_port=backend_port,
            mode="apply",
            queue_root=queue,
            protected_root=protected,
            finalization_root=finalization,
        )
        sent = bytearray()
        protected_events = 0

        async def observe(message: dict[str, Any]) -> None:
            nonlocal protected_events
            if message.get("type") == "http.response.start":
                # 1. base is durable before any protected stream bytes.
                require(len(_files(finalization, "base")) == 1, list(finalization.iterdir()))
                require(not _files(finalization, "seal"), list(finalization.iterdir()))
                return
            if message.get("type") != "http.response.body":
                return
            body = message.get("body", b"")
            if not body:
                # 4. normal iterator completion cannot precede seal.
                require(len(_files(finalization, "seal")) == 1, list(finalization.iterdir()))
                return
            text = body.decode("utf-8")
            if '"content"' in text:
                protected_events += 1
                # 2. corresponding segment exists before send.
                require(
                    len(list(finalization.glob("*.segment-*.json"))) >= protected_events,
                    list(finalization.iterdir()),
                )
            if "[DONE]" in text:
                # 3. DONE never precedes seal.
                require(len(_files(finalization, "seal")) == 1, list(finalization.iterdir()))
            sent.extend(body)

        events = asyncio.run(
            _invoke_asgi(create_app(str(config)), _payload(stream=True), before_send=observe)
        )
        status, _, body = _response(events)
        # 5. concatenated bytes exactly preserved.
        require(status == 200, status)
        require(body == LF_STREAM_BODY == bytes(sent), (body, sent))
        require(len(list(finalization.glob("*.segment-*.json"))) == 2, list(finalization.iterdir()))
        seal = _seal(finalization)
        require(_visible_text(seal) == "hello world", seal)
        require(len(list(queue.glob("slp-dispatch-v0-*.json"))) == 1, list(queue.iterdir()))
        require(len(list(protected.glob("protected-source-v0-*.json"))) == 1, list(protected.iterdir()))

    async def direct_cases() -> None:
        # 6-12. split frame, multiple frames/chunk, LF/CRLF, content-free/empty,
        # delta.content, legacy text extraction, and normal EOF sealing.
        raw_lf = (
            b'data: {"choices":[{"delta":{"content":"a"}}]}\n\n'
            b': ping\n\n'
            b'data: {"choices":[{"delta":{"content":""}}]}\n\n'
            b'data: {"choices":[{"text":"b"}]}\n\n'
            b'data: [DONE]\n\n'
        )
        output, root, session, counts = await _run_direct_stream(
            [raw_lf[:7], raw_lf[7:41], raw_lf[41:]]
        )
        require(output == raw_lf, output)
        require(session.sealed, session)
        require(_visible_text(_seal(root / "finalization")) == "ab", _seal(root / "finalization"))
        require(max(counts) == 2, counts)

        raw_crlf = (
            b'data: {"choices":[{"delta":{"content":"crlf"}}]}\r\n\r\n'
            b'data: [DONE]\r\n\r\n'
        )
        output, root, session, _ = await _run_direct_stream([raw_crlf])
        require(output == raw_crlf and session.sealed, output)
        require(_visible_text(_seal(root / "finalization")) == "crlf", _seal(root / "finalization"))

        # Normal EOF without an explicit [DONE] seals before iterator completion.
        raw_eof = b'data: {"choices":[{"delta":{"content":"eof"}}]}\n\n'
        output, root, session, _ = await _run_direct_stream([raw_eof])
        require(output == raw_eof and session.sealed, output)
        require(_visible_text(_seal(root / "finalization")) == "eof", _seal(root / "finalization"))

        # 13. ambiguous multiple content fields fails closed before that frame.
        ambiguous = (
            b'data: {"choices":[{"delta":{"content":"x"},"text":"y"}]}\n\n'
            b'data: [DONE]\n\n'
        )
        try:
            await _run_direct_stream([ambiguous])
            raise AssertionError("ambiguous content unexpectedly released")
        except RelayMEMSLPDurableFinalizationError as exc:
            _assert_public_content_free(exc)

        # 14. malformed UTF-8; 15. malformed JSON.
        for bad in (
            b"data: \xff\n\n",
            b'data: {"choices":\n\n',
        ):
            try:
                await _run_direct_stream([bad])
                raise AssertionError(("malformed stream unexpectedly released", bad))
            except RelayMEMSLPDurableFinalizationError as exc:
                _assert_public_content_free(exc)

        valid_one = b'data: {"choices":[{"delta":{"content":"one"}}]}\n\n'
        valid_two = b'data: {"choices":[{"delta":{"content":"two"}}]}\n\n'
        done = b"data: [DONE]\n\n"

        # 16. segment write failure before first yield.
        def fail_first(session: Any) -> None:
            session.store.publish_segment = lambda _: _failed_store_result(  # type: ignore[method-assign]
                "injected_segment_failure"
            )

        try:
            await _run_direct_stream([valid_one + done], setup=fail_first)
            raise AssertionError("first segment failure unexpectedly released")
        except RelayMEMSLPDurableFinalizationError as exc:
            _assert_public_content_free(exc)

        # 17. after partial delivery, stop before the unprotected second frame.
        partial_output = bytearray()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("queue", "protected", "finalization"):
                (root / name).mkdir()
            holder = RelayMEMSLPDurableFinalizationPreparedTurnHolder()
            session, _ = start_relaymem_slp_durable_finalization_stream(
                config=_direct_config(root),
                pipeline_context=_direct_context(),
                status_code=200,
                resolved_session_id="session-i1gb-direct",
                relayscn_scene_policy_artifact=_direct_scene(),
                relayemo_artifact=None,
                holder=holder,
            )
            require(session is not None, session)
            original = session.store.publish_segment
            calls = 0

            def fail_second(segment: object) -> RelayMEMSLPDurableFinalizationStoreResult:
                nonlocal calls
                calls += 1
                return original(segment) if calls == 1 else _failed_store_result("injected_second_failure")

            session.store.publish_segment = fail_second  # type: ignore[method-assign]

            async def source() -> AsyncIterator[bytes]:
                yield valid_one + valid_two + done

            try:
                async for part in wrap_stream_with_relaymem_slp_finalized_turn_capture(
                    source(),
                    capture=RelayMEMSLPFinalizedVisibleTextCapture(),
                    durable_session=session,
                ):
                    partial_output.extend(part)
            except RelayMEMSLPDurableFinalizationError:
                pass
            require(bytes(partial_output) == valid_one, partial_output)
            require(not _files(root / "finalization", "seal"), list((root / "finalization").iterdir()))

        # 18. seal failure before DONE.
        def fail_seal(session: Any) -> None:
            session.store.publish_seal = lambda _: _failed_store_result(  # type: ignore[method-assign]
                "injected_seal_failure"
            )

        try:
            await _run_direct_stream([valid_one + done], setup=fail_seal)
            raise AssertionError("seal failure unexpectedly released DONE")
        except RelayMEMSLPDurableFinalizationError as exc:
            _assert_public_content_free(exc)

        # 19. backend iterator exception is sanitized; 20. cancellation propagates.
        try:
            await _run_direct_stream(
                [valid_one], backend_error=RuntimeError("backend-canary-hidden")
            )
            raise AssertionError("backend failure unexpectedly completed")
        except RelayMEMSLPDurableFinalizationError as exc:
            require("backend-canary-hidden" not in repr(exc), repr(exc))
            _assert_public_content_free(exc)
        try:
            await _run_direct_stream(
                [valid_one], backend_error=asyncio.CancelledError()
            )
            raise AssertionError("cancellation unexpectedly completed")
        except asyncio.CancelledError as exc:
            _assert_public_content_free(exc)

        # 21. max segment bytes.
        try:
            await _run_direct_stream(
                [
                    b'data: {"choices":[{"delta":{"content":"'
                    + (b"x" * 1000)
                    + b'"}}]}\n\ndata: [DONE]\n\n'
                ],
                config_overrides={
                    "relaymem_slp_durable_finalization_max_segment_bytes": 600,
                },
            )
            raise AssertionError("segment bound unexpectedly accepted")
        except RelayMEMSLPDurableFinalizationError:
            pass

        # 22. max segment count.
        try:
            await _run_direct_stream(
                [valid_one + valid_two + done],
                config_overrides={
                    "relaymem_slp_durable_finalization_max_segment_count": 1,
                },
            )
            raise AssertionError("segment count unexpectedly accepted")
        except RelayMEMSLPDurableFinalizationError:
            pass

        # 23. total record bytes (tighten after durable base admission).
        def tighten_total(session: Any) -> None:
            current = sum(
                path.stat().st_size
                for path in Path(session.store._root_path).iterdir()  # noqa: SLF001
            )
            session.store._max_record_bytes = current + 1  # noqa: SLF001

        try:
            await _run_direct_stream([valid_one + done], setup=tighten_total)
            raise AssertionError("total record bound unexpectedly accepted")
        except RelayMEMSLPDurableFinalizationError:
            pass

        # 24. incomplete record is never replayable.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("queue", "protected", "finalization"):
                (root / name).mkdir()
            holder = RelayMEMSLPDurableFinalizationPreparedTurnHolder()
            session, _ = start_relaymem_slp_durable_finalization_stream(
                config=_direct_config(root),
                pipeline_context=_direct_context(),
                status_code=200,
                resolved_session_id="session-i1gb-direct",
                relayscn_scene_policy_artifact=_direct_scene(),
                relayemo_artifact=None,
                holder=holder,
            )
            require(session is not None, session)
            session.publish_content_unit("incomplete")
            session.abort()
            locator = str(session.base["locator_digest"])
            loaded = session.store.read_evidence(locator)
            require(loaded.status == "loaded", loaded)
            require(not loaded.sealed and not loaded.replayable, loaded)
            require(holder.get() is None, holder)
            # 25. projection/error/repr remain content-free.
            _assert_public_content_free(loaded)
            _assert_public_content_free(session)
            _assert_public_content_free(holder)

    asyncio.run(direct_cases())


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    try:
        test_nonstream_app(port)
        test_stream_app_and_direct(port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("I1-GB durable-finalization app smoke: OK")


if __name__ == "__main__":
    main()
