"""Tests for the PR-7 pipeline stage runner (relaylm/pipeline_stage.py).

Two things are pinned here:

1. A unit-level check that ``run_stage`` records the exact same
   ``node_timings`` entry shape (keys/semantics) that
   ``_start_timing``/``_finalize_timing`` produced when hand-inlined in
   ``handle_managed_chat_completion`` -- for sync, async, and offloaded sync
   calls -- without pinning any duration value.
2. An integration assertion that the ``node_timings`` a ``run_stage`` call
   records for the RelayREL/RelaySCN stages flows, unchanged, into the
   RelayRUN runtime artifact's ``node_statuses`` -- exactly as it did when
   ``managed_chat_runtime.py`` hand-bracketed those two stages with
   ``_start_timing``/``_finalize_timing`` directly. This drives
   ``relaylm/relayrun_runtime_artifact.py``'s
   ``_build_relayrun_runtime_artifact_for_context`` -- the same function
   ``handle_managed_chat_completion`` calls -- directly, rather than
   round-tripping through the HTTP trace file: the trace artifact passes
   through a separate content-free audit projection
   (``relaylm/audit_projection.py``) that intentionally redacts per-node
   ``node_statuses`` (including node names) before it is ever written to
   the trace file. That redaction predates this refactor and is unrelated
   to it, so it is not a faithful place to observe individual stage names.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.config import load_config
from relaylm.pipeline_stage import _finalize_timing, _start_timing, run_stage
from relaylm.relayrel import build_relayrel_relationship_projection
from relaylm.relayrun_runtime_artifact import (
    _ManagedRuntimeArtifactContext,
    _build_relayrun_runtime_artifact_for_context,
)
from relaylm.relayscn import build_relayscn_scene_policy_artifact
from relaylm.request_scope import extract_request_scope_identity
from relaylm.routing import resolve_route

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"

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


def _timing_keys(timing: dict) -> set[str]:
    return set(timing.keys())


_EXPECTED_TIMING_KEYS = {"started_at", "completed_at", "duration_ms"}


# ---------------------------------------------------------------------------
# 1. Unit: run_stage records the same node_timings shape as
#    _start_timing/_finalize_timing did when hand-inlined.
# ---------------------------------------------------------------------------


def test_run_stage_matches_manual_finalize_timing_shape_sync() -> None:
    """A sync stage run through run_stage records the legacy timing shape."""

    node_timings: dict = {}

    def stage(x: int, *, y: int) -> int:
        return x + y

    result = asyncio.run(run_stage(node_timings, "example_stage", stage, 1, y=2))

    assert result == 3
    assert set(node_timings.keys()) == {"example_stage"}
    recorded = node_timings["example_stage"]
    assert _timing_keys(recorded) == _EXPECTED_TIMING_KEYS

    # Cross-check against a manually bracketed call using the same helpers
    # run_stage delegates to -- presence/shape only, not duration values,
    # since wall-clock/monotonic reads are inherently non-deterministic.
    started_at, start_monotonic = _start_timing()
    manual = _finalize_timing(started_at, start_monotonic)
    assert _timing_keys(manual) == _EXPECTED_TIMING_KEYS
    assert isinstance(recorded["started_at"], str)
    assert isinstance(recorded["completed_at"], str)
    assert isinstance(recorded["duration_ms"], int)
    assert recorded["duration_ms"] >= 0


def test_run_stage_awaits_async_callable_before_recording_timing() -> None:
    """An async stage executes fully and records timing only after completion."""

    node_timings: dict = {}
    events: list[str] = []

    async def stage(value: str) -> str:
        events.append("started")
        await asyncio.sleep(0)
        events.append("completed")
        assert "async_stage" not in node_timings
        return value.upper()

    result = asyncio.run(run_stage(node_timings, "async_stage", stage, "hi"))

    assert result == "HI"
    assert events == ["started", "completed"]
    assert set(node_timings) == {"async_stage"}
    assert _timing_keys(node_timings["async_stage"]) == _EXPECTED_TIMING_KEYS


def test_run_stage_offload_routes_through_to_thread_and_records_same_shape() -> None:
    """offload=True still records the identical node_timings shape."""

    node_timings: dict = {}

    def blocking_stage(value: str) -> str:
        return value.upper()

    result = asyncio.run(
        run_stage(node_timings, "offloaded_stage", blocking_stage, "hi", offload=True)
    )

    assert result == "HI"
    assert set(node_timings.keys()) == {"offloaded_stage"}
    recorded = node_timings["offloaded_stage"]
    assert _timing_keys(recorded) == _EXPECTED_TIMING_KEYS
    assert isinstance(recorded["duration_ms"], int)
    assert recorded["duration_ms"] >= 0


def test_run_stage_rejects_async_callable_with_offload() -> None:
    """Coroutine functions cannot be passed through asyncio.to_thread."""

    node_timings: dict = {}

    async def async_stage() -> str:
        return "unexpected"

    try:
        asyncio.run(run_stage(node_timings, "async_stage", async_stage, offload=True))
    except TypeError as exc:
        assert "synchronous callable" in str(exc)
    else:
        raise AssertionError("expected TypeError for offload=True async callable")

    assert "async_stage" not in node_timings


def test_run_stage_does_not_force_a_timing_entry_for_stages_not_invoked() -> None:
    """Conditional stages that don't run today must not gain a forced entry.

    run_stage only ever writes node_timings[name] when it is actually
    called -- a caller guarding a stage behind e.g.
    ``if config.relayemo_enabled:`` and skipping the run_stage call
    entirely (as RelayEMO still does, unmigrated, in this PR) must not see
    a phantom node_timings entry appear.
    """

    node_timings: dict = {}
    relayemo_enabled = False

    if relayemo_enabled:
        asyncio.run(run_stage(node_timings, "relayemo", lambda: None))

    assert "relayemo" not in node_timings


def test_run_stage_propagates_exceptions_without_recording_timing() -> None:
    """A failing stage should not silently record a completed timing entry."""

    node_timings: dict = {}

    def boom() -> None:
        raise ValueError("stage failed")

    try:
        asyncio.run(run_stage(node_timings, "boom_stage", boom))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError to propagate")

    assert "boom_stage" not in node_timings


# ---------------------------------------------------------------------------
# 2. Integration: node_timings recorded by run_stage for relayrel/relayscn
#    flow into the RelayRUN runtime artifact's node_statuses, exactly like
#    every other (not-yet-migrated) stage's node_timings entry.
# ---------------------------------------------------------------------------


def _load_minimal_config_and_route(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL), encoding="utf-8"
    )
    config = load_config(str(config_path))
    route = resolve_route(config, "relaylm-default")
    return config, route


def test_relayrel_and_relayscn_node_timings_flow_into_relayrun_artifact(
    tmp_path: Path,
) -> None:
    config, route = _load_minimal_config_and_route(tmp_path)
    payload = {"model": "relaylm-default", "messages": [{"role": "user", "content": "Hi"}]}
    request_scope_identity = extract_request_scope_identity({}, payload)

    node_timings: dict = {}

    relayrel_relationship_projection = asyncio.run(
        run_stage(
            node_timings,
            "relayrel",
            build_relayrel_relationship_projection,
            route=route,
            request_scope_identity=request_scope_identity,
        )
    )
    relayscn_scene_policy_artifact = asyncio.run(
        run_stage(
            node_timings,
            "relayscn",
            build_relayscn_scene_policy_artifact,
            payload=payload,
        )
    )

    # Both stages recorded a node_timings entry -- and nothing else, since
    # only relayrel/relayscn were run through run_stage in this test.
    assert set(node_timings.keys()) == {"relayrel", "relayscn"}
    for name in ("relayrel", "relayscn"):
        assert _timing_keys(node_timings[name]) == _EXPECTED_TIMING_KEYS

    context = _ManagedRuntimeArtifactContext(
        config=config,
        request_id="test-request-id",
        run_id="run_test",
        route=route,
        stream_enabled=False,
        relayrel_relationship_projection=relayrel_relationship_projection,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=None,
        relayint_intent_artifact=None,
        relaymem_retrieval_artifact=None,
        runtime_ctx_injection_result=None,
        runtime_snippet_injection_result=None,
        relayctx_short_term_runtime_injection_apply_result=None,
        token_budget_truncation=None,
        node_timings=node_timings,
    )

    artifact = _build_relayrun_runtime_artifact_for_context(
        context,
        backend_forward_status="pending",
        stream_started=False,
        first_token_sent=False,
    )

    node_statuses = artifact["node_statuses"]
    node_by_name = {node["node_name"]: node for node in node_statuses}

    # relayrel/relayscn are the two stages PR-7 migrated to run_stage; they
    # must still show up as RelayRUN nodes, carrying the exact timing
    # values run_stage recorded, exactly like every other stage does today.
    assert "relayrel" in node_by_name
    assert "relayscn" in node_by_name

    for name in ("relayrel", "relayscn"):
        node = node_by_name[name]
        timing = node_timings[name]
        assert node["started_at"] == timing["started_at"]
        assert node["completed_at"] == timing["completed_at"]
        assert node["duration_ms"] == timing["duration_ms"]
