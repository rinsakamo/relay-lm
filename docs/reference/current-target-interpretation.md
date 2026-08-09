---
relaylm_doc_type: reference
relaylm_authority: current_target_migration_and_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - current/target authority precedence changes
  - compatibility or migration interpretation rules change
  - a cutover changes how older implementation or architecture sources must be read
  - scene or memory target scope becomes current and changes interpretation guidance
relaylm_not_authoritative_for:
  - exact current repository implementation status or active transaction state
  - exact runtime schemas, algorithms, APIs, gates, or mutation contracts
  - exact reader/writer cutover state or retirement approval
  - repository execution sequencing
  - target scene-aware ranking or future memory-scope implementation details
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../planning/project-execution.md
  - ../architecture/memory/system.md
  - ../architecture/memory/scene-memory-scope.md
  - ../architecture/current_target_migration_guide.md
  - ../architecture/relaymem_slp_current_target.md
  - ../architecture/scene_memory_scope_current_target.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - maintainers interpreting current versus target documentation
  - migration and compatibility reviewers
  - AI coding agents resolving apparently conflicting RelayLM sources
  - memory, scene, runtime, and documentation maintainers
relaylm_authority_level: lookup
---
# Current / Target / Migration Interpretation

## Authority summary

This reference explains **how to read RelayLM current, target, compatibility, migration, and historical material without turning an older completion record or future design into live authority**.

It is a lookup and interpretation aid. It does not maintain a second list of what is implemented today.

For exact current repository state, read:

```text
docs/PROJECT_STATUS.md
```

For durable implementation order, read:

```text
docs/planning/project-execution.md
```

For subsystem meaning and ownership, follow canonical architecture. For exact fields, gates, APIs, states, and must/must-not behavior, follow canonical contracts.

## Why this reference exists

RelayLM has accumulated several generations of implementation plans, compatibility surfaces, migration documents, completion evidence, target designs, and hard cutovers.

Without an interpretation rule, a reader can make unsafe inferences such as:

- a completed old path must still be the ordinary active path;
- a target architecture must already be implemented;
- an old fallback remains authorized because its tests still exist;
- a compatibility reader and its replacement can both serve one request;
- scene metadata can widen memory authority because a future design mentions scene-aware retrieval;
- a source document remains authoritative merely because it still exists in the repository.

The stable correction is:

```text
existence != current authority
completion history != current authority
accepted target != implemented state
compatibility != co-authority
migration evidence != activation permission
```

## Reading precedence

When two documents appear to disagree, use this precedence by responsibility rather than choosing the newest prose indiscriminately.

| Question | Primary authority |
|---|---|
| What is implemented now? | `docs/PROJECT_STATUS.md` |
| What is the durable repository execution order? | `docs/planning/project-execution.md` |
| What does a subsystem own? | canonical `docs/architecture/**` page for that responsibility |
| What exact schema/gate/API/state is normative? | canonical `docs/contracts/**` owner |
| What decision was accepted and why? | owning ADR |
| What happened in a completed PR/run/wave? | evidence, retained records, Git and PR history |
| What might be implemented later? | target architecture/planning/concept authority, never status by implication |

A lower row cannot silently override an authority in a higher row for a different responsibility.

For example, historical evidence can prove that a capability once shipped. It cannot prove that the capability remains the ordinary serving authority after a later cutover.

## `current` does not mean repository-wide status

A document with:

```yaml
relaylm_status: current
```

is current **for its declared authority**, not for every implementation claim mentioned in its body.

Examples:

- a current concept-policy page may define stable semantics while an implementation detail remains absent;
- a current contract may define one exact boundary without claiming the whole subsystem is active;
- a current reference may explain interpretation rules while delegating actual completion state to Project Status.

Always read `relaylm_authority` and `relaylm_not_authoritative_for` together with `relaylm_status`.

## `target` means adopted direction, not implementation

A target document records an accepted future or migration direction within its declared authority.

The safe rule is:

```text
target design
  + no matching current-status/runtime evidence
  -> treat as not yet implemented
```

Do not infer implementation from:

- detailed schemas in a target design;
- sample pseudocode;
- an accepted ADR alone;
- a completed prerequisite;
- a source filename containing `current_target`;
- an old roadmap entry saying a later slice is next.

Implementation becomes current only through the owning implementation/current-status evidence chain.

## Compatibility means bounded survival, not dual authority

A compatibility surface exists so a migration can preserve a bounded consumer or historical behavior while authority moves elsewhere.

Compatibility must be interpreted narrowly:

```text
explicit compatibility purpose
  -> allowed only inside its current owning gate
  -> no authority outside that gate
  -> no automatic fallback after replacement
```

