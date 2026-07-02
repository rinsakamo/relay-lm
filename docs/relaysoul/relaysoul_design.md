---
relaylm_doc_type: stable_architecture
relaylm_authority: relaysoul_persona_source_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaysoul
relaylm_update_trigger:
  - persona source ownership changes
  - RelaySOUL proposal/apply boundary changes
  - file-first character workspace source changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelaySOUL patch schema
  - exact revision metadata schema
  - RelayREL apply schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/file_first_character_workspace_design.md
  - ../architecture/pipeline_responsibility_design.md
  - ../contracts/relaysoul_patch_schema.md
  - ../contracts/relaysoul_revision_contract.md
---
# RelaySOUL Design

## Purpose

RelaySOUL is RelayLM's human-in-the-loop durable character-source calibration layer.

It creates, calibrates, versions, approves, applies, and rolls back durable character-source revisions. It does not train model weights and it does not own request-local scene state, current affect state, target-specific relationship state, short-term context, or compiled memory.

```text
RelaySOUL
  -> approved portable character sources

RelayLM runtime
  -> compiles approved sources with current REL, SCN, EMO, MEM, and CTX state
```

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md) and [Project Execution Plan](../architecture/project_execution_plan.md).

## File-first target boundary

The file-first workspace target supersedes the older three-file persona target.

Portable character sources:

```text
SOUL.md
  name, identity, values, temperament, and invariants.
  It should remain meaningful if copied into another compatible product.

STYLE.md
  base voice, tone, roleplay flavor, formatting, and output surface.

EMOTION.md
  emotion-state response profiles such as angry, warm, concerned, focused.
  It defines how emotion changes expression; it is not current emotion state.

BOUNDARY.md
  character-specific privacy, pressure, intimacy, disclosure, and safety-expression limits.

LORE.md
  optional world, backstory, setting, factions, and proper nouns when the character needs them.
```

Related workspace sources owned by other components:

```text
RELATIONSHIP.md
  RelayREL role and parameter vocabulary.

relationships/<target>.md
  RelayREL target-specific relationship instances such as relationships/user.md.

SCENE.md and scenes/*.md
  RelaySCN scene policy and SLP-maintained scene wiki pages.

MEMORY.md and memory/**/*.md
  RelayMEM / RelaySLP memory policy and memory wiki pages.
```

RelaySOUL owns durable portable character-source calibration. RelayREL owns target-specific relationship state and interaction policy. RelaySCN owns scene policy/state. RelayMEM/RelaySLP own durable memory pages and memory candidates.

## Legacy target-name interpretation

Older docs and scripts may still refer to:

```text
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

Target interpretation:

```text
OUTPUT_POLICY.md
  -> STYLE.md for voice/output surface.
  -> MEMORY.md or BOUNDARY.md when the old text was really memory-disclosure or privacy policy.

RELATIONSHIP_ANCHOR.md
  -> RELATIONSHIP.md for role/parameter definitions.
  -> relationships/<target>.md for concrete target-specific relationship state.

STABLE_MEMORY_SUMMARY.md
  -> MEMORY.md for policy.
  -> memory/**/*.md for human-readable memory pages.
  -> .relaylm/build/memory_units.jsonl for compiled units.

