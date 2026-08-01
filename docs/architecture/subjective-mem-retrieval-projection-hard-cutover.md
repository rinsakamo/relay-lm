---
relaylm_doc_type: subsystem_architecture
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
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - Subjective MEM retrieval and projection implementers
  - RelayCTX and grounded-recall integration reviewers
  - Primary-to-Subjective cutover and retirement reviewers
relaylm_authority_level: subsystem
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

This document defines the accepted target architecture for RT-1. RT-1A, RT-1B,
and RT-1C are implemented within it; RT-1D remains the unimplemented target.

RT-1 replaces the current Primary MEM ordinary-recall authority with one
Subjective MEM ordinary-Retrieval authority. It does so through a disposable
projection, exact current-revision eligibility, content-free durable usage
events, shadow-only characterization, one explicit authority transfer, and
retirement of the replaced Primary readers and writers.

This architecture does not claim the RT-1 series or its hard cutover is
implemented. It does not enable ordinary Subjective MEM Retrieval, change feature
defaults, migrate user data, or retire Primary MEM by itself.

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

### RT-1B projection-builder boundary

The implemented RT-1B builder owns snapshot-to-projection derivation and
disposable projection persistence only. Acquiring the snapshot — enumerating an
evidence space or workspace, locking, and loading canonical pages, selectors,
receipts, and authorization records — stays with those authorities' existing
owners, so the builder introduces no second enumeration, selector, receipt,
lifecycle, or canonical representation. The snapshot is therefore a fixed value
carrying canonical page images rather than workspace or page paths, and the
builder resolves no filesystem location of its own.

Committed receipt and authorization exactness is not re-implemented by the
builder. The shared committed-authority owner exposes its storage-neutral
validation stages, the Evidence-store-bound loader sequences the same stages,
and the builder calls them with the fixed source material, so exactly one
committed-authority evaluator exists.

Four consequences follow for the eligibility conditions above:

- build time binds to the fixed snapshot, never to an uncontrolled wall clock,
  so the same snapshot rebuilds to the same manifest identity;
- a published canonical page digest is a point-in-time fact that changes
  whenever a later memory is appended to the same page, so the selector's own
  recorded page image is checked against the receipt's post-image — both written
  by the same commit — while the projected page digest is the exact image the
  row was derived from;
- a duplicate or otherwise conflicting logical current selector refuses the
  build for that snapshot instead of projecting an ambiguous current row;
- only a complete authority-bound current selector is a supported source. A
  legacy unbound selector cannot name its canonical page, block, receipt, and
  authorization, so it is refused rather than projected as exact, and it can
  never become ordinarily eligible.

The projection bundle is one replace-only local file holding exactly one
generation. It is not durable operations authority, and deleting it changes no
canonical Markdown, selector, receipt, lifecycle record, tombstone, or
transition.

Its serialized digests are ordinary recomputable hashes and authenticate
nothing: an internally consistent altered bundle can always be re-digested.
A persisted projection therefore becomes trusted only by rebuilding the expected
projection from the exact fixed source snapshot and requiring the decoded
manifest and ordered row population to equal that rebuild. There is no
source-less trusted read, no repair-on-read, and no stale-generation fallback,
and persistence accepts only a projection equal to that rebuild.

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

## Authorized implementation budget

### Accepted position

RT-1A contract and projection foundation is complete. RT-1B projection builder
and deterministic rebuild is complete. RT-1C shadow adapter, grounding handoff,
and usage ledger is implemented in PR #784 within the budget this section
authorizes, and remains default-off, explicit shadow-only, and unwired from
ordinary Retrieval.

RT-1D hard cutover, Primary retirement, and authority transfer are
architecture-authorized and are not started. The next ordered Lane C work is
the S1-S3 structural prerequisite sequence defined below.

This section authorizes an implementation budget and records which slices have
since landed within it. It claims no ordinary served Subjective MEM Retrieval,
no authority cutover, and no completed RT-1 series; `../PROJECT_STATUS.md`
remains the only current-status authority.

Four accepted boundaries survive RT-1C unchanged:

- Primary MEM remains the sole served ordinary memory and Retrieval authority.
- RT-1B remains disposable, default-off, and unwired from ordinary Retrieval.
- ST-1 revision-1 `create` still produces a legacy unbound current selector that
  RT-1B rejects fail-closed, so those revision-1 memories stay outside every
  RT-1C selection until a later accepted slice publishes authority-bound
  selectors.
- E1-R4 remains the grounded-recall response-policy owner.

### RT-1C bounded scope

#### 1. Exact projection selection

- consume exactly one verified and supported projection generation;
- select only exact-current, exact-scope, eligible Subjective revisions under the
  accepted eligibility conjunction above;
- enforce the request's candidate limit and token budget;
- fail closed on generation, manifest, row, request, scope, policy, digest,
  lifecycle, mutation, currentness, or authority disagreement;
- never broaden the query, relax a scope partition, or bypass lifecycle
  eligibility to fill an empty result.

#### 2. Shadow-only adapter

- RT-1C runs the Subjective path in explicit shadow mode only, and RT-1D alone
  may serve it;
- never inject shadow evidence into the served RelayCTX or Main-LLM request;
- never combine Primary and Subjective runtime-private content;
- never use either path as a fallback for the other, including on an empty
  result;
- Primary remains the only served ordinary path for the whole slice.

#### 3. Runtime-private grounding handoff

- define the bounded runtime-private handoff required by the existing
  RelayCTX/E1-R4 grounding policy, carrying only selected Subjective content and
  opaque lineage;
- keep E1-R4 as the grounding-policy owner and change no grounding behavior;
- do not rewrite the visible response;
- expose no private handoff content through public diagnostics;
- fail closed rather than admitting a mismatched, oversized, or incomplete
  handoff;
- take the selected content only from the exact canonical page binding described
  under the P1 amendment below, never from caller-attested prose.

#### 4. Deterministic characterization

- compare Primary served behavior with Subjective shadow behavior without
  combining their results;
- keep comparison output content-free and bounded;
- never compare raw memory prose and never assume Primary and Subjective logical
  identities correspond;
- cover attempt class, candidate/selected counts, exclusion-reason classes,
  empty/non-empty agreement, handoff-shape class, token-budget class,
  deterministic replay, latency class, projection rebuild equivalence, and
  leakage outcomes.

#### 5. Durable usage ledger

- persist content-free events only for exact Subjective selections actually
  admitted to a backend-bound grounded context;
- write no event for shadow comparison, candidate consideration, exclusion,
  ranking consideration, or public projection;
- finalize the event durably before releasing the corresponding private evidence
  handoff;
- on finalization failure, admit no Subjective evidence and return a bounded
  fail-closed result with no fallback;
- enforce deterministic idempotency for the same request and exact selected row;
- preserve usage events across projection deletion and deterministic rebuild;
- never make usage an eligibility, truth, lifecycle, disclosure, formation,
  reinforcement, or consolidation authority.

### RT-1C P1 amendment

This section records one accepted P1 amendment to the RT-1C budget above. It
changed authorization only. At the time of that review RT-1C was authorized and
not yet implemented on `main`; the implementation landed later in PR #784 within
this amended budget. Primary MEM remains the sole served ordinary authority,
RT-1D is architecture-authorized and not started, and no ordinary request-path wiring
is authorized.

#### Accepted P1 characterization split

The original budget placed temporary shadow characterization inside the
selection owner and required a return to P1 if it could not stay bounded there.
Independent review of a paused RT-1C implementation confirmed that trigger: once
the integrity validation RT-1C requires was present, the co-located selection and
characterization owner crossed the roughly-700-line structural review trigger.
That is the exact architecture condition this document already named, so the
split is now decided explicitly rather than left to the implementation.

One third production responsibility file is therefore authorized:

```text
relaylm/subjective_mem_retrieval_characterization.py       temporary shadow
                                                           characterization owner
tests/test_subjective_mem_retrieval_characterization.py    its focused test owner
```

The characterization owner:

- owns only temporary, content-free Primary-vs-Subjective shadow
  characterization and the strict public-projection validation that
  characterization needs;
- owns no selection, private evidence, canonical parsing, durability, admission,
  E1-R4 policy, Primary reader, ordinary route, fallback, or authority;
- may import only storage-neutral public characterization values from the
  selection owner plus read-only content-free Primary served-path metrics;
- is temporary and carries the same RT-1D removal/disable gate as every other
  shadow-only surface;
- is never imported by the selection owner or by the durable usage ledger, so
  the dependency stays one-way.

No generic adapter framework, registry, plugin, API, configuration, or workflow
surface is authorized by this split.

#### Canonical-page-bound private evidence

Review of the same paused implementation demonstrated one exact authority gap.
A private evidence item built from caller-supplied grounded prose plus a
caller-supplied matching `grounded_content_digest` is only self-consistent. Self
consistency between prose and its own supplied digest is not canonical authority
and must not authorize a private handoff. That design is rejected.

The authorized binding is a pure read over bounded values the existing canonical
owner already supplies:

1. the canonical owner supplies bounded canonical page bytes as an in-memory
   value; RT-1C resolves no path and reads no file;
2. selection parses them with the existing
   `relaylm.subjective_mem_markdown.parse_subjective_mem_page_bytes` owner, and
   introduces no second canonical parser;
3. selection verifies, for each selected row, that:
   - the supplied value is `bytes` and within the existing canonical page bounds;
   - the parsed `page_id` and `character_id` match the exact projection row and
     request;
   - the parsed page digest equals `row.canonical_page_digest`;
   - exactly one parsed block matches `row.block_id`, `memory_id`, and
     `memory_revision`;
   - that block's `block_digest` equals `row.block_digest`;
   - that block's `revision_digest` equals `row.revision_digest`;
   - the parsed revision's character, memory kind, formation stage, lifecycle
     state, retrieval visibility, scope binding, and authorization identity agree
     with the exact projection row and the admitted request scope;
   - the parsed `grounded_content_digest` is internally valid under the existing
     Subjective MEM and canonical Markdown validators;
4. `grounded_content` and `grounded_content_digest` are extracted only from that
   exact parsed canonical revision, and the private item is constructed only from
   those parsed values;
5. duplicate, missing, extra, foreign, stale, conflicting, wrong-page,
   wrong-block, wrong-revision, wrong-digest, unsupported-schema, malformed, and
   oversized canonical page bindings all fail closed;
6. one canonical page may serve several selected rows only when each row
   independently resolves to exactly one matching block; a duplicate page
   submission or an ambiguous row-to-page binding fails closed;
7. no canonical page bytes, raw prose, subjective meaning, path, or private
   lineage enters a public projection, characterization output, usage outcome, or
   durable usage record;
8. selection remains a pure function over already supplied bounded values, with
   no filesystem access, workspace scan, path resolution, selector/receipt/
   authorization reconstruction, projection repair, or canonical mutation;
