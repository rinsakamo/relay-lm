"""Apply the deterministic I-4C1 status-document transition."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def swap(path: str, old: str, new: str) -> None:
    target = ROOT / path
    body = target.read_text(encoding="utf-8")
    if old not in body:
        if new in body:
            return
        raise RuntimeError(f"missing documentation anchor in {path}")
    if body.count(old) != 1:
        raise RuntimeError(f"ambiguous documentation anchor in {path}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    path = "docs/PROJECT_STATUS.md"
    swaps = (
        (
            "  - docs/architecture/phase_i4b_primary_current_state_shared_fence.md\n",
            "  - docs/architecture/phase_i4b_primary_current_state_shared_fence.md\n"
            "  - docs/architecture/phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "- Phase I-4B canonical current-state resolver, shared mutation fence, and read-only Forget boundary,\n",
            "- Phase I-4B canonical current-state resolver, shared mutation fence, and read-only Forget boundary,\n"
            "- Phase I-4C1 exact Forget preparation and hidden-successor commit,\n",
        ),
        (
            "Phase I-4C through I-4F hidden apply, M2 exclusion, UI, and validation: unimplemented",
            "Phase I-4C1 hidden-successor commit: complete\n"
            "Phase I-4C2 through I-4F resume/replay/tombstone, M2 exclusion, UI, and validation: unimplemented",
        ),
        (
            "- Phase I-4B canonical read-only current-state resolution and shared Correct/Forget mutation fencing.\n",
            "- Phase I-4B canonical read-only current-state resolution and shared Correct/Forget mutation fencing,\n"
            "- Phase I-4C1 immutable Forget prepared artifact, deterministic hidden successor, M3e publication, and hidden/recovery-required resolution.\n",
        ),
        (
            "Phase I-4A defines the lifecycle boundary, and Phase I-4B now implements its canonical read-only resolver and shared mutation fence:",
            "Phase I-4A defines the lifecycle boundary, Phase I-4B implements its canonical read-only resolver and shared mutation fence, and Phase I-4C1 implements hidden-successor commit ownership:",
        ),
        (
            "The hidden successor page is the lifecycle authority. The tombstone is audit/recovery evidence, not an independently updated sidecar flag. I-4B now supplies the canonical current-state resolver, preserves the Phase I-3 per-memory `.lock` as the shared Correct/Forget mutation fence, and implements read-only Forget preflight, five-minute token validation, and bounded zero-item history. Prepared and recovery-required evidence remains retrieval-ineligible.",
            "The hidden successor page is the lifecycle authority. The tombstone is audit/recovery evidence, not an independently updated sidecar flag. I-4B supplies the canonical current-state resolver, preserves the Phase I-3 per-memory `.lock` as the shared Correct/Forget mutation fence, and implements read-only Forget preflight, five-minute token validation, and bounded zero-item history. I-4C1 validates the exact token and reason again under that lock, publishes immutable `relaylm.mem.forget_prepared.v0`, deterministically builds `relaymem.primary_lifecycle_page.v0`, publishes it through M3c/M3d/M3e, canonically rereads it, and exposes `hidden / recovery_required / false`. Prepared and recovery-required evidence remains retrieval-ineligible.",
        ),
        (
            "- I-4C hidden-successor apply, prepared artifact, tombstone, exact replay, and forward-only recovery,",
            "- I-4C2 prepared resume, exact replay, forward-only recovery, response-loss convergence, and Forget tombstone finalization,",
        ),
        (
            "Phase I-4A/I-4B change no browser behavior.",
            "Phase I-4A/I-4B/I-4C1 change no browser behavior.",
        ),
        (
            "- I4C through I4F hidden apply, M2 exclusion, UI, and validation: unimplemented",
            "- I4C1 hidden-successor commit: complete\n"
            "- I4C2 through I4F resume/replay/tombstone, M2 exclusion, UI, and validation: unimplemented",
        ),
        (
            "UI-B0, I1-GA/I1-GB, Phase I-4A/I-4B, and O0 do not weaken existing server defaults. I1-GB is default-off and changes response ordering only in explicit apply mode. Phase I-4B adds no accepted loopback route, hidden-lifecycle write, M2 filtering change, or browser mutation capability. O0 cannot be elevated to apply by CLI flags and performs no discovery while disabled.",
            "UI-B0, I1-GA/I1-GB, Phase I-4A/I-4B/I-4C1, and O0 do not weaken existing server defaults. I1-GB is default-off and changes response ordering only in explicit apply mode. Phase I-4C1 adds no accepted loopback route, M3f/M3g convergence, tombstone, M2 filtering change, or browser mutation capability. O0 cannot be elevated to apply by CLI flags and performs no discovery while disabled.",
        ),
        (
            "- I-4C hidden-lifecycle apply/recovery and tombstone finalization, I-4D M2 exclusion, I-4E Forget API/UI, or I-4F production validation,",
            "- I-4C2 prepared resume/recovery/replay and tombstone finalization, I-4D M3f/M3g plus M2 exclusion, I-4E Forget API/UI, or I-4F production validation,",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)
    print("I-4C1 project status documentation updated")


if __name__ == "__main__":
    main()
