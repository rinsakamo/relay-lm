---
relaylm_doc_type: architecture_target
relaylm_authority: rt1_subjective_mem_retrieval_projection_and_hard_cutover
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM ordinary-Retrieval eligibility or projection authority changes
  - Primary MEM ordinary reader or writer retirement changes
  - durable retrieval-usage event authority changes
  - projection rebuild, shadow characterization, or hard-cutover sequencing changes
  - request-path grounding handoff changes
relaylm_not_authoritative_for:
  - current runtime implementation or completion status
  - exact cache database, table, index, vector, or FTS schema
  - exact ranking, embedding, or retrieval-fusion algorithm
  - migration of existing Primary MEM content into Subjective MEM
  - deployment approval, default-on policy, backup, restore, or rollback procedure
  - multi-host writer coordination
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-pin-unpin-runtime.md
  - subjective-mem-restore-runtime.md
  - subjective-mem-consolidate-runtime.md
  - relaymem_slp_current_target.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - e1r4_retrieval_response_grounding.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - acg3_retrieval_query_normalization.md
  - project_execution_plan.md
---
# RT-1 Subjective MEM Retrieval Projection and Hard Cutover

## Status and purpose

This document defines the accepted target architecture for RT-1 before runtime
implementation.

RT-1 replaces the current Primary MEM ordinary-recall authority with one
Subjective MEM ordinary-Retrieval authority. It does so through a disposable
projection, exact current-revision eligibility, content-free durable usage
events, shadow-only characterization, one explicit authority transfer, and
retirement of the replaced Primary readers and writers.

This architecture does not claim RT-1 is implemented. It does not enable
Subjective MEM Retrieval, change feature defaults, migrate user data, or retire
Primary MEM by itself.

## P0 current boundary

The current ordinary recall path remains:

```text
M2 preferred Primary candidate discovery
  -> canonical Primary recall adapter and bounded E1-R5 fallback
  -> shared I-4D Primary lifecycle eligibility
  -> runtime-private RelayCTX handoff
  -> E1-R4 grounded recall instructions
  -> Main LLM response generation
```

Primary MEM remains the sole ordinary memory and Retrieval authority until the
RT-1 hard-cutover receipt is finalized. Existing Subjective MEM revisions may be
logically `retrieval_eligible: true`, but no ordinary request-path reader consumes
them yet.

The current Primary adapter, lifecycle index, fallback discovery, grounding
handoff, smokes, and characterization tests remain read-only migration evidence.
They are not the target Subjective authority and must not silently become a
permanent compatibility layer.

## Target steady-state flow

The target steady-state path is:

```text
canonical Subjective MEM Markdown
  + exact finalized publication receipts
  + one logical current-state selector per memory
  + applicable durable lifecycle enforcement
  -> one versioned disposable retrieval projection generation
  -> exact current eligible Subjective revision selection
  -> bounded runtime-private evidence handoff
  -> existing grounded-recall response policy
  -> content-free durable usage event for the exact consumed selection
```

After hard cutover, no Primary MEM candidate, page, index, lifecycle overlay, or
fallback adapter may enter ordinary Retrieval. Primary assets may remain frozen
as historical, rollback, or migration evidence, but they are not a live reader,
writer, ranking source, or fallback authority.

## Fixed authority classes

### Canonical Subjective MEM authority

Canonical Markdown plus its exact finalized operation lineage owns:

- stable logical memory identity;
- immutable revision lineage;
- grounded content and subjective meaning;
- character and exact scope;
- memory kind and formation stage;
- canonical lifecycle-visible state;
- retrieval visibility;
- authorizing formation decision or lifecycle transition;
- exact current successor relationships.

A retrieval projection never repairs, rewrites, infers, or overrides these facts.

### Exact current-state authority

Exactly one `SubjectiveMemCurrentState` is permitted for each
`(character_id, memory_id)`. It must select the latest persisted revision and
bind the exact canonical page, block, revision, receipt, authorization, and
selector digests required by the accepted contracts.

