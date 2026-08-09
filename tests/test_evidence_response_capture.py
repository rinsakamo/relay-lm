"""Acceptance-matrix tests for managed assistant-response capture (EV-1)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.response_session import prepare_response_capture
from evidence_test_support import route_snapshot
from relaylm.evidence.response_capture import (
    capture_managed_assistant_response_nonstream,
    wrap_stream_with_evidence_response_capture,
)

NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path) -> EvidenceRecordStore:
    return EvidenceRecordStore(str(tmp_path / "evidence"))


def _nonstream(store, *, text="hi there!", key="resp-1", apply_enabled=True, now=NOW):
    return capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=apply_enabled,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="resp-id-1",
        delivery_cohort_id="cohort-1",
        request_source_event_ids=(),
        assistant_visible_text=text,
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response", issued_at=now.isoformat()),
        now=now,
    )


def test_nonstream_admits_one_assistant_origin_source_event(store) -> None:
    result = _nonstream(store)
    assert result.status == "admitted"
    record = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_event",
        record_id=result.source_event_id,
    )
    assert record["origin_kind"] == "assistant"
    assert record["source_role"] == "assistant_response"
    assert record["source_replay_identity"]["kind"] == "managed_response_identity"


def test_nonstream_no_output_creates_no_source_event(store) -> None:
    result = _nonstream(store, text=None, key="resp-empty")
    assert result.status == "terminal_no_output"
    assert result.source_event_id is None


def test_nonstream_duplicate_retry_is_idempotent(store) -> None:
    first = _nonstream(store)
    second = _nonstream(store)
    assert first.source_event_id == second.source_event_id
    assert second.status == "admitted"


def test_nonstream_conflicting_retry_is_integrity_failure(store) -> None:
    first = _nonstream(store)
    conflicting = _nonstream(store, text="a totally different reply")
    assert conflicting.status == "integrity_conflict"
    assert conflicting.source_event_id == first.source_event_id


async def _drain(store, chunks, *, key, on_finalized):
    async def gen():
        for chunk in chunks:
            yield chunk

    wrapped = wrap_stream_with_evidence_response_capture(
        gen(),
        store=store,
        apply_enabled=False,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="resp-stream",
        delivery_cohort_id="cohort-stream",
        request_source_event_ids=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response"),
        on_finalized=on_finalized,
    )
    return [chunk async for chunk in wrapped]


def test_stream_uses_one_sequence_per_delivery_cohort_not_per_chunk(store) -> None:
    chunks = [
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
        b'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    results = []
    drained = asyncio.run(
        _drain(store, chunks, key="resp-cohort", on_finalized=results.append)
    )
    assert drained == chunks
    assert len(results) == 1
    assert results[0].status == "dry_run_ready"


def test_stream_captures_only_canonical_accepted_visible_ranges(store) -> None:
    chunks = [
        b'data: {"choices":[{"delta":{"content":"Safe text"},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    results = []
    assert asyncio.run(
        _drain(store, chunks, key="resp-safe", on_finalized=results.append)
    ) == chunks
    assert results[0].status == "dry_run_ready"
    assert not any(store.root.rglob("sourceevent_*.json"))


def test_stream_cancellation_finalizes_proven_partial_range(store) -> None:
    async def gen_cancel():
        yield b'data: {"choices":[{"delta":{"content":"Partial"}}]}\n\n'
        raise asyncio.CancelledError()

    results = []

    async def run():
        wrapped = wrap_stream_with_evidence_response_capture(
            gen_cancel(),
            store=store,
            apply_enabled=False,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="resp-cancel",
            delivery_cohort_id="cohort-cancel",
            request_source_event_ids=(),
            operation_idempotency_key="resp-cancel-key",
            route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response"),
            on_finalized=results.append,
        )
        with pytest.raises(asyncio.CancelledError):
            async for _ in wrapped:
                pass

    asyncio.run(run())
    assert len(results) == 1
    assert results[0].status == "dry_run_ready"


def test_stream_backend_error_finalizes_without_crashing(store) -> None:
    async def gen_error():
        yield b'data: {"choices":[{"delta":{"content":"before error"}}]}\n\n'
        raise RuntimeError("backend exploded")

    results = []

    async def run():
        wrapped = wrap_stream_with_evidence_response_capture(
            gen_error(),
            store=store,
            apply_enabled=False,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="resp-error",
            delivery_cohort_id="cohort-error",
            request_source_event_ids=(),
            operation_idempotency_key="resp-error-key",
            route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response"),
            on_finalized=results.append,
        )
        with pytest.raises(RuntimeError):
            async for _ in wrapped:
                pass

    asyncio.run(run())
    assert len(results) == 1
    assert results[0].status == "dry_run_ready"


def test_stream_empty_output_is_terminal_no_output(store) -> None:
    results = []
    asyncio.run(
        _drain(store, [b"data: [DONE]\n\n"], key="resp-empty-stream", on_finalized=results.append)
    )
    assert results[0].status == "terminal_no_output"


def test_stream_first_chunk_is_not_blocked_by_capture(store) -> None:
    # The wrapper yields the first chunk *before* any admission work runs
    # (finalization only happens in the generator's ``finally`` at the end).
    order: list[str] = []

    async def gen():
        order.append("chunk_yielded")
        yield b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    def on_finalized(_result):
        order.append("finalized")

    async def run():
        wrapped = wrap_stream_with_evidence_response_capture(
            gen(),
            store=store,
            apply_enabled=False,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="resp-order",
            delivery_cohort_id="cohort-order",
            request_source_event_ids=(),
            operation_idempotency_key="resp-order-key",
            route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response"),
            on_finalized=on_finalized,
        )
        async for _ in wrapped:
            order.append("chunk_received")

    asyncio.run(run())
    # The essential R-1 guarantee: finalization (admission/governance/persist)
    # never runs before the first chunk has already been handed to the
    # consumer -- it only happens once, in the generator's ``finally``, after
    # every chunk has been yielded.
    assert order[0] == "chunk_yielded"
    assert order[1] == "chunk_received"
    assert order[-1] == "finalized"
    assert order.count("finalized") == 1


def test_hidden_reasoning_fields_are_never_present_in_diagnostics(store) -> None:
    chunks = [
        b'data: {"choices":[{"delta":{"content":"visible","reasoning_content":"HIDDEN"},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    results = []
    asyncio.run(_drain(store, chunks, key="resp-hidden", on_finalized=results.append))
    assert results[0].status == "dry_run_ready"
    assert "HIDDEN" not in str(results[0].to_log_dict())


def test_nonstream_retry_finalizes_restored_observation_without_duplication(store) -> None:
    key = "resp-recovery-idempotent"
    prepared, reasons = prepare_response_capture(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="resp-id-1",
        delivery_cohort_id="cohort-1",
        request_source_event_ids=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response", issued_at=NOW.isoformat()
        ),
        now=NOW,
    )
    assert prepared is not None and not reasons
    ok, observe_reasons = prepared.observe("hi", NOW.isoformat())
    assert ok and not observe_reasons

    result = _nonstream(store, text="hi", key=key, now=NOW)
    assert result.status == "admitted"
    events = store.read_log(
        evidence_space_id=result.evidence_space_id,
        log_kind="response_capture",
        key=prepared.response_capture_reservation_id,
    )
    assert sum(event.get("operation") == "output_observed" for event in events) == 1
