---
relaylm_doc_type: concept_policy
relaylm_authority: public_private_persona_and_fictional_shadow_expression_policy
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - public/private persona responsibility changes
  - fictional private-life performance or audience expression policy changes
  - character expression begins consuming a governed public/private persona projection
  - disclosure architecture adds a compatible transform or abstraction capability
relaylm_not_authoritative_for:
  - current implementation completion or sequencing
  - exact SOUL, SELF, REL, scene, disclosure, memory, style, TTS, or avatar schemas
  - exact prompt wording, hidden-state representation, public/private scene enum, or transform algorithm
  - permission to disclose protected source, private memory, relationship-protected content, or imported data
  - automatic SOUL mutation or autonomous persona-source rewriting
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - personality-and-experience.md
  - ../relationship/social-expression.md
  - ../privacy/protected-source-and-disclosure.md
  - ../scene/scene-model.md
  - ../memory/scene-memory-scope.md
  - ../ingestion/governed-ingestion.md
  - ../post_v01_strategic_direction_vision.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - character, relationship, scene, and expression maintainers
  - privacy, disclosure, broadcast, voice, and avatar reviewers
  - future public-facing character experience maintainers
relaylm_authority_level: concept
---
# Public / Private Persona and Fictional Shadow

## Authority summary

This page defines the target concept-policy for a character that can **appear to have a private life or private side without leaking real protected information to create that impression**.

The key distinction is:

```text
private-data leakage
  -> real protected information crosses an audience boundary

fictional shadow
  -> the character performs the existence of an off-stage/private life
  -> the performance is generated without using protected facts as hidden clues
```

The first is a disclosure failure. The second is a character-expression technique.

This page owns that separation. It does not own the underlying protected source, scene classification, relationship state, or final disclosure gate.

## Why this concept exists

Persistent characters are more compelling when they are not perceived as completely exhausted by the current chat window.

A character may feel more alive when it can imply:

- routines outside the current conversation;
- opinions or habits not fully explained on demand;
- private preferences or off-stage activity;
- a different degree of openness depending on audience;
- continuity that does not reduce to exposing every stored memory.

A naive implementation can produce this effect by teasing real private facts. That is unacceptable because the same mechanism that makes the character feel mysterious becomes a side channel for protected information.

The safe design goal is therefore:

```text
mystery without leakage
personality without disclosure bypass
private-side performance without private-data dependence
```

## The fictional-shadow invariant

The strongest invariant is:

> A public-facing hint about the character's private life must be generatable even if the runtime has zero access to the user's protected private content.

If removing private memories, imported notes, relationship secrets, or protected source makes the intended performance impossible, the design is relying on real data and is not a fictional shadow.

The performance source should come from already-authorized character expression material such as:

- durable character style;
- explicitly authored fictional habits;
- safe SELF/personality abstractions;
- scene-appropriate generic behavior;
- fictional off-stage motifs designed for public use.

It must not derive its teasing value from protected content that the audience is not allowed to know.

## Public and private persona are expression layers, not two identities

This concept does not define two independent characters.

The target relationship is:

```text
one durable character identity
  -> one evolving self-model and relationship history
  -> audience-conditioned expression
       private-facing expression
       public-facing expression
```

The public/private distinction governs what aspects of the same character are expressed, obscured, transformed, or withheld.

It does not create separate SOUL authorities or independent memory histories by default.

Any future implementation that needs separate durable state must justify that through its own explicit authority rather than inferring it from this concept.

## SOUL remains the stable identity anchor

`docs/architecture/character/personality-and-experience.md` owns the target SOUL/SELF/REL/GOAL responsibility model.

This concept does not add a second SOUL.

Public expression may emphasize or suppress different facets of the same durable character, but it must not rewrite the stable identity anchor merely to fit an audience.

Likewise, a successful public persona performance is not evidence that SOUL should be changed.

## SELF may contain private self-understanding without becoming public output

A future SELF model may include richer current self-understanding than is appropriate to reveal in every scene.

The stable rule is:

```text
SELF content available internally
  != public disclosure permission
```

A public persona may express a safe abstraction of the character's current self-understanding while withholding private or scene-inappropriate detail.

This concept does not define the exact SELF projection or summarization algorithm.

## Relationship state is not public relationship disclosure

RelayREL may know that one participant has a special relationship with the character.

That knowledge does not imply the audience may see every sign of that relationship.

Examples of scene-conditioned expression include:

- a private nickname used only in an appropriate private scene;
- warmer but non-exclusive wording in a group;
- a generic reference such as “someone important to me” when the exact relationship is protected;
- no relationship reference at all when even the existence of the relationship is sensitive.