A duplicate, missing, dangling, stale, non-latest, malformed, or conflicting
logical current selector fails closed. Physical file order, newest timestamp,
cache row order, or highest visible revision number is not a substitute for the
logical selector and finalized lineage.

### Rebuildable projection authority

The retrieval projection is a disposable derived index. It may contain bounded
derived fields for:

- exact current-revision lookup;
- canonical page and block digests;
- lifecycle and mutation eligibility;
- exact character and scope partitions;
- memory kind and formation stage facets;
- bounded text-search terms;
- optional vector or graph references;
- pinned and other contract-bounded ranking hints;
- derived usage counts and last-used time;
- explainable candidate and ranking features.

Projection persistence, WAL, replication, or fast lookup never makes it
canonical. Deleting the projection must not delete or change canonical memory,
selectors, receipts, tombstones, usage events, or lifecycle state.

### Durable operations authority

The existing durable operations authority owns non-rebuildable retrieval facts:

- exact hard-cutover intent and receipt;
- projection generation and rebuild-required state where needed;
- content-free durable retrieval-usage events;
- bounded idempotency results;
- recovery or operator-reconciliation state;
- old-reader and old-writer fence state during authority transfer.

It does not own memory prose, a second current selector, a second lifecycle state,
raw query text, prompt content, or a second editable ranking truth.

### Query and ranking policy

Query normalization, lexical matching, embeddings, vectors, and ranking are
candidate-generation or ordering mechanisms only. They cannot:

- make a non-current revision eligible;
- override lifecycle, mutation, scope, or retrieval visibility;
- infer authorization or disclosure permission;
- repair missing lineage;
- treat similarity as identity or merge authority;
- increase evidence confidence or prove truth;
- turn Primary/Secondary formation stage into an unconditional priority order.

Pinned state may remain a bounded ranking hint only after exact eligibility.
Grounded confidence, subjective conviction, salience, usage, and retrieval rank
must not collapse into one authority scalar.

## Exact ordinary-Retrieval eligibility

A Subjective MEM candidate may enter ordinary Retrieval only when every required
condition is true:

```text
one exact character authority
AND one exact admitted scope
AND one unambiguous logical current-state selector
AND exact latest persisted revision
AND canonical page and block digests match the selector
AND matching finalized publication receipt is resolvable
AND authorizing decision or lifecycle transition is resolvable
AND lifecycle_state in {active, pinned}
AND mutation_state == none
AND retrieval_eligible == true
AND retrieval_visible == true
AND no unresolved intent affects the page or memory
AND no recovery-required or corrupt state affects the revision
AND projection generation and source digests are current and supported
```

The following are always excluded:

- prior physical revisions;
- `held`, `hidden`, `superseded`, or `purged` revisions;
- prepared selectors or mutations;
- recovery-pending, recovery-required, or corrupt revisions;
- duplicate-current, missing-current, dangling-current, or stale selectors;
- unsupported page, block, renderer, projection, policy, or authority revisions;
- foreign page images or unverifiable finalized receipts;
- cross-character, cross-workspace, cross-participant, cross-relationship, or
  cross-scene scope candidates;
- memories whose required relationship or scene authority is missing or no
  longer admits the request audience;
- official product knowledge represented as personal Subjective MEM.

No fallback may admit an excluded revision.

## Projection generation and rebuild

One projection generation is built from a fixed source snapshot containing:

- supported canonical page manifests;
- parsed canonical memory blocks and exact digests;
- exact logical current selectors;
- matching finalized publication receipts;
- applicable lifecycle enforcement records;
- supported authority and schema revisions;
- durable content-free usage events needed for derived aggregates.

Each projected current row binds at least:

```text
character/workspace partition
memory_id
current revision
page_id and block_id
page, block, and revision digests
selector ID and digest
receipt ID and digest
authorization kind, ID, and digest
lifecycle and mutation state
retrieval eligibility and visibility
scope binding digest
projection generation ID
projection policy revision
```

