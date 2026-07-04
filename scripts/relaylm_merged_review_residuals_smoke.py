#!/usr/bin/env python3
"""Regression smoke for review findings discovered after merge."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_cache_write import (
    build_client_instruction_cache_write_preflight,
)
from relaylm.client_instruction_extraction import (
    build_client_instruction_extraction_dry_run,
)
from relaylm.client_instruction_identity import build_client_instruction_identity
from relaylm.client_instruction_typed_parse import (
    validate_client_instruction_typed_parse_candidate,
)
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
from relaylm.relaymem_store import build_relaymem_store_diagnostics


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


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


def _primary_candidate() -> dict[str, Any]:
    result = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene(),
        relayemo_artifact={"assistant_emotion_state": {"intensity": 0.81}},
        messages=[
            {"role": "assistant", "content": "previous response"},
            {"role": "user", "content": "Continue the RelayMEM implementation."},
        ],
        enabled=True,
    )
    require(result["candidate_count"] == 1, result)
    return dict(result["candidates"][0])


def test_m3c_operation_index() -> None:
    first = _primary_candidate()
    second = dict(first)
    second["candidate_id"] = f"{first['candidate_id']}-second"
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-review-residuals",
        namespace="character-review",
    )
    require(lineage["valid"] is True, lineage)
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[first, second],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    require(preflight["operation_count"] == 2, preflight)
    experience = build_relaymem_governed_experience_summary(
        candidate_id=second["candidate_id"],
        source_event_kind=second["source_event_kind"],
        namespace="character-review",
        title="Second operation",
        summary_text="The second M3b operation must retain its original index.",
    )
    result = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(result["page_candidate_count"] == 1, result)
    projected = result["projection"]["page_candidates"]
    require(len(projected) == 1, result)
    require(projected[0]["operation_index"] == 1, result)
    print("ok M3c preserves the source M3b operation index")


def test_store_validation_budget() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        sources = root / "memory" / "sources" / "conversations"
        pages = root / "memory" / "mem" / "primary" / "sessions"
        secondary = root / "memory" / "mem" / "secondary" / "projects"
        sources.mkdir(parents=True)
        pages.mkdir(parents=True)
        secondary.mkdir(parents=True)
        for index in range(70):
            (sources / f"conversation-{index:03d}.jsonl").write_text(
                '{"event":"bounded"}\n', encoding="utf-8"
            )
        target = pages / "session.md"
        target.write_text("# Retained primary page\n", encoding="utf-8")

        result = build_relaymem_store_diagnostics(
            root_path=str(root),
            store_enabled=True,
            retrieval_dry_run_only=True,
        )
        relative = target.relative_to(root).as_posix()
        require(relative in result["page_paths"], result)
        require(result["pages_discovered"] == 1, result)
        require(result["fallback_reason"] == "memory_store_validation_truncated", result)
        require(result["layout_compatibility"]["target_primary_secondary_present"] is True, result)
        require(result["validation"]["files_validated"] == 64, result)
        require(result["validation"]["validation_truncated"] is True, result)
        require(result["validation"]["full_tree_materialized"] is False, result)
        print("ok validation truncation preserves validated MEM pages before source overflow")


def _typed_parse_candidate() -> dict[str, Any]:
    return {
        "scene_type": "implementation_work",
        "scene_role": {
            "role_name": "review fixer",
            "role_scope": "scene",
            "confidence": 0.95,
        },
        "scene_context": {
            "setting": "repository review",
            "task": "close merged review findings",
            "participants": ["maintainer"],
        },
        "scene_constraints": [
            {"constraint_type": "response_length", "value": "bounded"}
        ],
        "durable_persona_candidates": [
            {
                "candidate_kind": "value",
                "normalized_value": "fail closed on version drift",
                "confidence": 0.8,
            }
        ],
        "blocked_instruction_kinds": ["runtime_policy_override"],
    }


def _identity() -> Any:
    payload = {
        "messages": [
            {"role": "system", "content": "system instruction"},
            {"role": "developer", "content": "developer instruction"},
            {"role": "user", "content": "user input"},
        ]
    }
    extraction = build_client_instruction_extraction_dry_run(
        payload,
        enabled=True,
        managed_route=True,
    )
    result = build_client_instruction_identity(
        payload,
        extraction,
        enabled=True,
        route_model="relaylm-review-route",
        character_id="relaylm-review-character",
        parser_version=None,
    )
    require(result is not None and result.ready is True, result)
    return result


def test_parser_version_write_block() -> None:
    parse_result = validate_client_instruction_typed_parse_candidate(
        _typed_parse_candidate(),
        enabled=True,
        parser_version="typed-parser-v1",
    )
    require(parse_result is not None and parse_result.parse_ready is True, parse_result)
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_root = Path(temp_dir)
        result = build_client_instruction_cache_write_preflight(
            parse_result=parse_result,
            identity_result=_identity(),
            enabled=True,
            dry_run_only=False,
            managed_route=True,
            route_model="relaylm-review-route",
            character_id="relaylm-review-character",
            cache_root=cache_root,
        )
        require(result is not None and result.status == "blocked", result)
        require(
            "source_typed_parse_parser_version_not_runtime_compatible"
            in result.blocked_reasons,
            result,
        )
        require(result.cache_entry_candidate_built is False, result)
        require(result.cache_write_attempted is False, result)
        require(not any(cache_root.iterdir()), list(cache_root.iterdir()))
        print("ok parser-versioned typed parses cannot become unversioned cache entries")


def main() -> int:
    test_m3c_operation_index()
    test_store_validation_budget()
    test_parser_version_write_block()
    print("ok merged review residual regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
