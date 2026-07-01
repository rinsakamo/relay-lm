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
  - file-first workspace memory policy changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelayMEM retrieval schemas
  - exact RelaySLP apply schema
  - RelaySOUL revision approval schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - file_first_character_workspace_design.md
  - context_packing_design.md
  - relaymem_mvp_design.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - scene_memory_scope_design.md
  - soul_lab_ui_mvp.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4d_primary_retrieval_exclusion.md
  - ../PROJECT_STATUS.md
---
# Memory Lifecycle Design

## Purpose

This document defines how RelayLM treats short-term memory, governed experience evidence, long-term MEM formation, memory policy, and SOUL Lab memory operations as one lifecycle.

The target user-facing source model is file-first. The stable policy for memory behavior lives in `MEMORY.md`; human-readable memory pages live under `memory/**/*.md`; generated units, indexes, and projections live under `.relaylm/**`.

The key product boundary is:

```text
Ordinary MEM formation is autonomous by default.
User approval is not required for every ordinary memory formation.
SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY changes
and high-risk memory operations require explicit intervention or proposals.
```

RelayMEM should feel like a character forming experience, not like the user managing a per-turn approval queue. SOUL Lab should let the user observe, correct, archive, forget, merge, and inspect what was used without turning memory into user labor.

This document is target architecture. Current implementation status belongs to [Project Status](../PROJECT_STATUS.md) and exact handoffs.

## File-first memory sources

Target layout:

```text
characters/<character>/
  MEMORY.md
  memory/
    core.md
    people/
      user.md
    projects/
    topics/
    episodes/
    inbox/
    forgotten/
  proposals/
    memory/
  .relaylm/
    sources/
    build/
      memory_units.jsonl
      links.jsonl
    indexes/
```

### MEMORY.md

`MEMORY.md` owns memory policy:

- what should be remembered;
- what should not be remembered;
- memory granularity;
- memory recall style;
- source-reference requirements;
- archive / forgotten / deleted semantics;
- personal-memory disclosure rules;
- SLP auto-apply versus proposal rules.

`MEMORY.md` is an uppercase human-editable source and should be compact, rarely changed, and KV-cache-friendly.

### memory/**/*.md

`memory/**/*.md` files are memory pages, not one-file-per-memory records.

```text
Markdown page = human editing unit
Memory block = semantic unit
Retrieval chunk = internal generated unit
```

A page may contain many stable memory blocks with Obsidian-style block IDs and inline metadata.

Example:

```markdown
## Target user direction ^mem-relaylm-target-user

status:: active
importance:: high
tags:: #relaylm #product-direction

RelayLM should target mid-range GPU local LLM hobbyists and character-AI
experimenters rather than DGX-class infrastructure operators.
```

## Lifecycle summary

```text
RelayCTX short-term state
  -> current-session continuity, referable items, unresolved slots

Experience evidence
  -> governed turn/session/communication evidence after normal response
  -> stored under protected .relaylm/sources/ when content-bearing source retention is needed

RelaySLP
  -> deferred memory extraction, salience/scope/safety classification,
     merge/update/hold/reject/proposal, and page compilation

RelayMEM durable memory
  -> formed memory blocks, summaries, relations, lifecycle revisions, retrieval pages,
     and compiled memory_units.jsonl / indexes

SOUL Lab / Character Workspace UI
  -> observation, correction, archive, forget, merge, source review,
     and escalation to proposals when needed
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
   SLP-consolidated memory organized against SOUL, BOUNDARY, MEMORY policy,
   existing MEM, lineage, relation typing, contradiction checks, and retrieval needs.

3. Character source layer
   SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY.
   This layer is not ordinary memory and changes through explicit proposal/approval.
```

SOUL is not just another memory page. MEMORY is not a memory page either; it is the stable policy source used to decide what should be remembered, how it should be recalled, and when a candidate must be held or proposed.

## Primary MEM: experience memory

Primary MEM captures what the character experienced, noticed, or found salient: session episodes, communication episodes, subjective impressions, relationship moments, recent project events, unresolved but salient experiences, emotional salience markers, and scene-bound memories.

RelayEMO influences salience and expression pressure. RelaySCN influences scope, scene, persistence policy, and whether the experience is eligible to be remembered. RelayREL influences target-specific permissions and relationship salience. None of them may turn raw affect estimates or one-turn impressions into durable user facts by themselves.

Example boundary:

```text
Allowed primary MEM:
  In the previous communication session, Mica seemed anxious in the latter half.

Disallowed durable fact:
  Mica is an anxious person.
```

## Secondary MEM: crystallized memory

