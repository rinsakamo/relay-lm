---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_memory_assessment_formation_timing_and_episode_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM formation timing changes
  - Shared Assessment production ownership changes
  - episode grouping or correction handling changes
  - assessment or subjective-formation pass policy changes
  - conversational versus durable Forget semantics change
relaylm_not_authoritative_for:
  - exact SourceEvent or Shared Assessment schema
  - exact Subjective MEM, relation, strength, temporal, or lifecycle schema
  - exact Markdown and SQLite commit protocol
  - exact durable queue or worker contract
  - current RelayMEM or RelaySLP implementation status
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_authority:
  - ../../adr/0003-subjective-mem-direction.md
  - ../memory_lifecycle_design.md
  - ../relaymem_slp_execution_design.md
  - ../relaymem_slp_current_target.md
  - ../context/context-assembly.md
  - ../runtime/request-response-pipeline.md
  - ../runtime/scheduler.md
---
# RelayLM Subjective Memory Formation

## Authority summary

This document is authoritative for target timing, episode grouping, and the split Shared Assessment / Subjective Formation reference path. It preserves the Evidence / Shared Assessment / Subjective MEM authority model accepted in ADR 0003 and does not claim the target runtime is implemented.

## Core distinction

```text
Protected Source Evidence
  what occurred, who produced it, and where it came from

Shared Assessment
  character-independent support, uncertainty, contradiction,
  refinement, temporal change, and unresolved alternatives

Subjective MEM
  character-scoped grounded content plus subjective meaning
```

This logical separation does not require synchronous formation during conversation. The ordinary response path waits for neither Shared Assessment nor Subjective MEM.

## Interactive path boundary

During an admitted conversation turn:

```text
user-origin SourceEvent capture and Evidence Admission
  -> REL / SCN / EMO / INT processing
  -> read-only MEM Retrieval
  -> Main LLM response streaming
  -> finalized assistant-origin Evidence
  -> RelayREF and output observations
  -> durable SLP coverage / operational job reference
```

No normal response-path stage writes durable MEM.

RelayCTX may retain current/session continuity and temporary overlays. It is not a durable staging store for Subjective MEM. The durable source of later formation is governed Evidence plus durable operational source coverage.

## Why episode formation is preferred

Natural conversation distributes one experience across several turns:

```text
“I have been tired lately.”
“It is probably lack of sleep rather than work.”
“I keep watching videos late.”
“I went to bed early yesterday.”
“I feel a little better today.”
```

Per-turn formation would create fragments before qualification and temporal change become visible. Episode formation can produce one bounded proposal preserving sequence, uncertainty, and later correction.

Episode grouping reduces near-duplicate creation and avoids relying on similarity-based repair as the normal path.

## Formation trigger classes

RelaySLP may become eligible when one or more conditions occur:

- the conversation has been idle for a configured interval;
- RelaySCN reports a topic or scene boundary effective for later processing;
- the session closes;
- related governed evidence reaches a bounded size or count;
- RelayINT records explicit remember intent;
- an operator or management surface invokes formation or consolidation;
- RelayRUN admits background work under current resource budget.

A trigger starts eligibility evaluation. It does not guarantee durable write.

## Episode input bundle

A formation bundle may contain opaque references to:

- related user-origin Protected Source Evidence;
- finalized assistant-origin Evidence and completion status;
- corrections, qualifications, or retractions represented by governed lineage;
- validated RelayREF observations;
- RelaySCN scene, audience, persistence, and disclosure policy references;
- RelayREL trusted target and relationship-scope references;
- bounded RelayEMO formation evidence marked non-authoritative;
- RelayCTX episode-boundary and continuity references;
- existing compatible Subjective MEM candidates;
- identified MEMORY, BOUNDARY, relationship, and scene-policy revisions;
- an identified SOUL revision only for the Subjective Formation pass.

