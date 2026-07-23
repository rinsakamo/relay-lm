"""Documentation boundary smoke for Phase I-2 after evidence cutover."""
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
    evidence = "docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md"
    require_text(
        "docs/PROJECT_STATUS.md",
        "SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3",
        "I1-G overall: complete",
        "I1-GE full production crash validation: complete",
    )
    require_text(
        "docs/architecture/project_execution_plan.md",
        "read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence",
        "MVP completion criteria",
    )
    require_text(
        "docs/architecture/relaymem_slp_current_target.md",
        "I2 real SOUL Lab observation is complete",
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
        evidence,
        "relaylm_doc_type: evidence",
        "relaylm_status: frozen",
        "**Historical implementation evidence.**",
        "Lab observation receipts are secondary read-only evidence only",
        "GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...",
    )
    require_text(
        "docs/evidence/implementation/README.md",
        "phase-i2-real-soul-lab-observation-handoff.md",
    )
    require_text("docs/README.md", "phase_i3_auditable_primary_mem_correct.md")
    require_text("docs/architecture/README.md", "phase_i3_auditable_primary_mem_correct.md")
    forbid_text("docs/README.md", "Phase I-2 real SOUL Lab observation")
    forbid_text("docs/architecture/README.md", "Phase I-2 Real SOUL Lab Observation")

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