Secondary MEM is SLP-consolidated memory. It is formed when RelaySLP organizes primary MEM or other governed evidence against source lineage, existing pages, contradiction checks, namespace boundaries, long-term retrieval needs, relationship policy, and `MEMORY.md`.

Secondary MEM may become stable project state, concept pages, relationship summaries, durable preferences, recurring patterns, contradiction-resolved claims, relation graph entries, or stable memory summaries.

Example transformation:

```text
Primary MEM:
  The user reacted strongly against requiring manual approval for every MEM candidate.

Secondary MEM:
  RelayLM MEM design should treat ordinary memory formation as autonomous,
  while Character Workspace UI provides observation, correction, archive, forget,
  merge, and source review after the fact.
```

## Character source escalation boundary

A memory may produce a proposal for a character-source change, but it must not directly mutate uppercase source files.

```text
Primary MEM
  -> what happened or felt salient

Secondary MEM
  -> what this means for future continuity

Proposal
  -> whether SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY should change

Approved source revision
  -> explicit intervention path only
```

Examples:

```text
ordinary memory:
  The user prefers file-first Markdown workspace terminology.

REL proposal:
  Increase direct_disagreement_permission for relationships/user.md.

SOUL proposal:
  The character's general temperament should become more confrontational.
```

## Component ownership

### RelayCTX short-term memory

RelayCTX owns request-local and session-local continuity needed for the current answer: current topic, active task/question, prior decisions, referable items, unresolved slots, selected recent continuity metadata, and bounded short-term summaries.

RelayCTX short-term memory must not be treated as durable memory merely because it helped a prompt. It is not automatically persisted and it is not a source of character-source changes.

### Experience evidence and .relaylm/sources

Experience evidence is governed source material produced around a turn, session, communication, correction, import, or recovery event.

It may include source references to the latest exchange, communication session summaries, RelayCTX Unpack/update candidates after validation, RelaySCN scene/persistence policy, RelayREL relationship policy classes, RelayEMO expression or salience evidence in bounded form, RelayRUN checkpoint/recovery metadata, user corrections or explicit memory requests, retrieval summaries, and source lineage.

Content-bearing evidence belongs in the protected memory/source domain, such as `.relaylm/sources/**`, not default trace/audit projections.

### RelaySLP

RelaySLP is the deferred workspace compiler. It decides whether governed evidence becomes no durable change, a new memory block, an update to an existing memory page, a session/scene summary, a relation update candidate, a held/blocked item, a correction/forgetting operation, or a source proposal.

RelaySLP is allowed to apply ordinary memory updates only when the apply gate, RelaySCN persistence policy, RelayREL permission policy, source lineage, confidence/stability, namespace, idempotency, and `MEMORY.md` checks pass.

RelaySLP may also create scene candidates under `scenes/_inbox/` and relationship proposals under `proposals/relationship/`, but it must not apply high-risk source changes during the normal response path.

### RelayMEM durable memory

RelayMEM durable memory stores formed experience and retrieval pages/units. It is lower authority than BOUNDARY, SOUL, REL, SCENE, EMOTION, STYLE, and MEMORY policy. It should inform answers and continuity, but it must not silently rewrite identity, values, relationship policy, emotion profiles, scene policy, memory policy, boundary policy, or output style.

### Character Workspace UI

The primary UI should not be a per-turn approval queue or a memory-id console. It should let the user:

- see recently formed memories;
- see held or uncertain memories;
- see memories used in the latest response;
- inspect source summaries;
- edit memory pages when desired;
- archive / forget / correct / merge;
- review proposals for high-risk changes.

Pin / Unpin and raw revision IDs are internal or Advanced diagnostics concepts, not the default user-facing vocabulary.

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
  -> scene-aware, relationship-aware, and EMO-influenced experience memory
  -> useful for recent continuity and subjective relationship memory

Secondary MEM
  -> source-aligned, contradiction-checked, lineage-backed memory
  -> useful for durable retrieval and stable summaries
```

RelaySLP may create primary MEM quickly at turn/session end, then consolidate it later into secondary MEM. Consolidation may merge several primary memories, mark older ones as superseded, or extract a stable relation/summary while preserving source lineage.

## Retrieval authority and prompt placement

Retrieval should preserve authority order.

```text
Highest stable authority:
  BOUNDARY / SOUL / RELATIONSHIP / STYLE / EMOTION / MEMORY policy

Target/session semi-stable context:
  selected relationships/<target>.md summary
  selected active scene page summary
  selected secondary MEM summary

Dynamic context:
  RelaySCN scene state
  RelayEMO expression state
  selected Primary MEM / Experience MEM
  selected short-term CTX
  latest user input
