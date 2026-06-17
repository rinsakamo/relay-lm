#!/usr/bin/env python3
"""End-to-end smoke checks for the history-exclusion backend forward gate."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app


class _Capture:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.payloads: list[dict[str, Any]] = []

    def append(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def count(self) -> int:
        with self._lock:
            return len(self.payloads)

    def latest(self) -> dict[str, Any]:
        with self._lock:
            return self.payloads[-1]


class _BackendHandler(BaseHTTPRequestHandler):
    capture = _Capture()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        self.capture.append(payload)
        body = {
            "id": "chatcmpl-history-exclusion",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        }
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    enabled: bool,
    dry_run_only: bool,
    mode: str,
) -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
    )
    config["backends"]["local_backend"]["base_url"] = (
        f"http://127.0.0.1:{port}/v1"
    )
    config["trace"] = {"enabled": True, "path": str(trace_path)}
    config["client_message_canonicalization_dry_run_enabled"] = False
    config["client_history_exclusion_preflight_enabled"] = False
    config["client_history_exclusion_apply_enabled"] = enabled
    config["client_history_exclusion_apply_dry_run_only"] = dry_run_only
    config["client_instruction_extraction_dry_run_enabled"] = False
    config["client_instruction_cache_lookup_enabled"] = False
    config["relayemo_enabled"] = False
    config["model_routes"]["relaylm-default"]["mode"] = mode
    config["memory"].update(
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
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def _payload(
    *,
    with_instruction: bool = False,
    stream: bool = False,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "prior user sentinel"},
        {"role": "assistant", "content": "prior assistant sentinel"},
        {"role": "user", "content": "current user sentinel"},
    ]
    if with_instruction:
        messages.insert(
            0,
            {"role": "system", "content": "raw instruction sentinel" * 500},
        )
    return {
        "model": "relaylm-default",
        "messages": messages,
        "stream": stream,
        "temperature": 0.2,
    }


def _trace_record(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    require(bool(lines), path)
    return json.loads(lines[-1])


def _pipeline_results(record: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), record)
    results = metadata.get("pipeline_node_results")
    require(isinstance(results, list), metadata)
    return results


def _apply_node(record: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        node
        for node in _pipeline_results(record)
        if node.get("node_name") == "client_history_exclusion_apply"
    ]
    require(len(nodes) == 1, nodes)
    return nodes[0]


def _assert_input_node_order(record: dict[str, Any]) -> None:
    names = [node.get("node_name") for node in _pipeline_results(record)]
    canonical_index = names.index("client_message_canonicalization")
    preflight_index = names.index("client_history_exclusion_preflight")
    apply_index = names.index("client_history_exclusion_apply")
    relayint_index = names.index("relayint_reference_repair")
    require(
        canonical_index < preflight_index < apply_index < relayint_index,
        names,
    )


def _run_success_case(
    root: Path,
    *,
    name: str,
    port: int,
    enabled: bool,
    dry_run_only: bool,
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_path = root / f"{name}.yaml"
    trace_path = root / f"{name}.jsonl"
    _write_config(
        config_path,
        port=port,
        trace_path=trace_path,
        enabled=enabled,
        dry_run_only=dry_run_only,
        mode=mode,
    )
    before = _BackendHandler.capture.count()
    with TestClient(create_app(str(config_path))) as client:
        response = client.post("/v1/chat/completions", json=_payload())
    require(response.status_code == 200, response.text)
    require(_BackendHandler.capture.count() == before + 1, name)
    return response.json(), _BackendHandler.capture.latest(), _trace_record(trace_path)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])

    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
            root = Path(temp_dir)

            _, backend_payload, trace = _run_success_case(
                root,
                name="dry_run",
                port=port,
                enabled=True,
                dry_run_only=True,
                mode="memory_light",
            )
            messages = backend_payload.get("messages")
            require(
                isinstance(messages, list)
                and len(messages) == 4
                and messages[-1]["content"] == "current user sentinel"
                and any(
                    message.get("content") == "prior user sentinel"
                    for message in messages
                    if isinstance(message, dict)
                ),
                backend_payload,
            )
            apply_node = _apply_node(trace)
            require(
                apply_node.get("status") == "diagnostic_only"
                and apply_node.get("decision")
                == "client_history_exclusion_apply_ready"
                and apply_node.get("diagnostics", {}).get(
                    "payload_mutation_applied"
                )
                is False,
                apply_node,
            )
            _assert_input_node_order(trace)
            print("ok dry-run preserves compiled client history")

            _, backend_payload, trace = _run_success_case(
                root,
                name="apply",
                port=port,
                enabled=True,
                dry_run_only=False,
                mode="memory_light",
            )
            messages = backend_payload.get("messages")
            require(
                isinstance(messages, list)
                and len(messages) == 2
                and messages[0].get("role") == "system"
                and messages[1]
                == {"role": "user", "content": "current user sentinel"}
                and "prior user sentinel"
                not in json.dumps(backend_payload, ensure_ascii=False)
                and "prior assistant sentinel"
                not in json.dumps(backend_payload, ensure_ascii=False),
                backend_payload,
            )
            apply_node = _apply_node(trace)
            rendered_node = json.dumps(apply_node, ensure_ascii=False)
            require(
                apply_node.get("status") == "applied"
                and apply_node.get("decision") == "client_history_exclusion_applied"
                and apply_node.get("diagnostics", {}).get(
                    "payload_mutation_applied"
                )
                is True
                and "current user sentinel" not in rendered_node
                and "prior user sentinel" not in rendered_node,
                apply_node,
            )
            _assert_input_node_order(trace)
            print("ok actual apply forwards only RelayLM prefix and current user")

            _, backend_payload, trace = _run_success_case(
                root,
                name="pass_through",
                port=port,
                enabled=True,
                dry_run_only=False,
                mode="pass_through",
            )
            messages = backend_payload.get("messages")
            require(
                isinstance(messages, list)
                and len(messages) == 3
                and messages[0]["content"] == "prior user sentinel",
                backend_payload,
            )
            apply_node = _apply_node(trace)
            require(
                apply_node.get("status") == "skipped"
                and apply_node.get("decision") == "pass_through_route_exempt",
                apply_node,
            )
            print("ok pass-through remains client-owned")

            for stream in (False, True):
                name = "blocked_stream" if stream else "blocked_json"
                config_path = root / f"{name}.yaml"
                trace_path = root / f"{name}.jsonl"
                _write_config(
                    config_path,
                    port=port,
                    trace_path=trace_path,
                    enabled=True,
                    dry_run_only=False,
                    mode="memory_light",
                )
                before = _BackendHandler.capture.count()
                with TestClient(create_app(str(config_path))) as client:
                    response = client.post(
                        "/v1/chat/completions",
                        json=_payload(with_instruction=True, stream=stream),
                    )
                require(response.status_code == 502, response.text)
                require(_BackendHandler.capture.count() == before, name)
                rendered_response = response.text
                require(
                    "client_history_exclusion_apply_blocked" in rendered_response
                    and "raw instruction sentinel" not in rendered_response
                    and "current user sentinel" not in rendered_response,
                    rendered_response,
                )
                trace = _trace_record(trace_path)
                apply_node = _apply_node(trace)
                rendered_node = json.dumps(apply_node, ensure_ascii=False)
                require(
                    apply_node.get("status") == "blocked"
                    and apply_node.get("decision")
                    == "client_history_exclusion_instruction_apply_blocked"
                    and "raw instruction sentinel" not in rendered_node
                    and "current user sentinel" not in rendered_node,
                    apply_node,
                )
                _assert_input_node_order(trace)
            print("ok blocked JSON and stream requests never reach backend")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
