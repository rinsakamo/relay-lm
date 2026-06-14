#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import relaylm.client_history_exclusion_preflight as preflight
from relaylm.client_message_canonicalization import build_client_message_canonicalization_dry_run
from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event

MARKERS = ("prior-marker", "current-marker", "instruction-marker", "tool-marker")


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def write_config(path: Path, *, enabled: bool = True, lookup: bool = False, mode: str = "memory_full") -> None:
    data = yaml.safe_load((ROOT / "config.example.yaml").read_text())
    data["trace"] = {"enabled": True, "path": str(path.with_suffix(".jsonl"))}
    data["client_message_canonicalization_dry_run_enabled"] = False
    data["client_history_exclusion_preflight_enabled"] = enabled
    data["client_instruction_extraction_dry_run_enabled"] = lookup
    data["client_instruction_cache_lookup_enabled"] = lookup
    data["client_instruction_cache_root"] = None
    data["model_routes"]["relaylm-default"]["mode"] = mode
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def request(messages: list[Any]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "stream": False}


def context(path: Path, body: dict[str, Any]) -> PipelineContext:
    config = load_config(str(path))
    return PipelineContext(
        request_id="r",
        run_id="u",
        original_payload=body,
        forwarded_payload=copy.deepcopy(body),
        route=resolve_route(config, "relaylm-default"),
        stream_enabled=False,
    )


def canonical(body: dict[str, Any]) -> dict[str, Any]:
    value = build_client_message_canonicalization_dry_run(body, enabled=True, managed_route=True)
    require(isinstance(value, dict), value)
    return value


def node_results(path: Path, ctx: PipelineContext) -> list[dict[str, Any]]:
    config = load_config(str(path))
    require(trace_runtime_event(
        config=config,
        diagnostics=RequestDiagnostics(
            request_id="r",
            character_id="default",
            route_model="relaylm-default",
            mode_applied=ctx.route.mode_applied,
        ),
        message_count=len(ctx.original_payload.get("messages", [])),
        response_present=True,
    ), "trace write")
    record = json.loads(Path(config.trace.path).read_text().splitlines()[-1])
    return record["metadata"]["pipeline_node_results"]


def no_markers(value: object) -> None:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for marker in MARKERS:
        require(marker not in rendered, rendered)


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
        root = Path(temp_dir)

        off = root / "off.yaml"
        write_config(off, enabled=False)
        off_ctx = context(off, request([{"role": "user", "content": MARKERS[1]}]))
        require(off_ctx.client_history_exclusion_preflight_result is None, off_ctx)
        consume_active_pipeline_context()
        print("ok default-off")

        on = root / "on.yaml"
        write_config(on)
        body = request([
            {"role": "user", "content": MARKERS[0]},
            {"role": "assistant", "content": MARKERS[0]},
            {"role": "user", "content": MARKERS[1]},
        ])
        original = copy.deepcopy(body)
        ctx = context(on, body)
        result = ctx.client_history_exclusion_preflight_result
        require(
            result and result.status == "ready"
            and result.instruction_resolution_mode == "none"
            and result.history_exclusion_apply_ready
            and result.excluded_message_count_candidate == 2,
            result,
        )
        nodes = node_results(on, ctx)
        names = [item["node_name"] for item in nodes]
        require(names[0] == "client_message_canonicalization", names)
        require("client_history_exclusion_preflight" in names, names)
        no_markers(nodes)
        require(ctx.forwarded_payload == original and ctx.last_mutating_step is None, ctx)
        print("ok ready preflight and typed projection")

        pass_path = root / "pass.yaml"
        write_config(pass_path, mode="pass_through")
        pass_ctx = context(pass_path, request([{"role": "user", "content": MARKERS[1]}]))
        skipped = pass_ctx.client_history_exclusion_preflight_result
        require(
            skipped and skipped.status == "skipped"
            and "pass_through_route_exempt" in skipped.blocked_reasons,
            skipped,
        )
        consume_active_pipeline_context()
        print("ok pass-through")

        instruction_body = request([
            {"role": "system", "content": MARKERS[2]},
            {"role": "user", "content": MARKERS[1]},
        ])

        class Lookup:
            status = "hit"

        lookup = Lookup()
        hit = preflight.build_client_history_exclusion_preflight(
            instruction_body, canonical(instruction_body), lookup,
            enabled=True, managed_route=True,
        )
        require(hit and hit.status == "ready" and hit.instruction_resolution_mode == "cache_hit", hit)
        lookup.status = "miss"
        miss = preflight.build_client_history_exclusion_preflight(
            instruction_body, canonical(instruction_body), lookup,
            enabled=True, managed_route=True,
        )
        require(miss and miss.status == "pending" and miss.first_pass_evidence_required, miss)
        lookup.status = "blocked"
        blocked = preflight.build_client_history_exclusion_preflight(
            instruction_body, canonical(instruction_body), lookup,
            enabled=True, managed_route=True,
        )
        require(blocked and blocked.status == "blocked", blocked)
        no_markers(preflight.build_client_history_exclusion_preflight_node_result(hit).to_log_dict())
        print("ok cache hit miss blocked")

        active_body = request([
            {"role": "user", "content": MARKERS[1]},
            {"role": "assistant", "content": None, "tool_calls": [{"id": MARKERS[3], "function": {"arguments": MARKERS[3]}}]},
            {"role": "tool", "content": MARKERS[3]},
        ])
        active = preflight.build_client_history_exclusion_preflight(
            active_body, canonical(active_body), None,
            enabled=True, managed_route=True,
        )
        require(
            active and active.status == "blocked"
            and active.active_tool_transaction_candidate
            and "active_tool_transaction_requires_preservation" in active.blocked_reasons,
            active,
        )
        no_markers(preflight.build_client_history_exclusion_preflight_node_result(active).to_log_dict())
        print("ok active tool transaction blocked")

        order = root / "order.yaml"
        write_config(order, lookup=True)
        order_ctx = context(order, request([{"role": "user", "content": MARKERS[1]}]))
        order_names = [item["node_name"] for item in node_results(order, order_ctx)]
        expected = [
            "client_message_canonicalization", "client_instruction_extraction",
            "client_instruction_fingerprint", "client_instruction_identity",
            "client_instruction_cache", "client_instruction_cache_lookup",
            "client_history_exclusion_preflight",
        ]
        require(order_names[:7] == expected, order_names)
        print("ok node ordering")

    print("client_history_exclusion_preflight_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
