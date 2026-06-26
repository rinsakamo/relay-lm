# Wave 3 I-4D completion report

## Identity

- Slice: Phase I-4D Primary lifecycle-aware retrieval exclusion
- Start main SHA: `4d31f45cfba967e23bd50f01f3c3d7ce9a8d0a33`
- Branch: `phase-i4d-primary-retrieval-exclusion`
- PR: #413

## Implemented boundary

- Ordinary retrieval consumes the complete shared Correct/Forget current-state index.
- Only the canonical current active physical revision remains eligible.
- Prior, hidden, prepared, recovery-required, corrupt, ambiguous, unresolved, and unsafe candidates fail closed.
- Existing M2 ordering, relevance, caps, budgets, and bounded handoff reconstruction remain authoritative.
- Fresh RelayCTX/backend-bound requests cannot include forgotten content.
- Historical used-memory receipts remain immutable.
- The separate `relaylm.lab.memory_used_lifecycle.v1` projection overlays current lifecycle without changing v0 compatibility.

## Validation

The dedicated workflow includes I-4D lifecycle, prior-revision, recovery-state, RelayCTX, fresh-conversation, historical projection, frontend schema, and leakage smokes plus I-4B/I-4C1/I-4C2/I-1/I-2/I-3 regressions.

Workflow result: pending PR execution.

## Documentation governance

Per the Wave 3 convergence rule, this PR adds only the dedicated architecture handoff and this completion report. Shared status documents remain reserved for the Wave 3 integration update.

## Remaining boundary

- I-4E loopback API and SOUL Lab mutation UI: unimplemented.
- I-4F full production validation: unimplemented.
