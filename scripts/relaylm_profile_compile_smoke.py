from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    instruction_role = "sys" + "tem"
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": instruction_role, "content": "incoming instruction"},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
    }

    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    config = RelayLMConfig.model_validate(cfg)
    route = resolve_route(config, "relaylm-default")
    before = copy.deepcopy(payload)
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    require(payload == before, payload)
    context = compiled.payload["messages"][0]["content"]
    require("<relationship_anchor>" not in context, context)
    require("<stable_memory_summary>" not in context, context)
    require("<scene_state>" in context, context)
    require("room_anchor" not in context, context)
    print("ok optional persona blocks omitted when unset")

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "rel.md").write_text("Important relationship anchor.", encoding="utf-8")
        (p / "stable.md").write_text("Stable summary notes.", encoding="utf-8")
        (p / "scene_state.md").write_text("Scene mood is energetic.", encoding="utf-8")

        cfg2 = copy.deepcopy(cfg)
        char = cfg2["characters"]["default"]
        char["memory_seed_path"] = str(p / "missing-seed.yaml")
        char["relationship_anchor"] = str(p / "rel.md")
        char["stable_memory_summary"] = str(p / "stable.md")
        char["scene_state"] = str(p / "scene_state.md")
        config2 = RelayLMConfig.model_validate(cfg2)
        route2 = resolve_route(config2, "relaylm-default")
        compiled2 = compile_chat_payload_if_enabled(config=config2, route=route2, payload=payload)
        context2 = compiled2.payload["messages"][0]["content"]
        require("<relationship_anchor>" in context2, context2)
        require("<stable_memory_summary>" in context2, context2)
        require("<scene_state>" in context2, context2)
        require(context2.index("<relationship_anchor>") < context2.index("<stable_memory_summary>"), context2)
        require(context2.index("<stable_memory_summary>") < context2.index("<scene_state>"), context2)
        print("ok optional persona blocks compiled with stable/slow/dynamic order")

        cfg3 = copy.deepcopy(cfg)
        char3 = cfg3["characters"]["default"]
        char3["memory_seed_path"] = "examples/memory/default_memories.yaml"
        char3["scene_state"] = str(p / "scene_state.md")
        config3 = RelayLMConfig.model_validate(cfg3)
        route3 = resolve_route(config3, "relaylm-default")
        before3 = copy.deepcopy(payload)
        compiled3 = compile_chat_payload_if_enabled(config=config3, route=route3, payload=payload)
        require(payload == before3, payload)
        context3 = compiled3.payload["messages"][0]["content"]
        require("<retrieved_memory>" in context3, context3)
        require("<scene_state>" in context3, context3)
        require(context3.index("<retrieved_memory>") < context3.index("<scene_state>"), context3)
        print("ok scene_state with selected memory keeps slow-before-dynamic order")

        cfg4 = copy.deepcopy(cfg)
        char4 = cfg4["characters"]["default"]
        char4["scene_state"] = str(p / "scene_state.md")
        config4 = RelayLMConfig.model_validate(cfg4)
        route4 = resolve_route(config4, "relaylm-default")
        compiled4 = compile_chat_payload_if_enabled(config=config4, route=route4, payload=payload)
        context4 = compiled4.payload["messages"][0]["content"]
        require("Scene mood is energetic." in context4, context4)
        require("room_state" not in context4, context4)
        print("ok scene_state is the only scene file field")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
