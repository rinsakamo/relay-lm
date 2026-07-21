---
relaylm_doc_type: contract
relaylm_authority: shared_assessment_and_subjective_mem_logical_contract
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Shared Assessment identity, revision, support, authorization, or formation-time receipt changes
  - Subjective MEM formation decision, output linkage, relation, lifecycle, or retrieval-visible authority changes
  - Primary/Secondary or Semantic/Episodic mapping changes
  - SOUL, SCN, REL, EMO, or product-knowledge boundaries change
relaylm_not_authoritative_for:
  - exact governed SourceEvent capture or evidence-governance storage
  - CTX-OVL, RelayATN, or current-request context packing
  - Markdown or SQLite physical storage and commit protocol
  - embeddings, vector indexes, ranking, or retrieval-fusion algorithms
  - runtime implementation, migration, deployment, or completion status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0003-subjective-mem-direction.md
  - ../architecture/memory/formation.md
  - governed-evidence-contract-family.md
  - relayctx-session-evidence-overlay.md
---
# Shared Assessment and Subjective MEM Contract

## Status and purpose

This is the normative **target** logical contract for character-independent Shared Assessment and character-scoped Subjective MEM. It does not claim that runtime implementation, physical storage, migration, or deployment is complete.

The contract consumes governed Evidence authority and the accepted Subjective MEM direction. It does not redefine Contract 1, CTX-OVL, RelayATN, RelaySLP scheduling, or storage authority.

## Fixed authority layers

```text
Protected Source Evidence
  -> Shared Assessment revision
  -> formation-time authorization receipt
  -> Subjective MEM decision
  -> exact decision result
  -> Subjective MEM revision / relation / lifecycle
  -> one logical current-state selector
```

**Shared Assessment remains character-independent.** It records support, uncertainty, contradiction, refinement, temporal change, or competing hypotheses without acquiring SOUL, character, REL, SCN, EMO, or STYLE identity.

**Subjective MEM separates grounded content from subjective meaning.** Grounded content must equal and remain SHA-256-bound to the exact referenced Shared Assessment revision. Subjective meaning may be conditioned by an identified SOUL revision only after the assessment is schema-valid, governance-valid, and recorded as `current_admitted` at decision time.

Official RelayLM product knowledge is outside this contract and must not be formed, reinforced, forgotten, or retrieved as personal Subjective MEM.

## Shared Assessment authority

A `SharedAssessmentRevision`:

- references one to 64 governed Evidence items;
- preserves source origin, evidence-space identity, authorization, and mandatory lineage revision;
- carries supported content, uncertainty, temporal state, and support state;
- stores `supported_content_digest = sha256(UTF-8 supported_content)`;
- has no character identifier or character-conditioned field;
- advances through immutable consecutive revisions;
- may supersede only the immediate resolvable revision of the same logical assessment.

Exactly one `SharedAssessmentCurrentState` may exist for each logical `assessment_id`. It selects the latest persisted revision. An active current state must be `current_admitted`; restricted or purged evidence cannot continue to authorize new formation.

A later Shared Assessment revision does not invalidate historically valid decisions or Subjective MEM revisions. Each decision therefore records an immutable formation-time authorization receipt containing the exact assessment revision, active lifecycle state, and `current_admitted` authorization observed at decision time. The receipt must name the assessment revision that was latest at that time; it is distinct from the assessment's current state now.

## Subjective formation boundary

A `SubjectiveMemDecision` consumes:

- an exact Shared Assessment revision and its formation-time authorization receipt;
- an identified character;
- a consistent trusted participant, relationship, scene, or character-private scope;
- exact existing compatible memory candidates;
- deterministic policy constraints.

Similarity is candidate generation only:

```yaml
similarity_granted_authority: false
```

Embedding or lexical proximity cannot authorize create, reinforce, refine, reinterpret, supersede, contradict, relate, lifecycle mutation, or retrieval visibility.

The false merge cost is treated as higher than temporary duplication. When identity, polarity, temporal meaning, audience, lifecycle, or provenance compatibility is uncertain, the decision is `hold`, `abstain`, or `leave_as_evidence`.

Decision outcomes are:

- `create`
- `reinforce`
- `refine`
- `reinterpret`
- `supersede`
- `contradict`
- `relate`
- `hold`
- `abstain`
- `leave_as_evidence`

Decision output linkage is exact and bidirectional:

- `create` requires one resolvable result memory reference at revision 1 and forbids a merge target;
- `reinforce`, `refine`, `reinterpret`, `supersede`, and `contradict` require an exact target that was the character-and-scope-compatible current logical memory at decision time and an exact consecutive successor result;
- `relate` requires an exact target and one resolvable result relation ID;
- `hold`, `abstain`, and `leave_as_evidence` forbid memory and relation results;
- every result memory records an `authorization_ref` back to its formation decision;
- every result relation records `authorizing_decision_id` back to its relation decision.

A decision that names a nonexistent result, a result authorized by another decision, another character, another scope, a nonconsecutive successor, or a stale target fails closed.

## Character-component boundaries

