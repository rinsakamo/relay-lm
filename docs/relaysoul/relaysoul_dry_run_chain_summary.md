# RelaySOUL Dry-Run Chain Summary

## Scope

This document summarizes the current RelaySOUL dry-run/preflight chain and separates it from the target durable-persona ownership model.

Current runtime status remains defined by [Project Status](../PROJECT_STATUS.md).

## Current implemented chain: `mvp-soul-0`

The current dry-run/tooling chain supports these canonical target files:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

This 5-file allowlist is historical implementation compatibility. It does not represent the desired final ownership boundary.

The current chain is:

```text
protected calibration evidence
  -> patch prompt dry-run
  -> patch candidate parser dry-run
  -> temporary revision compile dry-run
  -> revision history metadata dry-run
  -> approval package dry-run
  -> approval decision dry-run
  -> apply plan dry-run
  -> rollback plan dry-run
  -> persistence classification
  -> storage envelope/path/index dry-run
  -> apply/rollback/storage-writer preflight
  -> no real apply in the current dry-run chain
```

Current scripts may:

- include scene and stable-memory sources in patch prompts,
- generate/accept `SCENE_STATE.md` and `STABLE_MEMORY_SUMMARY.md` targets,
- block only `SOUL.md` in `normal_chat` at the revision-validator stage,
- use `mvp-soul-0` field names and artifact shapes.

Do not interpret those compatibility behaviors as final component ownership.

## Target ownership model

The target RelaySOUL chain should cover only:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Target routing for other state:

```text
scene candidate       -> RelaySCN
current affect        -> RelayEMO
short-term continuity -> RelayCTX
memory candidate      -> RelaySLP / RelayMEM
```

Target normal-chat behavior:

```text
normal_chat
  -> proposal only
  -> no durable persona apply
```

The docs-only Phase 3 PR does not implement this migration.

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
- mode when the schema carries it,
- target source class,
- evidence count,
- approval state,
- risk/budget classes,
- stable-prefix changed boolean,
- compile/apply/rollback readiness/status,
- storage-plan classes,
- blocking/warning reason IDs,
- `content_free: true`.

Current `mvp-soul-0` artifacts may use older field names or nested shapes. Consumers must follow the implemented schema version.

## Current safety invariants

- no model/runtime call unless a specific dry-run explicitly defines one,
- no real persona file mutation,
- no patch apply,
- no rollback execution,
- no persistence/index/path creation,
- no runtime forwarding behavior change,
- no protected content in generic content-free metadata,
- no client system prompt copied into approved RelaySOUL automatically.

## Target safety invariants

After migration:

- no `SCENE_STATE.md` or `STABLE_MEMORY_SUMMARY.md` RelaySOUL target,
- no normal-chat persona apply for any durable persona file,
- mode propagated through candidate/revision/approval/apply/rollback stages,
- typed protected candidates separated from content-free projections,
- all target-file allowlists updated atomically,
- examples and smoke tests migrated with the implementation.

## Current versus target mode posture

### Current `mvp-soul-0`

```text
character_creation
calibration
normal_chat
```

Current enforcement is partial; only `normal_chat + SOUL.md` is blocked by the central revision validator.

### Target posture

```text
character_creation
  approved persona targets after explicit approval / compile / rollback gates

calibration
  prefer OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  SOUL requires durable-identity justification

normal_chat
  proposal-only
  apply blocked for all durable persona sources
```

## Ownership

### RelaySOUL target ownership

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

## Required migration sequence

A future implementation PR should update:

1. patch-prompt source list and target rules,
2. patch-candidate allowlist and schema,
3. temporary revision compile inputs,
4. revision metadata and normal-chat gate,
5. approval package and decision,
6. apply/rollback plans,
7. persistence/storage preflight,
8. examples and smoke tests,
9. content-free projections,
10. compatibility/version handling.

No single stage should adopt the 3-file boundary while later stages still accept the legacy 5-file contract without an explicit migration layer.

## Why this matters

- prevents docs from describing unimplemented contracts as current,
- prevents hidden persona mutation,
- keeps persona revisions attributable and reversible,
- separates protected calibration content from content-free operational metadata,
- blocks scene/memory/affect ownership drift in the target design,
- preserves current tooling compatibility until migration is implemented.

## Non-goals

- no claim that target v1 is already implemented,
- no real persona patch apply from this summary,
- no scene or memory persistence through target RelaySOUL ownership,
- no rollback execution,
- no DB-backed calibration storage,
- no generic runtime trace containing protected evidence.

## Summary

```text
current
  mvp-soul-0 dry-run chain with legacy 5-file compatibility

target
  protected explicit persona feedback
  -> 3-file RelaySOUL candidate/revision chain
  -> content-free readiness projections
  -> future explicit approved apply/rollback
```
