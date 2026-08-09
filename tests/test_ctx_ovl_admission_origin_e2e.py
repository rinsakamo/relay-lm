from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.context_overlay.runtime import _registries, reset_ctx_ovl_runtime_cache

_BACKEND_URL = "http://127.0.0.1:8000/v1/chat/completions"


def _config(tmp_path: Path, evidence_root: Path) -> Path:
    payload = {
        "backends": {
            "local": {
                "type": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
                "api_key": "dummy",
                "default_model": "local-model",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local",
                "backend_model": "local-model",
                "mode": "memory_light",
                "character_id": "char1",
                "memory_namespace": "ns1",
                "user_id": "user1",
                "session_id": "sess1",
            }
        },
        "evidence_capture_enabled": True,
        "evidence_capture_dry_run_only": False,
        "evidence_capture_apply_enabled": True,
        "evidence_data_root": str(evidence_root),
        "ctx_ovl_enabled": True,
        "ctx_ovl_dry_run_only": False,
        "ctx_ovl_apply_enabled": True,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _request(text: str) -> dict[str, object]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": text}],
    }


def _mock_backend(request: httpx.Request) -> httpx.Response:
    json.loads(request.content.decode("utf-8"))
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-origin",
            "object": "chat.completion",
            "created": 1,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


def _only_state():
    assert len(_registries) == 1
    registry = next(iter(_registries.values()))
    assert len(registry.partitions) == 1
    return next(iter(registry.partitions.values()))


def test_normal_current_source_and_restart_rebuild_have_distinct_origins(
    tmp_path: Path,
) -> None:
    reset_ctx_ovl_runtime_cache()
    evidence_root = tmp_path / "evidence"
    config_path = _config(tmp_path, evidence_root)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(_BACKEND_URL).mock(side_effect=_mock_backend)
        first_client = TestClient(create_app(str(config_path)))
        first = first_client.post(
            "/v1/chat/completions", json=_request("normal source")
        )
    assert first.status_code == 200
    first_state = _only_state()
    assert len(first_state.overlays_by_source) == 1
    first_overlay = next(iter(first_state.overlays_by_source.values()))
    assert first_overlay.record["admission_origin"] == "normal_pipeline"
    assert first_state.sync_events == []

    reset_ctx_ovl_runtime_cache()
    with respx.mock(assert_all_called=False) as mock:
        mock.post(_BACKEND_URL).mock(side_effect=_mock_backend)
        restarted_client = TestClient(create_app(str(config_path)))
        second = restarted_client.post(
            "/v1/chat/completions", json=_request("new source after restart")
        )
    assert second.status_code == 200

    restarted_state = _only_state()
    origins = {
        item.text: item.record["admission_origin"]
        for item in restarted_state.overlays_by_source.values()
    }
    assert origins["normal source"] == "rebuild_pipeline"
    assert origins["new source after restart"] == "normal_pipeline"
    assert any(
        event.get("schema") == "relaylm.ctx_ovl_rebuild_event.v1"
        for event in restarted_state.sync_events
    )
