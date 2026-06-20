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
  - ../PROJECT_STATUS.md
---
# Memory Lifecycle Design

## Purpose

This document defines how RelayLM treats short-term memory, experience evidence, long-term MEM formation, and SOUL Lab memory operations as one lifecycle.

The key product boundary is:

```text
Ordinary MEM formation is autonomous by default.
User approval is not required for ordinary memory formation.
SOUL-level changes and high-risk memory operations require explicit intervention.
```

RelayMEM should feel like a character forming experience, not like the user managing a per-turn approval queue.

## Lifecycle summary

```text
RelayCTX short-term state
  -> current-session continuity, referable items, unresolved slots

Experience evidence
  -> governed turn/session/communication evidence after normal response

RelaySLP
  -> deferred memory extraction, salience/scope/safety classification, merge/update/hold/reject/proposal

RelayMEM durable memory
  -> formed memories, summaries, relations, and retrieval pages

SOUL Lab
  -> observation, correction, forgetting, pinning, merging, and SOUL-level intervention when needed
```

Short-term memory helps the current interaction. Long-term MEM crystallizes experience for future interactions.

## Memory layers

RelayLM memory should be read as four related layers:

```text
0. Short-term CTX
   Working memory for the current turn, session, or scene.

1. Primary MEM / Experience MEM
   EMO- and SCN-influenced experiential memory.

2. Secondary MEM / Crystallized MEM
   SLP-consolidated memory organized against SOUL, existing MEM, lineage, and retrieval needs.

3. SOUL anchor
   Durable identity, values, worldview, output policy, and relationship anchors.
```

SOUL is not just another memory page. It is the durable identity/value anchor used to decide whether an experience remains ordinary MEM, becomes stable relationship/project/concept memory, or must be escalated as a SOUL proposal.

### Short-term CTX

Short-term CTX is working memory.

It includes:

- current topic,
- active task,
- prior decision,
- referable items,
- unresolved slots,
- selected recent continuity,
- current-session summary.

It is request/session/scene local, latency-sensitive, and not automatically durable. It may become source evidence for RelaySLP, but it is not itself long-term MEM.

### Primary MEM: experience memory

Primary MEM is EMO- and SCN-influenced experiential memory.

It captures what the character experienced, noticed, or found salient. It may include:

- session episodes,
- communication episodes,
- subjective impressions,
- relationship moments,
- recent project events,
- unresolved but salient experiences,
- emotional salience markers,
- scene-bound memories.

Primary MEM is stronger than short-term CTX because it may survive the current session, but it is still closer to lived experience than to stable knowledge.

RelayEMO influences salience and temperature. RelaySCN influences scope, scene, persistence policy, and whether the experience is eligible to be remembered. Neither EMO nor SCN may turn raw affect estimates into durable facts by itself.

Example boundary:

```text
Allowed primary MEM:
  In the previous communication session, Mica seemed anxious in the latter half.

Disallowed durable fact:
  Mica is an anxious person.
```

### Secondary MEM: crystallized memory

Secondary MEM is SLP-consolidated memory.

It is formed when RelaySLP organizes primary MEM or other governed evidence against:

- SOUL constraints,
- existing MEM pages,
- source lineage,
- contradiction checks,
- namespace boundaries,
- long-term retrieval needs,
- relation typing and summaries.

Secondary MEM may become:

- stable project state,
- concept pages,
- relationship summaries,
- durable preferences,
- recurring patterns,
- contradiction-resolved claims,
- relation graph entries,
- stable memory summaries.

Secondary MEM is less emotionally raw than primary MEM. It preserves EMO/SCN as provenance, salience, or scope when useful, but it should not preserve transient affect as a durable claim.

Example transformation:

```text
Primary MEM:
  The user reacted strongly against requiring manual approval for every MEM candidate.

Secondary MEM:
  RelayLM MEM design should treat ordinary memory formation as autonomous, while SOUL Lab provides observation, correction, forgetting, pinning, and merging after the fact.
```

### SOUL anchor boundary

SOUL is the character's durable identity and value anchor.

SOUL affects secondary MEM formation by answering questions like:

- Is this ordinary memory or identity-level change?
- Does this experience conflict with protected values or relationship anchors?
- Should this become a stable relationship/project/concept memory?
- Should this be escalated as a RelaySOUL proposal?

A memory may produce a SOUL candidate, but it must not directly mutate SOUL.

```text
Primary MEM
  -> what happened or felt salient

Secondary MEM
  -> what this means for future continuity

SOUL proposal
  -> whether identity, values, or relationship anchors should change

SOUL revision
  -> explicit intervention path only
```

## Component ownership

### RelayCTX short-term memory

RelayCTX owns request-local and session-local continuity needed for the current answer:

- current topic,
- active task or question,
- prior decision,
- referable items,
- unresolved slots,
- selected recent continuity metadata,
- bounded short-term summaries.

RelayCTX short-term memory must not be treated as durable memory merely because it helped a prompt. It is not automatically persisted and it is not a source of RelaySOUL changes.

### Experience evidence

Experience evidence is governed source material produced around a turn, session, communication, correction, or recovery event.

It may include:

- source references to the latest exchange,
- communication session summaries,
- RelayCTX Unpack/update candidates after validation,
- RelaySCN scene/persistence policy,
- RelayEMO expression or salience evidence in bounded form,
- RelayRUN checkpoint/recovery metadata,
- user corrections or explicit memory requests,
- retrieval summaries and source lineage.

Experience evidence is not the same as generic runtime trace. Content-bearing evidence belongs in the protected memory/source domain, not default trace/audit projections.

### RelaySLP

RelaySLP is the deferred memory compiler.

It decides whether governed evidence becomes:

- no durable memory change,
- a new memory record,
- an update to an existing memory page,
- a session or scene summary,
- a relation update,
- a held/blocked item,
- a correction or forgetting operation,
- a RelaySOUL proposal candidate.

RelaySLP is allowed to apply ordinary memory updates only when the apply gate, RelaySCN persistence policy, source lineage, confidence/stability, namespace, and idempotency checks pass.

### RelayMEM durable memory

RelayMEM durable memory stores formed experience and retrieval pages.

It is lower authority than SOUL, OUTPUT_POLICY, and RELATIONSHIP_ANCHOR. It should inform answers and continuity, but it must not silently rewrite identity, values, relationship policy, or output style.

### SOUL Lab

SOUL Lab is not a mandatory approval queue for ordinary memory formation.

It should let the user:

- see recently formed memories,
- see which memories influenced an answer,
- inspect uncertain or held memories,
- correct a memory,
- forget or hide a memory,
- pin or unpin important memories,
- merge duplicates,
- resolve contradictions,
- escalate identity-level changes into SOUL Intervention.

## Short-term versus long-term memory

```text
Short-term memory
  - owned primarily by RelayCTX
  - request/session/scene local
  - helps immediate coherence
  - bounded and latency-sensitive
  - not automatically durable

Long-term MEM
  - owned by RelayMEM / RelaySLP
  - durable and namespace-scoped
  - formed from governed experience evidence
  - retrievable across turns/sessions
  - updateable by policy-governed SLP
```

Scene memory and session memory sit between the two. They may begin as short-term continuity and later become long-term MEM only when RelaySLP policy allows promotion.

## Primary-to-secondary consolidation

Primary MEM and secondary MEM should not collapse into one bucket.

```text
Short-term CTX
  -> turn/session working state
  -> source evidence for SLP when policy allows

Primary MEM
  -> scene-aware and EMO-influenced experience memory
  -> useful for recent continuity and subjective relationship memory

Secondary MEM
  -> SOUL-aligned, contradiction-checked, lineage-backed memory
  -> useful for durable retrieval and stable summaries
```

RelaySLP may create primary MEM quickly at turn/session end, then consolidate it later into secondary MEM. Consolidation may merge several primary memories, mark older ones as superseded, or extract a stable relation/summary while preserving source lineage.

## Retrieval authority and prompt placement

Retrieval should preserve authority order.

```text
Highest authority:
  SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR

Stable memory:
  Secondary MEM / Crystallized MEM

Dynamic context:
  RelaySCN scene state
  Primary MEM / Experience MEM
  Short-term CTX
  latest user input
```

