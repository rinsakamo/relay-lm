from pathlib import Path


def append_once(path: str, marker: str, body: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + body.strip() + "\n", encoding="utf-8")


append_once(
    "docs/README.md",
    "Wave 2 integrated boundary",
    """## Wave 2 integrated boundary

- I1-GD is complete; I1-GE full crash validation remains unimplemented.
- Phase I-4C2 is complete; ordinary M2/RelayCTX lifecycle exclusion remains I-4D.
- O1B and O1C are complete; the production round, policy, recovery, and validation remain O1D-O1F.
- The W2-INT authority map and frozen next-phase inputs are in [Wave 2 cross-slice convergence audit](architecture/wave2_cross_slice_convergence_audit.md).
""",
)
append_once(
    "docs/architecture/README.md",
    "wave2_cross_slice_convergence_audit.md",
    "- [Wave 2 cross-slice convergence audit](wave2_cross_slice_convergence_audit.md) — integrated I1-GD, I-4C2, O1B, and O1C authority, race, lock/root, leakage, and next-phase boundary.",
)
append_once(
    "docs/PROJECT_STATUS.md",
    "Wave 2 cross-slice convergence",
    """## Wave 2 cross-slice convergence

W2-INT audits the merged I1-GD, I-4C2, O1B, and O1C production boundaries. It adds no scheduler loop or retrieval exclusion. I1-GE, I-4D, and O1D1 remain the next independent implementation tracks after this audit is green.
""",
)
