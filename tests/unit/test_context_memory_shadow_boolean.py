from __future__ import annotations

import pytest

from relaylm.memory_provenance import MemoryTemporalScope

from .context_memory_shadow_support import memory_is_retained


@pytest.mark.parametrize(
    ("content", "heading", "scope", "retained"),
    [
        ("notifications_enabled: true", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("notifications_enabled: false", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("true", "Notifications Enabled", MemoryTemporalScope.UNKNOWN, True),
        ("false", "Notifications Enabled", MemoryTemporalScope.UNKNOWN, False),
        ("notifications_enabled: not true", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("notifications_enabled: not false", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("notifications_enabled: true\nnotifications_enabled: false", "Profile Notes", MemoryTemporalScope.UNKNOWN, False),
        ("notifications_enabled: true\nnotifications_enabled: true", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("Current notifications enabled is false.", "Profile Notes", MemoryTemporalScope.CURRENT, False),
        ("Current notifications enabled is false.", "Profile Notes", MemoryTemporalScope.UNKNOWN, True),
        ("Current notifications enabled is disabled.", "Profile Notes", MemoryTemporalScope.CURRENT, True),
        ("Previous current notifications enabled is false.", "Profile Notes", MemoryTemporalScope.CURRENT, True),
    ],
    ids=[
        "inline-match",
        "inline-mismatch",
        "heading-match",
        "heading-mismatch",
        "inline-negates-current",
        "inline-negates-opposite",
        "multiple-inline-any-mismatch",
        "multiple-inline-all-match",
        "typed-current-freeform-mismatch",
        "unknown-freeform-has-no-authority",
        "nonliteral-freeform-is-uninterpreted",
        "prefixed-freeform-is-outside-grammar",
    ],
)
def test_boolean_memory_shadow_boundaries(
    content: str,
    heading: str,
    scope: MemoryTemporalScope,
    retained: bool,
) -> None:
    assert memory_is_retained(
        content=content,
        heading=heading,
        scope=scope,
        key="notifications_enabled",
        value=True,
    ) is retained
