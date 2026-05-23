from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _build_token_budget_truncation_dry_run
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    cfg = base.model_dump()
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg["memory"]["token_budget"] = 30
    cfg["memory"]["chars_per_token"] = 4
    cfg["memory"]["token_budget_truncation_enabled"] = False
    config = RelayLMConfig.model_validate(cfg)

    route = resolve_route(config, "relaylm-default")
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": "assistant " * 20},
            {"role": "user", "content": "latest user"},
        ],
        "stream": False,
    }
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    baseline_messages = copy.deepcopy(compiled.payload.get("messages"))
    original_messages = compiled.payload.get("messages")
    require(isinstance(original_messages, list), compiled.payload)
    dry_run = _build_token_budget_truncation_dry_run(
        config=config,
        forwarded_messages=[m for m in original_messages if isinstance(m, dict)],
    )
    require(isinstance(dry_run, dict), dry_run)
    require(dry_run.get("applied") is False, dry_run)
    require(dry_run.get("apply_mode") == "dry_run", dry_run)
    require(dry_run.get("enforcement_enabled") is False, dry_run)
    require(dry_run.get("dropped_message_count", 0) >= 0, dry_run)
    require(compiled.payload.get("messages") == baseline_messages, compiled.payload)
    print("ok truncation dry run default disabled keeps forwarding payload unchanged")

    cfg2 = base.model_dump()
    cfg2["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg2["memory"]["token_budget"] = 30
    cfg2["memory"]["chars_per_token"] = 4
    cfg2["memory"]["token_budget_truncation_enabled"] = True
    config_enabled = RelayLMConfig.model_validate(cfg2)
    route_enabled = resolve_route(config_enabled, "relaylm-default")
    compiled_enabled = compile_chat_payload_if_enabled(config=config_enabled, route=route_enabled, payload=payload)
    baseline_messages_enabled = copy.deepcopy(compiled_enabled.payload.get("messages"))
    msgs_enabled = compiled_enabled.payload.get("messages")
    require(isinstance(msgs_enabled, list), compiled_enabled.payload)
    dry_run_enabled = _build_token_budget_truncation_dry_run(
        config=config_enabled,
        forwarded_messages=[m for m in msgs_enabled if isinstance(m, dict)],
    )
    require(isinstance(dry_run_enabled, dict), dry_run_enabled)
    require(dry_run_enabled.get("enforcement_enabled") is True, dry_run_enabled)
    require(dry_run_enabled.get("applied") is False, dry_run_enabled)
    require(dry_run_enabled.get("dropped_message_count", 0) > 0, dry_run_enabled)
    require(dry_run_enabled.get("preserved_system") is True, dry_run_enabled)
    require(dry_run_enabled.get("preserved_latest_user") is True, dry_run_enabled)
    require(compiled_enabled.payload.get("messages") == baseline_messages_enabled, compiled_enabled.payload)
    print("ok truncation dry run enabled still keeps forwarding payload unchanged")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_cfg = config_enabled.model_dump()
        trace_cfg["trace"] = {"enabled": True, "path": str(Path(tmpdir) / "trace.jsonl")}
        trace_config = RelayLMConfig.model_validate(trace_cfg)
        diagnostics = RequestDiagnostics(
            request_id="req-trunc-dry-run",
            token_budget_truncation=dry_run_enabled,
        )
        written = trace_runtime_event(
            config=trace_config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
        )
        require(written, "trace not written")
        trace_path = Path(tmpdir) / "trace.jsonl"
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[0])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), metadata)
        require(isinstance(metadata.get("token_budget_truncation"), dict), metadata)
        require(metadata["token_budget_truncation"].get("applied") is False, metadata)
        print("ok truncation dry run diagnostics and trace metadata recorded")

    blocked = _build_token_budget_truncation_dry_run(
        config=RelayLMConfig.model_validate(
            {
                **cfg2,
                "memory": {**cfg2["memory"], "token_budget": 5},
            }
        ),
        forwarded_messages=[
            {"role": "system", "content": "S" * 200},
            {"role": "user", "content": "U" * 200},
        ],
    )
    require(isinstance(blocked, dict), blocked)
    require(blocked.get("over_budget_after") is True, blocked)
    require(blocked.get("blocked_reason") == "preserved_messages_exceed_budget", blocked)
    print("ok truncation dry run blocked case does not alter request path")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
