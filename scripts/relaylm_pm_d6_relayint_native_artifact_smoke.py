from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayint import (  # noqa: E402
    build_relayint_reference_intent_artifact,
    build_relayint_reference_repair_dry_run,
)
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact  # noqa: E402


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _scene() -> dict[str, Any]:
    return {
        "scene_state": {
            "scene_type": "design_talk",
            "confidence": 0.95,
            "stability": 0.9,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "long_term_allowed",
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _artifact(text: str, *, scene: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_relayint_reference_intent_artifact(
        relayscn_artifact=_scene() if scene is None else scene,
        messages=[{"role": "user", "content": text}],
        ctx_hints={},
    )


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assert_native_schema() -> None:
    artifact = _artifact("それを直して")
    require(artifact.get("schema_version") == "relayint.intent.v1", artifact)
    require(artifact.get("runtime_private") is True, artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("request_local") is True, artifact)
    require(artifact.get("relayint_alias") is None, artifact)
    require(artifact.get("source_compat_module") is None, artifact)
    require(artifact.get("schema_version") != "relayref.dry_run_artifact.v0", artifact)
    projection = artifact.get("relayint_projection")
    require(isinstance(projection, dict), artifact)
    require(projection.get("schema_version") == "relayint.projection.v1", projection)
    require(projection.get("content_free") is True, projection)
    require(projection.get("mem_query_allowed") is False, projection)
    print("ok RelayINT direct call returns native artifact/projection")


def _assert_restrictive_reference_behavior() -> None:
    artifact = _artifact("それを直して")
    require(artifact.get("unresolved_reference_detected") is True, artifact)
    require(artifact.get("ambiguity_detected") is True, artifact)
    require(artifact.get("candidate_action") == "ask_clarification", artifact)
    require(artifact.get("mem_query_allowed") is False, artifact)
    require(artifact.get("mem_lookup_executed") is False, artifact)
    require("unresolved_reference_detected" in artifact.get("mode_reasons", []), artifact)
    print("ok ambiguous Japanese reference stays restrictive and non-retrieving")


def _assert_prior_memory_candidate_only() -> None:
    artifact = _artifact("前に話したことを思い出して")
    require(artifact.get("prior_memory_request_detected") is True, artifact)
    require(artifact.get("candidate_action") == "recall_then_answer_candidate", artifact)
    require(artifact.get("mem_query_needed_candidate") is True, artifact)
    require(artifact.get("mem_query_allowed") is False, artifact)
    require(artifact.get("mem_lookup_executed") is False, artifact)
    print("ok prior-memory intent remains candidate-only")


def _assert_fail_closed_scene() -> None:
    artifact = _artifact("続きをお願い", scene={})
    gate = artifact.get("scene_gate")
    require(isinstance(gate, dict), artifact)
    require(gate.get("restrictive_only") is True, artifact)
    require("malformed_relayscn_artifact" in gate.get("block_reasons", []), artifact)
    require(artifact.get("mem_query_allowed") is False, artifact)
    print("ok malformed RelaySCN input fails closed")


def _assert_legacy_entrypoint_is_native() -> None:
    artifact = build_relayint_reference_repair_dry_run(
        relayscn_artifact=_scene(),
        messages=[{"role": "user", "content": "それを直して"}],
        ctx_hints={},
    )
    require(artifact.get("schema_version") == "relayint.intent.v1", artifact)
    require("relayint_alias" not in artifact, artifact)
    require("source_compat_module" not in artifact, artifact)
    print("ok deprecated RelayINT entrypoint returns native schema")


def _assert_relaymem_consumes_native_artifact() -> None:
    artifact = _artifact("それを直して")
    retrieval = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene(),
        relayint_intent_artifact=artifact,
        messages=[{"role": "user", "content": "それを直して"}],
        store_diagnostics={"fallback_reason": "memory_store_read_only_selection_dry_run"},
    )
    require(retrieval.get("fallback_reason") == "unresolved_reference_requires_confirmation", retrieval)
    reasons = [item.get("reason") for item in retrieval.get("blocked", []) if isinstance(item, dict)]
    require("must_not_silently_resolve_ambiguous_reference" in reasons, retrieval)
    print("ok RelayMEM retrieval preserves unresolved-reference blocking with native artifact")


def _assert_projection_content_free() -> None:
    artifact = _artifact("それを直して")
    serialized = _dump({
        "projection": artifact.get("relayint_projection"),
        "reference_intent_analyzer": artifact.get("reference_intent_analyzer"),
        "scene_gate": artifact.get("scene_gate"),
    })
    forbidden = [
        "それを直して",
        "resolved_reference_text",
        "memory_text",
        "scene body",
        "relationship body",
        "runtime/",
        "/tmp/",
    ]
    for needle in forbidden:
        require(needle not in serialized, {"needle": needle, "serialized": serialized})
    print("ok public RelayINT projection is content-free")


def main() -> None:
    _assert_native_schema()
    _assert_restrictive_reference_behavior()
    _assert_prior_memory_candidate_only()
    _assert_fail_closed_scene()
    _assert_legacy_entrypoint_is_native()
    _assert_relaymem_consumes_native_artifact()
    _assert_projection_content_free()


if __name__ == "__main__":
    main()
