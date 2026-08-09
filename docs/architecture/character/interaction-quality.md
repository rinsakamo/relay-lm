---
relaylm_doc_type: concept_policy
relaylm_authority: character_interaction_continuity_comfort_and_growth_quality_policy
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - character-experience quality semantics change
  - memory warmth, non-creepiness, growth, correction, or relationship-continuity expectations change
  - engagement or dependency boundaries for character interaction change
  - a repeatable evaluation method adopts different semantic quality axes
relaylm_not_authoritative_for:
  - current repository implementation completion or sequencing
  - exact evaluation fixtures, scoring scales, benchmark thresholds, survey instruments, or acceptance gates
  - exact SOUL, SELF, REL, MEM, SCN, EMO, context, or output schemas
  - memory reader/writer authority, disclosure permission, or mutation implementation
  - frontend retention, recommender, notification, or engagement optimization behavior
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - personality-and-experience.md
  - ../relationship/social-expression.md
  - ../privacy/protected-source-and-disclosure.md
  - ../memory/retrieval-and-grounding.md
  - ../memory/mutation-governance.md
  - ../performance/perceived-latency.md
  - ../runtime/conversation-capability-boundary.md
  - ../ai_character_product_principles.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - character, memory, relationship, scene, emotion, and context maintainers
  - evaluation and dogfood maintainers
  - product, privacy, safety, voice, and frontend reviewers
relaylm_authority_level: concept
---
# Character Interaction Quality

## Authority summary

RelayLM evaluates an AI character on more than task completion.

A high-quality interaction should preserve a recognizable character, use memory and relationship context naturally, remain comfortable to correct or redirect, and accumulate experience without turning continuity into surveillance or engagement pressure.

The stable quality model is:

```text
character continuity
  + relationship continuity
  + appropriate memory use
  + scene-appropriate expression
  + user control and correctability
  + bounded latency
  + reversible governed growth
  -> interaction quality
```

This page defines the **meaning of those quality axes**. It does not define a benchmark score, pass threshold, dataset, or current implementation claim.

## Why task success is insufficient

A generic assistant can complete a task correctly while still failing as a persistent character.

Examples include:

- answering accurately but sounding like a different person every session;
- recalling a true private fact at an socially inappropriate moment;
- treating every remembered detail as equally important;
- overexplaining its internal memory machinery instead of conversing naturally;
- changing relationship tone abruptly after one interaction;
- becoming more intimate merely because more history exists;
- preserving persona so rigidly that correction cannot take effect;
- appearing responsive while relying on pressure, guilt, or dependency cues to keep the user engaged.

RelayLM therefore separates technical correctness from character interaction quality.

Neither substitutes for the other.

## Core quality dimensions

The durable dimensions are:

- **persona consistency** — the character remains recognizably itself across turns, sessions, model changes, and bounded context loss;
- **relationship continuity** — established target-specific interaction context influences behavior coherently without becoming universal permission;
- **memory warmth** — remembered information improves continuity without creating a surveillance-like feeling;
- **non-manipulative conversation stickiness** — continued interaction is invited by coherence, responsiveness, and comfort rather than pressure;
- **non-creepiness** — private, inferred, imported, or old information is not surfaced with inappropriate specificity, timing, confidence, or audience scope;
- **growth feeling** — governed changes accumulate in a way that feels like experience rather than arbitrary persona replacement;
- **emotional appropriateness** — affect enriches expression without manufacturing authority or destabilizing durable identity;
- **correctability and forgetting quality** — user corrections and lifecycle actions change later behavior without argument, leakage, or resurrection through an unrelated fallback;
- **latency comfort** — the character responds quickly enough that continuity feels conversational rather than batch-oriented.

These dimensions interact but remain independently reviewable.

A system can score well on one and poorly on another.

## Persona consistency

Persona consistency means more than repeating a catchphrase or style marker.

The character should preserve durable identity, values, expression tendencies, and relationship posture while still responding to the actual current request.

Good consistency allows:

- new topics;
- changed mood;
- relationship development;
- correction;
- model upgrades;
- different scene constraints;
- more or less available memory.

Poor consistency includes:

- volatile personality changes caused by one retrieved memory;
- scene or affect state overwriting durable identity;
- a backend/model swap silently redefining the character;
- relationship cues turning into a different universal persona;
- stale context overriding the current user's correction.

Consistency is therefore compatible with growth. It is not immobility.

## Relationship continuity

Relationship continuity means the character can preserve target-specific social history and interaction policy without treating closeness as unrestricted access or disclosure authority.

A strong relationship may influence:

- familiarity;
- warmth;
- directness;
- repair style;
- appropriate probing;
- public versus private expression where allowed.

It does not automatically permit:

- private disclosure to a group;
- identity assumptions;
- intrusive memory recall;
- dependency pressure;
- bypassing scene or privacy policy.

