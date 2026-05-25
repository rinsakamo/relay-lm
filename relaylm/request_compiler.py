"""Request payload compilation helpers for RelayLM MVP-2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import yaml

from relaylm.compile_gate import CompileApplyDecision, decide_compile_apply
from relaylm.compiler import (
    build_stable_prefix_hash_diagnostics,
    compile_profile_messages_with_system_fallback,
    summarize_context_blocks,
)
from relaylm.config import RelayLMConfig
from relaylm.memory_adapter import (
    build_memory_adapter_conflict_diagnostics,
    build_local_seed_memory_adapter_dry_run_from_selection,
    build_memory_adapter_readiness_check,
)
from relaylm.memory_candidate import MemoryBlockAssembly, MemorySelectionSummary
from relaylm.memory_context import MemoryConfigurationError, insert_memory_block
from relaylm.memory_selection import ConfiguredMemorySelection, build_configured_candidate_memory_selection
from relaylm.memory_token_dry_run import ConfiguredTokenMemoryDryRun, build_token_memory_dry_run_from_selected
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
    memory_source: str | None = None
    memory_selection_summary: MemorySelectionSummary | None = None
    memory_block_assembly: MemoryBlockAssembly | None = None
    memory_fallback_reason: str | None = None
    token_memory_dry_run: dict[str, Any] | None = None
    stable_prefix_hash: str | None = None
    stable_prefix_block_ids: list[str] | None = None
    memory_adapter_dry_run: dict[str, Any] | None = None
    memory_adapter_readiness: dict[str, Any] | None = None
    memory_adapter_conflicts: dict[str, Any] | None = None
    context_block_summary: dict[str, Any] | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "compiler_used": self.compiler_used,
            "memory_block_used": self.memory_block_used,
            "memory_source": self.memory_source,
            "memory_selection_summary": (
                self.memory_selection_summary.to_log_dict()
                if self.memory_selection_summary is not None
                else None
            ),
            "memory_block_assembly": (
                self.memory_block_assembly.to_log_dict()
                if self.memory_block_assembly is not None
                else None
            ),
            "memory_fallback_reason": self.memory_fallback_reason,
            "token_memory_dry_run": self.token_memory_dry_run,
            "stable_prefix_hash": self.stable_prefix_hash,
            "stable_prefix_block_ids": self.stable_prefix_block_ids,
            "memory_adapter_dry_run": self.memory_adapter_dry_run,
            "memory_adapter_readiness": self.memory_adapter_readiness,
            "memory_adapter_conflicts": self.memory_adapter_conflicts,
            "context_block_summary": self.context_block_summary,
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
            token_memory_dry_run=None,
        )

    profile_files = resolve_profile_files(config, route)
    profile_blocks = build_profile_blocks(profile_files)
    memory_selection, memory_fallback_reason = _resolve_memory_selection_best_effort(
        config=config,
        route=route,
    )
    memory_adapter_dry_run = build_local_seed_memory_adapter_dry_run_from_selection(
        route=route,
        memory_selection=memory_selection,
        memory_fallback_reason=memory_fallback_reason,
    ).to_log_dict()
    memory_adapter_readiness = build_memory_adapter_readiness_check(memory_adapter_dry_run).to_log_dict()
    memory_adapter_conflicts = build_memory_adapter_conflict_diagnostics(memory_adapter_dry_run).to_log_dict()
    token_dry_run = _resolve_token_memory_dry_run_best_effort(
        config=config,
        memory_selection=memory_selection,
    )
    memory_block = memory_selection.block
    blocks = insert_memory_block(
        profile_blocks=profile_blocks,
        memory_block=memory_block,
    )
    payload_dict["messages"] = compile_profile_messages_with_system_fallback(
        blocks,
        incoming_messages,
    )
    stable_prefix_hash, stable_prefix_block_ids = build_stable_prefix_hash_diagnostics(blocks)
    context_block_summary = summarize_context_blocks(blocks)
    return CompiledRequest(
        payload=payload_dict,
        plan=plan,
        decision=decision,
        compiler_used=True,
        memory_block_used=memory_block is not None,
        memory_source=memory_block.source if memory_block is not None else None,
        memory_selection_summary=memory_selection.summary,
        memory_block_assembly=memory_selection.assembly,
        memory_fallback_reason=memory_fallback_reason,
        token_memory_dry_run=token_dry_run.to_log_dict(),
        stable_prefix_hash=stable_prefix_hash,
        stable_prefix_block_ids=stable_prefix_block_ids,
        memory_adapter_dry_run=memory_adapter_dry_run,
        memory_adapter_readiness=memory_adapter_readiness,
        memory_adapter_conflicts=memory_adapter_conflicts,
        context_block_summary=context_block_summary,
    )


def _extract_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]


def _resolve_memory_selection_best_effort(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> tuple[ConfiguredMemorySelection, str | None]:
    try:
        return build_configured_candidate_memory_selection(config=config, route=route), None
    except MemoryConfigurationError:
        raise
    except (FileNotFoundError, OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        return ConfiguredMemorySelection(block=None, summary=None), f"memory_seed_load_error:{exc.__class__.__name__}"




def _resolve_token_memory_dry_run_best_effort(
    *,
    config: RelayLMConfig,
    memory_selection: ConfiguredMemorySelection,
) -> ConfiguredTokenMemoryDryRun:
    try:
        return build_token_memory_dry_run_from_selected(
            config=config,
            selected=memory_selection.selected,
            summary=memory_selection.summary,
        )
    except MemoryConfigurationError:
        raise
    except (FileNotFoundError, OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError):
        return ConfiguredTokenMemoryDryRun(summary=None, assembly=None)
