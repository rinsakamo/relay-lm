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
        timestamp="2026-08-18T06:35:00+09:00",
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
            memory_id=f"memory-negation-{scope.value}",
            derivation_id=f"derivation-negation-{scope.value}",
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
        location=f"memory/MEMORY.md#memory/negation-{scope.value}",
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


def test_exact_negation_of_current_scalar_is_suppressed() -> None:
    stale = _chunk(
        "Current residence location is not Fukuoka.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(chunk=stale).memory == ()


def test_negation_of_different_scalar_is_retained() -> None:
    compatible = _chunk(
        "Current residence location is not Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_key_first_negation_of_different_scalar_is_retained() -> None:
    compatible = _chunk(
        "The residence location is currently not Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_numeric_negation_of_different_scalar_is_retained() -> None:
    compatible = _chunk(
        "Current lucky number is not 7.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(
        chunk=compatible,
        state=_state(key="lucky_number", value=5),
    )

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_numeric_negation_of_current_scalar_is_suppressed() -> None:
    stale = _chunk(
        "Current lucky number is not 5.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert (
        _compile(chunk=stale, state=_state(key="lucky_number", value=5)).memory
        == ()
    )


def test_positive_scalar_mismatch_remains_suppressed_by_c6() -> None:
    stale = _chunk(
        "Current residence location is Hokkaido.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(chunk=stale).memory == ()


def test_not_prefix_without_token_boundary_remains_positive_mismatch() -> None:
    stale = _chunk(
        "Current residence location is notFukuoka.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(chunk=stale).memory == ()


def test_boolean_negation_remains_outside_c9() -> None:
    boolean_claim = _chunk(
        "Current notifications enabled is not true.",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(
        chunk=boolean_claim,
        state=_state(key="notifications_enabled", value=True),
    )

    assert [item.location for item in compiled.memory] == [boolean_claim.location]


def test_unknown_scope_does_not_gain_scalar_negation_authority() -> None:
    unknown = _chunk(
        "Current residence location is not Fukuoka.",
        scope=MemoryTemporalScope.UNKNOWN,
    )

    compiled = _compile(chunk=unknown)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_historical_scope_remains_retained() -> None:
    historical = _chunk(
        "Current residence location is not Fukuoka.",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]
