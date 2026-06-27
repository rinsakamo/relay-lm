"""Documentation boundary smoke for Phase I-2 without over-pinning later phases."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_text(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required boundary: {needle}")


def forbid_text(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        if needle in text:
            raise AssertionError(f"{path}: stale boundary remains: {needle}")


def main() -> None:
    handoff = "phase_i2_real_soul_lab_observation.md"
    require_text(
        "docs/PROJECT_STATUS.md",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "I1-G",
        "I1-GA through I1-GD durable-finalization boundary",
        "Visible-release restart evidence publication is implemented",
        "Restart-time one-record replay",
    )
    require_text(
        "docs/architecture/project_execution_plan.md",
        "read-only observation of latest runs, formed memory, held or blocked outcomes, and used-memory evidence",
        "MVP completion criteria",
    )
    require_text(
        "docs/architecture/pipeline_implementation_plan.md",
        "relaylm_doc_type: redirect_stub",
        "This file is a compatibility stub.",
    )
    require_text(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "relaylm_doc_type: redirect_stub",
        "This file is a compatibility stub.",
    )
    require_text(
        "docs/architecture/relaymem_slp_current_target.md",
        "I2 real SOUL Lab observation: complete",
        "cannot authorize repair or retrieval",
    )
    require_text(
        "docs/architecture/soul_lab_ui_mvp.md",
        "Phase I-2 provides real latest-run, formed/held/blocked, and used-memory evidence",
        "Real and preview data are never combined automatically",
        "AbortSignal",
    )
    require_text(
        "docs/architecture/soul_lab_runtime_mvp.md",
        "Phase I-2 does not implement the Runtime MVP adapter layer",
        "Observation receipt failure",
    )
    require_text(
        "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
        "UI-A7 settings or characters responses",
        "content-free schemas",
    )
    require_text(
        "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
        "Phase I-2 observes this path",
        "observation receipt",
    )
    require_text(
        "docs/architecture/phase_i2_real_soul_lab_observation.md",
        "Lab observation receipts are secondary read-only evidence only",
        "GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...",
    )
    require_text("docs/README.md", handoff, "phase_i3_auditable_primary_mem_correct.md")
    require_text("docs/architecture/README.md", handoff, "phase_i3_auditable_primary_mem_correct.md")

    for path in (
        "docs/PROJECT_STATUS.md",
        "docs/README.md",
        "docs/architecture/README.md",
        "docs/architecture/project_execution_plan.md",
        "docs/architecture/pipeline_implementation_plan.md",
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "docs/architecture/relaymem_slp_current_target.md",
    ):
        forbid_text(
            path,
            "SOUL Lab real observation is next",
            "latest-run and memory-outcome reads: pending",
            "real SOUL Lab observation of formed and used memory",
        )

    print("Phase I-2 documentation boundary smoke passed")


if __name__ == "__main__":
    main()
