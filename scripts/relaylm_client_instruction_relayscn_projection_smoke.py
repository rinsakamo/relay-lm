#!/usr/bin/env python3
"""Smoke checks for cache-hit RelaySCN projection."""

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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.client_instruction_cache_lookup import (
    CachedInstructionSceneConstraint,
    CachedInstructionSceneContext,
    CachedInstructionSceneRole,
    ClientInstructionCacheEntry,
    ClientInstructionCacheLookupResult,
)
from relaylm.client_instruction_cache_lookup_runtime import (
    ClientInstructionCacheLookupRuntimeResult,
)
from relaylm.client_instruction_relayscn_projection import (
    build_client_instruction_relayscn_projection,
    build_client_instruction_relayscn_projection_node_result,
)
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route

RAW_VALUES = (
    "system projection secret",
    "developer projection secret",
    "user projection secret",
    "SCENE_ROLE_PROJECTION_PRIVATE",
    "SCENE_CONTEXT_PROJECTION_PRIVATE",
    "SCENE_CONSTRAINT_PROJECTION_PRIVATE",
)
HASH_SENTINEL = "a" * 64


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
                "id": "chatcmpl-relayscn-projection-smoke",
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


def assert_not_leaked(value: Any, *, include_client_messages: bool = True) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    forbidden = RAW_VALUES if include_client_messages else RAW_VALUES[3:]
    for raw in forbidden + (HASH_SENTINEL,):
        require(raw not in encoded, raw)


def payload() -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system projection secret"},
            {"role": "developer", "content": "developer projection secret"},
            {"role": "user", "content": "user projection secret"},
        ],
        "metadata": {"scene_state": {"scene_type": "implementation_work"}},
        "stream": False,
    }


def write_config(path: Path, *, port: int, trace_path: Path, cache_root: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text())
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["client_message_canonicalization_dry_run_enabled"] = True
    cfg["client_instruction_extraction_dry_run_enabled"] = True
    cfg["client_instruction_cache_lookup_enabled"] = True
    cfg["client_instruction_cache_root"] = str(cache_root)
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_full"
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
        request_id="relayscn-projection-smoke",
        run_id="relayscn-projection-smoke-run",
        original_payload=request_payload,
        forwarded_payload=copy.deepcopy(request_payload),
        route=resolve_route(config, "relaylm-default"),
        stream_enabled=False,
    )


def make_identity(cfg_path: Path, request_payload: dict[str, Any]) -> Any:
    ctx = direct_context(cfg_path, request_payload)
    result = ctx.client_instruction_identity_result
    require(result is not None and result.ready and result.identity is not None, result)
    consume_active_pipeline_context()
    return result.identity


def valid_entry(identity: Any) -> dict[str, Any]:
    return {
        "schema_version": "relaylm.client_instruction_cache.v0",
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": "relaylm-default",
        "character_id": "default",
        "instruction_parse_schema_version": "client_instruction_parse.v1",
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": None,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": "implementation_work",
            "scene_role": {
                "role_name": "SCENE_ROLE_PROJECTION_PRIVATE",
                "role_scope": "turn",
                "role_source": "client_instruction_cache",
                "confidence": 0.95,
            },
            "scene_context": {
                "setting": "SCENE_CONTEXT_PROJECTION_PRIVATE",
                "task": None,
                "participants": ["SCENE_CONTEXT_PROJECTION_PRIVATE"],
            },
            "scene_constraints": [
                {
                    "constraint_type": "SCENE_CONSTRAINT_PROJECTION_PRIVATE",
                    "value": "SCENE_CONSTRAINT_PROJECTION_PRIVATE",
                }
            ],
        },
        "durable_candidate_count": 1,
        "blocked_instruction_kinds": [],
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }


def cache_file(cache_root: Path, identity: Any) -> Path:
    return cache_root / f"{identity.cache_key_sha256}.json"


