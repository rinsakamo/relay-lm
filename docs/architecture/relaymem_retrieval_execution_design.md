---
relaylm_doc_type: current_target_migration
relaylm_authority: relaymem_retrieval_runtime_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - ordinary memory reader decision changes
  - Primary or Subjective retrieval owner changes
  - RelayINT or RelaySCN retrieval input contract changes
  - RelayCTX selected-memory handoff changes
  - RT-1D-R5 or R6 retirement disposition changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status or sequencing
  - exact RT-1 durable cutover state or retirement approval
  - Primary or Subjective lifecycle mutation semantics
  - E1-R4 grounding policy internals
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_slp_current_target.md
  - current_target_migration_guide.md
  - ../contracts/grounded-recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - integration_i1_primary_mem_two_turn_recall.md
  - ../PROJECT_STATUS.md
---
# RelayMEM Retrieval Execution Design

Last reviewed: 2026-08-08 JST

## Purpose

RelayMEM Retrieval is the synchronous, read-only ordinary-memory stage for the current managed response. Its public facade, `relaylm/retrieval/runtime.py`, is the sole ordinary routing boundary between retained Primary compatibility retrieval, the fenced no-reader state, and finalized Subjective retrieval.

```text
Retrieval improves the current answer.
RelaySLP improves future memory.
```

This document describes current responsibility and the remaining retirement boundary. Repository-wide status remains owned by Project Status and exact RT-1 cutover state remains owned by the hard-cutover authority.

## Current one-authority runtime boundary

`run_relaymem_retrieval_stage(...)` resolves the immutable RT-1 reader decision **before any ordinary memory authority is touched**. The exact reader classes are:

```text
primary_only
  -> retained Primary compatibility retrieval only

neither
  -> no ordinary durable-memory authority

subjective_only
  -> finalized Subjective retrieval only
  -> no Primary root resolution, discovery, recall, ranking, or fallback
```

Primary and Subjective are never combined for one ordinary request. A missing, malformed, foreign, or otherwise invalid reader decision fails closed through the cutover owner; configuration values, store presence, old success, empty results, or grounding output do not select a different authority.

A refused, failed, or empty Subjective result continues without durable-memory context. There is no dual read, precedence between memory families, empty-result fallback, stale-projection fallback, or Primary fallback from `subjective_only`.

## Stage inputs

The current stage receives bounded request/runtime dependencies equivalent to:

```text
RelayLMConfig
ResolvedRoute
configured RelayMEM store root
RelaySCN scene-policy artifact
RelayINT intent artifact
request messages
exact primary_reader_decision
request correlation identity
```

The reader decision dominates the store and retrieval inputs. Inputs that could support Primary retrieval are not permission to read Primary storage when the decision is `neither` or `subjective_only`.

The stage is intentionally blocking/synchronous and is invoked by the managed pipeline through the existing offloaded stage boundary. The offload mechanism is an execution detail; it does not own memory authority.

## `primary_only` compatibility branch

While the exact reader decision is `primary_only`, the current facade retains the historical Primary request path:

```text
reader decision -> primary_only
  -> resolve character-scoped Primary root
  -> build bounded store diagnostics
  -> build the existing retrieval dry-run/runtime artifact
  -> if scope is allowed, run canonical Primary recall
  -> stamp ordinary_memory_authority=primary_only
```

This branch may use the existing Primary store diagnostics, query preparation, candidate/snippet planning, lifecycle/currentness filtering, and bounded E1-R5 fallback folded into canonical Primary recall. Those responsibilities remain compatibility behavior only inside `primary_only`; they do not authorize a second reader and do not survive into `subjective_only` by fallback.

The broad historical Primary artifact can contain runtime-private or content-bearing fields. `diagnostics_only` or dry-run naming does not by itself make the entire artifact safe for generic persistence. Persisted trace/audit output must use the existing typed content-free projection boundaries.

RT-1D-R5 owns retirement of replaced Primary ordinary-reader/fallback execution surfaces. This document records the live branch before that retirement and does not pre-authorize deletion.

## `neither` fenced branch

When the exact reader class is `neither`, Retrieval does not resolve a Primary root, inspect Primary diagnostics, run Primary candidate discovery/recall/fallback, or acquire Subjective evidence.

The stage returns bounded fenced diagnostics/artifact state with facts equivalent to:

```text
ordinary_memory_authority=neither
primary_reader_fenced=true
primary_store_read=false
selected_mem_candidates=[]
apply_decision=not_eligible
snippet_apply_decision=not_eligible
```

The fenced state is a deliberate no-reader transition, not an error-driven reason to retry a different authority.

## `subjective_only` finalized branch

When the exact reader class is `subjective_only`, the facade never resolves a Primary root and never runs Primary discovery, recall, lifecycle filtering, E1-R5 fallback, or any other Primary ordinary-reader owner.

The current Subjective serving order is fixed:

```text
exact reader decision -> subjective_only
  -> acquire the live projection bound to the finalized transfer authority
  -> exact-verify projection/source/generation bindings
  -> build the bounded retrieval request
  -> select exact current eligible Subjective revisions
  -> prepare runtime-private handoff
  -> durably finalize exact content-free usage events/results
  -> receive the sealed admitted handoff
  -> release fresh grounding dictionaries
```

