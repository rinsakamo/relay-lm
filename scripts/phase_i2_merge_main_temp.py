from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor: {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def normalize_i1g(path: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    replacements = (
        (
            "the pre-enqueue background-finalizer crash window",
            "I1-G, the pre-enqueue background-finalizer crash window",
        ),
        (
            "The pre-enqueue background-finalizer crash window",
            "I1-G, the pre-enqueue background-finalizer crash window",
        ),
        (
            "pre-enqueue background-task crash window",
            "I1-G pre-enqueue background-finalizer durability gap",
        ),
        (
            "pre-enqueue background-finalizer crash recovery",
            "I1-G pre-enqueue background-finalizer durability recovery",
        ),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


replace_once(
    "docs/PROJECT_STATUS.md",
    "- Phase I-2 real SOUL Lab latest-run and memory observation integration.\n",
    "- Phase I-2 real SOUL Lab latest-run and memory observation integration,\n"
    "- explicit I1-G tracking for the unresolved pre-enqueue background-finalizer durability boundary.\n",
)
replace_once(
    "docs/PROJECT_STATUS.md",
    "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected\n"
    "Next boundary: Phase I-3 auditable Correct operation\n",
    "SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected\n"
    "I1-G pre-enqueue background-finalizer durability: unresolved\n"
    "Next product boundary: Phase I-3 auditable Correct operation\n",
)
replace_once(
    "docs/PROJECT_STATUS.md",
    "- I2 real SOUL Lab observation: complete\n"
    "- auditable Correct operation: next as Phase I-3\n",
    "- I2 real SOUL Lab observation: complete\n"
    "- I1-G pre-enqueue background-finalizer durability: unresolved\n"
    "- auditable Correct operation: next as Phase I-3\n",
)

replace_once(
    "docs/architecture/pipeline_implementation_plan.md",
    "  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete\n\n"
    "RelayMEM Primary integration:\n",
    "  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete\n"
    "  I1-G pre-enqueue background-finalizer durability: unresolved\n\n"
    "RelayMEM Primary integration:\n",
)
replace_once(
    "docs/architecture/pipeline_implementation_plan.md",
    "Phase I-1 next-turn recall and scope isolation are complete. Phase I-2 real SOUL Lab observation is complete. Phase I-3 auditable Correct is the next product boundary.\n",
    "Phase I-1 next-turn recall and scope isolation are complete. Phase I-2 real SOUL Lab observation is complete. Phase I-3 auditable Correct is the next product boundary; I1-G remains a separate unresolved durability boundary.\n",
)

for document in (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
    "docs/architecture/phase_i2_real_soul_lab_observation.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/soul_lab_runtime_mvp.md",
    "docs/architecture/soul_lab_ui_a7_management_projection_handoff.md",
    "docs/architecture/soul_lab_ui_mvp.md",
):
    normalize_i1g(document)

replace_once(
    "scripts/relaylm_phase_i2_documentation_boundary_smoke.py",
    '        "pre-enqueue background-finalizer crash window",\n',
    '        "I1-G",\n'
    '        "pre-enqueue background-finalizer",\n',
)
