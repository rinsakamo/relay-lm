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


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _scene(scene_type: str, *, persistence_block: bool = False) -> dict[str, Any]:
    return {
        "scene_state": {
            "scene_type": scene_type,
            "confidence": 0.92,
            "stability": 0.88,
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
            "persistence_block": persistence_block,
            "persistence_block_reasons": ["policy_block"]
            if persistence_block
            else [],
        },
        "persistence_block": persistence_block,
        "persistence_block_reasons": ["artifact_block"]
        if persistence_block
        else [],
    }


def _messages() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "ignored for source counts"},
        {"role": "assistant", "content": "previous response"},
        {"role": "user", "content": "RelayMEM should form ordinary memories."},
    ]


def _relayemo() -> dict[str, Any]:
    return {
        "assistant_emotion_state": {"intensity": 0.81},
        "user_affect_estimate": {"confidence": 0.62, "mode": "positive"},
    }


def _assert_no_content(value: object) -> None:
    text = repr(value)
    forbidden = {
        "RelayMEM should form ordinary memories.",
        "previous response",
        "positive",
        "ignored for source counts",
    }
    for token in forbidden:
        require(token not in text, text)


def main() -> int:
    eligible = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene("design_talk"),
        relayemo_artifact=_relayemo(),
        messages=_messages(),
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
    )
    require(eligible["schema_version"] == "relaymem.primary_formation_dry_run.v0", eligible)
    require(eligible["diagnostics_only"] is True, eligible)
    require(eligible["helper_only"] is True, eligible)
    require(eligible["writes_memory"] is False, eligible)
    require(eligible["mutates_soul"] is False, eligible)
    require(eligible["invokes_slp"] is False, eligible)
    require(eligible["apply_allowed"] is False, eligible)
    require(eligible["candidate_count"] == 1, eligible)
    candidate = eligible["candidates"][0]
    require(candidate["memory_layer"] == "primary", candidate)
    require(candidate["memory_kind"] == "recent_project_event", candidate)
    require(candidate["promotion_policy"] == "free_to_update", candidate)
    require(candidate["safety_scope"] == "ordinary_memory", candidate)
    require(candidate["salience_band"] == "high", candidate)
    require(candidate["stability_band"] == "high", candidate)
    require(candidate["content_included"] is False, candidate)
    require(candidate["raw_text_included"] is False, candidate)
    require(candidate["raw_affect_estimates_included"] is False, candidate)
    require(eligible["source_summary"]["latest_user_message_chars"] > 0, eligible)
    _assert_no_content(eligible["projection"])
    print("ok eligible ordinary primary MEM candidate is content-free")

    disabled = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene("design_talk"),
        relayemo_artifact=_relayemo(),
        messages=_messages(),
        enabled=False,
    )
    require(disabled["candidate_count"] == 0, disabled)
    require("primary_formation_disabled" in disabled["blocked_reasons"], disabled)
    print("ok disabled helper does not form candidates")

    blocked = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene("medical_or_safety"),
        relayemo_artifact=_relayemo(),
        messages=_messages(),
        enabled=True,
    )
    require(blocked["candidate_count"] == 0, blocked)
    require(
        "scene_policy_blocks_persistence:medical_or_safety"
        in blocked["blocked_reasons"],
        blocked,
    )
    require(blocked["projection"]["candidate_count"] == 0, blocked)
    _assert_no_content(blocked["projection"])
    print("ok medical/safety scene blocks autonomous primary MEM formation")

    held = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact=_scene("system_ops"),
        relayemo_artifact=None,
        messages=_messages(),
        enabled=True,
    )
    require(held["candidate_count"] == 1, held)
    require(held["candidates"][0]["promotion_policy"] == "review_required", held)
    require(held["candidates"][0]["safety_scope"] == "held_for_review", held)
    require(held["candidates"][0]["salience_band"] == "unknown", held)
    print("ok non-ordinary system ops candidate is held for review")

    malformed = build_relaymem_primary_formation_dry_run(
        relayscn_scene_policy_artifact={"bad": "shape"},
        relayemo_artifact=_relayemo(),
        messages=_messages(),
        enabled=True,
    )
    require(malformed["candidate_count"] == 0, malformed)
    require("scene_policy_blocks_memory" in malformed["blocked_reasons"], malformed)
    require("malformed_relayscn_artifact" in malformed["blocked_reasons"], malformed)
    print("ok malformed RelaySCN policy fails closed")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
