from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _resolve_token_policy_shadow_setting
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_signal,
)
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _base_config_dict() -> dict:
    base = load_config(REPO_ROOT / "config.example.yaml")
    config_dict = base.model_dump()
    config_dict["characters"]["char_a"] = dict(config_dict["characters"]["default"])
    config_dict["characters"]["char_b"] = dict(config_dict["characters"]["default"])
    config_dict["characters"]["char_c"] = dict(config_dict["characters"]["default"])
    config_dict["characters"]["char_a"]["token_policy_shadow_enabled"] = True
    config_dict["characters"]["char_b"]["token_policy_shadow_enabled"] = False
    config_dict["model_routes"]["relaylm-char-a"] = dict(config_dict["model_routes"]["relaylm-default"])
    config_dict["model_routes"]["relaylm-char-a"]["character_id"] = "char_a"
    config_dict["model_routes"]["relaylm-char-b"] = dict(config_dict["model_routes"]["relaylm-default"])
    config_dict["model_routes"]["relaylm-char-b"]["character_id"] = "char_b"
    config_dict["model_routes"]["relaylm-char-c"] = dict(config_dict["model_routes"]["relaylm-default"])
    config_dict["model_routes"]["relaylm-char-c"]["character_id"] = "char_c"
    return config_dict


def _decision_for_model(config: RelayLMConfig, model: str) -> tuple[dict, dict]:
    route = resolve_route(config, model)
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload={"model": model, "messages": [{"role": "user", "content": "hello"}], "stream": False},
    )
    require(compiled.payload.get("model") == model, compiled.payload)
    require(compiled.payload.get("stream") is False, compiled.payload)
    shadow_enabled, shadow_source = _resolve_token_policy_shadow_setting(config, route)
    signal = build_token_policy_signal(compiled.token_memory_dry_run)
    decision = build_token_policy_decision_artifact(
        signal,
        shadow_enabled=shadow_enabled,
        shadow_source=shadow_source,
    )
    require(decision.enforcement_enabled is False, decision)
    return signal.to_log_dict(), decision.to_log_dict()


def main() -> int:
    config_dict = _base_config_dict()
    config_dict["memory"]["token_policy_shadow_enabled"] = False
    config_false = RelayLMConfig.model_validate(config_dict)

    _, decision_a = _decision_for_model(config_false, "relaylm-char-a")
    require(decision_a["shadow_enabled"] is True, decision_a)
    require(decision_a["shadow_source"] == "character", decision_a)
    require(decision_a["policy_mode"] == "shadow", decision_a)
    require(decision_a["action"] in {"shadow_only", "would_fallback", "none"}, decision_a)
    print("ok global false + character true override")

    _, decision_b = _decision_for_model(config_false, "relaylm-char-b")
    require(decision_b["shadow_enabled"] is False, decision_b)
    require(decision_b["shadow_source"] == "character", decision_b)
    require(decision_b["policy_mode"] == "disabled", decision_b)
    require(decision_b["action"] == "none", decision_b)
    print("ok global false + character false override")

    _, decision_c_false = _decision_for_model(config_false, "relaylm-char-c")
    require(decision_c_false["shadow_enabled"] is False, decision_c_false)
    require(decision_c_false["shadow_source"] == "global", decision_c_false)
    require(decision_c_false["policy_mode"] == "disabled", decision_c_false)
    require(decision_c_false["action"] == "none", decision_c_false)
    print("ok global false + character unset fallback")

    config_dict_true = _base_config_dict()
    config_dict_true["memory"]["token_policy_shadow_enabled"] = True
    config_true = RelayLMConfig.model_validate(config_dict_true)

    _, decision_b_true = _decision_for_model(config_true, "relaylm-char-b")
    require(decision_b_true["shadow_enabled"] is False, decision_b_true)
    require(decision_b_true["shadow_source"] == "character", decision_b_true)
    require(decision_b_true["policy_mode"] == "disabled", decision_b_true)
    require(decision_b_true["action"] == "none", decision_b_true)
    print("ok global true + character false override")

    signal_c_true, decision_c_true = _decision_for_model(config_true, "relaylm-char-c")
    require(decision_c_true["shadow_enabled"] is True, decision_c_true)
    require(decision_c_true["shadow_source"] == "global", decision_c_true)
    require(decision_c_true["policy_mode"] == "shadow", decision_c_true)
    require(decision_c_true["action"] in {"shadow_only", "would_fallback", "none"}, decision_c_true)
    print("ok global true + character unset fallback")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        trace_dict = config_dict_true
        trace_dict["trace"] = {"enabled": True, "path": str(trace_path)}
        trace_config = RelayLMConfig.model_validate(trace_dict)

        for req_id, model in [("req-a", "relaylm-char-a"), ("req-b", "relaylm-char-b"), ("req-c", "relaylm-char-c")]:
            signal_dict, decision_dict = _decision_for_model(trace_config, model)
            diagnostics = RequestDiagnostics(
                request_id=req_id,
                route_model=model,
                token_policy_signal=signal_dict,
                token_policy_decision=decision_dict,
            )
            written = trace_runtime_event(
                config=trace_config,
                diagnostics=diagnostics,
                messages=[{"role": "user", "content": f"hello {model}"}],
            )
            require(written, req_id)

        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(len(lines) == 3, lines)
        records = [json.loads(line) for line in lines]
        by_id = {record.get("trace_id"): record for record in records}
        require(by_id["req-a"]["metadata"]["token_policy_decision"]["shadow_source"] == "character", by_id["req-a"])
        require(by_id["req-b"]["metadata"]["token_policy_decision"]["shadow_source"] == "character", by_id["req-b"])
        require(by_id["req-c"]["metadata"]["token_policy_decision"]["shadow_source"] == "global", by_id["req-c"])
        print("ok mixed character trace metadata decisions")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
