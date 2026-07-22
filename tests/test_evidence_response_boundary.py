"""Behavioral regressions for EV-1 fail-closed request/response boundaries."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

import relaylm.managed_chat_response as managed_chat_response
import relaylm.managed_chat_runtime as managed_chat_runtime
from relaylm.app import create_app
from evidence_test_support import route_snapshot
from relaylm.evidence_response_capture import (
    EvidenceResponseCaptureResult,
    wrap_stream_with_evidence_response_capture,
)
from relaylm.pipeline_node_result import build_pipeline_node_result

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_URL = f"{BACKEND_BASE_URL}/chat/completions"
BACKEND_RESPONSE = {
    "id": "chatcmpl-evidence-boundary",
    "object": "chat.completion",
    "created": 1,
    "model": "local-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "visible answer"},
            "finish_reason": "stop",
        }
    ],
}


def _write_config(
    tmp_path: Path,
    *,
    evidence_apply: bool = False,
    invalid_durable_gate: bool = False,
) -> Path:
    evidence_root = tmp_path / "evidence"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
backends:
  local_backend:
    base_url: {BACKEND_BASE_URL}
    api_key: dummy
    default_model: local-model
model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    mode: memory_light
    character_id: char1
    memory_namespace: ns1
    user_id: user1
    session_id: sess1
evidence_capture_enabled: {str(evidence_apply).lower()}
evidence_capture_dry_run_only: {str(not evidence_apply).lower()}
evidence_capture_apply_enabled: {str(evidence_apply).lower()}
evidence_data_root: {evidence_root}
relaymem_slp_durable_finalization_enabled: {str(invalid_durable_gate).lower()}
relaymem_slp_durable_finalization_dry_run_only: true
relaymem_slp_durable_finalization_apply_enabled: {str(invalid_durable_gate).lower()}
""".strip(),
        encoding="utf-8",
    )
    return config_path


def _request() -> dict[str, object]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_apply_user_capture_failure_stops_before_backend(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path, evidence_apply=True)
    client = TestClient(create_app(str(config_path)))
    monkeypatch.setattr(
        managed_chat_runtime,
        "capture_evidence_for_user_input",
        lambda **_: build_pipeline_node_result(
            node_name="evidence_user_input_capture",
            status="failed",
            decision="integrity_conflict",
            blocked_reasons=("forced_user_capture_failure",),
        ),
    )
    with respx.mock(assert_all_called=False) as mock:
        backend = mock.post(BACKEND_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_request())
    assert response.status_code == 500
    assert response.json()["error"]["type"] == "evidence_capture_error"
    assert backend.call_count == 0


def test_apply_assistant_capture_failure_replaces_visible_body(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path, evidence_apply=True)
    client = TestClient(create_app(str(config_path)))
    monkeypatch.setattr(
        managed_chat_response,
        "capture_evidence_for_assistant_response_nonstream",
        lambda **_: build_pipeline_node_result(
            node_name="evidence_assistant_response_capture",
            status="failed",
            decision="integrity_conflict",
            blocked_reasons=("forced_assistant_capture_failure",),
        ),
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_request())
    assert response.status_code == 500
    assert response.json()["error"]["type"] == "evidence_finalization_error"
    assert "visible answer" not in response.text


def test_durable_gate_rejection_happens_before_nonstream_evidence_capture(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path, invalid_durable_gate=True)
    client = TestClient(create_app(str(config_path)))
    capture_calls: list[object] = []
    monkeypatch.setattr(
        managed_chat_response,
        "capture_evidence_for_assistant_response_nonstream",
        lambda **kwargs: capture_calls.append(kwargs),
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_request())
    assert response.status_code == 500
    assert capture_calls == []


def test_stream_reservation_failure_never_degrades_to_pass_through() -> None:
    finalized: list[EvidenceResponseCaptureResult] = []

    async def source():
        yield b'data: {"choices":[{"delta":{"content":"must-not-pass"}}]}\n\n'

    async def consume() -> list[bytes]:
        wrapped = wrap_stream_with_evidence_response_capture(
            source(),
            store=None,
            apply_enabled=True,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="response-1",
            delivery_cohort_id="cohort-1",
            request_source_event_ids=(),
            operation_idempotency_key="request-1:assistant_response",
            route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response"),
            on_finalized=finalized.append,
        )
        return [chunk async for chunk in wrapped]

    assert asyncio.run(consume()) == []
    assert len(finalized) == 1
    assert finalized[0].status == "fail_closed"
    assert finalized[0].blocked_reasons == ("evidence_stream_apply_requires_recovery_support",)