9. the durable ledger revalidates the immutable prepared private item against the
   exact projection row and the canonical binding identity selection established.
   It must not accept a reconstructed caller-authored private item as equivalent
   merely because its prose and digest agree with each other.

This closes the reviewed residual authority gap without adding a free-standing
`grounded_content_digest` to the RT-1A projection row. No RT-1A projection-row
digest addition is required, because the row already binds the canonical page,
block, and revision digests from which the canonical grounded content is
deterministically recovered.

#### Revised three-owner structural budget

```text
relaylm/subjective_mem_retrieval_selection.py          below roughly 700 lines
relaylm/subjective_mem_retrieval_characterization.py   below roughly 320 lines
relaylm/subjective_mem_retrieval_usage_ledger.py       below roughly 700 lines
each function                                          at or below roughly 80 lines
```

The characterization owner's budget was amended from below roughly 300 lines to
below roughly 320 lines by the second P1 budget-review disposition recorded
immediately below. No production behaviour may be duplicated in tests.

#### Second P1 characterization budget-review disposition

Independent review examined the responsibility-preserving implementation of the
characterization owner after genuine consolidation had already been applied. In
that reviewed implementation `relaylm/subjective_mem_retrieval_characterization.py`
is 309 lines.

Those 309 lines retain both strict fail-closed admission validation of the public
selection projection and deterministic content-free Primary-vs-Subjective
comparison, including the exact state relationships RT-1C requires. Admission
validation and comparison are one coherent temporary shadow-characterization
responsibility, not two separable production responsibilities: the comparison is
only safe because the projection it consumes was admitted by exactly those
checks, and no other consumer exists for either half.

Two alternatives were considered and are explicitly rejected:

- a fourth production owner is rejected, because it would split one
  responsibility across two files and add dependency surface for no authority
  gain;
- deleting security or state checks, or line-golfing the code, to reach the
  former roughly-300-line target is rejected, because the reviewed size is
  carried by required exactness rules rather than by prose or duplication.

The characterization structural budget is therefore amended from below roughly
300 lines to below roughly 320 lines. This is a bounded, reviewed exception for
this exact owner. It is not a general structural-budget relaxation, and it
changes no other owner's budget, the roughly-80-line function budget, or any
authority boundary.

Exactly three production owners remain authorized:

```text
relaylm/subjective_mem_retrieval_selection.py
relaylm/subjective_mem_retrieval_characterization.py
relaylm/subjective_mem_retrieval_usage_ledger.py
```

Strict validation and deterministic comparison remain in the same temporary
characterization owner, which keeps its RT-1D removal/disable gate and its
one-way dependency direction unchanged.

This disposition adjusted an implementation budget only, and RT-1C was not yet
implemented on `main` when it was recorded; the implementation landed later in
PR #784 within this budget. Primary MEM remains the sole served ordinary memory
and Retrieval authority, RT-1C remains default-off, shadow-only, and unwired from
the ordinary request path, no ordinary request-path wiring is authorized, and
RT-1D is architecture-authorized and not started.

#### Revised P1 return triggers

Return to P1 rather than continuing if:

- canonical parsing cannot reuse the existing Markdown owner;
- the RT-1A row, the RT-1B projection builder or store, the canonical Markdown
  owner, E1-R4, Primary, or ordinary request routing would require modification;
- more than these three new production files are required;
- the characterization owner reaches 320 lines;
- the characterization owner gains another responsibility, consumes private
  content, or becomes a general validation framework;
- characterization starts consuming private content;
- selection starts performing I/O;
- the durable ledger becomes a canonical content authority;
- a new configuration, API, UI, workflow, scheduler, worker, queue, daemon, or
  polling surface is proposed.

### RT-1C invariants

- exactly one served ordinary memory authority: Primary MEM;
- exactly one Subjective projection generation per selection;
- exactly one canonical current selector authority;
- no projection repair and no canonical-memory mutation;
- no Primary fallback from Subjective results;
- no Subjective fallback from Primary results;
- no dual-read serving;
- no ordinary route injection from shadow mode;
- no hidden, held, superseded, purged, prepared, recovery-required, corrupt,
  prior, dangling, stale, conflicting, cross-character, or cross-scope candidate
  admission;
- no public raw query, memory prose, subjective meaning, protected evidence,
  prompt content, private path, unrestricted identifier, selector digest,
  receipt digest, authorization lineage, or usage-correlation leakage;
- durable usage finalization precedes private evidence admission;
- failed usage finalization produces no handoff and no fallback;
- deterministic replay for identical supported inputs;
- all validation and CI remain repository-content read-only.

### Expected implementation paths

The bounded path budget the RT-1C implementation landed within is:

```text
relaylm/subjective_mem_retrieval_selection.py          exact selection, canonical-page
                                                       binding, and runtime-private handoff owner
relaylm/subjective_mem_retrieval_characterization.py   temporary shadow characterization owner
relaylm/subjective_mem_retrieval_usage_ledger.py       durable content-free usage-event owner
tests/test_subjective_mem_retrieval_selection.py       focused selection, canonical-binding,
                                                       and handoff fixtures
tests/test_subjective_mem_retrieval_characterization.py focused content-free comparison and
                                                       projection-validation fixtures
tests/test_subjective_mem_retrieval_usage_ledger.py    focused durable idempotency, ordering,
                                                       and finalization-failure fixtures
docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md
```

Selection and durable usage are separate owners with a one-way dependency:
selection is a pure, rebuildable read over one projection generation, while the
usage ledger is durable operations authority that outlives the disposable
projection. Merging them would put a disposable derived read and a durable
non-rebuildable write in one file with two unrelated reasons to change.

Shadow characterization is the third owner. It was originally co-located with
selection because it is a content-free comparison over two already-bounded
result projections rather than a third semantic authority. The accepted P1
amendment above records why that co-location no longer holds and authorizes the
split explicitly; it remains a temporary surface under the RT-1D removal gate,
not a new authority.

Two conditional paths are permitted only on demonstrated need:

```text
relaylm/subjective_mem_retrieval.py                 only when an exact missing RT-1C
tests/test_subjective_mem_retrieval_contract.py     contract identity is demonstrated
scripts/relaylm_ci_consolidated_smoke.py            at most one registration entry, only when
                                                    focused pytest discovery cannot validate
                                                    the request-path boundary
```

The storage-neutral contract already owns the retrieval request, projection row
and manifest, closed exclusion vocabulary, bounded selection, and content-free
usage-event identities, including the usage idempotency slot and result
identity. P1 must therefore demonstrate the exact absent identity — for example
a bounded runtime-private handoff shape or a content-free characterization
projection — before touching it, and must add the matching focused fixtures in
the same slice. A milestone-only or wrapper-only name is not an acceptable
substitute for any responsibility name above.

The canonical grounded content is not such an absent identity. The accepted P1
amendment binds it through the existing canonical page, block, and revision
digests the row already carries, so no RT-1A projection-row digest addition is
required or authorized for it.

### Not authorized for modification

RT-1C must not modify:

- `relaylm/relaymem_primary_recall.py`;
- `relaylm/relaymem_retrieval.py`;
- ordinary request routing;
- ordinary RelayCTX injection;
- E1-R4 grounding behavior;
- Primary MEM lifecycle, reader, writer, fallback, or precedence;
- Subjective lifecycle runtimes;
- canonical publication;
- API, UI, configuration, workflow YAML, scheduler, worker, queue, daemon, or
  background polling surfaces;
- `docs/PROJECT_STATUS.md`;
- `docs/architecture/project_execution_plan.md`.

If P1 inspection proves that one of the first four read-only integration
surfaces must later receive a minimal RT-1C hook, record it as a review-trigger
exception that returns the work to P1 for an explicit authority decision. It is
never silently authorized inside the implementation slice.

### Required negative cases

Canonical binding:

- arbitrary prose plus a matching caller-supplied digest is refused, or made
  impossible by the accepted API shape;
- canonical page digest mismatch;
- wrong page ID or wrong character;
- missing, duplicate, or extra canonical page binding;
- missing, duplicate, or wrong block;
- block digest mismatch;
- revision digest mismatch;
- memory ID or memory revision mismatch;
- memory kind, formation stage, lifecycle, visibility, scope, or authorization
  disagreement between the parsed revision and the exact row;
- malformed, noncanonical, unsupported-schema, or oversized page bytes;
- one canonical page carrying several memories resolves only the exact selected
  block;
- deterministic extraction under input reordering;
- no canonical page bytes, prose, or path leakage.

Characterization split:

- only exact content-free public projection values are accepted;
- no private handoff and no canonical page input is accepted;
- no raw prose or free-text reason injection is accepted or copied onward;
- deterministic replay over a bounded class vocabulary;
- Primary remains the only served ordinary authority;
- an explicit RT-1D removal gate exists;
- no reverse import into the selection owner or the durable ledger.

Durable ledger:

- prepared and admitted handoffs are separate types;
- private items are immutable;
- the exact event and result pair state matrix is enforced;
- finalization precedes admission;
- no event for a shadow, empty, or considered-only result;
- no content, path, or canonical page bytes in durable usage records;
- exact duplicate finalization;
- partial or divergent pair failure;
- persistence across projection deletion and deterministic rebuild.

Selection and projection:

- unsupported or mixed projection generation;
- request/manifest generation mismatch;
- stale, missing, duplicate, dangling, or conflicting projection row or current
  selector;
- wrong character, workspace, participant, relationship, scene, or scope;
- hidden, held, superseded, purged, prepared, recovery-required, corrupt, and
  prior revisions;
- unresolved intent;
- receipt, authorization, page, block, selector, scope, schema, renderer,
  policy, or platform mismatch;
- candidate-limit and token-budget overflow;
- shadow result attempted as ordinary served evidence;
- Primary/Subjective content combination;
- cross-authority empty-result fallback;
- usage event attempted for a shadow, excluded, or merely considered candidate;
- duplicate usage event for the same exact request and selection;
- usage finalization failure followed by a handoff;
- public diagnostics containing content, paths, raw query, or private IDs;
- non-deterministic replay for identical supported inputs.

### Compatibility owner and removal gate

- Primary MEM and its current canonical recall adapter remain the served-path
  and characterization-source owners until RT-1D.
- E1-R4 remains the grounding-policy owner.
- The RT-1C shadow adapter owns only temporary Subjective characterization and
  private handoff construction.
- `relaylm/subjective_mem_retrieval_characterization.py` is a temporary
  shadow-only owner. It and its focused tests are removed or disabled by the
  RT-1D one-authority transfer, after exact post-transfer validation.
- The durable usage ledger is durable operations authority; it is not deleted
  with the disposable projection and survives its rebuild.
- The temporary Primary-vs-Subjective characterization surface and every
  shadow-only wiring point must be removed or disabled as part of the RT-1D
  one-authority transfer, after exact post-transfer validation.
- RT-1C must not introduce a permanent compatibility layer, fallback,
  precedence rule, or second semantic authority.

### Structural-growth review triggers

