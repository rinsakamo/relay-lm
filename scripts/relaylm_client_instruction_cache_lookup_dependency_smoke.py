#!/usr/bin/env python3
"""Smoke checks for cache lookup identity dependency activation."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event

RAW_INSTRUCTION = "lookup dependency private instruction sentinel"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def find(results: list[dict[str, Any]], node_name: str) -> dict[str, Any]:
    return next(item for item in results if item.get("node_name") == node_name)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config = RelayLMConfig.model_validate(
            {
                "mode": "memory_full",
                "trace": {"enabled": True, "path": str(trace_path)},
                "client_message_canonicalization_dry_run_enabled": False,
                "client_instruction_extraction_dry_run_enabled": False,
                "client_instruction_cache_lookup_enabled": True,
                "client_instruction_cache_root": None,
                "client_instruction_cache_max_entry_bytes": 65536,
                "backends": {
                    "local_backend": {
                        "type": "openai_compatible",
                        "base_url": "http://127.0.0.1:1/v1",
                        "api_key": "dummy",
                        "default_model": "local-model",
                    }
                },
                "model_routes": {
                    "relaylm-default": {
                        "backend": "local_backend",
                        "backend_model": "local-model",
                        "character_id": "default",
                        "mode": "memory_full",
                    }
                },
            }
        )
        route = resolve_route(config, "relaylm-default")
        require(route.client_instruction_extraction_dry_run_enabled is False, route)
        require(route.client_instruction_cache_lookup_enabled is True, route)

        request_data = {
            "model": "relaylm-default",
            "messages": [
                {"role": "system", "content": RAW_INSTRUCTION},
                {"role": "user", "content": "hello"},
            ],
            "stream": False,
        }
        context = PipelineContext(
            request_id="lookup-dependency",
            run_id="lookup-dependency-run",
            original_payload=request_data,
            forwarded_payload=dict(request_data),
            route=route,
            stream_enabled=False,
        )

        identity = context.client_instruction_identity_result
        require(identity is not None and identity.ready is True, identity)
        require(identity.identity is not None, identity)
        private_hashes = (
            identity.identity.instruction_fingerprint_sha256,
            identity.identity.cache_key_sha256,
        )
        lookup_runtime = context.client_instruction_cache_lookup_runtime_result
        require(lookup_runtime is not None and lookup_runtime.status == "miss", lookup_runtime)
        require(lookup_runtime.reader_result is not None, lookup_runtime)
        require(
            lookup_runtime.reader_result.miss_reason == "cache_root_not_configured",
            lookup_runtime,
        )
        require(
            lookup_runtime.lookup_result is not None
            and lookup_runtime.lookup_result.status == "miss",
            lookup_runtime,
        )

        wrote = trace_runtime_event(
            config=config,
            diagnostics=RequestDiagnostics(
                request_id="lookup-dependency",
                route_model="relaylm-default",
                backend_model="local-model",
                backend_name="local_backend",
                character_id="default",
                mode_requested="memory_full",
                mode_applied="memory_full",
                stream_enabled=False,
                trace_enabled=True,
            ),
            message_count=2,
            response_present=True,
        )
        require(wrote is True, wrote)

        record = json.loads(trace_path.read_text(encoding="utf-8"))
        results = record["metadata"]["pipeline_node_results"]
        names = [item.get("node_name") for item in results]
        ordered = [
            "client_instruction_extraction",
            "client_instruction_fingerprint",
            "client_instruction_identity",
            "client_instruction_cache",
            "client_instruction_cache_lookup",
        ]
        require(
            [names.index(name) for name in ordered]
            == sorted(names.index(name) for name in ordered),
            names,
        )

        extraction = find(results, "client_instruction_extraction")
        require(extraction["diagnostics"].get("enabled") is True, extraction)
        identity_node = find(results, "client_instruction_identity")
        require(identity_node.get("decision") == "instruction_identity_ready", identity_node)
        cache_plan = find(results, "client_instruction_cache")
        require(cache_plan["diagnostics"].get("lookup_requested") is True, cache_plan)
        require(cache_plan["diagnostics"].get("cache_operation_plan_ready") is True, cache_plan)
        lookup_node = find(results, "client_instruction_cache_lookup")
        require(lookup_node.get("decision") == "instruction_cache_miss", lookup_node)
        require(
            lookup_node["diagnostics"].get("reader_miss_reason")
            == "cache_root_not_configured",
            lookup_node,
        )

        rendered = json.dumps(results, ensure_ascii=False, sort_keys=True)
        require(RAW_INSTRUCTION not in rendered, rendered)
        for private_hash in private_hashes:
            require(private_hash not in rendered, private_hash)
        require(str(trace_path.parent) not in rendered, rendered)

    print("ok lookup flag enables typed identity dependency projection")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
