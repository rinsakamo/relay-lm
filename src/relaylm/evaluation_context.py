from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState


def _message(*, event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T00:00:{second:02d}+00:00",
    )


async def evaluate_working_context_budget_atomicity() -> EvaluationScenarioResult:
    old_user = _message(
        event_id="old-user",
        actor="user",
        content="古い質問です",
        second=0,
    )
    old_assistant = _message(
        event_id="old-assistant",
        actor="assistant",
        content="古い回答です",
        second=1,
    )
    new_user = _message(
        event_id="new-user",
        actor="user",
        content="新しい質問です",
        second=2,
    )
    new_assistant = _message(
        event_id="new-assistant",
        actor="assistant",
        content="新しい回答です",
        second=3,
    )
    current_user = _message(
        event_id="current-user",
        actor="user",
        content="今の質問です",
        second=4,
    )
    history = (old_user, old_assistant, new_user, new_assistant, current_user)
    identity = Identity("# Evaluation Character\nBe grounded.\n")

    event_window = compile_cognitive_input(
        identity=identity,
        state=CanonicalState(),
        current_event=current_user,
        recent_events=history,
        max_working_context_events=3,
        max_working_context_chars=1000,
    )
    newest_pair_chars = len(new_user.payload["content"]) + len(
        new_assistant.payload["content"]
    )
    char_budget = compile_cognitive_input(
        identity=identity,
        state=CanonicalState(),
        current_event=current_user,
        recent_events=history,
        max_working_context_events=6,
        max_working_context_chars=newest_pair_chars,
    )

    expected = [
        ("user", "新しい質問です", (new_user.id,)),
        ("assistant", "新しい回答です", (new_assistant.id,)),
    ]
    observed_event_window = [
        (item.actor, item.content, item.sources) for item in event_window.context
    ]
    observed_char_budget = [
        (item.actor, item.content, item.sources) for item in char_budget.context
    ]
    selected_sources = {
        source for item in event_window.context for source in item.sources
    }

    checks = (
        EvaluationCheck(
            check_id="event_window_drops_orphan_assistant",
            boundary="context_compiler",
            passed=observed_event_window == expected,
            expected="new-user,new-assistant",
            observed=",".join(str(actor) for actor, _, _ in observed_event_window)
            or "none",
        ),
        EvaluationCheck(
            check_id="character_budget_keeps_newest_exchange_atomic",
            boundary="context_compiler",
            passed=observed_char_budget == expected,
            expected="new-user,new-assistant",
            observed=",".join(str(actor) for actor, _, _ in observed_char_budget)
            or "none",
        ),
        EvaluationCheck(
            check_id="selected_context_preserves_exact_sources",
            boundary="event_provenance",
            passed=selected_sources == {new_user.id, new_assistant.id},
            expected="new-user,new-assistant",
            observed=",".join(sorted(selected_sources)) or "none",
        ),
        EvaluationCheck(
            check_id="current_input_not_duplicated_into_context",
            boundary="context_compiler",
            passed=current_user.id not in selected_sources
            and event_window.input.id == current_user.id
            and char_budget.input.id == current_user.id,
            expected=True,
            observed=current_user.id not in selected_sources,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="working_context_budget_atomicity",
        checks=checks,
        metrics={
            "event_window_context_count": len(event_window.context),
            "character_budget_context_count": len(char_budget.context),
            "selected_source_count": len(selected_sources),
        },
    )
