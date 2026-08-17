from __future__ import annotations

import pytest

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
        payload={"content": "Are notifications enabled?"},
        event_id="current-event",
        timestamp="2026-08-18T07:48:00+09:00",
    )


def _state(value: bool) -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="notifications-current",
                state_class="user.fact",
                key="notifications_enabled",
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
            memory_id=f"memory-heading-boolean-{scope.value}",
            derivation_id=f"derivation-heading-boolean-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    body: str,
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    heading: str = "Notifications Enabled",
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/heading-boolean-{scope.value}",
        content=f"## {heading}\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk, *, value: bool):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(value),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


@pytest.mark.parametrize(
    ("state_value", "body", "retained"),
    [
        (True, "true", True),
        (True, "false", False),
        (True, "not true", False),
        (True, "not false", True),
        (False, "false", True),
        (False, "true", False),
        (False, "not false", False),
        (False, "not true", True),
    ],
)
def test_single_heading_body_uses_exact_boolean_value(
    state_value: bool,
    body: str,
    retained: bool,
) -> None:
    chunk = _chunk(body)

    compiled = _compile(chunk, value=state_value)

    assert bool(compiled.memory) is retained


def test_typed_current_uses_same_structural_heading_boolean_rule() -> None:
    compatible = _chunk("not false", scope=MemoryTemporalScope.CURRENT)

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_heading_boolean_negation_remains_exempt() -> None:
    historical = _chunk("not true", scope=MemoryTemporalScope.HISTORICAL)

    compiled = _compile(historical, value=True)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_multiple_nonempty_body_lines_remain_outside_c14() -> None:
    deferred = _chunk("not false\ntrue")

    compiled = _compile(deferred, value=True)

    assert [item.location for item in compiled.memory] == [deferred.location]


def test_heading_plus_inline_assignment_remains_outside_c14() -> None:
    deferred = _chunk("not false\nnotifications_enabled: false")

    assert _compile(deferred, value=True).memory == ()


@pytest.mark.parametrize(
    "body",
    [
        "disabled",
        "not not true",
        "not true or false",
        "never true",
    ],
)
def test_nonexact_heading_boolean_values_fall_through_existing_rule(body: str) -> None:
    chunk = _chunk(body)

    compiled = _compile(chunk, value=True)

    assert [item.location for item in compiled.memory] == [chunk.location]