A mixed generation cannot be served as one current view. A stale generation,
unsupported schema, missing row, duplicate row, source-digest mismatch, or
incomplete rebuild causes fail-closed ordinary Retrieval for the affected scope.
It must trigger a bounded rebuild-required state or operator-visible failure, not
a read from stale rows or Primary MEM.

A full rebuild from canonical Markdown, selectors, receipts, lifecycle records,
and usage events must produce an equivalent content-free projection manifest and
equivalent eligible candidate set for the same supported source snapshot.
Cache deletion and rebuild are required validation cases.

## Runtime-private retrieval handoff

RT-1 should preserve the accepted request-path separation by producing the same
kind of bounded runtime-private evidence handoff consumed by RelayCTX and E1-R4,
while changing the memory authority behind that handoff.

The private handoff may carry only the bounded selected Subjective content and
opaque lineage required for grounding and auditing. Public projections remain
content-free and may expose only bounded values such as:

```text
projection_generation_ready
candidate_count
selected_count
eligible_count
excluded_count_by_reason_class
usage_event_recorded
grounding_enabled
unsupported_detail_policy
runtime_private_evidence_omitted=true
```

Public diagnostics must not expose raw query text, memory prose, subjective
meaning, protected source content, prompt text, workspace paths, page paths,
private IDs, selector digests, receipt digests, authorization lineage, or usage
correlation material.

RT-1 does not rewrite the visible model response after generation. E1-R4 remains
the grounded-recall response-policy owner unless a later dedicated authority
changes that boundary.

## Durable usage events

A durable usage event is recorded only for the exact Subjective revision whose
bounded evidence was actually admitted to the backend-bound grounded-recall
context. Candidate discovery, ranking consideration, exclusion, shadow
comparison, or public projection alone is not a successful-use event.

The event is content-free and binds at least:

```text
character/workspace scope
memory_id and exact revision
selection/request correlation identity
bounded event kind
canonical selection or query-plan digest
retrieval policy revision
occurrence time
idempotency identity
```

It must not contain raw query text, prompt content, memory prose, private context,
source bodies, or unrestricted diagnostics.

The same request and exact selection must not create duplicate durable events.
The usage event is durably finalized before the selected memory handoff is sent
to the backend. If that finalization cannot complete, the Subjective evidence is
not admitted for that request and retrieval returns a bounded fail-closed outcome.
The ordinary conversation may continue without durable-memory context under its
existing request policy, but it must not fall back to Primary MEM, a stale cache,
or a cache-only counter. A usage-event failure never retroactively changes
eligibility or truth.

Usage events may influence only contract-bounded derived ranking features. They
never increase evidence confidence, authorize reinforcement or consolidation,
override scope or lifecycle, grant disclosure permission, or become memory
content.

## Shadow characterization boundary

Before authority transfer, the Primary path remains the only served ordinary
Retrieval path. A Subjective path may run in explicit shadow mode only when:

- its result is not injected into RelayCTX or the Main LLM context;
- it writes no ordinary usage event;
- it cannot repair or mutate canonical memory;
- it cannot become a fallback if Primary selects nothing;
- Primary cannot become a fallback for a Subjective shadow result;
- all comparison output is content-free and bounded;
- runtime-private content from the two paths is never combined.

The shadow comparison may measure:

- request classes for which each path attempted retrieval;
- candidate and selected counts;
- lifecycle, mutation, currentness, scope, and corruption exclusion classes;
- empty/non-empty outcome agreement;
- grounded-handoff shape and token-budget classes;
- deterministic replay and latency classes;
- projection rebuild equivalence;
- security and leakage outcomes.

Because Primary and Subjective logical identities need not correspond, equality
of raw IDs or memory prose is not a general convergence criterion. Characterized
behavior, eligibility safety, grounded response fixtures, and explicit migration
fixtures own the comparison. Shadow mode is temporary validation, not dual-read
authority.

