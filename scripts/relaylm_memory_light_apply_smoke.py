from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    base_payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "Keep this session concise."},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
    }

    config = load_config(REPO_ROOT / "config.example.yaml")
    pass_through_route = resolve_route(config, "relaylm-default")
    pass_through_compiled = compile_chat_payload_if_enabled(
        config=config,
        route=pass_through_route,
        payload=base_payload,
    )
    require(pass_through_compiled.compiler_used is False, pass_through_compiled)
    require(pass_through_compiled.memory_block_used is False, pass_through_compiled)
    require(pass_through_compiled.decision.should_apply is False, pass_through_compiled.decision)
    require(pass_through_compiled.payload["messages"] == base_payload["messages"], pass_through_compiled.payload)
    print("ok pass-through payload unchanged")

    memory_light_config = config.model_copy(deep=True)
    memory_light_config.model_routes["relaylm-default"].mode = "memory_light"
    memory_light_route = resolve_route(memory_light_config, "relaylm-default")
    memory_light_compiled = compile_chat_payload_if_enabled(
        config=memory_light_config,
        route=memory_light_route,
        payload=base_payload,
    )
    require(memory_light_compiled.compiler_used is True, memory_light_compiled)
    require(memory_light_compiled.memory_block_used is True, memory_light_compiled)
    require(memory_light_compiled.decision.should_apply is True, memory_light_compiled.decision)
    compiled_messages = memory_light_compiled.payload["messages"]
    require(compiled_messages[0]["role"] == "system", compiled_messages)
    compiled_context = compiled_messages[0]["content"]
    require("<relaylm_context" in compiled_context, compiled_context)
    require("<character_soul_anchor>" in compiled_context, compiled_context)
    require("<retrieved_memory>" in compiled_context, compiled_context)
    require("default-relaylm-project" in compiled_context, compiled_context)
    require("score=" in compiled_context, compiled_context)
    require("state=active" in compiled_context, compiled_context)
    require("<incoming_system_prompt>" in compiled_context, compiled_context)
    require(compiled_context.index("<retrieved_memory>") < compiled_context.index("<incoming_system_prompt>"), compiled_context)
    require(compiled_messages[1:] == [{"role": "user", "content": "hello"}], compiled_messages)
    print("ok memory-light payload compiled")
    print("ok candidate memory block applied")

    log_payload = memory_light_compiled.to_log_dict()
    require(log_payload["compiler_used"] is True, log_payload)
    require(log_payload["memory_block_used"] is True, log_payload)
    require(log_payload["decision"]["reason"] == "memory_light_compile_enabled", log_payload)
    print("ok compiled request log payload")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
