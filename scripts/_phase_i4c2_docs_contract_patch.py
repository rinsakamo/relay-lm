"""One-shot I-4C2 contract ownership reconciliation."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if body.count(old) != 1:
        raise RuntimeError(f"unexpected documentation drift: {path}: {old!r}")
    target.write_text(body.replace(old, new), encoding="utf-8")


def main() -> None:
    path = "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"
    replace_once(
        path,
        "**Defined target contract; I-4C1 hidden-successor commit is implemented.**",
        "**Defined target contract; I-4C1 hidden-successor commit and bounded I-4C2 recovery/finalization are implemented.**",
    )
    replace_once(
        path,
        "Phase I-4C1 implements exact intent preparation, shared revision claim, deterministic hidden successor publication through M3e, canonical reread, and `hidden / recovery_required / false` resolution. It does not add I-4C2 prepared resume/exact replay/tombstone finalization, I-4D M2 lifecycle exclusion, loopback mutation routes, or SOUL Lab Forget UI.",
        "Phase I-4C1 implements exact intent preparation, shared revision claim, deterministic hidden successor publication through M3e, canonical reread, and `hidden / recovery_required / false` resolution. Phase I-4C2 implements exact prepared resume, operation-scoped M3f/M3g control convergence, response-loss replay, and tombstone-backed `hidden / none / false` finalization. I-4D M2/RelayCTX lifecycle exclusion, loopback mutation routes, and SOUL Lab Forget UI remain unimplemented.",
    )
    replace_once(
        path,
        "The remaining production work begins at I-4C2 and I-4D; I-4C1 is complete.",
        "The remaining production work begins at I-4D; I-4C1 and bounded I-4C2 recovery/finalization are complete.",
    )
    replace_once(
        path,
        "I-4B completed the resolver/shared-fence/read-only portion. I-4C1 now owns the durable prepared artifact and hidden-page lifecycle commit; I-4C2 still owns resume, exact replay, forward recovery, response-loss convergence, and tombstone finalization.",
        "I-4B completed the resolver/shared-fence/read-only portion. I-4C1 owns the durable prepared artifact and hidden-page lifecycle commit. I-4C2 now implements exact resume, one-operation M3f/M3g convergence, forward recovery, response-loss replay, and tombstone finalization. I-4D owns ordinary M2/RelayCTX lifecycle exclusion.",
    )
    replace_once(
        path,
        "  - phase_i4c1_primary_forget_hidden_successor.md\n",
        "  - phase_i4c1_primary_forget_hidden_successor.md\n  - phase_i4c2_primary_forget_recovery_finalization.md\n",
    )

    path = "docs/architecture/phase_i4b_primary_current_state_shared_fence.md"
    replace_once(
        path,
        "  - Phase I-4C1 consumes the shared fence\n",
        "  - Phase I-4C1 and I-4C2 consume the shared fence\n",
    )
    replace_once(
        path,
        "- I-4C2: prepared resume, exact replay, forward-only recovery, response-loss\n  convergence, and Forget tombstone finalization.\n- I-4D: M3f/M3g convergence and canonical hidden/prepared/recovery/corrupt\n  exclusion in M2 and RelayCTX.",
        "- I-4C2: complete for exact prepared resume, forward-only hidden continuation,\n  operation-scoped M3f/M3g convergence, response-loss replay, and tombstone finalization.\n- I-4D: unimplemented ordinary M2/RelayCTX lifecycle exclusion, prior physical\n  revision exclusion, and historical lifecycle projection.",
    )

    path = "docs/architecture/phase_i4c1_primary_forget_hidden_successor.md"
    replace_once(
        path,
        "- I-4C2 prepared resume, forward-only recovery, exact replay, response-loss\n  convergence, Forget tombstone, and applied receipt;\n- I-4D M3f/M3g convergence and actual M2/RelayCTX hidden exclusion;",
        "- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence,\n  forward-only recovery, response-loss replay, and tombstone authority are complete;\n- I-4D ordinary M2/RelayCTX hidden and prior-revision exclusion is unimplemented;",
    )
    replace_once(
        path,
        "I-4C1 therefore completes hidden-successor commit ownership, not Phase I-4 as a\nwhole and not product-complete Forget behavior.",
        "I-4C1 therefore completes hidden-successor commit ownership. I-4C2 now completes\nthe bounded recovery/finalization continuation, but Phase I-4 as a whole and\nproduct-complete Forget behavior remain incomplete until I-4D through I-4F.",
    )


if __name__ == "__main__":
    main()