def find(results: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for item in results:
        if item.get("node_name") == name:
            return item
    raise AssertionError((name, results))


def direct_runtime_hit_result() -> ClientInstructionCacheLookupRuntimeResult:
    entry = ClientInstructionCacheEntry(
        schema_version="relaylm.client_instruction_cache.v0",
        cache_key_sha256=HASH_SENTINEL,
        instruction_fingerprint_sha256="b" * 64,
        route_model="relaylm-default",
        character_id="default",
        instruction_parse_schema_version="client_instruction_parse.v1",
        authority_policy_version="client_instruction_authority.v1",
        parser_version=None,
        scene_type="implementation_work",
        scene_role=CachedInstructionSceneRole(
            role_name="SCENE_ROLE_PROJECTION_PRIVATE",
            role_scope="turn",
            role_source="client_instruction_cache",
            confidence=0.95,
        ),
        scene_context=CachedInstructionSceneContext(
            setting="SCENE_CONTEXT_PROJECTION_PRIVATE",
            task=None,
            participants=("SCENE_CONTEXT_PROJECTION_PRIVATE",),
        ),
        scene_constraints=(
            CachedInstructionSceneConstraint(
                "SCENE_CONSTRAINT_PROJECTION_PRIVATE",
                "SCENE_CONSTRAINT_PROJECTION_PRIVATE",
            ),
        ),
        durable_candidate_count=1,
        blocked_instruction_kinds=(),
        raw_instruction_persisted=False,
        raw_response_persisted=False,
        runtime_private=True,
        content_bearing=True,
    )
    lookup = ClientInstructionCacheLookupResult(
        schema_version="client_instruction_cache_lookup.v0",
        status="hit",
        hit=True,
        entry=entry,
        miss_reason=None,
        blocked_reasons=(),
    )
    return ClientInstructionCacheLookupRuntimeResult(
        schema_version="client_instruction_cache_lookup_runtime.v0",
        status="hit",
        lookup_result=lookup,
    )


def test_direct_projection() -> None:
    result = build_client_instruction_relayscn_projection(direct_runtime_hit_result())
    require(result is not None, result)
    require(result.status == "projected", result)
    require(result.cache_hit is True, result)
    require(result.projection_ready is True, result)
    require(result.projected_scene_type == "implementation_work", result)
    require(result.projected_scene_role_scope == "turn", result)
    require(result.projected_scene_role_source == "client_instruction_cache", result)
    require(result.projected_scene_role_confidence_bucket == "very_high", result)
    require(result.projected_scene_context_participant_count == 1, result)
    require(result.projected_scene_constraint_count == 1, result)
    node = build_client_instruction_relayscn_projection_node_result(direct_runtime_hit_result())
    require(node is not None, node)
    require(node.node_name == "client_instruction_relayscn_projection", node)
    require(node.decision == "cache_hit_relayscn_projection_ready", node)
    assert_not_leaked(node.to_log_dict())
    print("ok direct cache hit projects allowlisted RelaySCN summary")


def test_direct_non_hit_statuses() -> None:
    miss_lookup = ClientInstructionCacheLookupResult(
        schema_version="client_instruction_cache_lookup.v0",
        status="miss",
        hit=False,
        entry=None,
        miss_reason="cache_entry_not_found",
        blocked_reasons=(),
    )
    for runtime_result, expected_decision in (
        (
            ClientInstructionCacheLookupRuntimeResult(
                schema_version="client_instruction_cache_lookup_runtime.v0",
                status="miss",
                lookup_result=miss_lookup,
            ),
            "cache_hit_relayscn_projection_miss",
        ),
        (
            ClientInstructionCacheLookupRuntimeResult(
                schema_version="client_instruction_cache_lookup_runtime.v0",
                status="blocked",
                blocked_reasons=("cache_entry_validation_failed",),
            ),
            "cache_hit_relayscn_projection_blocked",
        ),
        (
            ClientInstructionCacheLookupRuntimeResult(
                schema_version="client_instruction_cache_lookup_runtime.v0",
                status="skipped",
                blocked_reasons=("pass_through_route_exempt",),
            ),
            "cache_hit_relayscn_projection_skipped",
        ),
    ):
        node = build_client_instruction_relayscn_projection_node_result(runtime_result)
        require(node is not None, runtime_result)
        require(node.decision == expected_decision, node)
        require(node.diagnostics.get("projection_ready") is False, node)
        assert_not_leaked(node.to_log_dict())
    print("ok miss blocked and skipped projection statuses are content-free")


def test_app_trace_projection(port: int) -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        cache_root = root / "cache"
        cache_root.mkdir()
        cfg = root / "cfg.yaml"
        trace = root / "trace.jsonl"
        request_payload = payload()
        write_config(cfg, port=port, trace_path=trace, cache_root=cache_root)
        identity = make_identity(cfg, request_payload)
        entry_path = cache_file(cache_root, identity)
        before_bytes = json.dumps(valid_entry(identity), sort_keys=True).encode("utf-8")
        entry_path.write_bytes(before_bytes)

        original = copy.deepcopy(request_payload)
        before_count = Capture.count()
        with TestClient(create_app(str(cfg))) as client:
            response = client.post("/v1/chat/completions", json=request_payload)
        require(response.status_code == 200, response.text)
        require(request_payload == original, request_payload)
        require(Capture.count() == before_count + 1, Capture.count())
        backend_payload = Capture.get(before_count)
        require(backend_payload.get("messages") == original.get("messages"), backend_payload)
        require(entry_path.read_bytes() == before_bytes, entry_path)

        record = json.loads(trace.read_text(encoding="utf-8").strip().splitlines()[-1])
        results = record["metadata"]["pipeline_node_results"]
        lookup_node = find(results, "client_instruction_cache_lookup")
        projection_node = find(results, "client_instruction_relayscn_projection")
        names = [item.get("node_name") for item in results]
        require(
            names.index("client_instruction_cache_lookup")
            < names.index("client_instruction_relayscn_projection"),
            names,
        )
        require(lookup_node.get("decision") == "instruction_cache_hit", lookup_node)
        require(
            projection_node.get("decision") == "cache_hit_relayscn_projection_ready",
            projection_node,
        )
        diagnostics = projection_node.get("diagnostics", {})
        require(diagnostics.get("status") == "projected", projection_node)
        require(diagnostics.get("cache_hit") is True, projection_node)
        require(diagnostics.get("projection_ready") is True, projection_node)
        require(diagnostics.get("projected_scene_type") == "implementation_work", projection_node)
        require(diagnostics.get("projected_scene_role_scope") == "turn", projection_node)
        require(
            diagnostics.get("projected_scene_role_source") == "client_instruction_cache",
            projection_node,
        )
        require(diagnostics.get("projected_scene_role_confidence_bucket") == "very_high", projection_node)
        require(diagnostics.get("read_only") is True, projection_node)
        require(diagnostics.get("applied") is False, projection_node)
        assert_not_leaked(results, include_client_messages=False)
        assert_not_leaked(backend_payload, include_client_messages=False)
        assert_not_leaked(response.json(), include_client_messages=False)
    print("ok app trace emits read-only content-free RelaySCN projection node")


def main() -> int:
    test_direct_projection()
    test_direct_non_hit_statuses()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        test_app_trace_projection(int(server.server_address[1]))
    finally:
        server.shutdown()
        thread.join(timeout=5)
    print("client_instruction_relayscn_projection_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
