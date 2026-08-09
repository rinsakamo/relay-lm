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
  - a planning decision moves into a subsystem contract or architecture authority
relaylm_not_authoritative_for:
  - exact current implementation completion or current PR state
  - exact runtime schemas, algorithms, API fields, or mutation contracts
  - per-lane current authority recorded by Project Status
  - CI workflow syntax or implementation details
  - branch-specific receipts, exact heads, or transaction state
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - ../architecture/system-overview.md
  - ../architecture/pipeline-responsibilities.md
  - ../architecture/current_target_migration_guide.md
relaylm_related_contracts:
  - ../contracts/agent-execution-safety.md
  - ../contracts/documentation-governance.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - project maintainers and release reviewers
  - lane controllers and implementation agents
  - architecture, runtime, memory, evaluation, and documentation maintainers
relaylm_authority_level: sequencing
---
# Project Execution Planning

## Authority summary

This page is the canonical planning authority for **repository-level implementation order, dependency direction, and acceptance layering**.

It preserves the durable sequencing responsibility historically carried by:

```text
docs/architecture/project_execution_plan.md
```

without turning that milestone-oriented source path into the permanent planning location.

This page does not say which phase is currently active, complete, superseded, or retired. Exact implementation state belongs to:

```text
docs/PROJECT_STATUS.md
```

Exact technical behavior belongs to the owning architecture and contracts.

The stable split is:

```text
project-execution.md
  -> dependency and acceptance sequencing

PROJECT_STATUS.md
  -> exact current state and active boundary

architecture / contracts
  -> semantic and exact technical authority
```

## Planning principles

RelayLM work is ordered by dependency and authority rather than by directory order, historical milestone number, or implementation convenience.

The durable principles are:

1. stabilize an interface before widening its execution surface;
2. preserve one semantic owner for every decision or mutation authority;
3. keep visible-response work separate from deferred durable work;
4. keep optional refinement below the ordinary response path unless explicitly authorized;
5. define mutation, idempotency, and recovery before adding automation around them;
6. add scheduling only after queue, worker, and finalization boundaries are bounded;
7. treat browser UI as a consumer of server authority, not an alternate authority;
8. treat evaluation as acceptance evidence, not implementation authority;
9. keep compatibility modes explicit until separately retired;
10. require cumulative evidence before activation or release claims.

## Repository execution spine

The durable repository-level direction is:

```text
contracts and projections
  -> request pipeline wiring
  -> compile / checkpoint / recovery boundaries
  -> memory formation and lifecycle mutation
  -> durable handoff / queue / worker / finalization
  -> retrieval and response grounding
  -> analyzer / relationship / scene / affect integration
  -> operational scheduler layers
  -> management and observation UI
  -> stream safety and voice handoff
  -> value, recovery, and performance evaluation
  -> release acceptance
```

Milestone labels may change. The dependency direction remains the planning authority.

## Contract-first activation

A new behavior should not first discover its contract through an unrestricted live side effect.

The preferred progression is:

```text
schema or responsibility contract
  -> validation / projection
  -> focused evidence
  -> bounded runtime integration
  -> wider activation only after acceptance
```

Dry-run and content-free projection stages are preferred when they allow the behavior to be characterized without creating premature mutation authority.

Exact schemas remain owned by `docs/contracts/`.

## Request pipeline sequencing

Input-side responsibilities are integrated only after their ownership boundaries are stable.

The durable dependency shape is:

```text
validated request / admitted client evidence
  -> relationship policy
  -> scene policy
  -> affect modulation
  -> intent / reference / analyzer inputs
  -> memory retrieval when allowed
  -> context assembly / repack
  -> main-model generation
```

Response-side responsibilities follow generation and must not retroactively become same-turn input authority unless an explicit contract says otherwise.

The canonical pipeline architecture owns the exact component order and exceptions.

## Ordinary response latency boundary

The default planning posture separates response-critical work from durable post-response work:

```text
response-critical processing
  -> first and complete visible response
  -> bounded post-response admission / handoff
  -> deferred formation, maintenance, or evaluation
```

