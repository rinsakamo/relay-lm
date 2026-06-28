"""Runtime compatibility hooks for scoped Primary MEM recall."""
from __future__ import annotations

import re

_TOKEN_WITH_SLASH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_JAPANESE_RECALL_PHRASES = (
    "朝の集中作業",
    "集中作業",
    "落ち着く",
    "落ち着き",
    "飲み物",
    "浅煎り",
    "エチオピアコーヒー",
    "エチオピア",
    "コーヒー",
    "紅茶",
)


def install_relaymem_primary_recall_runtime() -> None:
    """Align scoped Primary recall with durable queue namespaces and E1 queries."""

    from . import relaymem_primary_recall as _primary_recall
    from . import relaymem_retrieval as _retrieval

    _primary_recall._TOKEN_RE = _TOKEN_WITH_SLASH_RE
    _retrieval._term_hints = _term_hints_with_japanese_recall_phrases


def _term_hints_with_japanese_recall_phrases(text: str) -> list[str]:
    terms: list[str] = []

    def add(term: str) -> None:
        term = term.strip(".,!?。！？、:;()[]{}\"'")[:32]
        if len(term) < 2 or term in terms:
            return
        terms.append(term)

    for raw in text.replace("\n", " ").split(" "):
        add(raw)
        if len(terms) >= 12:
            return terms[:12]

    for phrase in _JAPANESE_RECALL_PHRASES:
        if phrase in text:
            add(phrase)
            if len(terms) >= 12:
                break
    return terms[:12]