These return the future implementation to P1:

- more than the documented bounded path set;
- more than the three new production responsibility files the accepted P1
  amendment authorizes;
- roughly more than 200 added lines in one existing file;
- a new file growing beyond roughly 700 lines;
- a function growing beyond roughly 80 lines;
- production behavior duplicated in tests;
- a wrapper or adapter without an accepted current consumer and removal gate;
- a new configuration, API, UI, registry, workflow, scheduler, worker, queue,
  daemon, or polling surface;
- ordinary request-path wiring;
- a Primary fallback, precedence, reader, writer, lifecycle, or authority
  change;
- any RT-1D hard-cutover behavior;
- temporary patch scripts, Base64 fragments, partial assembly, placeholder or
  noop files, generated repair files, or repository construction helpers.

A trigger is not an automatic rejection. P1 must either reduce or split the
design along authority boundaries, or record why the current structure is
simpler and safer.

### RT-1C validation matrix

The RT-1C implementation must prove:

- exact canonical-page binding of every selected private item, including page,
  block, and revision digest agreement;
- refusal of caller-attested prose and of a caller-supplied matching digest;
- reuse of the existing canonical Markdown parser rather than a second parser;
- content-free deterministic characterization in its own owner, with no private
  handoff, canonical page bytes, or free-text reason accepted;
- prepared and admitted handoff type separation with finalization before
  admission;
- exact active and pinned current-revision inclusion;
- exclusion of every prohibited lifecycle, mutation, currentness, and scope case;
- one-generation and exact-manifest enforcement;
- deterministic bounded selection and token-budget enforcement;
- content-free deterministic characterization;
- no runtime-private content combination between the two paths;
- private grounding-handoff shape validation;
- no public query, content, path, or private-identifier leakage;
- usage-event exact identity and idempotency;
- no usage event for shadow, excluded, or considered-only rows;
- durable event finalization before handoff;
- finalization failure means no Subjective handoff;
- usage ledger survives projection deletion and deterministic rebuild;
- Primary remains the sole served ordinary authority;
- no ordinary request-path behavior change;
- no cross-authority empty-result fallback;
- unsupported schema, platform, and policy refusal;
- complete main-relative diff and temporary-artifact review.

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

## RT-1D architecture authorization and implementation budget

### Authorization boundary and owners

RT-1D is architecture-authorized, not started, and is the next ordered Lane C implementation slice. Its single atomic boundary transfers ordinary served memory authority from Primary to Subjective, records that transfer durably, and retires replaced surfaces only after exact post-transfer validation. One logical Lane C writer owns the transaction and no interval may contain two semantic authorities.

`relaylm/relaymem_retrieval.py` owns the ordinary reader entry point; `relaylm/relaymem_primary_recall.py` owns Primary candidate discovery, bounded fallback, and the Primary runtime artifact; `relaylm/subjective_mem_retrieval_cutover.py` is the one dedicated RT-1D cutover domain owner; and `relaylm/relaymem_grounded_recall_response.py` remains the E1-R4 grounding-policy owner. The governed Subjective formation/writer family remains `relaylm/subjective_mem_commit_runtime.py` plus the existing LC-1 runtime owners (`subjective_mem_lifecycle_runtime.py`, `subjective_mem_forget_runtime.py`, `subjective_mem_pin_runtime.py`, `subjective_mem_restore_runtime.py`, and `subjective_mem_consolidate_runtime.py`). The current Primary reader, candidate fallback, `primary_recall_runtime` lifecycle projection, Primary page/index/log writer family, the two compatibility no-op runtime modules, and RT-1C shadow characterizer are temporary pre-cutover compatibility surfaces, not permanent authorities.

#### Dedicated RT-1D cutover domain owner

One dedicated domain owner, `relaylm/subjective_mem_retrieval_cutover.py`, owns the whole semantic RT-1D authority transfer. Its function-oriented name states its responsibility, not a milestone.

That owner owns:

- the content-free cutover intent schema;
- the reader-fence schema and its transition;
- the writer-fence schema and its transition;
- the prepared, non-serving Subjective transition state;
- the finalized cutover receipt schema;
- exact predecessor binding of every durable record;
- configuration, authority, projection-generation, and scope binding;
- deterministic idempotency identity;
- transition validation;
- restart state reconstruction from the durable chain;
- caller/operator-invoked forward recovery;
- one bounded content-free public outcome;
- refusal of divergent, incomplete, stale, or mixed durable state.

That owner does not own:

- generic filesystem layout;
- generic locks;
- generic transaction journaling;
- canonical Subjective content;
- current selector evaluation;
- lifecycle evaluation;
- projection derivation;
- ordinary ranking;
- E1-R4 grounding policy;
- Primary or Subjective memory prose.

#### EvidenceRecordStore is a reused generic dependency

`relaylm/evidence_store.py` is generic persistence infrastructure, not the RT-1D semantic authority. `EvidenceRecordStore` already owns per-evidence-space locking, atomic record/log commit, create-or-verify identity, prepared-transaction replay, and bounded persistence mechanics, and it imports no domain module. RT-1C already follows this direction in `relaylm/subjective_mem_retrieval_usage_ledger.py`, and LC-1 follows it in its lifecycle runtime/engine owners. RT-1D preserves that same dependency direction:

```text
ordinary route / cutover orchestration
  -> subjective_mem_retrieval_cutover domain owner
       -> EvidenceRecordStore generic persistence
```

The generic store must never import the cutover owner.

The cutover owner reuses `EvidenceRecordStore` only for:

- one evidence-space lock;
- atomic record/log transactions;
- create-or-verify semantics;
- prepared-transaction recovery;
- generic bounded persistence.

Therefore RT-1D introduces no second lock, no second durable root, no second transaction journal, and no second generic recovery mechanism, and adds no RT-1D policy or state-machine logic to `relaylm/evidence_store.py`.

Modifying `relaylm/evidence_store.py` is allowed only through a documented P1 return that proves, from exact evidence, a missing generic persistence capability that is not RT-1D-specific. This authorization does not pre-authorize such a change.

### Prerequisites and exact execution order

An attempt requires RT-1A, RT-1B, RT-1C, exact-current-main authority, and an accepted deployment-specific readiness and characterization record. The order is fixed: (1) read-only pre-cutover validation and readiness proof; (2) durable intent, then old-reader fence, then old-writer fence; (3) exact one-authority transfer; (4) exact Subjective route preparation in a non-serving prepared state; (5) durable cutover-receipt finalization, which alone authorizes ordinary Subjective serving; (6) exact post-transfer request-path validation; (7) temporary shadow/adapter disablement or removal; and (8) retirement only after every removal gate passes. No mixed, ambiguous, dual-live, or precedence interval is accepted.

### Required semantic invariants

- Every accepted stable state has exactly one ordinary served memory/Retrieval authority: Primary before cutover and Subjective after the finalized receipt.
- Dual-read serving, fusion, precedence, and fallback are forbidden. Subjective cannot serve before receipt finalization; Primary cannot serve afterward, including when Subjective is empty, stale, corrupt, unavailable, or unsupported.
- Every Subjective item binds the exact current revision, selector, receipt, authorization, lifecycle, visibility, scope, canonical page and block, and projection generation. Legacy unbound selectors never enter ordinary Retrieval.
- Usage finalization is durable before private evidence admission. E1-R4 remains grounding-policy authority; no response rewriting occurs.
- Similarity, ranking, or embedding output is never eligibility, identity, authorization, truth, lifecycle, or disclosure authority.
- No Primary writer remains live after its ordinary reader retires. Subjective formation/commit/lifecycle gates remain governed and default-off unless separate accepted deployment authority changes them.
- This slice migrates no Primary prose. Stale, malformed, ambiguous, tampered, mixed-generation, cross-scope, recovery-required, or authority-inexact state fails closed.

### Durable cutover state and forward recovery

The durable state machine is:

```text
primary_live
  -> intent_recorded
  -> reader_fenced
  -> writer_fenced
  -> subjective_prepared
  -> receipt_finalized
  -> validated
  -> retired
```

Each record binds its predecessor, exact configuration and authority revisions, projection generation, scope, and idempotency identity. Before `intent_recorded` is the last safe rollback point. From durable intent or either fence onward, recovery is caller/operator-invoked and forward-only; operational rollback is a separate governed authority transfer and this repository authorization is not deployment approval.

No state authorizes ordinary Subjective serving before the finalized receipt is durable:

- `subjective_prepared` constructs or validates the exact Subjective route inputs but releases no ordinary evidence and serves no ordinary request.
- Ordinary Subjective serving is authorized only by the exact finalized receipt.
- After `receipt_finalized`, only Subjective may serve.

Crash behavior at every transition is therefore:

- A crash before fencing leaves Primary solely live after exact proof that no intent/fence advanced.
- A crash after reader fence but before writer fence resumes by fencing the writer; it does not reopen the Primary reader.
- A crash after writer fence but before Subjective preparation resumes preparation from the exact fenced state; neither reader serves meanwhile.
- A crash in `subjective_prepared` resumes forward finalization with both ordinary authorities non-serving.
- A crash after finalization but before retirement serves only Subjective and resumes validation/removal from the finalized receipt.

Restart reconstructs the exact state from the durable chain and revalidates all bound revisions before the next transition. Silent reset, repair-on-read, automatic retry after a head/state mismatch, and fallback to Primary are prohibited.

### Characterization and deployment gate

Before intent, an accepted operator/deployment authority must record exact build, configuration, scope, Primary and Subjective policy/schema/platform/renderer revisions, projection generation, rebuild result, and deterministic replay. The read-only Primary-versus-Subjective comparison is content-free and bounded to attempt/outcome classes, counts, exclusions, empty/non-empty class, handoff and token-budget classes, latency class, and leakage result. It neither compares raw content nor asserts identity equivalence. Acceptance requires deterministic replay, exact projection deletion/rebuild equivalence, all required eligibility and lifecycle exclusions, no private/public leakage, and an explicit disposition for every mismatch class. Architecture-gate success alone does not approve production deployment, default-on policy, or formation gates.

### P1 authority-carriage return and amended API boundary

Read-only inspection after the original authorization proved that its path/API
budget was incomplete.  The managed request caller passes configuration, route,
and the Primary root to the ordinary retrieval stage, but no explicit cutover
store or evidence-space identity, Subjective projection location, canonical
source authority, build/configuration identity, deployment/readiness authority,
or finalized-receipt identity.  The projection store requires an explicit safe
absolute root and exact source-bound validation; the projection builder consumes
a fixed source and deliberately owns neither filesystem enumeration nor source
loading.  The usage ledger already has the required dependency shape: an
explicit `EvidenceRecordStore` and evidence-space identity, with durable
finalization before admission.

