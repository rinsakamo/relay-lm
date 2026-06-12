from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import (
    append_incoming_system_prompt_block,
    compile_profile_messages_with_system_fallback,
    split_incoming_system_messages,
)
from relaylm.config import load_config
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    files = resolve_profile_files(config, route)
    blocks = build_profile_blocks(files)

    incoming_messages = [
        {"role": "system", "content": "Keep this session concise."},
        {"role": "developer", "content": "Ask one question at a time."},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    instruction_messages, recent_messages = split_incoming_system_messages(incoming_messages)
    require(len(instruction_messages) == 2, instruction_messages)
    require([message["role"] for message in instruction_messages] == ["system", "developer"], instruction_messages)
    require(len(recent_messages) == 2, recent_messages)
    require(recent_messages[0]["role"] == "user", recent_messages)
    require(all(message["role"] not in {"system", "developer"} for message in recent_messages), recent_messages)
    print("ok split incoming system/developer messages")

    blocks_with_fallback = append_incoming_system_prompt_block(blocks, instruction_messages)
    require(len(blocks_with_fallback) == len(blocks) + 1, blocks_with_fallback)
    require(blocks_with_fallback[-1].block_id == "incoming_system_prompt", blocks_with_fallback[-1])
    require(blocks_with_fallback[-1].include_in_prefix_cache_target is False, blocks_with_fallback[-1])
    require(blocks_with_fallback[-1].source == "incoming/messages/system_or_developer", blocks_with_fallback[-1])
    print("ok append incoming instruction block")

    messages = compile_profile_messages_with_system_fallback(blocks, incoming_messages)
    require(messages[0]["role"] == "system", messages)
    require("<incoming_system_prompt>" in messages[0]["content"], messages[0]["content"])
    require("Keep this session concise." in messages[0]["content"], messages[0]["content"])
    require("Ask one question at a time." in messages[0]["content"], messages[0]["content"])
    require(messages[1:] == recent_messages, messages)
    require(all(message["role"] != "developer" for message in messages[1:]), messages)
    print("ok compile messages with system/developer fallback")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
