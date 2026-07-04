#!/usr/bin/env python3
"""Smoke coverage guarding against RelayRUN node-sequence/node-builder drift.

RUNTIME_CHECKPOINT_NODE_SEQUENCE (relaylm/relayrun.py) declares the canonical
runtime checkpoint node names. app.py's `_build_relayrun_runtime_artifact`
independently builds the actual `node_statuses` list attached to every
request. Nothing enforced these two stay in sync, so a prior review found the
declared sequence missing RelayREL, RelayEMO, and the RelayCTX short-term
injection node entirely. This smoke fails closed if the two ever diverge
again.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _build_relayrun_runtime_artifact
from relaylm.config import RelayLMConfig, load_config
from relaylm.relayrun import RUNTIME_CHECKPOINT_NODE_SEQUENCE
from relaylm.routing import resolve_route


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _build_config() -> RelayLMConfig:
    data = load_config(REPO_ROOT / "config.example.yaml").model_dump()
    return RelayLMConfig.model_validate(data)


def main() -> int:
    config = _build_config()
    route = resolve_route(config, "relaylm-default")

    artifact = _build_relayrun_runtime_artifact(
        config=config,
        request_id="node-sequence-drift-smoke",
        run_id="run-node-sequence-drift-smoke",
        route=route,
        stream_enabled=False,
        relayrel_relationship_projection={
            "schema_version": "relayrel.relationship_projection.v0",
            "content_free": True,
        },
        relayscn_scene_policy_artifact={
            "scene_state": {"scene_type": "design_talk"},
            "scene_policy": {},
        },
        relayemo_artifact=None,
        relayint_intent_artifact={
            "unresolved_reference_detected": False,
            "mode_reasons": [],
        },
        relaymem_retrieval_artifact={
            "apply_decision": "not_eligible",
            "snippet_apply_decision": "not_eligible",
        },
        runtime_ctx_injection_result={"applied": False, "blocked_reasons": []},
        runtime_snippet_injection_result={"applied": False, "blocked_reasons": []},
        relayctx_short_term_runtime_injection_apply_result=None,
        token_budget_truncation=None,
        backend_forward_status="completed",
        stream_started=False,
        first_token_sent=False,
    )

    node_statuses = artifact.get("node_statuses")
    require(isinstance(node_statuses, list) and node_statuses, artifact)
    actual_node_names = {
        node.get("node_name") for node in node_statuses if isinstance(node, dict)
    }
    declared_node_names = set(RUNTIME_CHECKPOINT_NODE_SEQUENCE)

    require(
        actual_node_names == declared_node_names,
        (
            "RUNTIME_CHECKPOINT_NODE_SEQUENCE and app.py node_statuses names diverged: "
            f"declared_only={declared_node_names - actual_node_names} "
            f"actual_only={actual_node_names - declared_node_names}"
        ),
    )
    require(
        artifact.get("node_sequence") == list(RUNTIME_CHECKPOINT_NODE_SEQUENCE),
        artifact.get("node_sequence"),
    )

    for required_name in ("relayrel", "relayemo", "relayctx_short_term_injection"):
        require(required_name in declared_node_names, declared_node_names)
        require(required_name in actual_node_names, actual_node_names)

    require(
        RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("relayrel")
        < RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("relayscn")
        < RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("relayemo"),
        RUNTIME_CHECKPOINT_NODE_SEQUENCE,
    )
    require(
        RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("relaymem_runtime_ctx")
        < RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("relayctx_short_term_injection")
        < RUNTIME_CHECKPOINT_NODE_SEQUENCE.index("token_budget_truncation"),
        RUNTIME_CHECKPOINT_NODE_SEQUENCE,
    )

    print("ok RUNTIME_CHECKPOINT_NODE_SEQUENCE matches app.py node_statuses names")
    print("ok relayrel/relayemo/relayctx_short_term_injection sit at canonical positions")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
