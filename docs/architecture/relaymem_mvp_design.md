# RelayMEM MVP Design

## Purpose

RelayMEM is RelayLM's long-term memory subsystem.

It is not a simple RAG cache and it is not the owner of all memory-related decisions. The subsystem is split into:

```text
RelayMEM storage/index
  durable formed memory records and compiled pages

RelayMEM Retrieval
  synchronous read-only selection for the current answer

RelaySLP
  deferred autonomous ordinary memory formation, update, hold, reject, and proposal workflow
```

Current implementation phase and sequencing live in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md). Memory lifecycle semantics live in [Memory Lifecycle Design](memory_lifecycle_design.md).

## Core principle

```text
Retrieval improves the current answer.
RelaySLP improves future memory.
```

Retrieval only reads. RelaySLP may produce or apply governed memory changes through explicit gates.

Ordinary MEM formation is autonomous by default. User approval is not required for every ordinary memory update. Review and approval scopes are exception paths for sensitive, destructive, identity-level, low-confidence, contradictory, cross-namespace, or SOUL-affecting changes.

RelayMEM should represent formed experience, not a per-turn user approval queue.

## Relation to other components

### RelaySOUL

Owns durable identity, values, worldview, approved output/relationship policy, revision, approval, and rollback.

RelayMEM does not directly mutate RelaySOUL. RelaySLP may emit a proposal candidate that enters the separate RelaySOUL approval path.

### RelaySCN

Owns scene, memory-scope, recovery, and persistence policy. RelayMEM consumes the resolved policy.

### RelayINT

Owns whether long-term retrieval is needed and whether a reference scope is explicit or confirmed.

### RelayCTX

Owns final prompt packing and token-budget degradation. RelayMEM returns candidates/evidence; RelayCTX selects final placement.

### RelayREF

RelayREF is the post-generation output observer. It is not part of RelayMEM or RelaySLP and does not guide same-turn Retrieval.

### RelaySLP

Owns deferred candidate extraction, memory compilation, safety classification, merge/update/hold/reject decisions, lint, and proposal generation.

## Storage model

The MVP remains local-first and file-backed.

```text
memory/
  raw/
    conversations/
    docs/
    events/

  mem/
    index.md
    log.md
    projects/
    concepts/
    claims/
    summaries/
    relations/
      graph.json
```

### `raw_sources`

Primary governed evidence. Raw sources remain separate from compiled summaries and must not be silently overwritten.

Examples:

- approved conversation/event records,
- document evidence,
- explicit user memory requests,
- protected CTX/INT/SCN artifacts when policy allows,
- source references and lineage.

Raw evidence is not automatically eligible for runtime prompt packing.

### `mem_pages`

Compiled memory pages used for normal retrieval:

- project state,
- concept definitions,
- claims,
- session summaries,
- approved preferences,
- relations.

Compiled pages retain source references and approval/safety metadata.

### `mem_index`

A bounded retrieval index containing:

- page IDs,
- aliases/tags,
- summaries,
- relation hints,
- scope and safety metadata,
- update/version metadata.

A vector database is optional future infrastructure, not the component definition.

### `mem_log`

Append-only memory-operation evidence for RelaySLP decisions and store maintenance.

The memory log is distinct from the default runtime trace. It may contain approved page IDs and lineage references, but must not become a generic dump of raw user messages or runtime-private prompt artifacts.

## Memory kinds

Recommended initial kinds:

```text
raw_event
session_summary
project_state
concept
claim
preference
relation
soul_candidate
rejected_or_blocked_candidate
```

A `soul_candidate` remains a candidate. It is not a RelaySOUL revision or approval.

## Safety scopes

Safety scopes classify memory-operation risk. They must not be interpreted as a universal requirement that the user approve every memory candidate.

### `free_to_update`

May be applied by RelaySLP only when:

- the SLP apply gate is enabled,
- RelaySCN persistence policy allows it,
- source lineage is present,
- confidence/stability requirements pass,
- the update is idempotent.

Examples may include non-sensitive project notes, concept-page maintenance, ordinary session summaries, and low-risk relationship continuity details.

### `review_required`

Held for later user/operator review or Lab correction. This is an exception path, not the normal memory path.

