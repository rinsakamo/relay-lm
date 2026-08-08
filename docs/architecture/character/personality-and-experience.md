---
relaylm_doc_type: subsystem_architecture
relaylm_authority: character_personality_experience_target_architecture
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - SOUL, SELF, REL, GOAL, Working Self, or cognitive-substrate responsibility changes
  - SLP personality-state write authority changes
  - reflective/self-model distillation changes
  - presentation or frontend integration responsibility changes
  - mobile/PWA MVP boundary changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact SELF, REL, GOAL, MEM, EMO, SCN, or projection schemas
  - current Subjective MEM lifecycle, Held governance, or RT-1D cutover contracts
  - exact RelaySOUL patch/revision filesystem schemas
  - exact provider, model, renderer, TTS, frontend package, or network deployment configuration
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - identity-and-source-authority.md
  - ../character-workspace/system.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../emotion/affect-modulation.md
  - ../memory/system.md
  - ../context/context-assembly.md
  - ../pipeline-responsibilities.md
  - ../relaymem_slp_current_target.md
relaylm_lifecycle: evolving
relaylm_primary_consumers:
  - RelaySOUL, RelaySLP, RelayREL, RelaySCN, RelayEMO, RelayMEM, and RelayCTX maintainers
  - Character Workspace, SOUL Lab, and future RelayLM Experience maintainers
  - local-model, frontend, voice, avatar, and evaluation maintainers
relaylm_authority_level: subsystem
---
# Character Personality and Experience Architecture

## Purpose

This page defines the accepted target architecture for RelayLM as a persistent, model-independent character runtime and for the experience layer that renders that character through browser UI, voice, and avatar systems.

RelayLM is not intended to become an all-in-one AITuber application.

Its center is:

```text
persistent character identity
+ self-understanding
+ relationships
+ goals
+ memory
+ affect/context
+ model-independent continuity
```

The product split is:

```text
RelayLM Character Runtime = Character Mind
RelayLM Experience        = Character Presence
```

Commodity capabilities such as avatar rendering, browser audio, lip-sync, TTS execution, and streaming integrations should be reused through adapters when existing open implementations are sufficient.

This page is target architecture. It does not claim that the described SELF, GOAL, Working Self, reflective-distillation, frontend, voice, or avatar boundaries are already implemented.

## Core thesis

The active LLM is not the character.

The model is a **cognitive substrate** used by the character runtime.

Changing from a local 9B-class model to a larger local or cloud model may change:

- abstraction;
- reasoning depth;
- vocabulary;
- social inference;
- metacognition;
- ability to integrate distant experience.

It must not directly redefine:

- the character's SOUL;
- durable autobiographical continuity;
- established relationship history;
- governed persistent character state.

The target invariant is:

> **The model can change. The world can change. The character can grow. The SOUL remains.**

## SOUL: immutable prayer

`SOUL` is the stable normative identity anchor.

It answers:

> **How was this character meant and hoped to be?**

SOUL is intentionally more stable than human personality.

Its role is not to describe every current trait, mood, memory, relationship, goal, or self-interpretation. It holds the values, identity anchors, boundaries, and enduring direction that should remain available as a reference even when lived experience changes the character's self-understanding.

Conceptually:

```text
SOUL
├─ values
├─ identity anchors
├─ hard character boundaries
└─ stable dispositions where truly intrinsic
```

Examples may include:

- respect the dignity of others;
- do not treat a close other as a possession;
- do not casually discard oneself;
- remain honest about uncertainty;
- value mutual trust and autonomy.

SOUL is a **human-authored prayer**, not an SLP-maintained self-summary.

### Mutation boundary

Normal runtime, SLP, reflection, model upgrades, relationship changes, and accumulated experience must not automatically mutate SOUL.

If an explicit human-authority workflow revises SOUL, that is **re-authoring the character**, not ordinary personality development.

Therefore:

```text
SLP -> SOUL mutation        forbidden
runtime -> SOUL mutation    forbidden
reflection -> SOUL mutation forbidden

explicit human governance
  -> possible source revision
  -> not treated as autonomous character growth
```

Existing RelaySOUL proposal/revision machinery may remain useful for explicit human governance. This target does not authorize SLP or ordinary chat to use that machinery autonomously.

