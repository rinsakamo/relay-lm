#!/usr/bin/env python3
"""Static contract checks for consolidated smoke workflow definitions."""

from __future__ import annotations

from pathlib import Path

import yaml

from relaylm_ci_consolidated_smoke import COMMANDS, GROUPS, changed_outputs

ROOT = Path(__file__).resolve().parents[1]

PURE_UI_GROUPS = {
    "soul_lab_build",
    "lab_observation_frontend",
    "primary_mem_correct_frontend",
    "home_conversation_frontend",
    "forget_lifecycle_frontend",
}

WORKFLOW_PATH_REQUIREMENTS = {
    ".github/workflows/smoke-relaymem.yml": {
        "docs/evidence/implementation/o1d2_completion_report.md",
        "docs/evidence/implementation/i4e_completion_report.md",
        "docs/evidence/implementation/i5a_completion_report.md",
        "docs/evidence/implementation/i1ge_completion_report.md",
        "docs/evidence/implementation/i4d_completion_report.md",
        "docs/evidence/implementation/o1d1_completion_report.md",
    },
    ".github/workflows/smoke-runtime.yml": {
        "docs/evidence/implementation/e1r1_completion_report.md",
        "docs/evidence/implementation/e1r2_completion_report.md",
    },
    ".github/workflows/smoke-ui.yml": {
        "docs/evidence/implementation/i4e_completion_report.md",
        "docs/evidence/implementation/ui_b1a_completion_report.md",
        "docs/evidence/implementation/i5a_completion_report.md",
        "docs/evidence/implementation/i7ab_completion_report.md",
    },
}

WORKFLOW_JOBS = {
    ".github/workflows/smoke-relaymem.yml": {
        "changes",
        "primary-memory",
        "slp-queue",
        "durable-finalization",
        "scheduler-worker",
        "recall-correction-forget-pin",
        "cross-slice-convergence",
    },
    ".github/workflows/smoke-runtime.yml": {"changes", "smoke"},
    ".github/workflows/smoke-ui.yml": {
        "changes",
        "python-smoke",
        "frontend-smoke",
        "mixed-smoke",
    },
}


def fail(message: str) -> None:
    raise AssertionError(message)


def check_group_coverage() -> None:
    for workflow, groups in GROUPS.items():
        command_groups = COMMANDS.get(workflow, {})
        for group in groups:
            if workflow == "ui" and group in PURE_UI_GROUPS:
                continue
            if group not in command_groups:
                fail(f"missing command group: {workflow}/{group}")


def check_command_paths() -> None:
    for workflow, groups in COMMANDS.items():
        for group, commands in groups.items():
            if not commands:
                fail(f"empty command group: {workflow}/{group}")
            for command in commands:
                if not command:
                    fail(f"empty command in {workflow}/{group}")
                first = command[0]
                if first == "-m":
                    continue
                path = ROOT / first
                if not path.is_file():
                    fail(f"missing command path in {workflow}/{group}: {first}")


