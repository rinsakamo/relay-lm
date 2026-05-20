"""Request payload compilation helpers for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from relaylm.compile_gate import CompileApplyDecision, decide_compile_apply
from relaylm.compiler import compile_profile_messages_with_system_fallback
from relaylm.config import RelayLMConfig
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.profile_plan import ProfileCompilePlan, build_profile_compile_plan
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class CompiledRequest:
    payload: dict[str, Any]
    plan: ProfileCompilePlan
    decision: CompileApplyDecision
    compiler_used: bool

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "compiler_used": self.compiler_used,
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
        )

    profile_files = resolve_profile_files(config, route)
    blocks = build_profile_blocks(profile_files)
    payload_dict["messages"] = compile_profile_messages_with_system_fallback(
        blocks,
        incoming_messages,
    )
    return CompiledRequest(
        payload=payload_dict,
        plan=plan,
        decision=decision,
        compiler_used=True,
    )


def _extract_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]
