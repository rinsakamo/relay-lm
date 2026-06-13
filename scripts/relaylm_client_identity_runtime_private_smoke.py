from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.app import create_app
import relaylm.client_instruction_identity_runtime as identity_runtime
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route


RAW = (
    "system identity runtime secret",
    "developer identity runtime secret",
    "user identity runtime secret",
    "tool identity runtime secret",
    "call_identity_runtime_secret_123",
)
EXC = "identity runtime exception secret"


class Capture:
    payloads: list[dict[str, Any]] = []
    lock = threading.Lock()

    @classmethod
    def add(cls, value: dict[str, Any]) -> None:
        with cls.lock:
            cls.payloads.append(copy.deepcopy(value))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        Capture.add(json.loads(raw.decode("utf-8")) if raw else {})
        body = json.dumps(
            {
                "id": "chatcmpl-identity-runtime-private-smoke",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}}
                ],
            }
        ).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def base_messages() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "system identity runtime secret"},
        {
            "role": "developer",
            "content": [{"type": "text", "text": "developer identity runtime secret"}],
        },
        {"role": "user", "content": "user identity runtime secret"},
    ]


def payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages,
        "metadata": {"scene_state": {"scene_type": "implementation_work"}},
        "stream": False,
    }


def config_file(path: Path, *, port: int, trace: Path, enabled: bool, mode: str) -> None:
    cfg = yaml.safe_load((ROOT / "config.example.yaml").read_text())
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace)}
    cfg["client_message_canonicalization_dry_run_enabled"] = True
    cfg["client_instruction_extraction_dry_run_enabled"] = enabled
    cfg["model_routes"]["relaylm-default"]["mode"] = mode
    cfg["memory"]["ctx_block_apply_enabled"] = False
    cfg["memory"]["snippet_runtime_injection_enabled"] = False
    cfg["memory"]["token_budget_truncation_enabled"] = False
    path.write_text(yaml.safe_dump(cfg))


def private_context(cfg: Path, request_payload: dict[str, Any]) -> PipelineContext:
    config = load_config(str(cfg))
    return PipelineContext(
        request_id="identity-private",
        run_id="identity-private-run",
        original_payload=request_payload,
        forwarded_payload=copy.deepcopy(request_payload),
        route=resolve_route(config, "relaylm-default"),
        stream_enabled=False,
    )


def find(results: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(item for item in results if item.get("node_name") == name)


def no_private(value: Any, hashes: tuple[str, ...] = (), extra: tuple[str, ...] = ()) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for item in RAW + hashes + extra:
        require(item not in encoded, item)


def run_case(
    *,
    port: int,
    request_payload: dict[str, Any],
    enabled: bool = True,
    mode: str = "memory_full",
    fail_builder: bool = False,
) -> tuple[list[dict[str, Any]], Any, tuple[str, str] | None]:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        trace = root / "trace.jsonl"
        cfg = root / "cfg.yaml"
        config_file(cfg, port=port, trace=trace, enabled=enabled, mode=mode)

        direct = private_context(cfg, request_payload)
        result = direct.client_instruction_identity_result
        hashes = None
        if result is not None and result.identity is not None:
            hashes = (
                result.identity.instruction_fingerprint_sha256,
                result.identity.cache_key_sha256,
            )
        no_private(repr(direct), hashes or ())
        consume_active_pipeline_context()

        original = copy.deepcopy(request_payload)
        before = len(Capture.payloads)
        builder = identity_runtime.build_client_instruction_identity
        if fail_builder:
            identity_runtime.build_client_instruction_identity = (
                lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(EXC))
            )
        try:
            with TestClient(create_app(str(cfg))) as client:
                response = client.post("/v1/chat/completions", json=request_payload)
        finally:
            identity_runtime.build_client_instruction_identity = builder

        require(response.status_code == 200, response.text)
        require(request_payload == original, request_payload)
        require(len(Capture.payloads) == before + 1, Capture.payloads)
        backend = Capture.payloads[-1]
        require(backend.get("messages") == original.get("messages"), backend)
        require("client_instruction_identity" not in json.dumps(backend), backend)

        record = json.loads(trace.read_text().strip().splitlines()[-1])
        results = record["metadata"]["pipeline_node_results"]
        no_private(results, hashes or (), (EXC,))
        return results, result, hashes


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])

        off, off_result, _ = run_case(
            port=port,
            request_payload=payload(base_messages()),
            enabled=False,
        )
        require(off_result is None, off_result)
        require(all(x.get("node_name") != "client_instruction_identity" for x in off), off)

        ready, ready_result, hashes = run_case(
            port=port,
            request_payload=payload(base_messages()),
        )
        require(ready_result is not None and ready_result.ready, ready_result)
        require(hashes is not None and all(len(x) == 64 for x in hashes), hashes)
        names = [x.get("node_name") for x in ready]
        ordered = [
            "client_message_canonicalization",
            "client_instruction_extraction",
            "client_instruction_fingerprint",
            "client_instruction_identity",
            "client_instruction_cache",
        ]
        require(
            [names.index(x) for x in ordered]
            == sorted(names.index(x) for x in ordered),
            names,
        )
        node = find(ready, "client_instruction_identity")
        require(node.get("decision") == "instruction_identity_ready", node)
        require(node["diagnostics"].get("instruction_candidate_count") == 2, node)
        cache = find(ready, "client_instruction_cache")["diagnostics"]
        require(cache.get("lookup_requested") is False, cache)
        require(cache.get("cache_lookup_attempted") is False, cache)

        empty, empty_result, _ = run_case(
            port=port,
            request_payload=payload(
                [{"role": "user", "content": "user identity runtime secret"}]
            ),
        )
        require(empty_result is not None and empty_result.identity is not None, empty_result)
        require(empty_result.identity.empty_instruction, empty_result)
        require(find(empty, "client_instruction_identity")["diagnostics"]["empty_instruction"], empty)

        passed, passed_result, _ = run_case(
            port=port,
            request_payload=payload(base_messages()),
            mode="pass_through",
        )
        require(passed_result is not None and not passed_result.ready, passed_result)
        require("source_extraction_not_managed" in passed_result.blocked_reasons, passed_result)

        active_messages = base_messages() + [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_identity_runtime_secret_123",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            }
        ]
        active, active_result, _ = run_case(
            port=port,
            request_payload=payload(active_messages),
        )
        require(active_result is not None and not active_result.ready, active_result)
        require(
            "active_tool_transaction_requires_preservation"
            in find(active, "client_instruction_identity")["blocked_reasons"],
            active,
        )

        failed, _, _ = run_case(
            port=port,
            request_payload=payload(base_messages()),
            fail_builder=True,
        )
        require(
            "identity_runtime_preparation_failed"
            in find(failed, "client_instruction_identity")["blocked_reasons"],
            failed,
        )

        print("ok runtime-private instruction identity")
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
