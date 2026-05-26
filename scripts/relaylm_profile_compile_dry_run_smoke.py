from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    incoming_messages = [
        {"role": "system", "content": "Keep this session concise."},
        {"role": "user", "content": "hello"},
    ]

    plan = build_profile_compile_plan(
        config=config,
        route=route,
        incoming_messages=incoming_messages,
    )
    require(plan.enabled is True, plan)
    require(plan.route_model == "relaylm-default", plan)
    require(plan.character_id == "default", plan)
    require(plan.compiled_block_count == 5, plan)
    require(plan.compiled_message_count == 2, plan)
    require(plan.incoming_message_count == 2, plan)
    require(plan.incoming_system_message_count == 1, plan)
    require(plan.fallback_reason is None, plan)
    print("ok profile compile dry-run plan")

    payload = plan.to_log_dict()
    require(payload["enabled"] is True, payload)
    require(payload["compiled_block_count"] == 5, payload)
    require(payload["compiled_message_count"] == 2, payload)
    print("ok profile compile plan log payload")


    abstract_config = config.model_copy(deep=True)
    base_route = abstract_config.model_routes["relaylm-default"]
    abstract_config.model_routes["relaylm-companion"] = base_route.model_copy(update={
        "character_id": "companion",
        "memory_namespace": "character/companion",
        "cache_namespace": "character/companion",
    })
    abstract_config.model_routes["relaylm-work-assistant"] = base_route.model_copy(update={
        "character_id": "work_assistant",
        "memory_namespace": "character/work-assistant",
        "cache_namespace": "character/work-assistant",
    })
    abstract_config.model_routes["relaylm-code-reviewer"] = base_route.model_copy(update={
        "character_id": "code_reviewer",
        "memory_namespace": "character/code-reviewer",
        "cache_namespace": "character/code-reviewer",
    })

    for cid, soul_path, policy_path, seed_path in [
        ("companion", "examples/profiles/companion/SOUL.md", "examples/profiles/companion/OUTPUT_POLICY.md", "examples/memory/companion_memories.yaml"),
        ("work_assistant", "examples/profiles/work_assistant/SOUL.md", "examples/profiles/work_assistant/OUTPUT_POLICY.md", "examples/memory/work_assistant_memories.yaml"),
        ("code_reviewer", "examples/profiles/code_reviewer/SOUL.md", "examples/profiles/code_reviewer/OUTPUT_POLICY.md", "examples/memory/code_reviewer_memories.yaml"),
    ]:
        base = abstract_config.characters["default"].model_copy(deep=True)
        base.soul = soul_path
        base.output_policy = policy_path
        base.memory_seed_path = seed_path
        abstract_config.characters[cid] = base

    for route_model, expected_character_id in [
        ("relaylm-companion", "companion"),
        ("relaylm-work-assistant", "work_assistant"),
        ("relaylm-code-reviewer", "code_reviewer"),
    ]:
        abstract_route = resolve_route(abstract_config, route_model)
        abstract_plan = build_profile_compile_plan(
            config=abstract_config,
            route=abstract_route,
            incoming_messages=incoming_messages,
        )
        require(abstract_plan.enabled is True, abstract_plan)
        require(abstract_plan.character_id == expected_character_id, abstract_plan)
        require(abstract_plan.compiled_block_count == 5, abstract_plan)
        require(abstract_plan.compiled_message_count == 2, abstract_plan)

        character_cfg = abstract_config.characters[expected_character_id]
        require(Path(character_cfg.soul).exists(), character_cfg.soul)
        require(Path(character_cfg.output_policy).exists(), character_cfg.output_policy)
        require(character_cfg.memory_seed_path is not None and Path(character_cfg.memory_seed_path).exists(), str(character_cfg.memory_seed_path))

    print("ok openwebui abstract profile compile dry-run")

    broken_config = config.model_copy(deep=True)
    broken_config.characters["default"].soul = "missing/SOUL.md"
    fallback_plan = build_profile_compile_plan(
        config=broken_config,
        route=route,
        incoming_messages=incoming_messages,
    )
    require(fallback_plan.enabled is False, fallback_plan)
    require(fallback_plan.fallback_reason == "FileNotFoundError", fallback_plan)
    print("ok profile compile fallback plan")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
