---
relaylm_doc_type: proposal
relaylm_authority: proposed_subjective_memory_formation_consolidation_and_retrieval_model
relaylm_status: target
relaylm_proposal_status: under_review
relaylm_volatility: high
relaylm_owner: memory
relaylm_update_trigger:
  - this proposal is accepted, rejected, withdrawn, or materially revised
  - subjective MEM formation or evidence authority changes
  - aggregation or retrieval evaluation changes the recommended model
  - Markdown or SQLite storage authority changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - accepted production architecture
  - exact API, prompt, embedding, or database schema
  - implementation completion or migration readiness
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/character_conditioned_belief_model.md
---

# Subjective MEM Formation, Consolidation, and Retrieval Proposal

## Status and decision requested

This is an undecided proposal. It changes no current RelayMEM, RelaySLP, RelaySOUL, RelaySCN, RelayEMO, SOUL Lab, or storage behavior.

The requested decision is whether RelayLM should adopt this post-v0.1 direction:

1. protected source evidence remains immutable and character-independent;
2. RelaySLP uses the character's main LLM, conditioned by SOUL and bounded character state, to form **subjective MEM**;
3. strongly similar semantic evidence normally reinforces, refines, or reinterprets an existing MEM instead of creating a near-duplicate MEM;
4. retrieval searches canonical subjective MEM rather than every supporting observation;
5. the online main LLM may emit a bounded, non-authoritative semantic memory sidecar while CTX and RelaySLP retain authority for evidence, normalization, candidate selection, and durable decisions;
6. explicit semantic facets, temporal validity, lifecycle, and typed relations may influence deterministic filtering and ranking before bounded candidates reach the main LLM;
7. Markdown remains the human-readable steady-state representation while SQLite provides rebuildable retrieval projections and durable operation state;
8. production adoption is gated by aggregation-quality, retrieval-scale, sidecar-quality, main-LLM burden, lifecycle, migration, and platform validation.

If accepted, the durable decision belongs in an ADR. Exact formation, handoff, storage, lifecycle, and retrieval contracts should then be split into their owning documents.

## Recommendation

Adopt this direction as a target, subject to the evaluation gates below.

RelayLM should not become only a neutral note organizer. Its differentiating memory behavior should be:

> A character preserves governed evidence, reflects on it through its own SOUL and relationship context, and forms a grounded memory of what the experience meant to that character.

That subjectivity must not rewrite observation:

```text
Protected Source Evidence
  -> Character-independent Shared Assessment
  -> Character-conditioned Subjective MEM
  -> SCN and future interpretation
```

For repeated semantic evidence, the default should be:

```text
strongly equivalent evidence
  -> attach support to the existing MEM
  -> update confidence / stability / last confirmation
  -> do not create another retrieval-visible MEM
```

A new MEM is created only for a distinct event, meaning, subject, time scope, contradiction, or durable interpretation.

## Why this is needed

The current system proves protected source capture, autonomous ordinary Primary MEM formation, namespace isolation, provenance, lifecycle operations, bounded file-store discovery, and grounded recall.

It does not yet solve:

- repeated paraphrases producing redundant MEM;
- support versus refinement versus contradiction;
- character subjectivity without source corruption;
- similar memories occupying retrieval slots;
- retrieval quality at tens of thousands of MEM;
- temporal, entity, polarity, modality, project, and relationship compatibility in Retrieval;
- a safe low-burden handoff from the online main LLM into deferred memory work;
- explainable evidence-to-memory inspection in SOUL Lab.

Tracks A-D provide evidence for these questions but are not accepted architecture.

## Alignment with existing authority

### Observation and belief

[ADR: Character-conditioned belief without rewriting observation](../adr/character_conditioned_belief_model.md) establishes that observations are immutable, shared assessment is character-independent, and each character projects its own belief.

This proposal applies that boundary to durable memory:

```text
Shared evidence truth
  != Character A's subjective MEM
  != Character B's subjective MEM
```

SOUL may shape attention, significance, and interpretation. It must not change speaker, time, quantity, polarity, correction, or source lineage.

### Character dynamics

