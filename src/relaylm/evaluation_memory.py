from __future__ import annotations

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.memory_retrieval import select_memory_chunks


_MEMORY = """# Memory

## Preferences

Rin likes tea.

## Coffee

Rin currently prefers coffee over tea.

## Travel

Rin visited Fukuoka last year.
"""


async def evaluate_memory_heading_retrieval() -> EvaluationScenarioResult:
    relevant = select_memory_chunks(
        memory_markdown=_MEMORY,
        query="What did I say about coffee?",
        max_chunks=1,
        max_chars=200,
    )
    irrelevant = select_memory_chunks(
        memory_markdown=_MEMORY,
        query="Tell me about astronomy",
        max_chunks=2,
        max_chars=500,
    )

    oversized_memory = """# Memory

## Coffee details

Coffee preference has a deliberately long explanation that will not fit.

## Coffee summary

Coffee is preferred.
"""
    expected_summary = "## Coffee summary\n\nCoffee is preferred."
    oversized = select_memory_chunks(
        memory_markdown=oversized_memory,
        query="coffee",
        max_chunks=2,
        max_chars=len(expected_summary),
    )

    checks = (
        EvaluationCheck(
            check_id="relevant_memory_selects_complete_heading_section",
            boundary="memory_retrieval",
            passed=len(relevant) == 1
            and relevant[0].heading_path == ("Memory", "Coffee")
            and relevant[0].content == "## Coffee\n\nRin currently prefers coffee over tea.",
            expected="Memory/Coffee",
            observed="/".join(relevant[0].heading_path) if relevant else "none",
        ),
        EvaluationCheck(
            check_id="irrelevant_optional_memory_is_suppressed",
            boundary="memory_retrieval",
            passed=irrelevant == (),
            expected=0,
            observed=len(irrelevant),
        ),
        EvaluationCheck(
            check_id="oversized_chunk_is_skipped_without_truncation",
            boundary="memory_budget",
            passed=len(oversized) == 1
            and oversized[0].heading_path[-1] == "Coffee summary"
            and oversized[0].content == expected_summary,
            expected="Coffee summary",
            observed=oversized[0].heading_path[-1] if oversized else "none",
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="memory_heading_retrieval",
        checks=checks,
        metrics={
            "relevant_selected_count": len(relevant),
            "irrelevant_selected_count": len(irrelevant),
            "oversized_selected_count": len(oversized),
        },
    )
