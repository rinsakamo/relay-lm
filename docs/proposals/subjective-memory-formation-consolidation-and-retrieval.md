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
  - aggregation, session-overlay, or retrieval evaluation changes the recommended model
  - Markdown or SQLite storage authority changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - accepted production architecture
  - exact API, prompt, embedding, overlay, or database schema
  - implementation completion or migration readiness
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/character_conditioned_belief_model.md
relaylm_related_evidence:
  - ../evidence/implementation/session-evidence-overlay-feasibility.md
---

# Subjective MEM Formation, Consolidation, and Retrieval Proposal

## Status and decision requested

This is an undecided proposal. It changes no current RelayMEM, RelaySLP, RelaySOUL, RelaySCN, RelayEMO, SOUL Lab, or storage behavior.

The requested decision is whether RelayLM should adopt this post-v0.1 direction:

1. Protected Source Evidence remains immutable or append-only and character-independent.
2. The online main LLM may emit a bounded, optional, non-authoritative semantic sidecar and a current-session provisional interpretation.
3. RelayCTX may keep that provisional interpretation in a bounded **RelayCTX Session Evidence Overlay (CTX-OVL)** before RelaySLP completes.
4. RelaySLP uses the character's main LLM to form **subjective MEM** through a **SOUL-centered, SCN-grounded, EMO-decoupled** process.
5. Strongly similar semantic evidence normally reinforces, refines, or reinterprets an existing MEM instead of creating a near-duplicate retrieval-visible MEM.
6. Retrieval searches canonical subjective MEM rather than every supporting observation.
7. Explicit semantic facets, temporal validity, lifecycle, and typed relations influence deterministic filtering and ranking before bounded candidates reach the main LLM.
8. Markdown remains the human-readable steady-state representation while SQLite provides rebuildable retrieval projections and durable operation state.
9. Production adoption is gated by aggregation quality, sidecar burden, session-overlay correctness, subjective value, retrieval scale, lifecycle, migration, and platform validation.

If accepted, the durable decision belongs in an ADR. Exact sidecar, overlay, formation, storage, lifecycle, Retrieval, and operation contracts should then be split into their owning documents.

## Recommendation

Adopt this direction as a target, subject to the evaluation gates below.

RelayLM should not become only a neutral note organizer. Its differentiating memory behavior should be:

> A character preserves governed evidence, experiences it in the current scene and affect, then later reflects on it through stable character identity to form a grounded memory of what the experience meant.

The target flow is:

```text
Protected Source Evidence
  -> character-independent Shared Assessment
  -> SOUL-centered Subjective MEM formation
  -> future SCN and conversation behavior
```

The current conversational experience remains separately useful:

```text
current turn
  + current SCN
  + current EMO
  + bounded REL state
  -> hot provisional interpretation
  -> RelayCTX Session Evidence Overlay (CTX-OVL)
```

The hot interpretation may guide the ongoing conversation, but it is not automatically copied into durable MEM.

## Why this is needed

The current system proves protected source capture, autonomous ordinary Primary MEM formation, namespace isolation, provenance, lifecycle operations, bounded discovery, and grounded recall.

It does not yet solve:

- repeated paraphrases producing redundant MEM;
- support versus refinement versus contradiction;
- character subjectivity without source corruption;
- current-session continuity before RelaySLP completes;
- emotional over-weighting becoming durable fact;
- similar memories occupying retrieval slots;
- temporal, entity, polarity, modality, project, relationship, and scene compatibility;
- retrieval quality at tens of thousands of MEM;
- a safe low-burden handoff from the online main LLM into deferred memory work;
- explainable evidence-to-memory inspection in SOUL Lab.

Tracks A-D and the Session Evidence Overlay feasibility record provide evidence for these questions but are not accepted architecture.

## Alignment with existing authority

### Observation and belief

[ADR: Character-conditioned belief without rewriting observation](../adr/character_conditioned_belief_model.md) establishes that observations are immutable, Shared Assessment is character-independent, and each character projects its own belief.

