from __future__ import annotations

import pytest

from relaylm.memory_provenance import MemoryTemporalScope

from .context_memory_shadow_support import memory_is_retained


@pytest.mark.parametrize(
    ("content", "heading", "scope", "key", "value", "retained"),
    [
        ("residence_location: Fukuoka", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", True),
        ("residence_location: Hokkaido", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("residence_location: not Fukuoka", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("residence_location: not Hokkaido", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", True),
        ("not Fukuoka", "Residence Location", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("not Hokkaido", "Residence Location", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", True),
        ("residence_location: Hokkaido", "Residence Location", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("residence_location: Fukuoka\nresidence_location: Hokkaido", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("residence_location: Fukuoka\nresidence_location: Fukuoka", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", True),
        ("Current residence location is Hokkaido.", "Profile Notes", MemoryTemporalScope.CURRENT, "residence_location", "Fukuoka", False),
        ("Current residence location is Hokkaido.", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", True),
        ("Previous current residence location is Hokkaido.", "Profile Notes", MemoryTemporalScope.CURRENT, "residence_location", "Fukuoka", True),
        ("residence_location: notFukuoka", "Profile Notes", MemoryTemporalScope.UNKNOWN, "residence_location", "Fukuoka", False),
        ("lucky_number: not 5", "Profile Notes", MemoryTemporalScope.UNKNOWN, "lucky_number", 5, False),
        ("lucky_number: not 7", "Profile Notes", MemoryTemporalScope.UNKNOWN, "lucky_number", 5, True),
    ],
    ids=[
        "inline-match",
        "inline-mismatch",
        "inline-negates-current",
        "inline-negates-other",
        "heading-negates-current",
        "heading-negates-other",
        "heading-inline-local-mismatch",
        "multiple-inline-any-mismatch",
        "multiple-inline-all-match",
        "typed-current-freeform-mismatch",
        "unknown-freeform-has-no-authority",
        "prefixed-freeform-is-outside-grammar",
        "not-prefix-without-token-boundary",
        "numeric-negates-current",
        "numeric-negates-other",
    ],
)
def test_scalar_memory_shadow_boundaries(
    content: str,
    heading: str,
    scope: MemoryTemporalScope,
    key: str,
    value: object,
    retained: bool,
) -> None:
    assert memory_is_retained(
        content=content,
        heading=heading,
        scope=scope,
        key=key,
        value=value,
    ) is retained
