from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaysoul_patch import RelaySOULPatchCandidate, build_relaysoul_patch_candidate_dry_run


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    runtime_ok = {"feedback_status": "ok", "stable_prefix_hash_present": True}
    budget_ok = {"budget_status": "ok", "source_budget_ratios": {"character_output_policy": 0.5, "relationship_anchor": 0.4}}

    ok_candidate = RelaySOULPatchCandidate(
        candidate_id="c1",
        mode="calibration",
        target_files=["OUTPUT_POLICY.md", "RELATIONSHIP_ANCHOR.md"],
        feedback_ids=["f1"],
        feedback_labels=["warmth"],
        freeform_notes_present=False,
    )
    ok = build_relaysoul_patch_candidate_dry_run(ok_candidate, runtime_ok, budget_ok).to_log_dict()
    require(ok["dry_run_status"] == "ok", ok)
    print("ok calibration candidate passes")

    blocked_soul = RelaySOULPatchCandidate(
        candidate_id="c2",
        mode="normal_chat",
        target_files=["SOUL.md"],
        feedback_ids=["f1"],
        feedback_labels=[],
        freeform_notes_present=False,
    )
    blocked = build_relaysoul_patch_candidate_dry_run(blocked_soul, runtime_ok, budget_ok).to_log_dict()
    require(blocked["dry_run_status"] == "blocked", blocked)
    require("soul_patch_not_allowed_in_normal_chat" in blocked["blocking_reasons"], blocked)
    print("ok normal_chat soul patch blocked")

    unsupported_target = RelaySOULPatchCandidate(
        candidate_id="c3",
        mode="calibration",
        target_files=["UNKNOWN.md"],
        feedback_ids=[],
        feedback_labels=[],
        freeform_notes_present=False,
    )
    blocked_t = build_relaysoul_patch_candidate_dry_run(unsupported_target, runtime_ok, budget_ok).to_log_dict()
    require("unsupported_target_file" in blocked_t["blocking_reasons"], blocked_t)
    print("ok unsupported target blocked")

    unsupported_mode = RelaySOULPatchCandidate(
        candidate_id="c4",
        mode="review",
        target_files=["OUTPUT_POLICY.md"],
        feedback_ids=[],
        feedback_labels=[],
        freeform_notes_present=False,
    )
    blocked_m = build_relaysoul_patch_candidate_dry_run(unsupported_mode, runtime_ok, budget_ok).to_log_dict()
    require("unsupported_mode" in blocked_m["blocking_reasons"], blocked_m)
    print("ok unsupported mode blocked")

    runtime_warning = {"feedback_status": "warning", "stable_prefix_hash_present": False}
    warn = build_relaysoul_patch_candidate_dry_run(ok_candidate, runtime_warning, budget_ok).to_log_dict()
    require(warn["dry_run_status"] == "warning", warn)
    require("runtime_feedback_warning" in warn["warning_reasons"], warn)
    print("ok runtime feedback warning propagated")

    budget_warning = {
        "budget_status": "warning",
        "source_budget_ratios": {"scene_state": 1.5},
    }
    scene_candidate = RelaySOULPatchCandidate(
        candidate_id="c5",
        mode="calibration",
        target_files=["SCENE_STATE.md"],
        feedback_ids=[],
        feedback_labels=[],
        freeform_notes_present=False,
    )
    over = build_relaysoul_patch_candidate_dry_run(scene_candidate, runtime_ok, budget_warning).to_log_dict()
    require("persona_source_budget_warning" in over["warning_reasons"], over)
    require(over["target_budget_status"]["SCENE_STATE.md"] == "over_budget", over)
    require("patch_text" not in str(over), over)
    print("ok over-budget target flagged and content-free")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