Formation, consolidation, maintenance, and expensive optional analyzers do not move into the first-visible-response path merely because their implementations exist.

A latency optimization may not bypass a semantic or safety owner without a separate accepted authority.

## Durable memory formation sequence

Subjective memory formation is planned as a chain of bounded authorities rather than one broad write helper:

```text
eligible response / evidence
  -> admission decision
  -> durable response handoff
  -> queue record
  -> bounded worker execution
  -> formation / protected-source handling
  -> durable finalization
  -> replay or recovery convergence
```

Each stage must fail closed independently.

A scheduler or service may invoke the chain repeatedly but does not inherit the worker, publication, or memory-write authority owned below it.

## Lifecycle mutation sequence

Correct, Forget/Hide, Pin/Unpin, Held Governance, Restore, Consolidate, and later mutation families remain separately reviewable operations.

Their common planning shape is:

```text
read exact current state
  -> bounded preflight / decision
  -> explicit confirmation or authority when required
  -> mutation under the owning fence / lock
  -> durable receipt and current-state advance
  -> deterministic recovery-safe convergence
```

This common sequence is not permission to collapse different lifecycle operations into one generic mutation authority.

## Retrieval and response grounding sequence

Retrieval follows stable publication and lifecycle boundaries so it can consume authoritative current-state information.

Durable planning requirements are:

- candidate discovery is separate from final adoption;
- lifecycle and current-state eligibility is checked before release;
- provenance and source binding remain explicit;
- unsupported requested detail is suppressed or qualified by the owning grounding policy;
- memory-family cutovers are governed independently from ordinary documentation synthesis;
- a replaced reader or fallback is retired only through its explicit retirement gate.

This page does not name the current reader family; Project Status and the retrieval contracts do.

## Analyzer and classifier sequence

Analyzer-governed features are layered only after shared candidate governance exists.

The stable sequence is:

```text
heuristic / parser / model candidate
  -> bounded normalization
  -> source, confidence, and stability classification
  -> restrictive or separately authorized admission
  -> owning subsystem consumption
```

Individual analyzers may have producer-specific exact contracts.

High confidence by itself never creates broader runtime authority.

## Compile, checkpoint, and recovery sequence

Runtime compile and checkpoint work follows stable component projections.

The planning goal is reconstructible, bounded runtime state before always-on operation.

Durable expectations are:

- compile from canonical component state;
- reject contradictory or malformed projections before backend execution;
- keep request-local and durable state distinct;
- checkpoint only material allowed by the owning contract;
- make recovery idempotent and forward-convergent;
- do not replay an unowned side effect merely because a checkpoint is incomplete.

## Scheduler layering

Operational scheduling is layered after durable queue, worker, finalization, and replay seams exist.

The stable progression is:

```text
one-round aggregation
  -> replay and queue lane adapters
  -> deterministic fairness / pacing policy
  -> cancellation and bounded operational controls
  -> validation hardening
  -> supervised local service
  -> opt-in local process / CLI wrapper
```

A higher layer may decide when to invoke a lower layer again. It may not bypass lower claim, mutation, or finalization authority.

Default-off operation remains the safe planning posture until explicit configuration enables the relevant boundary.

## Management and observation UI sequence

SOUL Lab and related browser surfaces progress from presentation-only work toward real server-owned management surfaces:

```text
browser shell / preview
  -> server read projections
  -> strict browser validation
  -> real conversation transport
  -> lifecycle / operation visibility
  -> explicit preflight / confirmation / apply surfaces
```

The browser remains a consumer. It must not become the owner of memory stores, durable lifecycle truth, scheduler processes, protected source, credentials, or server mutation locks.

## Streaming and voice sequence

Voice integration follows the same layered authority pattern:

```text
backend stream
  -> visible / internal stream safety
  -> safe-visible segmentation
  -> adapter handoff planning
  -> transport envelope
  -> optional concrete synthesis / playback under a separate execution authority
```

A downstream voice component must not bypass stream-safety ownership by re-reading raw backend output as an alternate disclosure source.

Segmentation and handoff metadata are not proof that synthesis, audio generation, playback, or avatar control occurred.

