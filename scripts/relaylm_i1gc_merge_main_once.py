"""One-shot reconciliation of the I1-GC documentation boundary after merging main."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "I1-GC durable-finalization replay current boundary (2026-06-26)"

STATUS = f"""## {MARKER}

I1-GC is complete at the one-record replay boundary. The production path reconstructs
one sealed finalized turn, verifies its sealed A1/A2/B1 identity, converges existing
C1-5 before existing B2, canonically rereads both artifacts, and publishes one
immutable content-free completion marker under a nonblocking cross-process per-record
fence. The normal I1-GB finalizer uses the same authority.

This section supersedes earlier I1-GC pending statements in this file. I1-GD, I1-GE,
O1B discovery/delegation and O1C through O1F scheduling production work remain
incomplete. O1A is a completed contract-only boundary, not an automatic scheduler.
"""

COMMON = f"""## {MARKER}

This section supersedes earlier statements in this file that describe I1-GC as pending.

I1-GC is implemented as a caller-selected, one-record production convergence authority:

```text
sealed I1-G evidence
  -> exact finalized-turn source reconstruction
  -> existing A1 / A2 / B1 preparation
  -> exact sealed job / dispatch identity verification
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable completion marker
  -> content-free replay result
```

The normal I1-GB background finalizer and restart replay share the same nonblocking,
cross-process, deterministic per-locator fence. Completion is published only after
canonical reread proves exact C1-5 source-before-B2 queue correlation. A terminal B3
record may satisfy that downstream proof without mutation, but I1-G completion does
not mean B3 terminal success, worker execution, or Primary MEM formation.

Duplicate, race, uncertain-write, and restart paths converge by canonical reread.
`queue exists / source absent`, identity mismatch, collision, corruption, unsupported
schema, symlink, hardlink, and unsafe file type fail closed. Public projections remain
content-free and omit locator, digest, path, namespace, job, dispatch, lineage,
timestamp, lease token, protected payload, and raw exception values.

O1A remains the completed pure replay-then-queue scheduler-round contract. It does not
discover records or invoke I1-GC. Future O1B may discover and delegate one exact sealed
record to this authority without owning completion semantics.

Still incomplete and intentionally out of scope:

- I1-GD retention, orphan reconciliation, isolation lifecycle, and cleanup
- I1-GE full crash-at-every-boundary production validation
- O1B sealed-record discovery and one I1-GC delegation
- O1C through O1F production queue discovery, ordering, fairness, recovery, and validation
- O2 supervised always-on worker service
- B3 transition, C2/worker execution, M3a-M3h, and SOUL Lab UI from replay
"""

ROADMAP = f"""## {MARKER}

Completed dependency edge:

```text
I1-GA contract
  -> I1-GB pre-release sealed publication
  -> I1-GC one-record restart replay and completion convergence  [complete]
```

The operations boundary now separates the completed O1A contract from production work:

```text
O1A pure replay-then-queue round / idle contract  [complete]
  -> O1B sealed-record discovery / one I1-GC delegation
  -> O1C B2 discovery / one O0-compatible C2 delegation
  -> O1D ordering / fairness / retry-time / backoff / jitter
  -> O1E stale recovery / cancellation / graceful shutdown
  -> O1F production validation
```

The remaining I1-G durability work is:

```text
I1-GD retention / orphan reconciliation / cleanup
  -> I1-GE full production crash validation
```

This section supersedes earlier roadmap entries that list I1-GC itself as pending.
I1-GC does not add discovery, batch replay, retry loops, cleanup, B3 transitions,
C2 execution, workers, M3 writes, or UI.
"""

UPDATES = {
    "docs/PROJECT_STATUS.md": STATUS,
    "docs/README.md": STATUS,
    "docs/architecture/README.md": STATUS,
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md": COMMON,
    "docs/architecture/pipeline_implementation_plan.md": ROADMAP,
    "docs/architecture/post_i3_evaluation_work_roadmap.md": ROADMAP,
    "docs/architecture/relaymem_slp_current_target.md": STATUS,
    "docs/architecture/relaymem_mvp_implementation_plan.md": ROADMAP,
}

for relative, section in UPDATES.items():
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        path.write_text(text.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")

smoke_path = ROOT / "scripts/relaylm_documentation_current_boundary_smoke.py"
smoke = smoke_path.read_text(encoding="utf-8")
SMOKE_MARKER = "# I1-GC documentation boundary assertions"
if SMOKE_MARKER not in smoke:
    smoke += f'''\n\n{SMOKE_MARKER}\ndef _assert_i1gc_documentation_boundary() -> None:\n    root = Path(__file__).resolve().parents[1]\n    required = {tuple(UPDATES)!r}\n    for relative in required:\n        text = (root / relative).read_text(encoding="utf-8")\n        assert {MARKER!r} in text, relative\n        assert "I1-GD" in text, relative\n        assert "I1-GE" in text, relative\n        assert "O1A" in text, relative\n        assert "O1B" in text, relative\n    replay = (root / "relaylm/relaymem_slp_durable_finalization_replay.py").read_text(encoding="utf-8")\n    implementation = (root / "relaylm/_relaymem_slp_durable_finalization_replay_impl.py").read_text(encoding="utf-8")\n    assert "replay_relaymem_slp_durable_finalization_record" in replay\n    assert "COMPLETION_SCHEMA" in implementation\n    assert "transition_relaymem_slp_queue_state" not in implementation\n\n\nif __name__ == "__main__":\n    _assert_i1gc_documentation_boundary()\n'''
    smoke_path.write_text(smoke, encoding="utf-8")
