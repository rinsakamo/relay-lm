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


def _messages() -> list[dict[str, Any]]:
    return [
        {"role": "assistant", "content": "previous response"},
        {"role": "user", "content": "RelayMEM should form ordinary memories."},
    ]


def _candidate(scene_type: str = "design_talk") -> dict[str, Any]:
    result = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene(scene_type),
        relayemo_artifact={"assistant_emotion_state": {"intensity": 0.81}},
        messages=_messages(),
        enabled=True,
    )
    require(result["candidate_count"] == 1, result)
    return result["candidates"][0]


def _assert_projection_content_free(value: object) -> None:
    text = repr(value)
    forbidden = {
        "RelayMEM should form ordinary memories.",
        "previous response",
        "turn-0001",
        "turn-0002",
        "session-abc",
        "run-abc",
        "character-alpha",
        "memory/mem/primary",
    }
    for token in forbidden:
        require(token not in text, text)


def main() -> int:
    candidate = _candidate()
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-0001",
        namespace="character-alpha",
    )
    require(lineage["schema_version"] == "relaymem.primary_source_lineage.v0", lineage)
    require(lineage["valid"] is True, lineage)
    require(lineage["content_included"] is False, lineage)

    eligible = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
    )
    require(
        eligible["schema_version"] == "relaymem.primary_write_preflight_dry_run.v0",
        eligible,
    )
    require(eligible["diagnostics_only"] is True, eligible)
    require(eligible["helper_only"] is True, eligible)
    require(eligible["read_only"] is True, eligible)
    require(eligible["writes_memory"] is False, eligible)
    require(eligible["mutates_soul"] is False, eligible)
    require(eligible["invokes_slp"] is False, eligible)
    require(eligible["lab_api_exposed"] is False, eligible)
    require(eligible["write_apply_supported"] is False, eligible)
    require(eligible["apply_allowed"] is False, eligible)
    require(eligible["operation_count"] == 1, eligible)
    operation = eligible["operations"][0]
    require(operation["preflight_status"] == "eligible", operation)
    require(operation["target_category"] == "primary_projects", operation)
    require(operation["preflight_apply_eligible"] is False, operation)
    require(len(operation["idempotency_key"]) == 64, operation)
    require(operation["writes_memory"] is False, operation)
    require(operation["applied"] is False, operation)
    require(eligible["projection"]["idempotency_key_included"] is False, eligible)
    require(eligible["projection"]["lineage_fingerprint_included"] is False, eligible)
    _assert_projection_content_free(eligible["projection"])
    print("ok eligible primary write preflight is content-free and dry-run-only")

    same = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    require(
        same["operations"][0]["idempotency_key"] == operation["idempotency_key"],
        same,
    )
    different_lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-0002",
        namespace="character-alpha",
    )
    different = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=different_lineage,
        enabled=True,
    )
    require(
        different["operations"][0]["idempotency_key"] != operation["idempotency_key"],
        different,
    )
    print("ok idempotency key is stable and lineage-sensitive")

    long_prefix = "x" * 128
    long_a = build_relaymem_primary_source_lineage(
        source_event_id=f"{long_prefix}a",
    )
    long_b = build_relaymem_primary_source_lineage(
        source_event_id=f"{long_prefix}b",
    )
    require(long_a["valid"] is False, long_a)
    require(long_b["valid"] is False, long_b)
    require("source_event_id_invalid" in long_a["blocked_reasons"], long_a)
    require(long_a["lineage_fingerprint"] == "", long_a)
    require(long_b["lineage_fingerprint"] == "", long_b)
    print("ok overlong lineage IDs are blocked instead of truncated")

    invalid_kind = build_relaymem_primary_source_lineage(
        source_event_kind="unknown_event",
        source_event_id="turn-0001",
    )
    require(invalid_kind["valid"] is False, invalid_kind)
    require("source_event_kind_invalid" in invalid_kind["blocked_reasons"], invalid_kind)
    print("ok unknown source event kinds fail closed")

    missing_lineage = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=None,
        enabled=True,
    )
    require(missing_lineage["source_lineage_valid"] is False, missing_lineage)
    require("source_lineage_missing" in missing_lineage["blocked_reasons"], missing_lineage)
    require(missing_lineage["operations"][0]["preflight_status"] == "blocked", missing_lineage)
    require(missing_lineage["operations"][0]["idempotency_key"] == "", missing_lineage)
    print("ok missing source lineage blocks preflight keys")

    forged_lineage = dict(lineage)
    forged_lineage["lineage_fingerprint"] = "not-a-sha256"
    forged = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=forged_lineage,
        enabled=True,
    )
    require(forged["source_lineage_valid"] is False, forged)
    require(
        "source_lineage_fingerprint_invalid" in forged["blocked_reasons"],
        forged,
    )
    require(forged["operations"][0]["idempotency_key"] == "", forged)
    print("ok malformed lineage fingerprints fail closed")

    held_candidate = _candidate("system_ops")
    held = build_relaymem_primary_write_preflight_dry_run(
        candidates=[held_candidate],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    require(held["operations"][0]["preflight_status"] == "held", held)
    require(
        "promotion_policy_blocks_autonomous_apply:review_required"
        in held["operations"][0]["blocked_reasons"],
        held,
    )
    print("ok review-required candidates are held")

    held_without_lineage = build_relaymem_primary_write_preflight_dry_run(
        candidates=[held_candidate],
        source_lineage_artifact=None,
        enabled=True,
    )
    require(
        held_without_lineage["operations"][0]["preflight_status"] == "blocked",
        held_without_lineage,
    )
    print("ok missing lineage blocks review-required candidates before hold")

    never_auto = dict(candidate)
    never_auto["promotion_policy"] = "never_auto_promote"
    blocked = build_relaymem_primary_write_preflight_dry_run(
        candidates=[never_auto],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    require(blocked["operations"][0]["preflight_status"] == "blocked", blocked)
    require(
        "promotion_policy_blocks_autonomous_apply:never_auto_promote"
        in blocked["operations"][0]["blocked_reasons"],
        blocked,
    )
    print("ok never-auto-promote candidates are blocked")

    unknown_memory_kind = dict(candidate)
    unknown_memory_kind["memory_kind"] = "unregistered_kind"
    unknown_kind = build_relaymem_primary_write_preflight_dry_run(
        candidates=[unknown_memory_kind],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    require(unknown_kind["operations"][0]["preflight_status"] == "blocked", unknown_kind)
    require(
        "unsupported_memory_kind"
        in unknown_kind["operations"][0]["blocked_reasons"],
        unknown_kind,
    )
    require(unknown_kind["operations"][0]["target_category"] == "unknown", unknown_kind)
    require(unknown_kind["operations"][0]["idempotency_key"] == "", unknown_kind)
    print("ok unknown memory kinds do not inherit a default target category")

    disabled = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=False,
    )
    require(
        "primary_write_preflight_disabled" in disabled["blocked_reasons"],
        disabled,
    )
    require(disabled["operations"][0]["preflight_status"] == "blocked", disabled)
    print("ok disabled write preflight blocks operations")

    apply_gated = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate],
        source_lineage_artifact=lineage,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(apply_gated["apply_allowed"] is False, apply_gated)
    require(apply_gated["write_apply_supported"] is False, apply_gated)
    require(apply_gated["operations"][0]["preflight_apply_eligible"] is True, apply_gated)
    require(apply_gated["operations"][0]["writes_memory"] is False, apply_gated)
    print("ok apply gates only mark preflight eligibility without writes")

    lineage_from_run = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        run_id="run-abc",
        session_id="session-abc",
        turn_index=2,
    )
    require(lineage_from_run["valid"] is True, lineage_from_run)
    _assert_projection_content_free(
        build_relaymem_primary_write_preflight_dry_run(
            candidates=[candidate],
            source_lineage_artifact=lineage_from_run,
            enabled=True,
        )["projection"]
    )
    print("ok run/session lineage is accepted without public id leakage")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
