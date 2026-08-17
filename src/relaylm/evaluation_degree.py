from __future__ import annotations

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.validation import apply_state_candidates


async def evaluate_degree_hint_integrity() -> EvaluationScenarioResult:
    existing = StateRecord(
        state_id="coffee-existing",
        state_class="user.preference",
        key="coffee",
        value={"semantic": "likes", "degree_hint": 0.9},
        sources=("older-user-event",),
    )
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "コーヒーは前ほどじゃないけど、まだ好き"},
        event_id="current-degree",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    candidates = (
        StateCandidate.set(
            state_class="user.preference",
            key="coffee",
            value={"semantic": "likes", "degree_hint": 0.6},
            sources=(current.id,),
        ),
        StateCandidate.set(
            state_class="user.preference",
            key="tea",
            value={"semantic": "likes", "degree_hint": True},
            sources=(current.id,),
        ),
        StateCandidate.set(
            state_class="user.preference",
            key="water",
            value={"semantic": "likes", "degree_hint": 0.5, "confidence": 0.9},
            sources=(current.id,),
        ),
    )

    validation = apply_state_candidates(
        current_state=CanonicalState(states=(existing,)),
        candidates=candidates,
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )
    accepted = [
        decision for decision in validation.decisions if decision.status == "accepted"
    ]
    rejected = [
        decision for decision in validation.decisions if decision.status == "rejected"
    ]
    coffee = next(
        (record for record in validation.state.states if record.key == "coffee"),
        None,
    )

    checks = (
        EvaluationCheck(
            check_id="weakened_degree_is_set_replacement_not_remove",
            boundary="validator",
            passed=len(accepted) == 1 and accepted[0].action == "replace",
            expected="replace",
            observed=(accepted[0].action if accepted else "not accepted"),
        ),
        EvaluationCheck(
            check_id="weakened_positive_state_remains_active",
            boundary="canonical_state",
            passed=coffee is not None
            and coffee.value == {"semantic": "likes", "degree_hint": 0.6},
            expected="coffee=likes@0.6",
            observed=(
                "coffee=likes@0.6"
                if coffee is not None
                and coffee.value == {"semantic": "likes", "degree_hint": 0.6}
                else "coffee missing or changed"
            ),
        ),
        EvaluationCheck(
            check_id="invalid_degree_envelopes_are_rejected",
            boundary="validator",
            passed=len(rejected) == 2
            and all(decision.reason == "invalid_degree_hint_value" for decision in rejected),
            expected="invalid_degree_hint_value,invalid_degree_hint_value",
            observed=",".join(str(decision.reason) for decision in rejected) or "none",
        ),
        EvaluationCheck(
            check_id="invalid_degree_candidates_do_not_enter_state",
            boundary="canonical_state",
            passed={record.key for record in validation.state.states} == {"coffee"},
            expected="coffee",
            observed=",".join(record.key for record in validation.state.states) or "none",
        ),
        EvaluationCheck(
            check_id="valid_degree_replacement_retains_current_user_source",
            boundary="event_provenance",
            passed=coffee is not None and coffee.sources == (current.id,),
            expected=current.id,
            observed=(
                coffee.sources[0]
                if coffee is not None and coffee.sources
                else "missing"
            ),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="degree_hint_integrity",
        checks=checks,
        metrics={
            "accepted_candidate_count": len(accepted),
            "rejected_candidate_count": len(rejected),
            "final_state_count": len(validation.state.states),
        },
    )