- SOUL may condition subjective meaning, salience, interpretation, and relation choice. It cannot change supported content, uncertainty, provenance, or authorization.
- SCN may gate persistence and disclosure. It cannot invent memory content. Scene-scoped durable MEM requires an identified scene-policy revision.
- REL may constrain trusted participant identity, relationship scope, salience, and disclosure. Unknown or conflicting identity cannot authorize participant- or relationship-scoped durable MEM. Relationship-scoped durable MEM requires an identified relationship revision.
- EMO may be retained only as separately typed non-authoritative formation evidence. It cannot prove a user fact or increase grounded confidence.
- STYLE is not a meaning or evidence source.

## Orthogonal dimensions

Primary/Secondary and Semantic/Episodic are orthogonal.

- `formation_stage`: `primary | secondary`
- `memory_kind`: `episodic | semantic`

Consolidation may move a logical memory from Primary to Secondary without changing Semantic/Episodic kind merely because consolidation occurred.

Strength is multidimensional:

- grounded confidence;
- subjective conviction;
- salience;
- governed reinforcement count;
- explicit strength basis.

No single scalar may collapse evidence support, subjective conviction, relationship salience, and retrieval rank.

## Scope and identity

Scope is exactly one of:

- character-private;
- trusted participant;
- relationship-bounded;
- scene-bounded.

Participant and relationship scope require trusted participant identity. Unknown or conflicting identity fails closed and cannot shadow or mutate participant- or REL-scoped durable MEM.

Strong relationship does not imply disclosure permission. Audience and persistence boundaries are explicit and are compared exactly across decision, target, result, and relation records.

## Revision and current-state authority

Subjective MEM revisions are immutable. A successor preserves the logical `memory_id`, increments revision exactly once, references the immediate predecessor, and names exactly one authorizing formation decision or lifecycle transition.

Exactly one `SubjectiveMemCurrentState` may exist for each `(character_id, memory_id)`. It must select the latest persisted revision for that character and logical memory. Multiple selector records with different state IDs are still conflicting logical current states and fail closed.

Only the exact current revision may enter ordinary Retrieval. Ordinary Retrieval eligibility requires:

```text
lifecycle in {active, pinned}
AND mutation_state == none
AND one unambiguous logical current-state selector
AND exact latest current revision
```

`held`, `hidden`, `superseded`, `purged`, prepared, recovery-required, corrupt, missing-current, duplicate-current, dangling-current, and prior physical revisions are fail-closed from ordinary Retrieval.

## Lifecycle authority

Lifecycle states are:

- `active`
- `pinned`
- `held`
- `hidden`
- `superseded`
- `purged`

Governed transitions are:

- `correct`: active -> active
- `forget`: active -> hidden
- `restore`: hidden -> active
- `consolidate`: active Primary -> active Secondary
- `pin`: active -> pinned
- `unpin`: pinned -> active

`correct`, `forget`, `restore`, `pin`, and `unpin` require user-management or operator authority. RelayMEM policy may autonomously authorize only consolidation among these operations.

A lifecycle operation cannot conceal an unrelated payload rewrite:

- Forget, Restore, Pin, and Unpin may change lifecycle visibility and revision metadata only;
- Consolidate may additionally change `formation_stage` from `primary` to `secondary`, but cannot change grounded assessment/content, subjective meaning, scope, character, memory kind, formation snapshot, or strength as part of the same transition;
- Correct may change grounded content, subjective meaning, and strength only through its explicit corrected successor while preserving character, scope, memory kind, formation stage, and formation snapshot boundaries.

Purge is intentionally not represented as an ordinary reversible transition. Evidence purge remains owned by Evidence Governance; Subjective MEM purge requires its own irreversible authority.

## Relations and succession

Relations are explicit records:

- `supports`
- `refines`
- `reinterprets`
- `supersedes`
- `contradicts`
- `related`

Relations require resolvable exact revisions, one character authority, compatible exact scope, a formation decision that names the relation as its result, and monotonic creation time. Self-relations and successor/reinterpretation cycles fail closed.

A later SOUL revision does not silently rewrite an earlier Subjective MEM. Reinterpretation is a new revision or explicit relation.

## Lineage, time, and explainability

Every committed Subjective MEM revision retains opaque revision references for:

- Shared Assessment;
- SOUL;
- MEMORY policy;
- BOUNDARY;
- optional scene policy;
- optional relationship policy/instance;
- formation schema;
- model revision;
- the exact authorizing formation decision or lifecycle transition.

Assessment revisions, decisions, result revisions, relations, transitions, and current-state updates must be temporally monotonic. Grounded provenance remains reachable without placing every source item in normal conversation context.

## Machine-readable contract

The Draft 2020-12 bundle defines seven top-level record types:

1. `SharedAssessmentRevision`
2. `SharedAssessmentCurrentState`
3. `SubjectiveMemDecision`
4. `SubjectiveMemRevision`
5. `SubjectiveMemCurrentState`
6. `SubjectiveMemRelation`
7. `SubjectiveMemLifecycleTransition`

The fixture suite contains seven valid cases and forty invalid exact-error cases. The validator enforces schema strictness, content digests, logical current-state uniqueness, formation-time assessment authorization, exact decision-result linkage, target currentness, character/scope compatibility, immutable authorization lineage, historical assessment validity, revision succession, ordinary-Retrieval eligibility, relation safety, lifecycle payload fences, authority classes, and temporal order.

## Non-authorization

Acceptance of this target contract does not authorize runtime implementation, database migration, Markdown syntax, SQLite schemas, retrieval ranking, model selection, or deployment. Those remain separately governed.