Prompt placement should keep stable, approved context before dynamic evidence:

```text
stable prefix:
  SOUL
  OUTPUT_POLICY
  RELATIONSHIP_ANCHOR
  selected secondary MEM summary

dynamic suffix:
  SCN
  selected primary MEM
  selected short-term CTX
  latest input
```

Primary MEM can help a reply feel continuous and emotionally aware, but it must not override SOUL or secondary MEM. Secondary MEM can guide durable continuity, but it still remains lower authority than SOUL.

## Autonomous memory formation

Ordinary memory formation should be autonomous by default.

That means:

- the user should not approve every ordinary memory candidate,
- the normal conversation loop should not pause for memory decisions,
- safe low-risk memories may be formed after turn/session end when gates pass,
- Lab shows what was formed and what was held,
- user correction remains available after the fact.

This is intentionally different from RelaySOUL mutation. SOUL-level changes require explicit intervention because they alter identity, values, output policy, relationship anchors, or durable persona constraints.

## Intervention boundaries

User/operator intervention is required for:

- RelaySOUL changes,
- relationship anchor changes,
- durable output policy changes,
- destructive memory deletion,
- explicit pinning or unpinning when it changes retrieval priority,
- sensitive personal facts,
- low-confidence personal inference,
- unresolved contradictions,
- user-disputed memories,
- policy-blocked persistence,
- memory operations that cross namespace boundaries.

User/operator intervention is not required for every ordinary project note, concept refinement, relationship continuity detail, or session summary when RelaySLP gates classify it as safe to apply.

## Safety scopes

Safety scopes should be interpreted as memory-operation classes, not as a universal user-approval requirement.

```text
free_to_update
  May be autonomously applied by RelaySLP when all gates pass.

review_required
  Held because the system cannot safely decide without later review or correction.

explicit_approval_required
  Requires explicit user/operator approval or a RelaySOUL proposal path.

never_auto_promote
  Never becomes ordinary durable memory automatically.
```

`review_required` and `explicit_approval_required` are exception paths. They should not be the ordinary memory formation experience.

## Lab presentation model

Prefer these Lab surfaces:

```text
Memory Formation
  newly formed memories
  held or uncertain memories
  blocked memory operations
  memories used in latest response
  source experience summary
  correction / forget / pin / merge controls
```

Avoid making the primary UI a per-turn approval inbox:

```text
Memory candidate approval queue
  approve / hold / reject every candidate
```

The Lab should support operator control without turning normal memory formation into user labor.

## Retrieval relationship

RelayMEM Retrieval reads formed memory for the current answer. It does not write memory.

```text
formed MEM
  -> RelayMEM Retrieval
  -> bounded runtime-private evidence
  -> RelayCTX packing
  -> current answer
```

RelaySLP writes or updates future memory after the normal answer path.

```text
current experience
  -> governed evidence
  -> deferred RelaySLP
  -> gated memory apply
  -> future retrieval
```

## Content-bearing and content-free boundary

Content-bearing memory artifacts may contain source text, candidate values, snippets, or page updates only in protected memory/SLP domains.

Default trace, audit, public errors, and general runtime diagnostics must remain content-free and expose only:

- counts,
- booleans,
- status values,
- reason IDs,
- safety scope classes,
- confidence/stability bands,
- namespace classes,
- apply attempted/applied booleans.

## Non-goals

This lifecycle does not make RelayLM:

- a universal semantic memory judge,
- a vector database product,
- an automatic SOUL mutation system,
- a per-turn user approval workflow,
- a replacement for explicit user correction,
- a reason to persist raw runtime traces as memory.

## Summary

```text
RelayCTX keeps short-term continuity.
Primary MEM captures EMO- and SCN-influenced experience.
RelaySLP consolidates primary MEM into secondary MEM when gates pass.
Secondary MEM stores SOUL-aligned crystallized memory for durable retrieval.
SOUL Lab lets the user observe, correct, forget, pin, merge, and escalate.
SOUL Intervention remains explicit.
```
