from __future__ import annotations

import pytest

from relaylm.memory_provenance import MemoryTemporalScope
from relaylm.memory_retrieval import select_memory_chunks


def _metadata(
    *,
    temporal_scope: str,
    memory_id: str = "memory-preferred-beverage",
    derivation_id: str = "derivation-2026-08-18-a",
    source_kind: str = "state",
    reference_id: str = "state-preferred-beverage",
    version: str = "v1",
) -> str:
    return (
        f'<!-- relaylm-memory:{version} '
        f'{{"memory_id":"{memory_id}",'
        f'"derivation_id":"{derivation_id}",'
        f'"temporal_scope":"{temporal_scope}",'
        f'"sources":[{{"kind":"{source_kind}",'
        f'"reference_id":"{reference_id}"}}]}} -->'
    )


def test_valid_current_metadata_is_typed_and_preserved_on_memory_chunk() -> None:
    markdown = f"""# Preferences

{_metadata(temporal_scope="current")}
Rin prefers coffee.
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=1,
        max_chars=1000,
    )

    authority = chunk.temporal_authority
    assert authority.temporal_scope is MemoryTemporalScope.CURRENT
    assert authority.provenance is not None
    assert authority.provenance.memory_id == "memory-preferred-beverage"
    assert authority.provenance.derivation_id == "derivation-2026-08-18-a"
    assert authority.provenance.sources[0].kind.value == "state"
    assert authority.provenance.sources[0].reference_id == "state-preferred-beverage"
    assert "relaylm-memory" not in chunk.content
    assert "Rin prefers coffee." in chunk.content


def test_valid_historical_event_metadata_is_preserved_without_pseudo_event_identity() -> None:
    markdown = f"""# Travel

{_metadata(
        temporal_scope="historical",
        memory_id="memory-former-home",
        derivation_id="derivation-2026-08-18-b",
        source_kind="event",
        reference_id="event-user-moved-fukuoka",
    )}
Rin once lived in Hokkaido.
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="Hokkaido",
        max_chunks=1,
        max_chars=1000,
    )

    authority = chunk.temporal_authority
    assert authority.temporal_scope is MemoryTemporalScope.HISTORICAL
    assert authority.provenance is not None
    assert authority.provenance.sources[0].kind.value == "event"
    assert authority.provenance.sources[0].reference_id == "event-user-moved-fukuoka"


def test_unannotated_temporal_prose_remains_unknown() -> None:
    markdown = """# Residence history

Previously, in 2024, Rin lived in Hokkaido. Rin formerly called it home and now lives elsewhere.
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="Hokkaido",
        max_chunks=1,
        max_chars=1000,
    )

    assert chunk.temporal_authority.temporal_scope is MemoryTemporalScope.UNKNOWN
    assert chunk.temporal_authority.provenance is None


@pytest.mark.parametrize(
    "metadata_line",
    [
        '<!-- relaylm-memory:v1 {"memory_id":"broken"} -->',
        _metadata(temporal_scope="formerly"),
        _metadata(temporal_scope="current", source_kind="markdown"),
        _metadata(temporal_scope="current", version="v2"),
        '<!-- relaylm-memory:v1 {not-json} -->',
    ],
)
def test_malformed_or_unsupported_reserved_metadata_fails_closed_to_unknown(
    metadata_line: str,
) -> None:
    markdown = f"""# Preference

{metadata_line}
Rin prefers coffee.
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=1,
        max_chars=1000,
    )

    assert chunk.temporal_authority.temporal_scope is MemoryTemporalScope.UNKNOWN
    assert chunk.temporal_authority.provenance is None
    assert "relaylm-memory" not in chunk.content


def test_reserved_metadata_never_contributes_lexical_relevance() -> None:
    markdown = f"""# Preference

{_metadata(
        temporal_scope="current",
        memory_id="memory-secretneedle",
        derivation_id="derivation-secretneedle",
        reference_id="state-secretneedle",
    )}
Rin prefers coffee.
"""

    assert select_memory_chunks(
        memory_markdown=markdown,
        query="secretneedle",
        max_chunks=1,
        max_chars=1000,
    ) == ()

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=1,
        max_chars=1000,
    )
    assert chunk.temporal_authority.temporal_scope is MemoryTemporalScope.CURRENT


def test_metadata_must_be_first_nonblank_section_body_line() -> None:
    markdown = f"""# Preference

Rin prefers coffee.
{_metadata(temporal_scope="current")}
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=1,
        max_chars=1000,
    )

    assert chunk.temporal_authority.temporal_scope is MemoryTemporalScope.UNKNOWN
    assert chunk.temporal_authority.provenance is None
    assert "relaylm-memory" not in chunk.content


def test_reserved_metadata_inside_code_fence_is_plain_memory_content_not_authority() -> None:
    markdown = f"""# Notes

```text
{_metadata(temporal_scope="current")}
```
The example is about coffee.
"""

    (chunk,) = select_memory_chunks(
        memory_markdown=markdown,
        query="coffee",
        max_chunks=1,
        max_chars=2000,
    )

    assert chunk.temporal_authority.temporal_scope is MemoryTemporalScope.UNKNOWN
    assert chunk.temporal_authority.provenance is None
    assert "relaylm-memory:v1" in chunk.content
