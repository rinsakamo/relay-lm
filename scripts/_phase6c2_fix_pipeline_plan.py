from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "docs/architecture/pipeline_implementation_plan.md"
text = path.read_text(encoding="utf-8")
replacements = (
    (
        "  ordinary-runtime one-job runner and next-turn recall: pending\n",
        "  C2 one-job runtime adapter: complete\n  next-turn recall and scope isolation: pending\n",
    ),
    (
        "The next RelayLM Core boundary is a thin one-job claim/rehydrate/execute integration adapter. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior. It is not a queue scanner, daemon, generalized worker pool, or retry scheduler.\n",
        "Phase 6-C2 completes the thin one-job claim/rehydrate/execute integration adapter. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding a queue scanner, daemon, generalized worker pool, or retry scheduler. The next RelayLM Core boundary is next-turn recall and scope isolation.\n",
    ),
    (
        "  -> one-job claim/rehydrate/execute adapter           next\n",
        "  -> C2 one-job claim/rehydrate/execute adapter        complete\n",
    ),
    (
        "### I1-C: Phase 6-C Primary MEM worker — bounded components complete\n",
        "### I1-C: Phase 6-C Primary MEM worker — bounded components and C2 integration complete\n",
    ),
    (
        "- C1-5 durable protected capture, restart lookup, fresh-source construction, retention, and post-terminal cleanup.\n",
        "- C1-5 durable protected capture, restart lookup, fresh-source construction, retention, and post-terminal cleanup,\n- C2 exact queued-record claim, canonical reread, C1-5 preparation, unchanged C1-2 execution, and terminal-only cleanup.\n",
    ),
    (
        "Remaining connection:\n",
        "Completed C2 connection:\n",
    ),
    (
        "The adapter must not scan the queue, own a daemon lifecycle, create a worker pool, sleep until retry time, or redefine RelayMEM semantics.\n",
        "The C2 adapter does not scan the queue, own a daemon lifecycle, create a worker pool, sleep until retry time, or redefine RelayMEM semantics. The remaining I1 connection is next-turn recall with correct character and namespace scope.\n",
    ),
    (
        "- C1-2 exists, but the ordinary runtime still lacks the one-job adapter and later-turn recall proof.\n",
        "- C1-2 and C2 exist, but the ordinary runtime still lacks later-turn recall and scope-isolation proof.\n",
    ),
    (
        "Phase 6 has implemented B0-B3, I1-B, and C1-0 through C1-5. The remaining Phase 6 product connection is one bounded queued-record claim/rehydrate/execute adapter, followed by recall and Lab integration.\n",
        "Phase 6 has implemented B0-B3, I1-B, C1-0 through C1-5, and the bounded C2 queued-record claim/rehydrate/execute adapter. The remaining Phase 6 product connection is next-turn recall and scope isolation, followed by Lab integration.\n",
    ),
)
for old, new in replacements:
    if old not in text:
        raise SystemExit(f"pipeline plan anchor missing: {old[:80]!r}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("Phase 6-C2 pipeline plan consistency fixed.")
