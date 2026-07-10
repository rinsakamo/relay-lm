"""Backend-bound payload equivalence tests for the PR-10 pre-backend stages.

PR-10 extracts three pieces of inline handler logic in
``handle_managed_chat_completion`` (relaylm/managed_chat_runtime.py) into
named stage entry points:

1. RelayCTX short-term injection (node_timings key
   ``relayctx_short_term_injection``).
2. Token budget truncation (node_timings key ``token_budget_truncation``) --
   the final payload-mutation gate before the backend call.
3. The compile-gate/compile-decision diagnostics glue.

None of these are supposed to change the actual bytes RelayLM sends to the
backend. This file pins the EXACT backend-bound JSON payload (the ``json``
body of the mocked backend request, captured via respx) for a representative
set of request shapes, using full-dict equality rather than the coarser
structural assertions in tests/test_chat_completions_characterization.py --
the backend-bound payload is an external contract, not an internal artifact,
so full equality is the right tool here.

These tests were written and confirmed green against the pre-PR-10 base
branch (``claude/pr-09-memory-stages``) BEFORE the extraction landed, then
re-confirmed green after it, per the PR-10 task's required ordering.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.config import load_config
from relaylm.managed_chat_runtime import (
    _compile_chat_payload_and_capture_context_blocks,
)
from relaylm.request_compiler import (
    consume_compiled_context_blocks_runtime_private,
)
from relaylm.routing import resolve_route
from relaylm.token_budget_truncation import apply_token_budget_message_truncation

REPO_ROOT = Path(__file__).resolve().parents[1]

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

MINIMAL_CONFIG_YAML = """
backends:
  local_backend:
    base_url: {base_url}
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
""".strip()

# Mirrors config.example.yaml's memory_light character wiring (same shape
# tests/test_request_path_offload.py and scripts/relaylm_memory_light_apply_smoke.py
# use), with absolute paths so the config file's location doesn't matter.
MEMORY_LIGHT_CONFIG_YAML = """
backends:
  local_backend:
    base_url: {base_url}
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    character_id: default
    mode: memory_light

memory:
  candidate_limit: 3
  token_budget_hint: 800
  character_budget: 1200

characters:
  default:
    common_runtime_policy: {common_runtime_policy}
    soul: {soul}
    output_policy: {output_policy}
    memory_seed_path: {memory_seed_path}
    scene_state: {scene_state}
""".strip()

# A config where the token-budget truncation stage actually fires: a small
# memory.token_budget with enforcement enabled, driven by a fixture with
# enough filler turns to exceed it.
TOKEN_BUDGET_CONFIG_YAML = """
backends:
  local_backend:
    base_url: {base_url}
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model

memory:
  token_budget: 60
  token_budget_truncation_enabled: true
  chars_per_token: 4