## Existing Primary data

RT-1 does not automatically transform existing Primary MEM pages into Subjective
MEM.

Primary records generally lack the exact Shared Assessment, formation-time
receipt, Subjective decision, scope, and immutable lifecycle lineage required to
be valid Subjective revisions. Inventing that lineage during retrieval cutover is
prohibited.

At hard cutover:

- only independently valid, finalized Subjective MEM may enter ordinary
  Retrieval;
- old Primary content is fenced from ordinary readers and writers;
- old Primary assets may remain frozen for history, rollback evidence, export,
  or a later governed migration;
- a separate accepted migration authority is required to admit old Primary
  content into Subjective MEM;
- cutover must not claim historical Primary memories were migrated when they were
  merely archived or excluded.

A deployment that requires continued access to unported Primary memories must
remain before hard cutover until a migration authority is accepted and validated.

## One-authority hard cutover

Hard cutover is one governed authority transfer, not a gradual precedence rule.
The cutover transaction or controlled procedure must prove:

1. exact current main, configuration, authority, and projection revisions;
2. all required LC-1 eligibility operations are implemented and validated;
3. the Subjective projection generation is complete and rebuild-equivalent;
4. no unresolved Subjective mutation or recovery state affects served scopes;
5. shadow characterization and security validation satisfy the accepted gate;
6. the old Primary ordinary reader is fenced;
7. the old Primary formation/mutation writer paths are fenced for the transferred
   authority domain;
8. one Subjective ordinary reader is enabled;
9. the exact cutover receipt is durably finalized;
10. request-path probes prove only the Subjective reader can supply memory;
11. temporary shadow/adapter code and configuration are removed or disabled under
    an explicit immediate removal gate;
12. replaced Primary readers, writers, lifecycle overlays, and fallback paths are
    retired only after the exact post-transfer validation passes.

Permanent dual-read, dual-write, newest-wins, Primary-first, Subjective-first,
empty-result fallback, or conflict resolution between two live memory authorities
is prohibited.

A failed pre-transfer rehearsal leaves Primary as the sole ordinary authority. A
post-transfer rollback is a new governed authority transfer; it is not an
automatic fallback and cannot discard new Subjective usage or mutation history.

## Writer and mutation fencing

Retrieval remains read-only in the interactive path. RT-1 does not create memory
revisions, alter lifecycle, or invoke RelaySLP formation from an ordinary request.

The hard-cutover boundary must nevertheless fence the old Primary writer family
because a live writer whose output has no target ordinary reader would create an
ambiguous or stranded authority. The accepted deployment must establish one
formation/mutation authority domain:

```text
before cutover: Primary ordinary reader + existing Primary writer family
shadow phase:   Primary ordinary reader + Primary writer; Subjective read shadow only
after cutover:  Subjective ordinary reader + governed Subjective formation/ST-1/LC-1 writer family
```

A separate deployment decision owns when default-off Subjective formation and
commit gates become active. RT-1 cannot bypass those gates or treat dry-run output
as canonical memory.

## Ordered implementation slices

RT-1 is implemented in bounded order.

### RT-1A — contract and projection foundation

- define exact retrieval request, projection row/manifest, exclusion, selection,
  and content-free usage-event identities;
- implement pure validation and digest binding only;
- bind exact current selector, receipt, authorization, page/block, scope, and
  policy revisions;
- add focused valid/invalid fixtures;
- perform no filesystem scan, cache write, ordinary retrieval, usage write,
  Primary change, or cutover.

### RT-1B — projection builder and rebuild

- build one disposable projection generation from bounded canonical inputs;
- validate mixed-generation, stale, corrupt, unsupported, and incomplete states;
- prove deletion and full rebuild equivalence;
- remain default-off and unwired from ordinary Retrieval;
- add no Primary fallback or mutation authority.

### RT-1C — shadow adapter, grounding handoff, and usage ledger

