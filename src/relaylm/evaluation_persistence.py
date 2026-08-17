from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


async def evaluate_persistence_integrity() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-eval-persistence-") as temporary:
        root = Path(temporary)
        character = CharacterDirectory(root)

        event = Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="persisted-event",
            timestamp="2026-08-17T00:00:00+00:00",
        )
        state = CanonicalState(
            states=(
                StateRecord(
                    state_id="persisted-state",
                    state_class="user.preference",
                    key="tea",
                    value={"semantic": "likes", "degree_hint": 0.8},
                    sources=(event.id,),
                    valid_from=event.timestamp,
                ),
            )
        )

        character.append_event(event)
        character.save_state(state)
        reopened = CharacterDirectory(root)
        reopened_events = list(reopened.iter_events())
        reopened_state = reopened.load_state()
        state_temp_absent = not (root / "memory" / ".state.json.tmp").exists()

        malformed_state = "{not-json\n"
        reopened.state_path.write_text(malformed_state, encoding="utf-8")
        state_failure = False
        try:
            reopened.load_state()
        except CharacterDataError:
            state_failure = True
        malformed_state_unchanged = (
            reopened.state_path.read_text(encoding="utf-8") == malformed_state
        )

        valid_event_line = reopened.events_path.read_text(encoding="utf-8")
        malformed_events = valid_event_line + "not-json\n"
        reopened.events_path.write_text(malformed_events, encoding="utf-8")
        event_failure = False
        event_line_number_reported = False
        try:
            list(reopened.iter_events())
        except CharacterDataError as exc:
            event_failure = True
            event_line_number_reported = "line 2" in str(exc)
        malformed_events_unchanged = (
            reopened.events_path.read_text(encoding="utf-8") == malformed_events
        )

    checks = (
        EvaluationCheck(
            check_id="event_round_trip_across_reopen_is_exact",
            boundary="event_journal",
            passed=reopened_events == [event],
            expected="persisted-event",
            observed=(reopened_events[0].id if len(reopened_events) == 1 else "mismatch"),
        ),
        EvaluationCheck(
            check_id="state_round_trip_across_reopen_is_exact",
            boundary="canonical_state",
            passed=reopened_state == state,
            expected="persisted-state",
            observed=(
                reopened_state.states[0].state_id
                if len(reopened_state.states) == 1
                else "mismatch"
            ),
        ),
        EvaluationCheck(
            check_id="atomic_state_replace_leaves_no_temp_file",
            boundary="filesystem",
            passed=state_temp_absent,
            expected=True,
            observed=state_temp_absent,
        ),
        EvaluationCheck(
            check_id="malformed_state_fails_closed_without_rewrite",
            boundary="canonical_state",
            passed=state_failure and malformed_state_unchanged,
            expected=True,
            observed=state_failure and malformed_state_unchanged,
        ),
        EvaluationCheck(
            check_id="malformed_event_line_fails_closed_with_location",
            boundary="event_journal",
            passed=event_failure
            and event_line_number_reported
            and malformed_events_unchanged,
            expected=True,
            observed=event_failure
            and event_line_number_reported
            and malformed_events_unchanged,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="persistence_integrity",
        checks=checks,
        metrics={
            "round_trip_event_count": len(reopened_events),
            "round_trip_state_count": len(reopened_state.states),
            "malformed_failure_count": int(state_failure) + int(event_failure),
        },
    )
