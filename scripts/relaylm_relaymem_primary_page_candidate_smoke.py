from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_formation import (
    build_relaymem_primary_formation_dry_run,
)
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _scene(scene_type: str) -> dict[str, Any]:
    return {
        "scene_state": {
            "scene_type": scene_type,
            "confidence": 0.92,
            "stability": 0.88,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": False,
            "persistence_block_reasons": [],
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _candidate(scene_type: str = "design_talk") -> dict[str, Any]:
    result = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene(scene_type),
        relayemo_artifact={"assistant_emotion_state": {"intensity": 0.81}},
        messages=[
            {"role": "assistant", "content": "previous response"},
            {"role": "user", "content": "Continue the RelayMEM implementation."},
        ],
        enabled=True,
    )
    require(result["candidate_count"] == 1, result)
    return result["candidates"][0]


def _lineage(namespace: str = "character-alpha") -> dict[str, Any]:
    artifact = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-0001",
        namespace=namespace,
    )
    require(artifact["valid"] is True, artifact)
    return artifact


def _preflight(
    candidate: dict[str, Any],
    lineage: dict[str, Any],
) -> dict[str, Any]:
    return build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )


def _experience(
    candidate: dict[str, Any],
    namespace: str = "character-alpha",
) -> dict[str, Any]:
    return build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind=candidate["source_event_kind"],
        namespace=namespace,
        title="RelayMEM M3c progress",
        summary_text=(
            "A bounded Primary MEM page candidate contract was prepared "
            "without writing durable memory."
        ),
    )