```

Prompt placement should keep stable, approved context before dynamic evidence while preserving KV-cache-friendly tiers:

```text
stable prefix:
  BOUNDARY
  SOUL
  STYLE
  EMOTION
  RELATIONSHIP
  MEMORY
  optional LORE

semi-stable prefix:
  selected relationship instance
  selected scene summary
  selected secondary MEM summary

dynamic suffix:
  scene_state
  emotion_state
  selected primary MEM
  selected short-term CTX
  latest input
```

Primary MEM can help a reply feel continuous and emotionally aware, but it must not override character sources or secondary MEM. Secondary MEM can guide durable continuity, but it still remains lower authority than stable character and policy sources.

## Primary MEM lifecycle states

The Forget / Hide target uses one current-state resolver and separate lifecycle/mutation dimensions:

```text
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

A hidden current successor is the lifecycle authority. Prior physical pages remain audit evidence and must not re-enter ordinary retrieval. Prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior-revision states fail closed before prompt construction.

Exact current implementation status for I-4B/I-4C1/I-4C2/I-4D/I-4E/I-4F belongs to [Project Status](../PROJECT_STATUS.md) and the dedicated Phase I-4 handoffs.

## Autonomous memory formation

Ordinary memory formation should be autonomous by default.

That means:

- the user should not approve every ordinary memory candidate;
- the normal conversation loop should not pause for memory decisions;
- safe low-risk memories may be formed after turn/session end when gates pass;
- Lab shows what was formed and what was held;
- user correction remains available after the fact;
- SLP-maintained lowercase pages may grow without invalidating stable uppercase sources.

This is intentionally different from character-source mutation. Uppercase files and high-risk relationship parameters require explicit intervention because they alter identity, style, emotion profiles, scene policy, relationship policy, memory policy, or boundaries.

## Intervention boundaries

User/operator intervention is required for:

- `SOUL.md` changes;
- `STYLE.md` changes;
- `EMOTION.md` changes;
- `SCENE.md` changes;
- `RELATIONSHIP.md` changes;
- `MEMORY.md` changes;
- `BOUNDARY.md` changes;
- important `relationships/<target>.md` parameter or role changes;
- explicit Forget lifecycle transitions and any separate physical deletion operation;
- sensitive personal facts;
- low-confidence personal inference;
- unresolved contradictions;
- user-disputed memories;
- policy-blocked persistence;
- memory operations that cross namespace boundaries.

User/operator intervention is not required for every ordinary project note, concept refinement, low-risk relationship continuity detail, or session summary when RelaySLP gates classify it as safe to apply.

## Safety scopes

Safety scopes should be interpreted as memory-operation classes, not as a universal user-approval requirement.

```text
free_to_update
  May be autonomously applied by RelaySLP when all gates pass.

review_required
  Held because the system cannot safely decide without later review or correction.

explicit_approval_required
  Requires explicit user/operator approval or a source proposal path.

never_auto_promote
  Never becomes ordinary durable memory automatically.
```

`review_required` and `explicit_approval_required` are exception paths. They should not be the ordinary memory formation experience.

## Content-bearing and content-free boundary

Content-bearing memory artifacts may contain source text, candidate values, snippets, or page updates only in protected memory/SLP/source domains.

Default trace, audit, public errors, and general runtime diagnostics must remain content-free and expose only counts, booleans, status values, reason IDs, safety scope classes, confidence/stability bands, namespace classes, and apply attempted/applied booleans.

## Non-goals

This lifecycle does not make RelayLM:

- a universal semantic memory judge;
- a vector database product;
- an automatic character-source mutation system;
- a per-turn user approval workflow;
- a one-file-per-memory system;
- a replacement for explicit user correction;
- a physical deletion, secure-erasure, purge, restore, or unhide system through Forget;
- a reason to persist raw runtime traces as memory.

## Summary

```text
RelayCTX keeps short-term continuity.
Primary MEM captures SCN / EMO / REL-influenced experience.
RelaySLP consolidates Primary MEM into Secondary MEM when gates pass.
MEMORY.md defines memory policy.
memory/**/*.md stores human-readable memory pages.
.relaylm/build stores compiled retrieval units and indexes.
Character Workspace UI lets the user observe, correct, archive, Forget, merge, and review proposals.
```

## Primary MEM next-turn use

A successfully reconciled Primary MEM may participate in a later ordinary request only through its opaque character store partition, exact namespace, canonical page/index/log linkage, and current RelaySCN retrieval gates. Run and session are not added as new long-term restrictions. Held, blocked, failed, malformed, conflicting, or unreconciled candidates are not injected.
