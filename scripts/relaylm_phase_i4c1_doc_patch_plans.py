"""Apply deterministic I-4C1 roadmap and pipeline-plan updates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def swap(path: str, old: str, new: str) -> None:
    target = ROOT / path
    body = target.read_text(encoding="utf-8")
    if old not in body:
        if new in body:
            return
        raise RuntimeError(f"missing documentation anchor in {path}: {old[:72]!r}")
    if body.count(old) != 1:
        raise RuntimeError(f"ambiguous documentation anchor in {path}: {old[:72]!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


def pipeline() -> None:
    path = "docs/architecture/pipeline_implementation_plan.md"
    swaps = (
        (
            "  - phase_i4b_primary_current_state_shared_fence.md\n",
            "  - phase_i4b_primary_current_state_shared_fence.md\n"
            "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "  Phase I-4C through I-4F hidden apply, M2, UI, and validation: unimplemented",
            "  Phase I-4C1 hidden-successor commit: complete\n"
            "  Phase I-4C2 through I-4F recovery/replay/tombstone, M2, UI, and validation: unimplemented",
        ),
        (
            "Phase I-1 next-turn recall and scope isolation, Phase I-2 real SOUL Lab observation, Phase I-3 auditable Correct, UI-B0 Real Home Conversation, and the I-4B read-only resolver/shared-fence boundary are complete. I1-GA contract/design/fault-model work and I1-GB pre-release durable publication are complete. I1-GC through I1-GE remain planned; restart replay/completion convergence, cleanup, and full crash validation are unimplemented. Phase I-4A remains the exact Forget / Hide target contract, while I-4C through I-4F remain unimplemented.",
            "Phase I-1 next-turn recall and scope isolation, Phase I-2 real SOUL Lab observation, Phase I-3 auditable Correct, UI-B0 Real Home Conversation, the I-4B read-only resolver/shared-fence boundary, and I-4C1 hidden-successor commit ownership are complete. I1-GA contract/design/fault-model work and I1-GB pre-release durable publication are complete. I1-GC through I1-GE remain planned; restart replay/completion convergence, cleanup, and full crash validation are unimplemented. Phase I-4A remains the exact Forget / Hide target contract, while I-4C2 through I-4F remain unimplemented.",
        ),
        (
            "Correct and Forget must share one per-memory lock namespace, pending-operation fence, operation identity lookup, and revision claim. I-4B now implements the canonical read-only resolver, shared `.lock`/fence, preflight, token validation, and bounded zero-item history. Hidden-successor apply, durable history artifacts/projection, M2 exclusion, loopback routes, and UI remain unimplemented.",
            "Correct and Forget share one per-memory lock namespace, pending-operation fence, operation identity lookup, and revision claim. I-4B implements the canonical read-only resolver, shared `.lock`/fence, preflight, token validation, and bounded zero-item history. I-4C1 now adds exact token/reason revalidation, immutable prepared evidence, deterministic hidden successor publication through M3e, canonical reread, one-winner concurrency, and recovery-required projection. I-4C2 durable applied/tombstone history, M2 exclusion, loopback routes, and UI remain unimplemented.",
        ),
        (
            "I-4C  immutable hidden successor, prepared artifact,\n       tombstone, exact replay, and forward-only recovery",
            "I-4C1 immutable hidden successor, prepared artifact,\n       shared revision claim and M3e commit — complete\n\nI-4C2 tombstone, exact replay, response-loss convergence,\n       prepared resume and forward-only recovery",
        ),
        (
            "I-4C1  token/fence/revision ownership, prepared artifact,\n       hidden successor and M3e publication",
            "I-4C1  token/fence/revision ownership, prepared artifact,\n       hidden successor and M3e publication — complete",
        ),
        (
            "### Wave 1 — current: one-record recovery and lifecycle commit ownership",
            "### Wave 1 — in progress: one-record recovery and lifecycle commit ownership",
        ),
        (
            "Thread B  I-4C1 hidden-successor commit ownership",
            "Thread B  I-4C1 hidden-successor commit ownership — complete",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def roadmap() -> None:
    path = "docs/architecture/post_i3_evaluation_work_roadmap.md"
    swaps = (
        (
            "  - phase_i4b_primary_current_state_shared_fence.md\n",
            "  - phase_i4b_primary_current_state_shared_fence.md\n"
            "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "Phase I-3 Correct, UI-B0 real Home conversation, O0 local one-job execution, I1-GB pre-release durable-finalization publication, and the I-4B read-only current-state/shared-fence boundary are complete. Phase I-4A remains the target Forget / Hide contract. Restart replay/completion convergence and production hidden-lifecycle apply/exclusion remain incomplete.",
            "Phase I-3 Correct, UI-B0 real Home conversation, O0 local one-job execution, I1-GB pre-release durable-finalization publication, the I-4B read-only current-state/shared-fence boundary, and I-4C1 hidden-successor commit ownership are complete. Phase I-4A remains the target Forget / Hide contract. Restart replay/completion convergence, I-4C2 recovery/tombstone, and I-4D production exclusion remain incomplete.",
        ),
        (
            "- I-4B canonical read-only current-state resolver, shared Correct/Forget fence, Forget preflight/token validation, and bounded zero-item history.",
            "- I-4B canonical read-only current-state resolver, shared Correct/Forget fence, Forget preflight/token validation, and bounded zero-item history;\n"
            "- I-4C1 exact Forget prepare, shared revision claim, deterministic hidden successor, M3e commit, and hidden/recovery-required resolution.",
        ),
        (
            "- Phase I-4C through I-4F hidden apply, M2 exclusion, API/UI, and validation;",
            "- Phase I-4C2 through I-4F recovery/replay/tombstone, M2 exclusion, API/UI, and validation;",
        ),
        (
            "I-4B does not write hidden successors, prepared Forget artifacts, tombstones, index/log changes, API routes, or UI state. Ordinary M2 and RelayCTX behavior remains unchanged in this slice.\n\n### Phase I-4C through I-4F: Remaining Forget work",
            "I-4B does not write hidden successors, prepared Forget artifacts, tombstones, index/log changes, API routes, or UI state. Ordinary M2 and RelayCTX behavior remains unchanged in this slice.\n\n### Phase I-4C1: Hidden-successor commit — complete\n\nI-4C1 consumes the I-4B token and shared fence, publishes immutable prepared evidence before the deterministic hidden page, uses existing M3c/M3d/M3e authority, canonically rereads the page, enforces one-winner concurrency, and resolves committed state as `hidden / recovery_required / false`. It intentionally stops before M3f/M3g, tombstone, exact replay, and M2 exclusion.\n\n### Phase I-4C2 through I-4F: Remaining Forget work",
        ),
        (
            "I-4C1  exact token validation, shared revision claim, prepared artifact,\n       hidden-successor candidate, M3e publication, one-winner concurrency",
            "I-4C1  exact token validation, shared revision claim, prepared artifact,\n       hidden-successor candidate, M3e publication, one-winner concurrency — complete",
        ),
        ("### Wave 1 — current", "### Wave 1 — in progress"),
        ("I1-GC || I-4C1 || O1A design", "I1-GC || I-4C2 || O1A design"),
    )
    for old, new in swaps:
        swap(path, old, new)


def main() -> None:
    pipeline()
    roadmap()
    print("I-4C1 pipeline and roadmap documentation updated")


if __name__ == "__main__":
    main()
