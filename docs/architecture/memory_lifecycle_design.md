---
relaylm_doc_type: architecture
relaylm_authority: memory_lifecycle_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - short-term memory semantics change
  - RelayMEM or RelaySLP persistence policy changes
  - SOUL Lab memory operation UI changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelayMEM retrieval schemas
  - exact RelaySLP apply schema
  - RelaySOUL revision approval schema
relaylm_related_authority:
  - context_packing_design.md
  - relaymem_mvp_design.md
  - relaymem_slp_execution_design.md
  - scene_memory_scope_design.md
  - soul_lab_ui_mvp.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - ../PROJECT_STATUS.md
---
# Memory Lifecycle Design

## Purpose

This document defines how RelayLM treats short-term memory, governed experience evidence, durable MEM formation, and explicit SOUL Lab memory operations as one lifecycle.

The key product boundary is:

```text
Ordinary MEM formation is autonomous by default.
User approval is not required for every ordinary memory.
SOUL-level changes and destructive or authority-changing operations require explicit intervention.
```

RelayMEM should feel like a character forming experience, not like the user managing a per-turn approval queue.

## Lifecycle summary

```text
RelayCTX short-term state
  -> current-session continuity and unresolved working state

Governed experience evidence
  -> bounded turn/session/communication evidence after normal response

RelaySLP
  -> deferred extraction, salience/scope/safety classification, merge/update/hold/reject/proposal

RelayMEM durable memory
  -> Primary experience memories, Secondary crystallized memories, relations, and retrieval pages

SOUL Lab
  -> observation, Correct, Forget, Pin/Unpin, Merge, held review, and explicit SOUL intervention
```

Short-term memory helps the current interaction. Durable MEM crystallizes governed experience for future interactions.

## Memory layers

```text
0. Short-term CTX
   Request/session/scene working memory.

1. Primary MEM / Experience MEM
   EMO- and SCN-influenced experiential memory.

2. Secondary MEM / Crystallized MEM
   SLP-consolidated memory organized against SOUL, existing MEM, lineage, contradiction, and retrieval needs.

3. SOUL anchor
   Durable identity, values, worldview, output policy, and relationship anchors.
```

SOUL is not another memory page. It is a higher-authority identity/value anchor used to decide whether experience remains ordinary MEM, becomes stable Secondary MEM, or must become a separately governed proposal.

### Short-term CTX

Short-term CTX includes current topic, active task, referable items, unresolved slots, selected recent continuity, and bounded current-session summary. It is latency-sensitive and is not automatically durable. It may become source evidence for RelaySLP when policy permits.

### Primary MEM

Primary MEM captures what the character experienced, noticed, or found salient. It may represent session episodes, communication moments, subjective impressions, recent project events, unresolved experiences, emotional salience, and scene-bound memories.

Primary MEM may survive sessions, but it remains closer to lived experience than stable knowledge. RelayEMO influences salience and RelaySCN influences scope/persistence policy. Neither may turn raw affect estimates into durable facts by itself.

```text
Allowed Primary MEM:
  In the previous communication session, Mica seemed anxious in the latter half.

Disallowed durable fact:
  Mica is an anxious person.
```

### Secondary MEM

Secondary MEM is contradiction-checked, lineage-backed, SOUL-aligned crystallized memory. It may become stable project state, concepts, relationship summaries, preferences, recurring patterns, claims, relations, or durable summaries.

Secondary MEM is less emotionally raw than Primary MEM. EMO/SCN may remain provenance or salience, not an unsupported fact.

### SOUL anchor

SOUL answers whether an experience is ordinary memory, conflicts with protected values or relationship anchors, should become stable Secondary MEM, or should produce a proposal. RelayMEM/RelaySLP may produce SOUL candidates but never directly mutate SOUL.

## Component ownership

### RelayCTX

RelayCTX owns request/session-local continuity for the current answer. It is not durable merely because it helped a prompt.

### Governed experience evidence

Experience evidence may include source references, session summaries, validated CTX update candidates, RelaySCN persistence policy, bounded RelayEMO salience, RelayRUN recovery correlation, user corrections, explicit memory requests, and retrieval lineage.