""".strip()


def _write_config(tmp_path: Path, yaml_text: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml_text.format(base_url=BACKEND_BASE_URL), encoding="utf-8")
    return config_path


def _make_client(tmp_path: Path, yaml_text: str) -> TestClient:
    config_path = _write_config(tmp_path, yaml_text)
    app = create_app(str(config_path))
    return TestClient(app)


def _write_memory_light_config(tmp_path: Path) -> Path:
    profiles = REPO_ROOT / "examples" / "profiles" / "default"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MEMORY_LIGHT_CONFIG_YAML.format(
            base_url=BACKEND_BASE_URL,
            common_runtime_policy=profiles / "common_runtime_policy.md",
            soul=profiles / "SOUL.md",
            output_policy=profiles / "style.md",
            memory_seed_path=REPO_ROOT / "examples" / "memory" / "default_memories.yaml",
            scene_state=profiles / "SCENE_STATE.md",
        ),
        encoding="utf-8",
    )
    return config_path


def _sent_payload(route_mock) -> dict:
    assert route_mock.call_count == 1
    return json.loads(route_mock.calls[0].request.content)


# ---------------------------------------------------------------------------
# 1. Default config, single user message (non-stream). Also serves as the
#    non-stream half of scenario 5 (stream/non-stream variants); see
#    test_default_config_stream_variant_backend_payload below for the stream
#    half of the same request/config.
# ---------------------------------------------------------------------------


def test_default_config_single_user_message_nonstream_backend_payload(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path, MINIMAL_CONFIG_YAML)
    request_payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
    }

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=request_payload)

    assert response.status_code == 200
    sent_payload = _sent_payload(route)
    assert sent_payload == {
        "model": "local-model",
        "messages": [{"role": "user", "content": "Hi"}],
    }


# ---------------------------------------------------------------------------
# 2. Multi-turn history (system + user + assistant + user)
# ---------------------------------------------------------------------------


def test_multi_turn_history_backend_payload(tmp_path: Path) -> None:
    client = _make_client(tmp_path, MINIMAL_CONFIG_YAML)
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "How are you?"},
    ]
    request_payload = {"model": "relaylm-default", "messages": messages}

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=request_payload)

    assert response.status_code == 200
    sent_payload = _sent_payload(route)
    assert sent_payload == {
        "model": "local-model",
        "messages": messages,
    }


# ---------------------------------------------------------------------------
# 3. memory_light / compile enabled
# ---------------------------------------------------------------------------


def test_memory_light_compile_enabled_backend_payload(tmp_path: Path) -> None:
    config_path = _write_memory_light_config(tmp_path)
    config = load_config(config_path)
    route = resolve_route(config, "relaylm-default")

    request_messages = [
        {"role": "system", "content": "Keep this session concise."},
        {"role": "user", "content": "hello"},
    ]
    request_payload = {"model": "relaylm-default", "messages": request_messages}

    # Ground truth: call the compiler directly with the identical
    # config/route/payload the full request path resolves to. This is
    # deterministic (fixed example memory/profile fixtures, no wall-clock
    # content) so it is a stable target for full-dict equality rather than a
    # hand-maintained literal blob of compiled system-prompt text.
    #
    # Uses the same capture helper handle_managed_chat_completion offloads
    # onto a worker thread (rather than calling
    # compile_chat_payload_if_enabled directly) and immediately consumes the
    # captured ContextVar handoff -- calling the raw compiler function here
    # would leave its typed pre-render blocks parked in the request-local
    # ContextVar for the rest of this test process, which
    # tests/test_request_path_offload.py's ContextVar-propagation tests
    # depend on being empty until they set it themselves.
    expected_compiled, _captured_blocks = (
        _compile_chat_payload_and_capture_context_blocks(
            config=config,
            route=route,
            payload=request_payload,
        )
    )
    consume_compiled_context_blocks_runtime_private()
    assert expected_compiled.compiler_used is True
    assert expected_compiled.memory_block_used is True

    app = create_app(str(config_path))
    client = TestClient(app)

    with respx.mock(assert_all_called=False) as mock:
        route_mock = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=request_payload)

    assert response.status_code == 200
    assert response.headers["x-relaylm-mode"] == "memory_light"
    sent_payload = _sent_payload(route_mock)
    assert sent_payload == {
        "model": "local-model",
        "messages": expected_compiled.payload["messages"],
    }


# ---------------------------------------------------------------------------
# 4. token_budget_truncation reachable
# ---------------------------------------------------------------------------


def _token_budget_filler_messages() -> list[dict]:
    messages: list[dict] = [
        {"role": "system", "content": "You are a concise assistant."},
    ]
    for index in range(6):
        role = "user" if index % 2 == 0 else "assistant"
        messages.append(
            {
                "role": role,
                "content": f"filler turn {index} " + ("padding text " * 8),
            }
        )
    messages.append({"role": "user", "content": "What is the weather today?"})
    return messages


def test_token_budget_truncation_backend_payload(tmp_path: Path) -> None:
    client = _make_client(tmp_path, TOKEN_BUDGET_CONFIG_YAML)
    messages = _token_budget_filler_messages()
    request_payload = {"model": "relaylm-default", "messages": messages}

    # Ground truth: the same pure truncation function
    # (relaylm.token_budget_truncation.apply_token_budget_message_truncation)
    # the CTX Repack phase calls, with the exact keep_system/keep_latest_user
    # contract the phase uses.
    expected = apply_token_budget_message_truncation(
        messages=messages,
        token_budget=60,
        chars_per_token=4,
        keep_system=True,
        keep_latest_user=True,
    )
    assert expected.over_budget_before is True
    assert expected.dropped_message_count > 0
    assert expected.over_budget_after is False
    assert expected.blocked_reason is None
    # Sanity: the fixture must actually exercise truncation, not be a no-op.
    assert len(expected.truncated_messages) < len(messages)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=request_payload)

    assert response.status_code == 200
    sent_payload = _sent_payload(route)
    assert sent_payload == {
        "model": "local-model",
        "messages": expected.truncated_messages,
    }


# ---------------------------------------------------------------------------
# 5. stream variant of the default case (see scenario 1 above for the
#    non-stream variant of the same request/config).
# ---------------------------------------------------------------------------


def test_default_config_stream_variant_backend_payload(tmp_path: Path) -> None:
    client = _make_client(tmp_path, MINIMAL_CONFIG_YAML)
    request_payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": True,
    }
    sse_body = (
        b'data: {"id":"chatcmpl-1","object":"chat.completion.chunk",'
        b'"choices":[{"index":0,"delta":{"role":"assistant","content":"Hi"},'
        b'"finish_reason":null}]}\n\n'
        b"data: [DONE]\n\n"
    )

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=sse_body,
                headers={"content-type": "text/event-stream"},
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=request_payload
        ) as response:
            assert response.status_code == 200
            list(response.iter_lines())

    sent_payload = _sent_payload(route)
    assert sent_payload == {
        "model": "local-model",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": True,
    }
