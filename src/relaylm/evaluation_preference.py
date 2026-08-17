from __future__ import annotations

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.validation import apply_state_candidates


async def evaluate_comparative_preference_preservation() -> EvaluationScenarioResult:
    existing = StateRecord(
        state_id="tea-existing",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("older-user-event",),
    )
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "最近は紅茶よりコーヒーの方が好き"},
        event_id="current-preference",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    candidates = (
        StateCandidate.set(
            state_class="user.preference",
            key="coffee",
            value="likes",
            sources=(current.id,),
        ),
        StateCandidate.set(
            state_class="user.preference",
            key="preferred_beverage",
            value="coffee",
            sources=(current.id,),
        ),
    )

    validation = apply_state_candidates(
        current_state=CanonicalState(states=(existing,)),
        candidates=candidates,
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )
    preference_records = {
        record.key: record
        for record in validation.state.states
        if record.state_class == "user.preference"
    }
    accepted = [
        decision for decision in validation.decisions if decision.status == "accepted"
    ]
    new_records = [
        preference_records[key]
        for key in ("coffee", "preferred_beverage")
        if key in preference_records
    ]

    checks = (
        EvaluationCheck(
            check_id="comparative_additions_are_creates",
            boundary="validator",
            passed=[decision.action for decision in validation.decisions]
            == ["create", "create"],
            expected="create,create",
            observed=",".join(str(decision.action) for decision in validation.decisions),
        ),
        EvaluationCheck(
            check_id="weaker_positive_preference_is_preserved",
            boundary="canonical_state",
            passed=preference_records.get("tea") == existing,
            expected="tea=likes preserved",
            observed=(
                "tea=likes preserved"
                if preference_records.get("tea") == existing
                else "tea changed or missing"
            ),
        ),
        EvaluationCheck(
            check_id="comparative_preference_uses_separate_specific_keys",
            boundary="canonical_state",
            passed={key: record.value for key, record in preference_records.items()}
            == {
                "tea": "likes",
                "coffee": "likes",
                "preferred_beverage": "coffee",
            },
            expected="tea=likes,coffee=likes,preferred_beverage=coffee",
            observed=",".join(
                f"{key}={record.value}" for key, record in preference_records.items()
            ),
        ),
        EvaluationCheck(
            check_id="new_preference_states_retain_current_user_source",
            boundary="event_provenance",
            passed=len(new_records) == 2
            and all(record.sources == (current.id,) for record in new_records),
            expected=current.id,
            observed=(
                current.id
                if len(new_records) == 2
                and all(record.sources == (current.id,) for record in new_records)
                else "source mismatch"
            ),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="comparative_preference_preservation",
        checks=checks,
        metrics={
            "accepted_candidate_count": len(accepted),
            "final_preference_state_count": len(preference_records),
            "preserved_existing_state_count": int(
                preference_records.get("tea") == existing
            ),
        },
    )
