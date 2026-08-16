---
relaylm_doc_type: concept_policy
relaylm_authority: observation_shared_assessment_character_belief_and_utterance_separation
relaylm_status: current
relaylm_volatility: low
relaylm_owner: memory
relaylm_update_trigger:
  - observation or Protected Source Evidence authority changes
  - Shared Assessment or Subjective formation authority changes
  - character-conditioned belief, relationship, scene, affect, or disclosure boundaries change
  - SOUL Lab observation ownership changes
relaylm_not_authoritative_for:
  - exact Evidence, Shared Assessment, Subjective MEM, belief, relation, affect, or observation schemas
  - exact belief-calibration, inference, ranking, probing, or response-generation algorithms
  - current implementation completion or project sequencing
  - exact SOUL Lab API/UI/storage behavior
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/character_conditioned_belief_model.md
  - ../../adr/0003-subjective-mem-direction.md
relaylm_related_authority:
  - system.md
  - formation.md
  - retrieval-and-grounding.md
  - scene-memory-scope.md
  - ../scene/scene-model.md
  - ../../evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md
relaylm_related_contracts:
  - ../../contracts/shared-assessment-subjective-mem.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Evidence and memory formation maintainers
  - character-belief, relationship, scene, and affect maintainers
  - privacy, disclosure, evaluation, and SOUL Lab observation reviewers
relaylm_authority_level: concept
---
# Observation and Character-Conditioned Belief

## Authority summary

RelayLM separates what was observed, what shared evidence supports, what one character provisionally believes, what action the character feels inclined to take, what the current relationship/scene/audience permits, and what the character actually says.

These are distinct authority stages:

```text
Protected Source Evidence / observation
  -> character-independent Shared Assessment
  -> character-conditioned provisional belief
  -> probe or action impulse
  -> relationship + scene + audience + disclosure permission
  -> actual utterance
```

No downstream stage rewrites the authority of an earlier stage merely because it is more expressive, confident, emotionally salient, or visible to the user.

## Why the separation matters

A conversational system does not observe external truth directly. It observes events, utterances, tool results, files, and other admitted evidence with provenance.

A statement such as “I love autumn leaves” may be sincere, contextual, joking, role-played, outdated, uncertain, or contradicted later. Treating the surface sentence as timeless fact collapses several different questions:

- What exactly was observed?
- Who said or produced it?
- What does the evidence support now?
- How certain or unresolved is that assessment?
- What does this character make of it?
- Is the character allowed to reveal or act on that interpretation here?
- What did the character finally say?

The architecture keeps these questions separate so characterfulness does not corrupt provenance and privacy does not require flattening every character into the same behavior.

## Observation / Protected Source Evidence

Observation is the provenance-preserving evidence layer.

Stable observation responsibilities include, as applicable under the owning contract:

- source/speaker/origin;
- subject and event identity;
- time or temporal relationship;
- provenance and authority class;
- speech-act or source interpretation;
- audience or disclosure scope;
- correction, retraction, successor, or quarantine lineage.

Character components do not rewrite admitted observation content or provenance.

If later evidence changes the interpretation, the system records governed successor/retraction/assessment state rather than editing history to make the original observation agree with a later belief.

Observation is evidence about what occurred or was presented, not an assertion that every proposition contained in the observation is externally true.

## Shared Assessment

Shared Assessment is character-independent interpretation over governed Evidence.

It may represent:

- support;
- contradiction;
- refinement;
- temporal change;
- uncertainty;
- unresolved state;
- competing hypotheses;
- bounded relation between current and historical evidence.

Shared Assessment does not acquire character identity simply because a particular character later consumes it.

SOUL, scene, relationship, or current affect may not rewrite what the Shared Assessment says the evidence supports.

A Shared Assessment may remain uncertain or unresolved. The architecture does not force a single timeless fact merely to simplify storage or prompting.

## Character-conditioned provisional belief

Only after a governance- and schema-valid Shared Assessment exists may an identified character condition subjective interpretation.

Character-conditioned belief may vary because of durable cognitive style, attention, values, relationship context, scene, or bounded affective influence.

A character may therefore:

- weight one supported interpretation more strongly than another;
- notice one aspect of an unresolved situation;
- remain skeptical despite another character being more trusting;
- form a tentative expectation;
- decide that more evidence is needed;
- interpret the same evidence differently without altering its provenance.

This belief is **provisional character state/interpretation**, not a license to rewrite shared evidence.

