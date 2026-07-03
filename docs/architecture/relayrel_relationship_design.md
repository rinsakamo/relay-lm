---
relaylm_doc_type: stable_architecture
relaylm_authority: relayrel_relationship_state_and_interaction_policy_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayREL ownership changes
  - relationship source tree changes
  - relationship-conditioned policy changes
  - RelayREL runtime ordering changes
  - Character Workspace relationship compiler changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelayREL parser schema
  - exact relationship update apply schema
  - RelaySOUL portable source mutation schema
  - RelayMEM retrieval implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_responsibility_design.md
  - file_first_character_workspace_design.md
  - character_belief_relationship_dynamics_design.md
  - relayscn_mvp_scene_policy.md
  - context_packing_design.md
  - memory_lifecycle_design.md
  - ../relaysoul/relaysoul_design.md
---
# RelayREL Relationship Design

Last reviewed: 2026-07-03 JST

## Purpose

This document defines RelayREL's target responsibility boundary: target-specific relationship state and relationship-conditioned interaction policy.

RelayREL keeps character identity portable while allowing a character to behave differently with different authenticated targets. It separates:

```text
SOUL / STYLE / EMOTION / BOUNDARY
  -> portable character sources

RELATIONSHIP.md
  -> relationship role and parameter vocabulary

relationships/<target>.md
  -> concrete target-specific relationship instance
```

Current implementation status belongs to [Project Status](../PROJECT_STATUS.md). This document is a target architecture authority for ownership and source placement, not proof that full RelayREL Markdown parsing or relationship update apply already exists.

## Current implementation interpretation

The current P0-PIPE boundary has already established the request-path order:

```text
RelayREL -> RelaySCN -> RelayEMO -> RelayINT -> RelayMEM -> RelayCTX
```

That means RelayREL relationship projection is available before RelaySCN and input-side RelayEMO policy, but it does not mean the full file-first RelayREL source parser/compiler/UI is implemented.

## Owned sources

### `RELATIONSHIP.md`

`RELATIONSHIP.md` defines relationship roles, dimensions, permissions, and bounded update policy.

It may define vocabulary such as:

```text
relationship_roles
trust
attachment
respect_for_autonomy
correction_acceptance
direct_disagreement_permission
teasing_permission
bold_inference_permission
unsolicited_probe_permission
personal_memory_reference_permission
public_familiarity_permission
private_disclosure_permission
emo_gain
repair_style
relationship_update_policy
```

`RELATIONSHIP.md` must not contain a concrete target's private relationship state. It is the stable vocabulary and policy source.

### `relationships/<target>.md`

`relationships/<target>.md` is a target-specific relationship instance. It may represent the relationship between one character and one authenticated user, viewer class, co-host, or other target identity.

It may contain values such as:

```text
role: trusted_operator
trust: high
attachment: medium_high
direct_disagreement_permission: high
teasing_permission: medium
bold_inference_permission: medium
personal_memory_reference_permission: medium
public_familiarity_permission: low
probe_impulse_gain: medium
repair_style: concise_accepting
```

This file has meaning only under a concrete target. It is not portable by itself and must not be copied into another target's relationship instance without explicit user/operator action.

## Non-owned sources

RelayREL does not own:

```text
SOUL.md
  portable identity, values, temperament, and invariants

STYLE.md
  voice, tone, formatting, and output surface

EMOTION.md
  emotion-state response profiles

SCENE.md / scenes/*.md
  scene policy, scene wiki, and scene state ownership

MEMORY.md / memory/**/*.md
  memory policy and human-readable memory pages

BOUNDARY.md
  character-specific privacy, pressure, intimacy, and disclosure limits
```

RelayREL can constrain or modulate how these sources are applied for a target, but it must not silently mutate them.

## Runtime responsibilities

RelayREL is request-side and target-aware.

Responsibilities:

