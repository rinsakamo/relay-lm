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
from relaylm.relayctx_repack import _maybe_apply_token_budget_truncation
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    request_data = {
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
    disabled = RelayLMConfig.model_validate(cfg)
    baseline = copy.deepcopy(request_data)
    forwarded, result = _maybe_apply_token_budget_truncation(
        config=disabled,
        payload=request_data,
    )
    require(forwarded["messages"] == baseline["messages"], forwarded)
    require(result is not None and result.get("applied") is False, result)
    require(result.get("apply_mode") == "dry_run", result)
    require(request_data == baseline, request_data)
    print("ok truncation apply disabled is request-neutral")

    cfg_within = base.model_dump()
    cfg_within["memory"]["token_budget"] = 5000
    cfg_within["memory"]["chars_per_token"] = 4
    cfg_within["memory"]["token_budget_truncation_enabled"] = True
    within = RelayLMConfig.model_validate(cfg_within)
    within_baseline = copy.deepcopy(request_data)
    forwarded_within, result_within = _maybe_apply_token_budget_truncation(
        config=within,
        payload=request_data,
    )
    require(forwarded_within["messages"] == within_baseline["messages"], forwarded_within)
    require(result_within is not None and result_within.get("applied") is False, result_within)
    require(result_within.get("apply_mode") == "runtime_apply", result_within)
    require(result_within.get("dropped_message_count") == 0, result_within)
    require(request_data == within_baseline, request_data)
    print("ok truncation apply within budget is request-neutral")

    cfg_apply = base.model_dump()
    cfg_apply["memory"]["token_budget"] = 30
    cfg_apply["memory"]["chars_per_token"] = 4
    cfg_apply["memory"]["token_budget_truncation_enabled"] = True
    enabled = RelayLMConfig.model_validate(cfg_apply)
    apply_baseline = copy.deepcopy(request_data)
    forwarded_apply, result_apply = _maybe_apply_token_budget_truncation(
        config=enabled,
        payload=request_data,
    )
    require(result_apply is not None and result_apply.get("applied") is True, result_apply)
    require(result_apply.get("apply_mode") == "runtime_apply", result_apply)
    require(result_apply.get("dropped_message_count", 0) > 0, result_apply)
    require(result_apply.get("preserved_system") is True, result_apply)
    require(result_apply.get("preserved_latest_user") is True, result_apply)
    require(len(forwarded_apply["messages"]) < len(apply_baseline["messages"]), forwarded_apply)
    require(forwarded_apply.get("model") == apply_baseline["model"], forwarded_apply)
    require(forwarded_apply.get("stream") == apply_baseline["stream"], forwarded_apply)
    require(forwarded_apply.get("temperature") == apply_baseline["temperature"], forwarded_apply)
    require(request_data == apply_baseline, request_data)
    print("ok truncation apply over budget shortens forwarded messages")

    malformed = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system"},
            "not-a-dict-message",
            {"role": "user", "content": "latest user"},
        ],
        "stream": False,
    }
    malformed_baseline = copy.deepcopy(malformed)
    malformed_config = RelayLMConfig.model_validate(cfg_within)
    forwarded_malformed, result_malformed = _maybe_apply_token_budget_truncation(
        config=malformed_config,
        payload=malformed,
    )
    require(result_malformed is not None and result_malformed.get("applied") is False, result_malformed)
    require(result_malformed.get("dropped_message_count") == 0, result_malformed)
    require(forwarded_malformed.get("messages") == malformed_baseline["messages"], forwarded_malformed)
    require(malformed == malformed_baseline, malformed)
    print("ok truncation apply preserves malformed in-budget input")

    blocked_data = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "S" * 200},
            {"role": "user", "content": "U" * 200},
        ],
        "stream": False,
    }
    blocked_baseline = copy.deepcopy(blocked_data)
    cfg_blocked = base.model_dump()
    cfg_blocked["memory"]["token_budget"] = 5
    cfg_blocked["memory"]["chars_per_token"] = 4
    cfg_blocked["memory"]["token_budget_truncation_enabled"] = True
    blocked_config = RelayLMConfig.model_validate(cfg_blocked)
    forwarded_blocked, result_blocked = _maybe_apply_token_budget_truncation(
        config=blocked_config,
        payload=blocked_data,
    )
    require(result_blocked is not None and result_blocked.get("applied") is False, result_blocked)
    require(result_blocked.get("blocked_reason") == "preserved_messages_exceed_budget", result_blocked)
    require(forwarded_blocked["messages"] == blocked_baseline["messages"], forwarded_blocked)
    require(blocked_data == blocked_baseline, blocked_data)
    print("ok truncation blocked case remains request-neutral")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_data = enabled.model_dump()
        trace_path = Path(tmpdir) / "trace.jsonl"
        trace_data["trace"] = {"enabled": True, "path": str(trace_path)}
        trace_config = RelayLMConfig.model_validate(trace_data)
        diagnostics = RequestDiagnostics(
            request_id="req-trunc-apply",
            token_budget_truncation=result_apply,
        )
        written = trace_runtime_event(
            config=trace_config,
            diagnostics=diagnostics,
            message_count=len(forwarded_apply["messages"]),
            response_present=False,
        )
        require(written, "trace not written")
        metadata = json.loads(trace_path.read_text(encoding="utf-8"))["metadata"]
        require("token_budget_truncation" not in metadata, metadata)
        print("ok truncation apply diagnostics stay outside audit metadata")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