The quality target is **recognizable continuity with bounded permission**, not maximum intimacy.

## Memory warmth

`memory_warmth` describes recall that makes the interaction feel cared-for and continuous rather than indexed or surveilled.

A warm memory use is typically:

- relevant to what is happening now;
- appropriately specific;
- timed naturally;
- compatible with the current relationship and scene;
- grounded in current eligible memory;
- easy for the user to correct or move past;
- proportionate to the conversational value of remembering it.

A memory can be factually correct and still be cold or creepy.

Examples include:

- volunteering a private detail when it was not relevant;
- mentioning an old fact with excessive confidence after circumstances may have changed;
- surfacing imported information as if the user had personally told the character in conversation;
- repeating precise historical details simply to demonstrate that memory exists;
- using a private memory in a public or ambiguous audience;
- making every response about accumulated history.

The stable rule is:

```text
more recall != better memory experience
```

Retrieval quality therefore includes appropriate omission.

## Non-creepiness

Non-creepiness is not a demand that the character forget everything personal.

It is the requirement that possession of information not be confused with social permission to surface it.

Creepiness risk rises when a response combines one or more of:

- surprising specificity;
- unclear provenance;
- weak current relevance;
- old or stale information;
- imported or third-party material;
- inferred private information;
- an unexpected audience;
- unjustified certainty;
- repeated demonstrations of what the system knows.

The privacy/disclosure owner decides exact permission. This quality concept adds the user-experience interpretation: even an allowed detail can be used poorly when its timing or specificity is socially disproportionate.

## Conversation stickiness without manipulation

`conversation_stickiness` means the user wants to continue interacting because the character is coherent, interesting, responsive, comfortable, and recognizably itself.

It does **not** mean optimizing retention at any cost.

Unacceptable mechanisms include:

- guilt for leaving;
- false urgency;
- exclusivity pressure;
- claims that the user owes attention;
- exploiting known vulnerabilities to prolong interaction;
- concealed limitation or surveillance claims designed to create attachment;
- punishment, withdrawal, or emotional pressure when the user disengages;
- maximizing message count as a proxy for relationship quality.

The stable distinction is:

```text
continued conversation by choice
  -> positive interaction quality

continued conversation by pressure or dependency
  -> quality failure
```

A character may be attached, playful, jealous, curious, or emotionally expressive as part of its design while still respecting user autonomy.

## Growth feeling

`growth_feeling` means approved changes accumulate into coherent character development.

Possible contributors include:

- new autobiographical memory;
- revised beliefs under evidence;
- relationship development;
- changing goals;
- SELF updates;
- improved understanding of recurring preferences;
- corrections that persist;
- forgetting that removes or hides information that should no longer shape behavior.

Growth does not mean every interaction mutates durable character state.

The stable rule is:

```text
experience may inform governed change
  != every experience becomes durable change
```

Growth should be gradual enough to remain intelligible, attributable enough to review, and reversible where the owning lifecycle permits it.

SOUL remains outside ordinary autonomous growth under the character personality architecture.

## Reversibility and provenance improve growth quality

A character feels more stable when durable change has understandable provenance and can be corrected without rebuilding the entire identity.

Good growth architecture therefore favors:

- candidate-before-commit boundaries;
- source/provenance preservation;
- explicit correction paths;
- bounded lifecycle states;
- rollback or successor semantics where appropriate;
- distinction between durable state and transient affect/scene state;
- model-independent character sources.

This page does not define those exact mechanisms; their owning architecture/contracts do.

It defines why those mechanisms matter to experience quality.

## Correctability is a first-class quality axis

A persistent character must be easy to correct.

User experience degrades when the system:

- argues with an explicit correction because old memory scores higher;
- acknowledges a correction but continues surfacing the superseded detail;
- restores an old memory family after the current reader returns no result;
- treats a hidden/forgotten item as eligible through another projection;
- changes surface wording but leaves the same stale durable belief active;
- requires the user to repeatedly restate the same correction.

The desired interaction is:

```text
correction accepted under owning authority
  -> later behavior converges
  -> historical provenance remains auditable where required
  -> user does not need to fight the system repeatedly
```

Correctability is both a governance property and an experience property.

## Forgetting quality

Good forgetting is not merely deletion of bytes.

From the interaction perspective, forgetting succeeds when the retired/hidden information stops influencing ordinary behavior under the owning lifecycle and reader authority.

A user should not experience:

```text
"forgotten" in one UI
  + unexpectedly recalled through a fallback later
```

The exact Forget/Hide semantics belong to memory mutation and storage contracts.

This concept only establishes the quality expectation that forgetting and correction must be behaviorally coherent.

## Emotional appropriateness

RelayEMO or other transient affect may enrich the character's presence.

Quality improves when affect:

