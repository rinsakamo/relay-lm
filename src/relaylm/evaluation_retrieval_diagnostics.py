from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.event_retrieval import (
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event
from relaylm.memory_retrieval import (
    select_memory_chunks,
    select_memory_chunks_with_diagnostics,
)

_MEMORY_QUERY = "quasar memory querysecret"
_MEMORY_MARKDOWN = (
    "# Oversized Quasar Memory\n\n"
    "quasar memory querysecret memory-oversized-secret "
    + "oversizedpayload " * 24
    + "\n\n"
    "# Compact Quasar Alpha\n\n"
    "quasar memory querysecret memory-alpha-secret.\n\n"
    "# Compact Quasar Beta\n\n"
    "quasar memory querysecret memory-beta-secret.\n\n"
    "# Compact Quasar Extra\n\n"
    "quasar memory querysecret memory-extra-secret.\n"
)
_EVENT_QUERY = "nebula anchor querysecret"


def _event(
    *,
    event_id: str,
    event_type: str = "message",
    content: object,
    second: int,
) -> Event:
    return Event.create(
        type=event_type,
        actor="user",
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T00:00:{second:02d}+00:00",
    )


async def evaluate_retrieval_stage_diagnostics() -> EvaluationScenarioResult:
    memory_plain = select_memory_chunks(
        memory_markdown=_MEMORY_MARKDOWN,
        query=_MEMORY_QUERY,
        max_chunks=2,
        max_chars=140,
    )
    memory_result = select_memory_chunks_with_diagnostics(
        memory_markdown=_MEMORY_MARKDOWN,
        query=_MEMORY_QUERY,
        max_chunks=2,
        max_chars=140,
    )
    memory_zero = select_memory_chunks_with_diagnostics(
        memory_markdown=_MEMORY_MARKDOWN,
        query=_MEMORY_QUERY,
        max_chunks=0,
        max_chars=140,
    )

    events = (
        _event(
            event_id="event-excluded-secret",
            content="nebula anchor querysecret excluded-event-content-secret",
            second=10,
        ),
        _event(
            event_id="event-non-message-secret",
            event_type="observation",
            content="nebula anchor querysecret non-message-content-secret",
            second=11,
        ),
        _event(
            event_id="event-blank-secret",
            content=" ",
            second=12,
        ),
        _event(
            event_id="event-irrelevant-secret",
            content="gardening-only-event-content-secret",
            second=13,
        ),
        _event(
            event_id="event-extra-secret",
            content="nebula anchor querysecret event-extra-content-secret",
            second=14,
        ),
        _event(
            event_id="event-alpha-secret",
            content="nebula anchor querysecret event-alpha-content-secret",
            second=15,
        ),
        _event(
            event_id="event-beta-secret",
            content="nebula anchor querysecret event-beta-content-secret",
            second=16,
        ),
        _event(
            event_id="event-oversized-secret",
            content=(
                "nebula anchor querysecret event-oversized-content-secret "
                + "oversized-event-payload-secret " * 16
            ),
            second=17,
        ),
    )
    excluded_event_ids = (events[0].id,)
    event_plain = select_event_evidence(
        events=events,
        query=_EVENT_QUERY,
        max_events=2,
        max_chars=140,
        exclude_event_ids=excluded_event_ids,
    )
    event_result = select_event_evidence_with_diagnostics(
        events=events,
        query=_EVENT_QUERY,
        max_events=2,
        max_chars=140,
        exclude_event_ids=excluded_event_ids,
    )

    zero_budget_iterated = False

    def unseen_events():
        nonlocal zero_budget_iterated
        zero_budget_iterated = True
        yield events[-1]

    event_zero = select_event_evidence_with_diagnostics(
        events=unseen_events(),
        query=_EVENT_QUERY,
        max_events=0,
        max_chars=140,
    )

    memory_diagnostic = memory_result.diagnostics
    event_diagnostic = event_result.diagnostics
    memory_zero_diagnostic = memory_zero.diagnostics
    event_zero_diagnostic = event_zero.diagnostics

    serialized = json.dumps(
        [
            asdict(memory_diagnostic),
            asdict(event_diagnostic),
            asdict(memory_zero_diagnostic),
            asdict(event_zero_diagnostic),
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden_payload = (
        _MEMORY_QUERY,
        _EVENT_QUERY,
        "memory-oversized-secret",
        "memory-alpha-secret",
        "memory-beta-secret",
        "memory-extra-secret",
        "memory/MEMORY.md#oversized-quasar-memory",
        "memory/MEMORY.md#compact-quasar-alpha",
        "memory/MEMORY.md#compact-quasar-beta",
        "memory/MEMORY.md#compact-quasar-extra",
        "event-excluded-secret",
        "event-non-message-secret",
        "event-blank-secret",
        "event-irrelevant-secret",
        "event-extra-secret",
        "event-alpha-secret",
        "event-beta-secret",
        "event-oversized-secret",
        "excluded-event-content-secret",
        "non-message-content-secret",
        "gardening-only-event-content-secret",
        "event-extra-content-secret",
        "event-alpha-content-secret",
        "event-beta-content-secret",
        "event-oversized-content-secret",
        "oversized-event-payload-secret",
    )
    serialized_payload_free = all(
        payload not in serialized for payload in forbidden_payload
    )

    memory_zero_is_unobserved = (
        memory_zero_diagnostic.mode == "zero_budget"
        and memory_zero_diagnostic.parsed_chunk_count == 0
        and memory_zero_diagnostic.positive_candidate_count == 0
        and memory_zero_diagnostic.selected_count == 0
        and memory_zero_diagnostic.skipped_character_budget_count == 0
        and memory_zero_diagnostic.unadmitted_chunk_limit_count == 0
        and not memory_zero_diagnostic.chunk_budget_pressure
        and not memory_zero_diagnostic.character_budget_pressure
    )
    event_zero_is_unobserved = (
        not zero_budget_iterated
        and event_zero_diagnostic.mode == "zero_budget"
        and event_zero_diagnostic.input_event_count == 0
        and event_zero_diagnostic.excluded_event_count == 0
        and event_zero_diagnostic.non_message_count == 0
        and event_zero_diagnostic.blank_content_count == 0
        and event_zero_diagnostic.eligible_message_count == 0
        and event_zero_diagnostic.positive_candidate_count == 0
        and event_zero_diagnostic.selected_count == 0
        and event_zero_diagnostic.skipped_character_budget_count == 0
        and event_zero_diagnostic.unadmitted_event_limit_count == 0
        and not event_zero_diagnostic.event_budget_pressure
        and not event_zero_diagnostic.character_budget_pressure
    )

    checks = (
        EvaluationCheck(
            check_id="memory_diagnostic_selection_matches_plain_selector",
            boundary="memory_retrieval",
            passed=memory_result.chunks == memory_plain,
            expected=True,
            observed=memory_result.chunks == memory_plain,
        ),
        EvaluationCheck(
            check_id="memory_reports_positive_candidates_and_admission",
            boundary="memory_retrieval",
            passed=memory_diagnostic.positive_candidate_count == 4
            and memory_diagnostic.selected_count == 2,
            expected="positive=4,selected=2",
            observed=(
                f"positive={memory_diagnostic.positive_candidate_count},"
                f"selected={memory_diagnostic.selected_count}"
            ),
        ),
        EvaluationCheck(
            check_id="memory_reports_character_budget_skip",
            boundary="memory_retrieval",
            passed=memory_diagnostic.skipped_character_budget_count == 1
            and memory_diagnostic.character_budget_pressure,
            expected=1,
            observed=memory_diagnostic.skipped_character_budget_count,
        ),
        EvaluationCheck(
            check_id="memory_reports_chunk_limit_pressure",
            boundary="memory_retrieval",
            passed=memory_diagnostic.unadmitted_chunk_limit_count == 1
            and memory_diagnostic.chunk_budget_pressure,
            expected=1,
            observed=memory_diagnostic.unadmitted_chunk_limit_count,
        ),
        EvaluationCheck(
            check_id="event_diagnostic_selection_matches_plain_selector",
            boundary="event_retrieval",
            passed=event_result.events == event_plain,
            expected=True,
            observed=event_result.events == event_plain,
        ),
        EvaluationCheck(
            check_id="event_reports_exclusion_and_ineligibility",
            boundary="event_retrieval",
            passed=event_diagnostic.input_event_count == 8
            and event_diagnostic.excluded_event_count == 1
            and event_diagnostic.non_message_count == 1
            and event_diagnostic.blank_content_count == 1
            and event_diagnostic.eligible_message_count == 5,
            expected="input=8,excluded=1,non_message=1,blank=1,eligible=5",
            observed=(
                f"input={event_diagnostic.input_event_count},"
                f"excluded={event_diagnostic.excluded_event_count},"
                f"non_message={event_diagnostic.non_message_count},"
                f"blank={event_diagnostic.blank_content_count},"
                f"eligible={event_diagnostic.eligible_message_count}"
            ),
        ),
        EvaluationCheck(
            check_id="event_reports_positive_candidates_and_admission",
            boundary="event_retrieval",
            passed=event_diagnostic.positive_candidate_count == 4
            and event_diagnostic.selected_count == 2,
            expected="positive=4,selected=2",
            observed=(
                f"positive={event_diagnostic.positive_candidate_count},"
                f"selected={event_diagnostic.selected_count}"
            ),
        ),
        EvaluationCheck(
            check_id="event_reports_character_budget_skip",
            boundary="event_retrieval",
            passed=event_diagnostic.skipped_character_budget_count == 1
            and event_diagnostic.character_budget_pressure,
            expected=1,
            observed=event_diagnostic.skipped_character_budget_count,
        ),
        EvaluationCheck(
            check_id="event_reports_event_limit_pressure",
            boundary="event_retrieval",
            passed=event_diagnostic.unadmitted_event_limit_count == 1
            and event_diagnostic.event_budget_pressure,
            expected=1,
            observed=event_diagnostic.unadmitted_event_limit_count,
        ),
        EvaluationCheck(
            check_id="memory_zero_budget_does_not_infer_unseen_population",
            boundary="diagnostics",
            passed=memory_zero_is_unobserved,
            expected=True,
            observed=memory_zero_is_unobserved,
        ),
        EvaluationCheck(
            check_id="event_zero_budget_does_not_consume_or_infer_unseen_population",
            boundary="diagnostics",
            passed=event_zero_is_unobserved,
            expected=True,
            observed=event_zero_is_unobserved,
        ),
        EvaluationCheck(
            check_id="serialized_retrieval_diagnostics_are_content_free",
            boundary="diagnostics",
            passed=serialized_payload_free,
            expected=True,
            observed=serialized_payload_free,
        ),
    )

    return EvaluationScenarioResult(
        scenario_id="retrieval_stage_diagnostics",
        checks=checks,
        metrics={
            "memory_positive_candidate_count": memory_diagnostic.positive_candidate_count,
            "memory_selected_count": memory_diagnostic.selected_count,
            "memory_skipped_character_budget_count": (
                memory_diagnostic.skipped_character_budget_count
            ),
            "memory_unadmitted_chunk_limit_count": (
                memory_diagnostic.unadmitted_chunk_limit_count
            ),
            "event_input_event_count": event_diagnostic.input_event_count,
            "event_excluded_event_count": event_diagnostic.excluded_event_count,
            "event_ineligible_event_count": (
                event_diagnostic.non_message_count + event_diagnostic.blank_content_count
            ),
            "event_positive_candidate_count": event_diagnostic.positive_candidate_count,
            "event_selected_count": event_diagnostic.selected_count,
            "event_skipped_character_budget_count": (
                event_diagnostic.skipped_character_budget_count
            ),
            "event_unadmitted_event_limit_count": (
                event_diagnostic.unadmitted_event_limit_count
            ),
        },
    )