## Evaluation sequencing

Evaluation begins after the measured boundary has a stable implementation or contract.

Useful evidence families include:

- exact-contract and integration smokes;
- cross-slice convergence checks;
- memory value scenarios;
- restart and recovery scenarios;
- security and privacy negative tests;
- retrieval-scaling methods;
- perceived-latency measurements.

Evaluation material must distinguish:

```text
method or template
measured evidence
current implementation authority
```

A template is not evidence. A measured result does not silently redefine runtime semantics.

## Release acceptance layering

A release boundary is cumulative.

The durable acceptance shape is:

1. focused contract and integration evidence is green;
2. cross-slice convergence evidence is green;
3. documentation links and current-boundary semantics are green;
4. security and privacy boundaries remain intact;
5. default-off and fail-closed behavior remains intact where required;
6. Project Status accurately records current implementation truth;
7. value-oriented scenarios establish usefulness as well as syntactic correctness;
8. no known blocking regression remains inside the release evidence budget.

Exact release tags and receipts remain separately governed evidence.

## One-authority rule

A recurring repository invariant is:

```text
one semantic responsibility
  -> one current authority
```

Implementation helpers may be split for size or maintainability, but the split may not create independent decision owners for the same semantic boundary.

This matters especially for:

- reader and writer cutovers;
- current-state mutation;
- durable finalization;
- scene and relationship policy;
- scheduler lifecycle;
- browser/server management state.

## Parallelism and lane interaction

Parallel work is permitted only when ownership and write surfaces are demonstrably independent.

The durable rule is:

```text
disjoint authority + disjoint write surface
  -> parallel work may proceed

shared authority, shared current-status owner, or ambiguous overlap
  -> serialize
```

When another lane advances `main`, an in-flight transaction must re-evaluate its exact bootstrap and semantic overlap before merge. Reuse of a stale bootstrap is not justified merely because the file-level diff still applies cleanly.

The exact re-bootstrap mechanics belong to the execution-safety contract and ADR authority, not this planning page.

## Bounded transaction rule

Repository-changing work should remain one reviewable responsibility whenever practical.

A bounded transaction identifies:

- exact bootstrap/current authority;
- one logical writer;
- intended path and responsibility scope;
- required evidence;
- return/failure condition;
- acceptance and merge gate.

This makes later provenance, migration, rollback reasoning, and retirement tractable.

## Evidence before activation

A feature may exist in code before it is authorized as the ordinary path.

For high-risk authority changes, the durable sequence is:

```text
implementation
  -> bounded proof / rehearsal / comparison
  -> readiness decision
  -> activation
  -> post-transfer validation
  -> retirement of replaced authority
```

The exact current stage is recorded by its owning status and cutover authority.

This page owns only the ordering principle.

## Compatibility and retirement

Compatibility behavior is not permanent merely because it survived a migration.

Retirement requires explicit proof that:

- the replacement owns the required behavior;
- active consumers have migrated;
- historical evidence remains interpretable;
- fallback does not silently retain ordinary authority;
- deletion or retention disposition is explicit.

A retirement decision is a separate responsibility from creating the replacement unless provenance, consumer migration, and disposition are deliberately included in one bounded transaction.

## Documentation cutover sequence

Documentation restructuring follows the same authority discipline:

```text
inventory
  -> classify stable responsibility
  -> synthesize permanent architecture / contract / reference / planning pages
  -> validate current boundaries
  -> migrate active consumers
  -> retire transitional source separately
```

Milestone and phase filenames remain provenance, not preferred permanent semantic names.

Creating a canonical destination does not itself authorize deletion of its source.

## Current-status handoff

This planning page must never be used to infer whether a named phase is currently pending, active, complete, superseded, or retired.

For current state, read:

```text
docs/PROJECT_STATUS.md
```

Then follow its linked current architecture, contracts, and evidence.

## Source-retirement boundary

This canonicalization does not retire:

```text
docs/architecture/project_execution_plan.md
```

That source remains available until a separate bounded migration/retirement transaction proves provenance, consumer migration, replacement validation, and final disposition.
