from __future__ import annotations

from collections.abc import Iterable

from relaylm.cognitive import KnowledgeItem


def _require_non_negative_limit(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def select_knowledge_items(
    items: Iterable[KnowledgeItem],
    *,
    max_items: int,
    max_chars: int,
) -> tuple[KnowledgeItem, ...]:
    """Select deterministic whole-file package knowledge inside explicit caps.

    Input order is semantic-owner order (the package loader supplies sorted
    package-relative paths). Files are never truncated or semantically ranked.
    A file that cannot fit the remaining character budget is skipped so a later
    smaller file may still fit without changing relative order.
    """

    _require_non_negative_limit("max_items", max_items)
    _require_non_negative_limit("max_chars", max_chars)
    if max_items == 0 or max_chars == 0:
        return ()

    selected: list[KnowledgeItem] = []
    used_chars = 0
    for item in items:
        if not isinstance(item, KnowledgeItem):
            raise TypeError("items must contain KnowledgeItem values")
        if len(selected) >= max_items:
            break
        item_chars = len(item.content)
        if used_chars + item_chars > max_chars:
            continue
        selected.append(item)
        used_chars += item_chars
    return tuple(selected)
