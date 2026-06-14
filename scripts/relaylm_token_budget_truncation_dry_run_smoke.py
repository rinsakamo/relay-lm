from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.relayctx_repack import _build_token_budget_truncation_dry_run
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    cfg = base.model_dump()
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg["memory"]["token_budget"] = 30
    cfg["memory"]["chars_per_token"] = 4
    cfg["memory"]["token_budget_truncation_enabled"] = False
    config = RelayLMConfig.model_validate(cfg)

    route = resolve_route(config, "relaylm-default")
    request_data = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": "assistant " * 20},
            {"role": "user", "content": "latest user"},
        ],
        "stream": False,
    }
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload=request_data,
    )
    baseline = copy.deepcopy(compiled.payload.get("messages"))
    messages = compiled.payload.get("messages")
    require(isinstance(messages, list), compiled.payload)
    dry_run = _build_token_budget_truncation_dry_run(
        config=config,
        forwarded_messages=[item for item in messages if isinstance(item, dict)],
    )
    require(isinstance(dry_run, dict), dry_run)
    require(dry_run.get("applied") is False, dry_run)
    require(dry_run.get("apply_mode") == "dry_run", dry_run)
    require(dry_run.get("enforcement_enabled") is False, dry_run)
    require(compiled.payload.get("messages") == baseline, compiled.payload)
    print("ok truncation dry run disabled is response-neutral")

    cfg_enabled = base.model_dump()
    cfg_enabled["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg_enabled["memory"]["token_budget"] = 30
    cfg_enabled["memory"]["chars_per_token"] = 4
    cfg_enabled["memory"]["token_budget_truncation_enabled"] = True
    enabled = RelayLMConfig.model_validate(cfg_enabled)
    compiled_enabled = compile_chat_payload_if_enabled(
        config=enabled,
        route=resolve_route(enabled, "relaylm-default"),
        payload=request_data,
    )
    enabled_baseline = copy.deepcopy(compiled_enabled.payload.get("messages"))
    enabled_messages = compiled_enabled.payload.get("messages")
    require(isinstance(enabled_messages, list), compiled_enabled.payload)
    enabled_dry_run = _build_token_budget_truncation_dry_run(
        config=enabled,
        forwarded_messages=[
            item for item in enabled_messages if isinstance(item, dict)
        ],
    )
    require(isinstance(enabled_dry_run, dict), enabled_dry_run)
    require(enabled_dry_run.get("enforcement_enabled") is True, enabled_dry_run)
    require(enabled_dry_run.get("applied") is False, enabled_dry_run)
    require(enabled_dry_run.get("dropped_message_count", 0) > 0, enabled_dry_run)
    require(enabled_dry_run.get("preserved_system") is True, enabled_dry_run)
    require(enabled_dry_run.get("preserved_latest_user") is True, enabled_dry_run)
    require(compiled_enabled.payload.get("messages") == enabled_baseline, compiled_enabled.payload)
    print("ok truncation dry run enabled remains response-neutral")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_cfg = enabled.model_dump()
        trace_cfg["trace"] = {"enabled": True, "path": str(Path(tmpdir) / "trace.jsonl")}
        trace_config = RelayLMConfig.model_validate(trace_cfg)
        diagnostics = RequestDiagnostics(
            request_id="req-trunc-dry-run",
            token_budget_truncation=enabled_dry_run,
        )
        written = trace_runtime_event(
            config=trace_config,
            diagnostics=diagnostics,
            message_count=1,
            response_present=False,
        )
        require(written, "trace not written")
        metadata = json.loads(
            (Path(tmpdir) / "trace.jsonl").read_text(encoding="utf-8")
        )["metadata"]
        require("token_budget_truncation" not in metadata, metadata)
        require(metadata.get("projection_unsupported_artifact_count", 0) >= 1, metadata)
        print("ok unsupported truncation artifact is default-denied")

    blocked = _build_token_budget_truncation_dry_run(
        config=RelayLMConfig.model_validate(
            {**cfg_enabled, "memory": {**cfg_enabled["memory"], "token_budget": 5}}
        ),
        forwarded_messages=[
            {"role": "system", "content": "S" * 200},
            {"role": "user", "content": "U" * 200},
        ],
    )
    require(isinstance(blocked, dict), blocked)
    require(blocked.get("over_budget_after") is True, blocked)
    require(blocked.get("blocked_reason") == "preserved_messages_exceed_budget", blocked)
    print("ok truncation blocked case remains non-mutating")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
