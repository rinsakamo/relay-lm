---
relaylm_doc_type: stable_architecture
relaylm_authority: deferred_subjective_mem_formation_timing_and_episode_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - Subjective MEM formation timing changes
  - Shared Assessment production ownership changes
  - episode grouping or correction handling changes
  - RelaySLP fusion or adjudication policy changes
  - conversational versus durable Forget semantics change
relaylm_not_authoritative_for:
  - exact SourceEvent or Shared Assessment schema
  - exact Subjective MEM, relation, strength, temporal, or lifecycle schema
  - exact Markdown and SQLite commit protocol
  - current RelayMEM or RelaySLP implementation status
  - implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-call-interactive-runtime-deferred-formation.md
  - memory_lifecycle_design.md
  - relaymem_slp_execution_design.md
  - runtime_dataflow_modes.md
  - context_packing_design.md
  - relayrun_resource_scheduling_design.md
---
# Subjective MEM Deferred Formation Design

## Purpose

This document defines the target timing and episode boundary for Subjective MEM formation.

The stable product behavior is:

```text
conversation now
  -> preserve evidence and continuity
  -> answer with one Main LLM response call

memory later
  -> RelaySLP groups related evidence
  -> produces Shared Assessment and Subjective MEM proposal
  -> commits, holds, abstains, or leaves evidence only
```

This document narrows the target timing of RelaySLP without changing the accepted Evidence / Shared Assessment / Subjective MEM authority model.

## Core distinction

The following separation is logical and authoritative:

```text
Protected Source Evidence
  what occurred and where it came from

Shared Assessment
  character-independent support, uncertainty, contradiction, refinement,
  temporal change, or unresolved alternatives

Subjective MEM
  character-scoped grounded content plus subjective meaning
```

It does not require three synchronous runtime calls. The ordinary response path does not wait for either Shared Assessment or Subjective MEM.

## Interactive path

During an admitted conversation turn:

```text
SourceEvent capture and evidence admission
  -> CTX/REL/SCN/EMO/INT processing
  -> read-only MEM retrieval
  -> Main LLM response
  -> REF/output observations
  -> durable SLP job references
```

No normal response-path stage writes durable MEM.

RelayCTX may retain current/session continuity and temporary overlays. It is not a durable staging store for Subjective MEM. The durable source of later formation is governed evidence plus a durable operational SLP job or source-coverage record.

## Why episode formation is preferred

Natural conversation often distributes one experience across several turns:

```text
“I have been tired lately.”
“It is probably lack of sleep rather than work.”
“I keep watching videos late.”
“I went to bed early yesterday.”
“I feel a little better today.”
```

Per-turn formation would create fragments before qualification and temporal change become visible. Episode formation can produce one bounded memory proposal that preserves the sequence and uncertainty.

Episode grouping also reduces near-duplicate creation and avoids relying on later similarity-based repair as the normal path.

## Formation trigger classes

RelaySLP may run when one or more of these conditions are met:

- the conversation has been idle for a configured interval;
- RelaySCN reports a topic or scene boundary effective for later processing;
- the session closes;
- related governed evidence reaches a bounded size or count;
- RelayINT records an explicit remember intent;
- an operator or management surface explicitly invokes formation or consolidation;
- RelayRUN admits background work under the current resource budget.

A trigger starts eligibility evaluation. It does not guarantee a durable write.

## Episode input bundle

A formation bundle may contain opaque references to:

- related Protected Source Evidence;
- corrections, qualifications, or retractions represented by governed lineage;
- validated RelayREF response observations;
- RelaySCN scene, audience, persistence, and disclosure policy references;
- RelayREL trusted target and relationship-scope references;
- bounded RelayEMO formation evidence marked non-authoritative;
- RelayCTX episode-boundary and continuity references;
- existing compatible Subjective MEM candidates;
- identified SOUL, MEMORY, BOUNDARY, relationship, and scene-policy revisions.

RelayCTX text or an assistant inference does not become user-origin Evidence merely because it appears in the bundle.

## Normal formation call

The initial target may use one bounded structured Main LLM call inside RelaySLP:

```text
formation bundle
  -> structured SLP call
     |- shared_assessment section
     `- subjective_mem_proposal section
  -> deterministic validators
  -> policy and persistence gates
```

Example conceptual output:

```yaml
shared_assessment:
  evidence_refs:
    - source-1
    - source-2
  supported_content: "..."
  uncertainty:
    - recent_period_unspecified
  contradiction_state: none

subjective_mem_proposal:
  grounded_assessment_ref: assessment-candidate-1
  subjective_meaning: "..."
  subjective_salience: medium
  relation_decision: create