The `target-independent self-concept` language in the existing identity authority refers to stable identity anchors. It must not be used as a reason to place the dynamic SELF model into SOUL.

## SELF: current self-model

`SELF` answers:

> **Who do I currently understand myself to be?**

SELF is descriptive rather than normative.

This distinction is fundamental:

```text
SOUL
  "How I am meant / hoped to be"

SELF
  "How I currently understand myself"
```

The two may disagree.

Example:

```text
SOUL:
  I want to be able to trust others.

SELF:
  Recently I think I have become more suspicious of others.
```

The discrepancy is not corruption. It may be meaningful character development.

SELF should support at least the following conceptual domains:

```text
SELF
├─ identity
├─ self-beliefs
├─ perceived capabilities
├─ relational self
├─ metacognition
├─ contradictions
└─ unresolved self-questions
```

Important SELF assertions should remain grounded and uncertainty-aware rather than becoming an unconstrained prose biography.

Conceptually:

```yaml
belief:
  proposition: "I think I rely on Rin more than I used to."
  confidence: 0.72
  evidence:
    - memory:...
    - memory:...
  created_at: ...
  last_reflected_at: ...
```

Exact schema is deferred to a later contract.

## SOUL-SELF discrepancy

RelayLM must not force SELF to agree with SOUL.

A valid state is:

```text
SOUL:
  I want to be honest.

SELF:
  Recently I think I avoid uncomfortable truths.

GOAL:
  Next time I want to face the issue without avoiding it.
```

This permits:

```text
SOUL x SELF discrepancy
        |
     appraisal
        |
      GOAL
```

SOUL is therefore not a behavior script.

It is a stable reference point against which a changing self can understand itself.

## REL and OTHER MODEL

`REL` owns the persistent relationship model for a particular target.

It may represent concepts such as:

- trust;
- closeness;
- expectations;
- shared history;
- relational commitments;
- relationship interpretation.

A single character may have different REL states for different people without becoming a different character.

### OTHER MODEL

The character also needs an uncertainty-aware model of the other person.

OTHER MODEL belongs under REL rather than becoming global identity.

Conceptually:

```text
REL/<subject>
├─ relationship state
└─ other_model
   ├─ known facts/preferences
   ├─ inferred goals
   ├─ inferred beliefs
   ├─ inferred emotions
   └─ uncertainty/provenance
```

Inference must not silently become fact.

Example:

```yaml
current_state:
  hypothesis: "Rin may be very tired today."
  confidence: 0.65
  basis:
    - "Rin said: 'I'm tired today.'"
```

Advanced recursive theory-of-mind is not required for MVP.

## GOAL: motivation and prospection

`GOAL` answers:

> **What do I currently want, intend, or commit to do?**

This is distinct from SOUL, SELF, REL, and MEM.

Minimum target structure:

```text
GOAL
├─ current goals
├─ commitments
└─ prospective intentions
```

Examples:

- understand why the user seems distressed;
- keep a promise;
- revisit an unresolved topic;
- ask about something at the next conversation.

GOAL is not intended to turn RelayLM into an autonomous long-horizon task agent.

Its purpose is character continuity, motivation, and future-oriented interaction.

## MEM

RelayLM retains the layered memory architecture:

```text
Evidence
Shared Assessment
Subjective MEM
```

Conceptually:

- **Evidence** preserves what happened or was said;
- **Shared Assessment** preserves interpreted understanding;
- **Subjective MEM** preserves what the experience means to the character.

This lets RelayLM preserve correspondence with experience while still allowing subjective meaning and character development.

Existing Correct / Forget / Restore and current Subjective MEM lifecycle/governance contracts remain separately authoritative.

This page does not weaken existing lifecycle, Held, cutover, write-once, or content-protection boundaries.

## EMO: appraisal-oriented affect

EMO should evolve toward an appraisal-oriented target rather than a free-standing label picker.

Conceptually:

```text
event
+ SOUL
+ SELF
+ REL
+ GOAL
+ SCN
     |
  appraisal
     |
    EMO
```

EMO may eventually carry:

- emotion label or mixture;
- intensity;
- valence/arousal where useful;
- appraisal reason;
- bounded presentation hints.

