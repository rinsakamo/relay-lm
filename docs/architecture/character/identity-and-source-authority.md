---
relaylm_doc_type: subsystem_architecture
relaylm_authority: durable_character_identity_and_portable_source_authority
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaysoul
relaylm_update_trigger:
  - portable character-source ownership changes
  - Character Workspace durable source classes change
  - RelaySOUL calibration, approval, or activation responsibility changes
  - character identity is split from or merged with another subsystem
relaylm_not_authoritative_for:
  - maker-side creative direction for a specific developer-owned character
  - showcase, public starter, publication, or product-knowledge ownership
  - repository-wide implementation completion or sequencing
  - exact RelaySOUL patch, revision, approval, rollback, or filesystem schemas
  - exact Character Workspace parser, compiler, creation, import, or commit schemas
  - target-specific relationship, current scene, current affect, memory, or RelayCTX runtime semantics
  - active-character selection or request-time prompt assembly implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../character-workspace/system.md
  - ../character-workspace/source-compiler.md
  - ../character-workspace/creation-and-import.md
  - ../character-workspace/showcase-starter-product-knowledge.md
  - showcase-character-direction.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../emotion/affect-modulation.md
  - ../memory/system.md
  - ../context/context-assembly.md
  - ../privacy/protected-source-and-disclosure.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_related_contracts:
  - ../../contracts/relaysoul_patch_schema.md
  - ../../contracts/relaysoul_revision_contract.md
  - ../../contracts/character-workspace/source-tree.md
  - ../../contracts/character-workspace/parser-and-validation.md
  - ../../contracts/character-workspace/compiled-projections.md
  - ../../contracts/character-workspace/creation-commit.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelaySOUL and Character Workspace maintainers
  - RelayREL, RelaySCN, RelayEMO, RelayMEM, RelayCTX, and RelaySLP maintainers
  - character creation, calibration, privacy, and migration reviewers
relaylm_authority_level: subsystem
---
# Character Identity and Source Authority

## Purpose

This page is the canonical target architecture for RelayLM's durable, portable character identity and the source-authority boundary around it.

The core distinction is:

```text
portable character identity
  != target-specific relationship state
  != current scene state
  != current affect state
  != durable memory
  != conversation working state
  != active runtime projection
```

RelaySOUL owns durable portable character-source calibration. The Character Workspace provides the human-editable source tree and source lifecycle. Runtime components consume only validated, approved, explicitly activated projections under their own authority.

## Portable identity source

`SOUL.md` is the durable portable identity source.

It owns character-intrinsic material such as:

- name and self-identification;
- durable values and worldview;
- temperament;
- target-independent role or self-concept;
- identity invariants that should remain true across sessions, scenes, and conversation partners.

`SOUL.md` is intended to remain meaningful when the character is moved to another compatible RelayLM installation or renderer.

Portable identity is deliberately narrower than the full Character Workspace.

## Adjacent durable character sources

The target workspace keeps several durable sources adjacent to `SOUL.md` without collapsing them into identity:

```text
SOUL.md
  portable identity, values, temperament, invariants

STYLE.md
  ordinary voice, tone, formatting, response surface, roleplay flavor

EMOTION.md
  response profiles for affect states; not the current affect state

BOUNDARY.md
  character-specific privacy, pressure, intimacy, disclosure, and expression limits

LORE.md
  optional world/backstory/setting material when the character needs it
```

These files may jointly shape a rendered character, but they retain distinct responsibilities.

A style preference is not automatically an identity invariant. A current mood is not automatically an `EMOTION.md` change. A privacy boundary is not optional merely because a style instruction conflicts with it.

## Workspace sources owned elsewhere

Other durable workspace sources belong to different semantic owners:

```text
RELATIONSHIP.md
  RelayREL relationship vocabulary and policy

relationships/<target>.md
  target-specific relationship instance

SCENE.md
  RelaySCN scene policy

scenes/*.md
  reusable or governed scene material

MEMORY.md
  RelayMEM/RelaySLP memory policy

memory/**/*.md
  governed durable memory pages
```

Their presence in one file-first workspace does not transfer their semantic authority to RelaySOUL.

## SOUL versus relationship

The permanent split is:

```text
SOUL.md
  character-intrinsic
  target-independent
  portable

RELATIONSHIP.md
  relationship-role and parameter vocabulary

relationships/<target>.md
  concrete target-specific relationship state
```

A statement such as a general temperament tendency may belong to SOUL. A claim such as a particular user being trusted, familiar, privileged, or important is target-specific and belongs to RelayREL unless separately established as a genuinely portable character invariant.

Repeated closeness with one target must not silently rewrite portable character identity.

## SOUL versus scene

Scene is situational authority.

`SCENE.md`, reusable scene pages, classifiers, and current RelaySCN state may influence what the character is doing now, but they do not redefine who the character is.

A temporary role, task, location, public/private setting, or conversational stance must not be promoted into `SOUL.md` merely because it persisted for several turns.

Conversely, portable identity may constrain scene-compatible behavior without owning current scene selection.

## SOUL versus emotion

`EMOTION.md` describes how expression may vary under affect states. RelayEMO owns current affect estimation/modulation.

The stable rule is:

```text
emotion-response profile
  != current emotion estimate
  != portable identity mutation
```

A transient angry, warm, concerned, focused, or flustered state does not by itself justify a durable source edit.

## SOUL versus memory

Durable facts, project knowledge, user history, observations, and episodic material do not belong in `SOUL.md` merely because they influence responses.

RelayMEM/RelaySLP own memory evidence, lifecycle, storage, retrieval, and memory-page maintenance.

Portable identity may contain broad self-defining facts when they are truly character-intrinsic, but it must not become an unbounded memory summary or a hidden substitute for governed memory.

## SOUL versus RelayCTX

RelayCTX owns request-time context assembly and short-lived conversational continuity.

Current topic, open questions, referable items, selected retrieval, current scene/relationship/affect projections, and user input are runtime context, not durable identity.

The stable relationship is:

```text
approved durable sources
  + separately owned current state
  -> RelayCTX assembly
  -> backend character rendering
```

RelayCTX may compile or select a projection of identity for a request. It does not gain authority to rewrite the source simply because it consumed it.

## Character identity versus active character

A durable character source can exist without being active.

The permanent lifecycle distinction is:

```text
source exists
  != structurally valid
  != compiled
  != approved
  != committed
  != selected as active character
  != consumed by a particular request
```

Identity source authority therefore does not imply runtime activation authority.

Active-character selection and request-time source consumption remain separately governed runtime/product concerns.

## Human-editable source is the durable authority

For the file-first target, approved human-editable source remains the durable character authority.

Generated `.relaylm/build/**` material is derived projection. Cache entries, prompt fragments, summaries, renderer payloads, and request-local blocks are not alternate editable identity authorities.

A generated projection may be deleted and rebuilt from accepted source without erasing the source's durable meaning.

## Source compilation does not mutate identity

Read-only validation and deterministic compilation may classify, parse, hash, and project the source tree.

They do not by themselves:

- approve a proposed identity change;
- apply a RelaySOUL patch;
- select an active character;
- rewrite uppercase source files;
- convert relationship, scene, memory, or context state into SOUL.

The Source Compiler boundary remains a derivation boundary, not a semantic writer.

## Creation and import do not define identity authority

Character creation/import may stage or commit a workspace, but its authoring surface does not become a second identity authority.

A template name, preview card, imported folder name, archive metadata, or UI-selected label is not durable character identity unless the accepted source tree states that identity under the source contract.

A documented example, published template, or source-set draft is likewise a candidate rather than an authority. Showing intended source bodies does not make them a registered workspace, an active character, current runtime state, or portable source authority; only the owning creation, import, validation, approval, and commit lifecycle produces source.

A committed workspace still requires separate active-character selection.

## Client persona and system instructions

Client-supplied persona/system text is lower-trust request input unless explicitly imported through a governed character-source workflow.

It must not be copied wholesale into RelaySOUL or treated as an implicit durable identity revision.

The stable precedence boundary is conceptually:

```text
runtime/system/safety policy
  -> character-specific BOUNDARY constraints
  -> approved portable character sources
  -> separately owned REL/SCN/EMO/MEM/CTX state
  -> client/request instructions under their accepted authority
```