```

Exact fields remain deferred.

## Preserving the Shared Assessment boundary in a fused call

A fused inference call is allowed only when the output and validators preserve these rules:

1. Evidence references and supported content are produced without SOUL rewriting source support.
2. SOUL conditions only subjective meaning, salience, interpretation, and relation choice.
3. `MEMORY.md` controls remembrance policy, granularity, recall style, and apply/proposal behavior.
4. `BOUNDARY.md`, RelaySCN, and RelayREL constrain persistence and disclosure.
5. RelayEMO remains non-authoritative formation evidence and cannot prove user facts.
6. A validator can reject the Subjective MEM proposal while retaining a valid Shared Assessment candidate.
7. A valid subjective proposal cannot make an invalid or missing assessment valid.

A later implementation may split assessment and subjective formation into separate calls for selected high-risk cases. That split remains inside deferred RelaySLP.

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

Initial automatic relation outcomes should remain conservative. Similarity produces candidates only and never authorizes merge or supersession.

## Current-conversation corrections

A correction affects the active conversation before durable SLP completes:

```text
new correction Evidence
  -> RelayINT target/intent candidate
  -> RelayCTX prefers newer current evidence
  -> optional session overlay suppresses old assertion
```

RelaySLP later reads the old and new evidence together. It may produce refinement, a held correction candidate, a separate memory, or no durable change according to the accepted relation contract.

There is no requirement to synchronously invalidate every derived artifact during the conversation. The current packing rule must, however, prevent an explicitly corrected older MEM from being asserted as current.

## Conversational recall suppression

A natural-language “forget this for now” request is normally represented as a RelayCTX session-local recall suppression when the user did not invoke a durable management operation.

It may:

- prevent a topic or selected MEM from being packed again in the current session;
- encourage a scene/topic transition;
- expire at session end, explicit clear, or an owning resolution event.

It does not mutate Markdown MEM or governed evidence.

## Durable Forget and direct editing

Durable mutation is separate from ordinary formation:

```text
SOUL Lab / Character Workspace Forget
  -> governed RelayMEM lifecycle operation

Direct Markdown edit
  -> schema/revision validation
  -> canonical commit
```

After canonical mutation, the prior SQLite/cache revision must become retrieval-ineligible before normal retrieval resumes. Evidence purge remains a separate evidence-governance operation.

## Pending jobs and later evidence

A pending formation job is operational state, not a second memory authority.

When later related evidence arrives before formation commits, RelayRUN and RelaySLP may:

- cancel an uncommitted attempt when safe;
- coalesce compatible source coverage;
- supersede a pending job with a new idempotent job;
- retain all source references and scope partitions;
- rerun formation on the enlarged episode.

A partially generated proposal is not committed merely to avoid recomputation.

## Explicit remember intent

Example:

```text
User: “Please remember this.”
```

Immediate behavior:

- preserve the SourceEvent;
- record a high-priority explicit remember intent;
- respond naturally without waiting for MEM commit.

Deferred behavior:

- prioritize the related formation bundle;
- still apply evidence, scope, privacy, and persistence gates;
- hold or abstain when the request cannot be safely mapped to durable memory.

A conversational acknowledgement is not proof that a canonical write has completed.

## Shared Assessment storage direction

Shared Assessment is character-independent and belongs logically with the governed evidence domain rather than inside one character's canonical MEM pages.

This document does not choose its physical store. The owning contract must preserve:

- evidence-space identity independent of character identity;
- source and governance revision references;
- assessment revision and stale/superseding relation;
- uncertainty and unresolved alternatives;
- separate character-scoped Subjective MEM references.

## Formation authority snapshot

A committed Subjective MEM should retain opaque revision references sufficient to explain the formation context, including as applicable:

```text
Shared Assessment revision
SOUL revision
MEMORY policy revision
BOUNDARY revision
relationship policy/instance revision
scene policy revision
formation schema and model revision
```

A later SOUL revision does not silently rewrite prior subjective meaning. Reinterpretation, when supported by a future contract, is a new governed relation or successor operation.

## Failure behavior

```text
SLP not admitted because backend is busy
  -> evidence and pending job remain

formation inference fails
  -> no MEM commit
  -> evidence-only / retryable failure

assessment validates but subjective proposal fails
  -> retain valid assessment candidate when its owning contract allows
  -> no Subjective MEM commit

persistence preflight fails
  -> previous canonical state remains
  -> hold or retry under revision/idempotency rules

new interactive turn arrives
  -> interactive path proceeds
  -> pending formation may cancel, defer, or coalesce
```

A formation failure never invalidates an already delivered response.

## Non-goals

This design does not:

- require immediate MEM completion after each turn;
- require a second or third LLM call before the next user input;
- make CTX a durable MEM store;
- make every utterance a memory candidate;
- require exact external-truth adjudication;
- permit SOUL to alter evidence support;
- authorize automatic supersession from similarity;
- interpret conversational suppression as secure erasure.

## Fixed boundaries

- Ordinary conversation uses one Main LLM response call.
- RelaySLP formation is out of band and preferably episode-based.
- Governed Evidence, not CTX alone, is the durable source for formation.
- Shared Assessment remains character-independent.
- Subjective meaning is conditioned by an identified SOUL revision only after a valid assessment basis exists.
- Additional adjudication is optional and confined to SLP.
- Current corrections are handled immediately by CTX packing and durably by later SLP/MEM reconciliation.
- Conversational recall suppression and durable Forget remain separate operations.
