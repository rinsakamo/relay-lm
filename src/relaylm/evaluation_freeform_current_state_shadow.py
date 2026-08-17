from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _current() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-17T13:55:00+00:00",
    )


def _state(*, key: str = "residence_location", value: object = "Fukuoka") -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="current-state",
                state_class="user.fact",
                key=key,
                value=value,
                sources=("source-event",),
            ),
        )
    )


def _chunk(case_id: str, content: str) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/profile-notes/{case_id}",
        content=f"## Profile Notes\n\n{content}",
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current(),
        retrieved_memory=(chunk,),
    )


def _retained(compiled, chunk: MemoryChunk) -> bool:
    return tuple(item.location for item in compiled.memory) == (chunk.location,)


async def evaluate_freeform_current_state_shadow() -> EvaluationScenarioResult:
    explicit_conflict = _chunk(
        "explicit-conflict",
        "Current residence location is Hokkaido.",
    )
    explicit_conflict_result = _compile(chunk=explicit_conflict)

    explicit_match = _chunk(
        "explicit-match",
        "The residence location is currently Fukuoka.",
    )
    explicit_match_result = _compile(chunk=explicit_match)

    now_conflict = _chunk(
        "now-conflict",
        "Preferred beverage is now tea.",
    )
    now_conflict_result = _compile(
        chunk=now_conflict,
        state=_state(key="preferred_beverage", value="coffee"),
    )

    prefixed = _chunk(
        "prefixed-current",
        "Previous current residence location is Hokkaido.",
    )
    prefixed_result = _compile(chunk=prefixed)

    historical = _chunk(
        "historical",
        "Residence location in 2020 was Hokkaido.",
    )
    historical_result = _compile(chunk=historical)

    omitted_key = _chunk(
        "omitted-key",
        "Rin currently lives in Hokkaido.",
    )
    omitted_key_result = _compile(chunk=omitted_key)

    boolean_freeform = _chunk(
        "boolean-freeform",
        "Current notifications enabled is false.",
    )
    boolean_result = _compile(
        chunk=boolean_freeform,
        state=_state(key="notifications_enabled", value=True),
    )

    cases = (
        explicit_conflict_result,
        explicit_match_result,
        now_conflict_result,
        prefixed_result,
        historical_result,
        omitted_key_result,
        boolean_result,
    )
    retained_flags = (
        _retained(explicit_conflict_result, explicit_conflict),
        _retained(explicit_match_result, explicit_match),
        _retained(now_conflict_result, now_conflict),
        _retained(prefixed_result, prefixed),
        _retained(historical_result, historical),
        _retained(omitted_key_result, omitted_key),
        _retained(boolean_result, boolean_freeform),
    )

    checks = (
        EvaluationCheck(
            check_id="explicit_current_conflict_suppressed",
            boundary="context_compiler",
            passed=explicit_conflict_result.memory == (),
            expected=0,
            observed=len(explicit_conflict_result.memory),
        ),
        EvaluationCheck(
            check_id="explicit_current_match_retained",
            boundary="context_compiler",
            passed=retained_flags[1],
            expected=True,
            observed=retained_flags[1],
        ),
        EvaluationCheck(
            check_id="now_form_conflict_suppressed",
            boundary="context_compiler",
            passed=now_conflict_result.memory == (),
            expected=0,
            observed=len(now_conflict_result.memory),
        ),
        EvaluationCheck(
            check_id="prefixed_current_phrase_retained",
            boundary="context_compiler",
            passed=retained_flags[3],
            expected=True,
            observed=retained_flags[3],
        ),
        EvaluationCheck(
            check_id="historical_freeform_retained",
            boundary="context_compiler",
            passed=retained_flags[4],
            expected=True,
            observed=retained_flags[4],
        ),
        EvaluationCheck(
            check_id="omitted_key_freeform_retained",
            boundary="context_compiler",
            passed=retained_flags[5],
            expected=True,
            observed=retained_flags[5],
        ),
        EvaluationCheck(
            check_id="boolean_freeform_not_expanded",
            boundary="context_compiler",
            passed=retained_flags[6],
            expected=True,
            observed=retained_flags[6],
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="freeform_current_state_shadow",
        checks=checks,
        metrics={
            "case_count": len(cases),
            "suppressed_case_count": sum(len(case.memory) == 0 for case in cases),
            "retained_case_count": sum(retained_flags),
            "scalar_current_claim_count": 3,
        },
    )
