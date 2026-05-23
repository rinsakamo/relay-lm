from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.memory_token_dry_run import build_configured_token_memory_dry_run
from relaylm.routing import ResolvedRoute, resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _build_temp_seed(path: Path) -> None:
    records = [
        {"memory_id": "mem-a", "content": "aaaa", "importance": 3, "character_id": "default", "state": "active"},
        {"memory_id": "mem-b", "content": "bbbbbbbb", "importance": 2, "character_id": "default", "state": "active"},
        {"memory_id": "mem-c", "content": "cccccccccccc", "importance": 1, "character_id": "default", "state": "active"},
        {"memory_id": "mem-disabled", "content": "should not select", "importance": 10, "character_id": "default", "state": "disabled"},
    ]
    path.write_text(yaml.safe_dump({"memories": records}, sort_keys=False), encoding="utf-8")


def _route_without_character(route: ResolvedRoute) -> ResolvedRoute:
    return ResolvedRoute(
        route_model=route.route_model,
        backend_name=route.backend_name,
        backend=route.backend,
        backend_model=route.backend_model,
        character_id=None,
        mode_requested=route.mode_requested,
        mode_applied=route.mode_applied,
        cache_namespace=route.cache_namespace,
        memory_namespace=route.memory_namespace,
    )


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")

    with tempfile.TemporaryDirectory() as tmpdir:
        seed_path = Path(tmpdir) / "memory_seed.yaml"
        _build_temp_seed(seed_path)

        configured = config.model_copy(deep=True)
        configured.characters["default"].memory_seed_path = str(seed_path)
        configured.memory.token_budget = 30
        configured.memory.chars_per_token = 4

        dry_run = build_configured_token_memory_dry_run(config=configured, route=route)
        require(dry_run.summary is not None, dry_run)
        require(dry_run.assembly is not None, dry_run)
        require(dry_run.summary.selected_memory_ids == ["mem-a", "mem-b", "mem-c"], dry_run.summary)
        require(dry_run.summary.excluded_disabled_ids == ["mem-disabled"], dry_run.summary)
        require(dry_run.assembly.included_memory_ids == ["mem-a", "mem-b"], dry_run.assembly)
        require(dry_run.assembly.dropped_memory_ids == ["mem-c"], dry_run.assembly)
        require(dry_run.assembly.token_budget == 30, dry_run.assembly)
        require(dry_run.assembly.estimated_tokens <= 30, dry_run.assembly)
        print("ok configured token memory dry run")

        payload = dry_run.to_log_dict()
        require(isinstance(payload["summary"], dict), payload)
        require(isinstance(payload["assembly"], dict), payload)
        require(payload["summary"]["selected_memory_ids"] == ["mem-a", "mem-b", "mem-c"], payload)
        require(payload["assembly"]["included_memory_ids"] == ["mem-a", "mem-b"], payload)
        print("ok configured token memory dry run log payload")

        no_character = build_configured_token_memory_dry_run(
            config=configured,
            route=_route_without_character(route),
        )
        require(no_character.summary is None, no_character)
        require(no_character.assembly is None, no_character)
        print("ok configured token memory dry run no character")

        no_seed_config = configured.model_copy(deep=True)
        no_seed_config.characters["default"].memory_seed_path = None
        no_seed = build_configured_token_memory_dry_run(config=no_seed_config, route=route)
        require(no_seed.summary is None, no_seed)
        require(no_seed.assembly is None, no_seed)
        print("ok configured token memory dry run no seed")


    invalid_budget = config.model_dump()
    invalid_budget.setdefault("memory", {})["token_budget"] = 0
    try:
        RelayLMConfig.model_validate(invalid_budget)
    except Exception as exc:
        text = str(exc)
        require("token_budget" in text, text)
        require("greater than" in text or "gt" in text, text)
        print("ok invalid token_budget config rejected")
    else:
        raise AssertionError("expected token_budget validation error")

    invalid = config.model_dump()
    invalid.setdefault("memory", {})["chars_per_token"] = 0
    try:
        RelayLMConfig.model_validate(invalid)
    except Exception as exc:
        text = str(exc)
        require("chars_per_token" in text, text)
        require("greater than" in text or "gt" in text, text)
        print("ok invalid chars_per_token config rejected")
    else:
        raise AssertionError("expected chars_per_token validation error")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