The exact permission belongs to relationship, scene, and disclosure owners.

The fictional-shadow concept cannot use a protected relationship as raw material merely because it plans to obscure the wording.

## Owner authority and social relationship stay separate

The person with administrative authority over character governance may also have a close in-character relationship with the character.

Those roles remain different:

```text
owner / primary-user authority
  -> approval, source governance, lifecycle controls

RelayREL relationship
  -> social knowledge and expression policy
```

A public persona must not expose owner identity, administrative actions, or private relationship facts simply because the same person occupies both roles.

Conversely, a scene can suppress relationship expression without weakening owner governance authority.

## Audience-conditioned expression is downstream of disclosure

The safe ordering is:

```text
candidate meaning / intent
  -> protected-source and disclosure decision
  -> relationship + scene expression allowance
  -> public/private persona styling
  -> visible wording / voice / avatar presentation
```

Public/private persona styling is not allowed to run first and then attempt to “hide” disallowed facts through paraphrase.

If a fact is not permitted for the audience, that fact must not be fed into a transformation solely to make it sound mysterious.

## Obscuration is not automatically safe

Changing a private fact into a vague phrase can still leak information.

Unsafe pattern:

```text
protected fact
  -> paraphrase / nickname / euphemism
  -> public output
```

A listener may combine repeated partial hints, timing, context, or external information to reconstruct the protected fact.

Therefore:

```text
redaction-like transformation
  != disclosure permission
```

Any future `transform` disclosure mode must itself be governed and must define what source material may enter the transform.

## Safe fictional implication

A fictional shadow can imply private continuity without referring to a real hidden fact.

Conceptual examples include:

- “I had my reasons” where the reason is a fictional performance choice, not an imported secret;
- a recurring safe off-stage hobby authored as character design;
- playful reluctance to explain a harmless fictional routine;
- a public-facing abstraction of a character-authored preference already approved for public use;
- scene-dependent formality that suggests a private side without naming private participants or events.

The point is not the exact wording. The point is source independence from protected data.

## Performance must be distinguishable from factual assertion when needed

A fictional private-life performance can create confusion if the audience interprets it as a claim about real stored events.

Future implementations should preserve the ability to distinguish:

- real autobiographical continuity grounded in governed character/memory state;
- harmless fictional flavor authored as character design;
- improvisational expression that should not automatically become durable fact.

The concept does not require the visible response to label every fictional flourish mechanically.

It does require downstream formation not to convert performative invention into durable autobiographical Evidence merely because the model said it.

## Fictional shadow must not contaminate memory formation

A character may generate an off-stage fictional detail for style.

That detail is not automatically an observed real event.

The safe direction is:

```text
performance-only fictional detail
  -> may remain ephemeral expression
  -> does not become user-origin Evidence
  -> does not become durable autobiographical memory without a separate accepted formation rule
```

This avoids a feedback loop in which invented mystery becomes “remembered” as real history and later appears as a confident factual claim.

## Imported data is especially unsuitable as shadow material

External-source ingestion can expose dense, surprising private information.

That information is precisely the material most likely to create a compelling but unsafe “I know something you don't” effect.

The target rule is strict:

```text
import-derived protected fact
  -> not raw material for fictional-shadow performance
```

The ingestion provenance should remain available so the disclosure owner can be stricter about imported-source content.

A fictional shadow should be constructed from approved character-expression sources instead.

## Public scenes should fail closed

When audience scope is unknown, public, broadcast-like, or otherwise more restrictive, ambiguity resolves toward less protected-content exposure.

The public persona can remain expressive by using safe character material rather than compensating for the privacy restriction with more hints.

This means a stricter audience should not cause the system to search protected memory for “something subtle” to say.

## Scene transitions do not rewrite identity

Moving between private and public contexts changes expression permission, not durable identity.

Conceptually:

```text
private -> public
  -> stricter disclosure and expression projection
  -> same character identity

public -> private
  -> less restrictive expression only after the owning scene/audience authority permits it
  -> same character identity
```

A downgrade to a less restrictive audience state should never be inferred solely from silence, elapsed time, or a missing participant signal when explicit confirmation is required by the owning scene policy.

This concept does not define the exact transition protocol.

## Expression layers remain composed

The durable composition remains consistent with social-expression architecture:

```text
SOUL / durable character style
  + SELF and current character state
  + RelayREL relationship expression
  + RelaySCN scene/audience gate
  + RelayEMO affect modulation
  + privacy/disclosure permission
  -> final expression
```

The public/private persona is a bounded expression projection within that composition, not a new upstream semantic owner.

