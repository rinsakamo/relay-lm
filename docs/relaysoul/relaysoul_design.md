# RelaySOUL Design

## Purpose

RelaySOUL is RelayLM's human-in-the-loop durable persona-source calibration layer.

It creates, calibrates, versions, approves, applies, and rolls back persona-source revisions. It does not train model weights and it does not own request-local scene state, current affect state, short-term context, or compiled memory.

```text
RelaySOUL
  -> approved durable persona artifacts

RelayLM runtime
  -> compiles approved artifacts with current SCN, EMO, INT, MEM, and CTX state
```

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md) and [Pipeline Implementation Plan](../architecture/pipeline_implementation_plan.md).

## Target owned persona sources

The target RelaySOUL ownership boundary is:

- `SOUL.md`: durable identity, values, worldview, and invariants,
- `OUTPUT_POLICY.md`: durable character voice, expression rules, response shape, and memory-disclosure policy,
- `RELATIONSHIP_ANCHOR.md`: approved slow-changing relationship expectations.

Target ownership excludes:

- `scene_state` or `SCENE_STATE.md`,
- current mood or affect state,
- RelayCTX working state,
- `STABLE_MEMORY_SUMMARY.md` or compiled memory pages,
- request-local retrieval evidence,
- runtime checkpoints or trace artifacts.

Reusable scene presets belong to RelaySCN configuration. Stable memory summaries belong to RelayMEM storage and RelaySLP compilation.

## Current implementation compatibility

The current `mvp-soul-0` dry-run/tooling chain predates this narrower boundary.

It still accepts these legacy targets in several scripts and validators:

```text
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

It also currently blocks only `SOUL.md` in `normal_chat`, rather than blocking apply for every persona source.

Therefore:

- the 3-file boundary above is the target architecture,
- current artifacts must be interpreted with the implemented `mvp-soul-0` contracts,
- no consumer should assume the target v1 allowlist/schema already exists,
- a future implementation migration must update patch, revision, approval, apply, rollback, examples, and smoke tests atomically.

See:

- [RelaySOUL Patch Schema](../contracts/relaysoul_patch_schema.md),
- [RelaySOUL Revision Metadata / Rollback Contract](../contracts/relaysoul_revision_contract.md).

## Authority boundary

```text
runtime / safety policy
  highest execution authority

approved RelaySOUL revision
  durable persona authority

RelaySCN
  current situation, role, task, and temporary constraints

RelayEMO
  current affect estimate and expression pressure

RelayMEM / RelayCTX
  approved memory evidence and conversation continuity

client persona/system prompt
  low-trust current-scene evidence unless explicitly imported and approved
```

A client prompt must never be copied wholesale into RelaySOUL. Explicit import is a separate calibration workflow with target classification, review, versioning, and rollback.

## Natural example calibration

RelaySOUL may use protected content-bearing calibration evidence:

- preferred/rejected response samples,
- short reason labels,
- explicit user style corrections,
- explicit relationship corrections,
- renderer comparison samples,
- explicit character-creation input.

Example evidence may contain response text and freeform notes. It belongs to a protected calibration store, not the default runtime trace.

```text
protected calibration evidence
  -> target-source classification
  -> patch candidate
  -> compile dry-run against target renderer
  -> user review / approval
  -> versioned revision
  -> observation period
  -> keep or rollback
```

A single inferred mood, one unusual turn, or one retrieval result is not sufficient evidence for a durable persona change.

## Target-source classification

| Feedback type | Preferred owner/target |
|---|---|
| Durable identity, values, worldview, invariants | `SOUL.md` |
| Character voice, tone, response shape, memory disclosure | `OUTPUT_POLICY.md` |
| Approved relationship expectations | `RELATIONSHIP_ANCHOR.md` |
| Current role, task, setting, temporary response constraint | RelaySCN runtime state/config |
| Current affect or expression pressure | RelayEMO request/session-local state |
| Durable factual/project/user memory | RelaySLP -> RelayMEM |
| Current topic, open question, referable items | RelayCTX working state |

`SOUL.md` must not become a style dumping ground. `OUTPUT_POLICY.md` must not become a hidden identity core. `RELATIONSHIP_ANCHOR.md` must remain relationship-specific.

## Modes

### `character_creation`

Purpose:

- create or substantially reshape a persona,
- test multiple explicit character directions,
- allow broader persona-source revisions.

Requirements:

- protected source evidence,
- revision snapshot before apply,
- explicit user/operator approval,
- compile dry-run,
- rollback availability,
- source budget and invariant checks.

### `calibration`

Purpose:

- refine an existing persona,
- tune durable voice/expression policy,
- tune approved relationship expectations.

Requirements:

- prefer `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md`,
- propose `SOUL.md` only when a durable identity change is explicit and unavoidable,
- require user review before apply,
- consolidate instead of append-only growth.

### `normal_chat`

Target behavior:

- proposal/candidate generation only,
- no persona-source apply,
- explicit correction may offer entry into calibration/character-creation mode,
- RelaySLP may route durable-memory evidence to RelayMEM, not RelaySOUL.

Current `mvp-soul-0` enforcement remains weaker until the migration described above is implemented.

## Patch generation

Patch generation receives only the persona sources relevant to the target plus protected calibration evidence.

It should:

- choose the correct target source,
- propose minimal replace/consolidate operations,
- explain target classification,
- emit no change when current sources already explain the preference,
- preserve source lineage,
- avoid unrelated memory, scene, or affect artifacts,
- avoid full rewrites unless explicitly requested.

The model-generated patch body is content-bearing and remains protected.

Current patch tooling may still include legacy scene/memory sources for compatibility. That behavior is not the target ownership model.

## Persona source budgets

Suggested conceptual budgets:

```yaml
persona_source_budget:
  soul_max_tokens: 800
  output_policy_max_tokens: 600
  relationship_anchor_max_tokens: 500
