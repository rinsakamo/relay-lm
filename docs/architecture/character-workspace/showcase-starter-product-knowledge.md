---
relaylm_doc_type: concept_policy
relaylm_authority: showcase_starter_and_product_knowledge_ownership
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - official showcase character roles change
  - bundled public starter ownership or initial-state rules change
  - RelayLM onboarding or product-help knowledge lifecycle changes
  - character template or knowledge-package attachment policy changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact product-knowledge manifest, storage, retrieval, or attachment schema
  - exact SourceEvent, evidence-admission, RelayATN, RelayCTX, RelayMEM, RelayREL, RelaySCN, or RelaySLP contract
  - exact Forget, migration, backup, rollback, or workspace commit protocol
  - private twin data, unpublished character sources, or ReLM's own self-knowledge
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../character/showcase-character-direction.md
  - ../character/identity-and-source-authority.md
  - ../character/personality-and-experience.md
  - ../character/interaction-quality.md
  - creation-and-import.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - Character Workspace showcase, starter, template, and import maintainers
  - public showcase asset and publication reviewers
  - product-knowledge lifecycle and onboarding maintainers
relaylm_authority_level: concept
---
# Showcase, Public Starter, and Product Knowledge Ownership

Last reviewed: 2026-07-16 JST

## Purpose

This policy defines the target ownership separation between:

1. developer-owned showcase characters,
2. the public unnamed starter,
3. user-authored or imported characters, and
4. official RelayLM onboarding and product-help knowledge.

Its primary authority is the asset-class and lifecycle boundary. It does not define the exact runtime schema or transport used to implement that boundary.

## Canonical product message

RelayLM does not distribute ReLM as the user's personal character.

RelayLM distributes a character workspace and a blank adoptable vessel so that each user can grow a character with the kind of continuity, memory, relationship, and scene behavior demonstrated by ReLM.

## Asset classes

### Developer-owned showcase characters

Rin and ReLM are the developer's own demo and showcase characters. They demonstrate authored identity, long-term continuity, relationship behavior, scene differences, memory use, and public presentation.

They are not the standard character that a new user adopts as their own.

#### Rin

- Rin is a fictional self-parody persona based on the developer, not the developer's raw identity or private twin data.
- Rin is a male 男の娘 character.
- The normal and human-operated first-person form is `僕`.
- The chibi or twin-degraded first-person form is `ボク`.
- `僕` versus `ボク` is an auxiliary provenance cue, not a second personality.
- The exact operator, authority, evidence, and memory contract is owned by the relevant runtime architecture and contracts, not by this policy.

#### ReLM

- ReLM is a developed showcase character demonstrating what a grown RelayLM character can feel like.
- A public ReLM source set or fixture may be published only as reviewed, synthetic, reproducible showcase material.
- ReLM is not the default adoptable starter and must not arrive as the user's character with an implied pre-existing relationship to the real user.
- ReLM's authored relationship to Rin remains showcase-specific synthetic material.

### Public unnamed starter

The bundled public starter is the unnamed grey-haired, green-eyed vessel derived from the same visual lineage.

The starter is intended for adoption and growth by the user.

Required initial state:

```text
name
  unset until the user names the character

relationship to the user
  no prior relationship
  empty relationship anchor or target instance

personal memory
  no user relationship memory
  no conversation-derived memory
  no individualized character memory

identity
  minimal, safe starter identity that supports naming and growth
```

"Memory zero" means zero personal, relationship, and conversation-derived memory. It does not require the starter to be unable to explain RelayLM itself.

Visual lineage:

```text
Rin      black hair / blue eyes  -> authored origin
ReLM     white hair / red eyes   -> grown showcase
starter  grey hair / green eyes  -> not yet colored by a relationship
```

The starter must not receive an official personal name. The user owns the naming event and the relationship that follows it.

### User-authored and imported characters

User-authored and imported characters are the primary Character Workspace path.

They must not inherit Rin or ReLM relationship fixtures, synthetic showcase memories, or private developer material. They may explicitly attach official RelayLM product-help knowledge without becoming Rin, ReLM, or a developer-review persona.

### Official RelayLM product knowledge

RelayLM onboarding and Q&A content is application-maintained product knowledge. It is not character identity, relationship state, personal memory, or evidence about the user.

It may cover:

- what RelayLM is,
- the Character Workspace source model,
- SOUL, STYLE, EMOTION, SCENE, RELATIONSHIP, MEMORY, and BOUNDARY roles,
- editable Markdown source versus generated `.relaylm/**` artifacts,
- character creation, import, editing, and growth,
- memory behavior and disclosure boundaries,
- local privacy expectations,
- backup and migration basics,
- compact troubleshooting and known limitations.

It must not contain:

- current PR status,
- private roadmap arguments,
- hidden diagnostics,
- queue or memory identifiers,
- private developer facts,
- claims that target architecture is already implemented.

## Product-knowledge lifecycle invariants

Official product knowledge must remain distinguishable from the active character's own sources and memories end to end.

```text
provenance
  official RelayLM product knowledge

versioning
  tied to a RelayLM or product-knowledge version

mutation
  not rewritten, merged, strengthened, summarized away, or superseded
  by ordinary RelaySLP personal-memory maintenance

forget semantics
  not removed by ordinary personal-memory Forget

relationship semantics
  never treated as evidence about the user or the character-user relationship

voice
  may be rendered through the active character's STYLE and scene behavior

attachment
  bundled with the official public starter
  explicitly attachable to user-authored or imported characters
```

A retrieval implementation may share indexing or context-selection infrastructure with character memory. Shared machinery does not make product knowledge personal MEM. Provenance, authority, update policy, and deletion semantics remain separate.

The exact package path, manifest, retrieval envelope, attachment UI, and update protocol are deferred to later architecture and contract work.

## Current implementation adapter

The current CW-A5 implementation may project onboarding help through a protected pinned page such as `memory/topics/relaylm.md`.

That representation is an implementation adapter, not the target ownership model. While the adapter remains live:

- the page may be selected through the ordinary retrieval/compiler path;
- current behavior must be described honestly as pinned template-scoped memory;
- no document may claim that a dedicated knowledge package, manifest, attachment UI, migration, or separate Forget path is already implemented.

## Authority precedence and superseded target text

For the onboarding/product-help knowledge boundary, this policy supersedes the target statements that describe official RelayLM onboarding knowledge as ordinary character memory in:

- `docs/architecture/pinned_normal_memory_pages.md`.

That document remains usable for its other scopes and for the current pinned-page adapter until its canonical cutover or migration update. It is not authoritative for the final product-knowledge ownership or lifecycle model.

The retired RelaySOUL ReLM source-set draft and the retired Character Template and Creation Flow target source carried the same superseded assumption. Neither is a live document, so their onboarding-as-ordinary-memory target is not restored by this policy or by any successor.

The stable creation/import responsibility model and the exact current creation, template-validation, and commit semantics are owned by:

- `docs/architecture/character-workspace/creation-and-import.md`, and
- `docs/contracts/character-workspace/creation-commit.md`.

## Showcase publication boundary

- Rin is published only as a fictional self-parody, never as the developer's raw identity or private twin and never as a claim about a real person's life.
- Showcase fixtures are synthetic or explicitly reviewed authored material.
- Public showcase assets contain no real private life, real third-party facts, private twin material, or maker-side hidden/private meta settings presented as portable character data.
- Public character lore is identified as authored fiction rather than a real-person claim.
- Public showcase publication contains no material that identifies or reproduces third-party intellectual property.

These are durable ownership and publication constraints, not an exact machine schema or publication gate.

## Safety and lifecycle invariants

- Private twin data is never bundled with showcase or starter assets.
- The unnamed starter begins without fake familiarity or user-specific intimacy.
- Product knowledge cannot become evidence for relationship updates or subjective personal memory.
- A character may explain RelayLM in its own voice without claiming the product facts were personally experienced.
- Imported third-party characters do not receive product knowledge silently; attachment must be explicit unless the user selected an official starter that declares it.

## Related documents

- [Character Workspace Architecture](system.md)
- [Character Workspace Creation and Import](creation-and-import.md)
- [Pinned Normal Memory Pages](../pinned_normal_memory_pages.md)
- [Character Workspace Creation and Commit Contract](../../contracts/character-workspace/creation-commit.md)
- [Rin / ReLM Showcase Character Direction](../character/showcase-character-direction.md)

## Non-goals

- Implementing a product-knowledge runtime, schema, or migration.
- Changing the current Character Workspace parser or retrieval behavior.
- Publishing private Rin SOUL, REL, SCN, EMO, MEM, or twin-extraction sources.
- Making ReLM the default active character.
- Auto-creating or auto-activating any character workspace.
- Finalizing image, Live2D, TTS, broadcast, or multi-agent runtime behavior.
