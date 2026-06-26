# Phase I-4D Primary retrieval exclusion

Status: implementation slice complete when its workflow is green.

I-4D owns ordinary Primary MEM lifecycle filtering after existing M2 relevance selection and before RelayCTX/backend-bound injection. M2 continues to own relevance, ordering, candidate caps, and budgets.

## Authority

The implementation reuses the I-4B/I-4C2 read-only current-state scanner. It does not duplicate correction, prepared, hidden-page, finalization, or control schemas.

`relaymem_primary_i4c2_projection.py` now exposes the complete Correct/Forget current map to ordinary retrieval. A logical memory with a pending operation also marks its current physical revision pending. The existing recall compatibility seam therefore excludes the complete prepared-to-finalized interval.

A candidate survives only when M2 already selected it, scope matches, page and controls are canonical, physical identity maps to one logical memory, it is the canonical current physical revision, lifecycle is active, mutation state is none, and retrieval eligibility is true.

Prior revisions, hidden state, prepared state, recovery-required state, corrupt or ambiguous chains, unresolved mappings, stale controls, scope mismatches, and unsafe files fail closed. A hidden successor remains lifecycle authority; retrieval never falls back to a prior active revision.

## M2 and RelayCTX

`apply_relaymem_primary_recall_scope(...)` remains the integration point. It rebuilds selected candidates, snippets, evidence, context candidates, injection plans, runtime evidence, and content-free projection only from eligible candidates.

I-4D does not discover or substitute a current revision when M2 selected only a prior revision. Unrelated active candidates retain their existing relative order and budgets. A forgotten memory is absent from every RelayCTX handoff and from fresh backend-bound messages.

## Internal decision reasons

```text
eligible_current_active
excluded_prior_revision
excluded_hidden
excluded_prepared
excluded_recovery_required
excluded_corrupt
excluded_unresolved_identity
excluded_scope_mismatch
excluded_unsafe
```

The decision representation excludes content, paths, namespace values, identities, digests, operation data, and raw exceptions.

## Historical projection

The durable `relaylm.lab.memory_used.v0` receipt and existing v0 endpoint remain unchanged. I-4D adds the separate read-only schema `relaylm.lab.memory_used_lifecycle.v1`.

Each item retains historical `injected_summary` and overlays `current_summary`, `current_lifecycle_state`, `representation_changed`, and `lifecycle_changed`. Current summary is null for hidden or unresolved state. Mutation reasons, tokens, internal identifiers, paths, digests, and artifact bodies are not projected.

A dedicated strict TypeScript parser follows the new version. I-4D adds no mutation route or mutation UI.

## Validation boundary

Retrieval does not recover, write, lock, poll, or retry. Prepared and partial hidden states are ineligible. Stable bounded rereads reject non-regular, multiply-linked, oversized, unsafe, or changed files.

The dedicated workflow covers lifecycle/current/prior-revision filtering, recovery states, RelayCTX handoff exclusion, fresh-conversation backend absence, immutable historical evidence with current lifecycle overlay, content-free diagnostics, prior phase regressions, frontend typecheck/build, documentation links, and compileall.

I-4E remains the loopback API and SOUL Lab mutation UI. I-4F remains the full production validation slice.
