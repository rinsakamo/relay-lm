"""End-to-end ordinary runtime smoke for Phase 6 I1-B and C1-5.

The smoke proves that non-stream and stream responses finish independently from
post-response enqueue/source retention, that protected source is committed before
the queue record, and that the stream observer preserves backend SSE bytes exactly.
"""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_CANARY = "CANARY_RUNTIME_APP_USER_PRIVATE"
ASSISTANT_CANARY = "CANARY_RUNTIME_APP_ASSISTANT_PRIVATE"
NAMESPACE_CANARY = "CANARY_RUNTIME_APP_NAMESPACE_PRIVATE"

NON_STREAM_BODY = {
    "id": "chatcmpl-phase6-i1b",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": ASSISTANT_CANARY},
            "finish_reason": "stop",
        }
    ],
}
STREAM_FRAMES = (
    'data: {"id":"chatcmpl-phase6-i1b","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"CANARY_RUNTIME_APP_"}}]}\n\n',
    'data: {"id":"chatcmpl-phase6-i1b","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"ASSISTANT_PRIVATE"}}]}\n\n',
    "data: [DONE]\n\n",
)
STREAM_BODY = "".join(STREAM_FRAMES)


class _Capture:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.payloads: list[dict[str, Any]] = []

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)


class _BackendHandler(BaseHTTPRequestHandler):
    capture = _Capture()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).capture.add(payload)
        if payload.get("stream") is True:
            encoded = STREAM_BODY.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-cache")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        encoded = json.dumps(NON_STREAM_BODY).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
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
    queue_root: Path,
    protected_source_root: Path,
    trace_path: Path,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = (
        f"http://127.0.0.1:{backend_port}/v1"
    )
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"].update(
        {
            "mode": "memory_light",
            "character_id": "default",
            "memory_namespace": NAMESPACE_CANARY,
            "session_id": "session-phase6-i1b",
        }
    )
    cfg["relayemo_enabled"] = False
    cfg["relaymem_slp_runtime_enqueue_enabled"] = True
    cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = False
    cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = True
    cfg["trusted_home_scene_admission_runtime_trigger_enabled"] = False
    cfg["relaymem_slp_queue_root"] = str(queue_root.resolve())
    cfg["relaymem_slp_protected_source_root"] = str(protected_source_root.resolve())
    cfg["relaymem_slp_protected_source_max_artifact_bytes"] = 256 * 1024
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


def _payload(*, stream: bool, user_text: str) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": user_text}],
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


def _trace_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _runtime_enqueue_record(path: Path) -> dict[str, Any]:
    matches = [
        record
        for record in _trace_records(path)
        if isinstance(record.get("metadata"), dict)
        and record["metadata"].get("event") == "relaymem_slp_runtime_enqueue"
    ]
    require(matches, _trace_records(path))
    with_nodes = [
        record
        for record in matches
        if isinstance(record.get("metadata", {}).get("pipeline_node_results"), list)
    ]
    require(with_nodes, matches)
    return with_nodes[-1]


def _assert_trace_content_free(record: dict[str, Any]) -> None:
    text = json.dumps(record, ensure_ascii=False, sort_keys=True)
    for canary in (
        USER_CANARY,
        ASSISTANT_CANARY,
        NAMESPACE_CANARY,
        "slp-dispatch-v0:",
        "slp-job-v0:",
    ):
        require(canary not in text, (canary, text))
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), record)
    results = metadata.get("pipeline_node_results")
    require(isinstance(results, list), metadata)
    names = [item.get("node_name") for item in results if isinstance(item, dict)]
    if names and names[0] == "trusted_home_scene_admission":
        names = names[1:]
    require(
        names == [
            "relaymem_slp_finalized_turn_source",
            "relaymem_slp_runtime_enqueue",
        ],
        names,
    )
    enqueue = results[-1]
    require(enqueue.get("decision") in {"enqueued", "enqueue_failed"}, enqueue)
    require(enqueue.get("diagnostics", {}).get("worker_ready") is False, enqueue)
    require(enqueue.get("diagnostics", {}).get("worker_invoked") is False, enqueue)


