"""Tests pinning the response-service seams PR-11 extracted.

PR-11 moved everything response-side (backend forward, stream wrapping,
response construction, durable-finalization gates, and the post-response
RelayMEM SLP ``BackgroundTask`` enqueue) out of
``handle_managed_chat_completion`` into
``relaylm.managed_chat_response.build_managed_chat_response`` (and its
``_build_stream_response``/``_build_nonstream_response`` helpers). Those
functions are now directly importable, so this file pins three seams the
extraction makes newly observable at the module boundary, rather than
re-covering ground the existing characterization suite
(``tests/test_chat_completions_characterization.py``,
``tests/test_prebackend_payload_equivalence.py``, etc.) already owns:

1. Stream wrap order: the RelayMEM SLP finalized-turn capture wrap must be
   constructed before the LAT-2 stream-timing wrap, exactly as in the
   pre-PR-11 inline code.
2. The post-response ``BackgroundTask`` is attached to both the stream and
   non-stream responses whenever the RelayMEM SLP runtime-enqueue gate is
   on (default off, so these tests turn it on explicitly).
3. An invalid durable-finalization gate combination short-circuits both the
   stream and non-stream paths with a content-free 500, before either the
   backend stream is left open or the enqueue background task ever runs.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import relaylm.managed_chat_response as managed_chat_response
from relaylm.app import create_app

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
    b'data: {"id":"chatcmpl-i11","choices":[{"delta":{"content":"hello"}}]}\n\n'
    b"data: [DONE]\n\n"
)

# A ``memory_light`` route with no ``character_id`` so the compile stage's
# should_apply gate stays closed (no profile files to read) while still
# giving ``route.mode_applied != "pass_through"`` -- the condition every gate
# under test here keys off of.
BASE_CONFIG_YAML = """
backends:
  local_backend:
    base_url: {base_url}
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    mode: memory_light
    memory_namespace: test-namespace
    session_id: test-session

memory:
  store_enabled: false

trace:
  enabled: {trace_enabled}
  path: {trace_path}

