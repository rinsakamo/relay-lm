---
relaylm_doc_type: adr
relaylm_authority: decision_to_adopt_subjective_mem_direction
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-17
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - decision is superseded
  - an accepted owning contract contradicts or narrows a fixed boundary in this ADR
  - the Primary/Secondary-to-Subjective-MEM authority mapping changes
  - the Markdown/cache/operations authority separation changes
  - canonical lifecycle-visible authority changes
  - storage migration or permanent compatibility policy changes
relaylm_not_authoritative_for:
  - exact SourceEvent schema or evidence-admission contract
  - exact CTX evidence envelope or CTX-OVL schema
  - exact Subjective MEM, Shared Assessment, relation, strength, temporal, or lifecycle schema
  - exact Markdown syntax, page layout, stable ID representation, cache tables, or storage/commit protocol
  - embedding model, vector index, thresholds, or reranking
  - product-knowledge packaging, corpus, retrieval integration, attachment, update, or lifecycle behavior
  - migration, backup, rollback, or platform details
  - project-level implementation sequencing, scheduling, completion, or approval
  - current runtime implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0003: Subjective MEM direction — formation, consolidation, retrieval, and storage authority

This ADR accepts the stable cross-component direction for character-scoped Subjective MEM: its authority, the evidence boundary it depends on, the components that may condition or gate its formation, and the invariants later contracts must preserve. It does not define exact schemas, thresholds, storage mechanics, migration mechanics, or an implementation plan.

## Status

Accepted as target architecture on 2026-07-17. Implementation remains pending and separately governed. This ADR does not authorize a production runtime or storage change.

## Context

RelayLM already separates observation from character-conditioned belief in [Character-conditioned belief without rewriting observation](character_conditioned_belief_model.md). That ADR defines an observation ledger, character-independent shared evidence assessment, character-conditioned provisional belief, action impulse, relationship/scene/audience/disclosure permission, and final utterance as distinct stages.

[Memory Lifecycle Design](../architecture/memory_lifecycle_design.md) separately defines short-term CTX, Primary MEM / Experience MEM, Secondary MEM / Crystallized MEM, and the explicit character-source layer. It also establishes file-first memory pages, autonomous ordinary formation, governed lifecycle operations, and the rule that Primary and Secondary MEM must not collapse into one undifferentiated bucket.

The proposal associated with PR #586 was treated as non-authoritative design input. This ADR does not adopt that proposal wholesale. Any remaining proposal material must be reconciled separately against accepted owning ADRs and contracts.

Two adjacent accepted authorities constrain this decision without being restated here:

- [RelayATN pre-request authority separation](relayatn_pre_request_authority_separation.md) owns the pre-request turn-admission boundary. RelayATN does not own evidence admission, RelayCTX working state, subjective formation, relation, lifecycle, persistence, or durable retrieval authority.
- [Showcase, Public Starter, and Product Knowledge Ownership](../architecture/character-workspace/showcase-starter-product-knowledge.md) owns the asset-class and product-knowledge boundary. Subjective MEM does not absorb or redefine that authority.

Without one durable direction, later SourceEvent, RelayCTX, Subjective MEM schema, storage, retrieval, and migration contracts could independently invent incompatible meanings for evidence, character scope, similarity, lifecycle, or authority.

## Decision

RelayLM accepts the following stable direction for Subjective MEM. Exact field-level and operational contracts remain deferred.

### Evidence and assessment terminology

This ADR introduces stable names for two already-established authority layers; it does not create additional stores:

- **Protected Source Evidence** corresponds to the observation ledger. Once evidence is admitted, character components do not rewrite its admitted content or provenance. Corrections are represented through governed successor, retraction, or appended records rather than character-side mutation. Retention, expiry, redaction, quarantine, consent withdrawal, and purge remain owned by the governed evidence contract.
- **Shared Assessment** corresponds to character-independent shared evidence assessment. It may record support, contradiction, refinement, temporal change, uncertainty, competing hypotheses, or an unresolved outcome without acquiring character identity.

Exact SourceEvent identity, retention, consent, source-authority, privacy, replay, correction, retraction, and evidence-admission mechanics belong to a governed SourceEvent / evidence-admission contract.

