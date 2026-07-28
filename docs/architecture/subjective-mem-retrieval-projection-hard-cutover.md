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
and deterministic rebuild is complete.

RT-1C shadow adapter, grounding handoff, and usage ledger alone is the next
authorized implementation.

RT-1D hard cutover, Primary retirement, and authority transfer remain
unauthorized and not started.

This section authorizes an implementation budget. It does not claim RT-1C is
implemented, started, or validated; `../PROJECT_STATUS.md` remains the only
current-status authority.

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
  handoff.

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

The bounded path budget for the future RT-1C implementation is:

```text
relaylm/subjective_mem_retrieval_selection.py       exact selection, runtime-private
                                                    handoff, and shadow characterization owner
relaylm/subjective_mem_retrieval_usage_ledger.py    durable content-free usage-event owner
tests/test_subjective_mem_retrieval_selection.py    focused selection, handoff, and
                                                    characterization fixtures
tests/test_subjective_mem_retrieval_usage_ledger.py focused durable idempotency, ordering,
                                                    and finalization-failure fixtures
docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md
```

Selection and durable usage are separate owners with a one-way dependency:
selection is a pure, rebuildable read over one projection generation, while the
usage ledger is durable operations authority that outlives the disposable
projection. Merging them would put a disposable derived read and a durable
non-rebuildable write in one file with two unrelated reasons to change.

The selection owner carries the temporary characterization surface because
shadow characterization is a content-free comparison over two already-bounded
result projections, not a third semantic authority. If P1 finds that
characterization cannot stay bounded inside that owner, return to P1 for an
explicit architecture split rather than silently adding a third production file.

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
substitute for either responsibility name above.

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
- more than two new production responsibility files without an architecture
  split;
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
