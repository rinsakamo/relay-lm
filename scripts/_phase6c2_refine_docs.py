from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/phase6_async_relayslp_bounded_slice.md",
    "docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md",
    "docs/architecture/phase6c1_primary_mem_worker_contract.md",
    "docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md",
    "docs/architecture/phase6c1_durable_protected_source_persistence.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
)
MARKER_RE = re.compile(
    r"\n?<!-- phase6c2-status:start -->.*?<!-- phase6c2-status:end -->\n?",
    re.DOTALL,
)


def add_once(text: str, needle: str, addition: str) -> str:
    if addition in text:
        return text
    if needle not in text:
        raise RuntimeError(f"anchor not found: {needle!r}")
    return text.replace(needle, needle + addition, 1)


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise RuntimeError(f"replacement anchor not found: {old[:120]!r}")
    return text.replace(old, new, 1)


def strip_marker(text: str) -> str:
    return MARKER_RE.sub("\n", text).rstrip() + "\n"


def project_status(text: str) -> str:
    return strip_marker(text)


def docs_readme(text: str) -> str:
    text = strip_marker(text)
    line = (
        "\nCurrent Phase 6 integration handoff: "
        "[Phase 6-C2 One Queued Primary Worker Integration]"
        "(architecture/phase6c2_one_queued_primary_worker_integration.md). "
        "The next product boundary is next-turn recall with character/namespace isolation; "
        "queue scanning and daemon lifecycle remain out of scope.\n"
    )
    if "Current Phase 6 integration handoff:" not in text:
        text = text.rstrip() + "\n" + line
    return text


def architecture_readme(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "- [Phase 6-C1-5 Durable Protected Source Persistence](phase6c1_durable_protected_source_persistence.md)\n",
        "- [Phase 6-C2 One Queued Primary Worker Integration](phase6c2_one_queued_primary_worker_integration.md)\n",
    )
    text = replace_once(
        text,
        "Phase 6-A1/A2 and B0-B3 own deferred admission, finalized-turn handoff, durable queue publication, and fenced queue lifecycle. I1-B wires ordinary managed response finalization to post-response enqueue. C1-0 owns exact current-claim source construction, C1-1 composes M3a-M3h, C1-2 executes one already-claimed job, C1-3 classifies outcomes, C1-4 verifies integrated fault convergence, and C1-5 durably persists and restart-rehydrates the claim-independent protected capture.",
        "Phase 6-A1/A2 and B0-B3 own deferred admission, finalized-turn handoff, durable queue publication, and fenced queue lifecycle. I1-B wires ordinary managed response finalization to post-response enqueue. C1-0 owns exact current-claim source construction, C1-1 composes M3a-M3h, C1-2 executes one already-claimed job, C1-3 classifies outcomes, C1-4 verifies integrated fault convergence, C1-5 durably persists and restart-rehydrates the claim-independent protected capture, and C2 connects one exact queued record through canonical claim, rehydrate, and C1-2 execution.",
    )
    text = replace_once(
        text,
        "Phase 6-C1 is restart-complete for protected-source recovery of durably enqueued jobs. The next boundary is a thin one-job B3 claim -> C1-5 rehydrate -> C1-2 execute adapter. Queue scanning, daemon scheduling, the pre-enqueue background-finalizer crash window, and next-turn recall remain unimplemented.",
        "Phase 6-C2 is complete for one caller-selected canonical queued job. The next boundary is next-turn recall and character/namespace isolation. Queue scanning, daemon scheduling, and the pre-enqueue background-finalizer crash window remain unimplemented.",
    )
    text = replace_once(
        text,
        "- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current enqueue/source capture, queue lifecycle, completed C1-0 through C1-5, and remaining one-job runner/recall integration.",
        "- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current enqueue/source capture, queue lifecycle, completed C1-0 through C1-5 and C2, and remaining next-turn recall integration.",
    )
    return text


def pipeline_plan(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete\n",
        "  next-turn recall and scope isolation: next\n",
    )
    if "  - phase6c1_durable_protected_source_persistence.md\n" in text:
        text = add_once(
            text,
            "  - phase6c1_durable_protected_source_persistence.md\n",
            "  - phase6c2_one_queued_primary_worker_integration.md\n",
        )
    return text