```text
Shared evidence assessment
  != Character A's subjective MEM
  != Character B's subjective MEM
```

SOUL may shape attention, significance, and interpretation. It must not change speaker, time, quantity, polarity, correction, source lineage, scene facts, or audience scope.

### Character dynamics

[Character belief, relationship, and social expression dynamics](../architecture/character_belief_relationship_dynamics_design.md) separates observation, assessment, belief, relationship, action, expression, and durable authority.

This proposal applies that separation to durable memory. Subjective MEM is a governed result of deferred reflection, not a replacement for Shared Assessment and not a direct serialization of the online emotional response.

### RelaySLP

[RelayMEM SLP execution design](../architecture/relaymem_slp_execution_design.md) already defines existing-MEM lookup followed by merge, update, hold, or reject, with relations such as `supports`, `refines`, `supersedes`, and `contradicts`.

This proposal defines how online semantic hints, Session Evidence Overlay state, CTX-owned evidence metadata, normalized SCN inputs, main-LLM judgment, evidence reinforcement, subjective writing, and Retrieval collapse should connect.

### Lifecycle

Current Phase I-4 authority defines Forget as a hidden successor and retrieval exclusion, not physical deletion:

- [Forget / Hide contract](../architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Hidden-Successor Commit](../architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [Retrieval Exclusion](../architecture/phase_i4d_primary_retrieval_exclusion.md)

```text
Forget  = reversible retrieval exclusion
Restore = return to active retrieval
Purge   = separate irreversible operation
```

## Final-review corrections and evidence limits

1. **Shared Assessment must not be SOUL-conditioned.** Evidence is assessed first; only subjective formation is character-conditioned.
2. **RelaySLP formation is SOUL-centered, SCN-grounded, and EMO-decoupled.** Normalized scene facts remain necessary to interpret scope and modality; current EMO and transient scene-expression pressure do not condition the durable interpretation.
3. **SCN has three distinct roles.** Scene facts support interpretation, scene policy gates persistence/disclosure, and transient expression allowance stays in the online response path.
4. **EMO may remain reaction evidence.** It can record how the character felt at the time, but it cannot prove a user fact or directly determine durable subjective meaning.
5. **Embedding similarity is not identity.** It may find candidates but cannot authorize merge.
6. **The online sidecar is advisory, bounded, and optional.** It must not authorize writes, invent system metadata, select canonical MEM, or trigger synchronous retries.
7. **A Session Evidence Overlay is working state, not pending durable MEM.** It may shadow incompatible durable MEM within the same session without mutating durable authority.
8. **Recency is not temporal compatibility.** Retrieval should prefer the MEM valid for the question's referenced time, not merely the newest observation or file.
9. **Track D does not prove final Forget semantics.** It validates useful storage mechanics, not the accepted hidden-successor/Restore lifecycle.
10. **No embedding model, vector index, threshold, final Markdown syntax, sidecar transport, overlay schema, or production SQLite schema is selected.**

## Concepts and ownership

### Protected Source Evidence

Immutable or append-only governed material:

- exact or protected message references;
- explicit corrections;
- timestamps and speaker;
- source identity and lineage;
- independence group;
- normalized scene and audience references;
- approved system metadata.

It supports audit and regeneration and is not ordinary prompt content.

### Shared Assessment

A character-independent structure describing only what evidence supports:

```yaml
subject: user
predicate: prefers
object: light-roast Ethiopian coffee
context: focused work in the morning
polarity: positive
modality: asserted_preference
time_scope: current_habit
scene_scope: ordinary_private_conversation
explicitness: explicit
source_refs:
  - source:conversation:...
```

Shared Assessment may use normalized scene facts because scene determines who spoke, to whom, in what mode, and with what audience. It must not use current EMO or character preference as factual authority.

### Bounded semantic memory sidecar

The online main LLM may return a small sidecar beside its natural-language answer. It is a semantic hint for later CTX and RelaySLP processing, not a durable assessment or write instruction.

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
    provisional_significance_hint:
      text: may matter to focused morning routines
      grounded: false
```

The schema should generalize beyond time to bounded semantic facets such as:

- subject and entity;
- predicate or relation;
- polarity;
- modality, including fact, preference, intention, hypothetical, quotation, joke, role-play, and correction;
- temporal kind and original temporal expression;
- project, relationship, scene, audience, and topic scope;
- change, contradiction, correction, and retraction signals;
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

CTX attaches values known by the system and validates sidecar references:

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

The original temporal expression remains available. Resolution may stay partial or unknown. `observed_at` must not be silently reused as `valid_from`.

### RelayCTX Session Evidence Overlay (CTX-OVL)

CTX-OVL is a RelayCTX-owned, character/namespace/session-scoped, bounded, rebuildable working projection used before RelaySLP publication. It is part of RelayCTX short-term continuity, not a RelayMEM store.

It may retain:

```yaml
session_candidate:
  candidate_id: session:...
  evidence_refs: []
  semantic_facets: {}
  status: provisional
  shadows_durable_candidates: []
  correction_of: null
  provisional_interpretation:
    perceived_significance: null
    current_scene_ref: scene:...
    affect_ref: emo:...
    authority: non_authoritative
```

The overlay may:

- preserve current-session continuity after recent messages are compacted;
- apply explicit session-local corrections and retractions;
- boost or shadow durable Retrieval candidates for the current session;
- retain the fact that the character had a particular reaction;
- provide source-lineage hints to later RelaySLP reconciliation.

It must not:

- create a durable MEM ID;
- determine final relation or lifecycle;
- become searchable across sessions by ordinary Retrieval;
- overwrite Markdown or durable operation state;
- promote current EMO into a user fact;
- survive indefinitely without an explicit restart policy.

### SCN input split

SCN must be separated into three categories.

#### Normalized scene facts

Used by Shared Assessment and grounding:

```yaml
scene_facts:
  participants: []
  speaker: user
  addressee: character
  interaction_mode: ordinary_conversation
  roleplay_scope: none
  task_scope: personal_chat
  audience_scope: private
```

These facts help distinguish assertion from quotation, real conversation from role-play, and private from public scope.

#### Scene persistence and disclosure policy

Used by apply/hold/reject gates:

```yaml
scene_policy:
  persistence_allowed: true
  memory_scope: personal
  disclosure_scope: private
  safety_sensitivity: normal
```

This policy controls whether and where a candidate may persist. It does not write the subjective meaning.

#### Transient scene expression pressure

Used only by the online response path:

```yaml
scene_expression:
  formality: low
  playfulness: high
  character_expression_allowance: high
```

Transient expression allowance must not condition durable Subjective MEM formation.

### EMO reaction evidence

Current EMO belongs to the hot online interpretation. It may be retained as bounded evidence that the character experienced a reaction:

```yaml
provisional_reaction_evidence:
  affect_at_turn:
    concern: high
    attachment_activation: medium
  perceived_significance:
    text: "I felt this might be a request for reassurance."
  authority: non_authoritative
```

RelaySLP may inspect this as evidence about the character's reaction. It must not infer from it that the user was objectively anxious, affectionate, hostile, or trustworthy.

### Subjective MEM

A character-scoped durable memory with distinguishable grounded and subjective parts:

```yaml
grounded_content: what the evidence supports
subjective_meaning: how this character remembers its significance
formation_context:
  soul_revision: soul:...
  relationship_scope: relationship:...
  scene_fact_refs: []
  provisional_reaction_reviewed: true
```

The exact schema remains undecided; the separation is required.

### Semantic and Episodic MEM

- **Semantic MEM** represents a generalizable preference, fact, relationship understanding, concept, or project state. Repeated equivalent evidence normally reinforces it.
- **Episodic MEM** represents a distinct event, commitment, turning point, or time-bounded experience. Similar wording does not collapse separate episodes.

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
Main LLM online response
  -> natural response
  -> optional bounded semantic sidecar
  -> optional hot provisional interpretation
RelayCTX
  -> source validation and system metadata
  -> CTX-OVL update
  -> relative-time resolution where possible
RelaySLP deferred
  -> character-independent Shared Assessment
  -> existing-MEM candidate lookup and relation decision
  -> SOUL-centered, SCN-grounded, EMO-decoupled subjective formation
```

Required safeguards:

- `memory_disposition` gates detailed claims as `none`, `possible`, or `explicit`;
- ordinary turns may return no claims;
- the sidecar has a strict item and token budget;
- malformed or absent sidecars do not trigger response-path retries;
- schema failure falls back to protected evidence or no memory work;
- the sidecar cannot block or rewrite the natural response;
- evidence spans are verified against the referenced turn;
- system-owned values are added by CTX, never generated by the model;
- relation, canonical identity, lifecycle, and durable write decisions remain RelaySLP/MEM authority;
- current EMO may influence the provisional overlay but not the durable formation prompt;
- detailed analysis and subjective formation remain deferred outside the latency-critical response path.

A later implementation may produce the sidecar in the same generation, through a constrained secondary output channel, or through deferred re-analysis. The architecture decision should be based on measured response quality and latency.

## Formation pipeline

```text
Protected Source Evidence
  -> evidence admission and independence grouping
  -> validated CTX envelope
  -> normalized SCN facts
  -> optional sidecar and provisional reaction evidence
  -> character-independent Shared Assessment
  -> exact-key and scoped candidate lookup
  -> FTS / static-vector / metadata candidate generation
  -> deterministic compatibility gates
  -> SOUL-centered subjective relation decision
  -> grounded Subjective MEM draft
  -> scene-policy, evidence, privacy, and lifecycle validation
  -> durable intent
  -> Markdown commit
  -> SQLite projection refresh
  -> durable receipt
```

### Pass 1: grounded understanding

Inputs:

- Protected Source Evidence;
- CTX-owned metadata;
- normalized SCN facts;
- validated semantic sidecar when present;
- relevant historical evidence.

Excluded conditioning:

- SOUL preference;
- current EMO;
- transient scene expression allowance.

Example output:

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

Inputs:

- validated Shared Assessment;
- bounded related MEM;
- stable SOUL revision;
- target-specific REL identity and bounded relationship history;
- normalized scene facts needed for scope;
- provisional reaction evidence as non-authoritative historical input;
- allowed decisions and grounding constraints.

Excluded conditioning:

- current EMO state;
- transient SCN expression allowance;
- online excitement, fear, anger, or attachment pressure as truth authority.

The provisional reaction may be reviewed, retained as an episodic detail, revised, or rejected. It is never copied automatically.

### Pass 3: validation and persistence policy

Check that:

- grounded claims map to evidence or prior accepted MEM;
- sidecar evidence spans map to the referenced source turn;
- subject, speaker, polarity, modality, time, quantity, scene, and audience scope are preserved;
- character and namespace match;
- sensitive or weak inference is not promoted;
- relation choice passes deterministic gates;
- scene persistence/disclosure policy permits the operation;
- lifecycle and tombstones are respected;
- lineage remains available;
- the write is idempotent and revision-fenced.

Failure becomes `leave_as_evidence`, held review, or no change.

## Bounded relation decisions

| Decision | Meaning | Default effect |
|---|---|---|
| `reinforce_memory` | materially the same meaning | add evidence; update strength; no new retrieval-visible MEM |
| `refine_memory` | compatible new specificity | revise existing MEM; preserve prior revision |
| `reinterpret_memory` | grounded facts remain while subjective significance changes | revise subjective meaning with lineage |
| `supersede_memory` | newer durable state replaces current state | publish successor; preserve temporal history |
| `contradict_memory` | unresolved conflict | preserve both paths; link contradiction; lower certainty or hold |
| `relate_memory` | relevant but not the same meaning | typed link; no confidence reinforcement |
| `create_memory` | distinct durable meaning or episode | create new MEM |
| `leave_as_evidence` | valid but not ready or valuable as MEM | retain evidence only |

## Deciding strongly similar

### Candidate generation

Use a bounded union of:

```text
exact normalized key
FTS / exact terms
metadata and entity match
static vector similarity
typed relations
```

These channels find candidates; they do not authorize consolidation.

### Hard compatibility gates

Reject merge candidates that differ materially in:

- character or namespace;
- subject or entity;
- polarity;
- modality;
- temporal validity or time scope;
- memory kind;
- project, relationship, scene, or audience scope;
- lifecycle state;
- correction or tombstone authority.

Similar text must not merge different actors, preferences with actions, intentions with completed events, role-play with ordinary conversation, private and public scope, or past and current states.

### Main-LLM judgment

After hard gating, the main LLM decides whether the character experiences the evidence as confirmation, refinement, reinterpretation, successor, contradiction, relation, new memory, or non-memory.

It receives only a bounded neighborhood. The online sidecar and provisional reaction are hints, not substitutes for this decision.

### Conservative policy

False merge is more damaging than a temporary duplicate. Ambiguity should prefer `leave_as_evidence`, `relate_memory`, or a later-consolidatable new MEM.

Thresholds must be calibrated on RelayLM-specific Japanese and mixed-language examples.

## Memory strength

Strength is not one opaque score.

- **Evidence confidence:** how strongly governed evidence supports grounded content.
- **Stability:** whether the memory is durable across time and independent contexts.
- **Salience:** importance to this character's future interaction.
- **Subjective conviction:** how strongly the character holds the interpretation.
- **Reaction intensity:** how strongly the character reacted at the source moment; this does not increase evidence confidence by itself.

Subjective conviction and reaction intensity cannot turn weak evidence into fact.

### Independence groups

Derivatives of one source do not count as independent confirmation:

```text
one user message
  -> raw event
  -> sidecar
  -> Session Evidence Overlay candidate
  -> session summary
  -> extracted MEM candidate
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

Unknown validity does not default to observation time. File modification time is not semantic validity.

The same explicit-facet approach applies beyond time. Retrieval and consolidation may use subject, entity, predicate, polarity, modality, project, relationship, scene, audience, correction authority, and lifecycle as explainable compatibility signals.

## Authority and storage

### Protected source domain

Owns content-bearing evidence, speaker, timestamp, import provenance, correction origin, scene/audience references, and independence grouping. Subjective formation cannot rewrite it.

### RelayCTX Session Evidence Overlay (CTX-OVL) store

The first implementation should be app-scoped RAM state with strict composite isolation and revision fencing. It is a rebuildable short-term projection, not a second MEM authority.

An optional restart checkpoint may be considered only after user value, privacy, and recovery semantics are measured.

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

Owns non-rebuildable operation state:

- jobs, claims, and leases;
- apply intents and idempotency;
- receipts and failures;
- lifecycle tombstones;
- durable usage events when behavior depends on them.

It must not become a second authority for MEM prose or Session Evidence Overlay content.

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

The receipt is the commit marker. Recovery uses pre/post digests without double application.

## Retrieval

Ordinary conversation retrieves Subjective MEM, not every supporting evidence item. Evidence is expanded only for correction, contradiction, audit, exact confirmation, or grounding.

### Multi-stage path

```text
1. resolve bounded query facets, including temporal intent when present
2. character / namespace / lifecycle filter
3. exact / FTS / metadata candidates
4. static vector candidates
5. deterministic rank fusion and facet compatibility
6. apply current-session overlay boosts and shadows
7. canonical-MEM collapse
8. bounded typed-relation expansion
9. bounded rerank
10. token-aware context packing
```

### Hybrid Retrieval

- exact search handles IDs, names, and precise terms;
- FTS handles lexical relevance;
- metadata handles entity, scene, audience, modality, lifecycle, and temporal validity;
- static vectors handle Japanese paraphrase and semantic similarity;
- Session Evidence Overlay handles current-session provisional corrections and state changes.

Vector-only retrieval is insufficient for negation, actor identity, temporal change, quantities, exact terms, role-play, audience, and preference-versus-action distinctions.

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

### Session-overlay interaction

Within one correctly scoped session:

```text
current explicit user statement or correction
  > compatible Session Evidence Overlay candidate
  > active durable MEM
  > superseded or historical MEM
```

The overlay may shadow a durable candidate only for the current session and only when grounded by current-session evidence. It does not change durable lifecycle.

### Collapse and relations

Supporting evidence for one current MEM occupies one retrieval slot. Only a bounded relation neighborhood, normally one hop, is expanded.

### Ranking priority

```text
query relevance
  > character / namespace / entity scope
  > current-session explicit correction authority
  > temporal, polarity, modality, project, scene, and audience compatibility
  > lifecycle and correction authority
  > evidence confidence
  > stability and bounded salience
  > recency and bounded usage
```

Recency must not outrank a known validity mismatch. Current-session shadowing must not leak across scope keys. Usage must have bounded weight.

A reranker may select only existing IDs from a bounded top set. It may not invent memory. Candidates passed to the main LLM should include compact ranking reasons and relevant temporal or semantic facets.

## SOUL Lab implications

Future Memory Explorer needs stable identity, scope, grounded/subjective distinction, lifecycle, tags, semantic facets, provenance, evidence count, observation and validity times, usage, relations, operation status, Correct, Forget, Restore, and Pin.

A future session-continuity inspector may separately expose provisional overlay items, source turns, shadows, corrections, and SLP acknowledgement state. It must clearly label them as non-durable.

SOUL Lab remains an exploration and curation surface, not a mandatory approval queue, raw database editor, independent authority, or source-evidence rewriter.

## Evidence from Tracks A-D and overlay feasibility

### Track A: inventory

Provides storage, reader/writer, invocation, configuration, and dependency evidence for cutover. It is not deletion authority.

### Track B: characterization

Protects semantic invariants such as autonomous formation, provenance, namespace isolation, lifecycle authority, idempotency, and failure honesty.

Current file-layout details describe today's backend and must be replaced during hard cutover, not preserved as permanent layout.

### Track C: Memory Explorer mock

Validates product needs for search, provenance, tags, correction, lifecycle, relations, usage, and operation visibility. Browser-local state is not authority.

### Track D: Markdown/SQLite spike

Supports deterministic Markdown parse/render, rebuildable FTS, incremental projection, intent/digest/receipt recovery, idempotency, stale-snapshot protection, and schema versioning.

It remains an isolated experiment and does not validate final hidden-successor/Restore semantics, vector Retrieval, semantic consolidation, sidecar quality, overlay behavior, Windows/WSL behavior, backup, migration, or large-scale quality.

### Session Evidence Overlay feasibility

[Session Evidence Overlay implementation feasibility](../evidence/implementation/session-evidence-overlay-feasibility.md) finds the design implementable using existing session identity, request-local private candidates, RelayCTX Unpack principles, finalized-turn capture, protected source lineage, and target short-term-context packing.

Missing work includes an isolated cross-request store, deterministic reconciliation, next-turn packing, Retrieval interaction, stream-safe update ordering, RelaySLP acknowledgement, TTL, eviction, concurrency fencing, and optional restart recovery.

## Main risks and safeguards

| Risk | Required safeguard |
|---|---|
| hallucinated subjective meaning | Shared Assessment first; unsupported-inference output; grounding validator; abstention |
| online answer degradation | minimal optional sidecar; strict budget; no response-path retry; deferred detailed analysis |
| sidecar fabrication | verified evidence spans; system-owned metadata; nullable fields; sidecar remains advisory |
| hot emotional interpretation becomes durable fact | EMO-decoupled formation; provisional reaction separately typed; evidence validator |
| scene context is lost | normalized SCN facts retained independently of transient expression pressure |
| scene policy changes content meaning | persistence/disclosure policy evaluated after formation, not used to invent content |
| stale overlay shadows durable MEM | bounded TTL; revision fencing; source-lineage acknowledgement; fail-open to durable Retrieval |
| cross-session contamination | composite scope key; no global fallback; privacy-safe diagnostics |
| over-merge | hard semantic gates; conservative threshold; revision/evidence preservation |
| under-merge | scheduled consolidation; Retrieval collapse; duplicate-rate monitoring |
| temporal misranking | explicit validity and temporal intent; recency cannot override known mismatch |
| identity drift | MEM cannot mutate SOUL; SOUL change remains separate approval path |
| popularity feedback | relevance first; bounded usage weight; diversity and collapse |
| sensitive inference | direct authority required; weak or sensitive inference stays held or evidence-only |

## Evaluation gates

### Aggregation quality

Build a labeled Japanese and mixed-language set covering:

- duplicate and paraphrase;
- refinement and reinterpretation;
- temporal successor;
- contradiction;
- related but distinct;
- different subject, relationship, project, modality, scene, and audience;
- fact versus preference, intention, hypothetical, quotation, joke, and role-play;
- separate episodes with similar wording;
- user correction and tombstone;
- raw, sidecar, overlay, summary, and extracted derivatives of one source.

Primary safety metric: **false merge rate**.

Also measure relation accuracy, abstention, unsupported inference, lineage preservation, subjectivity consistency, SCN-scope accuracy, EMO leakage into grounded claims, and cross-character leakage.

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
- subject, polarity, modality, temporal-kind, scene, audience, correction, and change-signal accuracy;
- unsupported-field invention;
- `none` / `possible` / `explicit` disposition accuracy;
- downstream formation quality with and without the sidecar.

No online sidecar design is eligible if it materially degrades normal conversation or requires synchronous retries.

### RelayCTX Session Evidence Overlay (CTX-OVL)

Evaluate:

- immediate next-turn continuity with RelaySLP delayed;
- explicit correction and retraction behavior;
- current-session shadow precision and false-shadow rate;
- character, namespace, session, user, room, and scene isolation;
- concurrent same-session revision fencing;
- stream-completion followed immediately by the next request;
- TTL and eviction behavior;
- malformed sidecar and missing-session fallbacks;
- RelaySLP acknowledgement, replay, duplicate receipt, and stale acknowledgement;
- restart with and without optional checkpoint recovery;
- prompt token overhead and conversation-quality impact.

The synchronous overlay path is ineligible if it performs LLM inference, vector construction, fsync, or RelaySLP inline with visible response finalization.

### Conditioning ablation

Compare durable formation under:

1. Shared Assessment only;
2. Shared Assessment plus SOUL;
3. Shared Assessment plus SOUL and normalized SCN facts;
4. the recommended model plus bounded REL history;
5. the recommended model with current EMO incorrectly included as a negative control;
6. direct copying of the provisional hot interpretation as a negative control.

Measure:

- factual grounding;
- role-play and audience-scope accuracy;
- remembered-character feeling;
- SOUL consistency;
- relationship continuity;
- emotional overinterpretation;
- persistence of transient mood bias;
- correction behavior;
- usefulness of retained reaction evidence.

The recommended model is eligible only if normalized SCN facts improve contextual correctness without transient expression pressure or current EMO contaminating durable claims.

### Retrieval scale

Evaluate at 10,000, 50,000, and 100,000 MEM:

- FTS only;
- vector only;
- hybrid fusion;
- hybrid plus semantic-facet and temporal ranking;
- hybrid plus Session Evidence Overlay interaction;
- hybrid plus canonical collapse;
- hybrid plus relation expansion;
- optional bounded reranking.

Measure recall@k, precision@k, duplicate rate@k, relevant-fact coverage, contradiction visibility, current-state accuracy, historical-period accuracy, transition-chain accuracy, false-shadow rate, p50/p95 latency, CPU/RAM, build/rebuild time, incremental update, explainability, and token-pack quality.

### Storage and platform

Validate Linux, WSL Linux filesystem, supported Windows paths, rename/fsync behavior, WAL/busy handling, crash windows, cache corruption/rebuild, backup/restore, and migration rehearsal. Explicitly decide whether `/mnt/c` is unsupported.

## Recommended implementation sequence

1. Accept or reject this direction through an ADR.
2. Run a semantic-sidecar and conditioning-ablation spike.
3. Implement CTX-OVL-0: exact overlay contract and isolated in-memory store in dry-run/read-only form.
4. Implement CTX-OVL-1: non-stream current-session continuity with bounded local update.
5. Implement CTX-OVL-2: Retrieval boost/shadow and dynamic-suffix packing.
6. Implement CTX-OVL-3: stream-safe finalization ordering.
7. Implement CTX-OVL-4: RelaySLP source-lineage acknowledgement and overlay cleanup.
8. Consider CTX-OVL-5 restart recovery only if measured user value justifies durable checkpoint complexity.
9. Run the aggregation and Retrieval-scale spikes.
10. Correct and extend the storage spike with final lifecycle semantics and complete crash tests.
11. Define exact contracts and rehearse import, rebuild, backup, rollback, and migration.
12. Perform one hard cutover without permanent dual-read or dual-write.

## Non-goals

This proposal does not:

- change current runtime behavior;
- require a full structured answer on every turn;
- require response-path retries for sidecar validity;
- make the online main LLM the authority for MEM writes or system metadata;
- make Session Evidence Overlay a second durable memory store;
- make current EMO a durable truth source;
- remove normalized SCN facts from evidence interpretation;
- require per-memory approval;
- authorize MEM-to-SOUL mutation;
- make subjective MEM shared truth;
- expose full source evidence by default;
- select an embedding or vector database;
- require a graph database or one file per memory;
- adopt Obsidian as a dependency;
- approve Track D for production;
- claim Windows/WSL validation;
- define Purge;
- authorize automatic sensitive inference.

## Open decisions

1. Exact bounded semantic sidecar schema and token/item budget.
2. Whether the sidecar is same-generation, constrained secondary output, deferred re-analysis, or a measured hybrid.
3. Exact CTX evidence-envelope and relative-time-resolution contract.
4. Exact CTX-OVL schema, composite scope key, TTL, and revision protocol.
5. Exact normalized SCN facts and scene persistence/disclosure policy schemas.
6. Whether provisional reaction evidence is stored only in protected source, the overlay, episodic MEM metadata, or a bounded combination.
7. Exact Shared Assessment schema.
8. Exact SOUL and REL slices and prompt contract.
9. When to regenerate wording versus update strength only.
10. Reconciliation of user Markdown edits with grounding.
11. Japanese static embedding and vector index.
12. Automatic `reinforce_memory` precision threshold.
13. Held versus evidence-only conditions.
14. Representation of confidence, stability, salience, conviction, and reaction intensity.
15. Relation-expansion budget.
16. Reinterpretation after approved SOUL revision.
17. Usage-event and overlay-retention privacy.
18. Accepted response-quality, latency, false-shadow, and EMO-leakage thresholds.

## Final conclusion

RelayLM should adopt **reinforcement-first subjective memory formation** with a bounded semantic handoff and current-session provisional continuity:

```text
natural response
  + optional semantic sidecar
  + hot SCN/EMO-conditioned provisional interpretation
  -> CTX-owned evidence normalization
  -> bounded RelayCTX Session Evidence Overlay (CTX-OVL)
  -> immutable evidence
  -> Shared Assessment using normalized scene facts
  -> deterministic semantic and temporal candidate ranking
  -> SOUL-centered, REL-bounded, EMO-decoupled subjective reflection
  -> scene-policy persistence/disclosure gate
  -> reinforce / refine / reinterpret / supersede /
     contradict / relate / create / leave as evidence
  -> grounded Subjective MEM
  -> hybrid Retrieval with canonical collapse
```

This preserves the factual safety of the observation model while adding RelayLM's distinctive value:

- the character may react emotionally in the moment;
- the ongoing conversation remembers that provisional interpretation;
- later reflection can cool, revise, or reject it;
- durable memory still remains recognizably character-specific.

The sidecar and overlay are useful only when they improve continuity and deferred memory work without reducing conversation quality. They remain advisory and rebuildable. CTX owns evidence metadata and session continuity, RelaySLP owns assessment and subjective formation, scene policy owns persistence/disclosure gating, and MEM owns durable state.