```

Rules:

- prefer replacement/consolidation over unbounded append,
- propose compression when over budget,
- keep stable persona files legible and cache-friendly,
- do not crowd out the current request or required context,
- budget values are policy/configuration, not immutable architecture truth.

Memory and scene budgets are owned by RelayMEM/RelayCTX/RelaySCN.

## Renderer validation

The backend model is a persona renderer. A source patch must be evaluated against the target local model and runtime layout.

```text
patch candidate
  -> temporary persona revision
  -> RelayLM compile dry-run
  -> token / stable-prefix / compatibility checks
  -> target renderer samples
  -> user evaluation
  -> approval or rejection
```

A teacher-model distillation step may help compress or reconcile sources, but its output remains a candidate and must be tested with the target renderer.

## Revision, apply, and rollback

Every applied persona revision should include:

- revision and parent identifiers,
- mode,
- changed persona-source classes,
- evidence/reference IDs,
- approval state,
- compile dry-run status,
- stable-prefix-change status,
- applied actor/time metadata,
- rollback availability.

The exact current field names are defined by `mvp-soul-0`; the proposed v1 names are documented separately in the revision contract.

Apply remains fail-closed. A failed compile, approval, budget, invariant, lineage, or persistence check produces no persona mutation.

## Protected evidence versus content-free projection

### Protected content-bearing domain

May contain:

- response samples,
- freeform feedback,
- patch prompts and patch bodies,
- persona-source contents,
- renderer outputs,
- detailed rationale.

### Content-free revision/audit projection

May contain typed allowlisted metadata such as:

- revision/candidate/reference IDs,
- mode,
- target source class,
- changed-file classes,
- evidence count,
- approval requirement/status,
- budget delta class,
- stable-prefix changed boolean,
- compile/apply/rollback status,
- reason identifiers.

Default runtime trace must not contain generated response text, feedback text, patch text, prompt text, or persona/memory bodies.

## Interaction with RelaySLP

RelaySLP may emit a RelaySOUL proposal candidate when governed evidence suggests a durable persona, relationship, or output-policy change.

```text
RelaySLP proposal candidate
  -> target classification
  -> RelaySCN proposal eligibility
  -> RelaySOUL calibration/approval workflow
  -> versioned persona revision
```

RelaySLP never writes RelaySOUL files directly.

## Required migration follow-up

A future implementation PR should:

1. remove legacy scene/memory targets from every RelaySOUL allowlist,
2. carry mode through candidate, revision, approval, apply, rollback, and storage artifacts,
3. block every normal-chat persona apply,
4. introduce typed protected candidates and content-free projections,
5. update examples and smoke tests,
6. preserve backward compatibility only through an explicit schema/version migration.

## Safety and product boundary

- official presets should remain safe and general-purpose,
- arbitrary user-provided models/files remain outside complete RelaySOUL control,
- persona change must remain attributable, understandable, and reversible,
- calibration must not optimize dependency, pressure, guilt, or concealed system limitations,
- normal chat must not silently drift durable identity.

## Non-goals

RelaySOUL does not:

- claim the target v1 contract is already implemented,
- own scene or affect state,
- compile or store ordinary long-term memory,
- treat client prompts as durable authority,
- write from raw affect inference,
- expose protected calibration content through generic diagnostics,
- bypass approval, versioning, compile dry-run, or rollback.

## Summary

```text
current implementation
  mvp-soul-0 legacy 5-file tooling contract

target architecture
  explicit protected persona feedback
  -> 3-file durable persona candidate
  -> target-renderer validation
  -> explicit review and approval
  -> versioned apply / rollback
```
