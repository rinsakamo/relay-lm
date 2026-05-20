from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import compile_profile_messages, compile_profile_system_message
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

    system_message = compile_profile_system_message(blocks)
    require(system_message["role"] == "system", system_message)
    require(system_message["content"].startswith('<relaylm_context version="1">'), system_message["content"])
    require("<character_soul_anchor>" in system_message["content"], system_message["content"])
    require("<character_output_policy>" in system_message["content"], system_message["content"])
    print("ok compile profile system message")

    recent_messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    messages = compile_profile_messages(blocks, recent_messages=recent_messages)
    require(len(messages) == 3, messages)
    require(messages[0]["role"] == "system", messages)
    require(messages[1:] == recent_messages, messages)
    print("ok compile profile messages")

    require(messages[-1]["role"] == "assistant", messages)
    require(messages[-2]["role"] == "user", messages)
    print("ok recent messages preserved")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
