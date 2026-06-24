"""Temporarily normalize Phase I-3 documentation files to one terminal newline."""
from pathlib import Path

FILES = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
    "docs/architecture/memory_lifecycle_design.md",
    "docs/architecture/phase_i2_real_soul_lab_observation.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/soul_lab_runtime_mvp.md",
    "docs/architecture/soul_lab_ui_mvp.md",
)

for name in FILES:
    path = Path(name)
    body = path.read_text(encoding="utf-8")
    path.write_text(body.rstrip() + "\n", encoding="utf-8")

print(f"normalized {len(FILES)} Phase I-3 documentation files")
