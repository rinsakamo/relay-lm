"""Apply deterministic I-4C1 index and contract documentation updates."""
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


def docs_index() -> None:
    path = "docs/README.md"
    swaps = (
        (
            "completed I1-GA/I1-GB, defined Phase I-4A, and completed I-4B read-only resolver/fence boundary",
            "completed I1-GA/I1-GB, defined Phase I-4A, completed I-4B read-only resolver/fence boundary, and completed I-4C1 hidden-successor commit",
        ),
        (
            "- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md) — implemented read-only resolver, shared lock/fence, token, and zero-item history boundary\n",
            "- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md) — implemented read-only resolver, shared lock/fence, token, and zero-item history boundary\n"
            "- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md) — implemented exact prepare, deterministic hidden page, M3e commit, and recovery-required resolution\n",
        ),
        (
            "Phase I-4A defines the target contract. Phase I-4B is complete for the canonical read-only current-state resolver, shared Correct/Forget mutation fence, Forget preflight, five-minute token validation, and bounded zero-item history. Hidden-successor apply, tombstone/recovery, M2 exclusion, the loopback mutation API, and the SOUL Lab Forget UI remain unimplemented.",
            "Phase I-4A defines the target contract. Phase I-4B is complete for the canonical read-only current-state resolver, shared Correct/Forget mutation fence, Forget preflight, five-minute token validation, and bounded zero-item history. Phase I-4C1 is complete for exact token/reason revalidation, shared revision claim, immutable Forget prepare, deterministic hidden successor, existing M3c/M3d/M3e publication, canonical reread, one-winner concurrency, and `hidden / recovery_required / false` resolution. I-4C2 recovery/replay/tombstone, I-4D M3f/M3g and M2 exclusion, the loopback mutation API, and the SOUL Lab Forget UI remain unimplemented.",
        ),
        (
            "I1-GC through I1-GE, Phase I-4C through I-4F, O1/O2/O3 automatic operation",
            "I1-GC through I1-GE, Phase I-4C2 through I-4F, O1/O2/O3 automatic operation",
        ),
        (
            "- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)\n",
            "- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)\n"
            "- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md)\n",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def phase_i4_contract() -> None:
    path = "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"
    swaps = (
        (
            "  - phase_i4b_primary_current_state_shared_fence.md\n",
            "  - phase_i4b_primary_current_state_shared_fence.md\n"
            "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        ),
        (
            "**Defined target contract; hidden-lifecycle apply remains unimplemented.**",
            "**Defined target contract; I-4C1 hidden-successor commit is implemented.**",
        ),
        (
            "This document fixes the lifecycle, identity, persistence, concurrency, API, audit, recovery, and retrieval-exclusion contract for Phase I-4. Phase I-4B now implements the canonical read-only current-state resolver, shared Correct/Forget mutation fence, read-only Forget preflight, five-minute token validation, and bounded zero-item history. It does not add hidden-successor apply, tombstone finalization, M2 lifecycle exclusion, loopback mutation routes, or SOUL Lab Forget UI.",
            "This document fixes the lifecycle, identity, persistence, concurrency, API, audit, recovery, and retrieval-exclusion contract for Phase I-4. Phase I-4B implements the canonical read-only current-state resolver, shared Correct/Forget mutation fence, read-only Forget preflight, five-minute token validation, and bounded zero-item history. Phase I-4C1 implements exact intent preparation, shared revision claim, deterministic hidden successor publication through M3e, canonical reread, and `hidden / recovery_required / false` resolution. It does not add I-4C2 prepared resume/exact replay/tombstone finalization, I-4D M2 lifecycle exclusion, loopback mutation routes, or SOUL Lab Forget UI.",
        ),
        (
            "Remaining production work begins at I-4C1.",
            "The remaining production work begins at I-4C2 and I-4D; I-4C1 is complete.",
        ),
        (
            "I-4B completed the resolver/shared-fence/read-only portion. I-4C owns durable commit and recovery behavior.",
            "I-4B completed the resolver/shared-fence/read-only portion. I-4C1 now owns the durable prepared artifact and hidden-page lifecycle commit; I-4C2 still owns resume, exact replay, forward recovery, response-loss convergence, and tombstone finalization.",
        ),
        (
            "I-4B implements only the exact read-only preflight/token models and bounded zero-item history boundary. Routes and durable applied items remain I-4E/I-4C work.",
            "I-4B implements the exact read-only preflight/token models and bounded zero-item history boundary. I-4C1 consumes the exact bounded reason again at apply time and stores it only in runtime-private prepared evidence. Routes and durable applied/tombstone history items remain I-4E/I-4C2 work.",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def phase_i4b() -> None:
    path = "docs/architecture/phase_i4b_primary_current_state_shared_fence.md"
    swaps = (
        ("Phase I-4C consumes the shared fence", "Phase I-4C1 consumes the shared fence"),
        (
            "  - hidden lifecycle apply\n  - M2 hidden-state exclusion",
            "  - post-M3e Forget recovery, replay, and tombstone finalization\n  - M2 hidden-state exclusion",
        ),
        (
            "- I-4B performs no Forget lifecycle write and does not create hidden successors,\n  tombstones, prepared Forget artifacts, index/log mutations, or API/UI routes.\n- Ordinary M2 selection, RelayCTX injection, current SOUL Lab reads, and\n  historical used-memory evidence remain unchanged in this slice.\n\n## Remaining work",
            "- I-4B itself performs no Forget lifecycle write and does not create hidden successors,\n  tombstones, prepared Forget artifacts, index/log mutations, or API/UI routes.\n- Ordinary M2 selection, RelayCTX injection, current SOUL Lab reads, and\n  historical used-memory evidence remain unchanged in the I-4B slice.\n\n## I-4C1 consumer boundary\n\nI-4C1 now consumes this exact resolver and `.lock` authority. It adds immutable\n`relaylm.mem.forget_prepared.v0`, deterministic\n`relaymem.primary_lifecycle_page.v0`, existing M3c/M3d/M3e publication, canonical\npage reread, one-winner Correct/Forget and Forget/Forget concurrency, and\n`hidden / recovery_required / retrieval_eligible=false` resolution. It does not\nchange I-4B token semantics or ordinary M2 behavior.\n\n## Remaining work",
        ),
        (
            "- I-4C: hidden successor apply, prepared artifact, tombstone, exact replay, and\n  forward-only recovery.\n- I-4D: canonical hidden/prepared/recovery/corrupt exclusion in M2 and RelayCTX.",
            "- I-4C2: prepared resume, exact replay, forward-only recovery, response-loss\n  convergence, and Forget tombstone finalization.\n- I-4D: M3f/M3g convergence and canonical hidden/prepared/recovery/corrupt\n  exclusion in M2 and RelayCTX.",
        ),
    )
    for old, new in swaps:
        swap(path, old, new)


def main() -> None:
    docs_index()
    phase_i4_contract()
    phase_i4b()
    print("I-4C1 index and contract documentation updated")


if __name__ == "__main__":
    main()
