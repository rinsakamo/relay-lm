---
relaylm_doc_type: evidence
relaylm_authority: session_evidence_overlay_current_relayctx_alignment_record
relaylm_status: historical
relaylm_volatility: high
relaylm_owner: context_memory
relaylm_update_trigger:
  - the current RelayCTX short-term runtime contract changes materially
  - the CTX-OVL proposal or feasibility conclusion changes materially
  - cross-request RelayCTX continuity is implemented
relaylm_not_authoritative_for:
  - accepted CTX-OVL architecture
  - current runtime behavior beyond the linked current contract
  - exact CTX-OVL schema, implementation sequence, or production enablement
  - durable MEM authority
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 5d60433713574c042afe5ceab15b865a48824ae5
relaylm_source_pr: 586
relaylm_recorded_on: 2026-07-15
relaylm_related_evidence:
  - session-evidence-overlay-feasibility.md
  - relayatn-ctx-ovl-boundary-review.md
relaylm_related_contracts:
  - ../../contracts/context_compiler_contract.md
  - ../../contracts/relayctx_short_term_runtime_contract.md
---

# CTX-OVL Feasibility Alignment with the Current RelayCTX Runtime Contract

## Purpose

This dated addendum aligns the CTX-OVL feasibility assessment with the current-code-derived [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md) introduced on `main` after the original feasibility inventory began.

It does not amend that current contract, accept the CTX-OVL proposal, or authorize implementation.

## Current implemented RelayCTX boundary

The current managed runtime already contains a four-stage, default-off RelayCTX short-term chain:

```text
short-term extraction dry-run
  -> block assembly dry-run
  -> runtime injection preflight
  -> runtime injection apply gate
  -> token-budget truncation
```

The chain provides reusable safety and ordering evidence:

- deterministic request-local extraction;
- content-free artifacts and diagnostics;
- explicit enable and dry-run gates;
- strict predecessor-artifact dependencies;
- deep-copy discipline before backend-bound payload mutation;
- bounded token-budget checks;
- fail-closed blocked-reason handling;
- RelayCTX injection before token-budget truncation;
- no response mutation, persistence, or cross-thread restore.

The apply call site exists, but the feature remains default-off and request-local. This is current short-term RelayCTX plumbing, not CTX-OVL.

## CTX-OVL capabilities that remain absent

The current contract does not provide:

- an app-scoped cross-request overlay store;
- session, participant, room, relationship, scene-epoch, or quarantine partitions;
- content-bearing provisional semantic candidates;
- rejected-ingress coverage or catch-up;
- correction, retraction, or durable-MEM shadow reconciliation;
- a RelayCTX Reflex Snapshot for RelayATN;
- stream-finalization visibility guarantees for immediate next-turn continuity;
- RelaySLP source-lineage acknowledgement and cleanup;
- restart recovery for provisional continuity.

Accordingly, the feasibility conclusion remains unchanged: CTX-OVL is implementable within RelayCTX boundaries, but it is not an existing feature waiting to be enabled.

## Reuse boundary

A future CTX-OVL contract may reuse the current chain's architectural principles, but must not silently overload its schemas:

```text
current relayctx_short_term_* artifacts
  = request-local, content-free extraction / planning / injection governance

future relayctx.session_evidence_overlay.*
  = bounded cross-request, content-bearing provisional continuity
```

The two paths have different authority, retention, privacy, reconciliation, and failure semantics. Any production design requires separate schemas and an explicit integration point with the current RelayCTX runtime ordering.

## Documentation consequence

The original feasibility record remains the broad design and implementation-gap assessment. This addendum supplies the current-contract delta created by the ongoing documentation cutover without rewriting the historical assessment as though the current short-term chain already implemented CTX-OVL.

No runtime behavior, configuration default, implementation authorization, or durable-memory authority changes through this record.
