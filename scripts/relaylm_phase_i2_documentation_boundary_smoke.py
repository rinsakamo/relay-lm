"""Validate the frozen Phase I-2 evidence cutover without owning current-status prose."""
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
        "docs/architecture/soul_lab_ui_mvp.md",
        "Phase I-2",
        "Real and preview data are never combined automatically",
        "AbortSignal",
    )
    require_text(
        "docs/architecture/soul_lab_runtime_mvp.md",
        "Phase I-2",
        "Observation receipt failure",
    )
    require_text(
        "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
        "UI-A7",
        "content-free schemas",
    )
    require_text(
        "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
        "Phase I-2",
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
    forbid_text("docs/README.md", "Phase I-2 real SOUL Lab observation")
    forbid_text("docs/architecture/README.md", "Phase I-2 Real SOUL Lab Observation")

    for path in (
        "docs/README.md",
        "docs/architecture/README.md",
        "docs/architecture/project_execution_plan.md",
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
