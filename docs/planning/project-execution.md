---
relaylm_doc_type: planning
relaylm_authority: project_execution_sequence_and_acceptance_planning
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: project_governance
relaylm_update_trigger:
  - repository execution phases or acceptance gates change
  - a new implementation lane changes dependency order
  - release acceptance or evidence requirements change
  - a planning decision moves from milestone sequencing into a subsystem contract or architecture authority
relaylm_not_authoritative_for:
  - exact current implementation completion or current PR state
  - exact runtime schemas, algorithms, API fields, or mutation contracts
  - per-lane current authority recorded by Project Status
  - CI implementation details or workflow-file syntax
  - branch-specific execution receipts or transaction state
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - ../architecture/system-overview.md
  - ../architecture/pipeline-responsibilities.md
  - ../reference/current-target-interpretation.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - project maintainers and release reviewers
  - lane controllers and implementation agents
  - architecture, runtime, memory, evaluation, and documentation maintainers
relaylm_authority_level: planning
---
# Project Execution Planning

## Purpose

This document is the canonical planning authority for **how RelayLM implementation work is sequenced and accepted at repository level**.

It preserves the durable execution logic from the pre-canonical source:

```text
docs/architecture/project_execution_plan.md
```

without treating that milestone-named architecture path as the permanent planning location.

This page does **not** say which phase is currently complete. Current implementation state, active PRs, and the next authorized transaction remain owned by:

```text
docs/PROJECT_STATUS.md
```

The rule is:

```text
this page
  -> durable dependency and acceptance planning

Project Status
  -> exact current completion and active work

subsystem architecture/contracts
  -> exact technical authority
```

## Planning principles

RelayLM work is sequenced by dependency and authority, not by directory order or convenience.

Stable planning principles are:

1. stabilize interfaces before widening execution;
2. preserve one owner for every semantic authority;
3. separate visible response latency from deferred durable work;
4. keep optional refinement below the ordinary response path;
5. make mutation and recovery behavior explicit before automation;
6. add operational scheduling only after queue/worker/finalization boundaries are bounded;
7. treat UI as a consumer of server authority, never as an alternate runtime authority;
8. treat evaluation as acceptance evidence, not as a replacement implementation path;
9. keep compatibility modes explicit until their retirement is separately authorized;
10. require evidence before a milestone becomes release authority.

## Repository execution shape

The durable implementation direction is:

```text
contract and projection stability
  -> Core request pipeline wiring
  -> safe runtime compile/checkpoint boundaries
  -> memory formation and mutation foundations
  -> queue/worker/finalization durability
  -> retrieval and response grounding
  -> analyzer/scene/relationship/emotion integration
  -> local scheduling and operational hardening
  -> management and observation UI
  -> streaming / voice transport boundaries
  -> value and performance evaluation
  -> release acceptance
```

Milestone labels may change over time. The dependency direction above is the continuing planning authority.

## Phase 0 — contract and projection foundations

The original execution plan began with bounded contracts and dry-run/projection-first seams before broad runtime integration.

The durable requirement remains:

```text
schema / contract
  -> validation / projection
  -> focused evidence
  -> runtime integration
```

A subsystem should not first discover its contract by exposing an unrestricted live side effect.

Typical foundational responsibilities include:

- relationship, scene, and affect projections;
- context packing and update boundaries;
- structured analyzer candidates;
- runtime result/projection contracts;
- memory job/queue/worker records;
- content-free diagnostics;
- source/character scope resolution.

Exact schemas are owned by their subsystem contracts, not by this planning page.

## Phase 1 — request pipeline wiring

Once component boundaries are stable, they are wired into the request path in dependency order.

The stable input-side ordering principle is:

```text
validated request/client evidence
  -> relationship
  -> scene
  -> affect
  -> intent/reference/analyzer input
  -> memory retrieval when allowed
  -> context repack
  -> main model generation
```

Response-side responsibilities follow generation and must not retroactively become input authority for the same turn.

This planning page does not freeze the exact implementation function call graph; the canonical pipeline architecture owns that detail.