relaymem_slp_runtime_enqueue_enabled: {enqueue_enabled}
relaymem_slp_runtime_enqueue_dry_run_only: {enqueue_dry_run_only}
relaymem_slp_runtime_enqueue_apply_enabled: {enqueue_apply_enabled}
relaymem_slp_durable_finalization_enabled: {durable_enabled}
relaymem_slp_durable_finalization_dry_run_only: {durable_dry_run_only}
relaymem_slp_durable_finalization_apply_enabled: {durable_apply_enabled}
""".strip()


def _write_config(
    tmp_path: Path,
    *,
    trace_enabled: bool = False,
    trace_path: Path | None = None,
    enqueue_enabled: bool = False,
    enqueue_dry_run_only: bool = True,
    enqueue_apply_enabled: bool = False,
    durable_enabled: bool = False,
    durable_dry_run_only: bool = True,
    durable_apply_enabled: bool = False,
) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        BASE_CONFIG_YAML.format(
            base_url=BACKEND_BASE_URL,
            trace_enabled=str(trace_enabled).lower(),
            trace_path=(str(trace_path) if trace_path is not None else "null"),
            enqueue_enabled=str(enqueue_enabled).lower(),
            enqueue_dry_run_only=str(enqueue_dry_run_only).lower(),
            enqueue_apply_enabled=str(enqueue_apply_enabled).lower(),
            durable_enabled=str(durable_enabled).lower(),
            durable_dry_run_only=str(durable_dry_run_only).lower(),
            durable_apply_enabled=str(durable_apply_enabled).lower(),
        ),
        encoding="utf-8",
    )
    return config_path


def _make_client(config_path: Path) -> TestClient:
    return TestClient(create_app(str(config_path)))


def _chat_request(*, stream: bool) -> dict:
    return {
        "model": "relaylm-default",
        "stream": stream,
        "messages": [{"role": "user", "content": "Hi"}],
    }


# ---------------------------------------------------------------------------
# 1. Stream wrap order: SLP finalized-turn capture before LAT-2 stream timing.
# ---------------------------------------------------------------------------


def test_stream_wrap_order_capture_before_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trace_path = tmp_path / "trace.jsonl"
    config_path = _write_config(
        tmp_path,
        trace_enabled=True,
        trace_path=trace_path,
        enqueue_enabled=True,
        enqueue_dry_run_only=False,
    )
    client = _make_client(config_path)

    calls: list[str] = []
    original_capture_wrap = (
        managed_chat_response.wrap_stream_with_relaymem_slp_finalized_turn_capture
    )
    original_timing_wrap = managed_chat_response.wrap_stream_with_relayrun_stream_timing

    def _spy_capture_wrap(*args: object, **kwargs: object) -> object:
        calls.append("slp_finalized_turn_capture")
        return original_capture_wrap(*args, **kwargs)

    def _spy_timing_wrap(*args: object, **kwargs: object) -> object:
        calls.append("relayrun_stream_timing")
        return original_timing_wrap(*args, **kwargs)

    monkeypatch.setattr(
        managed_chat_response,
        "wrap_stream_with_relaymem_slp_finalized_turn_capture",
        _spy_capture_wrap,
    )
    monkeypatch.setattr(
        managed_chat_response, "wrap_stream_with_relayrun_stream_timing", _spy_timing_wrap
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=STREAM_BODY
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_request(stream=True)
        ) as response:
            assert response.status_code == 200
            _ = b"".join(response.iter_bytes())

    assert calls == ["slp_finalized_turn_capture", "relayrun_stream_timing"], calls


# ---------------------------------------------------------------------------
# 2. BackgroundTask attached to both stream and non-stream responses.
# ---------------------------------------------------------------------------


def test_background_task_attached_for_stream_when_enqueue_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _write_config(
        tmp_path, enqueue_enabled=True, enqueue_dry_run_only=False
    )
    client = _make_client(config_path)

    enqueue_calls: list[object] = []

    def _fake_enqueue(**kwargs: object) -> None:
        enqueue_calls.append(kwargs)

    monkeypatch.setattr(
        managed_chat_response, "run_relaymem_slp_runtime_enqueue_after_response", _fake_enqueue
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=STREAM_BODY
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_request(stream=True)
        ) as response:
            assert response.status_code == 200
            _ = b"".join(response.iter_bytes())

    # Starlette runs an attached BackgroundTask only after the response body
    # has been fully sent, so observing the fake enqueue call here proves a
    # BackgroundTask was actually attached to the StreamingResponse.
    assert len(enqueue_calls) == 1


def test_background_task_attached_for_nonstream_when_enqueue_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _write_config(
        tmp_path, enqueue_enabled=True, enqueue_dry_run_only=False
    )
    client = _make_client(config_path)

    enqueue_calls: list[object] = []

    def _fake_enqueue(**kwargs: object) -> None:
        enqueue_calls.append(kwargs)

    monkeypatch.setattr(
        managed_chat_response, "run_relaymem_slp_runtime_enqueue_after_response", _fake_enqueue
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request(stream=False))

    assert response.status_code == 200
    assert len(enqueue_calls) == 1


# ---------------------------------------------------------------------------
# 3. An invalid durable-finalization gate short-circuits both response paths.
# ---------------------------------------------------------------------------


def test_invalid_durable_finalization_gate_short_circuits_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # enabled=True + dry_run_only=True + apply_enabled=True matches none of
    # durable_finalization_gate_valid's three allowed combinations (dry-run
    # only, apply-only, or fully disabled), so the gate must reject it.
    config_path = _write_config(
        tmp_path,
        durable_enabled=True,
        durable_dry_run_only=True,
        durable_apply_enabled=True,
    )
    client = _make_client(config_path)

    enqueue_calls: list[object] = []
    monkeypatch.setattr(
        managed_chat_response,
        "run_relaymem_slp_runtime_enqueue_after_response",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=STREAM_BODY
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_request(stream=True)
        ) as response:
            assert response.status_code == 500
            body = b"".join(response.iter_bytes())

    import json

    error = json.loads(body)["error"]
    assert error["type"] == "server_error"
    assert error["message"] == "RelayLM could not safely finalize this response."
    # The gate check runs before the enqueue background task is ever built.
    assert enqueue_calls == []


def test_invalid_durable_finalization_gate_short_circuits_nonstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _write_config(
        tmp_path,
        durable_enabled=True,
        durable_dry_run_only=True,
        durable_apply_enabled=True,
    )
    client = _make_client(config_path)

    enqueue_calls: list[object] = []
    monkeypatch.setattr(
        managed_chat_response,
        "run_relaymem_slp_runtime_enqueue_after_response",
        lambda **kwargs: enqueue_calls.append(kwargs),
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request(stream=False))

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["type"] == "server_error"
    assert error["message"] == "RelayLM could not safely finalize this response."
    assert enqueue_calls == []
