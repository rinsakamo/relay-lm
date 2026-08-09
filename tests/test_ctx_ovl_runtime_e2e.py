"""OVL-1 through the real managed-chat API and EV-1 store."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
import yaml
from fastapi.testclient import TestClient
from respx.router import MockRouter

from relaylm.app import create_app
from relaylm.context_overlay.runtime import reset_ctx_ovl_runtime_cache

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_CHAT_COMPLETIONS_URL = f"{BACKEND_BASE_URL}/chat/completions"
_MARKER = "<relayctx_provisional_continuity>"


def _write_config(
    tmp_path: Path,
    *,
    evidence_root: Path,
    ctx_ovl_enabled: bool,
    ctx_ovl_dry_run_only: bool = True,
    ctx_ovl_apply_enabled: bool = False,
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
        "ctx_ovl_enabled": ctx_ovl_enabled,
        "ctx_ovl_dry_run_only": ctx_ovl_dry_run_only,
        "ctx_ovl_apply_enabled": ctx_ovl_apply_enabled,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _request(text: str) -> dict[str, object]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": text}],
    }


def _backend_response(index: int) -> dict[str, object]:
    return {
        "id": f"chatcmpl-ovl-{index}",
        "object": "chat.completion",
        "created": 1234567890 + index,
        "model": "local-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"assistant response {index}",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }


def _record_backend_payloads(
    mock: MockRouter,
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json=_backend_response(len(payloads)))

    mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(side_effect=handler)
    return payloads


def _continuity_messages(payload: dict[str, object]) -> list[str]:
    messages = payload.get("messages")
    assert isinstance(messages, list)
    return [
        str(message["content"])
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and _MARKER in message["content"]
    ]


def test_apply_uses_prior_user_evidence_but_never_self_injects_current_turn(
    tmp_path: Path,
) -> None:
    reset_ctx_ovl_runtime_cache()
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_root=evidence_root,
        ctx_ovl_enabled=True,
        ctx_ovl_dry_run_only=False,
        ctx_ovl_apply_enabled=True,
    )
    client = TestClient(create_app(str(config_path)))

    with respx.mock(assert_all_called=False) as mock:
        payloads = _record_backend_payloads(mock)
        first = client.post("/v1/chat/completions", json=_request("first private turn"))
        second = client.post("/v1/chat/completions", json=_request("second current turn"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(payloads) == 2
    assert _continuity_messages(payloads[0]) == []
    continuity = _continuity_messages(payloads[1])
    assert len(continuity) == 1
    assert "first private turn" in continuity[0]
    assert "second current turn" not in continuity[0]

    # CTX-OVL working state is process-local. EV-1 remains the only durable
    # authority below evidence_root.
    assert list(evidence_root.rglob("ctx_ovl*")) == []


def test_cache_loss_rebuilds_from_current_authorized_governed_evidence(
    tmp_path: Path,
) -> None:
    reset_ctx_ovl_runtime_cache()
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_root=evidence_root,
        ctx_ovl_enabled=True,
        ctx_ovl_dry_run_only=False,
        ctx_ovl_apply_enabled=True,
    )

    with respx.mock(assert_all_called=False) as mock:
        first_payloads = _record_backend_payloads(mock)
        first_client = TestClient(create_app(str(config_path)))
        first = first_client.post(
            "/v1/chat/completions", json=_request("rebuild source turn")
        )
    assert first.status_code == 200
    assert _continuity_messages(first_payloads[0]) == []

    reset_ctx_ovl_runtime_cache()
    with respx.mock(assert_all_called=False) as mock:
        second_payloads = _record_backend_payloads(mock)
        restarted_client = TestClient(create_app(str(config_path)))
        second = restarted_client.post(
            "/v1/chat/completions", json=_request("after process restart")
        )

    assert second.status_code == 200
    continuity = _continuity_messages(second_payloads[0])
    assert len(continuity) == 1
    assert "rebuild source turn" in continuity[0]
    assert "after process restart" not in continuity[0]


def test_default_off_and_dry_run_do_not_change_forwarded_messages(
    tmp_path: Path,
) -> None:
    for name, enabled, dry_run, apply in (
        ("disabled", False, True, False),
        ("dry-run", True, True, False),
    ):
        reset_ctx_ovl_runtime_cache()
        case_dir = tmp_path / name
        case_dir.mkdir()
        config_path = _write_config(
            case_dir,
            evidence_root=case_dir / "evidence",
            ctx_ovl_enabled=enabled,
            ctx_ovl_dry_run_only=dry_run,
            ctx_ovl_apply_enabled=apply,
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            payloads = _record_backend_payloads(mock)
            first = client.post("/v1/chat/completions", json=_request("one"))
            second = client.post("/v1/chat/completions", json=_request("two"))
        assert first.status_code == 200
        assert second.status_code == 200
        assert _continuity_messages(payloads[0]) == []
        assert _continuity_messages(payloads[1]) == []