def main() -> int:
    candidate = _candidate()
    lineage = _lineage()
    preflight = _preflight(candidate, lineage)
    experience = _experience(candidate)

    ready = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(
        ready["schema_version"] == "relaymem.primary_page_candidate_dry_run.v0",
        ready,
    )
    require(ready["diagnostics_only"] is True, ready)
    require(ready["helper_only"] is True, ready)
    require(ready["read_only"] is True, ready)
    require(ready["writes_memory"] is False, ready)
    require(ready["write_apply_supported"] is False, ready)
    require(ready["apply_allowed"] is False, ready)
    require(ready["mutates_soul"] is False, ready)
    require(ready["invokes_slp"] is False, ready)
    require(ready["lab_api_exposed"] is False, ready)
    require(ready["page_candidate_count"] == 1, ready)

    page = ready["page_candidates"][0]
    require(page["status"] == "ready", page)
    require(page["target_category"] == "primary_projects", page)
    require(
        page["target_relative_path"].startswith("memory/mem/primary/projects/"),
        page,
    )
    require(page["target_relative_path"].endswith(".md"), page)
    require(len(page["idempotency_key"]) == 64, page)
    require(len(page["lineage_fingerprint"]) == 64, page)
    require(len(page["page_digest"]) == 64, page)
    require(page["writer_handoff_eligible"] is False, page)
    require(page["writes_memory"] is False, page)
    require(page["applied"] is False, page)
    require("bounded Primary MEM page candidate" in page["page_markdown"], page)
    require("raw_affect" not in page["page_markdown"], page)

    projection_text = repr(ready["projection"])
    for forbidden in (
        experience["summary_text"],
        experience["title"],
        candidate["candidate_id"],
        lineage["namespace"],
        page["target_relative_path"],
        page["idempotency_key"],
        page["lineage_fingerprint"],
        page["page_digest"],
    ):
        require(forbidden not in projection_text, ready["projection"])
    require(ready["projection"]["content_free"] is True, ready)
    require(ready["projection"]["candidate_id_included"] is False, ready)
    require(ready["projection"]["target_path_included"] is False, ready)
    print("ok M3c page candidate is runtime-private and projection-safe")

    repeated = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    repeated_page = repeated["page_candidates"][0]
    require(
        repeated_page["target_relative_path"] == page["target_relative_path"],
        repeated,
    )
    require(repeated_page["page_digest"] == page["page_digest"], repeated)
    print("ok M3c page candidate serialization is deterministic")

    handoff = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(handoff["page_candidates"][0]["writer_handoff_eligible"] is True, handoff)
    require(handoff["writes_memory"] is False, handoff)
    require(handoff["apply_allowed"] is False, handoff)
    print("ok explicit gates only mark writer handoff eligibility")

    disabled = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=False,
    )
    require(disabled["page_candidate_count"] == 0, disabled)
    require("primary_page_candidate_disabled" in disabled["blocked_reasons"], disabled)
    print("ok disabled M3c blocks page candidates")

    mismatched_namespace = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=_experience(candidate, namespace="other"),
        enabled=True,
    )
    require(mismatched_namespace["page_candidate_count"] == 0, mismatched_namespace)
    require(
        "primary_page_candidate_namespace_mismatch"
        in mismatched_namespace["blocked_reasons"],
        mismatched_namespace,
    )
    print("ok lineage namespace mismatch fails closed")

    forged_preflight = dict(preflight)
    forged_operation = dict(preflight["operations"][0])
    forged_operation["idempotency_key"] = "0" * 64
    forged_preflight["operations"] = [forged_operation]
    forged = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=forged_preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(forged["page_candidate_count"] == 0, forged)
    require(
        "primary_page_candidate_idempotency_key_mismatch"
        in forged["blocked_reasons"],
        forged,
    )
    print("ok forged preflight idempotency key fails closed")

    content_bearing_preflight = dict(preflight)
    content_bearing_operation = dict(preflight["operations"][0])
    content_bearing_operation["content_included"] = True
    content_bearing_preflight["operations"] = [content_bearing_operation]
    content_bearing = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=content_bearing_preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(content_bearing["page_candidate_count"] == 0, content_bearing)
    require(
        "primary_write_preflight_content_included_invalid"
        in content_bearing["blocked_reasons"],
        content_bearing,
    )
    print("ok content-bearing preflight operations are rejected")

    held_candidate = _candidate("system_ops")
    held_lineage = _lineage()
    held = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=_preflight(held_candidate, held_lineage),
        source_lineage_artifact=held_lineage,
        governed_experience_artifact=_experience(held_candidate),
        enabled=True,
    )
    require(held["page_candidate_count"] == 0, held)
    require(
        "primary_write_preflight_preflight_status_invalid"
        in held["blocked_reasons"],
        held,
    )
    print("ok held preflight operations cannot become page candidates")

    raw_source = dict(experience)
    raw_source["raw_source_text_included"] = True
    blocked_raw = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=raw_source,
        enabled=True,
    )
    require(blocked_raw["page_candidate_count"] == 0, blocked_raw)
    require(
        "governed_experience_raw_source_text_included_invalid"
        in blocked_raw["blocked_reasons"],
        blocked_raw,
    )
    print("ok raw source text artifacts are rejected")

    overlong = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind="turn",
        namespace="character-alpha",
        summary_text="x" * 2049,
    )
    require(overlong["valid"] is False, overlong)
    require(
        "governed_experience_summary_invalid" in overlong["blocked_reasons"],
        overlong,
    )
    control = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind="turn",
        namespace="character-alpha",
        summary_text="invalid\0summary",
    )
    require(control["valid"] is False, control)
    surrogate = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind="turn",
        namespace="character-alpha",
        summary_text="invalid\ud800summary",
    )
    require(surrogate["valid"] is False, surrogate)
    require(
        "governed_experience_summary_invalid" in surrogate["blocked_reasons"],
        surrogate,
    )
    surrogate_result = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=surrogate,
        enabled=True,
    )
    require(surrogate_result["page_candidate_count"] == 0, surrogate_result)
    print("ok surrogate text is rejected before UTF-8 serialization")
    print("ok governed summaries are bounded and control-safe")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
