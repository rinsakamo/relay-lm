#!/usr/bin/env python3
"""Build a RelaySOUL patch-generation prompt artifact in dry-run mode.

This script is schema/tooling support only:
- no model API calls
- no patch application
- no persona source mutation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mvp-soul-0"
DEFAULT_FEEDBACK_PATH = "examples/relaysoul/feedback_examples.json"


class FeedbackShapeError(ValueError):
    """Raised when feedback JSON does not match expected minimal shape."""


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_feedback(path: str | Path) -> list[dict[str, Any]]:
    feedback_path = Path(path)
    data = json.loads(feedback_path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list):
        raise FeedbackShapeError(
            f"Feedback JSON must include list field 'items': {feedback_path}"
        )

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise FeedbackShapeError(
                f"Feedback item at index {idx} must be an object: {feedback_path}"
            )
        normalized.append(item)
    return normalized


def format_feedback_block(feedback_items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for idx, item in enumerate(feedback_items, start=1):
        labels = item.get("feedback_labels")
        label_text = ", ".join(labels) if isinstance(labels, list) else ""
        lines.extend(
            [
                f"### Feedback Example {idx}",
                f"feedback_id: {item.get('feedback_id', '')}",
                f"calibration_id: {item.get('calibration_id', '')}",
                f"prompt_kind: {item.get('prompt_kind', '')}",
                f"character_id: {item.get('character_id', '')}",
                f"user_id: {item.get('user_id', '')}",
                f"scene_id: {item.get('scene_id', '')}",
                f"preferred_response: {item.get('preferred_response', '')}",
                f"rejected_response: {item.get('rejected_response', '')}",
                f"feedback_labels: {label_text}",
                f"notes: {item.get('notes', '')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_prompt_text(
    *,
    soul: str,
    output_policy: str,
    relationship_anchor: str | None,
    stable_memory_summary: str | None,
    scene_state: str | None,
    feedback_items: list[dict[str, Any]],
) -> str:
    relationship_text = relationship_anchor if relationship_anchor else "(not provided)"
    stable_memory_text = stable_memory_summary if stable_memory_summary else "(not provided)"
    scene_state_text = scene_state if scene_state else "(not provided)"
    feedback_block = format_feedback_block(feedback_items)

    return f"""You are generating RelaySOUL patch candidates in DRY-RUN mode.

# Safety and scope constraints
- This is patch-generation prompt dry-run only.
- do not auto-apply any patch.
- Do not mutate persona source files.
- Generate minimal patches.
- Prefer replacement/consolidation/compression over unbounded growth.
- SOUL.md updates are high-risk and approval-gated.
- Use SCENE_STATE.md / scene_state terminology.
- Do not introduce ROOM_STATE.md terminology.

# Patch target rules
- Prefer OUTPUT_POLICY.md for tone, warmth, verbosity, response style, and memory-disclosure phrasing.
- Prefer RELATIONSHIP_ANCHOR.md for relationship distance, familiarity, trust expectations, and user-specific relational norms.
- Prefer SOUL.md only for durable persona core, values, worldview, identity, and invariants.
- Prefer SCENE_STATE.md or runtime overlay for temporary mood, situation, and short-lived direction.
- Propose no change when current persona sources already explain user preference.

# Persona Source Budget guidance
persona_source_budget:
  soul_max_tokens: 800
  output_policy_max_tokens: 600
  relationship_anchor_max_tokens: 500
  stable_memory_summary_max_tokens: 1000
  scene_state_max_tokens: 300

Budget rules:
- Keep persona sources legible and bounded.
- Prefer replacing/consolidating lines over appending new rules.
- If a candidate would exceed budget, propose compression instead.

# Current persona source contents
## SOUL.md
{soul}

## OUTPUT_POLICY.md
{output_policy}

## RELATIONSHIP_ANCHOR.md
{relationship_text}

## STABLE_MEMORY_SUMMARY.md
{stable_memory_text}

## SCENE_STATE.md
{scene_state_text}

# Feedback examples (preferred/rejected)
{feedback_block}

# Output request
Return patch candidates only (dry-run). For each candidate include:
- target_file
- target_block
- operation
- reason
- patch_text
- source_feedback_ids
- risk_level
- requires_user_approval
- budget_effect
- stable_prefix_change_expected
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feedback", default=DEFAULT_FEEDBACK_PATH)
    parser.add_argument("--soul", required=True)
    parser.add_argument("--output-policy", required=True)
    parser.add_argument("--relationship-anchor")
    parser.add_argument("--stable-memory-summary")
    parser.add_argument("--scene-state")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    feedback_items = load_feedback(args.feedback)
    soul_text = read_text(args.soul)
    output_policy_text = read_text(args.output_policy)
    relationship_anchor_text = read_text(args.relationship_anchor) if args.relationship_anchor else None
    stable_memory_summary_text = read_text(args.stable_memory_summary) if args.stable_memory_summary else None
    scene_state_text = read_text(args.scene_state) if args.scene_state else None

    warnings: list[str] = []
    if not args.relationship_anchor:
        warnings.append("relationship_anchor_not_provided")
    if not args.stable_memory_summary:
        warnings.append("stable_memory_summary_not_provided")
    if not args.scene_state:
        warnings.append("scene_state_not_provided")

    prompt_text = build_prompt_text(
        soul=soul_text,
        output_policy=output_policy_text,
        relationship_anchor=relationship_anchor_text,
        stable_memory_summary=stable_memory_summary_text,
        scene_state=scene_state_text,
        feedback_items=feedback_items,
    )

    artifact = {
        "artifact_type": "relaysoul_patch_prompt_dry_run",
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "feedback": args.feedback,
            "soul": args.soul,
            "output_policy": args.output_policy,
            "relationship_anchor": args.relationship_anchor,
            "stable_memory_summary": args.stable_memory_summary,
            "scene_state": args.scene_state,
        },
        "persona_sources": {
            "soul_chars": len(soul_text),
            "output_policy_chars": len(output_policy_text),
            "relationship_anchor_chars": len(relationship_anchor_text) if relationship_anchor_text else 0,
            "stable_memory_summary_chars": len(stable_memory_summary_text) if stable_memory_summary_text else 0,
            "scene_state_chars": len(scene_state_text) if scene_state_text else 0,
        },
        "feedback_count": len(feedback_items),
        "prompt_text": prompt_text,
        "warnings": warnings,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
