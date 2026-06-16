# RelaySOUL Persona Update Cadence Design

## Purpose

This document defines how quickly approved durable persona-source layers may change and how `persona_plasticity` affects proposal frequency without bypassing ownership, approval, versioning, compile dry-run, or rollback.

RelaySOUL owns only:

- `SOUL.md`,
- `OUTPUT_POLICY.md`,
- `RELATIONSHIP_ANCHOR.md`.

Scene, affect, short-term context, and compiled memory follow their own component contracts.

## Core principle

```text
fast runtime state changes do not imply fast durable persona changes
```

A temporary scene, one affect estimate, one retrieval result, or one unusual interaction must not silently become a durable trait.

## Cross-component cadence

| State/source | Owner | Typical cadence | Mutation posture |
|---|---|---:|---|
| request-local scene state/policy | RelaySCN | per request/turn | runtime-only, not a persona revision |
| affect/expression state | RelayEMO | per request/session | local/decaying, not durable persona |
| short-term topic/question/referents | RelayCTX | per turn/session | request/RAM-side candidate apply only |
| selected long-term memory | RelayMEM Retrieval | per request | read-only |
| compiled memory/summary/index | RelaySLP -> RelayMEM | deferred | evidence-linked gated apply |
| `RELATIONSHIP_ANCHOR.md` | RelaySOUL | medium-slow | explicit evidence, review/approval |
| `OUTPUT_POLICY.md` | RelaySOUL | slow | explicit style evidence, review/approval |
| `SOUL.md` | RelaySOUL | very slow | explicit durable identity change, approval/rollback |

Cadence controls when a change may be considered. It never grants ownership or apply authority.

## Persona plasticity

`persona_plasticity` controls how readily RelaySOUL surfaces proposals.

```yaml
persona_plasticity:
  relationship: low | medium | high
  expression_policy: low | medium | high
  persona_core: locked | very_low | low
```

Required invariants:

- no direct mutation switch,
- no ownership transfer from SCN/EMO/CTX/MEM,
- no low-confidence inference promoted to durable state,
- no runtime/safety/persona invariant override,
- proposal threshold/cooldown only,
- `persona_core` remains locked or very-low in normal chat,
- normal chat remains proposal-only.

## Evidence requirements

### Relationship anchor

Requires one or more of:

- explicit relationship preference/correction,
- repeated consistent interaction evidence,
- user confirmation of a proposal,
- approved calibration examples.

One emotionally intense turn is insufficient.

### Output policy

May use explicit style feedback or repeated protected preferred/rejected samples.

The candidate must describe durable character voice or response policy, not one temporary emotional expression.

### SOUL

Requires an explicit durable identity/value/worldview/invariant change that cannot be represented safely in output policy, relationship policy, RelaySCN state, RelayEMO state, or RelayMEM.

Explicit approval and rollback are mandatory.

### Faster-layer routing

Evidence belongs elsewhere when it describes:

```text
current role/task/setting/constraint -> RelaySCN
current affect/intensity            -> RelayEMO
current topic/open question          -> RelayCTX
factual/project/user memory          -> RelaySLP / RelayMEM
```

RelaySOUL should reject or reroute such candidates rather than patch persona files.

## Proposal and apply flow

```text
protected explicit feedback / governed RelaySLP proposal
  -> target-source classification
  -> ownership check
  -> confidence / contradiction / scope checks
  -> cadence and cooldown gate
  -> persona invariant and drift guard
  -> source-budget check
  -> compile dry-run against target renderer
  -> explicit review / approval
  -> versioned apply
  -> observation period
  -> keep or rollback
```

Every applied change remains attributable to protected evidence and content-free revision metadata.

## Normal-chat boundary

During normal chat:

- approved persona sources are execution inputs,
- RelaySCN may change current scene policy,
- RelayEMO may change bounded expression hints,
- RelayMEM Retrieval may select approved memory,
- RelaySLP may produce deferred candidates,
- RelaySOUL may surface a proposal,
- no persona-source apply occurs.

Explicit user feedback may offer entry into calibration or character creation. It does not mutate files inside the chat turn.

## Cooldown and accumulation

- accumulate compatible low-risk feedback,
- consolidate overlapping policy rather than append endlessly,
- avoid new durable proposals while a recent revision is under observation,
- hold contradictory evidence,
- prefer one coherent revision over micro-patches,
- preserve a rollback window,
- consider stable-prefix invalidation cost.

## Drift guards

Check whether the proposal:

- conflicts with persona invariants,
- belongs in SCN/EMO/CTX/MEM instead,
- overfits one scene or affect estimate,
- originated from ambiguous/recovery context,
- expands source budgets unnecessarily,
- changes memory disclosure invasively,
- destabilizes renderer behavior,
- is understandable and reversible.

When uncertain, prefer a faster runtime layer, held candidate, or no change.

## Protected evidence and diagnostics

Protected evidence may contain response examples and feedback text.

Content-free diagnostics may contain only:

- target source class,
- evidence count/source class,
- confidence/contradiction bands,
- plasticity level,
- cooldown status,
- invariant check outcomes,
- source-budget delta class,
- stable-prefix changed boolean,
- approval requirement/status,
- revision/rollback IDs,
- blocking/warning reason IDs.

Generic runtime trace must not contain response samples, feedback text, patch text, persona bodies, or affect semantic content.

## Growth feeling

Healthy character growth is:

- attributable,
- gradual,
- reversible,
- bounded by chosen persona/relationship expectations,
- distinct from silent core drift,
- produced by approved memory/relationship/expression changes across the correct owners.

## Non-goals

- No automatic persona mutation from normal chat.
- No use of plasticity as unrestricted learning rate.
- No durable relationship inference from one interaction.
- No RelayMEM/RelaySLP direct write into persona files.
- No SCN/EMO/CTX state stored as RelaySOUL revision.
- No removal of approval, versioning, renderer dry-run, or rollback gates.

## Summary

Temporary state may change quickly under SCN, EMO, CTX, and MEM contracts. Durable RelaySOUL sources change slowly, by proposal, explicit evidence, review, versioning, and rollback.
