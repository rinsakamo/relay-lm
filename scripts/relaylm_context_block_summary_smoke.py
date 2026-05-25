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
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "incoming system"},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
    }
    before = copy.deepcopy(payload)

    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "rel.md").write_text("relationship anchor content", encoding="utf-8")
        (p / "slow.md").write_text("stable memory summary content", encoding="utf-8")
        (p / "scene.md").write_text("scene state content", encoding="utf-8")

        char = cfg["characters"]["default"]
        char["memory_seed_path"] = "examples/memory/default_memories.yaml"
        char["relationship_anchor"] = str(p / "rel.md")
        char["stable_memory_summary"] = str(p / "slow.md")
        char["scene_state"] = str(p / "scene.md")

        config = RelayLMConfig.model_validate(cfg)
        route = resolve_route(config, "relaylm-default")
        compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)

        summary = compiled.context_block_summary
        require(summary is not None, compiled.to_log_dict())
        require(summary["scene_state_present"] is True, summary)
        require("scene_state" in summary["dynamic_block_ids"], summary)
        require("scene_state" not in summary["prefix_cache_target_block_ids"], summary)
        require("relationship_anchor" in summary["prefix_cache_target_block_ids"], summary)
        require("stable_memory_summary" not in summary["prefix_cache_target_block_ids"], summary)
        require(summary["retrieved_memory_present"] is True, summary)
        require("scene state content" not in str(summary), summary)
        require(payload == before, payload)
        print("ok context block summary diagnostics")

        scene_idx = summary["block_ids"].index("scene_state")
        rel_idx = summary["block_ids"].index("relationship_anchor")
        require(rel_idx < scene_idx, summary)
        print("ok scene_state dynamic and relationship stable")

    cfg2 = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg2["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    config2 = RelayLMConfig.model_validate(cfg2)
    route2 = resolve_route(config2, "relaylm-default")
    compiled2 = compile_chat_payload_if_enabled(config=config2, route=route2, payload=payload)
    require(compiled2.context_block_summary is None, compiled2.to_log_dict())
    print("ok pass_through has no context block summary")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
