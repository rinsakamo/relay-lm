from __future__ import annotations

from dataclasses import dataclass

from relaylm.budget import BudgetPlan


@dataclass(frozen=True, slots=True)
class ContextCompilerBudgetControls:
    """Budget-owned envelope values expressed in Context Compiler parameter units."""

    max_state_records: int
    max_working_context_events: int
    max_working_context_chars: int


@dataclass(frozen=True, slots=True)
class RetrievalBudgetControls:
    """Budget-owned envelope values expressed in Retrieval selector parameter units."""

    memory_max_chunks: int
    memory_max_chars: int
    event_max_events: int
    event_max_chars: int


@dataclass(frozen=True, slots=True)
class KnowledgeBudgetControls:
    """Budget-owned envelope for deterministic whole-file package knowledge."""

    max_items: int
    max_chars: int


@dataclass(frozen=True, slots=True)
class BudgetOwnerControls:
    """Content-free translation from a BudgetPlan into existing owner controls.

    This structure carries only envelope limits. It does not execute a selector,
    rank semantic content, or add a Continuity pressure-selection contract.
    """

    context_compiler: ContextCompilerBudgetControls
    retrieval: RetrievalBudgetControls
    knowledge: KnowledgeBudgetControls


def owner_controls_for_budget_plan(plan: BudgetPlan) -> BudgetOwnerControls:
    """Translate current plan caps into the parameter units owned by each layer."""

    return BudgetOwnerControls(
        context_compiler=ContextCompilerBudgetControls(
            max_state_records=plan.canonical_state.max_items,
            max_working_context_events=plan.working_context.max_items,
            max_working_context_chars=plan.working_context.max_chars,
        ),
        retrieval=RetrievalBudgetControls(
            memory_max_chunks=plan.retrieved_memory.max_items,
            memory_max_chars=plan.retrieved_memory.max_chars,
            event_max_events=plan.event_evidence.max_items,
            event_max_chars=plan.event_evidence.max_chars,
        ),
        knowledge=KnowledgeBudgetControls(
            max_items=plan.package_knowledge.max_items,
            max_chars=plan.package_knowledge.max_chars,
        ),
    )