The writer graph also exceeds the old four-facade budget.  The Primary pipeline
has per-call checkpoints before source consumption, page writing, and index/log
reconciliation, but aliases private writer implementations.  SLP lease/claim
fencing is not durable cutover fencing, and neither queued-runner nor worker
requests carry RT-1D authority.  Correct and Forget are independent live writer
entries whose apply and recovery paths do not receive it.  The Primary mutation
coordinator remains a per-memory Correct/Forget coordinator, not a global
cutover owner.

The rejected alternatives are a marker in the Primary root (a second durable
mechanism), a process-local flag (not restart-safe), implicit root derivation
(hidden precedence), and facade-only fencing while a private/direct apply path
remains.  Runtime implementation remains not started.  Primary remains the sole
current ordinary served memory and Retrieval authority.

#### Immutable runtime-private cutover binding

The cutover owner must expose one immutable runtime-private
`SubjectiveMemRetrievalCutoverBinding`, reconstructed from and revalidated
against the exact durable chain.  It carries content-free identities for:

- the explicit `EvidenceRecordStore` root dependency and cutover evidence space;
- the explicit Subjective projection location and canonical workspace/page
  source authority;
- exact build identity, configuration identity, and accepted
  deployment/readiness authority;
- projection generation and exact manifest identity;
- character, workspace, and admitted scope;
- Primary and Subjective policy, schema, renderer, platform, and authority
  revisions;
- expected intent, reader-fence, writer-fence, and finalized-receipt identities;
- the reconstructed cutover state and its exact predecessor/idempotency chain.

Paths and configuration locate inputs but never select served authority.  The
binding is not caller attestation: construction reads the durable chain through
`EvidenceRecordStore`, checks every supplied locator and revision, and refuses a
partial tuple, unsafe root, inferred default, stale value, or divergent record.

#### Reader and writer decisions

The cutover owner returns one bounded reader decision from that binding:

- before the durable reader fence: `primary_only`;
- after the reader fence and before the exact finalized receipt: `neither`;
- after the exact finalized receipt: `subjective_only`;
- for missing, incomplete, stale, divergent, unsupported, or mismatched durable
  state: fail closed.

The managed request caller explicitly constructs/carries the binding to the
ordinary retrieval owner.  The latter invokes the existing Primary candidate
path only for `primary_only`, releases neither authority for `neither`, and for
`subjective_only` uses the exact source, projection, selection, canonical
revalidation, usage finalization, admitted handoff, and unchanged E1-R4 owner.
An empty, corrupt, unavailable, or unsupported Subjective outcome after
finalization remains empty or fails closed; it never falls back to Primary.

The same binding produces the one durable Primary-writer decision.  The existing
pipeline checkpoint seam is reused before source consumption, M3e page write,
and M3g reconciliation; no second generic fence framework is introduced.  Every
live public, private, direct page/index/log apply either consumes the same
decision immediately before its durable side effect or is removed under an
explicit retirement gate.  Lease/claim fencing and cutover fencing are separate
required conditions and neither overrides the other.

#### Explicit SLP and Correct/Forget carriage

The immutable binding is carried explicitly through the one-queued-job runner
request, worker request, worker execution, pipeline invocation, and each exact
scheduler/runner construction root.  No singleton, environment lookup, or
Primary-root inference supplies it.

Correct and Forget carry the same binding through their route/caller,
preflight/apply, and recovery boundaries.  Each durable side effect reconstructs
or rechecks current cutover authority immediately before writing.  In
particular, a mutation token issued before `writer_fenced` cannot authorize an
apply or recovery write after `writer_fenced`.  The mutation coordinator may
receive only a narrow local checkpoint if exact implementation evidence needs
one; it does not evaluate the global cutover chain.

#### Canonical Subjective source acquisition and configuration

The future cutover owner orchestrates source acquisition but delegates all
semantic evaluation.  From the binding's explicit canonical workspace and
projection location, the ordinary retrieval owner loads canonical page bytes,
current selectors, receipts, authorization records, and admitted scope using
the existing canonical Markdown parser, lifecycle/receipt evaluators, projection
builder/store, selector, and usage ledger.  The projection builder continues to
receive one fixed source value and does not enumerate files or acquire locks.

Configuration may add explicit locator/binding fields following current naming
conventions for the evidence root/space, projection root, canonical workspace,
and exact build/configuration/deployment identities.  Validation rejects partial
tuples, unsafe roots, and inferred defaults.  Absence preserves current Primary-
only behavior.  No configuration value, enable boolean, or load success
authorizes deployment or serving; only the exact durable reader decision and
finalized receipt do so.

### Future implementation path budget

The replacement budget below supersedes the earlier facade-only budget.  A
fresh runtime transaction after this amendment merges must re-bootstrap and
prove each conditional path from the then-current call graph.

Required reader/config/source paths are:

```text
relaylm/config.py
config.example.yaml
relaylm/managed_chat_runtime.py
relaylm/relaymem_retrieval.py
relaylm/relaymem_primary_recall.py
relaylm/relayctx_repack.py
relaylm/subjective_mem_retrieval_cutover.py
relaylm/subjective_mem_retrieval_projection.py
relaylm/subjective_mem_retrieval_projection_store.py
relaylm/subjective_mem_retrieval_selection.py
relaylm/subjective_mem_retrieval_usage_ledger.py
relaylm/relaymem_primary_pipeline.py
relaylm/relaymem_slp_primary_worker.py
relaylm/_relaymem_slp_primary_worker_execute.py
relaylm/_relaymem_slp_primary_worker_types.py
relaylm/relaymem_slp_one_queued_job_runner.py
relaylm/relaymem_primary_correction.py
relaylm/relaymem_primary_forget.py
relaylm/relaymem_primary_forget_public_apply.py
relaylm/relaymem_primary_forget_recovery.py
relaylm/soul_lab_memory_correction_routes.py
relaylm/soul_lab_memory_forget_routes.py
```

Conditional paths, permitted only with exact live bypass or construction-root
evidence, are `_relaymem_primary_pipeline_impl.py`,
`relaymem_primary_page_writer.py`, `relaymem_primary_writer_handoff.py`,
`relaymem_primary_index_log_apply.py`, the exact scheduler/runner request
construction roots, exact correction/forget route-install roots, and
`relaymem_primary_mutation_coordinator.py` for a narrow local checkpoint only.
Facade-only changes are insufficient where a direct/private apply remains.

`relaylm/evidence_store.py`, `relaylm/evidence_space.py`, the canonical Markdown,
lifecycle, selector, receipt, and E1-R4 policy owners are reused and excluded
from modification absent a new evidence-backed P1 return.  They do not become
cutover authorities.  No generic registry, adapter, factory, plugin, second
store, marker, journal, lock, recovery owner, environment lookup, or inferred
root is authorized.

`relaylm/evidence_store.py` is an imported and reused generic infrastructure
dependency, not an expected modified production path and not the RT-1D semantic
owner.

Retirement candidates remain the shadow characterizer and its focused test, the
two Primary recall compatibility no-ops, old reader/fallback surfaces, and any
direct writer callable whose consumers have moved to the exact binding.  Each is
deleted or disabled only after its existing removal gate and complete negative
call-graph search pass; lifecycle/historical Primary state remains where an
accepted operational consumer still requires it.

The future test budget includes focused cutover state and restart reconstruction,
configuration tuple validation and absence behavior, one-authority ordinary
routing, final-receipt-only serving, prepared non-serving, empty/corrupt/
unavailable Subjective results without fallback, canonical source and projection
rebuild equivalence, M3 source/M3e/M3g checkpoints, direct/private bypass
searches, queued-runner/worker carriage, Correct and Forget token-before-fence/
apply-after-fence races, post-fence recovery, and proof that no Primary durable
write occurs after `writer_fenced`.  Security tests prove no second root/marker/
journal and no private path, identifier, digest, prose, query, prompt, or
correlation leakage.  Tests validate production semantics and do not duplicate
them.

The focused state/process owner is
`tests/test_subjective_mem_retrieval_cutover.py`; existing focused projection,
selection, usage, request-path, pipeline, worker, Correct, Forget, recovery, and
configuration tests may change only for the responsibility they already own.

A new selector, receipt evaluator, lifecycle evaluator, generic cutover
framework, adapter/registry/factory/plugin, second persistence/recovery
mechanism, implicit locator, or unbounded caller sweep is forbidden.  Return to
P1 if a path outside the classified budget is needed, an additional authority
owner appears, a direct writer cannot receive the binding, configuration would
select authority, or the usual structural-growth triggers fire.

### Compatibility consumers and removal gates

Live Primary consumers are the ordinary retrieval compiler, RelayCTX repack, Soul Lab observation projection, memory-stage extraction and request-path tests, Primary formation/page/index/log/SLP writers, lifecycle eligibility/current-state overlays, and their registered smokes. After exact finalized-receipt replay, restart testing, only-Subjective request-path probes, writer-fence proof, negative search for Primary ordinary serving, and disclosure/rebuild equivalence pass, the old reader/fallback and writer entry points are removed or disabled. The lifecycle overlay retires only when no accepted Primary operational/historical consumer requires it. Shadow characterization retires after its accepted gate record and post-transfer evidence are preserved. Frozen historical/evaluation fixtures remain only where a continuing accepted purpose is documented; they cannot be live authority. Primary and Subjective are never both canonical, and no permanent compatibility owner remains.

### Structural P1 Return and ordered prerequisite seams

Exact-current inspection returned runtime implementation to P1 before any
runtime write. The measurements at commit
`7c9afd62e6067b7476aeb10e7b165d8efde49bad` are:

```text
relaylm/managed_chat_runtime.py                       710 lines
  handle_managed_chat_completion                     lines 132-382, 251 lines
relaylm/relaymem_retrieval.py                        1435 lines
relaylm/relaymem_primary_recall.py                   1198 lines
relaylm/_relaymem_slp_primary_worker_execute.py       297 lines
  execute_relaymem_slp_primary_worker                lines 47-290, 244 lines
relaylm/relaymem_slp_one_queued_job_runner.py          700 lines
relaylm/relaymem_primary_correction.py                1100 lines
  apply_primary_memory_correction                    lines 157-279, 123 lines
relaylm/relaymem_primary_forget_recovery.py            779 lines
  apply_primary_memory_forget                        lines 155-304, 150 lines
relaylm/soul_lab_memory_correction_routes.py           161 lines
  install_primary_memory_correction_routes           lines 44-161, 118 lines
relaylm/soul_lab_memory_forget_routes.py               231 lines
  install_primary_memory_forget_routes               lines 53-231, 179 lines
```

These are review triggers, not permanent exemptions. Appending RT-1D carriage
would make the existing structural debt worse; facade-only wrapping would leave
private/direct writer bypasses; and splitting merely to lower line counts would
not transfer a coherent responsibility. Runtime therefore remains not started.

Responsibility-driven extraction may move existing behavior only when one exact
current responsibility, accepted caller, explicit input and output, and public
facade are identified. Semantics are moved rather than copied; no generic
framework or unused abstraction is introduced; equivalence tests prove
unchanged behavior; and source and destination remain bounded. Moving one giant
block into another file over roughly 700 lines is not an accepted seam.