The continued presence of compatibility code, tests, schemas, history views, or read-only projections does not establish an ordinary read or write path.

A surviving read-only administrative/history surface is especially not proof that the retired ordinary producer or reader still exists.

## Hard cutover interpretation

A hard cutover changes the authority graph, not merely the preferred code path.

After the owning cutover reaches a new current state:

- older completion evidence remains true as history;
- older implementation descriptions must be read through the new authority boundary;
- a replaced ordinary reader/writer/fallback does not remain available unless the new current authority explicitly preserves it;
- an empty, failed, or unavailable replacement result does not resurrect the old authority unless a current contract explicitly defines that fallback;
- retained read-only history/observation surfaces do not recreate mutation or serving authority.

The exact current cutover state must be read from Project Status and the owning cutover contract/architecture, not reconstructed from this reference.

## One-authority interpretation for migrated responsibilities

Migration prose frequently describes both the old and replacement systems in one document. That does not imply simultaneous authority.

The safe interpretation is:

```text
old implementation capability
  + replacement implementation capability
  + explicit cutover authority
  -> follow the cutover authority first
```

If the cutover selects exactly one active family, the other family may remain as:

- historical evidence;
- compatibility evidence;
- read-only administration;
- migration/recovery evidence;
- code awaiting later retirement.

None of those roles independently creates a second ordinary authority.

## Reader authority and candidate narrowing are different

Memory and scene documents often mention route, character, namespace, scene, relationship, intent, source, lifecycle, or generation metadata.

These inputs can have very different roles.

The stable distinction is:

```text
reader authority
  -> decides which memory family may be consulted

scope / lifecycle / scene / intent / provenance filters
  -> may narrow evidence inside an already-authorized family
```

A narrowing signal must not be interpreted as permission to:

- select a different memory family;
- broaden scope after a miss;
- combine old and replacement families;
- restore a retired fallback;
- authorize a write.

Exact current reader selection belongs to the owning retrieval/cutover authority.

## Writer authority and capability history are different

An implemented worker, lifecycle operation, UI route, recovery path, or historical token proves a capability existed. It does not prove that the capability currently has write authority.

The safe interpretation is:

```text
implemented mutation path
  + current writer fence/decision denies mutation
  -> mutation is not currently authorized through that path
```

Historical completion, a stale receipt, a previously valid token, or an old recovery path cannot override a newer current writer fence.

This rule applies even when the old code remains useful for regression, history, compatibility, or retirement evidence.

## Scene-aware memory scope: current versus target

The canonical durable policy for scene-aware memory scope lives in:

```text
docs/architecture/memory/scene-memory-scope.md
```

That policy establishes a key interpretation rule:

```text
scene information narrows already-authorized memory behavior
scene information does not create memory authority
```

Future or target scene-aware ranking may add governed dimensions such as relationship, scene, session, room, or audience context.

Until the owning current runtime/status authority says those dimensions are implemented, their appearance in target design must not be interpreted as live ranking behavior.

Likewise, a classifier or scene-wiki match does not by itself authorize memory retrieval, disclosure, persistence, or cross-family fallback.

## Missing target dimensions fail conservatively

A target architecture may define optional future scope dimensions that current runtime does not yet consume.

The interpretation rule is:

```text
missing implementation of a target dimension
  -> dimension is unavailable
  -> do not pretend it was evaluated
  -> do not broaden authority to compensate
```

Unknown is not equivalent to unrestricted.

A report or diagnostic should distinguish unimplemented/unknown from zero, empty, or explicitly allowed where that distinction matters.

## Current capability inventory belongs elsewhere

Legacy `current_target` sources often contain long milestone lists such as:

```text
slice A complete
slice B complete
slice C current
slice D pending
```

Those lists become stale whenever another lane advances.

They are not copied into this canonical reference.

Current completion belongs to Project Status. Durable responsibility belongs to architecture/contracts. Durable ordering belongs to planning. Historical completion remains in evidence and Git history.

This separation prevents a reference page from becoming a second high-churn status authority.

## Accepted target invariants may survive implementation changes

Some target invariants remain useful even after specific migration steps land.

Examples of durable interpretation patterns include:

- visible conversation should not wait for deferred durable formation merely because the formation path exists;
- candidate generation does not equal final adoption authority;
- retrieval remains read-only unless another explicit owner authorizes mutation;
- protected source and provenance do not become public diagnostics merely because a later consumer can use them;
- optional optimization does not replace the fail-closed reference path without equivalence evidence;
- a scheduler invokes lower authorities but does not inherit their mutation semantics;
- UI controls expose server-owned authority rather than minting authority in the browser.

The owning canonical architecture/contracts remain normative for each pattern. This reference explains how to interpret them across migration generations.

## Completion evidence after supersession

