---
relaylm_doc_type: subsystem_architecture
relaylm_authority: character_workspace_deferred_maintenance_candidate_and_proposal_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - RelaySLP Character Workspace maintenance candidate/proposal responsibility changes
  - candidate target domains, approval classes, or write-candidate boundary changes
  - maintenance/public-diagnostic content policy changes
  - source compiler handoff after approved workspace maintenance changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact candidate/proposal schemas, identifiers, CLI flags, risk enums, or approval UX
  - current-turn response behavior, runtime prompt injection, queue/worker operation, or always-on supervision
  - RelayMEM lifecycle/mutation, RelaySCN current scene, RelayREL current relationship, or RelaySOUL apply semantics
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - system.md
  - source-compiler.md
  - creation-and-import.md
  - ../../contracts/character-workspace/maintenance-candidates.md
  - ../cw_a4_slp_workspace_maintenance_candidates.md
  - ../relaymem_slp_current_target.md
  - ../memory/system.md
  - ../memory/mutation-governance.md
  - ../scene/scene-model.md
  - ../relationship/relationship-state.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace and RelaySLP maintainers
  - memory, scene, relationship, source-compiler, and governance maintainers
  - SOUL Lab, privacy, audit, and documentation reviewers
relaylm_authority_level: subsystem
---
# Character Workspace Maintenance Candidates

## Purpose

This page is the canonical subsystem architecture for deferred Character Workspace maintenance candidate and proposal planning.

The maintenance planner consumes governed completed-turn evidence and may prepare deterministic Memory Wiki, Scene Wiki, and Relationship candidates/proposals for later review or separately governed apply.

The stable boundary is:

```text
completed governed evidence
  -> deferred maintenance planner
  -> deterministic candidate / proposal classification
  -> dry-run preview by default
  -> optional allowlisted candidate/proposal write
  -> explicit approval or separately governed apply
  -> source/wiki change under owning authority
  -> Source Compiler rebuild when required
```

The planner does not answer the current turn and does not become runtime memory, scene, relationship, or persona authority.

## Exact current contract

This page owns the durable responsibility model, conceptual lifecycle, and ownership boundaries for deferred maintenance. Exact current schemas, fields, identifiers, statuses, risk vocabulary, candidate/proposal distinction, validation and write gates, content-free public projection, private/content-bearing boundary, and non-authority rules are owned by the [Character Workspace Maintenance Candidates Contract](../../contracts/character-workspace/maintenance-candidates.md).

The implementation handoff [CW-A4 SLP Workspace Maintenance Candidates](../cw_a4_slp_workspace_maintenance_candidates.md) remains live as the current implementation source. It is not retired or treated as a second permanent exact contract by this transaction.

## Deferred, not request-path authority

Character Workspace maintenance happens after the current response/evidence boundary.

It is deliberately separate from request-time orchestration.

The planner does not:

- generate the current assistant answer;
- modify the current prompt;
- select the current scene;
- select the current relationship target/state;
- select the current ordinary-memory reader;
- mutate current memory lifecycle;
- change current affect or RelayCTX state.

Deferred planning can affect future source material only after the relevant candidate/proposal passes its owning write/apply gate.

## Governed evidence input

Maintenance planning consumes bounded governed source evidence accepted under the Character Workspace/RelaySLP source contract.

The presence of evidence is not itself permission to modify a durable source.

The planner must preserve source provenance and distinguish at minimum between evidence suitable for bounded candidate formation and evidence that is insufficient, unsafe, speculative, or outside the target domain.

Assistant-only speculation must not be promoted into a durable user fact merely because it is easy to summarize.

## Candidate and proposal are not applied state

A maintenance output may be a candidate, an inbox artifact, or an approval-required proposal.

The permanent distinction is:

```text
governed evidence
  != maintenance candidate
  != proposal
  != approved change
  != committed source/wiki state
  != rebuilt projection
  != current runtime authority
```

A candidate can be useful for review without being eligible for automatic application.

## Dry-run-first behavior

Default maintenance planning is dry-run.

Dry-run may compute deterministic candidate/proposal results and a content-free public summary but writes no workspace files.

This allows operators/UI to inspect planned maintenance before any candidate/proposal artifact is persisted.

Dry-run success does not mean approval or source mutation.

## Optional write-candidates boundary

A separately requested write-candidates mode may persist only allowlisted candidate/proposal artifacts under the accepted maintenance domains.

The current bounded families are conceptually:

```text
memory/inbox/**
scenes/_inbox/**
relationships/_inbox/**
proposals/memory/**
proposals/scene/**
proposals/relationship/**
```

Exact filenames and schemas remain implementation details.

Writing a candidate/proposal is still not equivalent to applying it to active source/state.

## No direct uppercase source mutation

