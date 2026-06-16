#!/usr/bin/env python3
"""Smoke checks for client-history exclusion apply runtime plumbing."""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import relaylm.client_history_exclusion_apply_runtime as apply_runtime
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def write_config(
    path: Path,
    *,
    enabled: bool,
    dry_run_only: bool,
    mode: str = "memory_light",
) -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
    )
    config["client_message_canonicalization_dry_run_enabled"] = False
    config["client_history_exclusion_preflight_enabled"] = False
    config["client_history_exclusion_apply_enabled"] = enabled
    config["client_history_exclusion_apply_dry_run_only"] = dry_run_only
    config["client_instruction_extraction_dry_run_enabled"] = False
    config["client_instruction_cache_lookup_enabled"] = False
    config["model_routes"]["relaylm-default"]["mode"] = mode
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def original_payload(*, with_instruction: bool = False) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "prior user secret"},
        {"role": "assistant", "content": "prior assistant secret"},
    ]
    if with_instruction:
        messages.insert(0, {"role": "system", "content": "instruction secret"})
    messages.append({"role": "user", "content": "current user secret"})
    return {
        "model": "relaylm-default",
        "messages": messages,
        "stream": False,
        "temperature": 0.2,
    }


def compiled_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    client_messages = [
        message
        for message in payload["messages"]
        if message.get("role") not in {"system", "developer"}
    ]
    result["messages"] = [
        {"role": "system", "content": "relay-owned profile context"},
        *copy.deepcopy(client_messages),
    ]
    return result


def context(config_path: Path, payload: dict[str, Any]) -> PipelineContext:
    config = load_config(config_path)
    route = resolve_route(config, "relaylm-default")
    return PipelineContext(
        request_id="request-id",
        run_id="run-id",
        original_payload=copy.deepcopy(payload),
        forwarded_payload=compiled_payload(payload),
        route=route,
        stream_enabled=False,
    )


def test_all() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        root = Path(temp_dir)

        off_path = root / "off.yaml"
        write_config(off_path, enabled=False, dry_run_only=True)
        payload = original_payload()
        pipeline_context = context(off_path, payload)
        before = copy.deepcopy(pipeline_context.forwarded_payload)
        result = apply_runtime.run_client_history_exclusion_apply_runtime(
            pipeline_context=pipeline_context,
            compiler_used=True,
        )
        require(result is None, result)
        require(
            pipeline_context.client_history_exclusion_apply_result is None
            and pipeline_context.forwarded_payload == before
            and pipeline_context.last_mutating_step is None,
            pipeline_context,
        )
        consume_active_pipeline_context()
        print("ok runtime default-off")

        dry_path = root / "dry.yaml"
        write_config(dry_path, enabled=True, dry_run_only=True)
        pipeline_context = context(dry_path, payload)
        require(
            pipeline_context.route.client_history_exclusion_preflight_enabled is True,
            pipeline_context.route,
        )
        before = copy.deepcopy(pipeline_context.forwarded_payload)
        result = apply_runtime.run_client_history_exclusion_apply_runtime(
            pipeline_context=pipeline_context,
            compiler_used=True,
        )
        require(
            result
            and result.status == "ready"
            and result.forwarded_payload is not None
            and result.payload_mutation_applied is False,
            result,
        )
        require(
            pipeline_context.client_history_exclusion_apply_result is result
            and pipeline_context.forwarded_payload == before
            and pipeline_context.last_mutating_step is None
            and not apply_runtime.client_history_exclusion_apply_blocks_backend(
                pipeline_context.route,
                result,
            ),
            pipeline_context,
        )
        consume_active_pipeline_context()
        print("ok runtime dry-run is mutation-neutral")

        apply_path = root / "apply.yaml"
        write_config(apply_path, enabled=True, dry_run_only=False)
        pipeline_context = context(apply_path, payload)
        result = apply_runtime.run_client_history_exclusion_apply_runtime(
            pipeline_context=pipeline_context,
            compiler_used=True,
        )
        require(
            result
            and result.status == "applied"
            and result.payload_mutation_applied is True
            and pipeline_context.last_mutating_step
            == "client_history_exclusion_apply"
            and len(pipeline_context.forwarded_payload["messages"]) == 2
            and pipeline_context.forwarded_payload["messages"][0]["role"]
            == "system"
            and pipeline_context.forwarded_payload["messages"][1]
            == payload["messages"][-1]
            and not apply_runtime.client_history_exclusion_apply_blocks_backend(
                pipeline_context.route,
                result,
            ),
            (result, pipeline_context.forwarded_payload),
        )
        consume_active_pipeline_context()
        print("ok runtime apply replaces forwarded payload")

        blocked_payload = original_payload(with_instruction=True)
        pipeline_context = context(apply_path, blocked_payload)
        before = copy.deepcopy(pipeline_context.forwarded_payload)
        result = apply_runtime.run_client_history_exclusion_apply_runtime(
            pipeline_context=pipeline_context,
            compiler_used=True,
        )
        require(
            result
            and result.status == "blocked"
            and result.forwarded_payload is None
            and pipeline_context.forwarded_payload == before
            and pipeline_context.last_mutating_step is None
            and apply_runtime.client_history_exclusion_apply_blocks_backend(
                pipeline_context.route,
                result,
            )
            and apply_runtime.client_history_exclusion_apply_failure_reason(result)
            == "client_history_exclusion_apply_blocked",
            (result, pipeline_context),
        )
        consume_active_pipeline_context()
        print("ok actual apply request fails closed when preflight blocks")

        pass_path = root / "pass.yaml"
        write_config(
            pass_path,
            enabled=True,
            dry_run_only=False,
            mode="pass_through",
        )
        pipeline_context = context(pass_path, payload)
        before = copy.deepcopy(pipeline_context.forwarded_payload)
        result = apply_runtime.run_client_history_exclusion_apply_runtime(
            pipeline_context=pipeline_context,
            compiler_used=False,
        )
        require(
            result
            and result.status == "skipped"
            and pipeline_context.forwarded_payload == before
            and not apply_runtime.client_history_exclusion_apply_blocks_backend(
                pipeline_context.route,
                result,
            ),
            result,
        )
        consume_active_pipeline_context()
        print("ok pass-through remains client-owned")

        pipeline_context = context(apply_path, payload)
        original_builder = apply_runtime.build_client_history_exclusion_apply
        apply_runtime.build_client_history_exclusion_apply = (
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("secret"))
        )
        try:
            result = apply_runtime.run_client_history_exclusion_apply_runtime(
                pipeline_context=pipeline_context,
                compiler_used=True,
            )
        finally:
            apply_runtime.build_client_history_exclusion_apply = original_builder
        require(
            result
            and result.status == "blocked"
            and apply_runtime.client_history_exclusion_apply_blocks_backend(
                pipeline_context.route,
                result,
            )
            and apply_runtime.client_history_exclusion_apply_failure_reason(result)
            == "client_history_exclusion_apply_preparation_failed",
            result,
        )
        consume_active_pipeline_context()
        print("ok runtime exception fails closed without exception text")


if __name__ == "__main__":
    test_all()
