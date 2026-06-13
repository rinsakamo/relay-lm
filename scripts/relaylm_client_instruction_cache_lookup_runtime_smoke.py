#!/usr/bin/env python3
"""Smoke checks for runtime-private instruction cache lookup wiring."""

from __future__ import annotations

import copy
import json
import os
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
import relaylm.client_instruction_cache_lookup_runtime as cache_runtime
import relaylm.client_instruction_identity_runtime as identity_runtime
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route

RAW_VALUES = (
    "system lookup runtime secret",
    "developer lookup runtime secret",
    "user lookup runtime secret",
    "tool lookup runtime secret",
    "call_lookup_runtime_secret_123",
    "SCENE_ROLE_SENTINEL_PRIVATE",
    "SCENE_CONTEXT_SENTINEL_PRIVATE",
    "SCENE_CONSTRAINT_SENTINEL_PRIVATE",
    "ROUTE_MISMATCH_SENTINEL_PRIVATE",
    "CHARACTER_MISMATCH_SENTINEL_PRIVATE",
    "runtime exception secret sentinel",
)


class Capture:
    payloads: list[dict[str, Any]] = []
    lock = threading.Lock()

    @classmethod
    def add(cls, payload: dict[str, Any]) -> None:
        with cls.lock:
            cls.payloads.append(copy.deepcopy(payload))

    @classmethod
    def count(cls) -> int:
        with cls.lock:
            return len(cls.payloads)

    @classmethod
    def get(cls, index: int) -> dict[str, Any]:
        with cls.lock:
            return copy.deepcopy(cls.payloads[index])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        Capture.add(json.loads(raw.decode("utf-8")) if raw else {})
        body = json.dumps(
            {
                "id": "chatcmpl-cache-lookup-runtime-smoke",
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


def base_messages() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "system lookup runtime secret"},
        {
            "role": "developer",
            "content": [{"type": "text", "text": "developer lookup runtime secret"}],
        },
        {"role": "user", "content": "user lookup runtime secret"},
    ]


def payload(messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages if messages is not None else base_messages(),
        "metadata": {"scene_state": {"scene_type": "implementation_work"}},
        "stream": False,
    }


def write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    mode: str = "memory_full",
    extraction_enabled: bool = True,
    lookup_enabled: bool = True,
    cache_root: str | None = None,
    max_entry_bytes: int = 65536,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text())
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["client_message_canonicalization_dry_run_enabled"] = True
    cfg["client_instruction_extraction_dry_run_enabled"] = extraction_enabled
    cfg["client_instruction_cache_lookup_enabled"] = lookup_enabled
    cfg["client_instruction_cache_root"] = cache_root
    cfg["client_instruction_cache_max_entry_bytes"] = max_entry_bytes
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


def direct_context(cfg_path: Path, request_payload: dict[str, Any]) -> PipelineContext:
    config = load_config(str(cfg_path))
    return PipelineContext(
        request_id="cache-lookup-runtime-smoke",
        run_id="cache-lookup-runtime-smoke-run",
        original_payload=request_payload,
        forwarded_payload=copy.deepcopy(request_payload),
        route=resolve_route(config, "relaylm-default"),
        stream_enabled=False,
    )