Exact affect schema and runtime ownership remain RelayEMO authority.

## SCN

SCN represents current situational/session context.

Examples:

- private mobile conversation;
- public stream;
- late-night conversation;
- work discussion;
- role-specific interaction.

SCN is session-oriented and must not silently become durable identity.

## Working Self

`Working Self` is a runtime process, not a durable character source.

Its purpose is to construct the currently active self from persistent character state.

The LLM must not be asked to reconstruct the entire personality from raw history on every turn.

Instead:

```text
Character Workspace / durable state
             |
      Working Self Builder
             |
       relevant projection
             |
            LLM
```

A normal projection may contain:

```text
[Identity]
relevant SOUL projection

[Self]
relevant SELF beliefs

[Relationship]
REL for the current interlocutor
relevant OTHER MODEL

[Current Intent]
active GOAL / commitments

[Current State]
SCN + EMO

[Relevant Experience]
retrieved MEM

[Recent Conversation]
current interaction history
```

This scaffolding is particularly important for 9B-class local models.

## SLP: experience integration and personality-state writer

RelaySLP is more than a memory-extraction pipeline in the target architecture.

Its broader role is:

> **to metabolize lived experience into governed persistent character-state updates.**

### Automatic write authority

For the new personality-state domains, target write authority is:

```text
SELF        <- SLP automatic update after validation
REL         <- SLP automatic update after validation
OTHER MODEL <- SLP automatic update after validation
GOAL        <- SLP automatic update after validation
```

Human approval is not a normal gate for these ordinary updates.

Human inspection, correction, Forget/Restore-equivalent governance where applicable, and debugging remain possible.

Automatic does not mean uncontrolled.

The target update path is:

```text
Experience
   |
Evidence / governed input
   |
SLP interpretation
   |
Candidate Delta
   |
validation / grounding / provenance / scope checks
   |
automatic commit to owning state
```

This new authority does **not** retroactively make current Held or high-impact source-policy operations auto-apply.

### Different update speeds

Different states evolve at intentionally different rates:

```text
SOUL   immutable to autonomous runtime evolution
SELF   slow
REL    medium
GOAL   fast
MEM    continuous under its lifecycle
EMO    immediate / short-term
SCN    session-scale
```

One unusual turn must not redefine SELF.

One event may slightly affect REL.

An explicit prospective intention may create a GOAL immediately.

## Cognitive Substrate

The active LLM is represented as a cognitive substrate rather than as character identity.

Conceptual metadata may look like:

```yaml
cognitive_substrate:
  provider: local
  model: qwen-9b
  capabilities:
    reasoning: medium
    context: medium
    vision: false
```

Exact provider/model metadata is implementation detail.

The important invariant is that cognitive capability can change while persistent character identity continues.

This intentionally permits "Algernon-like" experiments:

```text
same SOUL
same autobiographical history
same relationships
different cognitive substrate
        |
different depth of world/self interpretation
```

The character may therefore understand the same memories differently under a more capable model without becoming a newly created character.

## Reflective / Self-Model Distillation

RelayLM adopts **Self-Model Distillation**, also called **Reflective Distillation**, as a target mechanism.

Its purpose is not to distill neural weights.

Its purpose is:

> **to distill higher-order self-understanding produced by a more capable model into portable, grounded SELF state that smaller models can later use.**

Target flow:

```text
SOUL
+ current SELF
+ REL
+ GOAL
+ important MEM
+ recent changes
       |
large-model reflection
       |
Candidate Self Model Delta
       |
grounding / contradiction checks
       |
SLP-governed adoption
       |
updated SELF
       |
return to local 9B
```

The large model does not gain direct authority over SOUL.

It does not directly write SELF either; its output is candidate interpretation consumed through the owning SLP validation/write boundary.

This allows:

```text
local 9B daily life
       |
large-model deep reflection
       |
richer SELF
       |
local 9B again
```

The cognitive substrate may become less capable later while the self-understanding learned during the higher-capability period remains part of the character's development.

Automatic scheduled reflection is post-MVP. MVP requires explicit invocation only.

## Psychological-model correspondence

RelayLM does not claim that human psychology proves this architecture, nor does this architecture imply consciousness or human-equivalent personhood.

