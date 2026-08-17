from __future__ import annotations

import pytest

from relaylm.memory_retrieval import select_memory_chunks


MEMORY = """# Memory

## Preferences

Rin likes tea.

## Coffee

Rin currently prefers coffee over tea.

## Travel

Rin visited Fukuoka last year.
"""


def test_selects_only_relevant_complete_heading_chunk() -> None:
    selected = select_memory_chunks(
        memory_markdown=MEMORY,
        query="What did I say about coffee?",
        max_chunks=1,
        max_chars=200,
    )

    assert len(selected) == 1
    assert selected[0].heading_path == ("Memory", "Coffee")
    assert selected[0].location == "memory/MEMORY.md#memory/coffee"
    assert selected[0].content == "## Coffee\n\nRin currently prefers coffee over tea."


def test_irrelevant_optional_memory_has_no_zero_match_fallback() -> None:
    selected = select_memory_chunks(
        memory_markdown=MEMORY,
        query="Tell me about astronomy",
        max_chunks=2,
        max_chars=500,
    )

    assert selected == ()


def test_oversized_relevant_chunk_is_skipped_not_truncated() -> None:
    markdown = """# Memory

## Coffee details

Coffee preference has a deliberately long explanation that will not fit.

## Coffee summary

Coffee is preferred.
"""
    selected = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=2,
        max_chars=len("## Coffee summary\n\nCoffee is preferred."),
    )

    assert [chunk.heading_path[-1] for chunk in selected] == ["Coffee summary"]
    assert selected[0].content == "## Coffee summary\n\nCoffee is preferred."


def test_duplicate_heading_locations_are_deterministic_and_unique() -> None:
    markdown = """# Memory

## Notes

Coffee note one.

## Notes

Coffee note two.
"""
    first = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=2,
        max_chars=500,
    )
    second = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=2,
        max_chars=500,
    )

    assert [chunk.location for chunk in first] == [
        "memory/MEMORY.md#memory/notes",
        "memory/MEMORY.md#memory/notes-2",
    ]
    assert first == second


def test_selection_preserves_document_order_after_ranking() -> None:
    markdown = """# Memory

## Coffee history

Coffee appears once.

## Other

Unrelated text.

## Coffee preference

Coffee coffee coffee.
"""
    selected = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=2,
        max_chars=500,
    )

    assert [chunk.heading_path[-1] for chunk in selected] == [
        "Coffee history",
        "Coffee preference",
    ]


def test_fenced_code_heading_is_not_split_into_memory_chunk() -> None:
    markdown = """# Memory

## Notes

Coffee example:

```markdown
## Not a memory heading
coffee code
```

Still the same notes section.
"""
    selected = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=2,
        max_chars=500,
    )

    assert len(selected) == 1
    assert selected[0].heading_path == ("Memory", "Notes")
    assert "## Not a memory heading" in selected[0].content


def test_zero_and_negative_budgets_are_explicit() -> None:
    original = MEMORY
    assert select_memory_chunks(
        memory_markdown=MEMORY,
        query="coffee",
        max_chunks=0,
        max_chars=100,
    ) == ()
    assert select_memory_chunks(
        memory_markdown=MEMORY,
        query="coffee",
        max_chunks=2,
        max_chars=0,
    ) == ()
    assert MEMORY == original

    with pytest.raises(ValueError, match="max_chunks must not be negative"):
        select_memory_chunks(
            memory_markdown=MEMORY,
            query="coffee",
            max_chunks=-1,
            max_chars=100,
        )
    with pytest.raises(ValueError, match="max_chars must not be negative"):
        select_memory_chunks(
            memory_markdown=MEMORY,
            query="coffee",
            max_chunks=1,
            max_chars=-1,
        )
