# RelaySOUL Dry-Run Chain Summary

## Scope

This document summarizes the current RelaySOUL dry-run/preflight chain before real persona-source apply or rollback.

The chain covers only approved durable persona sources:

- `SOUL.md`,
- `OUTPUT_POLICY.md`,
- `RELATIONSHIP_ANCHOR.md`.

Scene state, affect state, RelayCTX working state, and RelayMEM compiled memory are outside RelaySOUL revision ownership.

Current runtime status remains defined by [Project Status](../PROJECT_STATUS.md).

## Pipeline

```text
protected calibration evidence
  -> target-source classification
  -> patch prompt dry-run
  -> patch candidate parser dry-run
  -> temporary persona revision compile dry-run
  -> revision history metadata dry-run
  -> approval package dry-run
  -> approval decision dry-run
  -> apply plan dry-run
  -> rollback plan dry-run
  -> persistence classification
  -> storage envelope/path/index dry-run
  -> apply/rollback/storage-writer preflight
  -> future explicit approved persona persistence
```

A candidate for scene, affect, short-term context, or memory is rerouted/rejected before the RelaySOUL patch chain.

## Artifact domains

The chain does not make every artifact content-free.

### Protected content-bearing inputs/intermediates

May include:

- preferred/rejected response samples,
- freeform feedback,
- current persona-source bodies,
- patch prompt and patch text,
- target-renderer sample output,
- detailed patch rationale.

These remain in an explicit protected calibration domain and must not be copied into generic runtime trace or content-free revision metadata.

### Content-free operational artifacts

May include:

- evidence/candidate/revision IDs,
- mode,
- target source class,
- evidence count,
- approval state,
- risk/budget classes,
- stable-prefix changed boolean,
- compile/apply/rollback readiness/status,
- storage-plan classes,
- blocking/warning reason IDs,
- `content_free: true`.

## Safety invariants

- no hidden model/runtime call unless the specific dry-run explicitly defines one,
- no real persona file mutation,
- no patch apply,
- no rollback execution,
- no persistence/index/path creation,
- no runtime forwarding behavior change,
- no normal-chat persona apply,
- no `SCENE_STATE.md` or `STABLE_MEMORY_SUMMARY.md` persona target,
- no persona/memory/patch/prompt/response/feedback body in content-free metadata,
- no client system prompt copied into RelaySOUL.

## Mode posture

```text
character_creation
  broad allowed persona targets
  explicit approval / compile / rollback still required

calibration
  prefer OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  SOUL requires durable-identity justification

normal_chat
  proposal-only
  apply blocked for all persona sources
```

## Ownership

### RelaySOUL

- protected persona calibration evidence,
- target-source classification,
- persona patch candidate shaping,
- temporary persona revision metadata,
- approval/apply/rollback planning,
- durable persona revision lineage.

### RelayLM runtime/compiler

- compile dry-run against the configured target renderer,
- token/source-budget diagnostics,
- stable-prefix impact calculation,
- compatibility and runtime-boundary validation,
- content-free node/trace projections.

### Other component routing

```text
scene candidate       -> RelaySCN
current affect        -> RelayEMO
short-term continuity -> RelayCTX
memory candidate      -> RelaySLP / RelayMEM
```

## Implemented dry-run/preflight support

The repository contains scripts and helpers for patch prompting/parsing, temporary revision compilation, revision history, approval packages/decisions, apply/rollback planning, storage planning/indexing, and persistence/apply/rollback preflight.

The exact current inventory and next implementation boundary should be read from [Project Status](../PROJECT_STATUS.md) and implementation history rather than maintained as a competing roadmap here.

## Why this matters

- prevents hidden persona mutation,
- keeps persona revisions attributable and reversible,
- separates protected calibration content from content-free operational metadata,
- blocks scene/memory/affect ownership drift,
- exposes source-budget and renderer compatibility before approval,
- preserves normal-chat stability.

## Current non-goals

- real persona patch apply from this summary,
- automatic SOUL/OUTPUT_POLICY/RELATIONSHIP mutation,
- normal-chat apply,
- scene or memory persistence through RelaySOUL,
- rollback execution,
- DB-backed calibration storage,
- generic runtime trace containing protected evidence.

## Summary

```text
protected explicit persona feedback
  -> dry-run persona candidate/revision chain
  -> content-free readiness projections
  -> future explicit approved apply/rollback

non-persona state
  -> routed to its owning component
```