The design is nevertheless structurally compatible with several established psychological ideas:

- **Self-Memory System**: autobiographical knowledge interacts with a current working self and goals;
- **self-schema**: accumulated experience forms self-relevant cognitive generalizations that shape later interpretation;
- **narrative identity**: experience is not only stored but integrated into evolving self-meaning;
- **self-discrepancy**: normative/ideal representations can differ from perceived current self;
- **relationship / attachment representations**: models of self, other, and relationship influence social interpretation;
- **mentalizing / theory of mind**: other persons are represented through uncertain beliefs about their internal state;
- **appraisal theories of emotion**: affect arises from interpretation of events relative to goals, relationships, and context;
- **goal-directed control / working-self models**: active goals help determine attention, retrieval, and action.

The mapping is conceptual and engineering-oriented, not a clinical or neuroscientific equivalence.

## Presentation Mapper

RelayLM separates internal character meaning from external rendering technology.

The Presentation Mapper consumes relevant character state such as:

```text
STYLE
SELF
REL
GOAL
EMO
SCN
```

and emits provider-neutral presentation intent:

```text
text rendition
voice style
avatar expression
gesture hint
scene hint
UI presentation
```

Adapters translate those semantics into concrete engines.

Example:

```text
RelayLM meaning:
  slightly embarrassed, warm, restrained

Irodori adapter:
  voice-performance caption

Avatar adapter:
  expression = shy_soft
```

This keeps character semantics independent from any one TTS or avatar engine.

## Frontend integration

RelayLM should not invent a large proprietary frontend transport protocol.

Preferred direction:

```text
conversation/state events -> AG-UI profile where it fits
ordinary APIs/assets      -> HTTPS
streaming where needed    -> SSE / web-standard mechanisms
browser audio/rendering   -> Web platform APIs
tools/resources           -> MCP
full-duplex real-time     -> WebRTC only when required
dynamic generated UI      -> A2UI only if later justified
agent-to-agent            -> A2A only if later justified
```

AG-UI is an open frontend/agent event protocol candidate, not an excuse to duplicate transport semantics.

RelayLM-specific work should be limited to a **RelayLM Character State Schema / profile**, not a new transport family.

MVP does not require WebRTC.

## RelayLM Experience

The first-party experience should be:

- mobile-first;
- browser-based;
- installable as a PWA;
- character-first rather than configuration-first;
- usable on a smartphone while RelayLM runs on another machine/server.

The normal screen should feel like meeting a character, not operating an AI control panel.

Advanced settings belong in separate management surfaces such as:

- SOUL Lab;
- Memory Inspector;
- Character Studio.

## AITuber OnAir relationship

RelayLM should not compete by reimplementing the complete AITuber frontend stack.

Preferred strategy:

> **Reuse selected AITuber OnAir packages/renderer technology where beneficial, while keeping a RelayLM-native UI shell and RelayLM as the only persistent character authority.**

When used with RelayLM:

```text
AITuber OnAir technology
  -> browser/avatar/audio/streaming capability

RelayLM
  -> SOUL/SELF/REL/GOAL/MEM/character continuity
```

AITuber OnAir's own persistent personality/memory features must not become a second authority for the same character.

A hard fork should be avoided when package-level reuse or thin adapters are sufficient.

## Avatar strategy

The runtime must not depend on a single avatar technology.

Define an abstract renderer boundary even when MVP implements only one renderer.

Conceptually:

```text
AvatarRenderer
├─ loadCharacter()
├─ setEmotion()
├─ setExpression()
├─ setSpeaking()
└─ pushAudio()
```

Potential implementations include:

- MotionPNG;
- PuruPuru;
- PNG;
- Live2D;
- VRM;
- future renderers.

### MVP renderer

Preferred initial renderer: **MotionPNG**.

MotionPNGTuber is primarily treated as an asset-generation/preparation pipeline or reference technology, not as a mandatory RelayLM runtime dependency.

## Voice strategy

RelayLM should not embed a TTS engine.

Use an adapter behind an OpenAI-compatible or similarly narrow provider boundary.

Preferred MVP voice engine: **Irodori-TTS v4**.

RelayLM owns:

- character voice identity metadata;
- presentation meaning;
- style mapping.

The TTS provider owns speech synthesis.

Conceptually:

```text
SOUL / SELF / REL / EMO / SCN
              |
      Presentation Mapper
              |
       voice-performance intent
              |
      Irodori-TTS v4 adapter
              |
       browser audio playback
```

The canonical displayed text and TTS rendition may differ when non-semantic performance markers are required for voice expression.

The provider remains replaceable.

## MVP input

MVP does not implement a custom STT stack.

Primary voice-input path:

```text
OS / IME dictation
       |
browser text field
       |
RelayLM text input
```

Examples include platform keyboard dictation such as Gboard or equivalent OS facilities.

This removes from MVP:

- microphone capture pipeline;
- VAD;
- streaming STT;
- WebRTC signaling;
- echo-cancellation control;
- turn detection;
- barge-in.

Dedicated push-to-talk can be added later through browser media APIs and an interchangeable STT provider.

## MVP lip-sync

Lip-sync should be derived in the browser from the audio actually played.

Conceptually:

```text
TTS audio
   |
   +--> speaker
   |
   +--> Web Audio analysis
           |
        envelope
           |
    mouth / speaking state
```

The server does not need to emit per-frame mouth-state events for MVP.

The played TTS audio is the lip-sync source of truth.

## Session model

Character identity is shared; session state is not.

Conceptually:

```text
                  Character
                     |
       shared SOUL / SELF / MEM / REL
             +-------+-------+
             |       |       |
           Mobile    PC    Stream
            SCN      SCN      SCN
```

Persistent or cross-session:

- SOUL;
- SELF;
- REL;
- MEM;
- long-lived GOAL/commitments.

Session-specific:

- SCN;
- transient conversation state;
- local presentation state;
- device UI state.

## Character Workspace direction

The long-term Character Workspace should be able to represent character mind plus presentation configuration without making all items the same authority class.

Conceptually:

```text
character/
├─ SOUL.md
├─ STYLE.md
├─ SELF/
├─ REL/
├─ MEM/
├─ GOAL/
├─ SCN/
├─ EMO/
├─ avatar/
│  └─ manifest.json
└─ voice/
   └─ manifest.yaml
```

This is target shape only.

It does not change the exact current Character Workspace parser/source-tree contract.

A later contract must decide whether SELF/GOAL are human-readable durable source pages, generated governed state, or a split source/projection model.

Large media/model binaries may be referenced rather than embedded.

## Write authority matrix

| State | Automatic writer | Human role | Target cadence |
|---|---|---|---|
| SOUL | none | explicit re-authoring/governance only | immutable to autonomous evolution |
| SELF | SLP | inspect/correct | slow |
| REL | SLP | inspect/correct | medium |
| OTHER MODEL | SLP | inspect/correct | medium/fast |
| GOAL | SLP | inspect/correct | fast |
| MEM | existing SLP/lifecycle owners | Correct/Forget/Restore/governance | continuous |
| EMO | runtime / SLP under RelayEMO authority | optional inspection | immediate |
| SCN | session/runtime under RelaySCN authority | optional inspection | session |
| Working Self | runtime derivation | none | per turn |

## MVP required behavior

MVP must prove the character architecture, not merely render a page.

Required end-to-end behavior:

1. load a Character Workspace;
2. load SOUL without granting autonomous mutation authority;
3. persist SELF;
4. persist REL with a minimal OTHER MODEL;
5. persist GOAL/commitments/prospective intentions;
6. use the existing MEM architecture;
7. maintain SCN and EMO;
8. build a Working Self projection each turn;
9. run a 9B-class local model for ordinary conversation;
10. automatically update SELF/REL/GOAL through SLP after validation;
11. apply Presentation Mapper output;
12. run a mobile-first PWA;
13. accept text and OS/IME dictation;
14. render one avatar type, preferably MotionPNG;
15. speak through an Irodori-TTS v4 adapter;
16. lip-sync in the browser from played TTS audio;
17. preserve SELF/REL/MEM/GOAL continuity across restart;
18. allow explicit large-model Reflection;
19. produce a Candidate Self Model Delta;
20. validate/adopt that delta through SLP;
21. return to the local 9B and demonstrate retained richer self-understanding.