The only accepted Lane C order is:

```text
RT-1D-S1 reader seams
  -> mandatory same-lane P8 -> verify resulting main
  -> RT-1D-S2 worker seams
     -> mandatory same-lane P8 -> verify resulting main
     -> RT-1D-S3 mutation seams
        -> mandatory same-lane P8 -> verify resulting main
        -> fresh RT-1D runtime implementation
           -> mandatory same-lane P8 after merge
```

One logical writer owns each transaction, and none overlaps another Lane C
transaction. S1-S3 preserve Primary-only behavior and must not add the cutover
binding, cutover records, configuration fields, reader/writer decisions,
Primary fences, Subjective serving, fallback changes, authority selection,
retirement, `EvidenceRecordStore` changes, or another persistence/recovery
mechanism.

#### RT-1D-S1 reader seams

S1 separates managed post-validation stage orchestration, legacy Retrieval
dry-run construction, and Primary recall selection/store validation. Required
existing paths are `relaylm/managed_chat_runtime.py`,
`relaylm/relaymem_retrieval.py`, and `relaylm/relaymem_primary_recall.py`.
Authorized new owners are:

- `relaylm/managed_chat_pipeline_runtime.py` for post-validation
  compile/scope/evidence/stage orchestration and one explicit private result;
- `relaylm/relaymem_retrieval_dry_run.py` for the legacy M2 dry-run artifact;
- `_relaymem_retrieval_candidates.py` and `_relaymem_retrieval_snippet.py` only
  when exact extraction evidence is required to keep that owner bounded;
- `relaylm/relaymem_primary_recall_selection.py` for selection,
  relevance/fallback choice, and handoff construction;
- `relaylm/relaymem_primary_recall_store.py` for read-only
  control/index/log/page loading and exact validation.

The current public handler, retrieval stage, and Primary recall facade remain
authoritative. Public imports and schemas, stage order and timing, offload
boundary, diagnostics, artifacts, bytes, relevance/fallback behavior, path
safety, and lifecycle evaluation remain exact. Existing request-path,
memory-stage, prebackend-payload, chat-characterization, app-orchestration,
two-turn recall, and retrieval-exclusion tests/smokes may change only for
import/equivalence ownership; at most
`tests/test_rt1d_reader_seams.py` may be added. Managed response, RelayCTX
repack, Retrieval priority/store, configuration, Subjective modules, the
cutover owner, and current-authority documents are excluded from the S1 code
PR absent a new P1 Return.

#### RT-1D-S2 worker seams

S2 separates the long SLP executor and one-queued-job runner into existing
phases. Required existing paths are
`relaylm/_relaymem_slp_primary_worker_execute.py` and
`relaylm/relaymem_slp_one_queued_job_runner.py`. Authorized new owners are
`relaylm/_relaymem_slp_primary_worker_pipeline.py` for source-to-pipeline
request construction and checkpointed pipeline execution, and
`relaylm/_relaymem_slp_one_queued_job_runner_execute.py` for claim, source
preparation, worker invocation, and terminal cleanup.

Worker types, validation, outcome adaptation, and the public worker facade may
change only when exact type/import evidence requires it. Public functions and
projections, claim revalidation, lease renewal counts, protected-source release
order, status/reason bytes, retry, cleanup, and terminal transitions remain
exact. The existing phase 6-C1/6-C2 and O0 contract/security smokes own
equivalence; at most `tests/test_rt1d_worker_seams.py` may be added. Fence
semantics, Primary pipeline semantics, queue/store semantics, scheduler policy,
configuration, the cutover owner, and current-authority documents are excluded
from the S2 code PR absent a new P1 Return.

#### RT-1D-S3 monolithic P1 Return and ordered slices

The monolithic S3 behavior-preserving candidate was discarded with no commit,
push, PR, receipt, P8, runtime, or authority update. Current-main measurements
were:

```text
relaylm/relaymem_primary_correction.py                 1100 lines
relaylm/relaymem_primary_forget_recovery.py             779 lines
relaylm/soul_lab_memory_correction_routes.py             161 lines
relaylm/soul_lab_memory_forget_routes.py                 231 lines
preflight_primary_memory_correction                       72 lines
apply_primary_memory_correction                          123 lines
recover_primary_memory_corrections                        71 lines
apply_primary_memory_forget                              150 lines
recover_primary_memory_forget                             87 lines
Correct route installer                                  118 lines
Forget route installer                                   179 lines
```

Although the candidate passed relevant Correct, Forget, route, mutation-fence,
and lifecycle tests, it still measured 771 lines in
`_relaymem_primary_correction_apply.py`, 125 lines in Correct apply, 120 lines
in prepared-successor publication, 156 lines in Forget apply, 89 lines in Forget
finalization, and 153 lines in the Forget runtime factory. It therefore failed
the accepted approximate below-700-module and about-80-line orchestration gates.
The thresholds are review gates, not targets to waive, line-golf, reinterpret,
or evade with a monolithic move.

This transaction, PR #793, replaces monolithic S3 with
three ordered, non-overlapping, behavior-preserving Primary-only slices. The
amendment changes no runtime behavior and itself requires no P8. It merged with
exact result `5011eaaddd895b434f3d870dcf2206527725629c`.

##### RT-1D-S3A Correct core seams

Exact future production budget:

```text
relaylm/relaymem_primary_correction.py
relaylm/_relaymem_primary_correction_preflight.py
relaylm/_relaymem_primary_correction_apply.py
relaylm/_relaymem_primary_correction_publication.py
relaylm/_relaymem_primary_correction_recovery.py
relaylm/_relaymem_primary_correction_history.py
```

Optional focused test only: `tests/test_rt1d_s3a_correct_seams.py`.

The facade keeps exact public imports, functions, signatures, schemas, and
`__all__`. The extracted responsibilities are preflight/token issuance and
validation; apply/replay/receipt orchestration; prepared-successor construction,
publication, and index/log convergence; caller-invoked prepared-operation
recovery; and read-only history/current-state compatibility. Token bytes,
claims, TTL, digests, operation keys, fault names, lock order, receipts,
page/index/log bytes, idempotency, and crash/recovery behavior remain exact.
There is no generic mutation framework or second authority. The facade is
materially reduced, new modules remain below roughly 700 lines, and touched
orchestration remains about 80 lines or less. Another owner or path requires a
fresh S3A P1 Return before writing.

S3A excludes Forget, Soul Lab, mutation-coordinator semantics, documentation in
the code PR, cutover, configuration, serving, and retirement.

S3A completed in PR #794 with exact resulting main
`2d05a41235e396ac82d536437ed8e5568f617253`. Its final production owners are
`relaylm/relaymem_primary_correction.py` (122 lines),
`relaylm/_relaymem_primary_correction_preflight.py` (269),
`relaylm/_relaymem_primary_correction_apply.py` (444),
`relaylm/_relaymem_primary_correction_publication.py` (104),
`relaylm/_relaymem_primary_correction_recovery.py` (60), and
`relaylm/_relaymem_primary_correction_history.py` (137); the largest touched
orchestration span is 73 lines. This was a behavior-preserving structural
prerequisite only. The facade preserves exact public names,
signatures/defaults, constants, `__all__`, canonical exception/state identities,
and import locations. Existing `_utc` and
`apply_relaymem_primary_page_write` compatibility seams remain effective
through explicit internal dependency injection. No production monkeypatch,
pytest monkeypatch fixture, runtime patch installer, temporary patch module,
`sys.modules` manipulation, or `importlib` reload was introduced. Token
claims/TTL, operation keys, lock/validation order, receipts,
replay/idempotency, canonical page/index/log bytes, fault positions,
caller-invoked recovery, history/current-state behavior, and durable effects
remain exact.

##### RT-1D-S3B Forget core seams

Exact future production budget:

```text
relaylm/relaymem_primary_forget_recovery.py
relaylm/_relaymem_primary_forget_apply.py
```

Optional focused test only: `tests/test_rt1d_s3b_forget_seams.py`.

S3B owns external apply validation and exact replay; token/reason/operation
binding; handoff to the existing hidden-successor owner; reacquisition and
recovery/finalization handoff; caller-selected recovery; hidden-successor
verify/resume; index/log/control convergence; and tombstone/applied-receipt
finalization. `relaylm/relaymem_primary_forget.py` and
`relaylm/relaymem_primary_forget_public_apply.py` remain byte-identical. Public
symbols/import chains, schemas, result dataclasses, faults, locks, durable bytes,
replay, and already-hidden normalization remain exact. The recovery module stays
below roughly 700 lines and touched orchestration stays about 80 lines or less.
Any additional path requires a fresh S3B P1 Return before writing.

S3B excludes Correct, Soul Lab, Forget public facades, lifecycle/receipt
authority changes, documentation in the code PR, cutover, configuration,
serving, and retirement.


**RT-1D-S3B Forget core seams** completed in PR #796 from bootstrap/parent main `bc27c25d0b745fc2d9927e9e21179b14cd337141`, with implementation head `126e88dc18c8a61e439a41c8da7e6e0eaa2ccfc2`, commit subject `refactor: extract RT-1D-S3B Forget seams`, and exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427`. Its exact two-path diff was `relaylm/_relaymem_primary_forget_apply.py` (+400/-0) and `relaylm/relaymem_primary_forget_recovery.py` (+127/-274), total +527/-274. The recovery facade is now 632 physical lines (from 779), and the internal apply owner is 400 physical lines (from absent). Touched orchestration spans are public apply wrapper 45, public recovery wrapper 42, locked recovery 48, finalization coordinator 17, hidden-state resolution 16, control convergence 25, tombstone finalization 52, internal apply entry point 65, validated apply coordinator 29, existing-operation replay 34, hidden-successor handoff 42, and reacquisition/finalization 22 lines; both modules are below the approximate 700-line trigger and every touched orchestration is below 80 lines.

The public apply signature remains unchanged. `relaylm/relaymem_primary_forget_recovery.py` remains the canonical public compatibility, recovery, finalization, result-class, schema, and export owner; `relaylm/_relaymem_primary_forget_apply.py` owns bounded apply validation, exact replay, binding, initial lock/reread, hidden-successor handoff, reacquisition, and delegation to canonical finalization. The dependency direction is `relaymem_primary_forget_recovery -> _relaymem_primary_forget_apply`; the internal apply owner does not import the recovery facade. The facade constructs a frozen per-call dependency bundle from current module globals, preserving existing facade patch seams. No replacement public result dataclasses were introduced. Public schemas, signatures/defaults, class identities, inheritance, dataclass metadata, repr, schema behavior, `to_log_dict` projections, exception identity, and facade re-export identities remain exact. No production monkeypatch, pytest monkeypatch fixture, runtime patch installer, temporary patch module, `sys.modules` mutation, `importlib.reload`, or dynamic reverse import was introduced. Immutable facade hashes remain `relaylm/relaymem_primary_forget.py` SHA-256 `4fe026b1c87639c8cb248acce41ac4b2d875e1f05eb14d28fc79059dc0600f92` and `relaylm/relaymem_primary_forget_public_apply.py` SHA-256 `8a0af188df9ee1c037547de60f92fc8cf39e9d09a34f361292ea82133694021e`; both are byte-identical to the exact-main baseline.