## Ordinary response latency boundary

Ordinary conversation must keep user-visible response generation separate from deferred durable formation work.

The durable planning rule is:

```text
response-critical work
  -> complete visible response
  -> bounded post-response admission/handoff
  -> deferred durable formation / maintenance
```

Optional analyzers, formation, consolidation, evaluation, and maintenance should not be inserted into the first visible response path merely because they are available.

Any exception requires an explicit architecture/contract authority.

## Memory formation sequence

Durable Subjective MEM formation is planned as a staged authority chain rather than a single write helper.

The durable conceptual sequence is:

```text
eligible response/evidence
  -> job admission
  -> durable handoff/queue
  -> bounded worker execution
  -> protected-source / formation logic
  -> durable finalization
  -> replay/recovery convergence
```

Each stage must be independently fail-closed.

A higher scheduler or service may invoke the chain but does not inherit lower semantic write authority.

## Memory mutation sequence

Correct, Forget/Hide, Pin/Unpin, Held Governance, restore/recovery, and later mutation families require separate operation contracts.

The planning requirements are:

```text
read current canonical state
  -> bounded preflight / decision
  -> explicit authority / confirmation when required
  -> mutation under owning lock/fence
  -> durable receipt / current-state update
  -> recovery-safe convergence
```

Mutation families are not merged into one generic command merely to simplify UI or scheduling.

## Retrieval and response grounding

Retrieval work follows formation/mutation foundations so that read behavior can consume stable lifecycle and authority state.

Durable planning requirements are:

- candidate discovery remains separate from final adoption;
- lifecycle/current-state eligibility is checked before release;
- source/provenance remains explicit;
- unsupported requested detail fails closed or is qualified by the owning response-grounding policy;
- exact reader-family cutovers are governed independently from architecture documentation work.

The exact current reader authority remains outside this planning page.

## Analyzer and classifier integration

Analyzer-governed features are introduced only after the common candidate-governance boundary exists.

The stable direction is:

```text
untrusted / heuristic / model candidate
  -> bounded normalization
  -> confidence / stability / source classification
  -> restrictive or separately authorized policy admission
  -> owning subsystem consumption
```

Individual analyzers may have exact producer-specific contracts.

No analyzer gains broad runtime authority solely because its confidence is high.

## Runtime compile and checkpoint sequence

Runtime compile/checkpoint work follows stable component projections.

The planning goal is to make runtime state reconstructible and bounded before adding always-on operation.

Durable expectations include:

- compile from canonical component state;
- reject malformed or contradictory projections before backend execution;
- keep request-local and durable state distinct;
- checkpoint only the data the owning runtime contract allows;
- recover without replaying unowned side effects.

## Scheduler and local operation sequence

Operational scheduling is layered after durable queue/worker/replay seams exist.

The durable layering is:

```text
pure one-round aggregation
  -> replay and queue lane adapters
  -> deterministic policy / pacing
  -> cancellation and bounded operational controls
  -> validation hardening
  -> supervised local service
  -> opt-in local process / CLI
```

A higher layer may decide when to call the lower layer again but must not bypass its lower mutation/claim/finalization authority.

Default-off operation remains the safe planning posture until explicit configuration enables the relevant lower gates.

## UI sequence

SOUL Lab evolves from local mock/projection work toward real server-owned management and observation surfaces.

The stable progression is:

```text
browser shell / preview
  -> server read projections
  -> exact-key browser validation
  -> real conversation transport
  -> lifecycle / operation visibility
  -> explicit mutation preflight/apply surfaces
```

The browser may improve usability but must not become the owner of:

- memory stores;
- route/backend selection beyond server projections;
- mutation locks/tokens except bounded same-origin confirmation artifacts;
- scheduler processes;
- credentials;
- protected source;
- durable lifecycle truth.

## Streaming and voice sequence

Voice/streaming integration follows the same authority layering:

```text
backend stream
  -> visible/internal stream safety
  -> safe-visible segmentation
  -> adapter handoff planning
  -> transport envelope
  -> optional concrete TTS/audio execution under a separate authority
```

