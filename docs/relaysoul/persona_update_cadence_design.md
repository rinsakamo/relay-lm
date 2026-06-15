# RelaySOUL Persona Update Cadence Design

## Purpose

This document defines how quickly different persona-source layers may change and how `persona_plasticity` may influence proposal frequency without bypassing RelaySOUL safety, approval, versioning, or rollback gates.

RelaySOUL remains a human-in-the-loop persona source calibration layer. RelayMEM/RelaySLP may emit evidence or promotion candidates, but they do not directly mutate RelaySOUL source artifacts.

## Core principle

Persona layers should not all change at the same speed.

```text
fast state changes do not imply fast identity changes
```

A temporary scene, one unusual conversation, or one inferred preference must not silently become a durable character trait.

## Default update cadence

| Source layer | Typical cadence | Default mutation posture |
|---|---|---|
| `SCENE_STATE.md` / runtime scene overlay | per turn or session | automatic within RelaySCN/runtime policy; not a durable persona revision by itself |
| working or retrieved memory | per request | read-only selection in Retrieval; persistence handled separately by RelaySLP |
| `STABLE_MEMORY_SUMMARY.md` | medium | candidate-based, evidence-linked, conservative apply |
| `RELATIONSHIP_ANCHOR.md` | medium-slow | rate-gated, user-specific, correction-aware |
| `OUTPUT_POLICY.md` | slow | explicit feedback or repeated evidence; user review before apply |
| `SOUL.md` | very slow | proposal-only by default; explicit approval and rollback required |

The cadence describes how often a change may be considered. It does not grant authority to apply it.

## Persona plasticity

`persona_plasticity` is a bounded policy input that controls how readily RelaySOUL may surface change proposals for relationship, expression, or persona sources.

It must not act as a direct mutation switch.

Suggested conceptual shape:

```yaml
persona_plasticity:
  relationship: low | medium | high
  expression_policy: low | medium | high
  persona_core: locked | very_low | low
```

Required invariants:

- plasticity never bypasses source-specific approval requirements,
- plasticity never permits RelayMEM or RelaySLP to write `SOUL.md`,
- plasticity never converts low-confidence inference into durable fact,
- plasticity never overrides persona invariants or safety policy,
- plasticity changes proposal thresholds and cooldowns, not semantic ownership,
- `persona_core` should remain `locked` or `very_low` during normal chat.

## Evidence requirements

Different targets require different evidence strength.

### Scene or runtime overlay

May use current-turn evidence when RelaySCN confidence and stability are sufficient.

### Stable memory summary

Requires source references, confidence, scope checks, and contradiction handling. Explicit user statements are stronger than inferred traits.

### Relationship anchor

Should require one or more of:

- explicit user relationship preference,
- repeated consistent interaction evidence,
- user confirmation of a proposed relationship change,
- correction of an existing anchor.

One emotionally intense turn is insufficient by itself.

### Output policy

May use explicit style feedback or repeated preferred/rejected examples. The preferred target is usually `OUTPUT_POLICY.md`, not `SOUL.md`.

### SOUL

Requires a durable identity/value/worldview change that cannot be represented safely in output policy, relationship state, scene state, or memory. Explicit user approval is required before apply.

## Proposal and apply flow

```text
runtime evidence / user feedback
  -> RelaySLP or RelaySOUL candidate extraction
  -> target-source classification
  -> confidence / contradiction / scope checks
  -> cadence and cooldown gate
  -> persona invariant and drift guard
  -> compile dry-run against the target renderer
  -> user review and approval when required
  -> versioned apply
  -> observation period
  -> keep or rollback
```

Every applied persona-source change should remain attributable to evidence and a revision.

## Cooldown and accumulation

RelaySOUL should avoid repeated micro-patches that destabilize the stable prefix or make persona behavior difficult to understand.

Recommended behavior:

- accumulate compatible low-risk feedback before proposing a patch,
- consolidate overlapping instructions instead of appending endlessly,
- delay new relationship/output-policy proposals while a recent revision is still being evaluated,
- reject or hold contradictory evidence until the conflict is resolved,
- prefer one coherent revision over many small revisions,
- preserve a rollback window after each apply.

## Drift guards

Before proposing or applying a durable change, check:

- whether the change conflicts with persona invariants,
- whether it belongs in a faster layer instead,
- whether it overfits one scene or one user mood,
- whether memory confusion produced the candidate,
- whether the patch expands the persona-source budget unnecessarily,
- whether it invalidates stable-prefix reuse without sufficient benefit,
- whether it changes memory disclosure in a way that could feel invasive,
- whether the user can understand and reverse the change.

When uncertain, prefer a temporary scene/output overlay, a held candidate, or no change.

## Normal-chat boundary

During normal chat:

- RelaySOUL source files are execution inputs, not silently editable state,
- RelaySCN may change runtime scene policy,
- RelayEMO may change bounded expression hints,
- RelayMEM Retrieval may select approved memory,
- RelaySLP may produce candidates asynchronously,
- RelaySOUL may surface a proposal,
- no durable core-persona change is applied without the required review.

Explicit character-creation or calibration mode may allow faster exploration, but revision snapshots and rollback remain mandatory.

## Relationship to growth feeling

A user may experience healthy character growth when approved memory, relationship, and expression changes accumulate coherently over time.

Growth must remain:

- attributable rather than mysterious,
- gradual rather than erratic,
- reversible,
- bounded by the user's chosen relationship and persona expectations,
- distinct from silent core-identity mutation.

The goal is continuity the user can recognize and correct, not autonomous persona drift.

## Diagnostics

Useful diagnostics include:

- target source layer,
- evidence count and source references,
- confidence and contradiction state,
- current plasticity level,
- cooldown status,
- blocked reasons,
- persona invariant checks,
- source-budget delta,
- stable-prefix hash before/after,
- approval requirement,
- revision and rollback identifiers.

Diagnostics must not expose private conversation content unnecessarily.

## Non-goals

- No automatic SOUL mutation from normal chat.
- No use of plasticity as an unrestricted learning rate.
- No durable relationship inference from one ambiguous interaction.
- No direct RelayMEM/RelaySLP write into persona source files.
- No removal of approval, versioning, compile dry-run, or rollback gates.

## Summary

RelaySOUL should let temporary state change quickly while durable identity changes slowly.

`persona_plasticity` may control when proposals are surfaced, but durable updates remain target-specific, evidence-based, drift-guarded, versioned, and reviewable.
