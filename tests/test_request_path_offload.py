"""Tests for PR-6's `asyncio.to_thread` offload of blocking stage file I/O.

`handle_managed_chat_completion` (relaylm/managed_chat_runtime.py) used to
call synchronous, filesystem-heavy stage functions directly on the event
loop: one slow RelayMEM lookup would stall every other concurrent request,
including in-flight streams. This PR moves the file-I/O-bearing stage calls
(the RelayMEM retrieval dry-run artifact build, and the request compile step
that reads character workspace files) onto worker threads via
``asyncio.to_thread``.

Three things need proving here, beyond the existing 49-test suite (especially
the PR-5 characterization tests) staying green unchanged:

1. Event-loop liveness: a slow offloaded stage must not block unrelated
   concurrent requests (``test_slow_offloaded_stage_does_not_block_other_requests``).
2. The ``ContextVar`` handoff ``compile_chat_payload_if_enabled`` uses to pass
   typed pre-render compiler blocks to ``PipelineContext`` does NOT survive a
   naive ``asyncio.to_thread`` call (a ``.set()`` inside the worker's copied
   context never reaches the awaiting request context) -- and that the
   capture/restore helpers added alongside the offload actually fix this
   (``test_to_thread_context_var_does_not_propagate_without_restore`` and
   ``test_restore_helper_replays_captured_blocks_into_caller_context``).
3. An end-to-end request through the offloaded compile path still produces
   the same compiled backend-bound payload as the (synchronous, pre-PR-6)
   behavior asserted by ``scripts/relaylm_memory_light_apply_smoke.py``
   (``test_memory_light_request_through_offloaded_compile_stage_matches_expected_compilation``).
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.config import load_config
from relaylm.managed_chat_runtime import (
    _compile_chat_payload_and_capture_context_blocks,
)
import relaylm.managed_chat_runtime as managed_chat_runtime
from relaylm.request_compiler import (
    consume_compiled_context_blocks_runtime_private,
    restore_compiled_context_blocks_runtime_private,
)
from relaylm.routing import resolve_route

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

# Mirrors config.example.yaml's memory_light character wiring, but with
# absolute paths so the config file's location doesn't matter, and pointed at
# a mocked backend base_url.
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


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL), encoding="utf-8"
    )
    return config_path


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


def _chat_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    payload.update(overrides)
    return payload


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# 1. Event-loop liveness: a slow offloaded stage must not block /healthz
# ---------------------------------------------------------------------------


def test_slow_offloaded_stage_does_not_block_other_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow RelayMEM retrieval build must not stall concurrent /healthz.

    Before PR-6, ``build_relaymem_retrieval_dry_run_artifact`` ran directly
    on the event loop inside ``handle_managed_chat_completion``; a slow call
    (here simulated with ``time.sleep(0.5)``) would block every other
    in-flight coroutine, including trivial ``/healthz`` requests dispatched
    after it. With the stage offloaded via ``asyncio.to_thread``, those
    concurrent requests must complete well before the slow one does.
    """

    config_path = _write_config(tmp_path)
    app = create_app(str(config_path))

    real_builder = managed_chat_runtime.build_relaymem_retrieval_dry_run_artifact

    def _slow_builder(*args: object, **kwargs: object) -> dict:
        time.sleep(0.5)
        return real_builder(*args, **kwargs)

    monkeypatch.setattr(
        managed_chat_runtime, "build_relaymem_retrieval_dry_run_artifact", _slow_builder
    )

    completion_times: dict[str, float] = {}

    async def scenario() -> None:
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:

                async def slow_chat_request() -> None:
                    response = await client.post(
                        "/v1/chat/completions", json=_chat_request()
                    )
                    assert response.status_code == 200
                    completion_times["chat"] = time.monotonic()

                async def healthz_request(label: str) -> None:
                    response = await client.get("/healthz")
                    assert response.status_code == 200
                    completion_times[label] = time.monotonic()

                start = time.monotonic()
                chat_task = asyncio.create_task(slow_chat_request())
                # Give the slow chat request a moment to enter the
                # monkeypatched (sleeping) stage before dispatching the
                # healthz requests, so this only proves liveness during the
                # blocking window rather than winning a race at t=0.
                await asyncio.sleep(0.1)
                healthz_tasks = [
                    asyncio.create_task(healthz_request(f"healthz_{i}"))
                    for i in range(5)
                ]
                await asyncio.gather(*healthz_tasks)
                healthz_elapsed = time.monotonic() - start
                await chat_task
                chat_elapsed = completion_times["chat"] - start

        # Generous margins to avoid flakiness: the healthz requests must
        # finish well inside the 0.5s sleep window, and well before the slow
        # chat request itself completes.
        assert healthz_elapsed < 0.4, (
            f"healthz requests took {healthz_elapsed:.3f}s -- the slow stage "
            "appears to still be blocking the event loop"
        )
        assert chat_elapsed >= 0.5
        for i in range(5):
            assert completion_times[f"healthz_{i}"] < completion_times["chat"]

    _run(scenario())


