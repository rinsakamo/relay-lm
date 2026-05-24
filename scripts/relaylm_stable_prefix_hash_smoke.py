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


def _compile(cfg: dict, payload: dict) -> object:
    config = RelayLMConfig.model_validate(cfg)
    route = resolve_route(config, "relaylm-default")
    return compile_chat_payload_if_enabled(config=config, route=route, payload=payload)


def main() -> int:
    base_cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "incoming system a"},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
    }
    base_cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "rel-a.md").write_text("Relationship A", encoding="utf-8")
        (p / "rel-b.md").write_text("Relationship B", encoding="utf-8")
        (p / "stable-a.md").write_text("Stable A", encoding="utf-8")
        (p / "stable-b.md").write_text("Stable B", encoding="utf-8")
        (p / "room-a.md").write_text("Room A", encoding="utf-8")
        (p / "room-b.md").write_text("Room B", encoding="utf-8")

        cfg = copy.deepcopy(base_cfg)
        ch = cfg["characters"]["default"]
        ch["relationship_anchor"] = str(p / "rel-a.md")
        ch["stable_memory_summary"] = str(p / "stable-a.md")
        ch["room_state"] = str(p / "room-a.md")

        before = copy.deepcopy(payload)
        c1 = _compile(cfg, payload)
        require(payload == before, payload)
        require(c1.stable_prefix_hash is not None, c1)
        require(isinstance(c1.stable_prefix_block_ids, list), c1)

        c2 = _compile(cfg, payload)
        require(c1.stable_prefix_hash == c2.stable_prefix_hash, (c1, c2))
        print("ok stable prefix hash consistent for same stable blocks")

        cfg_room = copy.deepcopy(cfg)
        cfg_room["characters"]["default"]["room_state"] = str(p / "room-b.md")
        c_room = _compile(cfg_room, payload)
        require(c1.stable_prefix_hash == c_room.stable_prefix_hash, (c1, c_room))
        print("ok room_state change does not change stable prefix hash")

        payload_sys = copy.deepcopy(payload)
        payload_sys["messages"][0]["content"] = "incoming system b"
        c_sys = _compile(cfg, payload_sys)
        require(c1.stable_prefix_hash == c_sys.stable_prefix_hash, (c1, c_sys))
        print("ok incoming system prompt change does not change stable prefix hash")

        cfg_stable = copy.deepcopy(cfg)
        cfg_stable["characters"]["default"]["stable_memory_summary"] = str(p / "stable-b.md")
        c_stable = _compile(cfg_stable, payload)
        require(c1.stable_prefix_hash == c_stable.stable_prefix_hash, (c1, c_stable))
        print("ok stable_memory_summary change does not change stable prefix hash")

        cfg_rel = copy.deepcopy(cfg)
        cfg_rel["characters"]["default"]["relationship_anchor"] = str(p / "rel-b.md")
        c_rel = _compile(cfg_rel, payload)
        require(c1.stable_prefix_hash != c_rel.stable_prefix_hash, (c1, c_rel))
        print("ok relationship_anchor change updates stable prefix hash")

    pass_cfg = copy.deepcopy(base_cfg)
    pass_cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    c_pass = _compile(pass_cfg, payload)
    require(c_pass.stable_prefix_hash is None, c_pass)
    require(c_pass.stable_prefix_block_ids is None, c_pass)
    print("ok pass-through keeps stable prefix hash unset")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
