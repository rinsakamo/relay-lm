"""Content-free P0 runtime pipeline order projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

P0_REQUEST_PATH_ORDER: tuple[str, ...] = (
    "relayrel_relationship_projection",
    "relayscn_scene_policy",
    "relayemo_input",
    "relayint",
    "relaymem_retrieval",
    "relayctx_repack",
)


def build_p0_pipeline_order_projection(
    *,
    relayrel_projection: Mapping[str, Any] | None = None,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None = None,
    relayemo_artifact: Mapping[str, Any] | None = None,
    relaymem_retrieval_artifact: Mapping[str, Any] | None = None,
    actual_app_rewired: bool = False,
) -> dict[str, Any]:
    """Build a diagnostics-only order projection for P0 smoke coverage.

    The projection reports node names and content-free artifact presence/status
    flags only. It never includes raw messages, memory bodies, relationship
    bodies, scene bodies, assistant output, or backend payload text.
    """

    remaining_work: list[str] = []
    if not actual_app_rewired:
        remaining_work.append("app.py_request_path_not_yet_rewired")

    return {
        "schema_version": "relaylm.pipeline_order_projection.v0",
        "diagnostics_only": True,
        "content_free": True,
        "request_path_order": list(P0_REQUEST_PATH_ORDER),
        "nodes": [
            _node("relayrel_relationship_projection", relayrel_projection),
            _node("relayscn_scene_policy", relayscn_scene_policy_artifact),
            _node("relayemo_input", relayemo_artifact),
            _node("relayint", None, status="reserved"),
            _node("relaymem_retrieval", relaymem_retrieval_artifact),
            _node("relayctx_repack", None, status="reserved"),
        ],
        "relaymem_consumes_relayscn_policy": isinstance(relayscn_scene_policy_artifact, Mapping),
        "relayscn_precedes_relayemo": True,
        "relayrel_precedes_relayscn": True,
        "actual_app_rewired": bool(actual_app_rewired),
        "remaining_work": remaining_work,
        "merge_ready": not remaining_work,
    }


def _node(
    name: str,
    artifact: Mapping[str, Any] | None,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    artifact_present = isinstance(artifact, Mapping)
    return {
        "node_name": name,
        "node_status": status or ("completed" if artifact_present else "pending"),
        "diagnostics_only": True,
        "content_free": True,
        "artifact_present": artifact_present,
    }