A downstream voice component must not recover internal/suppressed material from the raw backend stream as an alternate disclosure path.

## Evaluation sequence

Evaluation is introduced after the behavior being measured has a stable implementation boundary.

Stable evaluation families include:

- contract and integration smoke evidence;
- cross-slice convergence evidence;
- memory value scenarios;
- retrieval-scaling methods;
- perceived-latency measurements;
- restart/recovery scenarios;
- security and privacy negative tests.

Evaluation documents must distinguish:

```text
method / template
measured evidence
current implementation authority
```

A template is not evidence, and a passing evaluation does not silently redefine runtime semantics.

## Release acceptance

A release milestone requires cumulative acceptance rather than one demonstration path.

The durable acceptance shape is:

1. focused exact-contract evidence is green;
2. cross-slice convergence evidence is green;
3. documentation links/current-boundary checks are green;
4. security/privacy boundaries are preserved;
5. default-off / fail-closed behavior is preserved where required;
6. current implementation state is accurately recorded by Project Status;
7. value-oriented scenarios show the feature is useful, not merely syntactically correct;
8. no known blocking regression remains in the release evidence budget.

Exact release receipts and tags remain separate evidence/current-status authority.

## Parallelism rule

Parallel implementation is allowed only for work whose ownership and write surfaces do not conflict.

Durable rule:

```text
parallel independent producers
  -> permitted when authorities and paths are disjoint

shared authority / same mutation surface / same current-status owner
  -> serialize
```

When uncertainty exists, serialization is preferred over speculative concurrent writers.

## One-authority rule

A recurring repository planning invariant is:

```text
one semantic responsibility
  -> one current authority
```

Implementation helpers may be split for size and maintainability, but a split must not create two independent sources of truth for the same decision.

This applies especially to:

- memory reader/writer cutovers;
- current-state mutation;
- durable finalization;
- scheduler lifecycle;
- scene authority;
- browser/server management state.

## Transaction rule

Repository-changing work should remain bounded to one reviewable responsibility whenever practical.

A bounded transaction should make explicit:

- exact bootstrap/current authority;
- one logical writer;
- intended production/documentation scope;
- expected evidence;
- failure/return condition;
- merge/acceptance gate.

This planning principle reduces authority drift and makes later retirement/provenance work possible.

## Evidence before activation

A feature may exist in code without yet being authorized as the ordinary active path.

The durable sequence for high-risk cutovers is:

```text
implementation
  -> bounded proof / rehearsal / comparison
  -> readiness decision
  -> activation
  -> post-transfer validation
  -> retirement of replaced authority
```

The exact current cutover state belongs to its owning contract and Project Status.

This page only preserves the sequencing principle.

## Compatibility and retirement

A compatibility path is not permanent merely because it survives a migration.

Retirement requires a separate decision that proves:

- the replacement owns the required behavior;
- active consumers have migrated;
- historical evidence remains interpretable;
- no fallback path silently retains ordinary authority;
- deletion/retention disposition is explicit.

Documentation source retirement follows the same principle: canonicalization and source deletion are separate transactions unless provenance and consumer migration are explicitly included in one bounded authority.

## Documentation sequencing

Documentation restructuring itself follows:

```text
inventory
  -> classify stable authority
  -> synthesize permanent architecture/reference/planning/strategy pages
  -> rebuild exact contracts from normative blocks
  -> validate current boundaries
  -> migrate active consumers
  -> retire transitional sources separately
```

Milestone/phase filenames are provenance, not preferred permanent semantic names.

The current canonical documentation graph should describe responsibility rather than implementation chronology.

## Current status handoff

This planning page must not be used to infer whether a named phase is currently pending, active, complete, superseded, or retired.

For that question, use:

```text
docs/PROJECT_STATUS.md
```

then follow its linked current architecture/contracts/evidence.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/project_execution_plan.md
```

The legacy source remains available until a separate provenance/consumer/migration transaction explicitly authorizes retirement.
