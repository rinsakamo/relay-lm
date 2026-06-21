from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_formation import build_relaymem_primary_formation_dry_run
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


def _build_result(
    *,
    preflight: dict[str, Any],
    lineage: dict[str, Any],
    experience: dict[str, Any],
) -> dict[str, Any]:
    return build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )


def main() -> int:
    formation = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene(),
        messages=[{"role": "user", "content": "Continue RelayMEM."}],
        enabled=True,
    )
    candidate = formation["candidates"][0]
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-security-1",
        namespace="character-alpha",
    )
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    experience = build_relaymem_governed_experience_summary(
        candidate_id=candidate["candidate_id"],
        source_event_kind="turn",
        namespace="character-alpha",
        summary_text="A bounded security regression summary.",
    )

    ready = _build_result(
        preflight=preflight,
        lineage=lineage,
        experience=experience,
    )
    require(ready["page_candidate_count"] == 1, ready)
    page = ready["page_candidates"][0]
    require(experience["summary_text"] in page["page_markdown"][:512], page)
    print("ok summary evidence remains inside the default snippet window")

    secret_lineage = dict(lineage)
    secret_lineage["valid"] = False
    secret_lineage["blocked_reasons"] = ["SECRET-LINEAGE-RAW-TEXT"]
    result = _build_result(
        preflight=preflight,
        lineage=secret_lineage,
        experience=experience,
    )
    require("SECRET-LINEAGE-RAW-TEXT" not in repr(result["projection"]), result)
    require("source_lineage_invalid" in result["blocked_reasons"], result)

    secret_experience = dict(experience)
    secret_experience["valid"] = False
    secret_experience["blocked_reasons"] = ["SECRET-EXPERIENCE-RAW-TEXT"]
    result = _build_result(
        preflight=preflight,
        lineage=lineage,
        experience=secret_experience,
    )
    require("SECRET-EXPERIENCE-RAW-TEXT" not in repr(result["projection"]), result)
    require("governed_experience_invalid" in result["blocked_reasons"], result)
    print("ok upstream blocked reasons are normalized before projection")

    for key in ("mutates_soul", "invokes_slp", "lab_api_exposed"):
        forged = dict(preflight)
        forged[key] = True
        result = _build_result(
            preflight=forged,
            lineage=lineage,
            experience=experience,
        )
        require(result["page_candidate_count"] == 0, result)
        require(
            f"primary_write_preflight_{key}_invalid" in result["blocked_reasons"],
            result,
        )

    for key in ("mutates_soul", "invokes_slp"):
        forged = dict(preflight)
        operation = dict(preflight["operations"][0])
        operation[key] = True
        forged["operations"] = [operation]
        result = _build_result(
            preflight=forged,
            lineage=lineage,
            experience=experience,
        )
        require(result["page_candidate_count"] == 0, result)
        require(
            f"primary_write_preflight_{key}_invalid" in result["blocked_reasons"],
            result,
        )
    print("ok top-level and operation side-effect flags fail closed")

    numeric_lineage = dict(lineage)
    numeric_lineage["content_free"] = 1
    result = _build_result(
        preflight=preflight,
        lineage=numeric_lineage,
        experience=experience,
    )
    require("source_lineage_content_free_invalid" in result["blocked_reasons"], result)

    numeric_experience = dict(experience)
    numeric_experience["runtime_private"] = 1
    numeric_experience["raw_source_text_included"] = 0
    result = _build_result(
        preflight=preflight,
        lineage=lineage,
        experience=numeric_experience,
    )
    require(
        "governed_experience_runtime_private_invalid" in result["blocked_reasons"],
        result,
    )
    require(
        "governed_experience_raw_source_text_included_invalid"
        in result["blocked_reasons"],
        result,
    )

    numeric_preflight = dict(preflight)
    numeric_preflight["enabled"] = 1
    numeric_preflight["writes_memory"] = 0
    result = _build_result(
        preflight=numeric_preflight,
        lineage=lineage,
        experience=experience,
    )
    require("primary_write_preflight_enabled_invalid" in result["blocked_reasons"], result)
    require(
        "primary_write_preflight_writes_memory_invalid" in result["blocked_reasons"],
        result,
    )

    numeric_operation_preflight = dict(preflight)
    numeric_operation = dict(preflight["operations"][0])
    numeric_operation["content_included"] = 0
    numeric_operation["mutates_soul"] = 0
    numeric_operation_preflight["operations"] = [numeric_operation]
    result = _build_result(
        preflight=numeric_operation_preflight,
        lineage=lineage,
        experience=experience,
    )
    require(
        "primary_write_preflight_content_included_invalid"
        in result["blocked_reasons"],
        result,
    )
    require(
        "primary_write_preflight_mutates_soul_invalid" in result["blocked_reasons"],
        result,
    )
    print("ok numeric stand-ins for boolean contract fields fail closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