### Subjective MEM identity and orthogonal dimensions

Subjective MEM is the umbrella authority for character-scoped durable personal memory. It separates:

- **grounded content**: what a governance- and schema-valid Shared Assessment supports, including supported uncertainty, unresolved state, or competing interpretations; and
- **subjective meaning**: what a particular character believes, weights, notices, or concludes from that grounded basis.

A governance- and schema-valid Shared Assessment is not necessarily a claim that external truth has been proven. It may remain uncertain, unresolved, contradicted, or represented by competing hypotheses.

Subjective MEM does not, by this ADR alone, collapse, replace, or supersede the current Primary MEM / Experience MEM and Secondary MEM / Crystallized MEM lifecycle stages.

Primary versus Secondary describes formation and consolidation stage. Semantic versus Episodic describes memory kind. These dimensions are orthogonal and may form a cross-product.

The follow-on Subjective MEM schema and lifecycle contract must define the current-to-target mapping and decide whether the Primary/Secondary distinction remains an explicit persisted field, a derived lifecycle stage, or another compatible representation. Existing accepted lifecycle behavior remains authoritative until an owning contract changes it.

Subjective MEM is distinct from RelayCTX current-request and current-session working state. Any future CTX-OVL remains RelayCTX-owned, bounded, rebuildable, and non-durable; it is not a pending or durable MEM store.

Official product knowledge is outside Subjective MEM authority. Subjective MEM formation, consolidation, relationship-evidence processing, and ordinary personal-memory lifecycle operations must not treat official product knowledge as personal MEM. Its physical corpus, retrieval integration, attachment, update, and lifecycle semantics remain owned by the separate product-knowledge decision.

### Formation conditioning

#### SOUL-centered subjective formation

Protected Source Evidence, Shared Assessment, and grounded-content determination remain independent of SOUL.

Only after a governance- and schema-valid Shared Assessment exists may a bounded, identified SOUL revision condition subjective meaning, salience, interpretation, and relation choice. The Shared Assessment may still be uncertain, unresolved, or represented by competing hypotheses. SOUL cannot change what the evidence supports, convert uncertainty into fact, rewrite provenance, or receive direct mutation from Subjective MEM.

#### SCN-grounded persistence and disclosure

RelaySCN may gate persistence eligibility, scene and audience scope, and disclosure for Subjective MEM. RelaySCN does not author, invent, or rewrite grounded content or subjective meaning and remains outside durable-memory write authority.

#### REL-bounded applicability

RelayREL may constrain applicability, trusted target identity, relationship scope, salience, and disclosure for relationship-scoped Subjective MEM. Unknown or conflicting participant identity cannot become participant-scoped or relationship-scoped memory authority. Subjective MEM does not directly mutate `relationships/<target>.md`.

#### EMO-decoupled durable truth

Current EMO or provisional reaction may be retained as separately typed, non-authoritative formation evidence, subject to later evidence and schema contracts. It is never copied automatically into grounded content or subjective meaning.

Affective gain, current EMO, one-turn impressions, and provisional reaction cannot by themselves prove a user fact, increase evidence confidence, or determine durable Subjective MEM meaning.

### Consolidation and relation direction

Strongly similar evidence should normally produce an explicit relation decision or abstention rather than automatically creating a near-duplicate retrieval-visible Subjective MEM.

Possible later contract outcomes include reinforcement, refinement, reinterpretation, supersession, contradiction, relation, creation, or leaving the input as evidence only. This ADR does not accept the exact taxonomy or decision schema.

Embedding or lexical similarity is candidate generation only. It is never merge authority by itself and never bypasses hard compatibility, identity, temporal, scope, lifecycle, correction, or provenance gates.

False merge is treated as more damaging than temporary duplication because a false merge silently corrupts meaning and lineage. When compatibility is uncertain, the system must preserve separation or abstain.

### Retrieval direction

Within the personal-memory path, ordinary retrieval targets canonical Subjective MEM rather than every supporting observation or Shared Assessment record.

Grounded provenance must remain reachable from the selected Subjective MEM without requiring normal conversation to surface every supporting source item. Exact candidate generation, canonical collapse, relation expansion, temporal filtering, ranking, context budget, and reranking remain separate contracts.