Exact request precedence remains owned by the runtime/pipeline contracts.

## Creator-side design material is not portable source

Material that a character's author holds about the character is a separate class from the character's own portable source.

Maker-side private intent, hidden interpretations, creator-only vision notes, private motives, and other design meta information do not become the character's portable self-knowledge merely because they informed its design.

Such material may enter a portable source only through an explicit reviewed adoption into the correct owning source. Absent that adoption, it is neither identity nor character-held knowledge, and it must not be injected as runtime context or answered as something the character knows about itself.

A character's source therefore carries only what the owning source authority accepted. Creative direction for a specific developer-owned character is owned by its own concept policy rather than by this page.

## Calibration is proposal-oriented

RelaySOUL may use protected calibration evidence to propose durable source changes.

Examples include:

- explicit character-creation input;
- preferred/rejected response samples;
- explicit style or identity corrections;
- explicit boundary corrections;
- renderer comparison samples.

The evidence may be content-bearing and protected.

A candidate source change remains a proposal until the applicable approval/apply boundary succeeds.

## Renderer evaluation is evidence, not authority

A candidate portable-source revision may be evaluated through compile dry-run, target renderer or model samples, and comparison evidence before review.

That evaluation is evidence about the candidate. It is not source authority:

- renderer output does not approve, apply, or become a source;
- a successful rendering does not bypass source ownership, approval, lineage, persistence, or any other owning apply gate;
- a teacher-model, distillation, or compression output is still a candidate and remains subject to the same authority.

The exact renderer schema, model, and backend layout are owned by the runtime and evaluation domains, not by this page.

## Smallest-correct-source rule

Calibration should choose the smallest source that owns the requested durable change.

Examples:

```text
identity/value/temperament invariant
  -> SOUL.md

ordinary voice/formatting
  -> STYLE.md

affect-conditioned expression profile
  -> EMOTION.md

privacy/intimacy/disclosure expression limit
  -> BOUNDARY.md

world/backstory/setting proper nouns
  -> optional LORE.md

target-specific relationship fact
  -> RelayREL source/proposal

scene-specific fact or policy
  -> RelaySCN source/proposal

durable memory fact
  -> RelayMEM/RelaySLP source/proposal
```

This rule prevents `SOUL.md` from becoming a dumping ground for all personalization.

## Durable-change evidence threshold

A durable identity change should be explicit and stable enough to justify portable-source mutation.

One unusual turn, one inferred mood, one retrieval result, one temporary scene, or one relationship estimate is insufficient by itself.

Character creation and calibration are the explicit durable-source workflows. Normal conversation may generate a candidate or offer entry into one of them, but ordinary chat must not silently rewrite portable identity. Exact workflow modes and reason identifiers remain contract authority.

## Explicit approval and fail-closed apply

High-impact durable character-source changes are approval-oriented.

The stable architecture requires that proposal, review, apply, and rollback remain distinguishable lifecycle stages.

A failed validation, compile, approval, lineage, persistence, or other owning gate must not be converted into a successful portable-source mutation.

Exact patch/revision fields and apply mechanics are contract authority, not this page.

## Revision and rollback principle

Applied portable-source changes should remain attributable to a revision lineage and be recoverable through the owning revision/rollback contract.

This architecture requires the capability boundary but does not duplicate exact revision IDs, fields, hashes, timestamps, or transaction mechanics.

Rollback restores an accepted source revision. It is not permission to restore unrelated relationship, scene, memory, or runtime state.

## Protected calibration domain

Content-bearing source calibration material may include:

- source file bodies;
- freeform feedback;
- preferred/rejected response examples;
- patch prompts and patch bodies;
- renderer outputs;
- detailed rationale.

Such material belongs to the protected calibration/tooling domain and must not be copied into generic runtime diagnostics merely because RelaySOUL used it.

## Content-free operational projection

Generic diagnostics may expose bounded metadata such as:

- source class;
- changed-fragment count;
- approval state;
- compile-dry-run state;
- stable-prefix-change boolean;
- rollback availability;
- bounded reason IDs.

They must not expose source bodies, prompt fragments, relationship or memory bodies, renderer output, or raw feedback.

Exact diagnostic schemas remain contract authority.

## Safety and BOUNDARY precedence

