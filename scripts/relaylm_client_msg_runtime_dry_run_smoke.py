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


RAW_VALUES = (
    "system runtime evidence",
    "developer runtime evidence",
    "old runtime history",
    "runtime current evidence",
    "https://example.invalid/runtime-image.png",
    "malformed runtime image",
    "tool runtime request",
    "call-runtime",
    "tool runtime result",
)


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def count(self) -> int:
        with self._lock:
            return len(self.payloads)

    def get(self, index: int) -> dict[str, Any]:
        with self._lock:
            return self.payloads[index]


class _BackendHandler(BaseHTTPRequestHandler):
    capture: _Capture

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-client-msg-runtime-smoke",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}}
                ],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    mode: str,
    enabled: bool,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["client_message_canonicalization_dry_run_enabled"] = enabled
    cfg["model_routes"]["relaylm-default"]["mode"] = mode
    cfg["memory"].update(
        {
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_dry_run_only": True,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _base_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages,
        "metadata": {
            "scene_state": {
                "scene_type": "implementation_work",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _post(
    *,
    port: int,
    payload: dict[str, Any],
    capture: _Capture,
    mode: str = "memory_full",
    enabled: bool = True,
) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        trace_path = root / "trace.jsonl"
        cfg_path = root / "cfg.yaml"
        _write_config(cfg_path, port=port, trace_path=trace_path, mode=mode, enabled=enabled)
        original = json.loads(json.dumps(payload, ensure_ascii=False))
        before_count = capture.count()
        with TestClient(create_app(str(cfg_path))) as client:
            response = client.post("/v1/chat/completions", json=payload)

        require(response.status_code == 200, response.text)
        require(payload == original, payload)
        require(capture.count() == before_count + 1, capture.count())
        backend_payload = capture.get(before_count)
        require(backend_payload.get("messages") == original.get("messages"), backend_payload)
        require(backend_payload.get("metadata") == original.get("metadata"), backend_payload)
        backend_encoded = json.dumps(backend_payload, ensure_ascii=False)
        require("client_message_canonicalization" not in backend_encoded, backend_payload)

        records = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(records, trace_path)
        record = json.loads(records[-1])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), record)
        results = metadata.get("pipeline_node_results")
        require(isinstance(results, list), metadata)
        return results


def _find_result(results: list[dict[str, Any]], node_name: str) -> dict[str, Any]:
    for result in results:
        if isinstance(result, dict) and result.get("node_name") == node_name:
            return result
    raise AssertionError((node_name, results))


def _assert_no_result(results: list[dict[str, Any]], node_name: str) -> None:
    require(
        all(not isinstance(result, dict) or result.get("node_name") != node_name for result in results),
        results,
    )


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for raw in RAW_VALUES:
        require(raw not in encoded, f"content leaked into diagnostics: {raw!r}")


def _assert_default_off(capture: _Capture, port: int) -> None:
    payload = _base_payload([{"role": "user", "content": "runtime current evidence"}])
    results = _post(port=port, payload=payload, capture=capture, enabled=False)
    _assert_no_result(results, "client_message_canonicalization")
    _assert_no_raw_content(results)
    print("ok default-off runtime omits client node result")


def _assert_enabled_managed_route(capture: _Capture, port: int) -> None:
    payload = _base_payload(
        [
            {"role": "system", "content": "system runtime evidence"},
            {"role": "developer", "content": [{"type": "text", "text": "developer runtime evidence"}]},
            {"role": "user", "content": "old runtime history"},
            {"role": "assistant", "content": "old assistant runtime history"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "runtime current evidence"},
                    {"type": "image_url", "image_url": {"url": "https://example.invalid/runtime-image.png"}},
                ],
            },
        ]
    )
    results = _post(port=port, payload=payload, capture=capture)
    names = [result.get("node_name") for result in results if isinstance(result, dict)]
    require(names[0] == "client_message_canonicalization", names)
    require(names.index("client_message_canonicalization") < names.index("relayint_reference_repair"), names)
    require(names.index("client_message_canonicalization") < names.index("relayctx_repack"), names)
    result = _find_result(results, "client_message_canonicalization")
    require(result.get("status") == "diagnostic_only", result)
    require(result.get("decision") == "current_request_evidence_identified", result)
    require(result.get("blocked_reasons") == [], result)
    diagnostics = result.get("diagnostics")
    require(isinstance(diagnostics, dict), result)
    require(diagnostics.get("content_free") is True, result)
    require(diagnostics.get("managed_route") is True, result)
    require(diagnostics.get("canonicalization_candidate_ready") is True, result)
    require(diagnostics.get("current_user_content_kind") == "multimodal_parts", result)
    require(diagnostics.get("current_user_text_part_count") == 1, result)
    require(diagnostics.get("current_user_non_text_part_count") == 1, result)
    require(diagnostics.get("current_user_invalid_part_count") == 0, result)
    _assert_no_raw_content(results)
    print("ok enabled managed route records client node before RelayINT/Repack")


