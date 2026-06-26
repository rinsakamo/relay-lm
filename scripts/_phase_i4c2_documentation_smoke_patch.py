"""One-shot current-boundary smoke update for Phase I-4C2."""
from pathlib import Path

PATH = Path("scripts/relaylm_documentation_current_boundary_smoke.py")


def replace_once(old: str, new: str) -> None:
    body = PATH.read_text(encoding="utf-8")
    if old not in body:
        if new in body:
            return
        raise RuntimeError(f"unexpected documentation smoke drift: {old!r}")
    if body.count(old) != 1:
        raise RuntimeError(f"ambiguous documentation smoke text: {old!r}")
    PATH.write_text(body.replace(old, new), encoding="utf-8")


def main() -> None:
    replace_once("I1-I4C1", "I1-I4C2")
    replace_once(
        '    "docs/architecture/post_i3_evaluation_work_roadmap.md",\n',
        '    "docs/architecture/post_i3_evaluation_work_roadmap.md",\n    "docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md",\n',
    )
    replace_once(
        '        "Phase I-4C1 hidden-successor commit: complete",\n        "I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete",\n',
        '        "Phase I-4C1 hidden-successor commit: complete",\n        "Phase I-4C2 exact recovery/finalization: complete",\n        "I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete",\n',
    )
    replace_once(
        '        "Phase I-4C1 hidden-successor commit: complete",\n        "exact read-only preflight/history/token",\n',
        '        "Phase I-4C1 hidden-successor commit: complete",\n        "Phase I-4C2 exact recovery and tombstone finalization: complete",\n        "exact read-only preflight/history/token",\n',
    )
    replace_once(
        '        "Phase I-4C1: Hidden-successor commit — complete",\n',
        '        "Phase I-4C1: Hidden-successor commit — complete",\n        "Phase I-4C2: Forget recovery and finalization — complete",\n',
    )
    replace_once(
        '        "M3i-g hidden-successor commit ownership: complete as Phase I-4C1",\n        "I1-GC one-record replay and completion convergence is complete",\n        "The next RelayMEM governance implementation slice is I-4C2",\n',
        '        "M3i-g hidden-successor commit ownership: complete as Phase I-4C1",\n        "M3i-h Forget recovery/finalization: complete as Phase I-4C2",\n        "I1-GC one-record replay and completion convergence is complete",\n        "The next RelayMEM governance implementation slice is I-4D",\n',
    )
    replace_once(
        '        "Phase I-4C1 hidden-successor commit — complete",\n        "Forget is not product-complete until I-4C2 through I-4F",\n',
        '        "Phase I-4C1 hidden-successor commit — complete",\n        "Phase I-4C2 exact recovery/finalization — complete",\n        "Forget is not product-complete until I-4D through I-4F",\n',
    )
    replace_once(
        '        "Phase I-4C1 is complete",\n',
        '        "Phase I-4C1 and Phase I-4C2 are complete",\n        "phase_i4c2_primary_forget_recovery_finalization.md",\n',
    )
    replace_once(
        '        "Phase I-4C1 Primary Forget Hidden-Successor Commit",\n',
        '        "Phase I-4C1 Primary Forget Hidden-Successor Commit",\n        "Phase I-4C2 Primary Forget Recovery and Finalization",\n',
    )
    replace_once(
        '        "I-4C2 prepared resume/exact replay/tombstone finalization",\n',
        '        "operation-scoped M3f/M3g control convergence",\n        "I-4D M2/RelayCTX lifecycle exclusion",\n',
    )
    replace_once(
        '        "I-4C2: prepared resume",\n        "I-4D: M3f/M3g convergence",\n',
        '        "I-4C2: complete for exact prepared resume",\n        "I-4D: unimplemented ordinary M2/RelayCTX lifecycle exclusion",\n',
    )
    replace_once(
        '        "I-4C2 prepared resume",\n        "M3f or M3g",\n',
        '        "I-4C2 exact prepared resume",\n        "operation-scoped M3f/M3g convergence",\n',
    )
    marker = '    "docs/architecture/o0_local_one_job_runner.md": (\n'
    dedicated = '''    "docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md": (\n        "Status: complete for the bounded I-4C2 one-operation recovery/finalization boundary.",\n        "relaylm.mem.forget_tombstone.v0",\n        "operation-scoped M3f-compatible index/log plan",\n        "hidden / none / retrieval_eligible=false",\n        "I-4D ordinary M2 lifecycle eligibility enforcement",\n        "after_m3g_index_before_log",\n        "No second Forget lock exists",\n    ),\n'''
    replace_once(marker, dedicated + marker)


if __name__ == "__main__":
    main()
