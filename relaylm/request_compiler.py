"""Request payload compilation helpers for RelayLM MVP-2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import yaml

from relaylm.compile_gate import CompileApplyDecision, decide_compile_apply
from relaylm.compiler import compile_profile_messages_with_system_fallback
from relaylm.config import RelayLMConfig
from relaylm.memory_context import (
    MemoryConfigurationError,
    insert_memory_block,
    resolve_seed_memory_block,
)
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.profile_plan import ProfileCompilePlan, build_profile_compile_plan
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class CompiledRequest:
    payload: dict[str, Any]
    plan: ProfileCompilePlan
    decision: CompileApplyDecision
    compiler_used: bool
    memory_block_used: bool = False
    memory_fallback_reason: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "compiler_used": self.compiler_used,
            "memory_block_used": self.memory_block_used,
            "memory_fallback_reason": self.memory_fallback_reason,
            "plan": self.plan.to_log_dict(),
            "decision": self.decision.to_log_dict(),
        }


def compile_chat_payload_if_enabled(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    payload: Mapping[str, Any],
) -> CompiledRequest:
    """Compile chat payload messages only when the route mode gate allows it."""

    incoming_messages = _extract_messages(payload)
    plan = build_profile_compile_plan(
        config=config,
        route=route,
        incoming_messages=incoming_messages,
    )
    decision = decide_compile_apply(mode_applied=route.mode_applied, plan=plan)

    payload_dict = dict(payload)
    if not decision.should_apply:
        return CompiledRequest(
            payload=payload_dict,
            plan=plan,
            decision=decision,
            compiler_used=False,
            memory_block_used=False,
        )

    profile_files = resolve_profile_files(config, route)
    profile_blocks = build_profile_blocks(profile_files)
    memory_block, memory_fallback_reason = _resolve_memory_block_best_effort(
        config=config,
        route=route,
    )
    blocks = insert_memory_block(
        profile_blocks=profile_blocks,
        memory_block=memory_block,
    )
    payload_dict["messages"] = compile_profile_messages_with_system_fallback(
        blocks,
        incoming_messages,
    )
    return CompiledRequest(
        payload=payload_dict,
        plan=plan,
        decision=decision,
        compiler_used=True,
        memory_block_used=memory_block is not None,
        memory_fallback_reason=memory_fallback_reason,
    )


def _extract_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]


def _resolve_memory_block_best_effort(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> tuple[Any | None, str | None]:
    try:
        return resolve_seed_memory_block(config, route), None
    except MemoryConfigurationError:
        raise
    except (FileNotFoundError, OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        return None, f"memory_seed_load_error:{exc.__class__.__name__}"
