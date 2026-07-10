"""Tests for the PR-8 input-stage extraction (RelayREL/RelaySCN/RelayEMO).

PR-8 moved the RelayREL/RelaySCN/RelayEMO stage *bodies* out of
``handle_managed_chat_completion`` (relaylm/managed_chat_runtime.py) into
named stage entry points: ``run_relayrel_stage`` (relaylm/relayrel.py),
``run_relayscn_stage`` (relaylm/relayscn.py), and ``run_relayemo_stage``
(relaylm/relayemo.py). This is a behavior-preserving extraction, so these
tests do not re-assert full characterization coverage (see
tests/test_chat_completions_characterization.py for that); they pin the
seams that are new or newly-observable because of the extraction itself:

1. The RelayREL/RelaySCN stage entry points are transparent wrappers --
   they must return exactly what the pre-existing public builders return
   for the same inputs.
2. The RelayEMO stage entry point preserves the handler's
   ``config.relayemo_enabled`` gate: when the caller does not invoke
   ``run_stage`` for a skipped stage, no ``node_timings["relayemo"]`` entry
   appears (matching how the handler itself only calls ``run_stage`` inside
   the ``if config.relayemo_enabled:`` block).
3. When enabled, ``run_relayemo_stage`` produces the same session-state
   diagnostics fields (session_key_source, previous_state_found,
   state_updated, fallback_reason, state_persisted, state_storage) the
   inline handler block used to set, and the in-process session-state
   store (``relaylm.relayemo._RELAYEMO_SESSION_STATE``) still round-trips
   assistant state across two calls sharing a session key.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.config import load_config
from relaylm.pipeline_stage import run_stage
from relaylm.relayemo import run_relayemo_stage
from relaylm.relayrel import build_relayrel_relationship_projection, run_relayrel_stage
from relaylm.relayscn import build_relayscn_scene_policy_artifact, run_relayscn_stage
from relaylm.request_scope import build_scope_resolution_diagnostics, extract_request_scope_identity
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
{extra}
""".strip()


def _load_config_and_route(tmp_path: Path, extra: str = ""):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL, extra=extra),
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    route = resolve_route(config, "relaylm-default")
    return config, route


# ---------------------------------------------------------------------------
# 1. RelayREL/RelaySCN stage entry points are transparent wrappers.
# ---------------------------------------------------------------------------


def test_run_relayrel_stage_matches_build_relayrel_relationship_projection(
    tmp_path: Path,
) -> None:
    _config, route = _load_config_and_route(tmp_path)
    request_scope_identity = extract_request_scope_identity({}, {"messages": []})

    expected = build_relayrel_relationship_projection(
        route=route, request_scope_identity=request_scope_identity
    )
    actual = run_relayrel_stage(route=route, request_scope_identity=request_scope_identity)

    assert actual == expected


def test_run_relayscn_stage_matches_build_relayscn_scene_policy_artifact() -> None:
    payload = {"messages": [{"role": "user", "content": "please review this PR"}]}

    expected = build_relayscn_scene_policy_artifact(payload=payload)
    actual = run_relayscn_stage(payload=payload)

    assert actual == expected


# ---------------------------------------------------------------------------
# 2. RelayEMO conditional gating: run_stage must never be called when the
#    stage is disabled, so no node_timings["relayemo"] entry appears.
# ---------------------------------------------------------------------------


def _run_relayemo_stage_conditionally(node_timings, **stage_kwargs):
    """Mirror the handler's ``if config.relayemo_enabled:`` gate exactly.

    ``handle_managed_chat_completion`` only calls ``run_stage`` for the
    relayemo stage inside this guard; a disabled stage must never see
    ``run_stage`` invoked at all (see relaylm/pipeline_stage.py's docstring
    on conditional stages).
    """

    relayemo_artifact = None
    if stage_kwargs["config"].relayemo_enabled:
        relayemo_artifact = asyncio.run(
            run_stage(node_timings, "relayemo", run_relayemo_stage, **stage_kwargs)
        )
    return relayemo_artifact


