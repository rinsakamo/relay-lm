from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _maybe_apply_token_budget_truncation
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": "assistant " * 20},
            {"role": "assistant", "content": "assistant 2 " * 20},
            {"role": "user", "content": "latest user"},
        ],
        "stream": False,
        "temperature": 0.2,
    }

    cfg = base.model_dump()
    cfg["memory"]["token_budget"] = 30
    cfg["memory"]["chars_per_token"] = 4
    cfg["memory"]["token_budget_truncation_enabled"] = False
    config_disabled = RelayLMConfig.model_validate(cfg)
    baseline_input = copy.deepcopy(payload)
    forwarded_disabled, result_disabled = _maybe_apply_token_budget_truncation(config=config_disabled, payload=payload)
    require(forwarded_disabled["messages"] == baseline_input["messages"], forwarded_disabled)
    require(result_disabled is not None and result_disabled.get("applied") is False, result_disabled)
    require(result_disabled.get("apply_mode") == "dry_run", result_disabled)
    require(payload == baseline_input, payload)
    print("ok truncation apply default disabled keeps forwarding payload unchanged")

    cfg_enabled = base.model_dump()
    cfg_enabled["memory"]["token_budget"] = 5000
    cfg_enabled["memory"]["chars_per_token"] = 4
    cfg_enabled["memory"]["token_budget_truncation_enabled"] = True
    config_enabled_within = RelayLMConfig.model_validate(cfg_enabled)
    baseline_within = copy.deepcopy(payload)
    forwarded_within, result_within = _maybe_apply_token_budget_truncation(config=config_enabled_within, payload=payload)
    require(forwarded_within["messages"] == baseline_within["messages"], forwarded_within)
    require(result_within is not None and result_within.get("applied") is False, result_within)
    require(result_within.get("apply_mode") == "runtime_apply", result_within)
    require(result_within.get("dropped_message_count") == 0, result_within)
    require(payload == baseline_within, payload)
    print("ok truncation apply enabled within budget keeps forwarding payload unchanged")

    cfg_apply = base.model_dump()
    cfg_apply["memory"]["token_budget"] = 30
    cfg_apply["memory"]["chars_per_token"] = 4
    cfg_apply["memory"]["token_budget_truncation_enabled"] = True
    config_enabled = RelayLMConfig.model_validate(cfg_apply)
    baseline_over = copy.deepcopy(payload)
    forwarded_apply, result_apply = _maybe_apply_token_budget_truncation(config=config_enabled, payload=payload)
    require(result_apply is not None and result_apply.get("applied") is True, result_apply)
    require(result_apply.get("apply_mode") == "runtime_apply", result_apply)
    require(result_apply.get("dropped_message_count", 0) > 0, result_apply)
    require(result_apply.get("preserved_system") is True, result_apply)
    require(result_apply.get("preserved_latest_user") is True, result_apply)
    require(len(forwarded_apply["messages"]) < len(baseline_over["messages"]), forwarded_apply)
    require(forwarded_apply.get("model") == baseline_over["model"], forwarded_apply)
    require(forwarded_apply.get("stream") == baseline_over["stream"], forwarded_apply)
    require(forwarded_apply.get("temperature") == baseline_over["temperature"], forwarded_apply)
    require(payload == baseline_over, payload)
    print("ok truncation apply enabled over budget shortens forwarding messages")

    blocked_payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "S" * 200},
            {"role": "user", "content": "U" * 200},
        ],
        "stream": False,
    }
    blocked_baseline = copy.deepcopy(blocked_payload)
    cfg_blocked = base.model_dump()
    cfg_blocked["memory"]["token_budget"] = 5
    cfg_blocked["memory"]["chars_per_token"] = 4
    cfg_blocked["memory"]["token_budget_truncation_enabled"] = True
    config_blocked = RelayLMConfig.model_validate(cfg_blocked)
    forwarded_blocked, result_blocked = _maybe_apply_token_budget_truncation(config=config_blocked, payload=blocked_payload)
    require(result_blocked is not None and result_blocked.get("applied") is False, result_blocked)
    require(result_blocked.get("blocked_reason") == "preserved_messages_exceed_budget", result_blocked)
    require(forwarded_blocked["messages"] == blocked_baseline["messages"], forwarded_blocked)
    require(blocked_payload == blocked_baseline, blocked_payload)
    print("ok truncation apply blocked case keeps forwarding payload unchanged")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_data = config_enabled.model_dump()
        trace_data["trace"] = {"enabled": True, "path": str(Path(tmpdir) / "trace.jsonl")}
        trace_config = RelayLMConfig.model_validate(trace_data)
        diagnostics = RequestDiagnostics(request_id="req-trunc-apply", token_budget_truncation=result_apply)
        written = trace_runtime_event(config=trace_config, diagnostics=diagnostics, messages=forwarded_apply["messages"])
        require(written, "trace not written")
        record = json.loads((Path(tmpdir) / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()[0])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), metadata)
        tbt = metadata.get("token_budget_truncation")
        require(isinstance(tbt, dict), metadata)
        require(tbt.get("applied") is True, tbt)
        require(tbt.get("apply_mode") == "runtime_apply", tbt)
        print("ok truncation apply diagnostics and trace metadata record applied true")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
