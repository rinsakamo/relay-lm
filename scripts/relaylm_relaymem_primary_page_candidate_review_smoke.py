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


def _scene() -> dict[str, Any]:
    return {
        "scene_state": {
            "scene_type": "design_talk",
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


def main() -> int:
    formation = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene(),
        relayemo_artifact={"assistant_emotion_state": {"intensity": 0.8}},
        messages=[{"role": "user", "content": "Continue RelayMEM."}],
        enabled=True,
    )
    require(formation["candidate_count"] == 1, formation)
    candidate = formation["candidates"][0]
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-review-1",
        namespace="character-alpha",
    )
    require(lineage["valid"] is True, lineage)
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    experience = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind="turn",
        namespace="character-alpha",
        summary_text="A bounded review regression summary.",
    )

    mismatched_preflight = dict(preflight)
    mismatched_operation = dict(preflight["operations"][0])
    mismatched_operation["target_category"] = "primary_relationships"
    mismatched_preflight["operations"] = [mismatched_operation]
    mismatched = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=mismatched_preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(mismatched["page_candidate_count"] == 0, mismatched)
    require(
        "primary_write_preflight_memory_kind_target_category_mismatch"
        in mismatched["blocked_reasons"],
        mismatched,
    )
    print("ok mismatched memory kind and target category fail closed")

    content_lineage = dict(lineage)
    content_lineage["content_free"] = False
    content_lineage["content_included"] = True
    content_lineage["raw_text_included"] = True
    blocked_lineage = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=content_lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(blocked_lineage["page_candidate_count"] == 0, blocked_lineage)
    for reason in (
        "source_lineage_content_free_invalid",
        "source_lineage_content_included_invalid",
        "source_lineage_raw_text_included_invalid",
    ):
        require(reason in blocked_lineage["blocked_reasons"], blocked_lineage)
    print("ok content-bearing source lineage fails closed")

    blocked_reasons_lineage = dict(lineage)
    blocked_reasons_lineage["blocked_reasons"] = ["forged_block"]
    blocked_reasons = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=blocked_reasons_lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require("source_lineage_blocked" in blocked_reasons["blocked_reasons"], blocked_reasons)
    print("ok valid lineage cannot carry blocked reasons")

    bool_summary_chars = dict(experience)
    bool_summary_chars["summary_chars"] = True
    blocked_summary_chars = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=bool_summary_chars,
        enabled=True,
    )
    require(
        "governed_experience_summary_chars_mismatch"
        in blocked_summary_chars["blocked_reasons"],
        blocked_summary_chars,
    )
    print("ok boolean summary character counts fail closed")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