The maintenance planner does not directly rewrite high-authority uppercase character sources such as:

```text
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
LORE.md
```

When governed evidence suggests a high-authority source change, the planner may emit approval-required proposal metadata under the owning contract.

It does not perform silent normal-turn persona/policy rewrites.

## Memory candidate boundary

Memory maintenance may prepare bounded Memory Wiki candidates and memory proposals.

Stable constraints include:

- memory pages remain human editing units rather than one-file-per-record authority;
- user-fact candidates require suitable user-origin evidence under the owning contract;
- assistant speculation is not promoted to a user fact;
- sensitive memory remains approval-required;
- forgotten/hidden material remains outside ordinary active candidate targeting unless a separately authorized lifecycle path says otherwise;
- maintenance planning does not run memory mutation operations.

The planner does not own Correct, Forget/Hide, Pin/Unpin, Delete/Purge, Consolidate, merge/supersession apply, or ordinary reader selection.

Current RT-1 reader authority and RelayMEM lifecycle/mutation governance remain independent.

## Scene candidate boundary

Scene maintenance may prepare bounded reusable Scene Wiki candidates and scene proposals.

Scene inbox content is staging material, not active scene state and not direct prompt authority.

Classifier/analyzer output may be evidence for a maintenance candidate where accepted, but it does not become current RelaySCN state merely because the maintenance planner receives it.

The planner does not:

- select the current scene;
- update request-local normalized scene state;
- mutate `.relaylm/state/**` current scene state;
- open memory policy through a maintenance candidate.

RelaySCN remains the runtime scene owner.

## Relationship candidate boundary

Relationship maintenance may prepare bounded target-specific Relationship candidates and approval-required proposals.

It preserves the distinction between relationship vocabulary/policy and one target-specific relationship instance.

Important target-specific parameters, roles, permissions, or highly consequential relationship changes remain subject to explicit review/apply authority.

The planner does not:

- resolve current target identity;
- rewrite current RelayREL policy during the request;
- merge target relationship state into SOUL;
- treat one positive/negative interaction as automatic durable relationship truth.

RelayREL remains the runtime relationship owner.

## Proposal-only high-impact changes

High-impact durable changes are proposal/review-oriented by default.

Examples include changes affecting:

- portable character identity;
- durable style/expression policy;
- emotion-response profiles;
- scene policy vocabulary;
- relationship policy or important target parameters;
- memory policy;
- character-specific boundaries;
- sensitive memory;
- destructive lifecycle semantics.

This page does not define exact risk levels or approval UX. It preserves the boundary that candidate planning is not authorization to apply a high-impact durable change.

## Idempotent candidate writes

Allowlisted candidate/proposal writes should be deterministic and safely repeatable.

The current bounded behavior treats an existing identical target as idempotent and blocks conflicting bytes rather than silently overwriting them.

The stable principles are:

- no accidental destructive overwrite;
- no implicit conflict resolution;
- deterministic reason classification for conflicts;
- no deletion as a side effect of candidate generation.

Exact transaction mechanics remain implementation details.

## No build mutation during planning

Maintenance planning does not directly rewrite `.relaylm/build/**`.

After an approved source/wiki change is applied by its owning authority, the deterministic Source Compiler may rebuild generated projections.

The stable chain is:

```text
maintenance candidate/proposal
  -> approved/apply under owner
  -> source/wiki change
  -> Source Compiler rebuild
```

Candidate generation cannot skip the apply boundary by writing a generated projection that runtime treats as newer source authority.

## No runtime state mutation

The maintenance planner does not directly write current runtime state domains such as `.relaylm/state/**`.

A scene candidate does not become active scene state.

A relationship proposal does not become current relationship policy.

A memory candidate does not become a selected retrieval result.

Runtime owners must consume only accepted/activated source/projection state under their own contracts.

## No queue or worker ownership

Character Workspace maintenance candidate planning is not the scheduler/worker service.

It does not:

- enqueue background jobs;
- claim durable queue records;
- start workers;
- poll or sleep;
- supervise always-on services;
- acquire unrelated mutation leases;
- turn a candidate into a worker payload by default.

If future asynchronous maintenance orchestration is added, it requires separately governed scheduling/queue authority.

## No current-turn side effect

The ordinary conversation response cannot depend on a maintenance candidate being persisted or approved during the same turn.

This prevents source mutation pressure from leaking into response latency/authority.

A planner failure should not invalidate an otherwise valid already-produced response.

## Source Compiler dependency

Maintenance planning validates its workspace/source scope through the accepted Character Workspace source boundary.

When a later approved change modifies source/wiki content, deterministic generated projections are rebuilt through the Source Compiler.

The maintenance planner does not duplicate or weaken source validation/compiler rules.

## Creation/import remains separate

