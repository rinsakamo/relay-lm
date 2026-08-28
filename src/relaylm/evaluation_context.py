from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input, compile_cognitive_input_with_diagnostics
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.event_retrieval import select_event_evidence
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateRecord


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


async def evaluate_state_selection_diagnostics() -> EvaluationScenarioResult:
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="tea-secret",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("source-tea-secret",),
            ),
            StateRecord(
                state_id="coffee-secret",
                state_class="user.preference",
                key="coffee",
                value="likes",
                sources=("source-coffee-secret",),
            ),
            StateRecord(
                state_id="preferred-secret",
                state_class="user.preference",
                key="preferred_beverage",
                value="coffee",
                sources=("source-preferred-secret",),
            ),
            StateRecord(
                state_id="home-secret",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                sources=("source-home-secret",),
            ),
        )
    )
    identity = Identity("# Evaluation Character\nBe grounded.\n")
    matched_event = _message(
        event_id="matched-current-secret",
        actor="user",
        content="Help me choose coffee today",
        second=5,
    )
    zero_match_event = _message(
        event_id="zero-match-current-secret",
        actor="user",
        content="Tell me something unrelated about weather",
        second=6,
    )

    matched = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=state,
        current_event=matched_event,
        max_state_records=2,
    )
    zero_match = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=state,
        current_event=zero_match_event,
        max_state_records=2,
    )
    matched_diagnostic = matched.diagnostics[0]
    zero_match_diagnostic = zero_match.diagnostics[0]
    serialized = json.dumps(
        [asdict(matched_diagnostic), asdict(zero_match_diagnostic)],
        ensure_ascii=False,
    )
    forbidden = (
        "coffee",
        "preferred_beverage",
        "Fukuoka",
        "tea-secret",
        "coffee-secret",
        "source-coffee-secret",
        "matched-current-secret",
        "zero-match-current-secret",
    )

    checks = (
        EvaluationCheck(
            check_id="matched_selection_reports_relevance_admission",
            boundary="diagnostics",
            passed=matched_diagnostic.mode == "relevance_filtered"
            and matched_diagnostic.eligible_count == 4
            and matched_diagnostic.relevance_admitted_count == 2
            and matched_diagnostic.relevance_culled_count == 2
            and matched_diagnostic.lexical_admitted_count == 2
            and matched_diagnostic.selected_count == 2
            and matched_diagnostic.budget_evicted_count == 0
            and matched_diagnostic.selected_fallback_count == 0
            and not matched_diagnostic.budget_pressure,
            expected=True,
            observed=matched_diagnostic.relevance_admitted_count == 2,
        ),
        EvaluationCheck(
            check_id="zero_match_selection_is_culled_without_fallback",
            boundary="diagnostics",
            passed=zero_match_diagnostic.mode == "relevance_filtered"
            and zero_match_diagnostic.eligible_count == 4
            and zero_match_diagnostic.relevance_admitted_count == 0
            and zero_match_diagnostic.relevance_culled_count == 4
            and zero_match_diagnostic.selected_count == 0
            and zero_match_diagnostic.budget_evicted_count == 0
            and zero_match_diagnostic.selected_fallback_count == 0
            and not zero_match_diagnostic.budget_pressure,
            expected=0,
            observed=zero_match_diagnostic.selected_count,
        ),
        EvaluationCheck(
            check_id="diagnostics_match_selected_state_cardinality",
            boundary="context_compiler",
            passed=matched_diagnostic.selected_count == len(matched.cognitive_input.state)
            and zero_match_diagnostic.selected_count
            == len(zero_match.cognitive_input.state),
            expected=True,
            observed=matched_diagnostic.selected_count == len(matched.cognitive_input.state),
        ),
        EvaluationCheck(
            check_id="diagnostics_do_not_expose_semantic_payload",
            boundary="diagnostics",
            passed=all(value not in serialized for value in forbidden),
            expected=True,
            observed=all(value not in serialized for value in forbidden),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="state_selection_diagnostics",
        checks=checks,
        metrics={
            "eligible_state_count": zero_match_diagnostic.eligible_count,
            "selected_state_count": zero_match_diagnostic.selected_count,
            "evicted_state_count": zero_match_diagnostic.evicted_count,
            "selected_fallback_count": zero_match_diagnostic.selected_fallback_count,
        },
    )


async def evaluate_targeted_event_retrieval() -> EvaluationScenarioResult:
    tea = _message(event_id="tea", actor="user", content="Rin likes tea.", second=10)
    coffee = _message(
        event_id="coffee",
        actor="user",
        content="Rin prefers coffee now.",
        second=11,
    )
    travel = _message(
        event_id="travel",
        actor="user",
        content="Rin visited Fukuoka.",
        second=12,
    )
    relevant = select_event_evidence(
        events=(tea, coffee, travel),
        query="What did I say about coffee?",
        max_events=2,
        max_chars=200,
    )
    irrelevant = select_event_evidence(
        events=(tea, travel),
        query="astronomy",
        max_events=2,
        max_chars=200,
    )

    prior = _message(
        event_id="prior-coffee",
        actor="user",
        content="Coffee is good.",
        second=13,
    )
    current = _message(
        event_id="current-coffee",
        actor="user",
        content="Coffee coffee coffee.",
        second=14,
    )
    excluded_current = select_event_evidence(
        events=(prior, current),
        query="coffee",
        max_events=1,
        max_chars=200,
        exclude_event_ids=(current.id,),
    )

    oversized_event = _message(
        event_id="oversized",
        actor="user",
        content="Coffee " + "details " * 30,
        second=15,
    )
    summary = _message(
        event_id="summary",
        actor="user",
        content="Coffee summary.",
        second=16,
    )
    oversized = select_event_evidence(
        events=(oversized_event, summary),
        query="coffee",
        max_events=2,
        max_chars=len(summary.payload["content"]),
    )

    older = _message(
        event_id="older-ranked",
        actor="user",
        content="Coffee preference changed.",
        second=17,
    )
    middle = _message(
        event_id="middle-ranked",
        actor="user",
        content="Coffee was mentioned.",
        second=18,
    )
    newer = _message(
        event_id="newer-ranked",
        actor="user",
        content="Preference for coffee was confirmed.",
        second=19,
    )
    ranked = select_event_evidence(
        events=(older, middle, newer),
        query="coffee preference",
        max_events=2,
        max_chars=300,
    )

    tie_older = _message(
        event_id="tie-older",
        actor="user",
        content="Coffee note.",
        second=20,
    )
    tie_newer = _message(
        event_id="tie-newer",
        actor="user",
        content="Coffee update.",
        second=21,
    )
    tie = select_event_evidence(
        events=(tie_older, tie_newer),
        query="coffee",
        max_events=1,
        max_chars=200,
    )

    dislikes = _message(
        event_id="dislikes",
        actor="user",
        content="Rin dislikes coffee.",
        second=22,
    )
    likes = _message(
        event_id="likes",
        actor="user",
        content="Rin likes tea.",
        second=23,
    )
    token_boundary = select_event_evidence(
        events=(dislikes, likes),
        query="likes",
        max_events=2,
        max_chars=200,
    )

    checks = (
        EvaluationCheck(
            check_id="positive_relevant_event_selected",
            boundary="event_retrieval",
            passed=relevant == (coffee,),
            expected="coffee",
            observed=",".join(event.id for event in relevant) or "none",
        ),
        EvaluationCheck(
            check_id="irrelevant_events_have_no_fallback",
            boundary="event_retrieval",
            passed=irrelevant == (),
            expected=0,
            observed=len(irrelevant),
        ),
        EvaluationCheck(
            check_id="current_event_can_be_excluded_from_evidence",
            boundary="event_provenance",
            passed=excluded_current == (prior,) and current not in excluded_current,
            expected="prior-coffee",
            observed=",".join(event.id for event in excluded_current) or "none",
        ),
        EvaluationCheck(
            check_id="oversized_event_is_skipped_without_truncation",
            boundary="event_budget",
            passed=oversized == (summary,)
            and oversized[0].payload["content"] == "Coffee summary.",
            expected="summary",
            observed=",".join(event.id for event in oversized) or "none",
        ),
        EvaluationCheck(
            check_id="relevance_admission_restores_source_chronology",
            boundary="event_retrieval",
            passed=ranked == (older, newer),
            expected="older-ranked,newer-ranked",
            observed=",".join(event.id for event in ranked) or "none",
        ),
        EvaluationCheck(
            check_id="equal_relevance_prefers_newer_occurrence",
            boundary="event_retrieval",
            passed=tie == (tie_newer,),
            expected="tie-newer",
            observed=",".join(event.id for event in tie) or "none",
        ),
        EvaluationCheck(
            check_id="exact_tokens_do_not_match_substrings",
            boundary="event_retrieval",
            passed=token_boundary == (likes,),
            expected="likes",
            observed=",".join(event.id for event in token_boundary) or "none",
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="targeted_event_retrieval",
        checks=checks,
        metrics={
            "relevant_selected_count": len(relevant),
            "irrelevant_selected_count": len(irrelevant),
            "excluded_current_selected_count": len(excluded_current),
            "oversized_selected_count": len(oversized),
            "ranked_selected_count": len(ranked),
            "tie_selected_count": len(tie),
            "token_boundary_selected_count": len(token_boundary),
        },
    )
