# RelayMEM MVP Design

Date basis: 2026-05-31 JST

## Purpose

RelayMEM is the long-term memory layer of RelayLM. It should not be treated as a simple RAG cache. Its MVP direction is a file-backed long-term memory compiler inspired by Karpathy-style LLM Wiki ideas.

RelayMEM preserves raw evidence, compiles stable memory pages, maintains retrieval indexes, and exposes only safe, token-budgeted memory blocks to RelayCTX at runtime.

## Core positioning

RelayMEM sits between raw conversation evidence and runtime context assembly.

```text
raw sources
  -> RelaySLP / memory compile path
  -> compiled MEM pages + index + log
  -> Retrieval path
  -> RelayCTX block
  -> Main LLM
```

The key distinction is:

```text
SLP improves memory quality.
Retrieval improves the current answer.
```

SLP may edit or propose edits to memory. Retrieval must only read memory and pack a safe context block.

## Relation to other RelayLM layers

```text
RelaySOUL
= Stable identity, long-term principles, relationship/approval layer.
= Never directly mutated by RelayMEM.

RelayEMO
= Mutable affect/expression runtime.
= user_affect_estimate is not persisted as a long-term fact.

RelayCTX
= Runtime context packing and unpacking.
= Receives token-budgeted RelayMEM context blocks.

RelaySCN
= Scene-state controller.
= Resolves memory scope and persistence/update gates.

RelaySLP / ReallyREF
= Reflection, lint, consolidation, and memory compile cycle.

RelayMEM
= Long-term memory compiler and retrieval source.
```

## Storage model

MVP should begin with a file-backed layout using Markdown and JSONL rather than a database.

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
      relaylm.md
      relaymem.md
      relayemo.md

    concepts/
      slp.md
      retrieval.md
      ctx_repack.md

    claims/
      claim_*.md

    summaries/
      session_*.md

    relations/
      graph.json
```

## Four-part memory structure

### raw_sources

Primary evidence. These are original or near-original records.

Examples:

- user messages
- assistant messages
- uploaded document summaries
- URL/source notes
- runtime events
- CTX snapshots

Raw sources should be preserved and not overwritten by compiled summaries.

### mem_pages

Compiled memory pages synthesized from raw evidence.

Examples:

- project pages
- concept pages
- claim pages
- session summaries
- relationship or policy diagnostics, when allowed

Runtime normally uses compiled summaries rather than raw evidence unless verification is needed.

### mem_index

A lightweight retrieval index.

Examples:

- `memory/mem/index.md`
- aliases
- tags
- page summaries
- relation hints
- updated timestamps

The first MVP can use keyword/semantic-lite search over Markdown before adding a vector store.

### mem_log

Append-only audit log for SLP operations.

Examples:

- candidate extraction runs
- page updates
- held candidates
- rejected candidates
- lint results
- SOUL promotion proposals

## Memory kinds

MVP should support a small set of memory kinds.

```yaml
memory_kind:
  raw_event:
    description: Primary event or source record. Not rewritten.

  session_summary:
    description: Summary of a recent conversation or session.

  project_state:
    description: Current state of a project such as RelayLM, RelayMEM, RelayEMO, or RelayKV.

  concept:
    description: Stable concept definition or design pattern.

  claim:
    description: Factual or design claim with evidence references.

  preference:
    description: User workflow preference or durable non-sensitive preference.

  relation:
    description: Typed relation between project, concept, and claim pages.

  soul_candidate:
    description: Candidate for RelaySOUL promotion. Must not directly mutate SOUL.

  rejected_or_blocked_candidate:
    description: Candidate that was blocked, rejected, stale, contradictory, or unsafe.
```

## Safety scopes

RelayMEM must classify memory candidates by update safety.

```yaml
safety_scope:
  free_to_update:
    description: Safe for RelayMEM to update automatically.
    examples:
      - project implementation notes
      - design docs
      - general concept pages
      - non-sensitive task state

  review_required:
    description: Hold for review before applying.
    examples:
      - durable user workflow preferences
      - major project direction changes
      - potentially ambiguous long-term facts

  explicit_approval_required:
    description: Must become an approval artifact or SOUL proposal.
    examples:
      - RelaySOUL principle changes
      - identity or relationship principles
      - long-term approval-sensitive memory

  never_auto_promote:
    description: Must not become long-term memory automatically.
    examples:
      - raw user_affect_estimate
      - transient emotion inference
      - sensitive attribute inference
      - low-confidence personal inference
```

## Relation model

RelayMEM should avoid untyped “related” links as the only relation form. Typed relations make memory useful for reasoning and linting.

Suggested relation types:

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

Example:

```yaml
relations:
  - source: relaymem
    type: depends_on
    target: relayctx
    confidence: 0.86

  - source: user_affect_estimate
    type: blocked_from_soul
    target: relaysoul
    confidence: 0.95
```

## Core rules

1. SLP edits or proposes memory changes; Retrieval only reads memory.
2. MEM can auto-update only `free_to_update` scope.
3. `review_required` candidates are held.
4. `explicit_approval_required` candidates become SOUL proposals or approval artifacts.
5. RelaySOUL is never directly mutated by RelayMEM.
6. Raw evidence is preserved.
7. Runtime normally uses compiled summaries.
8. Contradictory, stale, or unapproved memory is blocked from normal CTX packing.
9. Retrieval is token-budgeted and diagnostics-visible.
10. Raw `user_affect_estimate` is not persisted as a long-term fact.

## MVP implementation order

```text
MVP-MEM-1: File-backed memory store
- raw event append
- mem page read/write
- index.md generation
- log.md append

MVP-MEM-2: SLP dry-run
- read recent raw log
- extract memory candidates
- classify memory_kind
- classify safety_scope
- emit proposed page updates
- no apply by default

MVP-MEM-3: SLP apply gate
- apply free_to_update only
- hold review_required
- convert explicit_approval_required to SOUL proposal
- log every decision

MVP-MEM-4: Retrieval runtime
- build query from user input + scene/task
- search index
- load top candidate pages
- safety filter
- token-budget pack
- pass context block to RelayCTX

MVP-MEM-5: Retrieval diagnostics
- selected_mem
- blocked_mem
- token_budget
- used_tokens
- selection reasons
- fallback reason
```

## Non-goals for MVP

- Do not implement a vector database first.
- Do not mutate RelaySOUL directly.
- Do not persist raw affect estimates as durable facts.
- Do not let Retrieval update MEM.
- Do not require background asynchronous execution for the first version.
- Do not pack unapproved or contradictory memory into runtime context.

## Summary

RelayMEM MVP is a file-backed long-term memory compiler and runtime retriever.

```text
SLP path:
  raw events -> candidates -> safety classification -> compiled MEM pages -> index/log

Retrieval path:
  user input + scene/task -> safe selected MEM -> token-budgeted RelayCTX block
```

This gives RelayLM a stable long-term memory layer without turning RelayMEM into uncontrolled RAG or allowing RelaySOUL pollution.