Character bias cannot:

- convert uncertainty into source fact;
- change the original speaker;
- invent missing provenance;
- turn assistant speculation into user-origin evidence;
- silently edit Shared Assessment;
- authorize group disclosure;
- mutate RelaySOUL or relationship files directly.

## Belief is not automatically a durable memory write

A character forming a provisional belief does not by itself authorize durable Subjective MEM formation.

Durable memory still follows the owning formation contract:

```text
governed Evidence
  -> valid Shared Assessment
  -> character-scoped Subjective formation decision
  -> commit / hold / abstain under storage and policy authority
```

The formation system may choose to preserve a supported subjective interpretation, retain only Evidence, leave the matter unresolved, or abstain.

A transient thought, one-turn hypothesis, emotional reaction, or probe impulse is not durable memory merely because it affected the response.

## Subjective MEM and provisional belief

Subjective MEM is the durable character-scoped memory authority accepted by the memory architecture. A provisional belief is a reasoning-stage concept.

They overlap only when the formation authority decides that a character-scoped interpretation is sufficiently justified and policy-valid to become durable Subjective memory.

Stable rules are:

- provisional belief is not a second durable memory store;
- Subjective MEM grounded content remains bound to Shared Assessment;
- subjective meaning may reflect the identified character without changing evidence support;
- later correction or contradictory evidence is handled through governed assessment/memory lifecycle rather than silent belief overwrite;
- retrieval of Subjective MEM does not imply the belief is externally certain.

## Probe and action impulse

Character belief may create an impulse to probe, clarify, help, withhold, challenge, reassure, or take another bounded conversational action.

Impulse is not output authority.

Before expression, the system still applies relationship, scene, audience, privacy, safety, and disclosure constraints.

This distinction supports natural characters that can feel curiosity, suspicion, warmth, protectiveness, or hesitation without leaking private content or escalating every internal tendency into speech.

## Relationship boundary

RelayREL may affect applicability, trust calibration, salience, action comfort, and disclosure for target-scoped reasoning.

Strong relationship does not imply permission to disclose private content.

Unknown or conflicting participant identity cannot become relationship-scoped evidence or belief authority by guesswork.

Character belief does not directly mutate durable relationship state. Relationship changes require their own governed evidence and authority.

## Scene and audience boundary

RelaySCN may constrain which interpretation is relevant now, what audience is present, what temporary role the character performs, and what disclosure or persistence policy applies.

Scene changes what is appropriate to notice or say; it does not rewrite observation or Shared Assessment.

A roleplay scene may produce a different expression or provisional stance while the evidence layer remains unchanged.

Scene end does not automatically delete, confirm, or invalidate a belief or durable memory.

[Scene-Aware Memory Scope](scene-memory-scope.md) owns the cross-cutting rule that scene may narrow already-authorized memory use without creating memory authority.

## Affect boundary

RelayEMO may supply transient typed affect or bounded salience evidence.

Affective gain may vary by relationship and may influence attention, action impulse, expression intensity, or the character's provisional weighting.

It cannot by itself:

- prove a user fact;
- increase source confidence;
- establish durable Subjective meaning;
- authorize memory persistence;
- authorize SOUL mutation;
- override privacy or disclosure rules.

Strong feeling is not strong evidence.

## Disclosure permission

Knowing, believing, or remembering something does not imply permission to say it.

The final disclosure decision may depend on:

- the evidence's provenance and audience scope;
- current relationship identity and policy;
- current scene and participants;
- privacy/disclosure rules;
- safety boundaries;
- whether the content is public, private, inferred, uncertain, or unsupported.

In multi-user scenes, conservative content boundaries may coexist with bounded non-content relationship expression such as warmth, timing, or already-public familiarity.

No character belief, intimacy score, scene match, retrieval score, or affect signal bypasses disclosure authority.

## Utterance

The final utterance is an action/output, not a retroactive source of truth about earlier internal stages.

If the character says “I think you may prefer autumn trips,” that sentence does not automatically become user-origin Evidence or prove the underlying proposition.

Assistant-origin statements retain assistant provenance unless a later governed evidence process admits some new evidence for another reason.

Stable rules are:

- utterance does not rewrite observation;
- utterance does not automatically persist character belief;
- utterance does not convert an inference into direct support;
- later user confirmation may become new Evidence through the Evidence authority;
- a later correction may update assessment/memory through governed successor paths.

