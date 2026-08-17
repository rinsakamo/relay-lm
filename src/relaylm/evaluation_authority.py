from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateCandidate
from relaylm.validation import apply_state_candidates


async def evaluate_assistant_self_certification_prevention() -> EvaluationScenarioResult:
    prior_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "最近どう？"},
        event_id="prior-user",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    prior_assistant = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "あなたは北海道に住んでいる"},
        event_id="prior-assistant",
        timestamp="2026-08-17T00:00:01+00:00",
    )
    current_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "それ、私が言ったことだっけ？"},
        event_id="current-user",
        timestamp="2026-08-17T00:00:02+00:00",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded.\n"),
        state=CanonicalState(),
        current_event=current_user,
        recent_events=(prior_user, prior_assistant, current_user),
    )
    assistant_context = [
        item for item in compiled.context if item.actor == "assistant"
    ]

    candidate = StateCandidate.set(
        state_class="user.fact",
        key="residence_location",
        value="Hokkaido",
        sources=(prior_assistant.id,),
    )
    validation = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={
            prior_user.id: prior_user,
            prior_assistant.id: prior_assistant,
            current_user.id: current_user,
        },
    )
    rejected = [
        decision for decision in validation.decisions if decision.status == "rejected"
    ]

    checks = (
        EvaluationCheck(
            check_id="assistant_context_retains_actor_and_source",
            boundary="context_compiler",
            passed=len(assistant_context) == 1
            and assistant_context[0].content == "あなたは北海道に住んでいる"
            and assistant_context[0].sources == (prior_assistant.id,),
            expected="assistant/prior-assistant",
            observed=(
                f"{assistant_context[0].actor}/{assistant_context[0].sources[0]}"
                if len(assistant_context) == 1 and assistant_context[0].sources
                else "missing"
            ),
        ),
        EvaluationCheck(
            check_id="assistant_only_user_state_is_rejected",
            boundary="validator",
            passed=len(rejected) == 1
            and rejected[0].reason == "user_state_requires_user_source",
            expected="user_state_requires_user_source",
            observed=(rejected[0].reason if rejected else "not_rejected"),
        ),
        EvaluationCheck(
            check_id="rejected_self_certification_does_not_enter_state",
            boundary="canonical_state",
            passed=validation.state.states == (),
            expected=0,
            observed=len(validation.state.states),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="assistant_self_certification_prevention",
        checks=checks,
        metrics={
            "working_context_count": len(compiled.context),
            "rejected_candidate_count": len(rejected),
            "accepted_state_count": len(validation.state.states),
        },
    )
