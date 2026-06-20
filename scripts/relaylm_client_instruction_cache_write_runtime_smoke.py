#!/usr/bin/env python3
"""Smoke checks for C5c runtime-private cache-writer wiring."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_cache_write_runtime import (  # noqa: E402
    set_client_instruction_typed_parse_runtime_private_source,
)
from relaylm.config import BackendConfig  # noqa: E402
from relaylm.diagnostics import RequestDiagnostics  # noqa: E402
from relaylm.pipeline_context import PipelineContext  # noqa: E402
from relaylm.routing import ResolvedRoute  # noqa: E402
from relaylm.trace_runtime import _consume_pipeline_node_results  # noqa: E402

ROUTE = "relaylm-c5c-route"
CHARACTER = "relaylm-c5c-character"
RAW_VALUES = (
    "c5c role private",
    "c5c setting private",
    "c5c task private",
    "c5c participant private",
    "c5c constraint private",
    "c5c durable private",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def route(
    *,
    cache_root: str | None,
    dry_run_only: bool,
    typed_parse_enabled: bool = True,
    cache_write_enabled: bool = True,
) -> ResolvedRoute:
    return ResolvedRoute(
        route_model=ROUTE,
        backend_name="local",
        backend=BackendConfig(base_url="http://127.0.0.1:1234/v1"),
        backend_model="backend-model",
        character_id=CHARACTER,
        mode_requested="memory_light",
        mode_applied="memory_light",
        cache_namespace=None,
        memory_namespace=None,
        client_instruction_cache_lookup_enabled=False,
        client_instruction_cache_root=cache_root,
        client_instruction_cache_max_entry_bytes=65536,
        client_instruction_typed_parse_enabled=typed_parse_enabled,
        client_instruction_cache_write_enabled=cache_write_enabled,
        client_instruction_cache_write_dry_run_only=dry_run_only,
    )


def payload() -> dict[str, Any]:
    return {
        "model": ROUTE,
        "messages": [
            {"role": "system", "content": "c5c system instruction"},
            {"role": "developer", "content": "c5c developer instruction"},
            {"role": "user", "content": "hello"},
        ],
    }


def valid_candidate() -> dict[str, Any]:
    return {
        "scene_type": "implementation_work",
        "scene_role": {
            "role_name": RAW_VALUES[0],
            "role_scope": "scene",
            "confidence": 0.95,
        },
        "scene_context": {
            "setting": RAW_VALUES[1],
            "task": RAW_VALUES[2],
            "participants": [RAW_VALUES[3]],
        },
        "scene_constraints": [
            {"constraint_type": "response_length", "value": RAW_VALUES[4]}
        ],
        "durable_persona_candidates": [
            {
                "candidate_kind": "value",
                "normalized_value": RAW_VALUES[5],
                "confidence": 0.8,
            }
        ],
        "blocked_instruction_kinds": ["runtime_policy_override"],
    }


def assert_not_leaked(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for raw in RAW_VALUES:
        require(raw not in encoded, raw)


def new_context(
    *,
    cache_root: str | None,
    dry_run_only: bool,
    typed_parse_enabled: bool = True,
    cache_write_enabled: bool = True,
) -> PipelineContext:
    request_payload = payload()
    return PipelineContext(
        request_id="c5c-request",
        run_id="c5c-run",
        original_payload=request_payload,
        forwarded_payload=dict(request_payload),
        route=route(
            cache_root=cache_root,
            dry_run_only=dry_run_only,
            typed_parse_enabled=typed_parse_enabled,
            cache_write_enabled=cache_write_enabled,
        ),
        stream_enabled=False,
    )


def test_missing_runtime_private_source_blocks_write() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-c5c-missing-source-") as cache_root:
        context = new_context(cache_root=cache_root, dry_run_only=False)
        parse_result = context.client_instruction_typed_parse_result
        write_result = context.client_instruction_cache_write_result
        require(parse_result is not None and parse_result.status == "skipped", parse_result)
        require(write_result is not None and write_result.status == "blocked", write_result)
        require("source_typed_parse_not_ready" in write_result.blocked_reasons, write_result)
        require(write_result.cache_write_attempted is False, write_result)
        require(not list(Path(cache_root).glob("*.json")), cache_root)
    print("ok missing runtime-private typed parse source blocks cache write")


def test_disabled_route_clears_runtime_private_source() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-c5c-disabled-clears-source-") as cache_root:
        set_client_instruction_typed_parse_runtime_private_source(valid_candidate())
        disabled_context = new_context(
            cache_root=cache_root,
            dry_run_only=False,
            typed_parse_enabled=False,
            cache_write_enabled=False,
        )
        require(disabled_context.client_instruction_typed_parse_result is None, disabled_context)
        require(disabled_context.client_instruction_cache_write_result is None, disabled_context)

        enabled_context = new_context(cache_root=cache_root, dry_run_only=False)
        parse_result = enabled_context.client_instruction_typed_parse_result
        write_result = enabled_context.client_instruction_cache_write_result
        require(parse_result is not None and parse_result.status == "skipped", parse_result)
        require(write_result is not None and write_result.status == "blocked", write_result)
        require("source_typed_parse_not_ready" in write_result.blocked_reasons, write_result)
        require(write_result.cache_write_attempted is False, write_result)
        require(not list(Path(cache_root).glob("*.json")), cache_root)
    print("ok disabled route clears stale runtime-private typed parse source")


def test_versioned_runtime_private_source_blocks_write() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-c5c-versioned-source-") as cache_root:
        set_client_instruction_typed_parse_runtime_private_source(
            valid_candidate(),
            parser_version="client_instruction_parser.v2",
        )
        context = new_context(cache_root=cache_root, dry_run_only=False)
        parse_result = context.client_instruction_typed_parse_result
        write_result = context.client_instruction_cache_write_result
        require(parse_result is not None and parse_result.status == "valid", parse_result)
        require(parse_result.parser_version == "client_instruction_parser.v2", parse_result)
        require(write_result is not None and write_result.status == "blocked", write_result)
        require(
            "source_typed_parse_parser_version_not_runtime_compatible"
            in write_result.blocked_reasons,
            write_result,
        )
        require(write_result.cache_entry_candidate_built is False, write_result)
        require(write_result.cache_write_attempted is False, write_result)
        require(not list(Path(cache_root).glob("*.json")), cache_root)
        assert_not_leaked(context.node_results_to_log_dicts())
    print("ok versioned runtime-private typed parse source blocks cache write")


def test_runtime_private_source_dry_run() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-c5c-dry-run-") as cache_root:
        set_client_instruction_typed_parse_runtime_private_source(valid_candidate())
        context = new_context(cache_root=cache_root, dry_run_only=True)
        parse_result = context.client_instruction_typed_parse_result
        write_result = context.client_instruction_cache_write_result
        require(parse_result is not None and parse_result.status == "valid", parse_result)
        require(write_result is not None and write_result.status == "dry_run", write_result)
        require(write_result.cache_write_attempted is False, write_result)
        require(not list(Path(cache_root).glob("*.json")), cache_root)

        node_results = _consume_pipeline_node_results(
            RequestDiagnostics(
                request_id="c5c-request",
                route_model=ROUTE,
                character_id=CHARACTER,
                mode_applied="memory_light",
            )
        )
        require(node_results is not None, node_results)
        node_names = [result.get("node_name") for result in node_results]
        require("client_instruction_typed_parse" in node_names, node_names)
        require("client_instruction_cache_write" in node_names, node_names)
        require(
            node_names.index("client_instruction_typed_parse")
            < node_names.index("client_instruction_cache_write"),
            node_names,
        )
        assert_not_leaked(node_results)
    print("ok runtime-private typed parse source produces dry-run writer node")


def test_runtime_private_source_write() -> None:
    with tempfile.TemporaryDirectory(prefix="relaylm-c5c-write-") as cache_root:
        set_client_instruction_typed_parse_runtime_private_source(valid_candidate())
        context = new_context(cache_root=cache_root, dry_run_only=False)
        write_result = context.client_instruction_cache_write_result
        require(write_result is not None and write_result.status == "written", write_result)
        require(write_result.cache_write_attempted is True, write_result)
        require(write_result.cache_entry_written is True, write_result)
        require(write_result.atomic_write_used is True, write_result)
        require(len(list(Path(cache_root).glob("*.json"))) == 1, cache_root)
        assert_not_leaked(context.node_results_to_log_dicts())
    print("ok runtime-private typed parse source can invoke gated writer")


def main() -> int:
    test_missing_runtime_private_source_blocks_write()
    test_disabled_route_clears_runtime_private_source()
    test_versioned_runtime_private_source_blocks_write()
    test_runtime_private_source_dry_run()
    test_runtime_private_source_write()
    print("client_instruction_cache_write_runtime_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