def _assert_pass_through_skipped(capture: _Capture, port: int) -> None:
    payload = _base_payload([{"role": "user", "content": "runtime current evidence"}])
    results = _post(port=port, payload=payload, capture=capture, mode="pass_through", enabled=True)
    result = _find_result(results, "client_message_canonicalization")
    require(result.get("status") == "skipped", result)
    require(result.get("decision") == "pass_through_route_exempt", result)
    require("pass_through_route_exempt" in result.get("blocked_reasons", []), result)
    require(result.get("diagnostics", {}).get("managed_route") is False, result)
    _assert_no_raw_content(results)
    print("ok pass_through route is skipped")


def _assert_malformed_user_content_blocked(capture: _Capture, port: int) -> None:
    payload = _base_payload(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text"},
                    {"type": "image_url", "image_url": {"url": "malformed runtime image"}},
                ],
            }
        ]
    )
    results = _post(port=port, payload=payload, capture=capture)
    result = _find_result(results, "client_message_canonicalization")
    require(result.get("decision") == "canonicalization_candidate_blocked", result)
    require("current_user_content_invalid" in result.get("blocked_reasons", []), result)
    diagnostics = result.get("diagnostics", {})
    require(diagnostics.get("canonicalization_candidate_ready") is False, result)
    require(diagnostics.get("current_user_content_valid") is False, result)
    require(diagnostics.get("current_user_invalid_part_count") == 1, result)
    _assert_no_raw_content(results)
    print("ok malformed active user content is blocked")


def _assert_active_tool_transaction_blocked(capture: _Capture, port: int) -> None:
    payload = _base_payload(
        [
            {"role": "user", "content": "tool runtime request"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "call-runtime", "type": "function"}],
            },
            {"role": "tool", "tool_call_id": "call-runtime", "content": "tool runtime result"},
        ]
    )
    results = _post(port=port, payload=payload, capture=capture)
    result = _find_result(results, "client_message_canonicalization")
    require(result.get("decision") == "canonicalization_candidate_blocked", result)
    require("active_tool_transaction_requires_preservation" in result.get("blocked_reasons", []), result)
    diagnostics = result.get("diagnostics", {})
    require(diagnostics.get("active_tool_transaction_candidate") is True, result)
    require(diagnostics.get("canonicalization_candidate_ready") is False, result)
    require(diagnostics.get("assistant_tool_call_message_count") == 1, result)
    require(diagnostics.get("post_user_tool_message_count") == 1, result)
    _assert_no_raw_content(results)
    print("ok active tool transaction is preservation-blocked")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        _assert_default_off(capture, port)
        _assert_enabled_managed_route(capture, port)
        _assert_pass_through_skipped(capture, port)
        _assert_malformed_user_content_blocked(capture, port)
        _assert_active_tool_transaction_blocked(capture, port)
        print("ok backend payload messages/metadata are not changed by client dry-run")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