Content-bearing evidence belongs in protected memory/SLP domains, not default trace or public audit projections.

### RelaySLP

RelaySLP is the deferred memory compiler. It may classify governed evidence as no change, new memory, update, summary, relation, held/blocked result, separately authorized operation candidate, or RelaySOUL proposal candidate.

Ordinary memory may apply autonomously only when all policy, safety, lineage, namespace, confidence/stability, and idempotency gates pass.

### RelayMEM

RelayMEM owns durable formed memory, lifecycle, current revision, retrieval pages, lineage, and page/index/log persistence. It remains lower authority than SOUL, OUTPUT_POLICY, and RELATIONSHIP_ANCHOR.

### SOUL Lab

SOUL Lab is not a mandatory approval queue. It lets the user observe formed/used/held outcomes and perform explicit governed operations through server-owned APIs.

Canonical user operations include:

- Correct a current active memory,
- Forget a current active memory,
- Pin or Unpin where later contracts permit,
- Merge duplicates where later contracts permit,
- review held candidates,
- escalate identity-level proposals to SOUL Intervention.

## Short-term versus durable memory

```text
Short-term memory
  - owned primarily by RelayCTX
  - request/session/scene local
  - bounded and latency-sensitive
  - not automatically durable

Durable MEM
  - owned by RelayMEM / RelaySLP
  - character and namespace scoped
  - formed from governed evidence
  - retrievable across turns/sessions
  - changed only through policy-governed persistence or explicit operations
```

Scene and session memory may begin as short-term continuity and later become durable only when RelaySLP policy allows promotion.

## Primary-to-Secondary consolidation

```text
Short-term CTX
  -> source evidence when policy permits

Primary MEM
  -> scene-aware and EMO-influenced experience

Secondary MEM
  -> SOUL-aligned, contradiction-checked, lineage-backed stable memory
```

RelaySLP may later consolidate several eligible active Primary memories, mark older ones superseded, or extract stable relations/summaries while preserving lineage. A canonical hidden Primary MEM is not an ordinary consolidation candidate.

## Retrieval authority and prompt placement

Authority order:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest user input
```

Prompt placement should keep stable approved context before dynamic evidence. Primary MEM helps continuity but does not override SOUL or Secondary MEM.

RelayMEM Retrieval reads eligible formed memory for the current answer. It never writes memory. RelaySLP writes future memory after the normal answer path.

## Autonomous formation and explicit intervention

Ordinary safe memory formation is autonomous by default. The conversation loop does not pause for per-turn approvals. The Lab shows formed/held outcomes and allows after-the-fact explicit operations.

Explicit intervention is required for identity/SOUL changes, relationship-anchor changes, durable output-policy changes, destructive lifecycle changes, pinning that changes priority, sensitive disputed facts, unresolved contradictions, and cross-namespace operations.

Safety scopes remain:

```text
free_to_update
review_required
explicit_approval_required
never_auto_promote
```

Review and approval are exception paths, not the ordinary formation experience.

## Primary revision and lifecycle model

Each logical Primary MEM has one stable `memory_id`, one canonical current physical page, one monotonically increasing revision, one canonical lifecycle state, and one retrieval-eligibility result.

Target current-state resolver:

```text
relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

This resolver is the only authority for:

- what physical page is current,
- what revision is current,
- whether the current logical memory is active,
- whether it is eligible for ordinary retrieval,
- whether a pending/corrupt operation requires fail-closed quarantine.

The current implementation provides correction-specific resolution only. The common lifecycle resolver is target work for Phase I-4B.

## Phase I-3 Correct — implemented

```text
revision N active
  -> read-only Correct preflight
  -> exact token/revision-fenced apply
  -> immutable successor Primary page
revision N+1 active
  -> M3f/M3g convergence
  -> immutable correction receipt
```

Correct preserves logical identity, prior immutable pages, exact scope, per-memory one-winner concurrency, operation idempotency, crash recovery, and historical used-memory evidence. Existing M2 resolves only the corrected current revision.

