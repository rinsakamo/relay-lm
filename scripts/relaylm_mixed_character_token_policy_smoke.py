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
from relaylm.token_policy_signal import build_token_policy_decision_artifact, build_token_policy_signal
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def config_data(global_shadow: bool) -> dict:
    data = load_config(REPO_ROOT / "config.example.yaml").model_dump()
    for suffix in ("a", "b", "c"):
        char = f"char_{suffix}"
        model = f"relaylm-char-{suffix}"
        data["characters"][char] = dict(data["characters"]["default"])
        data["model_routes"][model] = dict(data["model_routes"]["relaylm-default"])
        data["model_routes"][model]["character_id"] = char
    data["characters"]["char_a"]["token_policy_shadow_enabled"] = True
    data["characters"]["char_b"]["token_policy_shadow_enabled"] = False
    data["memory"]["token_policy_shadow_enabled"] = global_shadow
    return data


def decision(config: RelayLMConfig, model: str) -> tuple[dict, dict]:
    route = resolve_route(config, model)
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload={"model": model, "messages": [{"role": "user", "content": "hello"}], "stream": False},
    )
    enabled, source = _resolve_token_policy_shadow_setting(config, route)
    signal = build_token_policy_signal(compiled.token_memory_dry_run)
    result = build_token_policy_decision_artifact(signal, shadow_enabled=enabled, shadow_source=source)
    require(result.enforcement_enabled is False, result)
    return signal.to_log_dict(), result.to_log_dict()


def main() -> int:
    false_config = RelayLMConfig.model_validate(config_data(False))
    _, a = decision(false_config, "relaylm-char-a")
    _, b = decision(false_config, "relaylm-char-b")
    _, c0 = decision(false_config, "relaylm-char-c")
    require((a["shadow_enabled"], a["shadow_source"]) == (True, "character"), a)
    require((b["shadow_enabled"], b["shadow_source"]) == (False, "character"), b)
    require((c0["shadow_enabled"], c0["shadow_source"]) == (False, "global"), c0)
    print("ok global false character overrides")

    true_config = RelayLMConfig.model_validate(config_data(True))
    _, b1 = decision(true_config, "relaylm-char-b")
    _, c1 = decision(true_config, "relaylm-char-c")
    require((b1["shadow_enabled"], b1["shadow_source"]) == (False, "character"), b1)
    require((c1["shadow_enabled"], c1["shadow_source"]) == (True, "global"), c1)
    print("ok global true character overrides")

    with tempfile.TemporaryDirectory() as tmpdir:
        data = config_data(True)
        trace_path = Path(tmpdir) / "trace.jsonl"
        data["trace"] = {"enabled": True, "path": str(trace_path)}
        trace_config = RelayLMConfig.model_validate(data)
        for request_id, model in (("req-a", "relaylm-char-a"), ("req-b", "relaylm-char-b"), ("req-c", "relaylm-char-c")):
            signal_data, decision_data = decision(trace_config, model)
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                route_model=model,
                token_policy_signal=signal_data,
                token_policy_decision=decision_data,
            )
            require(trace_runtime_event(
                config=trace_config,
                diagnostics=diagnostics,
                message_count=1,
                response_present=False,
            ), request_id)
        rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
        require(len(rows) == 3, rows)
        for row in rows:
            metadata = row["metadata"]
            require("token_policy_signal" not in metadata, metadata)
            require("token_policy_decision" not in metadata, metadata)
        print("ok mixed character policy diagnostics stay outside audit metadata")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