RelayCTX text, RelayREF observation, or assistant inference does not become user-origin Evidence because it appears in a bundle.

## Reference path: split assessment and subjective formation

The reference architecture uses two deferred semantic passes.

### Pass A: Shared Assessment

```text
Protected Source Evidence
+ governance and provenance metadata
+ corrections / temporal lineage
+ speaker and audience partitions
  -> SLP Assessment Pass
  -> deterministic assessment validation
  -> character-independent Shared Assessment
```

Pass A must not receive:

- SOUL content or character identity as semantic conditioning;
- character-specific relationship attachment or desired emotional meaning;
- current EMO as proof of source support;
- STYLE as a meaning source.

It may receive governance classes needed to preserve scope, provenance, speaker, audience, and privacy boundaries.

A minimal conceptual result is:

```yaml
shared_assessment:
  evidence_refs:
    - source-1
    - source-2
  supported_content: "..."
  uncertainty:
    - recent_period_unspecified
  contradiction_state: none
```

Exact fields remain contract-owned.

### Pass B: Subjective Formation

Only a governance- and schema-valid Shared Assessment may enter Subjective Formation.

```text
validated Shared Assessment
+ identified SOUL revision
+ MEMORY policy revision
+ BOUNDARY revision
+ bounded REL / SCN constraints
+ non-authoritative EMO evidence
+ existing compatible Subjective MEM candidates
  -> SLP Subjective Formation Pass
  -> Subjective MEM proposal
  -> deterministic and policy validation
  -> RelayMEM / workspace commit or hold
```

Conceptual result:

```yaml
subjective_mem_proposal:
  grounded_assessment_ref: assessment-1
  subjective_meaning: "..."
  subjective_salience: medium
  relation_decision: create
```

SOUL may condition subjective meaning, salience, interpretation, and relation choice. It cannot change what evidence supports, convert uncertainty into fact, or rewrite provenance.

`MEMORY.md` owns remembrance policy, granularity, recall behavior, and auto-apply/proposal policy. `BOUNDARY.md`, RelaySCN, and RelayREL constrain persistence and disclosure. RelayEMO is non-authoritative formation evidence and cannot prove user facts.

## Fused-call optimization boundary

A fused one-call output containing both assessment and subjective proposal is not the reference architecture.

It may be evaluated only as a non-authoritative optimization candidate when:

- Japanese fixtures compare it against the split reference path;
- SOUL contamination of supported content is measured;
- speaker, negation, uncertainty, audience, and assistant-inference boundaries remain acceptable;
- the system can fail closed to split processing;
- a valid subjective proposal cannot make an invalid assessment valid;
- a validator may reject subjective output while retaining an independently valid assessment only when the owning assessment contract permits it.

The optimization is never assumed equivalent merely because the output uses two JSON sections.

## Difficult cases and adjudication

The normal result for unresolved difficulty is hold or abstention, not repeated mandatory calls.

Possible adjudication candidates include:

- uncertain correction target;
- material contradiction between evidence groups;
- participant or relationship identity conflict;
- private/group scope conflict;
- possible supersession with unresolved temporal meaning;
- several plausible existing MEM relations.

```text
normal SLP result
  -> hold with typed reason
  -> optional later adjudication when important and resource-eligible
  -> commit or continue hold
```

Similarity produces candidates only and never authorizes merge or supersession.

## Current-conversation corrections

A correction affects active conversation before durable SLP completes:

```text
new correction Evidence
  -> RelayINT target/intent candidate
  -> RelayCTX presents newer evidence more saliently
  -> optional session overlay suppresses a resolved old item
```

This is best-effort input control. The architecture does not guarantee that a probabilistic model will never repeat old content.

RelaySLP later reads old and new Evidence together. It may produce refinement, a held correction candidate, a separate memory, or no durable change according to the accepted relation contract.

There is no requirement to synchronously invalidate every semantic derivative during conversation.

## Conversational recall suppression

