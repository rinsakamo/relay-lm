---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_contract
relaylm_status: current
relaylm_owner: relaymem_primary_governance
---
# Phase I-5B Pin / Unpin apply and ranking behavior

Phase I-5B connects the I-5A Pin / Unpin read-only contract to durable runtime apply, bounded SOUL Lab API/UI contracts, existing SOUL Lab app route wiring, and a deterministic Primary MEM ranking hint.

## Scope

I-5B applies only to one real, current, active Primary MEM in one character-scoped store and namespace. Pin state is governance metadata, not lifecycle metadata. It does not alter semantic memory content, does not publish a successor page, and does not make hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions eligible for ordinary retrieval.

## Durable state

The runtime stores content-free Pin / Unpin receipts under `memory/mem/pins/v0/<memory_id>/` and a bounded state projection in `state.json`. The artifacts are runtime-private and contain operation kind, bounded public status, current revision, target pin state, receipt id, and effect flags. Raw reason text, token values, filesystem paths, and physical-id values are not exposed through public projections.

If a process exits after a receipt is written but before `state.json` is refreshed, subsequent reads derive the effective state from the latest valid receipt. A replay of the same operation republishes the state projection and returns an idempotent content-free result.

## Apply authority

Apply revalidates the I-5A `relaylm.primary_pin_apply_token.v0` or `relaylm.primary_unpin_apply_token.v0` token before writing durable evidence. The implementation uses the shared per-memory mutation lock from the Correct / Forget coordinator and inspects existing Correct / Forget operation artifacts. Pending Correct / Forget evidence blocks Pin / Unpin.

## API/UI boundary

SOUL Lab browser contracts use no-store same-origin requests and exact response parsing. The browser supplies namespace, memory id, expected revision, reason, operation id, and apply token only. It cannot supply a store root, filesystem path, physical id, route authority, or token claims.

The production SOUL Lab wrapper mounts Pin / Unpin as loopback-only management routes through `relaylm/soul_lab_memory_pin_routes.py`. The existing Lab Observation page mounts `PrimaryMemoryPinPanel` only from active formed Primary MEM rows.

Preflight, refresh, row selection, and history load are read-only. Apply is reachable only from an explicit confirmation action after a ready preflight response. Stale browser generation fencing discards responses when the active character, namespace, memory id, revision, or component generation changes.

## Ranking behavior

Pin state is a deterministic ranking hint only. The Pin ranking helper reorders already selected Primary candidates by placing pinned eligible candidates before unpinned eligible candidates while preserving original order as the tie-breaker. Lifecycle and current-state eligibility remain the preceding authority; Pin state never admits hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions.

The ranking projection is content-free and does not include artifact paths, operation ids, raw reason text, token digests, or physical ids.

## Non-goals

This phase does not implement hidden-memory retrieval, restore/unhide/purge, semantic memory rewriting, Secondary MEM consolidation, merge/supersession, Held Apply/Discard runtime, RelaySOUL mutation, queue/worker/scheduler changes, durable-finalization changes, automatic ranking learning, or Home-origin trusted formation.