Only the admitted handoff returned after exact durable usage finalization can release runtime-private grounding evidence. Projection disagreement, source disagreement, selection refusal, empty selection, finalization failure, conflict, or malformed state releases no ordinary durable-memory evidence and never falls back to Primary.

The Subjective branch therefore reuses the existing E1-R4 evidence shape without moving grounding semantics into Retrieval.

## Output contract

The stage returns two request-local values:

1. bounded store/fence diagnostics; and
2. the retrieval artifact used by later RelayCTX stages.

Every ordinary retrieval artifact names the selected family through `ordinary_memory_authority`.

### Primary compatibility artifact

The `primary_only` branch retains the existing broad Primary retrieval artifact shape for compatibility. It may include candidate/snippet/runtime planning fields and is not automatically content-free as a whole.

### Fenced artifact

The `neither` and `subjective_only` branches use a bounded fenced artifact. It always records that Primary storage was not read. A successful Subjective release may add runtime-private selected evidence under the Subjective runtime key, making the whole request-local artifact content-bearing even though the Primary-fence diagnostics themselves remain content-free.

Public/log/audit projections must therefore remain typed and content-free rather than serializing the request-local artifact generically.

## RelayINT and RelaySCN boundary

The historical design described Retrieval as depending on a RelayREF-shaped compatibility input and treated typed RelayINT as future work. That is no longer the current interface: the stage now receives a `relayint_intent_artifact` directly together with RelaySCN scene policy and request messages.

RelayINT/RelaySCN inputs may narrow or block retrieval inside the selected authority, but they cannot override the RT-1 reader decision. The reader class is resolved first and dominates whether a memory family may be touched at all.

RelayREF remains post-generation/reference observation authority and is not the ordinary reader selector.

## E1-R4 and RelayCTX handoff

Retrieval selects exactly one ordinary memory family, if any. Later RelayCTX repack reads selected memories only from the family named by `ordinary_memory_authority` and applies the existing E1-R4 grounding policy.

```text
Retrieval reader decision
  -> exactly one authority or neither
  -> request-local selected memories from that authority only
  -> RelayCTX repack
  -> shared E1-R4 grounded recall policy
  -> backend-bound request
```

E1-R4 remains the grounding-policy owner. Retrieval does not classify support, invent a second Subjective grounding policy, combine Primary and Subjective evidence, or use grounding status as reader authorization.

## Safety and authority invariants

The stable execution invariants are:

- Retrieval is read-only in the interactive path.
- The exact RT-1 reader decision is resolved before ordinary memory access.
- `primary_only` may touch only the retained Primary compatibility reader.
- `neither` touches no ordinary durable-memory authority.
- `subjective_only` touches no Primary ordinary-reader owner.
- Primary and Subjective evidence are never merged for one request.
- Empty/refused/failed Subjective retrieval never causes Primary fallback.
- Selected Subjective evidence is released only after exact durable usage finalization.
- lifecycle, scope, generation, and canonical-source disagreement fail closed.
- request-local content-bearing artifacts are not generic persisted diagnostics.
- typed public/audit projections remain content-free.
- Retrieval never writes canonical memory, lifecycle state, relationship state, preferences, or RelaySOUL proposals.

Mutation, formation, lifecycle publication, and durable-memory retirement remain owned elsewhere.

## RT-1D-R5 / R6 retirement boundary

Current Project Status records R4 activation/P8 complete and R5 immediate retirement unstarted. Consequently this design still records the live `primary_only` compatibility branch.

R5/R6 own the eventual retirement or explicitly read-only retained disposition of:

- ordinary Primary reader/fallback execution surfaces;
- temporary rehearsal/shadow execution surfaces;
- compatibility tests and documentation that exist only to prove those serving paths;
- any remaining historical/operational Primary consumers after exact dependency characterization.

R5 must not be implemented by silently moving Primary reader behavior into another module, weakening request-path tests, adding dual read, or treating Subjective failure as fallback permission. Lane D documentation canonicalization does not authorize those changes.

## Validation boundary

Current validation should continue to prove, at minimum:

- exact reader-class routing;
- no Primary root resolution or Primary reader call in `neither` / `subjective_only`;
- no Subjective evidence release before durable usage finalization;
- empty/refused/failed Subjective behavior without Primary fallback;
- exact one-authority RelayCTX/E1-R4 consumption;
- managed-stage offload/liveness contract;
- content-free public/audit projections;
- R5 retirement behavior when the owning transaction changes the production surface.

The workflow and test registry remain the command authority; this document is not a second CI registry.

## Non-goals

This page does not authorize:

- RT-1D-R5/R6 implementation or Primary deletion;
- lifecycle mutation;
- queue/worker/scheduler mutation;
- a second ordinary reader;
- Primary/Subjective precedence or merge;
- Subjective-to-Primary failure fallback;
- post-hoc visible-response rewriting;
- generic persistence of runtime-private retrieval evidence;
- new API/UI authority;
- new memory formation, relationship, preference, or RelaySOUL mutation.

## Summary

```text
current
  exact RT-1 reader decision first
  -> primary_only: retained Primary compatibility retrieval
  -> neither: fenced no-reader result
  -> subjective_only: finalized Subjective retrieval with no Primary read/fallback
  -> RelayCTX consumes only the selected authority
  -> E1-R4 applies the shared grounding policy

after owning R5/R6 retirement
  Primary ordinary-reader/fallback and temporary cutover surfaces may be removed
  only according to the exact retirement authority and validated dependency set
```
