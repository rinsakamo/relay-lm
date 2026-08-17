from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input_with_diagnostics
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
        timestamp=f"2026-08-17T09:20:{second:02d}+00:00",
    )


async def evaluate_working_context_budget_diagnostics() -> EvaluationScenarioResult:
    old_user = _message(
        event_id="old-user-secret",
        actor="user",
        content="old question secret",
        second=0,
    )
    old_assistant = _message(
        event_id="old-assistant-secret",
        actor="assistant",
        content="old answer secret",
        second=1,
    )
    new_user = _message(
        event_id="new-user-secret",
        actor="user",
        content="new question secret",
        second=2,
    )
    new_assistant = _message(
        event_id="new-assistant-secret",
        actor="assistant",
        content="new answer secret",
        second=3,
    )
    current = _message(
        event_id="current-secret",
        actor="user",
        content="current question secret",
        second=4,
    )
    history = (old_user, old_assistant, new_user, new_assistant, current)
    identity = Identity("# Evaluation Character\nBe grounded.\n")

    event_window = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=CanonicalState(),
        current_event=current,
        recent_events=history,
        max_working_context_events=3,
        max_working_context_chars=1000,
    )
    newest_pair_chars = len(new_user.payload["content"]) + len(
        new_assistant.payload["content"]
    )
    character_budget = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=CanonicalState(),
        current_event=current,
        recent_events=history,
        max_working_context_events=6,
        max_working_context_chars=newest_pair_chars,
    )
    zero_character_budget = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=CanonicalState(),
        current_event=current,
        recent_events=history,
        max_working_context_events=6,
        max_working_context_chars=0,
    )

    window_diagnostic = event_window.diagnostics[1]
    character_diagnostic = character_budget.diagnostics[1]
    zero_diagnostic = zero_character_budget.diagnostics[1]
    selected_actors = tuple(item.actor for item in event_window.cognitive_input.context)
    serialized = json.dumps(
        [
            asdict(window_diagnostic),
            asdict(character_diagnostic),
            asdict(zero_diagnostic),
        ],
        ensure_ascii=False,
    )
    forbidden = (
        "old-user-secret",
        "old-assistant-secret",
        "new-user-secret",
        "new-assistant-secret",
        "current-secret",
        "old question secret",
        "new question secret",
        "current question secret",
    )

    checks = (
        EvaluationCheck(
            check_id="event_window_and_orphan_reasons_are_distinct",
            boundary="diagnostics",
            passed=window_diagnostic.eligible_count == 4
            and window_diagnostic.selected_count == 2
            and window_diagnostic.evicted_event_window_count == 1
            and window_diagnostic.evicted_orphan_assistant_count == 1
            and window_diagnostic.evicted_character_budget_count == 0,
            expected=True,
            observed=window_diagnostic.evicted_event_window_count == 1
            and window_diagnostic.evicted_orphan_assistant_count == 1,
        ),
        EvaluationCheck(
            check_id="character_budget_eviction_is_counted_separately",
            boundary="diagnostics",
            passed=character_diagnostic.eligible_count == 4
            and character_diagnostic.selected_count == 2
            and character_diagnostic.evicted_event_window_count == 0
            and character_diagnostic.evicted_orphan_assistant_count == 0
            and character_diagnostic.evicted_character_budget_count == 2
            and character_diagnostic.character_budget_used == newest_pair_chars,
            expected=2,
            observed=character_diagnostic.evicted_character_budget_count,
        ),
        EvaluationCheck(
            check_id="zero_character_budget_is_attributed_to_character_budget",
            boundary="diagnostics",
            passed=zero_diagnostic.mode == "zero_budget"
            and zero_diagnostic.selected_count == 0
            and zero_diagnostic.evicted_event_window_count == 0
            and zero_diagnostic.evicted_orphan_assistant_count == 0
            and zero_diagnostic.evicted_character_budget_count == 4,
            expected=4,
            observed=zero_diagnostic.evicted_character_budget_count,
        ),
        EvaluationCheck(
            check_id="diagnostics_match_existing_atomic_residency",
            boundary="context_compiler",
            passed=selected_actors == ("user", "assistant")
            and len(character_budget.cognitive_input.context) == 2
            and zero_character_budget.cognitive_input.context == (),
            expected="user,assistant",
            observed=",".join(selected_actors) or "none",
        ),
        EvaluationCheck(
            check_id="working_context_diagnostics_do_not_expose_dialogue_payload",
            boundary="diagnostics",
            passed=all(value not in serialized for value in forbidden),
            expected=True,
            observed=all(value not in serialized for value in forbidden),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="working_context_budget_diagnostics",
        checks=checks,
        metrics={
            "event_window_evicted_count": window_diagnostic.evicted_event_window_count,
            "orphan_assistant_evicted_count": window_diagnostic.evicted_orphan_assistant_count,
            "character_budget_evicted_count": character_diagnostic.evicted_character_budget_count,
            "zero_character_budget_evicted_count": zero_diagnostic.evicted_character_budget_count,
        },
    )