def test_relayemo_stage_disabled_produces_no_node_timings_entry(tmp_path: Path) -> None:
    config, route = _load_config_and_route(tmp_path, extra="relayemo_enabled: false")
    assert config.relayemo_enabled is False

    payload = {"messages": [{"role": "user", "content": "Hi"}]}
    request_scope_identity = extract_request_scope_identity({}, payload)
    scope_resolution_diagnostics = build_scope_resolution_diagnostics(
        route, request_scope_identity
    )

    node_timings: dict = {}
    artifact = _run_relayemo_stage_conditionally(
        node_timings,
        config=config,
        route=route,
        payload=payload,
        request=None,
        request_scope_identity=request_scope_identity,
        scope_resolution_diagnostics=scope_resolution_diagnostics,
        messages=payload["messages"],
    )

    assert artifact is None
    assert "relayemo" not in node_timings


# ---------------------------------------------------------------------------
# 3. RelayEMO enabled: node_timings entry appears, session-state diagnostics
#    fields are set, and the in-process session-state store round-trips.
# ---------------------------------------------------------------------------


def test_relayemo_stage_enabled_populates_artifact_and_node_timings(
    tmp_path: Path,
) -> None:
    config, route = _load_config_and_route(
        tmp_path,
        extra="relayemo_enabled: true\nrelayemo_session_state_enabled: true",
    )
    assert config.relayemo_enabled is True

    payload = {
        "messages": [{"role": "user", "content": "今日は嬉しい!"}],
        "metadata": {"session_id": "session-abc"},
    }
    request_scope_identity = extract_request_scope_identity({}, payload)
    scope_resolution_diagnostics = build_scope_resolution_diagnostics(
        route, request_scope_identity
    )

    node_timings: dict = {}
    artifact = _run_relayemo_stage_conditionally(
        node_timings,
        config=config,
        route=route,
        payload=payload,
        request=None,
        request_scope_identity=request_scope_identity,
        scope_resolution_diagnostics=scope_resolution_diagnostics,
        messages=payload["messages"],
    )

    assert artifact is not None
    assert "relayemo" in node_timings
    assert set(node_timings["relayemo"].keys()) == {
        "started_at",
        "completed_at",
        "duration_ms",
    }

    # First call for this session key: no previous state yet.
    assert artifact["session_state_enabled"] is True
    assert artifact["session_key_source"] == "resolved_session_id"
    assert artifact["previous_state_found"] is False
    assert artifact["state_updated"] is True
    assert artifact["state_persisted"] is False
    assert artifact["state_storage"] == "process_memory"
    assert "fallback_reason" not in artifact

    # Second call sharing the same session id: previous state must now be
    # found, proving the in-process session-state store round-trips through
    # the extracted stage entry point exactly as it did inline.
    node_timings_2: dict = {}
    artifact_2 = _run_relayemo_stage_conditionally(
        node_timings_2,
        config=config,
        route=route,
        payload=payload,
        request=None,
        request_scope_identity=request_scope_identity,
        scope_resolution_diagnostics=scope_resolution_diagnostics,
        messages=payload["messages"],
    )
    assert artifact_2["previous_state_found"] is True


def test_relayemo_stage_session_key_unavailable_sets_fallback_reason(
    tmp_path: Path,
) -> None:
    config, route = _load_config_and_route(
        tmp_path,
        extra="relayemo_enabled: true\nrelayemo_session_state_enabled: true",
    )

    # No session id anywhere (no metadata, no route session id): the stage
    # must fall back exactly as the inline handler block used to.
    payload = {"messages": [{"role": "user", "content": "Hi"}]}
    request_scope_identity = extract_request_scope_identity({}, payload)
    scope_resolution_diagnostics = build_scope_resolution_diagnostics(
        route, request_scope_identity
    )

    node_timings: dict = {}
    artifact = _run_relayemo_stage_conditionally(
        node_timings,
        config=config,
        route=route,
        payload=payload,
        request=None,
        request_scope_identity=request_scope_identity,
        scope_resolution_diagnostics=scope_resolution_diagnostics,
        messages=payload["messages"],
    )

    assert artifact["session_key_source"] == "unavailable"
    assert artifact["state_updated"] is False
    assert artifact["fallback_reason"] == "session_key_unavailable"
    assert artifact["previous_state_found"] is False
