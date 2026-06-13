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
    "system fp runtime secret",
    "developer fp runtime secret",
    "user fp runtime secret",
    "https://example.invalid/fp-runtime-image.png",
    "tool fp runtime secret",
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
                "id": "chatcmpl-client-fp-runtime-smoke",
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


def _write_config(path: Path, *, port: int, trace_path: Path, mode: str, enabled: bool) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["client_message_canonicalization_dry_run_enabled"] = True
    cfg["client_instruction_extraction_dry_run_enabled"] = enabled
    cfg["model_routes"]["relaylm-default"]["mode"] = mode
    cfg["memory"].update(
        {
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _base_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "metadata": {}, "stream": False}


def _post(*, port: int, payload: dict[str, Any], capture: _Capture, mode: str = "memory_full", enabled: bool = True) -> list[dict[str, Any]]:
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
        encoded_backend = json.dumps(backend_payload, ensure_ascii=False)
        require("client_instruction_fingerprint" not in encoded_backend, backend_payload)
        records = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(records, trace_path)
        record = json.loads(records[-1])
        results = record.get("metadata", {}).get("pipeline_node_results")
        require(isinstance(results, list), record)
        return results


def _find(results: list[dict[str, Any]], node_name: str) -> dict[str, Any]:
    for result in results:
        if isinstance(result, dict) and result.get("node_name") == node_name:
            return result
    raise AssertionError((node_name, results))


def _assert_no_node(results: list[dict[str, Any]], node_name: str) -> None:
    require(all(not isinstance(result, dict) or result.get("node_name") != node_name for result in results), results)


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for raw in RAW_VALUES:
        require(raw not in encoded, f"content leaked into diagnostics: {raw!r}")


def _assert_default_off(capture: _Capture, port: int) -> None:
    payload = _base_payload([
        {"role": "system", "content": "system fp runtime secret"},
        {"role": "user", "content": "user fp runtime secret"},
    ])
    results = _post(port=port, payload=payload, capture=capture, enabled=False)
    _assert_no_node(results, "client_instruction_extraction")
    _assert_no_node(results, "client_instruction_fingerprint")
    _assert_no_raw_content(results)
    print("ok default-off omits fp node")


def _assert_ready(capture: _Capture, port: int) -> None:
    payload = _base_payload([
        {"role": "system", "content": "system fp runtime secret"},
        {"role": "developer", "content": [{"type": "text", "text": "developer fp runtime secret"}]},
        {"role": "user", "content": "user fp runtime secret"},
    ])
    results = _post(port=port, payload=payload, capture=capture)
    names = [result.get("node_name") for result in results if isinstance(result, dict)]
    require(names.index("client_instruction_extraction") < names.index("client_instruction_fingerprint"), names)
    require(names.index("client_instruction_fingerprint") < names.index("relayint_reference_repair"), names)
    result = _find(results, "client_instruction_fingerprint")
    require(result.get("status") == "diagnostic_only", result)
    require(result.get("decision") == "instruction_fingerprint_plan_ready", result)
    diag = result.get("diagnostics", {})
    require(diag.get("content_free") is True, result)
    require(diag.get("fingerprint_plan_ready") is True, result)
    require(diag.get("fingerprint_hash_computed") is False, result)
    require(diag.get("cache_key_computed") is False, result)
    require(diag.get("cache_lookup_attempted") is False, result)
    require(diag.get("cache_save_attempted") is False, result)
    require(diag.get("instruction_candidate_count") == 2, result)
    _assert_no_raw_content(results)
    print("ok managed route records fp node")


def _assert_pass_through(capture: _Capture, port: int) -> None:
    payload = _base_payload([
        {"role": "system", "content": "system fp runtime secret"},
        {"role": "user", "content": "user fp runtime secret"},
    ])
    results = _post(port=port, payload=payload, capture=capture, mode="pass_through")
    result = _find(results, "client_instruction_fingerprint")
    require(result.get("status") == "skipped", result)
    require(result.get("decision") == "pass_through_route_exempt", result)
    require("pass_through_route_exempt" in result.get("blocked_reasons", []), result)
    _assert_no_raw_content(results)
    print("ok pass-through skips fp node")


def _assert_source_block(capture: _Capture, port: int) -> None:
    payload = _base_payload([
        {
            "role": "developer",
            "content": [
                {"type": "text", "text": "developer fp runtime secret"},
                {"type": "image_url", "image_url": {"url": "https://example.invalid/fp-runtime-image.png"}},
            ],
        },
        {"role": "user", "content": "user fp runtime secret"},
    ])
    results = _post(port=port, payload=payload, capture=capture)
    result = _find(results, "client_instruction_fingerprint")
    require(result.get("decision") == "instruction_fingerprint_plan_blocked", result)
    blocked = result.get("blocked_reasons", [])
    require("source_extraction_blocked" in blocked, result)
    require("source_multimodal_instruction_candidate_requires_preservation" in blocked, result)
    _assert_no_raw_content(results)
    print("ok source block propagates to fp node")


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        _assert_default_off(capture, port)
        _assert_ready(capture, port)
        _assert_pass_through(capture, port)
        _assert_source_block(capture, port)
        print("ok backend payload unchanged by fp runtime dry-run")
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
