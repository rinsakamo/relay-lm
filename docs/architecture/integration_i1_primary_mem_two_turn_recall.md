---
relaylm_doc_type: implementation_handoff
relaylm_authority: primary_mem_two_turn_recall
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary recall producer or consumer changes
  - Primary writer or reader cutover decisions change
  - character or namespace scope changes
  - downstream observation or mutation boundary changes
  - Primary recall candidate discovery or retirement changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - Subjective MEM ordinary Retrieval, ranking, or projection semantics
  - RT-1D-R5 completion, Primary retirement, or deletion approval
  - queue scanning, scheduler, or daemon lifecycle
  - SOUL Lab observation schema details
  - memory mutation contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - subjective-mem-retrieval-projection-hard-cutover.md
  - phase_i4d_primary_retrieval_exclusion.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - phase6c2_one_queued_primary_worker_integration.md
  - project_execution_plan.md
  - relaymem_slp_current_target.md
  - ../evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md
---
# Primary MEM Two-Turn Compatibility Handoff

Last reviewed: 2026-08-08 JST

## Transitional status

Historical handoff identity: **Integration I1: Primary MEM Two-Turn Recall**.

Phase I-1 proved the original durable Primary formation -> later Primary recall
integration. That proof remains useful regression and historical evidence, but it
no longer defines the universal ordinary memory authority after RT-1D-R4.

This legacy underscore-named document therefore remains a transitional D5 source:

- owner: RelayMEM compatibility / Lane D documentation canonicalization;
- current consumers: Primary-only integration regressions, Phase I-2 observation
  evidence, E1 evaluation, and RT-1 retirement review;
- removal gate: RT-1D-R5/R6 proves the final disposition of the Primary ordinary
  writer, reader, fallback, and every continuing historical/operational consumer;
- replacement validation: the final Retrieval/Primary documentation graph retains
  every still-current scope, fail-closed, projection, and observation contract
  before this handoff is retired through the retirement manifest and Git history.

Repository-wide implementation and retirement status remain owned by
`docs/PROJECT_STATUS.md` and the RT-1 hard-cutover authority.

## Current responsibility

The old two-turn path now exists only as a bounded Primary compatibility proof.
The complete Primary formation -> later Primary recall chain is possible only
while both of these exact cutover decisions allow it:

1. the Primary writer decision is `permitted`; and
2. the later ordinary reader decision is `primary_only`.

The cutover owner derives both decisions from durable cutover state. Configuration,
store presence, a successful historical I1 run, or an empty Subjective result does
not authorize either Primary writing or Primary reading.

Primary writes remain permitted only strictly before `primary_writer_fenced`.
After that state, the writer decision is rejected and no old Phase I-1 formation,
worker, Correct/Forget apply/recovery, Pin/Unpin, or related caller may use a
pre-fence token or missing decision to restore Primary mutation authority.

The ordinary Retrieval facade resolves the reader decision before touching any
memory store:

```text
primary_only
  -> Primary compatibility Retrieval may run

neither
  -> no ordinary durable-memory authority is read

subjective_only
  -> no Primary root resolution, store diagnostics, candidate discovery,
     recall, or fallback
  -> only finalized Subjective evidence may be released
```

A missing, foreign, malformed, or tampered reader decision fails closed to
`neither`; it does not silently restore Primary.

## Primary-only two-turn compatibility flow

When the writer is still permitted and the later reader decision is
`primary_only`, the historical integration shape remains:

```text
Turn 1 managed response
  -> durable source / queue evidence
  -> explicit one-record worker execution
  -> bounded Primary durable formation
  -> terminal success

Turn 2 managed request
  -> exact RT-1 Primary-only reader decision
  -> character-partitioned RelayMEM root
  -> M2 preferred candidate discovery
  -> exact Primary page / index / log / namespace validation
  -> shared Primary lifecycle/current-state eligibility
  -> bounded E1-R5 fallback only if no eligible scoped M2 candidate survives
  -> request-local selected-memory artifact
  -> existing RelayCTX grounding / injection handoff
  -> backend-bound request
```

This is a compatibility path, not a second ordinary reader beside Subjective MEM.
Once the reader decision is `subjective_only`, none of the Turn 2 Primary branch
runs. Once the writer decision is rejected, the old Turn 1 Primary formation
branch cannot create or mutate new Primary authority.

There is no dual read, precedence contest, stale-projection fallback, empty-result
fallback, or Subjective-failure fallback to Primary.

## Primary-only selection and scope

Inside `primary_only`, existing M2 discovery remains the preferred relevance
source. The retained Primary recall owner narrows or rebuilds only bounded,
validated candidates for the exact character and namespace scope.

If no eligible scoped Primary candidate survives the preferred M2 path, the
absorbed E1-R5 compatibility fallback may inspect bounded Primary index/log/page
controls for an eligible relevant page. That fallback remains inside the same
Primary-only authority and is not independently reachable.

The compatibility path may admit a Primary candidate only when all of the
following remain exact:

- character store and namespace scope are valid;
- path is a safe non-symlink Primary Markdown page inside the scoped root;
- page schema and bounded body are valid;
- index/log linkage and digest/currentness checks agree;
- physical identity resolves to one logical memory;
- the physical revision is the canonical current revision;
- lifecycle is active;
- mutation state is none;
- retrieval eligibility is true;
- query relevance, item count, character count, and token budget stay bounded.

Prior, hidden, prepared, recovery-required, corrupt, unresolved, unsafe,
cross-scope, wrong-namespace, duplicate, or relevance-insufficient candidates fail
closed. A hidden successor never causes fallback to an older active revision.

Slash-style namespaces such as `character/default` remain accepted by the
retained Primary compatibility path so historical formation and Primary-only
recall do not disagree solely on namespace-token shape. Character ids,
namespaces, roots, paths, digests, lineage, and exact identities remain
runtime-private.

## RelayCTX and grounding boundary

Only admitted bounded Primary evidence reaches the existing RelayCTX grounding
and injection handoff inside `primary_only`. This document does not define a
global precedence between Primary and Subjective MEM; the RT-1 reader decision
first decides which ordinary memory authority exists for the request.

Primary paths, namespace values, character ids, lineage, digests, idempotency
metadata, retry state, queue state, and lifecycle internals are not placed in the
backend prompt merely because a Primary candidate was selected.

The runtime artifact containing Primary snippets remains request-local and must
not be copied into generic pipeline results, trace, stdout/stderr, or workflow
logs.

## Public projection

The retained Primary recall projection is content-free. It may expose only bounded
status such as attempted/selected counts, Primary-layer counts, scope booleans,
estimated size, injection-candidate presence, fallback discovery counts, and
reason ids.

It must not expose raw memory text, raw transcript text, protected source bodies,
queue payloads, roots, paths, namespace values, claim or lease material, digests,
lineage, operation data, or exact private identities.

## Idempotency and mutation separation

Dispatch identity, durable Primary write identity, retrieval deduplication,
cutover writer/reader decisions, and observation receipt identity are separate.

Historical C2/M3 formation owns its durable write idempotency only while the
Primary writer decision permits it. Primary-only recall deduplicates admitted
physical/logical identity before RelayCTX assembly. Neither duplicate discovery,
worker retry, nor Phase I-2 replay may multiply memory in the prompt or restore a
fenced writer/reader.

## Phase I-2 observation boundary

Phase I-2 remains read-only evidence about the historical/current compatibility
path. It may distinguish candidate, selected, injected, backend-bound, and
response-completed stages after restart, but its **observation receipt** is
secondary evidence only.

An observation receipt cannot:

- authorize Primary writing or reading;
- turn `neither` into a serving authority;
- make an unselected candidate selected;
- replay Primary evidence into a later request;
- override character or namespace isolation;
- replace the RT-1 reader/writer decisions.

See [Phase I-2 Real SOUL Lab Observation](../evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md).

## Historical Phase I-3 boundary

Phase I-3 auditable Primary Correct remains historical implementation evidence for
how one Primary revision could be corrected while Primary mutation authority was
permitted. Current Correct lifecycle semantics are owned by the current Subjective
MEM lifecycle architecture and runtime boundaries, not by this I1 handoff.

The old I1/Phase I-3 evidence therefore does not authorize a Primary writer after
`primary_writer_fenced` and does not make Primary an ordinary reader after
`subjective_only`.

Historical implementation evidence remains available at
`docs/evidence/implementation/phase-i3-auditable-primary-mem-correct-handoff.md`.

## R5 removal gate

RT-1D-R5 owns retirement of the replaced Primary ordinary reader/fallback and
associated temporary execution surfaces. R6/final retirement owns the remaining
repository/documentation cleanup after exact consumers are proved.

This document does not pre-authorize deletion and does not predict which
read-only historical, observation, migration, rollback, or operational consumers
will remain. A live component survives only when an accepted continuing
responsibility is proved; otherwise Git history is the recovery surface after its
owning atomic retirement.

## Validation boundary

While this compatibility handoff remains active, validation must continue to
prove at least:

- Primary writer rejection after the writer fence;
- no Primary store access for `neither` or `subjective_only`;
- no Primary fallback after Subjective transfer;
- Primary-only character/namespace isolation and lifecycle exclusion;
- bounded M2-preferred / E1-R5 fallback behavior;
- request-local/private evidence handling;
- content-free public projections;
- Phase I-2 observation receipt non-authority;
- historical I1/E1 regression evidence remains linkable.

Existing Phase I-1 two-turn, E1-R5, I-4D, RT-1 request-path, and Phase I-2
smokes remain regression evidence while their exact owning surfaces still exist.
The current workflow/registry is the command authority; this handoff is not a
second smoke registry.

## Non-goals

No Subjective MEM selection/ranking/projection implementation, RT-1D-R5
completion, Primary retirement/deletion, queue scanner/scheduler/daemon authority,
automatic migration/repair, browser-owned trust, new lifecycle mutation semantics,
Secondary consolidation, RelaySOUL mutation, static UI serving, media runtime
execution, or post-hoc visible-response rewriting is authorized here.
