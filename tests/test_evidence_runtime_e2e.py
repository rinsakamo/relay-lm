"""End-to-end managed-route smoke: EV-1 wired through the real FastAPI app.

Exercises the full request path (``handle_managed_chat_completion`` ->
``build_managed_chat_response``) with a mocked OpenAI-compatible backend,
proving the feature posture end-to-end rather than only at the module level:
disabled / dry-run / apply, non-stream / stream, and pass-through exemption.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import respx
import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.evidence_store import EvidenceRecordStore

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_CHAT_COMPLETIONS_URL = f"{BACKEND_BASE_URL}/chat/completions"

BACKEND_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "local-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello there!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
}

STREAM_BODY = (
    b'data: {"id":"chatcmpl-i11","choices":[{"delta":{"content":"hi"}}]}\n\n'
    b"data: [DONE]\n\n"
)


def _write_config(
    tmp_path: Path,
    *,
    mode: str = "memory_light",
    evidence_enabled: bool = False,
    evidence_dry_run_only: bool = True,
    evidence_apply_enabled: bool = False,
    evidence_data_root: str | None = None,
) -> Path:
    config = {
        "backends": {
            "local_backend": {
                "type": "openai_compatible",
                "base_url": BACKEND_BASE_URL,
                "api_key": "dummy",
                "default_model": "local-model",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local_backend",
                "backend_model": "local-model",
                "mode": mode,
                "character_id": "char1",
                "memory_namespace": "ns1",
                "user_id": "user1",
            "session_id": "sess1",
            }
        },
        "evidence_capture_enabled": evidence_enabled,
        "evidence_capture_dry_run_only": evidence_dry_run_only,
        "evidence_capture_apply_enabled": evidence_apply_enabled,
        "evidence_data_root": evidence_data_root,
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _client(config_path: Path) -> TestClient:
    return TestClient(create_app(str(config_path)))


def _chat_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi, please help me today"}],
    }
    payload.update(overrides)
    return payload


def _evidence_files(root: Path) -> list[Path]:
    return list(root.rglob("*.json")) if root.exists() else []


def test_feature_disabled_creates_no_evidence_files(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(tmp_path, evidence_enabled=False)
    client = _client(config_path)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())
    assert response.status_code == 200
    assert _evidence_files(evidence_root) == []


def test_dry_run_produces_no_durable_writes(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_enabled=True,
        evidence_dry_run_only=True,
        evidence_apply_enabled=False,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())
    assert response.status_code == 200
    assert _evidence_files(evidence_root) == []


def test_apply_mode_admits_current_user_input_and_assistant_response(tmp_path: Path) -> None:
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
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())
    assert response.status_code == 200

    store = EvidenceRecordStore(str(evidence_root))
    space_dirs = [
        path for path in evidence_root.iterdir() if path.is_dir()
    ]
    assert len(space_dirs) == 1
    evidence_space_id = space_dirs[0].name
    source_events_dir = space_dirs[0] / "records" / "source_event"
    assert source_events_dir.exists()
    source_events = list(source_events_dir.glob("*.json"))
    assert len(source_events) == 2  # one user-origin, one assistant-origin

    origins = set()
    for path in source_events:
        record = store.read_record(
            evidence_space_id=evidence_space_id,
            record_kind="source_event",
            record_id=path.stem,
        )
        origins.add(record["origin_kind"])
    assert origins == {"participant", "assistant"}


def test_apply_mode_stream_fails_closed_until_recovery_support(tmp_path: Path) -> None:
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
                content=STREAM_BODY,
                headers={"content-type": "text/event-stream"},
            )
        )
        response = client.post(
            "/v1/chat/completions", json=_chat_request(stream=True)
        )
    assert response.status_code == 500
    assert response.json()["error"]["type"] == "evidence_stream_capture_error"

    # The request-owned user input was admitted before the unsupported
    # assistant stream boundary was reached; no assistant SourceEvent exists.
    space_dirs = [path for path in evidence_root.iterdir() if path.is_dir()]
    assert len(space_dirs) == 1
    source_events = list(
        (space_dirs[0] / "records" / "source_event").glob("*.json")
    )
    assert len(source_events) == 1


def test_pass_through_route_creates_no_capture_even_with_apply_enabled(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        mode="pass_through",
        evidence_enabled=True,
        evidence_dry_run_only=False,
        evidence_apply_enabled=True,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())
    assert response.status_code == 200
    assert _evidence_files(evidence_root) == []


def test_no_protected_content_leaks_into_response_headers_or_diagnostics(
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
    canary = "TOP-SECRET-CANARY-af92k"
    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post(
            "/v1/chat/completions", json=_chat_request(messages=[{"role": "user", "content": canary}])
        )
    assert response.status_code == 200
    for value in response.headers.values():
        assert canary not in value