This retrieval direction does not define product-knowledge retrieval behavior and does not make CTX-OVL a durable retrieval corpus.

### Storage authority direction

Markdown is the human-readable steady-state authority direction for durable Subjective MEM prose, user-visible organization, and canonical lifecycle-visible state. Memory pages remain human-scale pages rather than one file per memory record.

A rebuildable SQLite cache may project Markdown for full-text search, metadata, vectors, semantic facets, relations, lifecycle, and ranking. Deleting or rebuilding that cache must not destroy committed Subjective MEM, canonical lifecycle-visible state, or governed evidence.

A separate durable operations database may own operational anti-reformation tombstones, jobs, claims, leases, intents, idempotency, receipts, failures, and durable usage events. Such a tombstone enforces an operation but is not a second authority for Subjective MEM prose or canonical active, hidden, restored, or successor representation.

The exact atomic reconciliation between Markdown lifecycle state and operational tombstones, together with page layout, stable IDs, cache tables, commit protocol, crash recovery, and platform behavior, belongs to the Markdown/SQLite storage-authority and commit-protocol contract.

### Migration principle

This ADR independently accepts a no-permanent-dual-authority principle for a future Subjective MEM storage migration. A production migration must converge on one accepted authority and must not retain permanent dual-read or dual-write behavior.

[ADR 0002](0002-documentation-information-architecture.md) is a documentation-cutover precedent only. This reference does not extend ADR 0002's authority to runtime or storage behavior.

Exact migration, backup, restore, rollback, rehearsal, platform-support, and old-authority retirement mechanics remain deferred.

### Deferred owning contracts

This ADR authorizes no exact schema. Separate decisions must own at least:

- governed SourceEvent and evidence admission;
- CTX evidence envelope and CTX-OVL;
- Shared Assessment and Subjective MEM fields;
- Primary/Secondary lifecycle mapping and Semantic/Episodic kinds;
- relation decisions, compatibility gates, strength dimensions, temporal validity, correction, and lifecycle;
- Markdown syntax, page layout, stable IDs, cache projection, operations state, and commit protocol;
- embedding, vector, threshold, reranking, and retrieval-fusion choices;
- product-knowledge packaging and runtime integration;
- migration, backup, rollback, and platform support.

### Contract prerequisite boundary

A production implementation must not rely on an undefined deferred contract. Acceptance of the relevant owning contract is a necessary prerequisite for implementing that contract's authority, but it is not, by itself, project-level implementation approval.

Independent characterization tests, evidence collection, isolated experiments, evaluation fixtures, and implementation work whose required owning contracts are already accepted are not globally blocked by unrelated deferred contracts.

Exact cross-PR sequencing, scheduling, and implementation approval remain owned by the [Project Execution Plan](../architecture/project_execution_plan.md) and current status authority. This ADR itself does not authorize a production runtime or storage change.

## Consequences

### Positive

- Later contracts share one evidence, character-scope, and authority vocabulary.
- Character-specific meaning can remain expressive without corrupting source provenance or Shared Assessment.
- Primary/Secondary lifecycle stage remains distinct from Semantic/Episodic memory kind.
- Similarity-based consolidation begins from false-merge safety rather than duplicate-count reduction.
- Markdown, rebuildable cache, and durable operations state have non-overlapping high-level authorities before exact schemas are chosen.
- RelayATN, CTX-OVL, product knowledge, SOUL, SCN, REL, and EMO remain bounded by their owning decisions.

### Costs

- More explicit state classes, lineage, abstention, and scope discipline are required.
- Each deferred area still requires an accepted owning contract before production implementation can rely on that area's authority.
- Current Primary/Secondary representation and the accepted umbrella terminology coexist until the schema/lifecycle contract defines the mapping.
- Retrieval and storage implementation cannot infer exact fields, thresholds, or commit behavior from this ADR alone.

## Rejected alternatives

### Define exact schemas and implementation sequencing here

Rejected because SourceEvent, RelayCTX, Subjective MEM, storage, retrieval, migration, and product knowledge have different owners, update triggers, and failure costs. Combining them would violate one-document/one-primary-authority discipline.

### Adopt PR #586 wholesale

