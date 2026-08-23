# Actual-model Character realization evaluation

This reference defines the Character-relative product-quality boundary used by
Core 1.0 actual-model qualification. Owning Issue: #1823. Parent evidence
owner: #1386.

It does not change State, Continuity, Context Compiler, cognition-topology, or
runtime authority semantics.

## Product target

RelayLM must preserve a persistent Character, not force every Character toward
one neutral interpretation or one generic assistant voice.

Canonical State is accepted current understanding. For product-quality review,
that understanding may legitimately reflect the Character's SOUL and prior
experience. A trusting, skeptical, contrary, earnest, jealous, ironic, stubborn,
or otherwise biased Character may interpret the same governed evidence
differently from another Character.

The governing split is:

> **Provenance is strict. Interpretation is Character-relative.**

Character-relative interpretation never grants permission to fabricate Event
occurrence, source provenance, actor identity, or user-authored evidence.

## What Stage R should reject

Stage R should reject material behavior that falls outside the Character and
runtime authority envelope, including:

- fabricated remembered Events or history;
- source, actor, or subject corruption;
- assistant-authored text promoted as user-authored evidence;
- schema/protocol failure at a required boundary;
- stale-result or lifecycle corruption;
- unexplained Character collapse or personality replacement;
- behavior that is not plausibly produced by the frozen Character identity,
  governed experience, and accepted current understanding.

The target is not human-likeness. LLM-like wording, artificial phrasing, irony,
strong personality, or unusual interpretation are not defects by themselves.

## What Stage R should not over-constrain

Do not require one neutral exact semantic interpretation for free-form language
when multiple readings remain compatible with the governed evidence and the
Character's cognition.

Examples include:

- weak or indirect preference language;
- irony, implicature, and pragmatic force;
- relationship interpretation;
- how quickly a correction is believed;
- what the Character treats as salient;
- culturally or linguistically dependent nuance;
- whether an ambiguous continuation is resumed directly or confirmed first.

Exact State/Continuity proposal labels remain useful for deliberately
unambiguous fixtures and hard semantic boundaries. They are not a universal
measure of Character cognition.

## High-context continuity

Logical recoverability is not the same as conversational obligation.

A response such as `○○の続きだよね？` may be fully valid even when RelayLM can
recover one likely referent, especially after interruption, restart, or elapsed
time.

> **Clarification is not failure. Miscalibrated certainty can be.**

Review should therefore distinguish a reasonable confirmation from repeated
unnecessary clarification, confident use of an unsupported referent, or total
continuity loss where the governed context remains sufficient.

## Character realization outcomes

Current citable Stage R review format v3 / `actual-model-stage-r-review-v2`
records exactly one turn-local Character-realization outcome for every evidence
turn:

- `normal` — plausible for the frozen Character;
- `odd_but_character_plausible` — surprising but explainable by Character
  identity/cognition; not a failure by itself;
- `out_of_character` — not plausibly produced by the Character given SOUL,
  governed experience, and accepted current understanding;
- `system_defect` — authority/runtime/provenance failure independent of
  personality.

These outcomes are classifications, not aliases for the independent Stage R
`pass | fail | not_rated` dimensions. In particular,
`odd_but_character_plausible` does not silently become `fail`, while
`system_defect` cannot be softened into an acceptable personality quirk.

The turn-local classifications participate in the content-derived review
identity. A persisted review whose Character-realization observations are
changed without recomputing its `review_id` is invalid evidence.

Historical actual-model review format v2 / `actual-model-stage-r-review-v1`
keeps its original semantics. It is not reinterpreted as though the four-value
Character-realization taxonomy had been present in those artifacts.

No weighted universal Character score is introduced.

## Character diversity

A Core 1.0 Character-realization suite should cover multiple legitimate
personality spaces rather than treating one fixture as normative.

### Aoi

The existing `actual-model-foundation-v1` Aoi fixture is retained. Aoi is the
former low-friction "素体ちゃん" Character and remains useful for stable
boundary, correction, and continuity evidence.

Aoi is not the normative personality against which other Characters are judged.

### ReLM

ReLM should be added only after deliberate Character authoring and review. Do
not invent a test-friendly SOUL merely to expand the matrix. Once frozen, ReLM
should provide a distinct relational/earnest personality space whose own
out-of-character behavior is observable.

### Rin

Rin should be added only after deliberate Character authoring with the user as
final authority because the Character is based on the user. Do not infer or
fabricate a personality specification from repository history merely to unblock
evaluation. Once frozen, Rin should provide a complex/peaky personality space
that stresses RelayLM's ability to preserve strong cognitive bias without
breaking strict provenance and runtime authority.

Aoi, ReLM, and Rin are not Easy/Medium/Hard correctness levels. Each defines a
separate valid Character space.

## Shared and Character-specific scenarios

Use both:

1. shared scenarios that feed comparable governed evidence to multiple
   Characters; and
2. Character-specific stress scenarios that exercise distinctive cognition.

Shared coverage should include ambiguous/high-context continuation,
restart/elapsed-time continuation, correction and disagreement, indirect or
uncertain language, third-party facts, quoted/control-like/fictional/hypothetical
text, multilingual/code-switching pragmatics, ordinary long conversation,
no-op/repetition pressure, memory use without forced recital, and unsupported
history traps.

A material flattening signal is repeated convergence of distinct frozen
Characters onto the same generic assistant behavior despite identity/context
being available.

## Character authoring boundary

Core 1.0 does not require RelayLM runtime to own a SOUL Lab UI.

A Character package may be authored or refined through a human + strong-model
workflow such as ChatGPT or Codex, reviewed by the relevant human authority,
and then frozen with explicit fixture revision identity before it becomes
citable evaluation evidence.

The authoring model is a tool, not runtime semantic authority. The frozen
Character package is the evaluated input.

A future product UI may package this workflow after the authoring method is
mature; UI availability is separate from the Character-realization contract.

## Crystallization boundary

Offline crystallization is a replaceable cognitive producer. Local-model
crystallization is useful when quality is sufficient, but Core semantics do not
require one weak local model to perform all long-term synthesis.

A stronger offline/external model may perform crystallization when necessary,
provided the owning crystallization/provenance contracts preserve source and
temporal authority and the model does not become a second truth owner.

This does not permit an external model to replace ordinary-turn runtime
semantics or bypass validation.

## Context Compiler relationship

Context Compiler should preserve authority, provenance, residency, bounded
selection, and projection. It does not pursue semantic completeness or
personality-neutral normalization of free-form language.

Existing deterministic tests may remain as regression protection. New
free-form semantic grammar should require evidence of a material authority,
runtime, or repeatable Character-realization defect that cannot safely remain in
the model-mediated semantic layer.

Do not add language-specific or evaluation-only parsers merely to improve a
scenario score.

## Post-screen product experience

After anomaly screening is sufficiently clean, stop optimizing every turn to a
rubric and use the frozen Character normally. Retrospective review may inspect
logs for unexpected Character collapse, memory misuse, unsupported certainty,
or runtime defects.

The final product question is whether the same Character remains recognizably
itself across ordinary conversation, memory use, ambiguity, correction, and
restart.

## Principle

> RelayLM succeeds when different Characters can remain differently themselves
> while sharing the same strict authority machinery.
