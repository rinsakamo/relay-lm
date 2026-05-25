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


def _build_config(*, scene_state_path: str | None = None) -> RelayLMConfig:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    char = cfg["characters"]["default"]
    char["memory_seed_path"] = "examples/memory/default_memories.yaml"
    if scene_state_path is not None:
        char["scene_state"] = scene_state_path
    return RelayLMConfig.model_validate(cfg)


def _compile(config: RelayLMConfig, payload: dict[str, object]):
    route = resolve_route(config, "relaylm-default")
    return compile_chat_payload_if_enabled(config=config, route=route, payload=payload)


def main() -> int:
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    before = copy.deepcopy(payload)

    config = _build_config()
    compiled = _compile(config, payload)

    diag = compiled.persona_source_budget_diagnostics
    require(diag is not None, compiled.to_log_dict())
    require(diag["budget_status"] in {"ok", "warning"}, diag)
    require("scene_state" in diag["source_budgets"], diag)
    require("scene_state" in diag["source_char_counts"], diag)
    require("scene_state" in diag["source_budget_ratios"], diag)
    require("<scene_state>" not in str(diag), diag)
    require(payload == before, payload)
    print("ok persona source budget diagnostics present")

    with tempfile.TemporaryDirectory() as tmpdir:
        scene_path = Path(tmpdir) / "SCENE_STATE.md"
        scene_path.write_text("X" * 1300, encoding="utf-8")
        config_over = _build_config(scene_state_path=str(scene_path))
        compiled_over = _compile(config_over, payload)
        diag_over = compiled_over.persona_source_budget_diagnostics
        require(diag_over is not None, compiled_over.to_log_dict())
        require("scene_state" in diag_over["over_budget_block_ids"], diag_over)
        require(diag_over["budget_status"] == "warning", diag_over)
        print("ok scene_state over budget flagged")

    cfg_pt = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg_pt["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    config_pt = RelayLMConfig.model_validate(cfg_pt)
    compiled_pt = _compile(config_pt, payload)
    require(compiled_pt.persona_source_budget_diagnostics is None, compiled_pt.to_log_dict())
    print("ok pass_through has no persona source budget diagnostics")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
