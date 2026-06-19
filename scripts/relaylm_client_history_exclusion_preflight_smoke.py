#!/usr/bin/env python3
"""Smoke checks for client history exclusion preflight.

The integrated runtime/trace checks cover multimodal detachment, invalid
sources, stale/active tool history, runtime failure, and typed apply ordering.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import relaylm.client_history_exclusion_preflight as preflight
from relaylm.client_history_exclusion_preflight import (
    build_client_history_exclusion_preflight_node_result,
)
from relaylm.client_message_canonicalization import (
    build_client_message_canonicalization_dry_run,
)
from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event

SENTINELS = (
    "prior history sentinel",
    "current user text sentinel",
    "image/audio URL sentinel",
    "raw system instruction",
    "raw developer instruction",
    "tool_call_secret",
    "tool args secret",
    "tool result secret",
    "exception sentinel",
)


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def config_file(
    path: Path,
    *,
    enabled: bool = True,
    canonicalization: bool = False,
    lookup: bool = False,
    mode: str = "memory_full",
    apply_enabled: bool = False,
    apply_dry_run_only: bool = True,
) -> None:
    config = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text())
    config["backends"]["local_backend"]["base_url"] = "http://127.0.0.1:9/v1"
    config["trace"] = {
        "enabled": True,
        "path": str(path.with_suffix(".jsonl")),
    }
    config["client_message_canonicalization_dry_run_enabled"] = canonicalization
    config["client_history_exclusion_preflight_enabled"] = enabled
    config["client_history_exclusion_apply_enabled"] = apply_enabled
    config["client_history_exclusion_apply_dry_run_only"] = apply_dry_run_only
    config["client_instruction_extraction_dry_run_enabled"] = lookup
    config["client_instruction_cache_lookup_enabled"] = lookup
    config["client_instruction_cache_root"] = None
    config["model_routes"]["relaylm-default"]["mode"] = mode
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def context(config_path: Path, payload: dict[str, Any]) -> PipelineContext:
    config = load_config(str(config_path))
    route = resolve_route(config, payload.get("model", "relaylm-default"))
    forwarded_payload = copy.deepcopy(payload)
    if route.mode_applied == "memory_light":
        compiled = compile_chat_payload_if_enabled(
            config=config,
            route=route,
            payload=payload,
        )
        forwarded_payload = copy.deepcopy(compiled.payload)
    return PipelineContext(
        request_id="r",
        run_id="u",
        original_payload=payload,
        forwarded_payload=forwarded_payload,
        route=route,
        stream_enabled=False,
    )


def node_results(
    config_path: Path,
    pipeline_context: PipelineContext,
) -> list[dict[str, Any]]:
    config = load_config(str(config_path))
    wrote = trace_runtime_event(
        config=config,
        diagnostics=RequestDiagnostics(
            request_id="r",
            character_id="default",
            route_model="relaylm-default",
            mode_applied=pipeline_context.route.mode_applied,
            compiler_used=pipeline_context.route.mode_applied == "memory_light",
        ),
        message_count=len(pipeline_context.original_payload.get("messages", [])),
        response_present=True,
    )
    require(wrote is True, wrote)
    record = json.loads(
        Path(config.trace.path).read_text().strip().splitlines()[-1]
    )
    return record["metadata"].get("pipeline_node_results", [])


def no_leak(value: Any) -> None:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) + repr(value)
    for sentinel in SENTINELS:
        require(sentinel not in rendered, sentinel)


def user_payload(messages: list[Any]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "stream": False}


def canonical(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = build_client_message_canonicalization_dry_run(
        payload,
        enabled=True,
        managed_route=True,
    )
    require(isinstance(artifact, dict), artifact)
    return artifact


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        root = Path(temp_dir)

        config_path = root / "off.yaml"
        config_file(config_path, enabled=False)
        payload = user_payload([{"role": "user", "content": SENTINELS[1]}])
        original = copy.deepcopy(payload)
        pipeline_context = context(config_path, payload)
        require(pipeline_context.client_history_exclusion_preflight_result is None, pipeline_context)
        require(pipeline_context.forwarded_payload == original, pipeline_context)
        require(build_client_history_exclusion_preflight_node_result(None) is None, "node")
        consume_active_pipeline_context()
        print("ok default-off")

        config_path = root / "on.yaml"
        config_file(config_path, enabled=True)
        payload = user_payload(
            [
                {"role": "user", "content": SENTINELS[0]},
                {"role": "assistant", "content": SENTINELS[0]},
                {"role": "user", "content": SENTINELS[1]},
            ]
        )
        original = copy.deepcopy(payload)
        pipeline_context = context(config_path, payload)
        result = pipeline_context.client_history_exclusion_preflight_result
        require(
            result
            and result.status == "ready"
            and result.instruction_resolution_mode == "none"
            and result.history_exclusion_apply_ready
            and result.excluded_message_count_candidate == 2,
            result,
        )
        require(result.current_user_message is not payload["messages"][-1], result)
        payload["messages"][-1]["content"] = "changed"
        require(result.current_user_message["content"] == SENTINELS[1], result)
        results = node_results(config_path, pipeline_context)
        names = [node["node_name"] for node in results]
        require(names[0] == "client_message_canonicalization", names)
        require("client_history_exclusion_preflight" in names, names)
        no_leak(results)
        require(pipeline_context.forwarded_payload == original, pipeline_context)
        print("ok dependency activation and no-instruction")

        config_path = root / "pass.yaml"
        config_file(config_path, enabled=True, mode="pass_through")
        pipeline_context = context(
            config_path,
            user_payload([{"role": "user", "content": SENTINELS[1]}]),
        )
        result = pipeline_context.client_history_exclusion_preflight_result
        require(
            result
            and result.status == "skipped"
            and result.current_user_message is None
            and "pass_through_route_exempt" in result.blocked_reasons,
            result,
        )
        consume_active_pipeline_context()
        print("ok pass-through")

        hit_payload = user_payload(
            [
                {"role": "system", "content": SENTINELS[3]},
                {"role": "developer", "content": SENTINELS[4]},
                {"role": "user", "content": SENTINELS[1]},
            ]
        )

        class Lookup:
            status = "hit"

        lookup = Lookup()
        result = preflight.build_client_history_exclusion_preflight(
            hit_payload,
            canonical(hit_payload),
            lookup,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "ready"
            and result.instruction_resolution_mode == "cache_hit"
            and result.raw_instruction_exclusion_candidate,
            result,
        )
        no_leak(build_client_history_exclusion_preflight_node_result(result).to_log_dict())

        lookup.status = "miss"
        result = preflight.build_client_history_exclusion_preflight(
            hit_payload,
            canonical(hit_payload),
            lookup,
            enabled=True,
            managed_route=True,
        )
        require(result and result.status == "pending" and result.first_pass_evidence_required, result)

        lookup.status = "blocked"
        result = preflight.build_client_history_exclusion_preflight(
            hit_payload,
            canonical(hit_payload),
            lookup,
            enabled=True,
            managed_route=True,
        )
        require(result and result.status == "blocked", result)
        print("ok cache hit miss blocked")

        multimodal = user_payload(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SENTINELS[1]},
                        {"type": "image_url", "image_url": {"url": SENTINELS[2]}},
                    ],
                }
            ]
        )
        result = preflight.build_client_history_exclusion_preflight(
            multimodal,
            canonical(multimodal),
            None,
            enabled=True,
            managed_route=True,
        )
        require(result and result.status == "ready" and result.current_user_multimodal, result)
        require(result.current_user_message is not multimodal["messages"][0], result)
        result.current_user_message["content"][1]["image_url"]["url"] = "mut"
        require(
            multimodal["messages"][0]["content"][1]["image_url"]["url"] == SENTINELS[2],
            multimodal,
        )
        no_leak(build_client_history_exclusion_preflight_node_result(result).to_log_dict())
        no_leak(result)
        print("ok multimodal detached privacy")

        invalid_payloads = [
            {"model": "relaylm-default"},
            {"model": "relaylm-default", "messages": "x"},
            user_payload([1]),
            user_payload([{"role": "assistant", "content": "x"}]),
            user_payload([{"role": "user", "content": "   "}]),
            user_payload([{"role": "user", "content": [{"type": "text", "text": ""}]}]),
        ]
        for invalid_payload in invalid_payloads:
            artifact = canonical(invalid_payload) if isinstance(invalid_payload.get("messages"), list) else None
            result = preflight.build_client_history_exclusion_preflight(
                invalid_payload,
                artifact,
                None,
                enabled=True,
                managed_route=True,
            )
            require(result and result.status == "blocked", (invalid_payload, result))
        print("ok invalid sources")

        stale_tool_payload = user_payload(
            [
                {"role": "user", "content": SENTINELS[0]},
                {
                    "role": "assistant",
                    "content": "x",
                    "tool_calls": [
                        {"id": SENTINELS[5], "function": {"arguments": SENTINELS[6]}}
                    ],
                },
                {"role": "tool", "content": SENTINELS[7]},
                {"role": "user", "content": SENTINELS[1]},
            ]
        )
        result = preflight.build_client_history_exclusion_preflight(
            stale_tool_payload,
            canonical(stale_tool_payload),
            None,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "ready"
            and result.history_exclusion_apply_ready
            and not result.active_tool_transaction_candidate
            and result.excluded_message_count_candidate == 3,
            result,
        )
        no_leak(build_client_history_exclusion_preflight_node_result(result).to_log_dict())
        print("ok stale completed tool history is excludable")

        active_tool_payload = user_payload(
            [
                {"role": "user", "content": SENTINELS[1]},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": SENTINELS[5], "function": {"arguments": SENTINELS[6]}}
                    ],
                },
                {"role": "tool", "content": SENTINELS[7]},
            ]
        )
        result = preflight.build_client_history_exclusion_preflight(
            active_tool_payload,
            canonical(active_tool_payload),
            None,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "blocked"
            and result.current_user_message is None
            and result.active_tool_transaction_candidate
            and "active_tool_transaction_requires_preservation" in result.blocked_reasons,
            result,
        )
        no_leak(build_client_history_exclusion_preflight_node_result(result).to_log_dict())
        print("ok active post-user tool transaction is blocked")

        config_path = root / "exception.yaml"
        config_file(config_path, enabled=True)
        original_builder = preflight.build_client_history_exclusion_preflight
        preflight.build_client_history_exclusion_preflight = (
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(SENTINELS[8]))
        )
        try:
            pipeline_context = context(
                config_path,
                user_payload([{"role": "user", "content": SENTINELS[1]}]),
            )
            result = pipeline_context.client_history_exclusion_preflight_result
            require(
                result
                and result.status == "blocked"
                and result.blocked_reasons == ("history_exclusion_preflight_preparation_failed",),
                result,
            )
            no_leak(build_client_history_exclusion_preflight_node_result(result).to_log_dict())
        finally:
            preflight.build_client_history_exclusion_preflight = original_builder
            consume_active_pipeline_context()
        print("ok runtime exception")

        config_path = root / "apply.yaml"
        config_file(
            config_path,
            enabled=True,
            mode="memory_light",
            apply_enabled=True,
            apply_dry_run_only=True,
        )
        pipeline_context = context(
            config_path,
            user_payload(
                [
                    {"role": "user", "content": SENTINELS[0]},
                    {"role": "assistant", "content": SENTINELS[0]},
                    {"role": "user", "content": SENTINELS[1]},
                ]
            ),
        )
        results = node_results(config_path, pipeline_context)
        names = [node["node_name"] for node in results]
        preflight_index = names.index("client_history_exclusion_preflight")
        apply_index = names.index("client_history_exclusion_apply")
        require(apply_index == preflight_index + 1, names)
        apply_node = results[apply_index]
        require(apply_node["decision"] == "client_history_exclusion_apply_ready", apply_node)
        require(apply_node["diagnostics"]["payload_candidate_present"] is True, apply_node)
        require(apply_node["diagnostics"]["payload_mutation_applied"] is False, apply_node)
        require(apply_node["artifacts"][0]["artifact_name"] == "client_history_exclusion_apply_summary", apply_node)
        no_leak(results)
        print("ok apply node typed projection and ordering")

        config_path = root / "order.yaml"
        config_file(config_path, enabled=True, lookup=True)
        pipeline_context = context(
            config_path,
            user_payload([{"role": "user", "content": SENTINELS[1]}]),
        )
        names = [node["node_name"] for node in node_results(config_path, pipeline_context)]
        expected = [
            "client_message_canonicalization",
            "client_instruction_extraction",
            "client_instruction_fingerprint",
            "client_instruction_identity",
            "client_instruction_cache",
            "client_instruction_cache_lookup",
            "client_instruction_relayscn_projection",
            "client_history_exclusion_preflight",
        ]
        require(names[:8] == expected, names)
        print("ok node ordering")

    print("client_history_exclusion_preflight_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