[Character belief, relationship, and social expression dynamics](../architecture/character_belief_relationship_dynamics_design.md) defines:

```text
Observation
  -> Shared Assessment
  -> Character Belief
  -> Relationship
  -> Behavior
```

Subjective MEM is a durable governed result of character-conditioned interpretation, not a replacement for Shared Assessment.

### RelaySLP

[RelayMEM SLP execution design](../architecture/relaymem_slp_execution_design.md) already defines existing-MEM lookup followed by merge, update, hold, or reject, with relations such as `supports`, `refines`, `supersedes`, and `contradicts`.

This proposal defines how candidate retrieval, bounded online semantic hints, CTX-owned evidence metadata, main-LLM judgment, evidence reinforcement, subjective writing, and retrieval collapse should connect.

### Lifecycle

Current Phase I-4 authority defines Forget as a hidden successor and retrieval exclusion, not physical deletion:

- [Forget / Hide contract](../architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Hidden-Successor Commit](../architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [Retrieval Exclusion](../architecture/phase_i4d_primary_retrieval_exclusion.md)

The target remains:

```text
Forget  = reversible retrieval exclusion
Restore = return to active retrieval
Purge   = separate irreversible operation
```

## Final-review corrections and evidence limits

1. **Shared Assessment must not be SOUL-conditioned.** Evidence is assessed first; only subjective formation is character-conditioned.
2. **Embedding similarity is not identity.** It may find candidates but cannot authorize merge.
3. **Track D does not prove final Forget semantics.** Its current experiment branch physically removes the Markdown block. It validates useful storage mechanics, not hidden-successor/Restore behavior.
4. **Current Retrieval is bounded, not large-scale semantic Retrieval.** Scan and read caps protect latency but do not prove recall quality at scale.
5. **No embedding model is selected.** Japanese thresholds and models require RelayLM-specific evaluation.
6. **The online main-LLM sidecar is advisory, bounded, and optional.** It must not authorize writes, invent system metadata, select canonical MEM, or degrade the natural response path when absent or invalid.
7. **Recency is not temporal compatibility.** Retrieval should prefer the MEM valid for the question's referenced time, not merely the newest file or observation.

## Concepts and ownership

### Protected Source Evidence

Immutable or append-only governed material: message references, imported communications, explicit corrections, timestamps, speaker, source ID, and independence group. It supports audit and regeneration and is not ordinary prompt content.

### Shared Assessment

A character-independent structure describing only what evidence supports:

```yaml
subject: user
predicate: prefers
object: light-roast Ethiopian coffee
context: focused work in the morning
polarity: positive
time_scope: current_habit
explicitness: explicit
source_refs:
  - source:conversation:...
```

### Bounded semantic memory sidecar

The online main LLM may return a small sidecar beside its natural-language answer. The sidecar is a semantic hint for later CTX and RelaySLP processing, not a durable assessment or write instruction.

It should contain only values that materially benefit from understanding the conversation:

```yaml
memory_disposition: possible
claims:
  - subject_hint: user
    predicate_hint: prefers
    object_text: light-roast Ethiopian coffee
    polarity_hint: positive
    modality_hint: asserted_state
    temporal_kind_hint: current_state
    temporal_expression: recently
    change_signal: possible_change
    explicitness_hint: explicit
    evidence_span:
      source: user_turn
      quote: "Recently I prefer light-roast Ethiopian coffee."
    subjective_significance_hint:
      text: may matter to focused morning routines
      grounded: false
```

The schema should generalize beyond time to bounded semantic facets such as:

- subject and entity;
- predicate or relation;
- polarity;
- modality, including fact, preference, intention, hypothetical, quotation, joke, and correction;
- temporal kind and original temporal expression;
- project, relationship, scene, and topic scope;
- change, correction, contradiction, and retraction signals;
- explicitness and evidence span;
- possible subjective significance.

The online main LLM must not decide or fabricate:

```yaml
target_mem_id: forbidden_online_authority
canonical_mem_id: forbidden_online_authority
final_relation: forbidden_online_authority
observed_at: system_owned
valid_from: unresolved_without_evidence
valid_until: unresolved_without_evidence
evidence_confidence: slp_owned
stability: slp_owned
```

Unknown values remain absent or `null`; schema completion must not encourage invention.

### CTX evidence envelope

CTX attaches values known by the system and validates sidecar references before deferred memory work:

```yaml
evidence_context:
  observed_at: system_clock
  conversation_id: system_owned
  turn_id: system_owned
  speaker: system_owned
  character_id: system_owned
  namespace: system_owned
  timezone: system_owned
  source_digest: system_owned
  independence_group: system_owned

temporal_resolution:
  original_expression: last autumn
  normalized_start: 2025-09-01
  normalized_end: 2025-11-30
  resolution_confidence: medium
```

The original expression remains available. Resolution may stay partial or unknown. `observed_at` must not be silently reused as `valid_from`.

### Subjective MEM

A character-scoped durable memory with distinguishable grounded and subjective parts:

```yaml
grounded_content: what the evidence supports
subjective_meaning: how this character remembers its significance
```

The exact schema is undecided; the separation is required.

### Semantic and Episodic MEM

- **Semantic MEM** represents a generalizable preference, fact, relationship understanding, concept, or project state. Repeated equivalent evidence normally reinforces it.
- **Episodic MEM** represents a distinct event, commitment, turning point, or time-bounded experience. Similar wording does not collapse separate episodes.

A useful hierarchy is:

```text
episodes
  -> Semantic MEM
  -> SCN synthesis
```

### Evidence Link

A typed link from evidence or Shared Assessment to MEM: `supports`, `refines`, `contradicts`, `supersedes`, or `derived_from`.

## Online handoff and main-LLM burden

The natural-language response is primary. The sidecar must not consume enough reasoning, tokens, or retry behavior to materially reduce conversational quality.

```text
Main LLM
  -> natural response
  -> optional bounded semantic memory sidecar
CTX
  -> source validation and system metadata
  -> relative-time resolution where possible
RelaySLP
  -> character-independent Shared Assessment
  -> existing-MEM candidate lookup and relation decision
  -> character-conditioned subjective formation
```

Required safeguards:

- `memory_disposition` gates detailed claims as `none`, `possible`, or `explicit`;
- ordinary turns may return no claims;
- the sidecar has a strict item and token budget;
- malformed or absent sidecars do not trigger response-path retries;
- schema validation failure falls back to evidence-only deferred processing or no memory work;
- the sidecar cannot block or rewrite the natural response;
- evidence spans are verified against the referenced turn;
- system-owned values are added by CTX, never generated by the model;
- relation, canonical identity, lifecycle, and durable write decisions remain RelaySLP/MEM authority;
- detailed analysis and subjective formation remain deferred outside the latency-critical response path.

A later implementation may produce the sidecar in the same generation, through a constrained secondary output channel, or through deferred re-analysis. The architecture decision should be based on measured response quality and latency, not on assuming that one-pass structured output is free.

## Formation pipeline

```text
Protected Source Evidence
  -> evidence admission and independence grouping
  -> validated CTX evidence envelope and optional semantic sidecar
  -> character-independent Shared Assessment
  -> exact-key and scoped candidate lookup
  -> FTS / vector / metadata candidate generation
  -> deterministic compatibility gates
  -> main-LLM subjective relation decision
  -> grounded subjective MEM draft
  -> evidence and policy validation
  -> durable intent
  -> Markdown commit
  -> SQLite projection refresh
  -> durable receipt
```

This is deferred RelaySLP work. It may use the main character model because it is outside the latency-critical answer path. The online sidecar may guide attention but must not replace this deferred assessment.

### Pass 1: grounded understanding

Produce a bounded artifact:

```yaml
supported_facts: []
unsupported_inferences: []
uncertainties: []
candidate_existing_memories: []
proposed_relation: reinforce_memory
target_mem_id: mem:...
added_information: []
subjective_significance_candidates: []
```

### Pass 2: subjective formation

Provide the validated assessment, bounded related MEM, SOUL, target-specific REL, relevant SCN, bounded EMO, allowed decisions, and grounding constraints. Generate a proposed MEM revision.

### Pass 3: validation

Check that:

- grounded claims map to evidence or prior accepted MEM;
- sidecar evidence spans map to the referenced source turn;
- subject, speaker, polarity, modality, time, quantity, and scope are preserved;
- character and namespace match;
- sensitive or weak inference is not promoted;
- relation choice passes deterministic gates;
- lifecycle and tombstones are respected;
- lineage remains available;
- the write is idempotent and revision-fenced.

Failure becomes `leave_as_evidence`, held review, or no change.

## Bounded relation decisions

| Decision | Meaning | Default effect |
|---|---|---|
| `reinforce_memory` | materially the same meaning | add evidence; update strength; no new retrieval-visible MEM |
| `refine_memory` | compatible new specificity | revise existing MEM; preserve prior revision |
| `reinterpret_memory` | facts remain, subjective significance changes | revise subjective meaning with lineage |
| `supersede_memory` | newer durable state replaces current state | publish successor; preserve temporal history |
| `contradict_memory` | unresolved conflict | preserve both paths; link contradiction; lower certainty or hold |
| `relate_memory` | relevant but not the same meaning | typed link; no confidence reinforcement |
| `create_memory` | distinct durable meaning or episode | create new MEM |
| `leave_as_evidence` | valid but not ready or valuable as MEM | retain evidence only |

## Deciding "strongly similar"

### Candidate generation

Use a bounded union of:

```text
exact normalized key
FTS / exact terms
metadata and entity match
vector similarity
typed relations
```

These channels find candidates; they do not authorize consolidation.

### Hard compatibility gates

Reject merge candidates that differ materially in:

- character or namespace;
- subject or entity;
- polarity;
- modality, such as fact versus intention or hypothetical;
- temporal validity or time scope;
- memory kind;
- project, relationship, or scene scope;
- lifecycle state;
- correction or tombstone authority.

Thus, similar text must not merge different actors, preferences with actions, intentions with completed events, or past and current states.

### Main-LLM judgment

After hard gating, the main LLM decides whether the character experiences the evidence as confirmation, refinement, reinterpretation, successor, contradiction, relation, new memory, or non-memory.

It receives only a bounded neighborhood, never the full corpus. The online sidecar is an input hint, not a substitute for this decision.

### Conservative policy

False merge is more damaging than a temporary duplicate. Automatic reinforcement should target very high precision. Ambiguity should prefer `leave_as_evidence`, `relate_memory`, or a later-consolidatable new MEM.

Thresholds must be calibrated on RelayLM-specific Japanese and mixed-language examples.

## Memory strength

Strength is not one opaque score.

- **Evidence confidence:** how strongly governed evidence supports grounded content.
- **Stability:** whether the memory is durable across time and independent contexts.
- **Salience:** importance to this character's future interaction.
- **Subjective conviction:** how strongly the character holds the interpretation.

Subjective conviction cannot turn weak evidence into fact.

### Independence groups

Derivatives of one source do not count as independent confirmation:

```text
one user message
  -> raw event
  -> session summary
  -> extracted candidate
```

These share one `independence_group`. A later independent statement may increase stability.

## Temporal and semantic facets

Temporal data should distinguish evidence time from validity time:

```yaml
observed_at: when RelayLM received the evidence
valid_from: when the represented state became true, if known
valid_until: when it stopped being true, if known
first_observed_at: first supporting observation
last_confirmed_at: latest independent confirmation
```

Unknown validity does not default to the observation time. File modification time is not semantic validity.

The same explicit-facet approach applies beyond time. Retrieval and consolidation may use subject, entity, predicate, polarity, modality, project, relationship, scene, correction authority, and lifecycle as explainable compatibility signals.

## Authority and storage

### Protected source domain

Owns content-bearing evidence, speaker, timestamp, import provenance, correction origin, and independence grouping. Subjective formation cannot rewrite it.

### Markdown steady-state authority

Subjective MEM should have a human-readable Markdown steady-state form for inspection, backup, migration, and governed editing.

Use human-scale pages, not one file per memory. Stable MEM IDs should survive page movement and title changes.

Possible visible fields include grounded content, subjective meaning, kind, lifecycle, representative provenance, semantic facets, temporal validity, strength dimensions, first observed, last confirmed, and typed relations. Exact syntax remains undecided.

### Rebuildable `memory-cache.db`

Possible projections:

- parsed MEM blocks;
- FTS;
- vector references or embeddings;
- semantic facets, temporal intervals, tags, and entities;
- typed relations;
- canonical-MEM membership;
- lifecycle;
- page and block digests;
- retrieval features and explainable ranking reasons.

Deleting this database must not destroy durable MEM or evidence.

### Durable `operations.db`

Own non-rebuildable operation state:

- jobs, claims, and leases;
- apply intents and idempotency;
- receipts and failures;
- lifecycle tombstones;
- durable usage events when behavior depends on them.

It must not become a second authority for MEM prose.

### Commit protocol

```text
durable intent
  -> render temporary Markdown
  -> validate schema and grounding
  -> fsync
  -> atomic replace
  -> verify digest
  -> refresh rebuildable cache
  -> durable receipt
```

The receipt is the commit marker. Recovery uses pre/post digests without double application. This remains proposal-level until tests use the final lifecycle semantics.

## Retrieval

Ordinary conversation retrieves Subjective MEM, not every supporting evidence item. Evidence is expanded only for correction, contradiction, audit, exact confirmation, or grounding.

### Multi-stage path

```text
1. resolve bounded query facets, including temporal intent when present
2. character / namespace / lifecycle filter
3. exact / FTS / metadata candidates
4. vector candidates
5. deterministic rank fusion and facet compatibility
6. canonical-MEM collapse
7. bounded typed-relation expansion
8. bounded rerank
9. token-aware context packing
```

### Hybrid retrieval

- exact search handles IDs, names, and precise terms;
- FTS handles lexical relevance;
- metadata handles entity, scope, modality, lifecycle, and temporal validity;
- vectors handle Japanese paraphrase and semantic similarity.

Vector-only retrieval is insufficient for negation, actor identity, temporal change, quantities, exact terms, scope, and preference-versus-action distinctions.

### Temporal compatibility

Retrieval should rank by compatibility with the query's referenced time, not by recency alone.

```text
current-state query
  -> active successor and currently valid MEM first
historical query
  -> MEM whose validity overlaps the requested period first
transition query
  -> bounded supersedes / contradicts / correction chain
unspecified time
  -> current authority first, with bounded historical diversity when relevant
```

A query may carry a bounded temporal intent such as `current`, `historical`, `point_in_time`, `range`, `transition`, or `unspecified`. Failure to resolve it falls back to ordinary hybrid Retrieval.

### Collapse and relations

Supporting evidence for one current MEM occupies one retrieval slot. Only a bounded relation neighborhood, normally one hop, is expanded. The full graph is not traversed per request.

### Ranking priority

```text
query relevance
  > character / namespace / entity scope
  > temporal, polarity, modality, and project compatibility
  > lifecycle and correction authority
  > evidence confidence
  > stability and bounded salience
  > recency and bounded usage
```

Recency must not outrank a known validity mismatch. Usage must have bounded weight to prevent popularity feedback loops.

A reranker may select only existing IDs from a bounded top set. It may not invent memory. Candidates passed to the main LLM should include compact ranking reasons and relevant temporal or semantic facets so the model can distinguish current, historical, hypothetical, corrected, and contradictory states.

## Obsidian-inspired cues

Useful principles:

- human-readable Markdown;
- stable IDs and backlinks;
- typed properties and relations;
- people, project, topic, and SCN hubs;
- list, timeline, relation, and search views from projections;
- local-first rebuildability.

Do not adopt as defaults:

- one file per memory;
- manual-link-only maintenance;
- graph visualization as Retrieval;
- unrestricted plugin syntax as authority;
- direct editing of operational SQLite state.

## SOUL Lab implications

Future Memory Explorer needs stable identity, scope, grounded/subjective distinction, lifecycle, tags, semantic facets, provenance, evidence count, observation and validity times, usage, relations, operation status, Correct, Forget, Restore, and Pin.

It remains an exploration and curation surface, not a mandatory approval queue, raw database editor, independent authority, or source-evidence rewriter.

## Evidence from Tracks A-D

### Track A: inventory

Provides storage, reader/writer, invocation, configuration, and dependency evidence for cutover. It is not deletion authority; absence from inferred graphs is not proof of dead code.

### Track B: characterization

Protects semantic invariants such as autonomous formation, provenance, namespace isolation, lifecycle authority, idempotency, and failure honesty.

Current `index.md`, `log.md`, file queue, advisory-lock, and partial-file-state tests describe today's backend and must be replaced during hard cutover, not preserved as permanent layout.

### Track C: Memory Explorer mock

Validates product needs for search, provenance, tags, correction, lifecycle, relations, usage, and operation visibility. Browser-local state is not authority and the mock does not define production API or storage schema.

### Track D: Markdown/SQLite spike

Supports deterministic Markdown parse/render, rebuildable FTS, incremental projection, intent/digest/receipt recovery, idempotency, stale-snapshot protection, and schema versioning. It also reveals SQLite write-lock unfairness, page-level serialization, and fsync-limited writes.

It remains an isolated experiment. Its current Forget implementation physically removes the block, so it does not validate hidden-successor/Restore semantics. It also does not validate vector retrieval, semantic consolidation, semantic-sidecar quality, Windows/WSL behavior, backup, migration, or large-scale quality.

## Main risks and safeguards

| Risk | Required safeguard |
|---|---|
| hallucinated subjective meaning | Shared Assessment first; unsupported-inference output; grounding validator; abstention |
| online answer degradation | minimal optional sidecar; strict budget; no response-path retry; deferred detailed analysis |
| sidecar fabrication | verified evidence spans; system-owned metadata; nullable fields; sidecar remains advisory |
| over-merge | hard semantic gates; conservative threshold; revision/evidence preservation |
| under-merge | scheduled consolidation; Retrieval collapse; duplicate-rate monitoring |
| temporal misranking | explicit validity and temporal intent; recency cannot override known mismatch |
| identity drift | MEM cannot mutate SOUL; SOUL change remains separate approval path |
| cross-character contamination | shared evidence may be reused; subjective MEM is always character-scoped |
| popularity feedback | relevance first; bounded usage weight; diversity and collapse |
| sensitive inference | direct authority required; weak/sensitive inference stays held or evidence-only |

## Evaluation gates

### Aggregation quality

Build a labeled Japanese and mixed-language set covering:

- duplicate and paraphrase;
- refinement and reinterpretation;
- temporal successor;
- contradiction;
- related but distinct;
- different subject, relationship, project, modality, and scene;
- fact versus preference, intention, hypothetical, quotation, and joke;
- separate episodes with similar wording;
- user correction and tombstone;
- raw/summary/extracted derivatives of one source.

Primary safety metric: **false merge rate**.

Also measure relation accuracy, abstention, unsupported inference, lineage preservation, subjectivity consistency, and cross-character leakage.

### Semantic sidecar quality and main-LLM burden

Compare:

- natural response with no sidecar;
- natural response plus minimal sidecar in one generation;
- natural response plus a constrained secondary output channel;
- natural response followed by deferred re-analysis.

Measure:

- natural-response quality and character consistency;
- time to first token and total response latency;
- output token overhead;
- malformed-sidecar rate and retry rate;
- evidence-span precision and claim recall;
- subject, polarity, modality, temporal-kind, scope, correction, and change-signal accuracy;
- unsupported-field invention;
- `none` / `possible` / `explicit` disposition accuracy;
- downstream formation quality with and without the sidecar.

No online sidecar design is eligible if it materially degrades the normal conversation or requires synchronous retries to satisfy the schema.

### Retrieval scale

Evaluate at 10,000, 50,000, and 100,000 MEM:

- FTS only;
- vector only;
- hybrid fusion;
- hybrid plus semantic-facet and temporal ranking;
- hybrid plus collapse;
- hybrid plus relation expansion;
- optional bounded reranking.

Measure recall@k, precision@k, duplicate rate@k, relevant-fact coverage, contradiction visibility, current-state accuracy, historical-period accuracy, transition-chain accuracy, p50/p95 latency, CPU/RAM, build/rebuild time, incremental update, explainability, and token-pack quality.

### Subjective value

Compare neutral fact extraction, SOUL-conditioned MEM, grounded SOUL-conditioned MEM, and grounded MEM plus SCN evolution.

Judge remembered-character feeling, SOUL consistency, relationship continuity, factual grounding, intrusiveness, overinterpretation, and correction behavior.

### Storage and platform

Validate Linux, WSL Linux filesystem, supported Windows paths, rename/fsync behavior, WAL/busy handling, crash windows, cache corruption/rebuild, backup/restore, and migration rehearsal. Explicitly decide whether `/mnt/c` is unsupported.

## Recommended sequence

1. Accept or reject this direction through an ADR.
2. Run a semantic-sidecar spike that measures main-LLM response quality, latency, evidence-span grounding, schema failure, and deferred fallback.
3. Run an aggregation spike for Shared Assessment, bounded candidates, hard gates, main-LLM relation decisions, evidence linking, semantic facets, and abstention.
4. Run a Retrieval-scale spike with FTS, a selected static embedding, deterministic facet and temporal ranking, fusion, collapse, relations, and machine-readable evaluation.
5. Correct and extend the storage spike with hidden-successor Forget, Restore, evidence links, subjective revisions, semantic facets, temporal validity, independence groups, and complete crash tests.
6. Define sidecar, CTX envelope, formation, schema, evidence-link, storage, Retrieval, operation, and Memory Explorer contracts.
7. Rehearse import, rebuild, backup, rollback, lifecycle, and provenance migration.
8. Perform one hard cutover: update callers, import durable state once, switch authority, and remove obsolete readers/writers without permanent dual-read or dual-write.

## Non-goals

This proposal does not change current runtime behavior, require a full structured answer on every turn, require response-path retries for sidecar validity, make the online main LLM the authority for MEM writes or system metadata, require per-memory approval, authorize MEM-to-SOUL mutation, make subjective MEM shared truth, expose full source evidence by default, select an embedding or vector database, require a graph database, require one file per memory, adopt Obsidian as a dependency, approve Track D for production, claim Windows/WSL validation, define Purge, or authorize automatic sensitive inference.

## Open decisions

1. Exact bounded semantic sidecar schema and token/item budget.
2. Whether the sidecar is same-generation, a constrained secondary channel, deferred re-analysis, or a measured hybrid.
3. Exact CTX evidence-envelope and relative-time-resolution contract.
4. Exact Shared Assessment schema.
5. Required SOUL/REL/SCN/EMO slices and prompt contract.
6. When to regenerate wording versus update strength only.
7. Reconciliation of user Markdown edits with grounding.
8. Japanese static embedding and vector index.
9. Automatic `reinforce_memory` precision threshold.
10. Held versus evidence-only conditions.
11. Representation of confidence, stability, salience, and conviction.
12. Relation-expansion budget.
13. Reinterpretation after approved SOUL revision.
14. Usage-event retention and privacy.
15. Accepted main-LLM response-quality and latency regression thresholds.

## Final conclusion

RelayLM should adopt **reinforcement-first subjective memory formation** with a bounded semantic handoff as the target direction:

```text
natural response + optional semantic sidecar
  -> CTX-owned evidence and temporal normalization
  -> immutable evidence
  -> shared factual assessment
  -> deterministic semantic and temporal candidate ranking
  -> SOUL-conditioned subjective reflection
  -> reinforce / refine / reinterpret / supersede /
     contradict / relate / create / leave as evidence
  -> grounded Subjective MEM
  -> hybrid Retrieval with canonical collapse
```

This preserves the factual safety of the existing observation model while adding RelayLM's distinctive value: a character does not merely store what happened; it develops a grounded, character-specific memory of what the experience meant.

The sidecar is useful only when it improves deferred memory work without reducing normal conversation quality. It remains advisory; CTX owns evidence metadata, RelaySLP owns relation and subjective formation, and MEM owns durable state.

The storage evidence supports continuing to ADR and evaluation. It does not justify production adoption by itself. Aggregation quality, sidecar quality, main-LLM burden, and Retrieval scale are co-equal gates with durability and migration safety.
