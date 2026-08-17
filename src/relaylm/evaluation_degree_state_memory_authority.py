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
        payload={"content": "What do you remember about tea?"},
        event_id="evaluation-current-event",
        timestamp="2026-08-17T12:30:00+00:00",
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="tea-current",
                state_class="user.preference",
                key="tea",
                value={"semantic": "likes", "degree_hint": 0.85},
                sources=("evaluation-source-event",),
            ),
        )
    )


def _chunk(*, case_id: str, heading: str, content: str) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#evaluation/{case_id}",
        content=f"## {heading}\n\n{content}",
    )


def _is_retained(chunk: MemoryChunk) -> bool:
    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=_state(),
        current_event=_current(),
        retrieved_memory=(chunk,),
    )
    return tuple(item.location for item in compiled.memory) == (chunk.location,)


async def evaluate_degree_state_memory_authority() -> EvaluationScenarioResult:
    stale_degree = _chunk(
        case_id="stale-degree",
        heading="Tea",
        content="Rin likes tea.\ndegree_hint: 0.65",
    )
    matching_degree = _chunk(
        case_id="matching-degree",
        heading="Tea",
        content="Rin likes tea.\ndegree_hint = 0.85",
    )
    missing_degree = _chunk(
        case_id="missing-degree",
        heading="Tea",
        content="Rin likes tea.",
    )
    semantic_conflict = _chunk(
        case_id="semantic-conflict",
        heading="Tea",
        content="Rin dislikes tea.\ndegree_hint: 0.85",
    )
    inline_stale = _chunk(
        case_id="inline-stale",
        heading="Profile Notes",
        content="tea: likes; degree_hint: 0.65",
    )
    cross_key_degree = _chunk(
        case_id="cross-key-degree",
        heading="Profile Notes",
        content="tea: likes\ncoffee: likes; degree_hint: 0.65",
    )
    historical = _chunk(
        case_id="historical",
        heading="Preference History",
        content="An old tea survey recorded degree_hint: 0.65.",
    )

    observations = {
        "stale_degree": _is_retained(stale_degree),
        "matching_degree": _is_retained(matching_degree),
        "missing_degree": _is_retained(missing_degree),
        "semantic_conflict": _is_retained(semantic_conflict),
        "inline_stale": _is_retained(inline_stale),
        "cross_key_degree": _is_retained(cross_key_degree),
        "historical": _is_retained(historical),
    }

    checks = (
        EvaluationCheck(
            check_id="stale_explicit_degree_suppressed",
            boundary="context_compiler",
            passed=not observations["stale_degree"],
            expected=False,
            observed=observations["stale_degree"],
        ),
        EvaluationCheck(
            check_id="matching_explicit_degree_retained",
            boundary="context_compiler",
            passed=observations["matching_degree"],
            expected=True,
            observed=observations["matching_degree"],
        ),
        EvaluationCheck(
            check_id="missing_degree_not_inferred_as_conflict",
            boundary="context_compiler",
            passed=observations["missing_degree"],
            expected=True,
            observed=observations["missing_degree"],
        ),
        EvaluationCheck(
            check_id="matching_number_does_not_rescue_semantic_conflict",
            boundary="context_compiler",
            passed=not observations["semantic_conflict"],
            expected=False,
            observed=observations["semantic_conflict"],
        ),
        EvaluationCheck(
            check_id="inline_same_line_degree_is_authoritative",
            boundary="context_compiler",
            passed=not observations["inline_stale"],
            expected=False,
            observed=observations["inline_stale"],
        ),
        EvaluationCheck(
            check_id="inline_key_does_not_borrow_other_key_degree",
            boundary="context_compiler",
            passed=observations["cross_key_degree"],
            expected=True,
            observed=observations["cross_key_degree"],
        ),
        EvaluationCheck(
            check_id="unaddressed_historical_degree_prose_retained",
            boundary="context_compiler",
            passed=observations["historical"],
            expected=True,
            observed=observations["historical"],
        ),
    )
    retained_count = sum(observations.values())
    return EvaluationScenarioResult(
        scenario_id="degree_state_memory_authority",
        checks=checks,
        metrics={
            "case_count": len(observations),
            "retained_case_count": retained_count,
            "suppressed_case_count": len(observations) - retained_count,
        },
    )