Rejected because it is design input that mixes recommendations belonging to RelayATN, RelayCTX, evidence ingress, Subjective MEM, retrieval, and storage owners. Accepted parts must live in their owning ADRs and contracts.

### Make Subjective MEM a third competing durable-memory layer

Rejected because Subjective MEM is an umbrella authority vocabulary, not a new lifecycle stage beside Primary and Secondary MEM. Primary/Secondary and Semantic/Episodic remain orthogonal dimensions pending the owning schema/lifecycle contract.

### Collapse Primary and Secondary MEM into one bucket

Rejected because formation-stage experience memory and later consolidated memory have different latency, lineage, reconciliation, and retrieval roles. This ADR does not erase that accepted distinction.

### Let SOUL, SCN, REL, or EMO determine grounded truth

Rejected because those components may condition subjective meaning, gate persistence, constrain applicability, or provide non-authoritative reaction evidence, but they cannot rewrite Protected Source Evidence or character-independent Shared Assessment.

### Let embedding similarity decide merges

Rejected because statistical proximity is not evidence of subject, identity, modality, polarity, temporal, scope, lifecycle, or relation compatibility. It can discover candidates only.

### Store durable MEM prose or canonical lifecycle in two authorities

Rejected because Markdown and an operations database would become competing sources of truth. Operations state may enforce and recover mutations but cannot own a second copy of canonical memory prose or lifecycle-visible representation.

### Preserve permanent dual-read or dual-write migration behavior

Rejected because permanent compatibility would preserve ambiguous authority and make recovery, correction, Forget, and rebuild behavior dependent on two live stores.

## Fixed boundaries

- Admitted Protected Source Evidence content and provenance are not rewritten by Subjective MEM or character components; retention and deletion remain governed separately.
- Shared Assessment and grounded-content determination remain character-independent and may preserve uncertainty, unresolved outcomes, or competing hypotheses.
- Subjective MEM separates grounded content from character-scoped subjective meaning.
- Primary/Secondary lifecycle stage and Semantic/Episodic memory kind are orthogonal.
- SOUL conditions only bounded subjective formation after a governance- and schema-valid Shared Assessment and is never directly mutated by Subjective MEM.
- RelaySCN gates persistence and disclosure but does not invent memory content.
- RelayREL constrains trusted applicability, target, and disclosure but does not silently mutate durable relationship state.
- Current EMO or provisional reaction cannot by itself prove a fact or determine durable meaning.
- Similarity generates candidates only; embedding similarity is never merge authority.
- False merge is treated as more damaging than temporary duplication.
- Official product knowledge remains outside Subjective MEM authority.
- CTX-OVL, if implemented under its owning contract, is non-durable RelayCTX working state and is never writable by RelayATN.
- Markdown is the steady-state authority direction for Subjective MEM prose and canonical lifecycle-visible state.
- Rebuildable cache state is projection only.
- Operations state does not own Subjective MEM prose or a second canonical lifecycle representation.
- A future production storage migration introduces no permanent dual-read or dual-write authority.
- Owning-contract acceptance is a prerequisite for relying on that contract's authority, not project-level implementation approval.
- This ADR does not authorize runtime implementation or exact sequencing.

## Related documents

- [Character-conditioned belief without rewriting observation](character_conditioned_belief_model.md)
- [RelayATN pre-request authority separation](relayatn_pre_request_authority_separation.md)
- [ADR 0002: Adopt authority-first documentation architecture by hard cutover](0002-documentation-information-architecture.md)
- [Memory Lifecycle Design](../architecture/memory_lifecycle_design.md)
- [RelayMEM MVP Design](../architecture/relaymem_mvp_design.md)
- [RelayMEM / RelaySLP Current / Target Boundary](../architecture/relaymem_slp_current_target.md)
- [Character Workspace Architecture](../architecture/character-workspace/system.md)
- [Showcase, Public Starter, and Product Knowledge Ownership](../architecture/character-workspace/showcase-starter-product-knowledge.md)
- [RelaySCN MVP Scene Policy](../architecture/relayscn_mvp_scene_policy.md)
- [RelayREL Relationship State](../architecture/relationship/relationship-state.md)
- [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md)
- [Project Execution Plan](../architecture/project_execution_plan.md)
- [Project Status](../PROJECT_STATUS.md)