def post_case(
    *,
    cfg_path: Path,
    request_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    original = copy.deepcopy(request_payload)
    before = Capture.count()
    with TestClient(create_app(str(cfg_path))) as client:
        response = client.post("/v1/chat/completions", json=request_payload)
    require(response.status_code == 200, response.text)
    body = response.json()
    require(body["choices"][0]["message"]["content"] == "ok", body)
    require(request_payload == original, request_payload)
    require(Capture.count() == before + 1, Capture.count())
    backend = Capture.get(before)
    require(backend.get("messages") == original.get("messages"), backend)
    require(backend.get("metadata") == original.get("metadata"), backend)
    trace_path = Path(yaml.safe_load(cfg_path.read_text())["trace"]["path"])
    record = json.loads(trace_path.read_text().strip().splitlines()[-1])
    results = record["metadata"]["pipeline_node_results"]
    assert_private_not_leaked(results)
    assert_private_not_leaked(backend, include_client_messages=False)
    assert_private_not_leaked(body)
    return results, backend, body


def find(results: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for item in results:
        if item.get("node_name") == name:
            return item
    raise AssertionError((name, results))


def no_node(results: list[dict[str, Any]], name: str) -> None:
    require(all(item.get("node_name") != name for item in results), results)


CACHE_PRIVATE_VALUES = RAW_VALUES[5:]


def assert_private_not_leaked(
    value: Any,
    extra: tuple[str, ...] = (),
    *,
    include_client_messages: bool = True,
) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    forbidden = RAW_VALUES if include_client_messages else CACHE_PRIVATE_VALUES
    for raw in forbidden + extra:
        require(raw not in encoded, raw)


def valid_entry(identity: Any, *, route_model: str = "relaylm-default", character_id: str | None = "default") -> dict[str, Any]:
    return {
        "schema_version": "relaylm.client_instruction_cache.v0",
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": route_model,
        "character_id": character_id,
        "instruction_parse_schema_version": "client_instruction_parse.v1",
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": None,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": "implementation_work",
            "scene_role": {
                "role_name": "SCENE_ROLE_SENTINEL_PRIVATE",
                "role_scope": "turn",
                "role_source": "client_instruction_cache",
                "confidence": 0.95,
            },
            "scene_context": {
                "setting": "SCENE_CONTEXT_SENTINEL_PRIVATE",
                "task": None,
                "participants": [],
            },
            "scene_constraints": [
                {
                    "constraint_type": "SCENE_CONSTRAINT_SENTINEL_PRIVATE",
                    "value": "SCENE_CONSTRAINT_SENTINEL_PRIVATE",
                }
            ],
        },
        "durable_candidate_count": 1,
        "blocked_instruction_kinds": [],
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }


def make_identity(cfg_path: Path, request_payload: dict[str, Any]) -> Any:
    ctx = direct_context(cfg_path, request_payload)
    result = ctx.client_instruction_identity_result
    require(result is not None and result.ready and result.identity is not None, result)
    consume_active_pipeline_context()
    return result.identity


def cache_file(cache_root: Path, identity: Any) -> Path:
    return cache_root / f"{identity.cache_key_sha256}.json"


def test_default_off(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        write_config(cfg, port=port, trace_path=trace, lookup_enabled=False)
        original_reader = cache_runtime.read_client_instruction_cache_candidate
        original_lookup = cache_runtime.resolve_client_instruction_cache_lookup
        cache_runtime.read_client_instruction_cache_candidate = lambda *a, **k: (_ for _ in ()).throw(AssertionError("reader called"))
        cache_runtime.resolve_client_instruction_cache_lookup = lambda *a, **k: (_ for _ in ()).throw(AssertionError("lookup called"))
        try:
            ctx = direct_context(cfg, payload())
            require(ctx.client_instruction_cache_lookup_runtime_result is None, ctx)
            consume_active_pipeline_context()
            results, _, _ = post_case(cfg_path=cfg, request_payload=payload())
        finally:
            cache_runtime.read_client_instruction_cache_candidate = original_reader
            cache_runtime.resolve_client_instruction_cache_lookup = original_lookup
        no_node(results, "client_instruction_cache_lookup")
    print("ok default-off omits lookup runtime and avoids reader/lookup")


def test_pass_through(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        write_config(cfg, port=port, trace_path=trace, mode="pass_through", cache_root=str(root / "cache"))
        original_reader = cache_runtime.read_client_instruction_cache_candidate
        cache_runtime.read_client_instruction_cache_candidate = lambda *a, **k: (_ for _ in ()).throw(AssertionError("reader called"))
        try:
            results, _, _ = post_case(cfg_path=cfg, request_payload=payload())
        finally:
            cache_runtime.read_client_instruction_cache_candidate = original_reader
        node = find(results, "client_instruction_cache_lookup")
        require(node.get("decision") == "pass_through_route_exempt", node)
        require("pass_through_route_exempt" in node.get("blocked_reasons", []), node)
    print("ok pass-through skips filesystem lookup")


def test_source_blocked(port: int) -> None:
    cases = [
        ("empty", payload([{"role": "user", "content": "user lookup runtime secret"}]), None),
        (
            "tool",
            payload(
                base_messages()
                + [
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_lookup_runtime_secret_123",
                                "type": "function",
                                "function": {"name": "lookup", "arguments": "{}"},
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": "call_lookup_runtime_secret_123", "content": "tool lookup runtime secret"},
                ]
            ),
            None,
        ),
        ("failure", payload(), "runtime exception secret sentinel"),
    ]
    for _, request_payload, failure in cases:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)
            cfg = root / "cfg.yaml"
            trace = root / "trace.jsonl"
            write_config(cfg, port=port, trace_path=trace, cache_root=str(root / "cache"))
            original_reader = cache_runtime.read_client_instruction_cache_candidate
            original_builder = identity_runtime.build_client_instruction_identity
            cache_runtime.read_client_instruction_cache_candidate = lambda *a, **k: (_ for _ in ()).throw(AssertionError("reader called"))
            if failure is not None:
                identity_runtime.build_client_instruction_identity = lambda *a, **k: (_ for _ in ()).throw(RuntimeError(failure))
            try:
                results, _, _ = post_case(cfg_path=cfg, request_payload=request_payload)
            finally:
                cache_runtime.read_client_instruction_cache_candidate = original_reader
                identity_runtime.build_client_instruction_identity = original_builder
            node = find(results, "client_instruction_cache_lookup")
            require(node.get("decision") == "instruction_cache_source_blocked", node)
            require(node.get("blocked_reasons"), node)
    print("ok source-blocked gates skip reader")


def test_missing(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        for label, cache_root in (
            ("unset", None),
            ("missing-root", str(root / "missing-cache-root")),
            ("missing-entry", str(root / "cache")),
        ):
            if label == "missing-entry":
                Path(cache_root).mkdir()
            cfg = root / f"{label}.yaml"
            trace = root / f"{label}.jsonl"
            write_config(cfg, port=port, trace_path=trace, cache_root=cache_root)
            results, _, _ = post_case(cfg_path=cfg, request_payload=payload())
            node = find(results, "client_instruction_cache_lookup")
            require(node.get("decision") == "instruction_cache_miss", node)
            diag = node.get("diagnostics", {})
            require(diag.get("status") == "miss", node)
            require(diag.get("reader_miss_reason") in {"cache_root_not_configured", "cache_root_missing", "cache_entry_not_found"}, node)
            require(diag.get("lookup_miss_reason") == "cache_entry_not_found", node)
    print("ok missing roots and entries resolve as miss")


def test_hit(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cache_root = root / "cache"
        cache_root.mkdir()
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        request_payload = payload()
        write_config(cfg, port=port, trace_path=trace, cache_root=str(cache_root))
        identity = make_identity(cfg, request_payload)
        path = cache_file(cache_root, identity)
        raw = json.dumps(valid_entry(identity), sort_keys=True).encode("utf-8")
        path.write_bytes(raw)
        before = path.read_bytes()
        ctx = direct_context(cfg, request_payload)
        runtime_result = ctx.client_instruction_cache_lookup_runtime_result
        require(runtime_result is not None and runtime_result.status == "hit", runtime_result)
        require(runtime_result.lookup_result is not None and runtime_result.lookup_result.entry is not None, runtime_result)
        require("SCENE_ROLE_SENTINEL_PRIVATE" not in repr(runtime_result), repr(runtime_result))
        consume_active_pipeline_context()
        results, _, _ = post_case(cfg_path=cfg, request_payload=copy.deepcopy(request_payload))
        node = find(results, "client_instruction_cache_lookup")
        require(node.get("decision") == "instruction_cache_hit", node)
        require(node.get("diagnostics", {}).get("cache_hit") is True, node)
        require(path.read_bytes() == before, path)
        assert_private_not_leaked(results, (identity.cache_key_sha256, identity.instruction_fingerprint_sha256, str(cache_root), path.name))
    print("ok cache hit stays runtime-private and read-only")


def test_lookup_blocked(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cache_root = root / "cache"
        cache_root.mkdir()
        request_payload = payload()
        for label, mutate in (
            ("key", lambda entry: entry.update({"cache_key_sha256": "b" * 64})),
            ("fingerprint", lambda entry: entry.update({"instruction_fingerprint_sha256": "c" * 64})),
            ("route", lambda entry: entry.update({"route_model": "ROUTE_MISMATCH_SENTINEL_PRIVATE"})),
            ("scene", lambda entry: entry.update({"scene_state": {"scene_type": "unknown"}})),
        ):
            cfg = root / f"blocked-{label}.yaml"
            trace = root / f"blocked-{label}.jsonl"
            write_config(cfg, port=port, trace_path=trace, cache_root=str(cache_root))
            identity = make_identity(cfg, request_payload)
            entry = valid_entry(identity)
            mutate(entry)
            cache_file(cache_root, identity).write_text(json.dumps(entry), encoding="utf-8")
            results, _, _ = post_case(cfg_path=cfg, request_payload=copy.deepcopy(request_payload))
            node = find(results, "client_instruction_cache_lookup")
            require(node.get("decision") == "instruction_cache_lookup_blocked", node)
            require(node.get("diagnostics", {}).get("reader_status") == "found", node)
            require(node.get("diagnostics", {}).get("lookup_status") == "blocked", node)
    print("ok lookup blocked cases keep entry private")


def test_reader_blocked(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cache_root = root / "cache"
        cache_root.mkdir()
        request_payload = payload()
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        write_config(cfg, port=port, trace_path=trace, cache_root=str(cache_root), max_entry_bytes=16)
        identity = make_identity(cfg, request_payload)
        cases: list[tuple[str, Any]] = [
            ("malformed", lambda p: p.write_text("{", encoding="utf-8")),
            ("limit", lambda p: p.write_text("{" + "x" * 32, encoding="utf-8")),
            ("symlink", lambda p: p.symlink_to(root / "target.json")),
        ]
        for _, writer in cases:
            path = cache_file(cache_root, identity)
            if path.exists() or path.is_symlink():
                path.unlink()
            writer(path)
            original_lookup = cache_runtime.resolve_client_instruction_cache_lookup
            cache_runtime.resolve_client_instruction_cache_lookup = lambda *a, **k: (_ for _ in ()).throw(AssertionError("lookup called"))
            try:
                results, _, _ = post_case(cfg_path=cfg, request_payload=copy.deepcopy(request_payload))
            finally:
                cache_runtime.resolve_client_instruction_cache_lookup = original_lookup
            node = find(results, "client_instruction_cache_lookup")
            require(node.get("decision") == "instruction_cache_read_blocked", node)
            require(node.get("diagnostics", {}).get("lookup_status") is None, node)
    print("ok reader blocked cases do not call lookup")


def test_runtime_exception(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        write_config(cfg, port=port, trace_path=trace, cache_root=str(root / "cache"))
        original_reader = cache_runtime.read_client_instruction_cache_candidate
        cache_runtime.read_client_instruction_cache_candidate = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("runtime exception secret sentinel"))
        try:
            results, _, _ = post_case(cfg_path=cfg, request_payload=payload())
        finally:
            cache_runtime.read_client_instruction_cache_candidate = original_reader
        node = find(results, "client_instruction_cache_lookup")
        require(node.get("decision") == "instruction_cache_runtime_preparation_failed", node)
        require("instruction_cache_runtime_preparation_failed" in node.get("blocked_reasons", []), node)
    print("ok runtime exceptions fail closed without leaking text")


def test_ordering(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cache_root = root / "cache"
        cache_root.mkdir()
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        write_config(cfg, port=port, trace_path=trace, cache_root=str(cache_root))
        results, _, _ = post_case(cfg_path=cfg, request_payload=payload())
        names = [item.get("node_name") for item in results]
        ordered = [
            "client_message_canonicalization",
            "client_instruction_extraction",
            "client_instruction_fingerprint",
            "client_instruction_identity",
            "client_instruction_cache",
            "client_instruction_cache_lookup",
        ]
        require([names.index(name) for name in ordered] == sorted(names.index(name) for name in ordered), names)
        cache_plan = find(results, "client_instruction_cache")
        require(cache_plan.get("diagnostics", {}).get("lookup_requested") is True, cache_plan)
        require(cache_plan.get("diagnostics", {}).get("cache_lookup_attempted") is False, cache_plan)
    print("ok node ordering and cache plan lookup_requested")


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        test_default_off(port)
        test_pass_through(port)
        test_source_blocked(port)
        test_missing(port)
        test_hit(port)
        test_lookup_blocked(port)
        test_reader_blocked(port)
        test_runtime_exception(port)
        test_ordering(port)
    finally:
        server.shutdown()
        thread.join(timeout=5)
    print("client_instruction_cache_lookup_runtime_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