def phase6_slice(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_durable_protected_source_persistence.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "Phase 6 is implemented through I1-B, fenced B3 lifecycle, and Phase 6-C1-0 through C1-5.",
        "Phase 6 is implemented through I1-B, fenced B3 lifecycle, Phase 6-C1-0 through C1-5, and the bounded Phase 6-C2 one-job adapter.",
    )
    text = add_once(
        text,
        "### C1-5: durable protected source\n\nC1-5 persists the claim-independent capture separately, validates identity and integrity, rehydrates after restart, retains it across retry/stale recovery, and removes it only after canonical terminal commit.\n",
        "\n### C2: one queued-job integration\n\nC2 accepts one caller-selected exact queued record, delegates claim mutation to canonical B3, delegates fresh source/scope preparation to C1-5, invokes C1-2 unchanged, and runs terminal-only protected-source cleanup. It does not scan or schedule the queue.\n",
    )
    old = """## Next integration boundary

The next slice is deliberately smaller than a scheduler:

```text
one exact queued canonical B3 record
  -> canonical B3 claim
  -> C1-5 protected capture lookup
  -> fresh C1-0 source and scope
  -> C1-2 one-claimed worker
  -> B3 retry release or terminal commit
```

It must not:

- scan the queue,
- run a daemon,
- create a generalized worker pool,
- sleep until retry time,
- own broad backoff policy,
- redefine M3 semantics,
- execute inline with visible response delivery.

## End-to-end recall validation

After the one-job adapter exists, prove:
"""
    new = """## Next integration boundary: next-turn recall and scope isolation

C2 now provides the bounded one-job claim/rehydrate/execute path. The next smoke must prove:
"""
    text = replace_once(text, old, new)
    text = replace_once(
        text,
        "Phase 6-C1 is restart-complete for protected-source recovery of durably enqueued jobs. Phase 6 is product-complete for I1 only when ordinary queued work reaches C1-2 through the one-job adapter, queue state converges correctly, a later turn retrieves and uses the memory, and the separate pre-enqueue background-finalizer crash window is resolved or explicitly bounded.",
        "Phase 6-C1 is restart-complete for protected-source recovery of durably enqueued jobs, and C2 completes one exact queued-job execution. Phase 6 is product-complete for I1 only when a later turn retrieves and uses the memory within the correct character/namespace scope and the separate pre-enqueue background-finalizer crash window is resolved or explicitly bounded.",
    )
    return text


def i1b_handoff(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_one_claimed_primary_worker_handoff.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "I1-B, C1-2, C1-4, and C1-5 are implemented. The next bounded boundary is a one-job adapter that accepts one exact queued canonical record, performs B3 claim, rehydrates through C1-5, and invokes C1-2.\n\nIt must remain separate from a queue scanner, daemon, generalized scheduler, and visible response delivery.\n\nAfter that adapter, I1 still requires next-turn recall with character/namespace isolation, real SOUL Lab observation, one auditable Correct operation, and an explicit decision for the pre-enqueue background-finalizer crash window.",
        "I1-B, C1-2, C1-4, C1-5, and C2 are implemented. C2 accepts one exact queued canonical record, performs canonical B3 claim, rehydrates through C1-5, and invokes C1-2 without adding a scanner, daemon, generalized scheduler, or visible-response coupling.\n\nThe next bounded boundary is next-turn recall with character/namespace isolation. Real SOUL Lab observation, one auditable Correct operation, and an explicit decision for the pre-enqueue background-finalizer crash window remain later I1 work.",
    )
    return text


def c1_contract(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_durable_protected_source_persistence.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "The next boundary is a thin C2 one-job queued-record claim/rehydrate/execute adapter, followed by next-turn recall. I1 separately retains the pre-enqueue background-finalizer crash window.",
        "Phase 6-C2 one-job queued-record claim/rehydrate/execute adapter: complete. The next boundary is next-turn recall and scope isolation: next. I1 separately retains the pre-enqueue background-finalizer crash window.",
    )
    return text