SCENE_STATE.md
  -> SCENE.md / scenes/*.md for durable scene policy and scene wiki.
  -> .relaylm/state/scene_state.json for current runtime state.
```

Current compatibility tooling may accept older names until a dedicated implementation PR updates parser allowlists, patch target classification, examples, revision contracts, and smoke tests atomically.

## Authority boundary

```text
runtime / system / safety policy
  highest execution authority

BOUNDARY.md
  character-specific privacy, pressure, intimacy, disclosure, and expression limits

SOUL.md
  durable portable identity and values

RelayREL
  target-specific relationship state and interaction policy

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

## SOUL versus REL

RelaySOUL must keep `SOUL.md` portable.

```text
SOUL.md
  character-intrinsic
  target-independent
  portable

RELATIONSHIP.md + relationships/<target>.md
  relationship-bound
  target-specific
  not portable by itself
```

Examples:

```text
SOUL.md
  The character is quick to anger when important things are treated carelessly.

EMOTION.md
  angry responses become shorter and more direct, while repair remains possible.

RELATIONSHIP.md
  defines trust, attachment, permissions, disclosure, and EMO gain.

relationships/user.md
  user is a valued co-creator and trusted operator.
```

Target-specific facts such as `user is most_important_person`, `probe_impulse_gain is high`, or `public_familiarity_permission is low` belong to RelayREL, not SOUL.

## Natural example calibration

RelaySOUL may use protected content-bearing calibration evidence:

- preferred/rejected response samples,
- short reason labels,
- explicit user style corrections,
- explicit character-creation input,
- renderer comparison samples,
- explicit boundary corrections.

Relationship corrections are usually RelayREL proposals. They may trigger a RelaySOUL proposal only when they reveal a portable character invariant rather than a target-specific relationship parameter.

Example flow:

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

A single inferred mood, one unusual turn, one retrieval result, or one relationship estimate is not sufficient evidence for a durable character-source change.

## Target-source classification

| Feedback type | Preferred owner/target |
|---|---|
| Name, identity, values, worldview, temperament, invariants | `SOUL.md` |
| Character voice, tone, response shape, roleplay flavor | `STYLE.md` |
| Emotion-state response profile | `EMOTION.md` |
| Character-specific privacy, pressure, intimacy, disclosure limits | `BOUNDARY.md` |
| Backstory, world, setting, factions, proper nouns | optional `LORE.md` |
| Relationship roles and parameter vocabulary | RelayREL `RELATIONSHIP.md` |
| Concrete relationship with a target | RelayREL `relationships/<target>.md` |
| Scene selection/generation/merge policy | RelaySCN `SCENE.md` |
| Concrete scene pages and candidates | RelaySCN `scenes/*.md`, `scenes/_inbox/*.md` |
| Durable factual/project/user memory and memory policy | RelayMEM/RelaySLP `MEMORY.md`, `memory/**/*.md` |
| Current topic, open question, referable items | RelayCTX working state |

`SOUL.md` must not become a style dumping ground. `STYLE.md` must not become a hidden identity core. `RELATIONSHIP.md` must not contain target-specific relationship state. `relationships/<target>.md` must not silently rewrite portable character identity.

## Modes

### `character_creation`

Purpose:

- create or substantially reshape a character,
- test multiple explicit character directions,
- allow broader portable-source revisions.

Requirements:

- protected source evidence,
- revision snapshot before apply,
- explicit user/operator approval,
- compile dry-run,
- rollback availability,
- source budget and invariant checks.

### `calibration`

Purpose:

- refine an existing character,
- tune durable voice/expression policy,
- tune emotion profiles,
- tune character-specific boundaries.

Requirements:

- choose the smallest correct source,
- propose `SOUL.md` only when a durable identity/value/temperament change is explicit and unavoidable,
- require user review before apply,
- consolidate instead of append-only growth,
- preserve KV-cache-friendly stable prefixes.

### `normal_chat`

Target behavior:

- proposal/candidate generation only,
- no portable character-source apply,
- explicit correction may offer entry into calibration/character-creation mode,
- RelaySLP may route ordinary durable-memory evidence to RelayMEM,
- RelaySLP may route target-specific relationship evidence to RelayREL proposals.

## Patch generation

Patch generation receives only the target source(s) relevant to the requested change plus protected calibration evidence.

It should:

- choose the correct target source,
- propose minimal replace/consolidate operations,
- explain target classification,
- emit no change when current sources already explain the preference,
- preserve source lineage,
- avoid unrelated memory, scene, relationship, or affect artifacts,
- avoid full rewrites unless explicitly requested,
- keep stable source fragments cache-friendly.

The model-generated patch body is content-bearing and remains protected.

## Persona source budgets and cache stability

Suggested conceptual budgets:

```yaml
persona_source_budget:
  soul_max_tokens: 800
  style_max_tokens: 600
  emotion_max_tokens: 800
  boundary_max_tokens: 600
  lore_max_tokens: 1200
```

Rules:

- prefer replacement/consolidation over unbounded append,
- propose compression when over budget,
- keep stable persona files legible and cache-friendly,
- avoid changing stable uppercase files during normal chat,
- do not crowd out current request, selected relationship state, selected scene state, or selected memory evidence,
- budget values are policy/configuration, not immutable architecture truth.

Memory, scene, and relationship-instance budgets are owned by RelayMEM/RelaySLP, RelaySCN, RelayREL, and RelayCTX.

## Renderer validation

The backend model is a character renderer. A source patch must be evaluated against the target local model and runtime layout.

```text
patch candidate
  -> temporary character-source revision
  -> RelayLM compile dry-run
  -> token / stable-prefix / compatibility checks
  -> target renderer samples
  -> user evaluation
  -> approval or rejection
```

A teacher-model distillation step may help compress or reconcile sources, but its output remains a candidate and must be tested with the target renderer.

## Revision, apply, and rollback

Every applied portable character-source revision should include:

- revision and parent identifiers,
- mode,
- changed source classes,
- evidence/reference IDs,
- approval state,
- compile dry-run status,
- stable-prefix-change status,
- applied actor/time metadata,
- rollback availability.

Apply remains fail-closed. A failed compile, approval, budget, invariant, lineage, persistence, or cache-stability check produces no portable character-source mutation.

## Protected evidence versus content-free projection

### Protected content-bearing domain

May contain:

- response samples,
- freeform feedback,
- patch prompts and patch bodies,
- character-source contents,
- renderer outputs,
- detailed rationale.

### Content-free revision/audit projection

May contain typed allowlisted metadata such as:

- source class names,
- changed-fragment counts,
- token-count bands,
- stable-prefix-change boolean,
- approval state,
- reason IDs,
- rollback availability,
- compile-dry-run status.

It must not contain source file bodies, prompt fragments, relationship bodies, memory bodies, renderer outputs, or raw feedback.

## Summary

```text
RelaySOUL owns portable character-source calibration.
RelayREL owns target-specific relationship policy.
RelaySCN owns scene policy/state.
RelayMEM/RelaySLP own memory pages and memory candidates.
RelayCTX compiles selected sources into cache-friendly backend context.
```