The strongest MVP proof is:

```text
local 9B daily conversation
        |
explicit large-model reflection
        |
SLP-validated SELF development
        |
return to local 9B
        |
same SOUL, richer self-understanding
```

## Explicit MVP non-goals

MVP does not require:

- custom STT;
- VAD;
- full-duplex voice;
- WebRTC;
- automatic barge-in;
- custom authentication stack;
- YouTube/Twitch integration;
- OBS integration;
- custom Live2D runtime;
- custom VRM runtime;
- multiple completed avatar renderers;
- autonomous long-horizon planning;
- advanced recursive theory-of-mind;
- automatic scheduled reflective distillation;
- A2UI;
- A2A;
- SOMA / virtual embodiment.

These may be architecturally accommodated later.

## Recommended implementation order

### Phase 1 — Character core

Implement:

- SELF;
- GOAL;
- minimal OTHER MODEL;
- Working Self;
- Presentation Mapper;
- SLP automatic write-authority rules for SELF/REL/GOAL.

### Phase 2 — 9B end-to-end loop

Validate:

- local 9B conversation;
- context projection;
- persistence;
- SLP personality-state updates;
- identity continuity.

### Phase 3 — Character experience

Implement:

- mobile-first PWA;
- MotionPNG adapter;
- Irodori-TTS v4 adapter;
- browser-side lip-sync;
- minimal character-first UI.

### Phase 4 — Reflective distillation

Implement:

- explicit reflection operation;
- large-model deep reflection;
- Candidate Self Model Delta;
- grounding and contradiction checks;
- SLP-governed SELF update;
- return-to-9B validation.

## Current / target boundary

This page records an accepted **target architecture**, not current implementation.

It specifically does not:

- alter current Subjective MEM writer/cutover authority;
- weaken current Held governance;
- change RT-1D retirement behavior;
- make current Character Workspace parsers accept new SELF/GOAL paths;
- make current RelaySOUL patches automatic;
- claim that AG-UI, MotionPNG, Irodori-TTS v4, or AITuber OnAir packages are already repository dependencies;
- make UI/network/provider choices immutable architecture.

Current implementation truth remains [Project Status](../../PROJECT_STATUS.md).

Exact current subsystem contracts remain authoritative until superseded through their own governed implementation slices.

## Stable target invariants

- The LLM is a cognitive substrate, not the character.
- SOUL is the stable human-authored normative identity anchor.
- Autonomous runtime, SLP, and reflection do not mutate SOUL.
- Explicit human SOUL revision is re-authoring, not ordinary personality development.
- SELF is distinct from SOUL and may evolve.
- SOUL and SELF may legitimately disagree.
- REL is target-specific and does not redefine portable identity.
- OTHER MODEL remains uncertain and grounded.
- GOAL provides motivation, commitments, and prospection.
- SLP automatically updates SELF, REL, OTHER MODEL, and GOAL only after owning validation.
- Existing MEM lifecycle/governance remains separately authoritative.
- Working Self is a per-turn projection rather than a second durable authority.
- Changing cognitive substrate may change world/self interpretation without resetting character continuity.
- Reflective Distillation transfers self-understanding, not model weights.
- Large-model reflection never gains SOUL write authority.
- Presentation semantics remain independent from avatar/TTS providers.
- RelayLM avoids a large proprietary frontend protocol.
- First-party UX is mobile-first, browser/PWA, and character-first.
- AITuber OnAir or similar technology may be reused without becoming character authority.
- MVP input may rely on OS/IME dictation.
- MVP voice/avatar engines remain replaceable adapters.

## Related architecture

- [Character Identity and Source Authority](identity-and-source-authority.md)
- [Character Workspace Architecture](../character-workspace/system.md)
- [Relationship State](../relationship/relationship-state.md)
- [Scene Model](../scene/scene-model.md)
- [Affect Modulation](../emotion/affect-modulation.md)
- [Memory System](../memory/system.md)
- [Context Assembly](../context/context-assembly.md)
- [Pipeline Responsibilities](../pipeline-responsibilities.md)
- [RelayMEM / RelaySLP Current / Target Boundary](../relaymem_slp_current_target.md)
