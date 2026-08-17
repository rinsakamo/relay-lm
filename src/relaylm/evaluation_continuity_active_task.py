from __future__ import annotations

import json
from typing import Any

from relaylm.context import compile_cognitive_input, compile_cognitive_input_with_diagnostics
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState


def _current() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What should we do next?"},
        event_id="current-event",
        timestamp="2026-08-17T13:42:00+00:00",
    )


def _item(
    *,
    item_id: str,
    kind: str,
    key: str,
    value: Any,
    sources: tuple[str, ...],
    epistemic_role: str,
) -> ContinuityItem:
    return ContinuityItem(
        item_id=item_id,
        kind=kind,  # type: ignore[arg-type]
        key=key,
        value=value,
        sources=sources,
        epistemic_role=epistemic_role,  # type: ignore[arg-type]
        accepted_revision=2,
        expires_revision=5,
    )


def _decoded(content: str) -> dict[str, Any]:
    value = json.loads(content)
    if not isinstance(value, dict):
        raise AssertionError("projected Continuity content must be a JSON object")
    return value


async def evaluate_continuity_active_task_retention() -> EvaluationScenarioResult:
    identity = Identity("# Evaluation Character\nBe grounded.")
    state = CanonicalState()
    current = _current()

    active_task = _item(
        item_id="continuity-task",
        kind="active_task",
        key="task.current",
        value={"task": "send the blue draft", "status": "active"},
        sources=("event-user-1", "event-assistant-1"),
        epistemic_role="assistant_commitment",
    )
    task_context = ContinuityContext(
        max_items=3,
        revision=2,
        items=(active_task,),
    )
    zero_budget = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=task_context,
        max_working_context_events=0,
        max_working_context_chars=0,
    )
    task_payload = _decoded(zero_budget.context[0].content)["continuity"]

    referent = _item(
        item_id="continuity-referent",
        kind="referent",
        key="draft.current",
        value="the blue draft",
        sources=("event-user-1",),
        epistemic_role="user_assertion",
    )
    unresolved = _item(
        item_id="continuity-unresolved",
        kind="unresolved",
        key="question.address",
        value="Which address?",
        sources=("event-assistant-2",),
        epistemic_role="assistant_inference",
    )
    ordered_context = ContinuityContext(
        max_items=5,
        revision=2,
        items=(referent, active_task, unresolved),
    )
    ordered = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=ordered_context,
        max_working_context_events=0,
        max_working_context_chars=0,
    )
    ordered_kinds = tuple(
        _decoded(item.content)["continuity"]["kind"] for item in ordered.context
    )

    diagnostic = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=task_context,
        max_working_context_events=0,
        max_working_context_chars=0,
    )
    diagnostic_layers = tuple(item.layer for item in diagnostic.diagnostics)

    checks = (
        EvaluationCheck(
            check_id="active_task_survives_zero_recent_budget",
            boundary="context_compiler",
            passed=(
                len(zero_budget.context) == 1
                and task_payload["kind"] == "active_task"
                and task_payload["key"] == "task.current"
                and task_payload["value"]
                == {"status": "active", "task": "send the blue draft"}
            ),
            expected="active_task",
            observed=task_payload["kind"],
        ),
        EvaluationCheck(
            check_id="active_task_preserves_sources_role_and_actor_boundary",
            boundary="context_compiler",
            passed=(
                zero_budget.context[0].sources
                == ("event-user-1", "event-assistant-1")
                and task_payload["epistemic_role"] == "assistant_commitment"
                and zero_budget.context[0].actor is None
            ),
            expected=True,
            observed=zero_budget.context[0].actor is None,
        ),
        EvaluationCheck(
            check_id="initial_continuity_kinds_preserve_accepted_order",
            boundary="context_compiler",
            passed=ordered_kinds == ("referent", "active_task", "unresolved"),
            expected="referent,active_task,unresolved",
            observed=",".join(ordered_kinds),
        ),
        EvaluationCheck(
            check_id="active_task_diagnostics_preserve_four_layer_authority",
            boundary="context_compiler",
            passed=(
                diagnostic.cognitive_input.context == zero_budget.context
                and diagnostic_layers
                == (
                    "canonical_state",
                    "working_context",
                    "retrieved_memory",
                    "event_evidence",
                )
            ),
            expected="canonical_state,working_context,retrieved_memory,event_evidence",
            observed=",".join(diagnostic_layers),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="continuity_active_task_retention",
        checks=checks,
        metrics={
            "active_task_input_count": len(task_context.items),
            "zero_budget_projected_count": len(zero_budget.context),
            "ordered_continuity_count": len(ordered.context),
            "diagnostic_layer_count": len(diagnostic_layers),
        },
    )
