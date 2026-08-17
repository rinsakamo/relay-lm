from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import apply_state_candidates


async def evaluate_correction_remove_semantics() -> EvaluationScenarioResult:
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="tea-old",
        timestamp="2026-08-16T00:00:00+00:00",
    )
    revoke_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "もう紅茶が好きではない"},
        event_id="tea-revoke",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    initial_tea = StateRecord(
        state_id="tea-state",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=(old_event.id,),
    )
    remove_candidate = StateCandidate.remove(
        state_class="user.preference",
        key="tea",
        sources=(revoke_event.id,),
    )
    remove_result = apply_state_candidates(
        current_state=CanonicalState(states=(initial_tea,)),
        candidates=(remove_candidate,),
        events={old_event.id: old_event, revoke_event.id: revoke_event},
        required_source_ids=frozenset({revoke_event.id}),
    )

    with tempfile.TemporaryDirectory(prefix="relaylm-eval-correction-") as temporary:
        character = CharacterDirectory(Path(temporary))
        character.append_event(old_event)
        character.append_event(revoke_event)
        character.save_state(remove_result.state)
        persisted_events = list(CharacterDirectory(temporary).iter_events())
        persisted_state = CharacterDirectory(temporary).load_state()

    weaken_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "コーヒーは前ほどじゃないけど、まだ好き"},
        event_id="coffee-weaken",
        timestamp="2026-08-17T00:00:01+00:00",
    )
    initial_coffee = StateRecord(
        state_id="coffee-state",
        state_class="user.preference",
        key="coffee",
        value={"semantic": "likes", "degree_hint": 0.9},
        sources=("coffee-old",),
    )
    weakening_candidate = StateCandidate.set(
        state_class="user.preference",
        key="coffee",
        value={"semantic": "likes", "degree_hint": 0.6},
        sources=(weaken_event.id,),
    )
    weakening_result = apply_state_candidates(
        current_state=CanonicalState(states=(initial_coffee,)),
        candidates=(weakening_candidate,),
        events={weaken_event.id: weaken_event},
        required_source_ids=frozenset({weaken_event.id}),
    )
    weakened = weakening_result.state.states[0] if weakening_result.state.states else None

    checks = (
        EvaluationCheck(
            check_id="explicit_remove_is_accepted_as_remove",
            boundary="validator",
            passed=len(remove_result.decisions) == 1
            and remove_result.decisions[0].status == "accepted"
            and remove_result.decisions[0].action == "remove",
            expected="accepted/remove",
            observed=(
                f"{remove_result.decisions[0].status}/{remove_result.decisions[0].action}"
                if remove_result.decisions
                else "no decision"
            ),
        ),
        EvaluationCheck(
            check_id="remove_closes_current_state_slot",
            boundary="canonical_state",
            passed=persisted_state.states == (),
            expected=0,
            observed=len(persisted_state.states),
        ),
        EvaluationCheck(
            check_id="remove_does_not_delete_event_history",
            boundary="event_journal",
            passed=[event.id for event in persisted_events]
            == [old_event.id, revoke_event.id],
            expected="tea-old,tea-revoke",
            observed=",".join(event.id for event in persisted_events) or "none",
        ),
        EvaluationCheck(
            check_id="weakening_remains_set_replacement_not_remove",
            boundary="validator",
            passed=len(weakening_result.decisions) == 1
            and weakening_result.decisions[0].status == "accepted"
            and weakening_result.decisions[0].action == "replace",
            expected="accepted/replace",
            observed=(
                f"{weakening_result.decisions[0].status}/{weakening_result.decisions[0].action}"
                if weakening_result.decisions
                else "no decision"
            ),
        ),
        EvaluationCheck(
            check_id="weakened_positive_state_remains_current",
            boundary="canonical_state",
            passed=weakened is not None
            and weakened.value == {"semantic": "likes", "degree_hint": 0.6},
            expected="coffee=likes@0.6",
            observed=(
                "coffee=likes@0.6"
                if weakened is not None
                and weakened.value == {"semantic": "likes", "degree_hint": 0.6}
                else "missing or changed"
            ),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="correction_remove_semantics",
        checks=checks,
        metrics={
            "remove_decision_count": len(remove_result.decisions),
            "post_remove_state_count": len(persisted_state.states),
            "persisted_event_count": len(persisted_events),
            "weakening_state_count": len(weakening_result.state.states),
        },
    )