Validation/fault order, operation/token/reason binding, lock/replay/handoff/reacquisition behavior, caller-selected recovery, hidden resume, M3f/M3g/control convergence, tombstone publication/reread, deterministic timestamp, durable bytes, result/error/leakage behavior, response-lost, and reconciliation behavior remain exact. Python 3.12.13 validation and every applicable exact-head workflow succeeded for implementation head `126e88dc18c8a61e439a41c8da7e6e0eaa2ccfc2`; legitimate changed-path exclusions were skipped, with no failed, queued, or in-progress check remaining. PR #796 added no cutover, runtime, configuration, persistence, lifecycle, receipt, API, UI, S3C, or P8 behavior. Primary MEM remains the sole ordinary served memory and Retrieval authority.
##### RT-1D-S3C Soul Lab mutation route seams

**RT-1D-S3C Soul Lab mutation route seams** completed in PR #798 from bootstrap/parent main `e221f17906682bdb077d8016e09843d176af5df4`, with implementation head `97e161beab5b037ab1b8505641b9c6091b7b4ca0`, commit subject `refactor: extract RT-1D-S3C Soul Lab mutation seams`, and exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. Its exact four-path diff was `relaylm/soul_lab_memory_correction_routes.py` (+42/-99; 104 lines), `relaylm/soul_lab_memory_correction_runtime.py` (+136/-0; 136 lines), `relaylm/soul_lab_memory_forget_routes.py` (+43/-168; 106 lines), and `relaylm/soul_lab_memory_forget_runtime.py` (+209/-0; 209 lines), total +430/-267, with no optional focused test. Every module is below the approximate 700-line trigger; maximum orchestration is 52 lines, all touched orchestration is below about 80 lines, and no waiver applies. Route metrics are Correction loopback 9, dependency resolution 12, installer 52, nested handlers 10 each; and Forget loopback 9, dependency resolution 13, installer 52, nested handlers 10 each. Correction runtime metrics are dependency owner 9, exact JSON 10, scope 7, error mapping 4, preflight 24, apply 22, history 16. Forget runtime metrics are dependency owner 10, exact JSON 10, scope 7, error mapping 4, preflight projection 20, apply projection 28, preflight 26, apply 27, history 22.

The one-way acyclic owner graph is `soul_lab_memory_correction_routes -> soul_lab_memory_correction_runtime` and `soul_lab_memory_forget_routes -> soul_lab_memory_forget_runtime`. Route owners retain installers, decorators and registration, paths, methods and order, `response_model=None`, namespace `Query` constraints (`min_length=1`, `max_length=128`), global loopback authorization, per-request dependency construction, and module-level patch seams. Runtime owners retain operation-specific JSON parsing, scope resolution, domain invocation, safe projection, error mapping, no-store JSON responses, and separate preflight/apply/history paths. There is no reverse route import, generic mutation runtime, dynamic import, `sys.modules` mutation, `importlib.reload`, production monkeypatch, or patch installer.

All six routes remain exact and ordered: `POST .../correct/preflight`, `POST .../correct`, `GET .../corrections`, `POST .../forget/preflight`, `POST .../forget`, and `GET .../forget-history`. Exact methods/order, `response_model=None`, namespace constraints, authorization-first order, strict `application/json`, 16,384-byte limit, empty/oversize/UTF-8/JSON/Pydantic errors, scope-before-domain order, the full error map and unknown normalization, exact successful objects, Forget projections, status/detail bytes, `Cache-Control: no-store`, leakage bounds, call arguments/order, and post-app-creation `patch.object` behavior are preserved. `relaylm/soul_lab_app.py` remained byte-identical with baseline/final SHA-256 `877457129d617ed0a90df879e1a41d9807503bb2612b68095812dfc87dea58e4`; configuration, contracts, workflows, documentation, and evidence were unchanged in PR #798.

The external baseline/candidate differential matrix SHA-256 was `44547117872e449294095f240d79f16b8bbd9c7f6c89737fa9c865e461c65dac`. It covered registration/order, authorization and authorization-before-domain access, media/body/UTF-8/JSON/Pydantic failures, valid preflight/apply/history objects and arguments, projections/leakage, every mapped error, unknown normalization, status/detail/cache, and post-install patches; its harness and stores remained outside the repository. Python 3.12 validation passed `scripts/relaylm_soul_lab_memory_routes_split_smoke.py`, `scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py`, `scripts/relaylm_phase_i4e_forget_api_security_smoke.py`, `scripts/relaylm_phase_i4f_forget_validation_security_smoke.py`, focused Correct/Forget security and validation smokes, `py_compile` for all four paths, `compileall` for `relaylm`/`scripts`/`tests`, `git diff --check`, and the isolated differential comparison. Every applicable exact-head workflow for `97e161beab5b037ab1b8505641b9c6091b7b4ca0` succeeded or was legitimately path-skipped; none failed, queued, or remained running.

##### Ordered convergence and shared exclusions

```text
S1 PR #789 result b272edb78602032009d4882a6244883cce610b86
  -> S1 P8 PR #790 result 3e20274f18306f7db2410fd5239051411b9c052b
  -> S2 PR #791 result 31b700a2db0af7819f761d51bd946ff6798eb4c9
  -> S2 P8 PR #792 result 7e4fb4383dc6c1229d488ac200132b66f6b65bba
  -> S3 P1 architecture amendment PR #793 result 5011eaaddd895b434f3d870dcf2206527725629c
  -> S3A PR #794 result 2d05a41235e396ac82d536437ed8e5568f617253
  -> S3A mandatory P8 PR #795 result bc27c25d0b745fc2d9927e9e21179b14cd337141
  -> S3B implementation PR #796 result b75df848bf3982e00f67969c016ba1f28dd93427
  -> mandatory S3B P8 current-authority synchronization PR #797 result e221f17906682bdb077d8016e09843d176af5df4
  -> S3C implementation PR #798 result 56fa66fdba475a3d6e1a4bc4cbc3480ba238720e
  -> mandatory S3C P8 current-authority synchronization PR #799 result d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f
  -> independently verify S3C P8 PR #799 exact resulting main
  -> fresh RT-1D runtime next, not started -> separate implementation transaction -> runtime P8
```

S3A and its mandatory P8 PR #795 are complete, with P8 result `bc27c25d0b745fc2d9927e9e21179b14cd337141`. S3B and its mandatory P8 PR #797 are complete, with P8 result `e221f17906682bdb077d8016e09843d176af5df4`. S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. The mandatory S3C P8 current-authority synchronization PR #799 merged with exact resulting main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Fresh RT-1D runtime is architecture-authorized in five ordered slices but has not started. Primary MEM remains the sole ordinary served memory and Retrieval authority. Subjective ordinary retrieval remains disabled and unwired. No cutover, authority switch, serving, fallback, or retirement change occurred. No Lane C
transaction overlaps. Only the exact resulting main after S3C P8 verification may bootstrap
fresh runtime implementation. All three slices preserve Primary-only behavior
and exclude cutover binding, configuration, authority selection, Subjective
serving, fallback change, retirement, new persistence authority, API behavior,
and UI behavior. Every implementation merge requires its mandatory same-lane P8
and exact resulting-main verification before the next slice. A fixed budget may not be silently expanded.

#### Structural completion gates for S1-S3

Before Ready, every S1, S2, or S3 code PR proves that its complete
main-relative path budget was fixed before writing; every touched public API,
import, and schema remains exact; projections and HTTP responses remain
byte-equivalent where applicable; and durable filesystem bytes and fault,
crash, and recovery outcomes remain unchanged. It also proves that the slice
introduces no import cycle, import-time side effect, duplicated semantics,
generic framework, new authority, new configuration authority, or new
persistence or recovery owner.

Every touched orchestration function is at or below the approximate 80-line
review target. Any exception to that target requires an exact reviewed P1
Return before any branch write, never a post-hoc exemption. Every new
production module remains below the approximate 700-line review trigger. Every
touched pre-existing oversized facade is materially reduced and brought toward
or below approximately 700 lines where the accepted responsibility-driven
extraction can do so; no destination module becomes another oversized dumping
ground. A slice unable to meet these gates returns to P1: it does not waive,
line-golf, bypass, or reinterpret the thresholds.

### Required RT-1D negative matrix

Tests must refuse stale, missing, duplicate, or conflicting selectors; legacy unbound selectors; missing, partial, inferred, or mismatched binding tuples; unsafe or Primary-derived roots; missing or mismatched receipts, authorizations, build, configuration, deployment/readiness authority, page, block, scope, policy, schema, renderer, or platform; mixed or stale generations; hidden, held, superseded, purged, prepared, recovery-required, corrupt, prior, cross-character, or cross-scope revisions; unresolved lifecycle/publication intent; combined Primary/Subjective results; fallback after an empty, corrupt, or unavailable Subjective result; Subjective serving before finalization; Primary serving afterward; a direct/private Primary writer bypass; a queued/worker request without the exact binding; a Correct/Forget token crossing `writer_fenced`; recovery writing after the fence; usage-finalization failure followed by evidence admission; a second root, marker, journal, lock, or process-local authority; public leakage of prose, query text, paths, private IDs, digests, or correlation material; crash/restart at every transition; non-deterministic replay; and partial retirement before exact validation.

### RT-1D validation matrix

Focused unit tests own state validation, immutable binding reconstruction, exact identities, configuration tuple validation, and negative classes. Request-path integration tests own explicit reader carriage, one-authority routing, E1-R4 handoff, prepared/empty/failure results, and finalized-receipt-only serving. Process tests kill/restart every durable transition. Pipeline tests exercise the existing source/M3e/M3g checkpoints; worker and route tests prove queued, Correct, Forget, apply, recovery, and mutation-token carriage. Characterization tests own content-free deterministic comparison and leakage; projection tests own source acquisition and deletion/rebuild equivalence. Security tests own scope, private-disclosure refusal, and absence of a second persistence mechanism. Exact one-authority and repository-wide direct-call negative searches prove no alternate Primary reader or writer route remains. The future PR also requires exact-head CI, complete-diff review, resulting-main validation after merge, and a mandatory same-lane P8 authority-synchronization PR before Lane C advances.

### RT-1D explicit non-goals

This authorization PR contains no runtime implementation, deployment approval, default-on policy, Primary-to-Subjective migration, backup/restore completion, multi-host coordination, physical purge, Merge/Supersession operations, RelaySOUL apply/rollback, API/UI/config/scheduler/worker/queue/daemon/background automation, ranking or embedding redesign, E1-R4 policy change, response rewriting, unrelated documentation cleanup, or repository maintenance.

