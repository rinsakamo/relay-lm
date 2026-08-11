"""Tests for the PR-9 memory-side stage extraction (RelayINT/RelayMEM).

PR-9 moved three more stage bodies out of ``handle_managed_chat_completion``
(relaylm/managed_chat_runtime.py) into named stage entry points:
``run_relayint_stage`` (relaylm/relayint.py), ``run_relaymem_retrieval_stage``
(relaylm/retrieval/runtime.py, still offloaded via
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
from relaylm.retrieval.runtime import run_relaymem_retrieval_stage
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.subjective_mem.retrieval_cutover import (
    resolve_subjective_mem_retrieval_primary_reader_decision,
)
from relaylm.relayrun import new_run_id
from relaylm.routing import resolve_route

import asyncio

def _primary_only_reader_decision(config):
    """The exact decision a default pre-cutover deployment carries."""

    decision = resolve_subjective_mem_retrieval_primary_reader_decision(config)
    assert decision.reader_class == "primary_only"
    return decision


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


def test_run_relaymem_retrieval_stage_serves_no_primary_after_retirement(
    tmp_path,
) -> None:
    """RT-1D-R5 retired the ordinary Primary reader, so the stage serves none.

    Before retirement this stage rebuilt the dry-run artifact and revalidated it
    against Primary MEM recall scope whenever the carried reader decision named
    `primary_only`. That path no longer exists: the recall entry point, its
    discovery, selection, and fallback are deleted rather than fenced. A
    decision that still names Primary therefore fails closed to `neither` and
    releases nothing, instead of silently degrading into a Primary read.
    """

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

    def _run():
        return run_relaymem_retrieval_stage(
            config=config,
            route=route,
            relaymem_configured_store_root=None,
            relayscn_scene_policy_artifact=relayscn_artifact,
            relayint_intent_artifact=relayint_artifact,
            messages=messages,
            primary_reader_decision=_primary_only_reader_decision(config),
            request_correlation="run-1",
        )

    store_diagnostics, retrieval_artifact = _run()

    # No Primary authority is served and no Primary store is opened.
    assert store_diagnostics["ordinary_memory_authority"] == "neither"
    assert store_diagnostics["primary_store_read"] is False
    assert store_diagnostics["content_free"] is True
    assert retrieval_artifact["ordinary_memory_authority"] == "neither"

    # Nothing Primary-derived is released through the artifact.
    assert retrieval_artifact.get("selected_mem_candidates") in (None, [])
    assert "primary_recall_runtime" not in retrieval_artifact
    assert "primary_recall_projection" not in retrieval_artifact

    # The result is deterministic across repeated calls: retirement is not a
    # one-shot transition that later restores Primary.
    assert _run() == (store_diagnostics, retrieval_artifact)

    # The stage stays a plain blocking callable offloadable via run_stage.
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
            primary_reader_decision=_primary_only_reader_decision(config),
            request_correlation="run-1",
            offload=True,
        )

    offloaded_store_diagnostics, offloaded_retrieval_artifact = asyncio.run(_invoke())

    assert offloaded_store_diagnostics == store_diagnostics
    assert offloaded_retrieval_artifact == retrieval_artifact
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