def check_change_selection() -> None:
    selected = changed_outputs(
        "relaymem",
        ["docs/mvp/wave3/i4d_completion_report.md"],
        False,
    )
    if any(selected.values()):
        fail(
            "retired Wave 3 path unexpectedly selected a live relaymem group: "
            f"{[g for g, v in selected.items() if v]!r}"
        )

    for workflow, groups in GROUPS.items():
        for group, patterns in groups.items():
            if any(pattern.startswith("docs/mvp/wave4/") for pattern in patterns):
                fail(f"retired docs/mvp/wave4/ selector still present in {workflow}/{group}")

    for workflow in GROUPS:
        selected = changed_outputs(
            workflow,
            ["docs/evidence/implementation/docs_execution_plan_consolidation_completion_report.md"],
            False,
        )
        if any(selected.values()):
            fail(
                "canonical docs-execution-plan report unexpectedly selected a "
                f"{workflow} group: {[g for g, v in selected.items() if v]!r}"
            )

    selected = changed_outputs(
        "relaymem",
        ["relaylm/relaymem_primary_page_writer.py"],
        False,
    )
    if not selected["primary_memory"]:
        fail("primary-memory change did not select primary_memory")
    if selected["slp_queue"]:
        fail("primary-memory-only change unexpectedly selected slp_queue")

    selected = changed_outputs(
        "runtime",
        ["relaylm/token_budget.py"],
        False,
    )
    if not selected["token_estimation"]:
        fail("token change did not select token_estimation")
    if selected["e1r2_character_store_bootstrap"]:
        fail("token-only change unexpectedly selected E1-R2")

    selected = changed_outputs(
        "runtime",
        ["docs/evidence/implementation/e1r2_completion_report.md"],
        False,
    )
    if not selected["e1r2_character_store_bootstrap"]:
        fail("canonical E1-R2 evidence change did not select E1-R2")

    selected = changed_outputs(
        "relaymem",
        ["docs/evidence/implementation/o1d2_completion_report.md"],
        False,
    )
    if not selected["scheduler_worker"]:
        fail("canonical O1D2 evidence change did not select scheduler_worker")

    selected = changed_outputs(
        "relaymem",
        ["docs/evidence/implementation/o1d1_completion_report.md"],
        False,
    )
    if not selected["scheduler_worker"]:
        fail("canonical O1D1 evidence change did not select scheduler_worker")
    if selected["recall_correction_forget_pin"]:
        fail("canonical O1D1 evidence change unexpectedly selected recall/correction/forget/pin")

    selected = changed_outputs(
        "relaymem",
        ["docs/evidence/implementation/i1ge_completion_report.md"],
        False,
    )
    if not selected["durable_finalization"]:
        fail("canonical I1-GE evidence change did not select durable_finalization")
    if selected["recall_correction_forget_pin"]:
        fail("canonical I1-GE evidence change unexpectedly selected recall/correction/forget/pin")

    selected = changed_outputs(
        "relaymem",
        [
            "docs/evidence/implementation/i4e_completion_report.md",
            "docs/evidence/implementation/i5a_completion_report.md",
        ],
        False,
    )
    if not selected["recall_correction_forget_pin"]:
        fail("canonical I-4E/I-5A evidence changes did not select recall/correction/forget/pin")

    selected = changed_outputs(
        "relaymem",
        ["docs/evidence/implementation/i4d_completion_report.md"],
        False,
    )
    if not selected["recall_correction_forget_pin"]:
        fail("canonical I-4D evidence change did not select recall/correction/forget/pin")
    if not selected["cross_slice_convergence"]:
        fail("canonical I-4D evidence change did not select cross_slice_convergence")

    expected_ui = {
        "docs/evidence/implementation/i4e_completion_report.md": "forget_lifecycle_regressions",
        "docs/evidence/implementation/ui_b1a_completion_report.md": "lifecycle_visibility",
        "docs/evidence/implementation/i5a_completion_report.md": "pin_unpin",
        "docs/evidence/implementation/i7ab_completion_report.md": "held_governance",
    }
    for path, group in expected_ui.items():
        selected = changed_outputs("ui", [path], False)
        if not selected[group]:
            fail(f"{path} did not select UI group {group}")

    selected = changed_outputs(
        "ui",
        ["apps/soul-lab/src/features/lifecycle/example.ts"],
        False,
    )
    if not selected["soul_lab_build"] or not selected["lifecycle_visibility"]:
        fail("lifecycle UI change did not select build and lifecycle visibility")
    if selected["held_governance"]:
        fail("lifecycle-only change unexpectedly selected held governance")

    for workflow, groups in GROUPS.items():
        selected = changed_outputs(workflow, [], True)
        if set(selected) != set(groups) or not all(selected.values()):
            fail(f"manual dispatch does not select every {workflow} group")


def check_workflow_yaml() -> None:
    for relative, expected_jobs in WORKFLOW_JOBS.items():
        path = ROOT / relative
        if not path.exists():
            if relative != ".github/workflows/smoke-relaymem.yml":
                continue
            fail(f"missing workflow: {relative}")
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = document.get("jobs", {})
        if set(jobs) != expected_jobs:
            fail(
                f"{relative}: unexpected jobs; "
                f"expected={sorted(expected_jobs)} actual={sorted(jobs)}"
            )
        for job_name, job in jobs.items():
            if job_name == "changes":
                continue
            if "timeout-minutes" not in job:
                fail(f"{relative}: {job_name} has no timeout-minutes")


def check_workflow_trigger_paths() -> None:
    for relative, required_paths in WORKFLOW_PATH_REQUIREMENTS.items():
        document = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        triggers = document.get("on", document.get(True, {}))
        for event in ("push", "pull_request"):
            patterns = triggers.get(event, {}).get("paths", [])
            for required in required_paths:
                if not any(Path(required).match(pattern) for pattern in patterns):
                    fail(f"{relative}: {event} does not cover {required}")


def main() -> int:
    check_group_coverage()
    check_command_paths()
    check_change_selection()
    check_workflow_yaml()
    check_workflow_trigger_paths()
    print("consolidated smoke contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