A natural-language “forget this for now” request is normally represented as RelayCTX session-local suppression when no durable management authority was invoked.

It may:

- prevent a topic or selected MEM from being packed again in the active session;
- encourage scene/topic transition;
- expire at session end, explicit clear, or owning resolution event.

It does not mutate Markdown MEM or governed Evidence.

## Durable Forget and direct editing

Durable mutation is separate from ordinary formation:

```text
Character Workspace / SOUL Lab / governed API Forget
  -> RelayMEM lifecycle mutation fence
  -> canonical revision

human Markdown edit
  -> schema/revision validation
  -> canonical commit
```

After canonical mutation, the prior cache projection becomes retrieval-ineligible before normal retrieval resumes. A failed rebuild leaves a fail-closed state. Evidence purge remains a separate Evidence Governance operation.

A natural-language conversational “forget” does not become a durable SLP mutation request unless an explicit management contract resolves and authorizes that operation.

## Pending work and later evidence

A pending formation job is operational state, not a second memory authority.

When later related evidence arrives before formation commits, RelayRUN and RelaySLP may:

- cancel an uncommitted attempt when safe;
- coalesce compatible operational source coverage;
- supersede a pending operational job with a new idempotent job;
- retain all source references and scope partitions;
- rerun assessment and formation on the enlarged episode.

RelayRUN may coalesce operational jobs but never decides semantic memory identity. A partially generated proposal is not committed merely to avoid recomputation.

## Explicit remember intent

```text
User: “Please remember this.”
```

Immediate behavior:

- preserve the SourceEvent;
- record high-priority explicit remember intent;
- respond naturally without waiting for MEM commit.

Deferred behavior:

- prioritize related assessment and formation work;
- retain evidence, scope, privacy, and persistence gates;
- hold or abstain when the request cannot safely map to durable memory.

A conversational acknowledgement is not proof that canonical write completed.

## Shared Assessment storage direction

Shared Assessment is character-independent and belongs logically with governed Evidence rather than inside one character's canonical MEM pages.

This document does not choose physical storage. The owning contract must preserve:

- evidence-space identity independent of character identity;
- source and governance revision references;
- assessment revision and stale/superseding relation;
- uncertainty and unresolved alternatives;
- separate character-scoped Subjective MEM references.

## Formation authority snapshot

A committed Subjective MEM should retain opaque revision references sufficient to explain formation context, including as applicable:

```text
Shared Assessment revision
SOUL revision
MEMORY policy revision
BOUNDARY revision
relationship policy/instance revision
scene policy revision
formation schema and model revision
```

A later SOUL revision does not silently rewrite prior subjective meaning. Reinterpretation is a new governed relation or successor operation.

## Failure behavior

```text
assessment work not admitted because backend is busy
  -> evidence and pending coverage remain

Assessment Pass fails or does not validate
  -> no Shared Assessment
  -> no Subjective Formation

Subjective Formation fails
  -> valid Shared Assessment may remain under its owning contract
  -> no Subjective MEM commit

persistence preflight fails
  -> previous canonical state remains
  -> hold or retry under revision/idempotency rules

new interactive turn arrives
  -> interactive path proceeds
  -> pending formation may cancel, defer, or coalesce
```

Formation failure never invalidates an already delivered response.

## Fixed invariants

- Ordinary conversation uses one Main LLM response-generation call on the no-tool critical path.
- RelaySLP formation is out of band and preferably episode-based.
- Governed Evidence, not CTX alone, is the durable source for formation.
- Finalized assistant output and RelayREF observation remain distinct formation inputs.
- Shared Assessment remains character-independent and is validated before SOUL-conditioned subjective formation.
- The split path is reference; fused processing is evaluation-gated optimization only.
- Additional adjudication is optional and confined to SLP.
- Current corrections use best-effort CTX input control and later SLP/MEM reconciliation.
- Conversational recall suppression and durable Forget remain separate operations.