# ---------------------------------------------------------------------------
# 2. ContextVar propagation: the naive gap, and the fix
# ---------------------------------------------------------------------------


def _memory_light_route_and_config(tmp_path: Path):
    config_path = _write_memory_light_config(tmp_path)
    config = load_config(config_path)
    route = resolve_route(config, "relaylm-default")
    return config, route


def test_to_thread_context_var_does_not_propagate_without_restore(
    tmp_path: Path,
) -> None:
    """Prove the underlying hazard: a bare ``asyncio.to_thread`` call loses it.

    ``compile_chat_payload_if_enabled`` stashes its typed compiled blocks in
    a request-local ``ContextVar`` (``_COMPILED_CONTEXT_BLOCKS``) for
    ``PipelineContext`` to pick up. ``asyncio.to_thread`` runs the target in
    a *copy* of the current context; a ``ContextVar.set`` performed inside
    that copy is discarded when the worker thread finishes and does not
    reach the awaiting coroutine's own context. This test confirms that gap
    exists (motivating the capture/restore helpers) rather than assuming it.
    """

    config, route = _memory_light_route_and_config(tmp_path)
    payload = _chat_request()

    async def scenario() -> tuple[object, object]:
        compiled_request, captured_blocks = await asyncio.to_thread(
            _compile_chat_payload_and_capture_context_blocks,
            config=config,
            route=route,
            payload=payload,
        )
        # No restore call here -- this is deliberately the naive path.
        leaked = consume_compiled_context_blocks_runtime_private()
        return compiled_request, captured_blocks, leaked

    compiled_request, captured_blocks, leaked_into_caller_context = _run(scenario())

    assert compiled_request.compiler_used is True
    assert captured_blocks is not None and len(captured_blocks) > 0
    assert leaked_into_caller_context is None, (
        "a ContextVar.set performed inside asyncio.to_thread's worker thread "
        "must not be visible in the awaiting coroutine's own context"
    )


def test_restore_helper_replays_captured_blocks_into_caller_context(
    tmp_path: Path,
) -> None:
    """The capture/restore pair used by the offloaded compile stage works.

    Mirrors exactly what ``handle_managed_chat_completion`` does: await the
    to_thread call, then explicitly replay the captured blocks into the
    request's own context via ``restore_compiled_context_blocks_runtime_private``
    before anything (here, a direct ``consume`` call standing in for
    ``PipelineContext.__post_init__``) reads them.
    """

    config, route = _memory_light_route_and_config(tmp_path)
    payload = _chat_request()

    async def scenario() -> tuple[object, object]:
        compiled_request, captured_blocks = await asyncio.to_thread(
            _compile_chat_payload_and_capture_context_blocks,
            config=config,
            route=route,
            payload=payload,
        )
        restore_compiled_context_blocks_runtime_private(captured_blocks)
        restored = consume_compiled_context_blocks_runtime_private()
        return captured_blocks, restored

    captured_blocks, restored = _run(scenario())

    assert restored is captured_blocks
    assert restored is not None and len(restored) > 0
    # Consuming is one-shot, same contract as the synchronous path.
    assert _run(_consume_once()) is None


async def _consume_once():
    return consume_compiled_context_blocks_runtime_private()


# ---------------------------------------------------------------------------
# 3. End-to-end: offloaded compile stage matches the pre-PR-6 compiled shape
# ---------------------------------------------------------------------------


def test_memory_light_request_through_offloaded_compile_stage_matches_expected_compilation(
    tmp_path: Path,
) -> None:
    """The full request path still compiles memory_light payloads correctly.

    Same expected compiled-message shape asserted directly against
    ``compile_chat_payload_if_enabled`` by
    ``scripts/relaylm_memory_light_apply_smoke.py``, now driven end-to-end
    through the app so the compile stage's ``asyncio.to_thread`` offload and
    its ContextVar capture/restore are exercised on the real request path.
    """

    config_path = _write_memory_light_config(tmp_path)
    app = create_app(str(config_path))
    client = TestClient(app)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post(
            "/v1/chat/completions",
            json=_chat_request(
                messages=[
                    {"role": "system", "content": "Keep this session concise."},
                    {"role": "user", "content": "hello"},
                ]
            ),
        )

    assert response.status_code == 200
    assert route.call_count == 1
    import json

    sent_payload = json.loads(route.calls[0].request.content)
    compiled_messages = sent_payload["messages"]

    assert compiled_messages[0]["role"] == "system"
    compiled_context = compiled_messages[0]["content"]
    assert "<relaylm_context" in compiled_context
    assert "<character_soul_anchor>" in compiled_context
    assert "<retrieved_memory>" in compiled_context
    assert "default-relaylm-project" in compiled_context
    assert "<incoming_system_prompt>" in compiled_context
    assert compiled_messages[1:] == [{"role": "user", "content": "hello"}]

    assert response.headers["x-relaylm-mode"] == "memory_light"