## SOUL boundary

RelaySOUL supplies durable character identity, values, cognitive priors, and repair style under its own authority.

SOUL may condition subjective interpretation only after character-independent assessment exists.

Belief or memory does not directly rewrite SOUL. Repeated compatible experience may eventually produce a separately governed SOUL proposal if such a contract permits it, but that is not implied by ordinary belief formation.

Character adaptation must not erase durable identity or optimize dependency, guilt, exclusivity, or coerced engagement.

## Observation UI is not evidence authority

SOUL Lab Observation is a read-only visibility surface over bounded runtime evidence.

Historical Phase I-2 established the important rule that observation receipts are secondary read-only evidence only. They do not repair queues, recreate protected source, publish memory, change retrieval, or drive retry/terminal transitions.

A browser view, projection, stale response, cached observation, or UI label does not become canonical Evidence, memory, belief, or lifecycle authority.

Current SOUL Lab implementation may expose newer bounded observation capabilities; exact current behavior remains owned by its current runtime/UI architecture and Project Status.

## Current implementation versus accepted concept

This concept is current as an accepted architectural boundary, not a claim that every stage has one fully implemented production schema or persistent runtime artifact.

Current RelayLM already contains bounded Evidence, memory, scene, relationship, affect, retrieval, and observation implementations. The complete target chain from governed observation through shared assessment and fully explicit character-belief reasoning may remain partially implemented or represented implicitly in some paths.

Project Status remains the authority for what is implemented now.

## Evaluation implications

Character quality should not be evaluated only by factual answer accuracy.

Useful evaluation dimensions include:

- provenance preservation;
- calibration under uncertainty;
- contradiction handling;
- willingness to abstain;
- comfortable probing rather than forced certainty;
- relationship-aware but privacy-safe expression;
- scene-aware disclosure;
- repair after mismatch;
- separation of internal characterfulness from shared evidence corruption.

A system that produces more confident character opinions by rewriting evidence is worse, not better, under this architecture.

## Failure model

```text
ambiguous / conflicting observation
  -> preserve provenance and uncertainty
  -> do not force shared fact

valid Shared Assessment but character-specific ambiguity
  -> provisional belief may differ by character
  -> do not rewrite Shared Assessment

strong belief but disclosure not allowed
  -> withhold or reframe under disclosure policy
  -> do not leak because belief is strong

strong affect but weak evidence
  -> expression/salience may change within bounds
  -> evidence confidence does not increase

assistant utterance contains inference
  -> retain assistant provenance
  -> do not backfill user-origin fact

stale Observation UI projection
  -> discard/fail closed under UI/runtime rules
  -> do not alter canonical state
```

## Stable invariants

- Observation/Protected Source Evidence preserves origin and provenance and is not rewritten by character interpretation.
- Shared Assessment is character-independent and may remain uncertain, unresolved, or multi-hypothesis.
- Character-conditioned belief may differ by character without changing shared evidence authority.
- Provisional belief is not automatically a durable memory write.
- Subjective MEM grounded content remains bound to accepted Shared Assessment.
- Probe/action impulse is not output or mutation authority.
- Strong relationship does not imply disclosure permission.
- Scene and affect may condition relevance/expression but do not determine grounded truth.
- Strong affect is not strong evidence.
- Utterance does not retroactively become user-origin observation or durable belief.
- SOUL conditions subjective interpretation but is not directly mutated by belief or memory.
- Observation receipts/UI projections are secondary read-only visibility, not canonical authority.
- Privacy/disclosure remains a separate gate between belief/knowledge and expression.

## Non-goals

This concept does not define:

- exact Evidence, Shared Assessment, belief, or memory schemas;
- a specific belief-calibration model or confidence scale;
- automatic durable storage for every provisional belief;
- relationship or SOUL mutation;
- exact multi-user privacy implementation;
- exact SOUL Lab API/UI behavior;
- a prompt format or response-generation algorithm;
- project-level implementation sequencing.

## Related architecture and decisions

- [ADR: Character-conditioned belief without rewriting observation](../../adr/character_conditioned_belief_model.md)
- [ADR 0003: Subjective MEM direction](../../adr/0003-subjective-mem-direction.md)
- [Memory Subsystem Architecture](system.md)
- [Subjective Memory Formation](formation.md)
- [Scene-Aware Memory Scope](scene-memory-scope.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Historical Phase I-2 Real SOUL Lab Observation](../../evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md)