- select exact current eligible Subjective revisions from one projection
  generation;
- produce bounded runtime-private RelayCTX/E1-R4 handoff in shadow mode first;
- add deterministic content-free characterization against the current Primary
  path without combining results;
- implement idempotent durable usage events for real admitted selections, but do
  not enable them from shadow-only comparison;
- keep Primary as the sole served authority.

### RT-1D — hard cutover and retirement

- satisfy the explicit deployment and characterization gate;
- fence old Primary readers and writers;
- enable one Subjective ordinary reader;
- finalize one cutover receipt;
- prove request-path one-authority behavior;
- remove temporary shadow/adapter surfaces;
- retire replaced Primary reader/writer/lifecycle/fallback code only after exact
  post-transfer validation.

Each slice remains a separate atomic PR or explicitly coordinated atomic set. A
later slice cannot claim completion of an earlier missing authority.

## First implementation budget

The next authorized implementation is RT-1A only.

Expected bounded paths are:

```text
relaylm/subjective_mem_retrieval.py                 new pure contract owner
tests/test_subjective_mem_retrieval_contract.py     focused fixtures
docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md
```

A small existing smoke registration path may be added only if P1 proves it is
required. RT-1A must not modify:

- `relaylm/relaymem_primary_recall.py`;
- `relaylm/relaymem_retrieval.py`;
- request routing or RelayCTX injection;
- E1-R4 grounding behavior;
- Subjective lifecycle runtimes or publication engine;
- config, API, UI, workflow YAML, scheduler, worker, queue, or Primary writer
  modules;
- project status or cutover state.

Review triggers return the work to P1:

- materially more than three ordinary paths;
- roughly 200 added lines to an existing file;
- a new file above roughly 700 lines;
- a function above roughly 80 lines;
- production logic duplicated in tests;
- an implementation-specific cache schema introduced before RT-1B;
- any ordinary request-path wiring, Primary fallback, dual authority, or writer
  change;
- temporary patch scripts, generated repair files, Base64 fragments, partial
  assembly, or compatibility aliases.

## Validation matrix

The full RT-1 series must eventually prove:

- exact latest-current active and pinned inclusion;
- hidden, held, superseded, purged, prepared, recovery-required, corrupt, and
  prior-revision exclusion;
- missing, duplicate, dangling, stale, and conflicting selector exclusion;
- page/block/selector/receipt/authorization/scope/schema digest mismatch refusal;
- unresolved-intent and unverifiable-receipt refusal;
- mixed projection generation refusal;
- projection deletion and deterministic full rebuild equivalence;
- bounded candidate selection and token-budget enforcement;
- no scope or character leakage;
- no public content, path, query, prompt, or private-identifier leakage;
- exact runtime-private E1-R4 grounding handoff;
- deterministic replay and idempotent usage-event finalization;
- no usage event for shadow, excluded, or merely considered candidates;
- usage-event persistence across projection rebuild;
- Primary-only served behavior before cutover;
- Subjective-only served behavior after cutover;
- no empty-result fallback to the other authority;
- old reader/writer fencing and temporary-adapter removal;
- post-transfer process restart and fresh-request behavior;
- unsupported platform, schema, and configuration refusal;
- complete current-main-relative diff and temporary-artifact review.

## Non-goals

RT-1 does not authorize:

- automatic migration or semantic conversion of Primary MEM;
- formation, correction, lifecycle mutation, consolidation, or purge from the
  ordinary retrieval path;
- LLM adjudication inside ordinary retrieval;
- multi-memory merge or duplicate collapse;
- raw query or memory storage in usage events;
- a canonical SQLite/vector/graph store;
- permanent shadow, dual-read, dual-write, precedence, or fallback behavior;
- default-on deployment;
- backup/restore completion;
- multi-host publication or writer coordination;
- API/UI management features;
- post-hoc visible-response rewriting;
- deletion of old Primary assets before a separate retirement or migration
  authority proves they are no longer needed.
