"""Tests for the PR-9 memory-side stage extraction (RelayINT/RelayMEM).

PR-9 moved three more stage bodies out of ``handle_managed_chat_completion``
(relaylm/managed_chat_runtime.py) into named stage entry points:
``run_relayint_stage`` (relaylm/relayint.py), ``run_relaymem_retrieval_stage``
(relaylm/relaymem_retrieval.py, still offloaded via
``run_stage(..., offload=True, ...)`` exactly as ``_run_relaymem_retrieval_stage``
was before), and ``run_relaymem_runtime_ctx_stage``
(relaylm/relayctx_repack.py, a thin wrapper around the pre-existing
``apply_relaymem_runtime_injection_phase``).

This is a behavior-preserving extraction, so these tests do not re-assert
full characterization coverage (see
tests/test_chat_completions_characterization.py for that); they pin the new
seams only: each stage entry point, called directly with plain arguments,
must return exactly what its pre-existing builder/phase function already
returned for the same inputs.
"""
from __future__ import annotations

from copy import deepcopy

from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_stage import run_stage
from relaylm.relayctx_repack import (
    apply_relaymem_runtime_injection_phase,
    run_relaymem_runtime_ctx_stage,
)
from relaylm.relayint import build_relayint_reference_intent_artifact, run_relayint_stage
from relaylm.relaymem_primary_recall import apply_relaymem_primary_recall_scope
from relaylm.relaymem_retrieval import (
    build_relaymem_retrieval_dry_run_artifact,
    run_relaymem_retrieval_stage,
)
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.relayrun import new_run_id
from relaylm.routing import resolve_route

import asyncio

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


def _load_config_and_route(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL), encoding="utf-8"
    )
    config = load_config(str(config_path))
    route = resolve_route(config, "relaylm-default")
    return config, route


# ---------------------------------------------------------------------------
# 1. RelayINT stage entry point is a transparent wrapper.
# ---------------------------------------------------------------------------


def test_run_relayint_stage_matches_build_relayint_reference_intent_artifact() -> None:
    relayscn_artifact = {
        "scene_state": {"scene_type": "casual_chat", "is_estimate": True},
        "scene_policy": {"policy_authority": "heuristic_non_authoritative"},
    }
    messages = [{"role": "user", "content": "that thing we discussed earlier"}]
    ctx_hints = {"current_topic": "planning"}

    expected = build_relayint_reference_intent_artifact(
        relayscn_artifact=relayscn_artifact,
        messages=messages,
        ctx_hints=ctx_hints,
    )
    actual = run_relayint_stage(
        relayscn_scene_policy_artifact=relayscn_artifact,
        messages=messages,
        ctx_hints=ctx_hints,
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# 2. RelayMEM retrieval stage entry point matches manual store-diagnostics +
#    retrieval-artifact construction, and stays offloadable via run_stage.
# ---------------------------------------------------------------------------


def test_run_relaymem_retrieval_stage_matches_manual_build(tmp_path) -> None:
    config, route = _load_config_and_route(tmp_path)
    messages = [{"role": "user", "content": "diagnostic smoke text"}]
    relayscn_artifact = {
        "scene_state": {"scene_type": "casual_chat", "is_estimate": True},
        "scene_policy": {
            "relaymem_retrieval_scope": "relationship_or_recent",
            "relaymem_update_gate": "dry_run_only",
        },
    }
    relayint_artifact = {"unresolved_reference_detected": False, "mode_reasons": []}

    expected_store_diagnostics = build_relaymem_store_diagnostics(
        root_path=None,
        store_enabled=config.memory.store_enabled,
        retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
    )
    expected_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=relayscn_artifact,
        relayint_intent_artifact=relayint_artifact,
        messages=messages,
        token_budget=config.memory.token_budget or config.memory.token_budget_hint,
        store_diagnostics=expected_store_diagnostics,
        max_candidates=config.memory.candidate_limit,
        ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
        snippet_extraction_enabled=config.memory.snippet_extraction_enabled,
        snippet_dry_run_only=config.memory.snippet_dry_run_only,
        snippet_apply_enabled=config.memory.snippet_apply_enabled,
        snippet_budget=config.memory.snippet_budget,
        max_snippet_chars=config.memory.max_snippet_chars,
        max_snippet_candidates=config.memory.max_snippet_candidates,
    )
    # run_relaymem_retrieval_stage also revalidates the retrieval artifact
    # against Primary MEM recall scope (unless the store layout is
    # incompatible); with no configured store root that revalidation always
    # runs, exactly as it did inline as part of _run_relaymem_retrieval_stage.
    expected_retrieval_artifact = apply_relaymem_primary_recall_scope(
        expected_retrieval_artifact,
        scoped_store_root=None,
        expected_namespace=route.memory_namespace,
        max_snippet_chars=config.memory.max_snippet_chars,
        max_snippet_candidates=config.memory.max_snippet_candidates,
        snippet_budget=config.memory.snippet_budget,
        chars_per_token=config.memory.chars_per_token,
    )

    actual_store_diagnostics, actual_retrieval_artifact = run_relaymem_retrieval_stage(
        config=config,
        route=route,
        relaymem_configured_store_root=None,
        relayscn_scene_policy_artifact=relayscn_artifact,
        relayint_intent_artifact=relayint_artifact,
        messages=messages,
    )

    assert actual_store_diagnostics == expected_store_diagnostics
    assert actual_retrieval_artifact == expected_retrieval_artifact

    # The stage stays a plain blocking callable: handle_managed_chat_completion
    # offloads it via run_stage(..., offload=True, ...), the same shape
    # _run_relaymem_retrieval_stage used with a bare asyncio.to_thread call.
    node_timings: dict = {}

    async def _invoke():
        return await run_stage(
            node_timings,
            "relaymem_retrieval",
            run_relaymem_retrieval_stage,
            config=config,
            route=route,
            relaymem_configured_store_root=None,
            relayscn_scene_policy_artifact=relayscn_artifact,
            relayint_intent_artifact=relayint_artifact,
            messages=messages,
            offload=True,
        )

    offloaded_store_diagnostics, offloaded_retrieval_artifact = asyncio.run(_invoke())

    assert offloaded_store_diagnostics == expected_store_diagnostics
    assert offloaded_retrieval_artifact == expected_retrieval_artifact
    assert set(node_timings["relaymem_retrieval"].keys()) == {
        "started_at",
        "completed_at",
        "duration_ms",
    }


