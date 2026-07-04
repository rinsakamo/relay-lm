"""Content-free P0 runtime pipeline order projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    measured_node_order: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a diagnostics-only order projection for P0 smoke coverage.

    The projection reports node names and content-free artifact presence/status
    flags only. It never includes raw messages, memory bodies, relationship
    bodies, scene bodies, assistant output, or backend payload text.

    ``relayscn_precedes_relayemo`` and ``relayrel_precedes_relayscn`` are derived
    from ``measured_node_order`` (an actual observed call/execution order, e.g.
    from AST line-number measurement of app.py) when the caller supplies it, so
    the fields report a measured fact rather than a declared constant. When no
    measured order is supplied, they fall back to ``actual_app_rewired`` (the
    only other measurement available to this diagnostics-only helper).
    """

    remaining_work: list[str] = []
    if not actual_app_rewired:
        remaining_work.append("app.py_request_path_not_yet_rewired")

    safe_measured_order = _safe_string_sequence(measured_node_order)

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
        "relaymem_consumes_relayscn_policy": _relaymem_consumes_relayscn_policy(
            relaymem_retrieval_artifact
        ),
        "relayscn_precedes_relayemo": _measured_order_precedes(
            safe_measured_order,
            "relayscn_scene_policy",
            "relayemo_input",
            fallback=actual_app_rewired,
        ),
        "relayrel_precedes_relayscn": _measured_order_precedes(
            safe_measured_order,
            "relayrel_relationship_projection",
            "relayscn_scene_policy",
            fallback=actual_app_rewired,
        ),
        "measured_node_order": safe_measured_order,
        "actual_app_rewired": bool(actual_app_rewired),
        "remaining_work": remaining_work,
        "merge_ready": not remaining_work,
    }


def _safe_string_sequence(value: Sequence[str] | None) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return [str(item) for item in value]


def _measured_order_precedes(
    measured_node_order: list[str] | None,
    before: str,
    after: str,
    *,
    fallback: bool,
) -> bool:
    """Return whether ``before`` precedes ``after`` in a measured node order.

    Falls back to ``fallback`` when no measured order is supplied or either
    node name is absent from it, since precedence cannot be measured then.
    """

    if measured_node_order is None:
        return fallback
    if before not in measured_node_order or after not in measured_node_order:
        return fallback
    return measured_node_order.index(before) < measured_node_order.index(after)


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


def _relaymem_consumes_relayscn_policy(
    relaymem_retrieval_artifact: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(relaymem_retrieval_artifact, Mapping):
        return False

    scene_type = relaymem_retrieval_artifact.get("scene_type")
    retrieval_scope = relaymem_retrieval_artifact.get("retrieval_scope")
    if not isinstance(scene_type, str) or not scene_type or scene_type == "unknown":
        return False
    if not isinstance(retrieval_scope, str) or not retrieval_scope:
        return False

    persistence_block_reasons = relaymem_retrieval_artifact.get("persistence_block_reasons")
    if isinstance(persistence_block_reasons, Sequence) and not isinstance(
        persistence_block_reasons, str
    ):
        reason_values = {str(reason) for reason in persistence_block_reasons}
        if "malformed_relayscn_artifact" in reason_values:
            return False

    return True