Examples:

- durable workflow preferences,
- major project-direction changes,
- ambiguous long-term facts,
- user-disputed memories,
- unresolved contradictions.

### `explicit_approval_required`

Converted into an approval artifact or RelaySOUL proposal candidate. Never auto-applied.

Examples:

- SOUL-level identity/value/relationship-anchor changes,
- sensitive personal facts,
- destructive memory deletion,
- cross-namespace memory movement,
- pin/unpin operations that materially change retrieval priority.

### `never_auto_promote`

Rejected, held as blocked evidence, or retained only under a protected source policy.

Examples:

- raw affect estimates,
- sensitive attribute inference,
- transient emotional interpretation,
- low-confidence personal inference.

## Retrieval path

```text
RelaySCN memory scope
  + RelayINT retrieval decision and confirmed scope
  -> index search
  -> approved candidate pages
  -> safety/authority filter
  -> bounded runtime-private evidence
  -> RelayCTX final packing
```

Retrieval must not:

- write pages or index entries,
- mutate RelaySOUL,
- silently resolve ambiguous references,
- broaden scope after a miss,
- expose snippets/paths through default trace projections.

## RelaySLP path

```text
governed source evidence
  -> candidate extraction
  -> memory_kind classification
  -> safety_scope classification
  -> existing-page lookup
  -> merge / update / hold / reject
  -> relation typing
  -> lint
  -> gated page/index/log update
  -> optional RelaySOUL proposal candidate
```

RelaySLP runs outside the latency-critical normal response path and never produces the current answer directly.

For ordinary safe memory, `merge` or `update` may be autonomous when all gates pass. `hold`, `reject`, and `proposal` paths preserve operator control for uncertain, sensitive, contradictory, or identity-affecting changes.

## Relation model

Useful typed relations include:

```text
supports
contradicts
refines
supersedes
depends_on
part_of
example_of
risk_for
derived_from
candidate_for_soul
blocked_from_soul
```

Untyped `related` links should not be the only relation form.

## Runtime-private versus content-free artifacts

### Runtime-private memory artifacts

May contain:

- candidate title/summary/snippet,
- page/source references,
- resolved query text,
- proposed page updates,
- relation values,
- blocked candidate details.

These remain request-local, SLP-local, or protected by the memory store's explicit access and retention policy.

### Default runtime trace projections

Contain only typed allowlisted metadata:

- candidate/selected/blocked counts,
- source and scope classes,
- confidence/stability bands,
- budget values,
- reason identifiers,
- apply state,
- page-update counts,
- payload/persistence booleans.

They must not contain raw messages, memory bodies, snippets, local paths, semantic scene/intent text, or final responses.

## Persistence rules

1. Retrieval only reads.
2. RelaySLP is the only memory compiler/apply owner.
3. Ordinary `free_to_update` MEM formation may apply autonomously only when all SLP, RelaySCN, lineage, confidence, namespace, and idempotency gates pass.
4. `review_required` is held for later Lab/operator review or correction.
5. `explicit_approval_required` becomes an approval/proposal artifact.
6. RelaySOUL is never directly mutated by RelayMEM.
7. Raw evidence is preserved separately from compiled pages.
8. Contradictory, stale, blocked, or unapproved records stay out of normal CTX packing.
9. Raw affect estimates are not persisted as durable user facts.
10. Every apply path is idempotent and lineage-aware.

## Namespace isolation

Character, user/viewer, project, scene, session, room, memory, and cache namespaces must not be mixed merely because one RelayLM process serves them.

External IDs should not be exposed in default trace projections.

## Non-goals

RelayMEM does not:

- own scene classification,
- own intent/reference resolution,
- own final prompt layout,
- inspect generated output,
- directly mutate RelaySOUL,
- require per-turn user approval for ordinary memory formation,
- persist raw affect inference as fact,
- require vector infrastructure for the MVP,
- expose content-bearing memory artifacts through default trace/audit surfaces.

## Summary

```text
RelayMEM storage
  formed durable memory substrate

RelayMEM Retrieval
  read-only current-answer evidence

RelaySLP
  deferred governed memory formation and proposal path

RelayREF
  separate post-generation observer
```
