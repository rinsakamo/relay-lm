from __future__ import annotations

import pytest

from relaylm.memory_provenance import MemoryTemporalScope

from context_memory_shadow_support import memory_is_retained


_DEGREE_STATE = {"semantic": "likes", "degree_hint": 0.85}


@pytest.mark.parametrize(
    ("content", "heading", "scope", "retained"),
    [
        ("tea: likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: dislikes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: likes; degree_hint: 0.65", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: not likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: not dislikes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: not likes; degree_hint: 0.65", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: likes; degree_hint: 0.85\ntea: likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: likes; degree_hint: 0.85\ntea: dislikes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: not dislikes; degree_hint: 0.85\ntea: not likes; degree_hint: 0.65", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: not dislikes; degree_hint: 0.85\ntea: not likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: likes; degree_hint: 0.85\ntea: not dislikes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: dislikes; degree_hint: 0.85\ntea: not avoids; degree_hint: 0.65", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("tea: likes; degree_hint: 0.85\ntea: not likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("not likes; degree_hint: 0.85", "Tea", MemoryTemporalScope.UNKNOWN, False),
        ("not dislikes; degree_hint: 0.85", "Tea", MemoryTemporalScope.UNKNOWN, True),
        ("likes; degree_hint: 0.65\ncontext note", "Tea", MemoryTemporalScope.UNKNOWN, False),
        ("likes; degree_hint: 0.85\ncontext note", "Tea", MemoryTemporalScope.UNKNOWN, True),
        ("Rin likes tea.\ndegree_hint: 0.65", "Tea", MemoryTemporalScope.UNKNOWN, False),
        ("Rin likes tea.\ndegree_hint: 0.85", "Tea", MemoryTemporalScope.UNKNOWN, True),
        ("Rin likes tea.", "Tea", MemoryTemporalScope.UNKNOWN, True),
        ("Rin dislikes tea.\ndegree_hint: 0.85", "Tea", MemoryTemporalScope.UNKNOWN, False),
        ("tea: likes\ncoffee: likes; degree_hint: 0.65", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("Current tea is likes; degree_hint: 0.65.", "Profile Notes", MemoryTemporalScope.CURRENT, False),
        ("Current tea is not likes; degree_hint: 0.85.", "Profile Notes", MemoryTemporalScope.CURRENT, False),
        ("Current tea is not dislikes; degree_hint: 0.85.", "Profile Notes", MemoryTemporalScope.CURRENT, True),
        ("Current tea is likes; degree_hint: 0.65.", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("tea: not not likes; degree_hint: 0.85", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
    ],
    ids=[
        "inline-match",
        "inline-semantic-mismatch",
        "inline-degree-mismatch",
        "inline-negates-active-pair",
        "inline-negates-other-semantic",
        "inline-negates-other-degree",
        "multiple-positive-all-match",
        "multiple-positive-any-mismatch",
        "multiple-negated-all-compatible",
        "multiple-negated-active-pair",
        "mixed-compatible",
        "mixed-positive-mismatch",
        "mixed-active-negation",
        "heading-negates-active-pair",
        "heading-negates-other-pair",
        "heading-multiline-local-degree-mismatch",
        "heading-multiline-local-pair-match",
        "heading-fallback-degree-mismatch",
        "heading-fallback-degree-match",
        "heading-fallback-missing-degree",
        "heading-fallback-semantic-mismatch",
        "inline-does-not-borrow-unrelated-degree",
        "typed-current-freeform-degree-mismatch",
        "typed-current-freeform-negates-active-pair",
        "typed-current-freeform-negates-other-pair",
        "unknown-freeform-has-no-authority",
        "double-negation-remains-uninterpreted",
    ],
)
def test_reserved_degree_memory_shadow_boundaries(
    content: str,
    heading: str,
    scope: MemoryTemporalScope,
    retained: bool,
) -> None:
    assert memory_is_retained(
        content=content,
        heading=heading,
        scope=scope,
        key="tea",
        value=_DEGREE_STATE,
        state_class="user.preference",
    ) is retained
