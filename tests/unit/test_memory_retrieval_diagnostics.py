from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.memory_retrieval import (
    select_memory_chunks,
    select_memory_chunks_with_diagnostics,
)


MEMORY = """# Memory

## Coffee oversized

Coffee details are deliberately very long and will not fit inside the selected character budget.

## Coffee summary

Coffee is preferred.

## Coffee note

Coffee note.
"""


def test_memory_retrieval_diagnostics_report_budget_reasons_without_changing_selection() -> None:
    max_chars = len("## Coffee summary\n\nCoffee is preferred.")

    result = select_memory_chunks_with_diagnostics(
        memory_markdown=MEMORY,
        query="coffee",
        max_chunks=1,
        max_chars=max_chars,
    )
    plain = select_memory_chunks(
        memory_markdown=MEMORY,
        query="coffee",
        max_chunks=1,
        max_chars=max_chars,
    )

    assert result.chunks == plain
    assert [chunk.heading_path[-1] for chunk in result.chunks] == ["Coffee summary"]

    diagnostic = result.diagnostics
    assert diagnostic.mode == "lexical"
    assert diagnostic.parsed_chunk_count == 3
    assert diagnostic.positive_candidate_count == 3
    assert diagnostic.selected_count == 1
    assert diagnostic.chunk_budget_limit == 1
    assert diagnostic.character_budget_limit == max_chars
    assert diagnostic.character_budget_used == max_chars
    assert diagnostic.skipped_character_budget_count == 1
    assert diagnostic.unadmitted_chunk_limit_count == 1
    assert diagnostic.chunk_budget_pressure is True
    assert diagnostic.character_budget_pressure is True

    serialized = json.dumps(asdict(diagnostic), ensure_ascii=False)
    assert "Coffee" not in serialized
    assert "memory/MEMORY.md" not in serialized


def test_memory_retrieval_diagnostics_do_not_infer_candidates_when_retrieval_is_not_run() -> None:
    zero_budget = select_memory_chunks_with_diagnostics(
        memory_markdown=MEMORY,
        query="coffee",
        max_chunks=0,
        max_chars=100,
    )
    irrelevant = select_memory_chunks_with_diagnostics(
        memory_markdown=MEMORY,
        query="astronomy",
        max_chunks=2,
        max_chars=500,
    )

    assert zero_budget.chunks == ()
    assert zero_budget.diagnostics.mode == "zero_budget"
    assert zero_budget.diagnostics.parsed_chunk_count == 0
    assert zero_budget.diagnostics.positive_candidate_count == 0
    assert zero_budget.diagnostics.selected_count == 0
    assert zero_budget.diagnostics.chunk_budget_pressure is False
    assert zero_budget.diagnostics.character_budget_pressure is False

    assert irrelevant.chunks == ()
    assert irrelevant.diagnostics.mode == "lexical"
    assert irrelevant.diagnostics.parsed_chunk_count == 3
    assert irrelevant.diagnostics.positive_candidate_count == 0
    assert irrelevant.diagnostics.selected_count == 0
    assert irrelevant.diagnostics.skipped_character_budget_count == 0
    assert irrelevant.diagnostics.unadmitted_chunk_limit_count == 0
    assert irrelevant.diagnostics.chunk_budget_pressure is False
    assert irrelevant.diagnostics.character_budget_pressure is False
