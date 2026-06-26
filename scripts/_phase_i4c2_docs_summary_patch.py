"""One-shot I-4C2 current-boundary summary reconciliation."""
from pathlib import Path


def append_once(path: str, anchor: str, section: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if anchor not in body:
        target.write_text(body.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if body.count(old) != 1:
        raise RuntimeError(f"unexpected documentation drift: {path}: {old!r}")
    target.write_text(body.replace(old, new), encoding="utf-8")


def main() -> None:
    append_once(
        "docs/PROJECT_STATUS.md",
        "Phase I-4C2 exact recovery/finalization: complete",
        """## Phase I-4C2 current boundary (2026-06-26 JST)\n\n- Phase I-4C1 hidden-successor commit: complete.\n- Phase I-4C2 exact recovery/finalization: complete.\n- One exact prepared operation resumes through deterministic hidden M3e evidence, operation-scoped index-before-log convergence, canonical reread, and immutable tombstone replay.\n- Final resolver state is `hidden / none / retrieval_eligible=false`.\n- I-4D ordinary M2/RelayCTX lifecycle exclusion and historical projection: unimplemented.\n- I-4E API/UI and I-4F full production validation: unimplemented.\n- Phase I-4 and product-complete Forget are not complete.""",
    )
    append_once(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase I-4C2 exact recovery and tombstone finalization: complete",
        """### I1-F4 / Phase I-4C2: exact Forget recovery and finalization — complete\n\nPhase I-4C2 exact recovery and tombstone finalization: complete. It owns one exact prepared-operation resume, hidden-page forward recovery, operation-scoped M3f/M3g convergence, tombstone publication, and exact response-loss replay. Phase I-4D remains the unimplemented ordinary M2/RelayCTX lifecycle exclusion slice.""",
    )
    append_once(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "Phase I-4C2: Forget recovery and finalization — complete",
        """### Phase I-4C2: Forget recovery and finalization — complete\n\nThe bounded one-operation recovery/finalization authority is complete. Current governance work advances to Phase I-4D ordinary M2/RelayCTX lifecycle exclusion and historical projection; API/UI and full production validation remain I-4E/I-4F.""",
    )
    append_once(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-h Forget recovery/finalization: complete as Phase I-4C2",
        """### M3i-h Forget recovery/finalization: complete as Phase I-4C2\n\nPrepared resume, deterministic hidden continuation, operation-scoped M3f/M3g convergence, immutable tombstone authority, and exact replay are complete. The next RelayMEM governance implementation slice is I-4D ordinary retrieval and RelayCTX lifecycle exclusion.""",
    )
    replace_once(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "The next RelayMEM governance implementation slice is I-4C2",
        "The next RelayMEM governance implementation slice is I-4D",
    )
    append_once(
        "docs/architecture/relaymem_slp_current_target.md",
        "Phase I-4C2 exact recovery/finalization — complete",
        """### Phase I-4C2 exact recovery/finalization — complete\n\nOne exact durable Forget operation now converges through hidden page, index/log controls, and tombstone-backed replay. Ordinary M2/RelayCTX hidden filtering is unchanged and remains Phase I-4D ownership.""",
    )
    replace_once(
        "docs/architecture/relaymem_slp_current_target.md",
        "Forget is not product-complete until I-4C2 through I-4F",
        "Forget is not product-complete until I-4D through I-4F",
    )
    append_once(
        "docs/README.md",
        "phase_i4c2_primary_forget_recovery_finalization.md",
        """## Phase I-4C2 current handoff\n\n- [`architecture/phase_i4c2_primary_forget_recovery_finalization.md`](architecture/phase_i4c2_primary_forget_recovery_finalization.md) — exact prepared resume, operation-scoped controls convergence, immutable tombstone, and exact replay.\n- Phase I-4C1 and Phase I-4C2 are complete bounded authorities; I-4D through I-4F remain.""",
    )
    append_once(
        "docs/architecture/README.md",
        "Phase I-4C2 Primary Forget Recovery and Finalization",
        """## Phase I-4C2 Primary Forget Recovery and Finalization\n\n- [`phase_i4c2_primary_forget_recovery_finalization.md`](phase_i4c2_primary_forget_recovery_finalization.md)\n- I-4C2 provides caller-selected exact recovery, index-before-log convergence, tombstone finalization, and exact replay. I-4D retains ordinary M2/RelayCTX exclusion ownership.""",
    )


if __name__ == "__main__":
    main()