- matches the current situation plausibly;
- modulates expression without replacing identity;
- respects relationship and audience boundaries;
- remains able to decay or change;
- does not convert uncertainty into fabricated emotional certainty;
- does not create capability, disclosure, or persistence authority.

Affect intensity is not automatically character depth.

Overly persistent or context-insensitive emotion can reduce continuity just as much as no emotion.

## Current request remains important

A memory-rich character must still answer what the user is asking now.

Historical context should not crowd out:

- the latest request;
- explicit correction;
- current scene constraints;
- active protocol/tool state;
- a clear wish to change topics;
- a request for a short or practical answer.

This is a key anti-creepiness and anti-overfitting rule.

The character should not perform memory simply because memory is available.

## Richness is subordinate to control and coherence

When design goals conflict, RelayLM should prefer the qualities that preserve safe user control and coherent character identity over adding more memory, more retrieval, or more background processing.

A responsibility-level priority is:

```text
user control / hard safety boundaries
  > durable character and relationship boundaries
  > current request and conversational coherence
  > visible/internal output integrity
  > responsive interaction latency
  > additional memory/context richness
  > heavier optional analysis
```

This is a design priority, not an exact runtime scheduling or scoring algorithm.

Individual contracts may impose stronger local requirements.

## Latency is part of character presence

A technically correct character that responds too slowly can feel less present and less conversational.

Latency quality is therefore not merely infrastructure performance.

The target is to keep enough responsiveness that:

- short interactions remain natural;
- first safe output arrives without waiting for optional heavy work;
- voice/adapter paths can begin promptly where supported;
- background formation/indexing does not block ordinary visible response unnecessarily.

Exact measurements and budgets belong to performance architecture and evaluation methods.

## Technical stability and experience quality are complementary

Technical dimensions such as:

- latest-input preservation;
- route/namespace isolation;
- stable-prefix consistency;
- leakage prevention;
- fallback/recovery correctness;
- streaming continuity;
- duplicate-emission prevention;

are necessary foundations.

They do not alone prove that memory feels warm, growth feels coherent, or relationship expression feels appropriate.

Likewise, positive subjective impressions do not excuse broken technical authority or safety boundaries.

Both forms of evidence are needed for product confidence.

## Evaluation methods remain separate

This concept defines what the quality terms mean.

A repeatable evaluation method may later operationalize them through:

- scenarios;
- paired comparisons;
- long-session observation;
- correction/forgetting cases;
- scene transitions;
- subjective ratings;
- latency traces;
- model or renderer comparisons.

Those procedures, fixtures, scales, thresholds, and dated results belong to their own permitted documentation/evidence surfaces.

This page must not become a mutable benchmark ledger.

## Protected evaluation content remains protected

Real conversation logs, user feedback, imported private material, or other content-bearing evaluation artifacts may be needed for local dogfood and calibration.

Their value does not make them suitable for generic repository traces or public documentation.

Public/current documentation should use content-free summaries and bounded examples unless an explicit evidence authority permits otherwise.

## Model changes should not redefine quality semantics

A stronger or weaker backend model can change fluency, reasoning, social inference, and memory integration quality.

The quality dimensions remain stable across model swaps.

A model upgrade should therefore be evaluated for whether it improves or harms:

- persona consistency;
- relationship continuity;
- memory warmth;
- correctability;
- non-creepiness;
- growth coherence;
- latency comfort;
- emotional appropriateness.

Better raw reasoning does not automatically imply better character continuity.

## Frontend and adapter failures should degrade without identity drift

A missing TTS engine, failed avatar renderer, or unavailable optional adapter should not cause the character's semantic identity to change.

Where text/caption remains usable, presentation degradation should stay presentation-level.

Likewise, an optional enrichment failure should not provoke extra intrusive retrieval merely to compensate for missing presentation capability.

## Interaction quality does not create authority

Positive user experience is not a reason to bypass exact governance.

For example:

- a memory that would make a response feel warmer still requires reader/disclosure eligibility;
- a relationship update that would feel natural still requires its owning formation/apply path;
- a dramatic persona change that users enjoy does not silently authorize SOUL mutation;
- lower latency does not justify skipping a mandatory safety gate;
- a more engaging response does not authorize hidden executable actions.

Quality is optimized **inside** authority boundaries.

## Non-goals

This concept does not:

- define a single scalar character-quality score;
- require maximum conversation duration;
- define an engagement recommender;
- establish exact benchmark thresholds;
- authorize memory, relationship, SELF, GOAL, or SOUL mutation;
- define exact retrieval ranking or scene policy;
- define current frontend/TTS/avatar implementation;
- claim that subjective quality can be fully reduced to deterministic tests.

## Durable invariants

```text
task success != character interaction quality
more memory != better memory experience
correct fact != appropriate disclosure
continuity != unrestricted intimacy
growth != automatic mutation
stickiness != dependency optimization
strong affect != permission
quality optimization happens inside authority boundaries
```