Maintenance operates on an existing governed workspace after completed evidence exists.

Creation/import initializes a new candidate/committed workspace under its own explicit approval/commit boundary.

Maintenance does not create a hidden workspace when none exists, and creation/import does not borrow maintenance candidate auto-write semantics.

## Stable candidate identity

Candidate/proposal identity should be deterministic from accepted bounded content/scope rather than incidental runtime values.

Deterministic identities improve idempotency and review correlation.

They must not depend on:

- random UUIDs merely for uniqueness;
- file mtimes;
- current timestamps as semantic identity;
- absolute host paths.

Exact identifier formats remain contract details.

## Privacy and sensitive content

Maintenance candidates/proposals may be content-bearing protected workspace artifacts.

They are not public diagnostics simply because the planner can summarize them.

Sensitive memory and relationship content must preserve the applicable privacy/provenance/approval boundaries.

The planner must not make private evidence broadly visible through reason text, file paths, or generic UI diagnostics.

## Content-free public projection

Default public maintenance diagnostics remain content-free.

They may expose bounded metadata such as:

- candidate/proposal counts;
- target domain classes;
- deterministic candidate/proposal identifiers where safe under the public contract;
- relative target classes/paths where allowlisted;
- risk/approval-required classes;
- blocked/conflict reason IDs;
- sensitive-candidate count;
- dry-run/write-candidate mode class.

They do not expose by default:

- raw source evidence;
- memory text;
- scene body text;
- relationship notes;
- private filesystem roots;
- queue/worker payloads;
- runtime-private identifiers;
- secrets or unrestricted rationale.

## Fail-closed behavior

Maintenance planning closes toward no source/runtime mutation.

```text
workspace invalid
  -> no accepted maintenance write

source evidence insufficient/unsupported
  -> no durable-fact promotion

candidate conflicts with existing different bytes
  -> block conflict
  -> no overwrite

high-impact change
  -> proposal / approval-required
  -> no direct source rewrite

write-candidate failure
  -> source/runtime state unchanged

later apply not authorized
  -> candidate/proposal remains non-authoritative
```

## Current versus target

This page is current as the canonical responsibility map for bounded deferred Character Workspace maintenance candidate/proposal planning.

Current CW-A4 establishes dry-run-first planning, deterministic Memory/Scene/Relationship candidate/proposal artifacts, allowlisted optional candidate writes, no direct uppercase source mutation, content-free public projection, and explicit separation from current runtime state/lifecycle authority.

Broader automatic maintenance apply, asynchronous service orchestration, richer approval UX, additional source domains, or deeper cross-subsystem maintenance may remain target or separately governed work.

Project Status remains authoritative for exact implementation completion.

## Stable invariants

- Maintenance planning is deferred and does not answer the current turn.
- Governed evidence does not itself authorize durable source mutation.
- Candidate/proposal existence is not applied source/state or runtime authority.
- Default mode is dry-run and writes nothing.
- Optional writes are restricted to allowlisted candidate/proposal domains.
- Uppercase durable source changes are not directly auto-written by the planner.
- Sensitive/high-impact changes remain proposal/approval oriented.
- Memory candidates do not bypass RT-1, lifecycle, mutation, privacy, or provenance authority.
- Scene candidates do not become current RelaySCN state.
- Relationship candidates do not become current RelayREL state or SOUL identity.
- Candidate writes are deterministic/idempotent and conflicts are blocked rather than overwritten.
- Planning does not write build, runtime-state, or queue/worker domains.
- Approved source changes rebuild through the Source Compiler rather than projection-as-source shortcuts.
- Creation/import remains a separate subsystem.
- Public diagnostics remain content-free.
- Failure closes toward no source/runtime mutation.

## Non-goals

This architecture does not define:

- exact candidate/proposal schemas or risk enums;
- exact LLM/classifier implementation for candidate formation;
- automatic high-authority source apply;
- current-turn response mutation;
- queue/worker/always-on scheduling;
- current scene/relationship/memory reader authority;
- memory mutation/lifecycle apply;
- source compiler schemas;
- creation/import behavior;
- repository-level project sequencing.

## Related architecture

- [Character Workspace Architecture](system.md)
- [Character Workspace Source Compiler](source-compiler.md)
- [Character Workspace Creation and Import](creation-and-import.md)
- [Character Workspace Maintenance Candidates Contract](../../contracts/character-workspace/maintenance-candidates.md)
- [CW-A4 SLP Workspace Maintenance Candidates](../cw_a4_slp_workspace_maintenance_candidates.md)
- [RelayMEM / RelaySLP Current Target](../relaymem_slp_current_target.md)
- [RelayMEM System](../memory/system.md)
- [Memory Mutation Governance](../memory/mutation-governance.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
