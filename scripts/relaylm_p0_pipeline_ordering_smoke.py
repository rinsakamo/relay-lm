#!/usr/bin/env python3
"""Smoke coverage for P0 RelayREL / RelaySCN / RelayEMO ordering."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from relaylm.pipeline_ordering import build_p0_pipeline_order_projection
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relayrel import build_relayrel_relationship_projection
from relaylm.relayscn import build_relayscn_scene_policy_artifact


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    signature = inspect.signature(build_relayscn_scene_policy_artifact)
    _assert(
        "relayemo_artifact" not in signature.parameters,
        "RelaySCN public API must not expose a relayemo_artifact parameter",
    )

    source = Path("relaylm/relayscn.py").read_text(encoding="utf-8")
    _assert(
        "_extract_relayemo_scene_state" not in source,
        "RelaySCN must not keep the RelayEMO scene-state extractor",
    )
    _assert(
        "scene_state_source\": source" in source,
        "RelaySCN artifact should expose its normalized scene-state source",
    )
    _assert(
        'source = "relayemo_artifact"' not in source,
        "RelaySCN must not emit scene_state_source=relayemo_artifact",
    )

    explicit_artifact = build_relayscn_scene_policy_artifact(
        payload={
            "metadata": {
                "relayscn": {
                    "scene_state": {
                        "scene_type": "review_work",
                        "confidence": 0.91,
                        "stability": 0.86,
                    }
                }
            },
            "messages": [{"role": "user", "content": "casual fallback text"}],
        }
    )
    _assert(explicit_artifact["scene_state_source"] == "request_metadata", "explicit metadata should win")
    _assert(explicit_artifact["scene_state"]["scene_type"] == "review_work", "explicit scene type should be preserved")

    heuristic_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]}
    )
    _assert(heuristic_artifact["scene_state_source"] == "heuristic", "missing metadata should use heuristic")
    _assert(heuristic_artifact["scene_state"]["scene_type"] == "review_work", "heuristic should classify review text")

    relayemo_like_scene = {"scene_state": {"scene_type": "vtuber_roleplay", "confidence": 1.0}}
    ignored_artifact = build_relayscn_scene_policy_artifact(
        payload={"messages": [{"role": "user", "content": "Please review this PR diff."}]},
        **{"relayemo_artifact": relayemo_like_scene},
    )
    _assert(ignored_artifact["scene_state_source"] == "heuristic", "RelayEMO scene_state must be ignored")
    _assert(ignored_artifact["scene_state"]["scene_type"] == "review_work", "RelayEMO scene_state must not override RelaySCN")

    unknown_artifact = build_relayscn_scene_policy_artifact(payload={"messages": []})
    _assert(unknown_artifact["scene_state_source"] == "heuristic", "empty request should remain heuristic/fail-closed")
    _assert(unknown_artifact["scene_state"]["scene_type"] == "unknown", "empty request should fail closed to unknown")

    relayrel_projection = build_relayrel_relationship_projection(route=None, request_scope_identity={"session_id": "s"})
    retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayref_artifact={"unresolved_reference_detected": False, "mode_reasons": []},
        messages=[{"role": "user", "content": "content intentionally not emitted in public diagnostics"}],
        token_budget=256,
        store_diagnostics={"store_enabled": False, "readiness": "disabled"},
        max_candidates=4,
        ctx_block_apply_enabled=False,
        snippet_extraction_enabled=False,
        snippet_dry_run_only=True,
        snippet_apply_enabled=False,
        snippet_budget=128,
        max_snippet_chars=128,
        max_snippet_candidates=2,
    )
    order_projection = build_p0_pipeline_order_projection(
        relayrel_projection=relayrel_projection,
        relayscn_scene_policy_artifact=heuristic_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact=retrieval_artifact,
    )
    order = order_projection["request_path_order"]
    _assert(order.index("relayrel_relationship_projection") < order.index("relayscn_scene_policy"), "RelayREL must precede RelaySCN")
    _assert(order.index("relayscn_scene_policy") < order.index("relayemo_input"), "RelaySCN must precede input RelayEMO")
    _assert(order.index("relaymem_retrieval") > order.index("relayscn_scene_policy"), "RelayMEM must consume RelaySCN policy after SCN")
    _assert(order_projection["relaymem_consumes_relayscn_policy"] is True, "order projection should mark RelayMEM as consuming RelaySCN")

    public_json = json.dumps(order_projection, ensure_ascii=False)
    for forbidden in (
        "content intentionally not emitted",
        "relationship body",
        "memory body",
        "assistant output",
    ):
        _assert(forbidden not in public_json, f"public diagnostics leaked forbidden content: {forbidden}")

    print("relaylm_p0_pipeline_ordering_smoke: PASS")


if __name__ == "__main__":
    main()