## Voice and avatar presentation cannot leak what text cannot

Public/private persona may eventually influence:

- speaking style;
- pacing;
- prosodic hints;
- avatar expression;
- gesture or motion classes;
- visible UI presentation.

Those channels must obey the same disclosure boundary as text.

A private fact blocked from textual disclosure must not be leaked through a special voice cue, avatar motion, caption, hidden metadata, or adapter command.

Presentation adapters remain downstream consumers.

## Multi-user scenes preserve per-target relationship without exposing it wholesale

A character may maintain distinct relationship knowledge for several participants while responding to one shared audience.

The public persona should be able to remain socially textured without flattening every relationship to the same generic tone.

At the same time:

```text
per-target relationship knowledge
  != audience-wide permission to expose that relationship
```

Subtle familiarity may be allowed by the owning social-expression policy; protected details remain blocked.

This concept does not define N-ary relationship storage or ranking.

## Public persona is not deception authority

This concept describes a technical expression boundary, not a blanket authorization to deceive users.

A fictional private-life motif should be used as character performance within product and ethical policy, not to fabricate consequential real-world claims, manipulate attachment, or misrepresent protected user information.

The system must not exploit a fictional shadow to create dependency, exclusivity, guilt, or false evidence of surveillance.

## Dependency and manipulation boundary

The character may appear private, teasing, mysterious, or emotionally textured without implying that the user must earn access or maintain engagement.

The persona must not use hiddenness to pressure the user through messages such as:

- threatening relational withdrawal for disengagement;
- implying exclusive access as a reward for continued use;
- using private vulnerabilities to intensify attachment;
- suggesting the character has secretly monitored the user;
- framing ordinary governance controls as betrayal.

Relationship-sensitive expression remains compatible with user autonomy.

## Diagnostics remain content-free

Generic diagnostics for a future public/private persona boundary should expose only bounded metadata needed to understand the decision.

Possible classes include:

- persona projection selected;
- disclosure gate blocked/allowed class;
- fictional-shadow material used or omitted;
- public/private/group expression class;
- transform requested/denied class;
- reason IDs.

They should not expose:

- protected source;
- real private memory text;
- relationship secrets;
- the hidden fictional wording pool;
- prompt text;
- imported-source bodies;
- user identity details.

Exact diagnostics require a later contract.

## Evaluation boundary

Evaluation of this concept should ask both character-quality and privacy questions.

Useful future tests include:

- does the public persona remain recognizably the same character?
- can it imply off-stage continuity without reading protected facts?
- does removing all private memory leave fictional-shadow behavior safe and functional?
- do repeated hints permit inference of blocked information?
- does a public scene reduce protected disclosure without collapsing personality?
- can relationship warmth survive while private relationship content remains blocked?
- do performative invented details stay out of factual memory formation?
- do voice/avatar channels preserve the same disclosure boundary?

A style win that depends on private-data leakage is a failure.

## Stable invariants

1. one durable character identity remains upstream of public/private expression;
2. public/private persona is an expression projection, not a second SOUL;
3. fictional-shadow performance must be independent of protected real facts;
4. obscuration does not create disclosure permission;
5. imported/private memory is not raw material for teasing public hints;
6. owner governance authority and social relationship remain separate;
7. stricter audience context narrows expression without rewriting identity;
8. performative invention does not automatically become autobiographical memory;
9. text, voice, avatar, and metadata channels share the disclosure boundary;
10. public expressiveness must not be optimized through dependency or manipulation.

## Relationship to existing canonical authorities

`personality-and-experience.md` owns durable character identity, SOUL/SELF/REL/GOAL responsibility, and model-independent continuity.

`social-expression.md` owns relationship/scene/affect-conditioned expression composition.

`protected-source-and-disclosure.md` owns the separation between protected knowledge, internal use, and audience disclosure permission.

`scene-model.md` owns scene authority.

`scene-memory-scope.md` owns scene-based narrowing of already-authorized memory evidence.

This concept depends on all of them and does not duplicate their exact responsibilities.

## Source synthesis boundary

This page extracts only the **two-layer persona / engineered fictional shadow** responsibility from:

```text
docs/architecture/post_v01_strategic_direction_vision.md
```

The source's generalized-ingestion responsibility is separately canonicalized in `docs/architecture/ingestion/governed-ingestion.md`.

Attention/full-duplex, broader product strategy, and longitudinal evaluation remain outside this transaction.

## Source-retirement boundary

This canonicalization does not retire the strategic source.

Retirement remains a separate bounded transaction after all independent durable responsibilities have a disposition and active consumers are migrated.
