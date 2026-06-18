"""Shared helpers for Phase 5-C4a smoke scripts."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from relaylm.client_instruction_extraction import (
    build_client_instruction_extraction_dry_run,
)
from relaylm.client_instruction_identity import build_client_instruction_identity
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_config(
    path: Path,
    *,
    dry_run_only: bool,
    mode: str = "memory_light",
    lookup_enabled: bool = False,
    cache_root: str | None = None,
    trace_path: str | None = None,
) -> None:
    cfg = yaml.safe_load(
        (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
    )
    cfg["client_message_canonicalization_dry_run_enabled"] = False
    cfg["client_history_exclusion_preflight_enabled"] = False
    cfg["client_history_exclusion_apply_enabled"] = True
    cfg["client_history_exclusion_apply_dry_run_only"] = dry_run_only
    cfg["client_instruction_extraction_dry_run_enabled"] = False
    cfg["client_instruction_cache_lookup_enabled"] = lookup_enabled
    cfg["client_instruction_cache_root"] = cache_root
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
    if trace_path is not None:
        cfg["trace"] = {"enabled": True, "path": trace_path}
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def payload(
    instructions: list[tuple[str, str]],
    *,
    current: Any = "exact current user sentinel",
    prior: bool = True,
    stream: bool = False,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": role, "content": text} for role, text in instructions
    ]
    if prior:
        messages.extend(
            [
                {"role": "user", "content": "prior user sentinel"},
                {"role": "assistant", "content": "prior assistant sentinel"},
            ]
        )
    messages.append({"role": "user", "content": current})
    return {
        "model": "relaylm-default",
        "messages": messages,
        "stream": stream,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 128,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "lookup helper",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": "auto",
        "response_format": {"type": "json_object"},
        "provider_options": {"reasoning_effort": "low"},
    }


def build_context(
    config_path: Path,
    request_payload: dict[str, Any],
) -> tuple[PipelineContext, dict[str, Any]]:
    config = load_config(config_path)
    route = resolve_route(config, "relaylm-default")
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload=copy.deepcopy(request_payload),
    )
    compiled_snapshot = copy.deepcopy(compiled.payload)
    context = PipelineContext(
        request_id="phase5c4a-smoke",
        run_id="phase5c4a-smoke-run",
        original_payload=copy.deepcopy(request_payload),
        forwarded_payload=copy.deepcopy(compiled.payload),
        route=route,
        stream_enabled=bool(request_payload.get("stream")),
    )
    return context, compiled_snapshot


def identity_for(request_payload: dict[str, Any]) -> Any:
    extraction = build_client_instruction_extraction_dry_run(
        request_payload,
        enabled=True,
        managed_route=True,
    )
    result = build_client_instruction_identity(
        request_payload,
        extraction,
        enabled=True,
        route_model="relaylm-default",
        character_id="default",
    )
    assert result is not None and result.ready and result.identity is not None
    return result.identity


def cache_entry(identity: Any, opaque_value: str) -> dict[str, Any]:
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
                "role_name": opaque_value,
                "role_scope": "turn",
                "role_source": "client_instruction_cache",
                "confidence": 0.95,
            },
            "scene_context": {
                "setting": opaque_value,
                "task": None,
                "participants": [],
            },
            "scene_constraints": [],
        },
        "durable_candidate_count": 1,
        "blocked_instruction_kinds": [],
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }
