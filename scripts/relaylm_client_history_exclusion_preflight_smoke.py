#!/usr/bin/env python3
"""Smoke checks for client history exclusion preflight."""

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
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event

SENTINELS = (
    "prior history sentinel",
    "current user text sentinel",
    "image/audio URL sentinel",
    "raw system instruction",
    "raw developer instruction",
    "normalized instruction",
    "SCENE_ROLE_SENTINEL_PRIVATE",
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
    cache_root: Path | None = None,
) -> None:
    config = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text())
    config["backends"]["local_backend"]["base_url"] = "http://127.0.0.1:9/v1"
    config["trace"] = {
        "enabled": True,
        "path": str(path.with_suffix(".jsonl")),
    }
    config["client_message_canonicalization_dry_run_enabled"] = canonicalization
    config["client_history_exclusion_preflight_enabled"] = enabled
    config["client_instruction_extraction_dry_run_enabled"] = lookup
    config["client_instruction_cache_lookup_enabled"] = lookup
    config["client_instruction_cache_root"] = str(cache_root) if cache_root else None
    config["model_routes"]["relaylm-default"]["mode"] = mode
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def context(config_path: Path, payload: dict[str, Any]) -> PipelineContext:
    config = load_config(str(config_path))
    route = resolve_route(config, payload.get("model", "relaylm-default"))
    return PipelineContext(
        request_id="r",
        run_id="u",
        original_payload=payload,
        forwarded_payload=copy.deepcopy(payload),
        route=route,
        stream_enabled=False,
    )


def node_results(
    config_path: Path,
    pipeline_context: PipelineContext,
) -> list[dict[str, Any]]:
    config = load_config(str(config_path))
    diagnostics = RequestDiagnostics(
        request_id="r",
        character_id="default",
        route_model="relaylm-default",
        mode_applied=pipeline_context.route.mode_applied,
        compiler_used=False,
    )
    trace_runtime_event(
        config=config,
        diagnostics=diagnostics,
        messages=[],
        response_text="ok",
    )
    record = json.loads(
        Path(config.trace.path).read_text().strip().splitlines()[-1]
    )
    return record["metadata"].get("pipeline_node_results", [])


def no_leak(value: Any, extra: tuple[str, ...] = ()) -> None:
    rendered = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        if not isinstance(value, str)
        else value
    ) + repr(value)
    for sentinel in SENTINELS + tuple(extra):
        require(sentinel not in rendered, sentinel)


def user_payload(messages: list[Any]) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages,
        "stream": False,
    }


def test_all() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        root = Path(temp_dir)

        # Default-off.
        config_path = root / "off.yaml"
        config_file(config_path, enabled=False)
        payload = user_payload(
            [{"role": "user", "content": "current user text sentinel"}]
        )
        original = copy.deepcopy(payload)
        pipeline_context = context(config_path, payload)
        require(
            pipeline_context.client_history_exclusion_preflight_result is None,
            pipeline_context,
        )
        require(
            pipeline_context.forwarded_payload == original
            and pipeline_context.original_payload == original
            and pipeline_context.last_mutating_step is None,
            pipeline_context,
        )
        require(build_client_history_exclusion_preflight_node_result(None) is None, "node")
        consume_active_pipeline_context()
        print("ok default-off")

        # Dependency activation and no instruction.
        config_path = root / "on.yaml"
        config_file(config_path, enabled=True, canonicalization=False)
        payload = user_payload(
            [
                {"role": "user", "content": "prior history sentinel"},
                {"role": "assistant", "content": "prior history sentinel"},
                {"role": "user", "content": "current user text sentinel"},
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
        require(
            result.current_user_message == payload["messages"][-1]
            and result.current_user_message is not payload["messages"][-1],
            result,
        )
        payload["messages"][-1]["content"] = "changed"
        require(
            result.current_user_message["content"] == "current user text sentinel",
            result.current_user_message,
        )
        results = node_results(config_path, pipeline_context)
        names = [node["node_name"] for node in results]
        require(
            names[:1] == ["client_message_canonicalization"]
            and "client_history_exclusion_preflight" in names,
            names,
        )
        no_leak(results)
        require(
            pipeline_context.forwarded_payload == original
            and pipeline_context.last_mutating_step is None,
            pipeline_context,
        )
        print("ok dependency activation and no-instruction")

        # Pass-through.
        config_path = root / "pass.yaml"
        config_file(config_path, enabled=True, mode="pass_through")
        pipeline_context = context(
            config_path,
            user_payload(
                [{"role": "user", "content": "current user text sentinel"}]
            ),
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

        # Cache hit, miss, and blocked states.
        hit_payload = user_payload(
            [
                {"role": "system", "content": "raw system instruction"},
                {"role": "developer", "content": "raw developer instruction"},
                {"role": "user", "content": "current user text sentinel"},
            ]
        )
        artifact = build_client_message_canonicalization_dry_run(
            hit_payload,
            enabled=True,
            managed_route=True,
        )

        class Lookup:
            status = "hit"

        lookup = Lookup()
        result = preflight.build_client_history_exclusion_preflight(
            hit_payload,
            artifact,
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
        no_leak(
            preflight.build_client_history_exclusion_preflight_node_result(
                result
            ).to_log_dict()
        )
        print("ok cache hit")

        miss_payload = user_payload(
            [
                {"role": "system", "content": "raw system instruction"},
                {"role": "user", "content": "current user text sentinel"},
            ]
        )
        miss_artifact = build_client_message_canonicalization_dry_run(
            miss_payload,
            enabled=True,
            managed_route=True,
        )
        lookup.status = "miss"
        result = preflight.build_client_history_exclusion_preflight(
            miss_payload,
            miss_artifact,
            lookup,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "pending"
            and result.first_pass_evidence_required
            and not result.blocked_reasons,
            result,
        )
        require(
            preflight.build_client_history_exclusion_preflight_node_result(
                result
            ).decision
            == "client_instruction_first_pass_required",
            result,
        )
        print("ok cache miss")

        lookup.status = "blocked"
        result = preflight.build_client_history_exclusion_preflight(
            miss_payload,
            miss_artifact,
            lookup,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "blocked"
            and not result.history_exclusion_apply_ready,
            result,
        )
        print("ok cache blocked")

        # Multimodal detach and privacy.
        multimodal = user_payload(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "current user text sentinel"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "image/audio URL sentinel"},
                        },
                    ],
                }
            ]
        )
        artifact = build_client_message_canonicalization_dry_run(
            multimodal,
            enabled=True,
            managed_route=True,
        )
        result = preflight.build_client_history_exclusion_preflight(
            multimodal,
            artifact,
            None,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "ready"
            and result.current_user_multimodal
            and result.current_user_message is not multimodal["messages"][0],
            result,
        )
        result.current_user_message["content"][1]["image_url"]["url"] = "mut"
        require(
            multimodal["messages"][0]["content"][1]["image_url"]["url"]
            == "image/audio URL sentinel",
            multimodal,
        )
        no_leak(
            preflight.build_client_history_exclusion_preflight_node_result(
                result
            ).to_log_dict()
        )
        no_leak(result)
        print("ok multimodal detached privacy")

        # Invalid sources.
        invalid_payloads = [
            {"model": "relaylm-default"},
            {"model": "relaylm-default", "messages": "x"},
            user_payload([1]),
            user_payload([{"role": "assistant", "content": "x"}]),
            user_payload([{"role": "user", "content": "   "}]),
            user_payload(
                [{"role": "user", "content": [{"type": "text", "text": ""}]}]
            ),
        ]
        for invalid_payload in invalid_payloads:
            artifact = (
                build_client_message_canonicalization_dry_run(
                    invalid_payload,
                    enabled=True,
                    managed_route=True,
                )
                if isinstance(invalid_payload.get("messages"), list)
                else None
            )
            result = preflight.build_client_history_exclusion_preflight(
                invalid_payload,
                artifact,
                None,
                enabled=True,
                managed_route=True,
            )
            require(result and result.status == "blocked", (invalid_payload, result))
        print("ok invalid sources")

        # Completed tool history before the current user is stale and excludable.
        stale_tool_payload = user_payload(
            [
                {"role": "user", "content": "prior history sentinel"},
                {
                    "role": "assistant",
                    "content": "x",
                    "tool_calls": [
                        {
                            "id": "tool_call_secret",
                            "function": {"arguments": "tool args secret"},
                        }
                    ],
                },
                {"role": "tool", "content": "tool result secret"},
                {"role": "user", "content": "current user text sentinel"},
            ]
        )
        artifact = build_client_message_canonicalization_dry_run(
            stale_tool_payload,
            enabled=True,
            managed_route=True,
        )
        result = preflight.build_client_history_exclusion_preflight(
            stale_tool_payload,
            artifact,
            None,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "ready"
            and result.instruction_resolution_mode == "none"
            and result.history_exclusion_apply_ready
            and not result.active_tool_transaction_candidate
            and result.excluded_message_count_candidate == 3,
            result,
        )
        no_leak(
            preflight.build_client_history_exclusion_preflight_node_result(
                result
            ).to_log_dict()
        )
        print("ok stale completed tool history is excludable")

        # Tool activity after the current user remains an active transaction.
        active_tool_payload = user_payload(
            [
                {"role": "user", "content": "current user text sentinel"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tool_call_secret",
                            "function": {"arguments": "tool args secret"},
                        }
                    ],
                },
                {"role": "tool", "content": "tool result secret"},
            ]
        )
        artifact = build_client_message_canonicalization_dry_run(
            active_tool_payload,
            enabled=True,
            managed_route=True,
        )
        result = preflight.build_client_history_exclusion_preflight(
            active_tool_payload,
            artifact,
            None,
            enabled=True,
            managed_route=True,
        )
        require(
            result
            and result.status == "blocked"
            and result.current_user_message is None
            and not result.history_exclusion_apply_ready
            and result.active_tool_transaction_candidate
            and "active_tool_transaction_requires_preservation"
            in result.blocked_reasons,
            result,
        )
        no_leak(
            preflight.build_client_history_exclusion_preflight_node_result(
                result
            ).to_log_dict()
        )
        print("ok active post-user tool transaction is blocked")

        # Runtime exception.
        config_path = root / "ex.yaml"
        config_file(config_path, enabled=True)
        original_builder = preflight.build_client_history_exclusion_preflight
        preflight.build_client_history_exclusion_preflight = (
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("exception sentinel")
            )
        )
        try:
            pipeline_context = context(
                config_path,
                user_payload(
                    [{"role": "user", "content": "current user text sentinel"}]
                ),
            )
            result = pipeline_context.client_history_exclusion_preflight_result
            require(
                result
                and result.status == "blocked"
                and result.blocked_reasons
                == ("history_exclusion_preflight_preparation_failed",),
                result,
            )
            no_leak(
                preflight.build_client_history_exclusion_preflight_node_result(
                    result
                ).to_log_dict()
            )
        finally:
            preflight.build_client_history_exclusion_preflight = original_builder
            consume_active_pipeline_context()
        print("ok runtime exception")

        # Ordering with lookup enabled. Empty-instruction lookup is source-blocked,
        # but history exclusion can still be ready.
        config_path = root / "ord.yaml"
        config_file(
            config_path,
            enabled=True,
            canonicalization=False,
            lookup=True,
        )
        pipeline_context = context(
            config_path,
            user_payload(
                [{"role": "user", "content": "current user text sentinel"}]
            ),
        )
        results = node_results(config_path, pipeline_context)
        names = [node["node_name"] for node in results]
        expected = [
            "client_message_canonicalization",
            "client_instruction_extraction",
            "client_instruction_fingerprint",
            "client_instruction_identity",
            "client_instruction_cache",
            "client_instruction_cache_lookup",
            "client_history_exclusion_preflight",
        ]
        require(names[:7] == expected, names)
        no_leak(results)
        print("ok ordering and privacy")


if __name__ == "__main__":
    test_all()
    print("client_history_exclusion_preflight_smoke passed")
