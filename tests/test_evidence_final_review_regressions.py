"""Regression coverage for PR #629 final-review findings."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx

import relaylm.evidence_response_capture as response_capture_module
from relaylm.evidence_response_capture import (
    capture_managed_assistant_response_nonstream,
    wrap_stream_with_evidence_response_capture,
)
from relaylm.evidence_store import EvidenceRecordStore
from evidence_test_support import route_snapshot
from test_evidence_runtime_e2e import (
    BACKEND_CHAT_COMPLETIONS_URL,
    _chat_request,
    _client,
    _write_config,
)


class _TrackingAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self._chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def test_nonstream_backend_error_is_preserved_without_assistant_evidence(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_enabled=True,
        evidence_dry_run_only=False,
        evidence_apply_enabled=True,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    backend_body = {
        "error": {
            "message": "backend rate limit",
            "type": "rate_limit_error",
        }
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(429, json=backend_body)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 429
    assert response.json() == backend_body
    source_files = list(evidence_root.rglob("records/source_event/*.json"))
    assert len(source_files) == 1
    source = json.loads(source_files[0].read_text(encoding="utf-8"))
    assert source["origin_kind"] == "participant"


def test_stream_apply_rejection_closes_open_backend_stream(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_enabled=True,
        evidence_dry_run_only=False,
        evidence_apply_enabled=True,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    backend_stream = _TrackingAsyncByteStream(
        (
            b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n',
            b"data: [DONE]\n\n",
        )
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                stream=backend_stream,
                headers={"content-type": "text/event-stream"},
            )
        )
        response = client.post(
            "/v1/chat/completions", json=_chat_request(stream=True)
        )

    assert response.status_code == 500
    assert backend_stream.closed is True


def test_dry_run_stream_bounds_incomplete_sse_frame_without_altering_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        response_capture_module, "_MAX_PENDING_SSE_FRAME_BYTES", 32
    )
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    chunks = (b"x" * 64, b"data: [DONE]\n\n")
    results = []

    async def source():
        for chunk in chunks:
            yield chunk

    async def drain():
        wrapped = wrap_stream_with_evidence_response_capture(
            source(),
            store=store,
            apply_enabled=False,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="response-buffer-bound",
            delivery_cohort_id="cohort-buffer-bound",
            request_source_event_ids=(),
            operation_idempotency_key="buffer-bound",
            route_snapshot_payload=route_snapshot(
                capture_profile="managed_assistant_response"
            ),
            on_finalized=results.append,
        )
        return tuple([chunk async for chunk in wrapped])

    assert asyncio.run(drain()) == chunks
    assert len(results) == 1
    assert results[0].status == "fail_closed"
    assert (
        "assistant_stream_frame_buffer_limit_exceeded"
        in results[0].blocked_reasons
    )


def test_change_refs_and_assistant_projection_use_persisted_partition_keys(
    tmp_path: Path,
) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    results = []
    for index in range(2):
        result = capture_managed_assistant_response_nonstream(
            store=store,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id=f"response-{index}",
            delivery_cohort_id=f"cohort-{index}",
            request_source_event_ids=(),
            assistant_visible_text=f"answer {index}",
            operation_idempotency_key=f"assistant-{index}",
            route_snapshot_payload=route_snapshot(
                capture_profile="managed_assistant_response"
            ),
        )
        assert result.status == "admitted"
        results.append(result)

        source = store.read_record(
            evidence_space_id=result.evidence_space_id,
            record_kind="source_event",
            record_id=result.source_event_id,
        )
        change_set_id = source["authority_change_set_ref"]["change_set_id"]
        change_events = store.read_log(
            evidence_space_id=result.evidence_space_id,
            log_kind="change_set",
            key=change_set_id,
        )
        mutation_kinds = {
            ref["record_kind"]
            for ref in change_events[0]["operation_payload"][
                "authoritative_mutation_refs"
            ]
        }
        assert "governance_event" in mutation_kinds
        assert "evidence_governance_event" not in mutation_kinds

    space_root = store.root / results[0].evidence_space_id / "logs"
    projection_files = list((space_root / "change_projection").glob("*.json"))
    coverage_files = list(
        (space_root / "change_coverage_checkpoint").glob("*.json")
    )
    assert len(projection_files) == 1
    assert len(coverage_files) == 1
    assert projection_files[0].stem != "evidence_control"
    assert coverage_files[0].stem == projection_files[0].stem
    assert len(json.loads(projection_files[0].read_text(encoding="utf-8"))) == 2
    assert len(json.loads(coverage_files[0].read_text(encoding="utf-8"))) == 2


def test_store_rejects_existing_symlink_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "evidence-link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="evidence_store_root_unsafe"):
        EvidenceRecordStore(str(link))


def test_nonstream_raw_2xx_fails_closed_in_evidence_apply(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_enabled=True,
        evidence_dry_run_only=False,
        evidence_apply_enabled=True,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=b"successful but not a chat-completion JSON body",
                headers={"content-type": "text/plain"},
            )
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 500
    assert response.json()["error"]["type"] == "evidence_finalization_error"
    source_files = list(evidence_root.rglob("records/source_event/*.json"))
    assert len(source_files) == 1
    source = json.loads(source_files[0].read_text(encoding="utf-8"))
    assert source["origin_kind"] == "participant"
