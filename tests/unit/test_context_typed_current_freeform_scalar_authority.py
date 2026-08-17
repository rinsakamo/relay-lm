from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
)
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _current_event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-17T16:22:00+00:00",
    )


def _state(*, key: str = "residence_location", value: object = "Fukuoka") -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="current-state",
                state_class="user.fact",
                key=key,
                value=value,
                sources=("source-event",),
            ),
        )
    )


def _authority(scope: MemoryTemporalScope) -> MemoryTemporalAuthority:
    if scope is MemoryTemporalScope.UNKNOWN:
        return MemoryTemporalAuthority(temporal_scope=scope)
    return MemoryTemporalAuthority(
        temporal_scope=scope,
        provenance=MemoryProvenance(
            memory_id=f"memory-freeform-{scope.value}",
            derivation_id=f"derivation-freeform-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(content: str, *, scope: MemoryTemporalScope) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/profile-notes-{scope.value}",
        content=f"## Profile Notes\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_typed_current_freeform_canonical_key_conflict_is_suppressed() -> None:
    stale = _chunk(
        "Current residence location is Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=stale)

    assert compiled.memory == ()


def test_typed_current_freeform_canonical_key_match_is_retained() -> None:
    current = _chunk(
        "The residence location is currently Fukuoka.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_typed_current_now_form_conflict_is_suppressed() -> None:
    stale = _chunk(
        "Preferred beverage is now tea.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(
        chunk=stale,
        state=_state(key="preferred_beverage", value="coffee"),
    )

    assert compiled.memory == ()


def test_unknown_current_wording_does_not_gain_freeform_authority() -> None:
    unknown = _chunk(
        "Current residence location is Hokkaido.",
        scope=MemoryTemporalScope.UNKNOWN,
    )

    compiled = _compile(chunk=unknown)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_historical_current_wording_remains_retained_by_c5() -> None:
    historical = _chunk(
        "Current residence location is Hokkaido.",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_prefixed_current_phrase_remains_outside_bounded_freeform_grammar() -> None:
    ambiguous = _chunk(
        "Previous current residence location is Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=ambiguous)

    assert [item.location for item in compiled.memory] == [ambiguous.location]


def test_typed_current_prose_without_canonical_key_is_not_semantically_inferred() -> None:
    unaddressed = _chunk(
        "Rin currently lives in Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=unaddressed)

    assert [item.location for item in compiled.memory] == [unaddressed.location]


def test_typed_current_freeform_boolean_claim_is_not_expanded_by_scalar_c6() -> None:
    boolean_claim = _chunk(
        "Current notifications enabled is false.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(
        chunk=boolean_claim,
        state=_state(key="notifications_enabled", value=True),
    )

    assert [item.location for item in compiled.memory] == [boolean_claim.location]