Authority: `phase_i3_auditable_primary_mem_correct.md`.

## Phase I-4A Forget / Hide — defined target

The canonical terms are deliberately distinct:

| Term | Meaning |
|---|---|
| Forget | user-facing explicit operation |
| `hidden` | canonical current lifecycle state that is not active and not retrieval-eligible |
| Forget tombstone | immutable runtime-private audit/recovery artifact; not a lifecycle state or retrieval page |

`Hide` is phase-language only, not a second operation. Physical deletion, secure erase, purge, restore, and unhide are separate future boundaries.

### Persistence decision

Candidate A is selected:

```text
revision N active
  -> exact prepared operation; fail-closed quarantine
  -> immutable successor Primary page through M3e
revision N+1 hidden
  -> M3f/M3g index-before-log convergence
  -> M2 exclusion verification
  -> immutable Forget tombstone
```

The hidden successor page is lifecycle authority. A tombstone is audit evidence and must not become an independently committed sidecar flag.

### Retrieval target

- active, valid, converged current memory may be ranked by existing M2;
- hidden current memory is excluded;
- all prior physical revisions are excluded;
- prepared, recovery-required, corrupt, or ambiguous chains are excluded fail-closed;
- hidden reason and tombstone metadata never reach RelayCTX;
- unrelated memory ranking is unchanged.

### Concurrency target

Correct and Forget share one per-memory lock namespace, pending-operation fence, operation identity lookup, and current revision claim. Only one operation can consume revision N.

```text
Correct preflight at N -> Forget commits N first -> Correct returns stale_revision
Forget preflight at N -> Correct commits N first -> Forget returns stale_revision
concurrent Forget applies -> one commit owner
exact Forget replay -> same result, no new revision/tombstone
new Forget against hidden -> already_hidden
Correct/Pin/Merge/Secondary against hidden -> ineligible unless a later contract explicitly changes it
```

### Historical evidence target

Past used-memory receipts remain immutable:

```text
injected_summary = representation actually injected in the past
current_summary = null when current lifecycle is hidden
current_lifecycle_state = hidden
lifecycle_changed = true
```

The past conversation is never rewritten as though it did not use the memory.

### Current implementation claim

Phase I-4A is documentation only. Production Forget preflight/apply/history, lifecycle resolver changes, hidden successor publication, M2 exclusion, observation projection changes, and SOUL Lab Forget UI are unimplemented.

Authority: `phase_i4_primary_mem_forget_hide_contract.md`.

## Lab presentation model

Preferred surfaces:

```text
Memory Formation
  newly formed memories
  held or blocked outcomes
  memories used in latest response
  current revision and lifecycle
  Correct / Forget / Pin / Merge controls when eligible
```

Avoid a mandatory approval inbox for every candidate. Real mutation failure must never become mock success.

Target Forget UI must state:

- future ordinary conversations no longer retrieve the memory,
- this is not physical file deletion,
- audit evidence remains,
- past conversation and used-memory evidence is not rewritten.

## Content-bearing and content-free boundary

Content-bearing source, candidate, summary, and page data remains in protected memory/SLP domains. Generic trace, public errors, and diagnostics remain bounded and exclude raw source, prompts, transcripts, credentials, paths, roots, digests, lineage, and unrestricted pages.

Forget reason and tombstone metadata are not retrieval inputs.

## Non-goals

This lifecycle does not make RelayLM a universal semantic judge, vector database product, automatic SOUL mutation system, per-turn approval workflow, physical deletion/secure-erasure system, restore/unhide system, or reason to persist raw runtime traces as memory.

## Current operational boundary

Successfully reconciled active Primary MEM may participate in later ordinary requests only through exact character partition, namespace, canonical page/index/log linkage, current lifecycle resolution, and existing M2/RelayCTX gates.

Held, blocked, failed, malformed, superseded, hidden, prepared, recovery-required, conflicting, or corrupt candidates are not target prompt inputs.

I1-G pre-enqueue background-finalizer durability remains unresolved. Queue scanner / daemon operation, UI-B0, and O0 remain unimplemented/planned and are unchanged by Phase I-4A.