def _assert_enqueue_decision(record: dict[str, Any], expected: str) -> None:
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), record)
    results = metadata.get("pipeline_node_results")
    require(isinstance(results, list) and results, metadata)
    require(results[-1].get("decision") == expected, record)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            queue_root = root / "queue"
            protected_source_root = root / "protected-source"
            queue_root.mkdir()
            protected_source_root.mkdir()
            trace_path = root / "apply.jsonl"
            config_path = root / "apply.yaml"
            _write_config(
                config_path,
                backend_port=port,
                queue_root=queue_root,
                protected_source_root=protected_source_root,
                trace_path=trace_path,
            )
            app = create_app(str(config_path))
            with TestClient(app) as client:
                non_stream = client.post(
                    "/v1/chat/completions",
                    json=_payload(stream=False, user_text=USER_CANARY),
                )
                require(non_stream.status_code == 200, non_stream.text)
                require(non_stream.json() == NON_STREAM_BODY, non_stream.json())
                require(
                    len(list(queue_root.glob("slp-dispatch-v0-*.json"))) == 1,
                    list(queue_root.iterdir()),
                )
                require(
                    len(list(protected_source_root.glob("protected-source-v0-*.json"))) == 1,
                    list(protected_source_root.iterdir()),
                )
                registry = app.state.relaymem_slp_primary_worker_source_registry
                require(registry.size == 1, registry)
                first_trace = _runtime_enqueue_record(trace_path)
                _assert_trace_content_free(first_trace)
                _assert_enqueue_decision(first_trace, "enqueued")

                with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    json=_payload(
                        stream=True,
                        user_text=USER_CANARY + "-stream",
                    ),
                ) as stream_response:
                    require(stream_response.status_code == 200, stream_response.status_code)
                    streamed = "".join(stream_response.iter_text())
                require(streamed == STREAM_BODY, streamed)
                require(
                    len(list(queue_root.glob("slp-dispatch-v0-*.json"))) == 2,
                    list(queue_root.iterdir()),
                )
                require(
                    len(list(protected_source_root.glob("protected-source-v0-*.json"))) == 2,
                    list(protected_source_root.iterdir()),
                )
                require(registry.size == 2, registry)
                stream_trace = _runtime_enqueue_record(trace_path)
                _assert_trace_content_free(stream_trace)
                _assert_enqueue_decision(stream_trace, "enqueued")

            failure_trace = root / "failure.jsonl"
            failure_config = root / "failure.yaml"
            missing_queue = root / "missing-queue"
            failure_protected_source_root = root / "failure-protected-source"
            failure_protected_source_root.mkdir()
            _write_config(
                failure_config,
                backend_port=port,
                queue_root=missing_queue,
                protected_source_root=failure_protected_source_root,
                trace_path=failure_trace,
            )
            failure_app = create_app(str(failure_config))
            with TestClient(failure_app) as client:
                response = client.post(
                    "/v1/chat/completions",
                    json=_payload(stream=False, user_text=USER_CANARY + "-failure"),
                )
            require(response.status_code == 200, response.text)
            require(response.json() == NON_STREAM_BODY, response.json())
            require(not missing_queue.exists(), missing_queue)
            require(
                not list(failure_protected_source_root.glob("protected-source-v0-*.json")),
                list(failure_protected_source_root.iterdir()),
            )
            require(
                failure_app.state.relaymem_slp_primary_worker_source_registry.size == 0,
                failure_app.state.relaymem_slp_primary_worker_source_registry,
            )
            failed_trace = _runtime_enqueue_record(failure_trace)
            _assert_trace_content_free(failed_trace)
            _assert_enqueue_decision(failed_trace, "enqueue_failed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("Phase 6 runtime enqueue app smoke passed")


if __name__ == "__main__":
    main()