- resolve the active relationship target from route/session/authenticated metadata rather than unsafe natural-language guessing;
- compile a content-free relationship projection for diagnostics;
- provide relationship-conditioned permissions and limits to RelaySCN, RelayEMO, RelayINT, RelayMEM, RelayCTX, and RelaySLP;
- keep target-specific relationship parameters out of portable SOUL identity;
- prevent one-turn relationship impressions from becoming durable user facts;
- require explicit source lineage and update gates for relationship changes.

RelayREL answers:

```text
What relationship-specific interaction policy applies to this target?
```

## Relationship-conditioned policy surfaces

RelayREL may influence:

```text
RelaySCN
  public/private familiarity, audience disclosure pressure, intimacy limits

RelayEMO
  expression gain, probe impulse gain, repair tone, attachment-sensitive salience

RelayINT
  whether direct disagreement, playful challenge, or clarification style is permitted

RelayMEM
  whether personal memory references are appropriate for this target and scene

RelayCTX
  placement and wording constraints for relationship policy blocks

RelaySLP
  whether evidence becomes ordinary memory, relationship update candidate, held item, or proposal
```

These are constraints and modulation hints. RelayREL must not override hard safety, BOUNDARY, or scene-publicness constraints.

## Relationship state versus memory

Relationship state and memory overlap but are not identical.

```text
memory
  what happened, what was said, what is known, what is retrievable

relationship state
  how the character is permitted and inclined to interact with this target
```

A memory can support a relationship update candidate. A relationship update candidate can cite memory evidence. But a memory record must not directly rewrite `relationships/<target>.md` during the synchronous response path.

## Relationship state versus SOUL

RelaySOUL keeps portable character identity stable. RelayREL keeps target-specific interaction state separate.

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

Example:

```text
SOUL.md
  The character values honest co-creation.

RELATIONSHIP.md
  direct_disagreement_permission controls when blunt correction is allowed.

relationships/user.md
  direct_disagreement_permission: high
```

The character's general value belongs to SOUL. The permission to be blunt with this specific target belongs to RelayREL.

## Relationship state versus scene

RelaySCN owns the current scene and public/private situation. RelayREL owns target-specific relationship policy.

```text
RelayREL
  I am close to this target and usually allowed to be direct.

RelaySCN
  This is a public group scene with low tolerance for personal disclosure.
```

When these conflict, the more restrictive scene and boundary policy wins for the current turn. Familiarity does not authorize public over-disclosure.

## Relationship state versus emotion

RelayEMO estimates current affect and expression pressure. RelayREL can modulate expression gain, but it does not own affect classification.

```text
current affect
  concern: medium

relationship gain
  attachment_salience: high
  unsolicited_probe_permission: low

result
  warmth may increase, but intrusive probing remains suppressed
```

## Update path

The target update path is out-of-band:

```text
governed evidence
  -> RelaySLP relationship candidate
  -> authority / confidence / safety classification
  -> hold, reject, ordinary memory, or relationship proposal
  -> explicit review when required
  -> versioned relationship source update
```

No normal response-path stage may silently mutate `RELATIONSHIP.md` or `relationships/<target>.md`.

## Diagnostics

Default public diagnostics must remain content-free.

Allowed classes include:

```text
relationship_target_present: true | false
relationship_projection_status: ok | missing | fallback | invalid
relationship_policy_classes: bounded enum list
permission_bands: high | medium | low | unknown
source_authority: route | approved_source | candidate | none
restrictive_reason_ids: enum list
```

Disallowed in default diagnostics:

```text
relationship file bodies
private target names when not already public
raw user text
relationship notes
filesystem roots
protected evidence snippets
```

## Non-goals

This design does not implement:

- full RelayREL Markdown parser/compiler;
- relationship update apply API;
- Character Workspace relationship UI;
- automatic target identity discovery from free text;
- relationship-state mutation during normal response generation;
- using relationship state to override BOUNDARY, RelaySCN publicness, or safety gates.

## Summary

```text
RelayREL owns target-specific relationship policy.
RelaySOUL owns portable character identity.
RelaySCN owns current scene policy.
RelayEMO owns affect and expression pressure.
RelayMEM owns durable memory evidence.
RelaySLP owns deferred candidate/proposal formation.
```