`BOUNDARY.md` contains character-specific expression/privacy/intimacy/disclosure limits, but it does not replace higher-level runtime/system safety policy.

A character source cannot authorize the runtime to reveal protected data, bypass permission checks, or weaken a system safety boundary.

Similarly, a stronger relationship does not automatically override `BOUNDARY.md` or protected-source disclosure policy.

## Portability invariant

A portable character source should not depend on hidden local runtime identity to make sense.

`SOUL.md` should remain interpretable without a particular:

- user ID;
- room ID;
- session ID;
- relationship instance;
- current scene;
- current affect estimate;
- current memory retrieval result;
- queue/job/worker identity.

When such state is required, it belongs to the owning runtime/source domain and is composed with SOUL rather than embedded into it.

## Cache-stability principle

Portable sources are comparatively stable and may participate in stable prompt-prefix/KV-cache tiers.

Cache stability is an optimization constraint, not an authority rule.

A newer approved source revision must not be ignored merely to preserve a stale cache prefix. Conversely, normal chat should not churn portable sources just to optimize a current response.

Exact source/token budgets are policy/configuration and are not immutable architecture truth.

## Legacy source-name interpretation

Older RelaySOUL tooling may still refer to source names such as:

```text
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

Those names are compatibility/current-tooling concerns, not the target file-first ownership model.

Target responsibility maps their durable meanings into the smallest current source domain, for example style/boundary, relationship, memory, or scene ownership.

This page does not claim that every current patch parser or legacy tool has already completed that migration. Current implementation status remains Project Status and exact current contracts.

## Stable invariants

- `SOUL.md` owns portable target-independent character identity and invariants.
- `STYLE.md`, `EMOTION.md`, `BOUNDARY.md`, and optional `LORE.md` are adjacent durable sources, not aliases for SOUL.
- RelayREL owns target-specific relationship semantics.
- RelaySCN owns current scene semantics.
- RelayEMO owns current affect state/modulation.
- RelayMEM/RelaySLP own durable memory evidence, lifecycle, and memory-page semantics.
- RelayCTX owns request-time context assembly rather than source mutation.
- Client persona/system text is not durable character authority unless explicitly imported and approved.
- Creator-side private intent, hidden interpretation, and design meta material are not portable character source without explicit reviewed adoption.
- Renderer, teacher-model, and comparison output is calibration evidence and never bypasses an owning apply gate.
- Existence, validation, compilation, approval, commit, activation, and request consumption remain distinct states.
- A documented example, template, or source-set draft is a candidate, not a registered workspace or active character.
- Generated projections are derived artifacts, not editable identity authority.
- Normal chat does not silently rewrite portable identity.
- Durable changes use the smallest correct owning source.
- Calibration content remains protected; generic diagnostics remain content-free.
- Character-specific boundaries never override higher runtime/system safety policy.
- A target relationship, scene, affect state, memory result, or cache optimization cannot silently redefine portable identity.
- Exact patch/revision/apply/rollback schemas remain contract authority.
- Project Status remains repository-wide implementation authority.

## Non-goals

This page does not define:

- exact Markdown schemas or headings for character sources;
- exact RelaySOUL patch-candidate fields;
- exact revision, digest, lineage, approval, or rollback schemas;
- filesystem transaction mechanics;
- Character Workspace creation/import API details;
- active-character selection implementation;
- request-time prompt block ordering;
- relationship, scene, emotion, memory, or context state schemas;
- model training or weight updates;
- a remote character marketplace or registry;
- repository-level implementation sequencing.

## Related architecture

- [Character Workspace](../character-workspace/system.md)
- [Source Compiler](../character-workspace/source-compiler.md)
- [Creation and Import](../character-workspace/creation-and-import.md)
- [Showcase, Public Starter, and Product Knowledge Ownership](../character-workspace/showcase-starter-product-knowledge.md)
- [Rin / ReLM Showcase Character Direction](showcase-character-direction.md)
- [Relationship State](../relationship/relationship-state.md)
- [Scene Model](../scene/scene-model.md)
- [Affect Modulation](../emotion/affect-modulation.md)
- [Memory System](../memory/system.md)
- [Context Assembly](../context/context-assembly.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