def c1_worker_handoff(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_durable_protected_source_persistence.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "C1-2 still does not implement a queue scanner, automatic claim scheduler, daemon supervision, generalized worker pool, the thin one-job queued-record claim/rehydrate adapter, later-turn recall proof, or SOUL Lab observation. Those remain subsequent I1 integration work.",
        "C1-2 still does not implement a queue scanner, automatic claim scheduler, daemon supervision, generalized worker pool, later-turn recall proof, or SOUL Lab observation. C2 now owns the thin one-job queued-record claim/rehydrate adapter without changing C1-2. Next-turn recall and scope isolation are the next I1 integration boundary.",
    )
    return text


def durable_source(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_integrated_worker_fault_smoke_handoff.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    return text


def current_target(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_durable_protected_source_persistence.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "The Phase 6 integration boundary is implemented through C1-5:",
        "The Phase 6 integration boundary is implemented through C1-5 and C2:",
    )
    text = add_once(
        text,
        "C1-5 durable claim-independent protected source and restart rehydration\n",
        "C2 one-job claim/rehydrate/execute adapter\n",
    )
    text = replace_once(
        text,
        "C1-2 executes only one already-claimed canonical B3 job. It does not scan or select queued work. C1-5 persists protected content separately from the content-free queue and creates a fresh C1-0 source/scope for each current claim.",
        "C1-2 executes only one already-claimed canonical B3 job. It does not scan or select queued work. C1-5 persists protected content separately from the content-free queue and creates a fresh C1-0 source/scope for each current claim. C2 accepts one caller-selected exact queued record and connects canonical B3 claim, C1-5 preparation, and unchanged C1-2 execution.",
    )
    text = re.sub(
        r"(?m)^- a bounded ordinary-runtime adapter that accepts one exact queued record, performs B3 claim, rehydrates through C1-5, and invokes C1-2,\n",
        "",
        text,
    )
    text = replace_once(
        text,
        "  -> one-job claim/rehydrate/execute adapter         next",
        "  -> C2 one-job claim/rehydrate/execute adapter      complete",
    )
    text = replace_once(
        text,
        "The sequence is:\n\n1. add the bounded one-job claim/rehydrate/execute adapter,\n2. prove ordinary runtime enqueue -> claim -> rehydrate -> worker -> B3 transition,\n3. validate later-turn recall and character/namespace isolation,\n4. expose real latest-run and memory outcomes through server-owned SOUL Lab APIs,\n5. add one auditable Correct operation that changes later retrieval,\n6. resolve or formally bound the separate pre-enqueue background-finalizer crash window.",
        "The sequence is now:\n\n1. validate later-turn recall and character/namespace isolation,\n2. expose real latest-run and memory outcomes through server-owned SOUL Lab APIs,\n3. add one auditable Correct operation that changes later retrieval,\n4. resolve or formally bound the separate pre-enqueue background-finalizer crash window.",
    )
    text = replace_once(
        text,
        "I1-B, B3, and C1-0 through C1-5 are complete prerequisites. The Primary MEM product loop remains integration pending.",
        "I1-B, B3, C1-0 through C1-5, and C2 are complete prerequisites. Next-turn recall and scope isolation: next; the Primary MEM product loop remains integration pending.",
    )
    text = replace_once(
        text,
        "M3a-M3h completion means the Primary MEM primitives exist. C1-1 fixes their exact order. C1-2 executes one active claim. C1-3 classifies exact outcomes. C1-4 verifies integrated convergence. C1-5 makes protected-source recovery restart-complete for durably enqueued jobs.\n\nNone of these alone means the memory feature is end to end. The active migration is complete only when ordinary queued work reaches C1-2 through the bounded adapter and a later ordinary turn retrieves and uses the resulting memory within the correct scope.",
        "M3a-M3h completion means the Primary MEM primitives exist. C1-1 fixes their exact order. C1-2 executes one active claim. C1-3 classifies exact outcomes. C1-4 verifies integrated convergence. C1-5 makes protected-source recovery restart-complete for durably enqueued jobs. C2 connects one exact queued record to that worker.\n\nThese boundaries still do not make the memory feature end to end. The active migration completes only when a later ordinary turn retrieves and uses the resulting memory within the correct character/namespace scope.",
    )
    return text


def mvp_plan(text: str) -> str:
    text = strip_marker(text)
    text = add_once(
        text,
        "  - phase6c1_durable_protected_source_persistence.md\n",
        "  - phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = replace_once(
        text,
        "RelayMEM's immediate goal is no longer another persistence primitive. M3a-M3h, C1-1/C1-2 execution, C1-4 fault convergence, and C1-5 protected-source restart recovery now exist. The next goal is to connect one ordinary queued job to that worker and prove later-turn recall.",
        "RelayMEM's immediate goal is no longer another persistence primitive. M3a-M3h, C1-1/C1-2 execution, C1-4 fault convergence, C1-5 protected-source restart recovery, and the C2 one-job adapter now exist. The next goal is to prove later-turn recall with character/namespace isolation.",
    )
    text = replace_once(
        text,
        "  M3i-b one-job runtime adapter and next-turn recall: next",
        "  M3i-b one-job runtime adapter: complete as Phase 6-C2\n  M3i-c next-turn recall and scope isolation: next",
    )
    text = replace_once(
        text,
        "## MEM-M3i-b: one-job runtime integration and recall — next",
        "## MEM-M3i-b: one-job runtime integration — complete; recall is next",
    )
    text = replace_once(
        text,
        "M3i-b must:\n\n- add the thin one-job queued-record claim/rehydrate/execute adapter,\n- reuse exact C1/M3 artifacts rather than public projections,\n- verify new memory is discoverable by M2,",
        "C2 completed the one-job portion of M3i-b by adding the thin queued-record claim/rehydrate/execute adapter and reusing exact C1/M3 artifacts rather than public projections. The remaining recall scope must:\n\n- verify new memory is discoverable by M2,",
    )
    text = replace_once(
        text,
        "3. claim and execute one job through the new adapter,",
        "3. claim and execute one job through the C2 adapter,",
    )
    text = replace_once(
        text,
        "M3 is not end-to-end complete until M3i-b passes. C1-0 through C1-5 prove the worker and protected-source restart boundary, not the product recall loop.",
        "The C2 one-job portion of M3i-b is complete, but M3 is not end-to-end complete until next-turn recall and scope isolation pass. C1-0 through C1-5 and C2 prove worker execution and protected-source restart boundaries, not the product recall loop.",
    )
    text = replace_once(
        text,
        "Until M3i-b closes, prefer connecting existing producers and consumers over new persistence schemas, recovery layers, or Secondary MEM behavior.",
        "Until next-turn recall and scope isolation close M3i, prefer connecting existing producers and consumers over new persistence schemas, recovery layers, or Secondary MEM behavior.",
    )
    return text


TRANSFORMS = {
    "docs/PROJECT_STATUS.md": project_status,
    "docs/README.md": docs_readme,
    "docs/architecture/README.md": architecture_readme,
    "docs/architecture/pipeline_implementation_plan.md": pipeline_plan,
    "docs/architecture/phase6_async_relayslp_bounded_slice.md": phase6_slice,
    "docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md": i1b_handoff,
    "docs/architecture/phase6c1_primary_mem_worker_contract.md": c1_contract,
    "docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md": c1_worker_handoff,
    "docs/architecture/phase6c1_durable_protected_source_persistence.md": durable_source,
    "docs/architecture/relaymem_slp_current_target.md": current_target,
    "docs/architecture/relaymem_mvp_implementation_plan.md": mvp_plan,
}


def main() -> None:
    for path in DOCS:
        target = ROOT / path
        if not target.is_file():
            raise RuntimeError(f"missing {path}")
        before = target.read_text(encoding="utf-8")
        after = TRANSFORMS[path](before)
        if after == before:
            raise RuntimeError(f"no change for {path}")
        if "phase6c2-status:start" in after:
            raise RuntimeError(f"marker retained in {path}")
        target.write_text(after, encoding="utf-8")
    print("Phase 6-C2 documentation refined.")


if __name__ == "__main__":
    main()