# ---------------------------------------------------------------------------
# 3. RelayMEM runtime-ctx stage entry point is a transparent wrapper around
#    apply_relaymem_runtime_injection_phase (including its PipelineContext
#    mutation, which stays inside the phase function unchanged).
# ---------------------------------------------------------------------------


def test_run_relaymem_runtime_ctx_stage_matches_apply_relaymem_runtime_injection_phase(
    tmp_path,
) -> None:
    config, route = _load_config_and_route(tmp_path)
    compiled_payload = {"messages": [{"role": "user", "content": "hi"}]}
    relaymem_retrieval_artifact = {
        "apply_decision": "not_eligible",
        "snippet_apply_decision": "not_eligible",
        "ctx_block": None,
        "ctx_block_candidate": None,
        "ctx_block_snippet_candidate": None,
    }

    expected_context = PipelineContext(
        request_id="req-1",
        run_id=new_run_id(),
        original_payload=deepcopy(compiled_payload),
        forwarded_payload=deepcopy(compiled_payload),
        route=route,
        stream_enabled=False,
    )
    expected = apply_relaymem_runtime_injection_phase(
        config=config,
        pipeline_context=expected_context,
        relaymem_retrieval_artifact=deepcopy(relaymem_retrieval_artifact),
        compiled_payload=compiled_payload,
    )

    actual_context = PipelineContext(
        request_id="req-1",
        run_id=new_run_id(),
        original_payload=deepcopy(compiled_payload),
        forwarded_payload=deepcopy(compiled_payload),
        route=route,
        stream_enabled=False,
    )
    actual = run_relaymem_runtime_ctx_stage(
        config=config,
        pipeline_context=actual_context,
        relaymem_retrieval_artifact=deepcopy(relaymem_retrieval_artifact),
        compiled_payload=compiled_payload,
    )

    assert actual == expected
    # The phase mutates pipeline_context.forwarded_payload internally (via
    # replace_pipeline_forwarded_payload); the stage wrapper does not add,
    # remove, or relocate that mutation, so both contexts end up in the same
    # state as the un-wrapped phase call.
    assert actual_context.forwarded_payload == expected_context.forwarded_payload