## Fresh exact-current RT-1D runtime P0/P1 authorization (2026-08-01)

### Inspection basis and P2 disposition

This architecture-only transaction selected **Codex Cloud**, inspected exact
`origin/main` `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`, and authorizes budgets only.
Fresh RT-1D runtime P0/P1 architecture authorization PR #800 completed with
result `68cc16b9d5ed7b999c22d27457390e53de851335`. PR #800 is architecture-only and requires no P8. RT-1D-R1 is not
started and is non-executable until PR #800 merges and its exact resulting main
is independently verified; no implementation slice may start from the PR head,
and PR #800's independently verified resulting main bootstrapped R1.
PR #799 is merged with head `b596ffc5cf9cf7f0d38d862dd7a81c12509aa182`
and that exact resulting main; PR #798 is merged with result
`56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. There was no open PR, target
branch, competing Lane C writer, active workflow, branch-pushing validation, or
`relaylm:p6-stop`; the governance epoch was
`2c4dcdcee169e6056c2bb29124d52fdac96288c98446820d7c8a464b1cf5d1db`.
The checkout and index were clean. No runtime implementation has started.

The inspection enumerated direct imports, public/re-exported names, tests,
smokes, scheduler and queue roots, routes, configuration, persistence, recovery,
and operator entry points. The reader order is
`managed_chat_pipeline_runtime.run_managed_chat_pipeline` ->
`relaymem_retrieval.run_relaymem_retrieval_stage` ->
`relaymem_primary_recall.prepare_primary_recall_selection` -> selection/store ->
RelayCTX repack -> E1-R4. Primary fallback is owned by
`relaymem_primary_recall_selection`; no Subjective owner is imported by the
ordinary path. Subjective selection -> canonical-page revalidation -> prepared
private handoff -> usage-ledger finalization -> admitted handoff is complete but
has only focused test callers. The characterization owner is similarly test-only.

The live Primary writer ingress families are: managed-response SLP enqueue and
durable enqueue; local/supervised scheduler queue and replay lanes; one-job
runner; worker and pipeline; direct M3e page and M3g index/log apply/recovery;
Correct preflight/apply/recovery plus its Soul Lab routes; Forget
preflight/apply/recovery plus its routes; and Pin/Unpin routes/runtime. Primary
Restore and Consolidate have no live Primary apply route: their governed live
implementations are Subjective-only. Primary observation, history, and frozen
lifecycle projections may remain read-only admin/history surfaces, never an
ordinary reader or writer. Queue claims and mutation tokens acquired before a
fence confer no write authority after the durable writer fence.

Exact-current structural measurements include: `managed_chat_pipeline_runtime.py`
305 lines (largest orchestration 78), `relaymem_retrieval.py` 112 (60),
`relaymem_primary_recall.py` 148 (43), `relaymem_primary_recall_selection.py`
698 (92 and 160 review-trigger spans), `relaymem_primary_recall_store.py` 427
(118), `subjective_mem_retrieval_selection.py` 552 (68),
`subjective_mem_retrieval_characterization.py` 309 (51),
`subjective_mem_retrieval_usage_ledger.py` 428 (59),
`_relaymem_slp_primary_worker_execute.py` 294 (46),
`_relaymem_slp_primary_worker_pipeline.py` 62 (17),
`relaymem_slp_primary_worker.py` 141 (39),
`relaymem_slp_one_queued_job_runner.py` 504 (59), and
`_relaymem_slp_one_queued_job_runner_execute.py` 297 (41). Exact baseline
SHA-256 values for the byte-sensitive reader/worker owners are, respectively,
`382830637cae6c271aa9299510cdd8543f06515a816ffb696696c7321fc84469`,
`92f147f0bb834357908b89410324412d7a4e61e396b3c61ce86500deda9f25f3`,
`013da1ec84f472a6207a21176c778803843bb1fc8473fa528e4558d80813adcb`,
`fa1df65bea95d2f5c27b318f3628c40497e67b394cedd9f80d51c26931cdc0fd`,
and `6fd3846cdca9a4542b71c914c528513981d0d833c20a356d5b921881ce91cb4e`.
`evidence_store.py` is 681 lines and remains byte-identical generic
infrastructure, not semantic cutover authority.

The No-Patch Gate and Stable-Structure Gate pass only for the five ordered slices
below. Rejected alternatives are configuration-only authority, a Primary-root
marker, a second store or journal, facade-only fencing, permanent dual mode,
empty-result fallback, automatic rollback, and one broad runtime PR. Any extra
path, reverse facade import, new generic registry, or inability to keep new
production owners below about 700 lines and touched orchestration at about 80
lines returns to P1.

### Existing-data gate

ST-1 revision-1 create selectors that lack the complete authority binding remain
excluded by RT-1B and RT-1C. Current finalized, authority-bound revisions are
accepted; legacy unbound revision-1 selectors are not silently bound, migrated,
or projected. No pre-transfer migration is required for correctness: cutover may
proceed with those memories absent, and users lose ordinary recall of unported
Primary memories and excluded Subjective memories. A deployment requiring them
must remain Primary-only until a separately accepted binding/migration authority
completes. Frozen Primary assets are history, export, or governed rollback
evidence only.

### Ordered implementation slices and exact budgets

Every slice starts from the independently verified resulting main of the prior
slice's mandatory same-lane P8, has one writer, and ends with its own P8 and
resulting-main verification. Paths not listed for that slice remain byte-identical.

#### RT-1D-R1 — durable preparation (default-off)

Purpose: add the one semantic cutover owner, content-free schemas, exact chain
reconstruction, configuration tuple validation, and rehearsal-only operator API.

Production/config budget:

```text
relaylm/subjective_mem_retrieval_cutover.py              new
relaylm/config.py
config.example.yaml
```

Focused evidence budget:

```text
tests/test_subjective_mem_retrieval_cutover.py           new
scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py new
```

The owner depends on `EvidenceRecordStore`; the store, canonical Markdown,
projection, selectors, lifecycle evaluators, usage ledger, all readers, and all
writers remain byte-identical. Allowed behavior is fail-closed validation and
explicit rehearsal only. Defaults remain Primary-only. It cannot create durable
intent/fence/receipt records, serve Subjective evidence, or fence a writer.

#### RT-1D-R2 — Primary writer-fence carriage (default-off)

Purpose: carry one reconstructed writer decision to every live Primary formation
and mutation side effect, while the durable state remains `primary_stable`.

Production budget:

```text
relaylm/subjective_mem_retrieval_cutover.py
relaylm/managed_chat_runtime.py
relaylm/relaymem_slp_runtime_finalization.py
relaylm/relaymem_slp_one_queued_job_runner.py
relaylm/_relaymem_slp_one_queued_job_runner_execute.py
relaylm/relaymem_slp_primary_worker.py
relaylm/_relaymem_slp_primary_worker_types.py
relaylm/_relaymem_slp_primary_worker_execute.py
relaylm/_relaymem_slp_primary_worker_pipeline.py
relaylm/relaymem_primary_pipeline.py
relaylm/_relaymem_primary_pipeline_impl.py
relaylm/relaymem_primary_correction.py
relaylm/_relaymem_primary_correction_apply.py
relaylm/_relaymem_primary_correction_recovery.py
relaylm/relaymem_primary_forget_recovery.py
relaylm/_relaymem_primary_forget_apply.py
relaylm/soul_lab_memory_correction_runtime.py
relaylm/soul_lab_memory_forget_runtime.py
relaylm/soul_lab_memory_pin_routes.py
relaylm/relaymem_primary_pin.py
```

Focused tests may modify only the existing worker, pipeline, queue, Correct,
Forget, Pin, route, scheduler, and runtime-finalization tests plus
`tests/test_subjective_mem_retrieval_cutover.py`. Direct M3e/M3g functions remain
unchanged because the existing three pipeline checkpoints guard source
consumption, page publication, and index/log reconciliation; a negative call
graph test must prove no independent live apply root bypasses them. If it finds
one, stop at P1 rather than adding a conditional path. Allowed behavior is only
carriage and rejection when an injected test binding says fenced; production
state remains Primary-only and no fence record can yet be written.

#### RT-1D-R3 — rehearsal and readiness

Purpose: acquire the exact fixed Subjective source, validate one projection
generation, run deterministic content-free characterization, and persist no
ordinary usage event or authority state.

Production budget:

```text
relaylm/subjective_mem_retrieval_cutover.py
relaylm/subjective_mem_retrieval_characterization.py
```

Focused budget:

```text
tests/test_subjective_mem_retrieval_cutover.py
tests/test_subjective_mem_retrieval_characterization.py
scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py
```

Projection builder/store, selection, usage ledger, Primary reader, managed route,
and configuration remain byte-identical. Acceptance is content-free deterministic
replay, deletion/rebuild equivalence, lifecycle/security/leakage cases,
empty/non-empty and token-budget classes, bounded latency/request classes, and
an exact readiness identity. Shadow output is never served and writes no ordinary
usage event. No new diagnostic registry or control plane is allowed.

#### RT-1D-R4 — one-authority activation

Purpose: the sole authority-changing slice. It creates intent and fences, binds
the exact projection, finalizes the receipt, and wires the one ordinary Subjective
reader.

Production budget:

```text
relaylm/subjective_mem_retrieval_cutover.py
relaylm/managed_chat_pipeline_runtime.py
relaylm/managed_chat_runtime.py
relaylm/relaymem_retrieval.py
relaylm/relaymem_primary_recall.py
relaylm/relayctx_repack.py
relaylm/subjective_mem_retrieval_selection.py
relaylm/subjective_mem_retrieval_usage_ledger.py
```

Focused tests may modify the exact request-path, reader-seam, offload, pipeline
ordering, RelayCTX, selection, usage-ledger, configuration, and cutover tests and
`relaylm_p0_pipeline_ordering_smoke.py` plus the cutover smoke. E1-R4 policy,
projection builder/store, Evidence store, writer modules, canonical/lifecycle
owners, API/UI, scheduler, and deployment files remain byte-identical. Allowed
behavior is exactly Primary-only -> neither -> Subjective-only. There is no
result merge, empty-result fallback, stale-cache fallback, or Primary fallback.

#### RT-1D-R5 — immediate retirement and proof

Purpose: after exact R4 post-transfer probes, remove replaced ordinary Primary
reader/fallback and temporary characterization surfaces and permanently disable
the transferred Primary writer/mutation entry points while preserving explicitly
classified read-only history/admin projections.

Production deletion/modification budget:

```text
relaylm/relaymem_primary_recall.py
relaylm/relaymem_primary_recall_selection.py
relaylm/relaymem_primary_recall_store.py
relaylm/subjective_mem_retrieval_characterization.py
relaylm/relaymem_retrieval.py
relaylm/subjective_mem_retrieval_cutover.py
```

Focused budget is limited to their current tests/smokes, request-path and package
import tests, the cutover test/smoke, and `scripts/relaylm_p0_pipeline_ordering_smoke.py`.
Writer modules remain byte-identical: R2's durable decision makes their live
transferred-domain writes unreachable/rejected. Primary lifecycle overlays used
by observation/history survive only as read-only admin surfaces. Removal requires
negative import/call searches, Primary-reader rejection, Primary-writer rejection
and drained queues, Subjective-only probes, leakage checks, and preserved frozen
assets. Any continuing ordinary consumer blocks retirement and returns to P1.

### Exact durable state machine and crash matrix

The semantic owner accepts only this predecessor-linked chain:

```text
primary_stable (Primary only)
  -> rehearsal_ready (Primary only)
  -> transfer_intent (Primary only; forward recovery begins)
  -> primary_reader_fenced (neither)
  -> primary_writer_fenced (neither)
  -> subjective_generation_bound (neither)
  -> subjective_reader_enabled (Subjective only; same atomic transaction as receipt)
  -> transfer_receipt_finalized (Subjective only)
  -> post_transfer_validated (Subjective only)
  -> retirement_complete (Subjective only)