A completion report, merged PR, smoke, or evaluation can remain valid evidence after the implemented surface is superseded.

What changes is the conclusion a reader may draw from it.

Safe interpretation:

```text
old evidence proves:
  the old boundary existed and passed its stated checks at that commit

old evidence does not prove:
  the boundary remains current after a later authority change
```

Do not rewrite accurate historical evidence merely to make it sound current. Instead, use current authority to interpret it.

## Historical terminology after canonicalization

Milestone names such as Phase, Wave, ACG, CW, O1, E1-R, PM-D, LC, or RT identifiers can remain in evidence and Git history.

They are provenance labels, not preferred permanent semantic names.

When looking for current authority, navigate from stable responsibility names such as:

- memory formation;
- retrieval and grounding;
- mutation governance;
- scene-aware memory scope;
- scheduler;
- request/response pipeline;
- current-target interpretation;
- project execution planning.

A milestone-named source may still be useful context but should not outrank its canonical replacement.

## Migration documents are interpretation aids, not deletion authority

A source may clearly describe that another authority has replaced it and still remain present in the tree.

That does not mean the source can be deleted casually.

Canonicalization and retirement are separate responsibilities:

```text
canonical destination created and validated
  != source retirement complete
```

Retirement additionally requires its own provenance, consumer migration, link/workflow/validator repair, and disposition proof under documentation governance.

This reference therefore does not retire any of its source documents.

## How to resolve an apparent contradiction

When a reader finds two statements that appear incompatible, use this sequence:

1. Identify the responsibility in dispute: status, sequencing, architecture, exact contract, evidence, or target direction.
2. Read each document's front matter, especially authority, status, and non-authoritative fields.
3. Read Project Status if the dispute includes a claim about what is implemented now.
4. Follow canonical architecture for the responsibility rather than a milestone source.
5. Follow the exact contract for schema/gate/state/API details.
6. Check whether a later cutover or retirement changed the authority graph.
7. Treat historical evidence as commit-bounded proof, not a current override.
8. Treat target design as unimplemented unless current authority proves otherwise.
9. If two live canonical authorities truly claim the same responsibility, stop: that is an authority conflict, not something to reconcile by guessing.

## Examples of unsafe inference

### Unsafe: source exists, therefore path is live

```text
legacy reader module or document exists
therefore ordinary requests may still use it
```

Wrong. The current cutover/serving authority decides whether it is live.

### Unsafe: target schema is detailed, therefore runtime emits it

```text
target document defines scene/session/room fields
therefore current retrieval ranks on all of them
```

Wrong. Target detail is not implementation evidence.

### Unsafe: compatibility result was successful, therefore it may fallback

```text
old compatibility path can still succeed
therefore replacement failure may fallback to it
```

Wrong unless a current exact contract explicitly authorizes that fallback.

### Unsafe: UI route exists, therefore mutation is authorized

```text
management UI has an Apply button
therefore current writer authority permits the operation
```

Wrong. The server-side preflight/fence/current-state owner remains authoritative.

### Unsafe: historical test still passes, therefore historical authority is current

```text
regression test proves old behavior
therefore old behavior is current serving policy
```

Wrong. Regression evidence can survive supersession.

## Minimal lookup checklist

Before implementing or documenting a change based on older RelayLM material, answer:

```text
1. What exact responsibility am I changing?
2. What does PROJECT_STATUS say is current?
3. What permanent architecture page owns the responsibility?
4. Is there an exact contract?
5. Is the source I am reading current, target, compatibility, or evidence?
6. Did a later cutover narrow or replace its authority?
7. Am I interpreting a narrowing signal as broader authority?
8. Am I treating historical completion as current permission?
9. Am I copying volatile status into a stable reference?
10. Would my change create two live authorities?
```

If item 10 is yes or unclear, the work must not proceed as a routine synthesis.

## Source synthesis boundary

This reference synthesizes the durable interpretation responsibility previously spread across:

```text
docs/architecture/current_target_migration_guide.md
docs/architecture/relaymem_slp_current_target.md
docs/architecture/scene_memory_scope_current_target.md
```

It intentionally does **not** copy their volatile milestone completion inventories or pre-cutover current-state statements.

Their stable memory topology now belongs to `docs/architecture/memory/system.md`; stable scene-aware memory policy belongs to `docs/architecture/memory/scene-memory-scope.md`; current implementation truth belongs to `docs/PROJECT_STATUS.md`; repository sequencing belongs to `docs/planning/project-execution.md`.

## Source-retirement boundary

No source is retired by this canonicalization.

The three transitional sources remain in place until a separate bounded documentation-retirement transaction proves exact provenance, active-consumer migration, link/validator/workflow repair, and final disposition.
