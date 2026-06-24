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
        "auditable Correct operation: next",
        "I1-G",
        "pre-enqueue background-finalizer",
    )
    require_text(
        "docs/architecture/pipeline_implementation_plan.md",
        "I2 real latest-run and memory observation: complete",
        "observation read model",
    )
    require_text(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "observation receipts",
    )
    require_text(
        "docs/architecture/relaymem_slp_current_target.md",
        "I2 real SOUL Lab observation: complete",
        "cannot authorize repair or retrieval",
    )
    require_text(
        "docs/architecture/soul_lab_ui_mvp.md",
        "Source: RelayLM runtime",
        "Source: Local preview data",
        "AbortController",
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
    require_text("docs/README.md", handoff)
    require_text("docs/architecture/README.md", handoff)

    for path in (
        "docs/PROJECT_STATUS.md",
        "docs/README.md",
        "docs/architecture/README.md",
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