```

`subjective_reader_enabled` and `transfer_receipt_finalized` are two validated
records in one `EvidenceStoreTransaction`; no externally reconstructible state
may contain only the first. Missing, partial, divergent, tampered, unsupported,
or predecessor-inexact state is `recovery_required` and serves neither unless
the last complete state is provably `primary_stable` or `rehearsal_ready`.
Operator reconciliation is forward-only after intent. A post-transfer rollback
is a separate governed transfer, never automatic fallback.

Crash rules are: before intent, Primary resumes; after intent before fences,
Primary may serve but no new transfer attempt starts; after reader fence, neither
serves and recovery advances; after writer fence or generation binding, neither
serves and queued/in-flight writes are rejected/reconciled; activation and receipt
commit atomically, so there is no admitted crash point between them; after usage
finalization but before backend handoff, retry returns the exact idempotent result
and may release only the revalidated admitted handoff; after backend handoff a
lost response never creates another usage pair; after receipt before probes,
Subjective alone serves; during retirement, Subjective alone serves and removal
resumes idempotently. Ordinary conversation may always continue without durable
memory context under existing policy.

### Receipt, startup, diagnostics, and validation

The content-free receipt binds schema/digest, authority domain and transferred
scope, bootstrap/resulting-main and policy revisions, exact projection generation
and source digest, reader/writer fence IDs and digests, Subjective reader identity,
configuration/deployment/readiness identity, intent/result/idempotency IDs,
occurrence/finalization times, and post-transfer probe-result identity. It forbids
memory prose, query/prompt/private context, source bodies, filesystem paths,
private IDs, unrestricted lineage, and correlation material. Digesting uses the
existing canonical JSON digest owner and create-or-verify semantics.

Configuration is requested deployment mode and explicit safe locators only.
Startup first reconstructs durable state, then validates the complete config tuple
against it, then permits the reader decision. Missing config defaults to
Primary-only only before intent; partial tuples, config/state disagreement,
configuration-requested Subjective without a finalized receipt, finalized receipt
with wrong generation, and unsupported combinations fail closed. Configuration
alone never selects authority.

Public diagnostics expose only state class, generation-ready boolean, bounded
candidate/selected/exclusion counts, usage-finalized boolean, reader/writer fence
booleans, probe class, recovery-required boolean, and
`runtime_private_evidence_omitted=true`. Logs, receipts, errors, characterization,
and projections forbid prose, raw query/prompt, paths, private handoff, page or
workspace identity, selector/receipt/authorization digests, and private lineage.

Each implementation slice must cover its owned portion of: rehearsal; cache
deletion/rebuild; deterministic selection; usage-before-release; Subjective-only
serving; Primary reader/writer rejection and queue drain; no fallback; empty and
stale projection; malformed durable state; config disagreement; every fault
position; restart/recovery; response-lost idempotency; concurrent transfer/write;
security/leakage; post-transfer probes; retirement negative searches; package
imports; structural spans; and exact-head checks. R4 activation is not authorized
until R1-R3 and their P8 resulting mains are verified. No slice claims runtime
completion before R5 and its mandatory P8 merge.

The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets. This architecture transaction records that no cutover, authority switch, serving, fallback, writer fence, or retirement change occurred.

## RT-1D-R1 completion evidence and mandatory P8 gate

### Identity and inventory

PR #800 architecture authorization completed with result `68cc16b9d5ed7b999c22d27457390e53de851335`. RT-1D-R1 implementation PR #801 used branch `agent/rt1d-r1-durable-preparation` and that exact bootstrap. Commit `c8c65cdf0f49ca5e42c70079ac8034bc96ca28bf` is `feat: add RT-1D-R1 durable preparation`. Corrective commit `ac54854f82bd03c11425efa3014919ec004e72a5` is `test: stabilize unsupported cutover mode validation`, with parent `c8c65cdf0f49ca5e42c70079ac8034bc96ca28bf`. The final head is `ac54854f82bd03c11425efa3014919ec004e72a5` and exact result is `90a3c4f1cedf54e007cf5c0a6a9abc69a30d2acd`.

The exact five-path R1 inventory is +894/-0: `config.example.yaml` +14/-0; `relaylm/config.py` +65/-0; `relaylm/subjective_mem_retrieval_cutover.py` +403/-0; `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py` +99/-0; and `tests/test_subjective_mem_retrieval_cutover.py` +313/-0. A sixth R1 path is invalid.

### Semantic owner, API, and configuration

`relaylm/subjective_mem_retrieval_cutover.py` is the sole semantic owner: 403 physical lines, largest function 46 lines. Its sole operator API is `rehearse_subjective_mem_retrieval_cutover(*, store: EvidenceRecordStore, binding: SubjectiveMemRetrievalCutoverBinding, request: SubjectiveMemRetrievalCutoverRequest) -> SubjectiveMemRetrievalCutoverResult`. Binding, request, diagnostic, and result types are immutable and closed; error identities are stable and canonical encoding/digests deterministic. There is no semantic write API. Dependency direction is cutover owner -> `evidence_store` / `evidence_common` only. `EvidenceRecordStore` does not import the semantic owner and is not semantic authority.

The exact fields are `subjective_mem_retrieval_cutover_mode`, `subjective_mem_retrieval_cutover_store_root`, `subjective_mem_retrieval_cutover_evidence_space_id`, `subjective_mem_retrieval_cutover_deployment_id`, `subjective_mem_retrieval_cutover_scope_id`, `subjective_mem_retrieval_cutover_bootstrap_main_sha`, `subjective_mem_retrieval_cutover_resulting_main_sha`, `subjective_mem_retrieval_cutover_policy_revision_id`, `subjective_mem_retrieval_cutover_projection_generation_id`, `subjective_mem_retrieval_cutover_projection_source_digest`, and `subjective_mem_retrieval_cutover_readiness_id`. Only `primary_only` and `rehearsal` exist. Default `primary_only` has all locators null and rejects a non-empty tuple; `rehearsal` requires the complete tuple. The root must be absolute and safe, identifiers bounded safe tokens, digest fields lowercase SHA-256, and unsupported mode is stably rejected. Configuration requests validation only and is never authority. Loading configuration performs no store access or semantic-owner import.

### State and fail-closed rules

The complete state chain is:

```text
primary_stable
-> rehearsal_ready
-> transfer_intent
-> primary_reader_fenced
-> primary_writer_fenced
-> subjective_generation_bound
-> subjective_reader_enabled
-> transfer_receipt_finalized
-> post_transfer_validated
-> retirement_complete
```

`recovery_required` is derived only; an absent bounded log reconstructs `primary_stable`. Exact predecessor, binding, digest, order, uniqueness, and single-head shape are mandatory. Malformed, skipped, reordered, duplicate, divergent, unsupported, mismatched, tampered, partial, or multiple-chain state fails closed. R1 authorizes Primary-only only for `primary_stable` and `rehearsal_ready`; later complete chains parse, but R1 returns `recovery_required` / neither. Invalid post-intent state never triggers automatic Primary fallback. `rehearsal_ready` is in-memory only. No production semantic record constructor or writer exists.

### Content-free and no-change boundary

Public diagnostics/results expose no paths, memory prose, raw query/prompt, private context/handoff, page/source body, workspace identity, selector/receipt/authorization digests, unrestricted lineage, or arbitrary correlation material. Subjective serving is false, both fences are false, usage-finalized is false, counts are zero, probe is not applicable, and `runtime_private_evidence_omitted=true`. R1 is caller-invoked, default-off, and Primary-only. It adds no ordinary-path wiring; intent, fence, activation, final receipt, usage, or probe record; reader, writer, fallback, queue, worker, scheduler, mutation, API/UI/app, deployment, or retirement change.

Immutable SHA-256 evidence: `relaylm/evidence_store.py` `41cfa9af6c32c1359be04f497924883ffbc4abb4e39313a44755494f92e2b41f`; `relaylm/evidence_common.py` `db03f3cb892bd43159d1b7e11d9d80cc923fd5c2a5c29891eea082c9a5bb7ec0`; `relaylm/subjective_mem_retrieval_selection.py` `13ef7dd7cd652e60db62bcc744c4361db49062c7beedd515b004139d0abe89e9`; `relaylm/subjective_mem_retrieval_usage_ledger.py` `eb2f9196f54a4aecf6ff63cc377df13df9f918881befdb8c59d505b8780a27d9`; `relaylm/managed_chat_pipeline_runtime.py` `382830637cae6c271aa9299510cdd8543f06515a816ffb696696c7321fc84469`; `relaylm/relaymem_retrieval.py` `92f147f0bb834357908b89410324412d7a4e61e396b3c61ce86500deda9f25f3`; `relaylm/relaymem_primary_recall.py` `013da1ec84f472a6207a21176c778803843bb1fc8473fa528e4558d80813adcb`; `relaylm/relaymem_primary_pipeline.py` `5a353151da197e9c43a25d4255f785777b739c2f9040cb517b4f8e2e2aceb22f`.

Focused R1 validation was 38 passed and focused config/store/import validation was 60 passed. R1 smoke, consolidated Subjective lifecycle group, ruff, `py_compile`, `compileall`, diff/path/hash/structure checks, execution guard, and all applicable exact-head workflows passed. There were no reviews, comments, requested reviewers, or unresolved threads.

### Current gate

Mandatory R1 P8 current-authority synchronization PR #802 is current. R2 is next but not started and is non-executable until this P8 merges and its exact resulting main is independently verified. Only that verified resulting main may bootstrap R2; the P8 head may not. Primary remains the sole ordinary served memory and Retrieval authority. Subjective ordinary Retrieval remains disabled and unwired. No cutover intent, fence, activation, final receipt, serving, fallback, writer-authority, or retirement change occurred.
