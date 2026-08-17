from __future__ import annotations

import json
from typing import Any

from relaylm.context import compile_cognitive_input, compile_cognitive_input_with_diagnostics
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState


def _event(event_id: str, *, actor: str, content: str, minute: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T13:{minute:02d}:00+00:00",
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
        accepted_revision=1,
        expires_revision=4,
    )


def _decoded(content: str) -> dict[str, Any]:
    value = json.loads(content)
    if not isinstance(value, dict):
        raise AssertionError("projected Continuity content must be a JSON object")
    return value


async def evaluate_continuity_context_retention() -> EvaluationScenarioResult:
    identity = Identity("# Evaluation Character\nBe grounded.")
    state = CanonicalState()
    current = _event(
        "current-event",
        actor="user",
        content="What were we referring to?",
        minute=24,
    )
    referent = _item(
        item_id="continuity-referent",
        kind="referent",
        key="draft.current",
        value={"entity": "the blue draft"},
        sources=("event-user-1",),
        epistemic_role="user_assertion",
    )
    unresolved = _item(
        item_id="continuity-unresolved",
        kind="unresolved",
        key="question.delivery",
        value={"question": "Which address should receive it?"},
        sources=("event-assistant-1",),
        epistemic_role="assistant_inference",
    )
    accepted = ContinuityContext(
        max_items=4,
        revision=1,
        items=(referent, unresolved),
    )

    zero_budget = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=accepted,
        max_working_context_events=0,
        max_working_context_chars=0,
    )
    zero_decoded = tuple(_decoded(item.content) for item in zero_budget.context)

    recent_user = _event(
        "recent-user",
        actor="user",
        content="I will send it tonight.",
        minute=22,
    )
    recent_assistant = _event(
        "recent-assistant",
        actor="assistant",
        content="Okay, tonight.",
        minute=23,
    )
    ordered = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current,
        recent_events=(recent_user, recent_assistant),
        continuity_context=accepted,
    )

    diagnostic = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=accepted,
        max_working_context_events=0,
        max_working_context_chars=0,
    )
    diagnostic_layers = tuple(item.layer for item in diagnostic.diagnostics)

    empty = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current,
        continuity_context=ContinuityContext(max_items=1),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    expected_kinds = ("referent", "unresolved")
    observed_kinds = tuple(
        decoded["continuity"]["kind"] for decoded in zero_decoded
    )
    observed_roles = tuple(
        decoded["continuity"]["epistemic_role"] for decoded in zero_decoded
    )
    recent_projection = ordered.context[len(accepted.items) :]

    checks = (
        EvaluationCheck(
            check_id="referent_unresolved_survive_zero_recent_budget",
            boundary="context_compiler",
            passed=(
                len(zero_budget.context) == 2
                and observed_kinds == expected_kinds
            ),
            expected="referent,unresolved",
            observed=",".join(observed_kinds),
        ),
        EvaluationCheck(
            check_id="continuity_preserves_sources_roles_and_actor_boundary",
            boundary="context_compiler",
            passed=(
                tuple(item.sources for item in zero_budget.context)
                == (("event-user-1",), ("event-assistant-1",))
                and observed_roles == ("user_assertion", "assistant_inference")
                and tuple(item.actor for item in zero_budget.context) == (None, None)
            ),
            expected=True,
            observed=(
                tuple(item.actor for item in zero_budget.context) == (None, None)
            ),
        ),
        EvaluationCheck(
            check_id="continuity_precedes_recent_working_context_without_reordering",
            boundary="context_compiler",
            passed=(
                tuple(
                    _decoded(item.content)["continuity"]["kind"]
                    for item in ordered.context[:2]
                )
                == expected_kinds
                and tuple(item.content for item in recent_projection)
                == ("I will send it tonight.", "Okay, tonight.")
                and tuple(item.sources for item in recent_projection)
                == (("recent-user",), ("recent-assistant",))
            ),
            expected=True,
            observed=tuple(item.content for item in recent_projection)
            == ("I will send it tonight.", "Okay, tonight."),
        ),
        EvaluationCheck(
            check_id="diagnostic_projection_preserves_four_layer_authority",
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
        EvaluationCheck(
            check_id="empty_continuity_preserves_empty_zero_budget_context",
            boundary="context_compiler",
            passed=empty.context == (),
            expected=0,
            observed=len(empty.context),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="continuity_context_retention",
        checks=checks,
        metrics={
            "accepted_continuity_input_count": len(accepted.items),
            "zero_budget_projected_count": len(zero_budget.context),
            "recent_working_context_count": len(recent_projection),
            "diagnostic_layer_count": len(diagnostic_layers),
            "empty_projection_count": len(empty.context),
        },
    )
