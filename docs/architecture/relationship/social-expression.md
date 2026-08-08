---
relaylm_doc_type: concept_policy
relaylm_authority: relationship_scene_affect_audience_conditioned_social_expression
relaylm_status: current
relaylm_volatility: low
relaylm_owner: relationship
relaylm_update_trigger:
  - relationship-conditioned expression semantics change
  - RelaySCN audience/publicness or expression policy changes
  - RelayEMO modulation or return-side expression ownership changes
  - privacy/disclosure or multi-user expression boundaries change
  - mismatch-repair or probing policy changes
relaylm_not_authoritative_for:
  - exact relationship, scene, affect, memory, privacy, output, TTS, or avatar schemas
  - exact response-generation prompt, ranking, model, style, or rendering algorithm
  - exact relationship-update, persona-update, or memory-mutation implementation
  - current implementation completion or project sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/character_conditioned_belief_model.md
relaylm_related_authority:
  - relationship-state.md
  - ../emotion/affect-modulation.md
  - ../scene/scene-model.md
  - ../privacy/protected-source-and-disclosure.md
  - ../memory/observation-and-character-belief.md
  - ../memory/scene-memory-scope.md
  - ../character_belief_relationship_dynamics_design.md
  - ../safe_soul_scene_ctx_compile_chain.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - relationship, scene, emotion, and response maintainers
  - privacy, multi-user, UI, voice, and avatar integration reviewers
  - character-quality and safety evaluation maintainers
relaylm_authority_level: concept
---
# Social Expression

## Authority summary

Social expression is the bounded realization of character style after belief, relationship, scene, affect, audience, privacy, and output constraints have been resolved.

It answers:

```text
Given what the character currently believes or wants to express,
what form of expression is appropriate here and now?
```

It does not answer what is true, what memory may be read or written, who the relationship target is, what the current scene is, or which protected information may be disclosed.

The stable rule is:

```text
belief / impulse
  + relationship-specific permission
  + current scene and audience
  + affect modulation
  + privacy / disclosure gates
  + durable character/output policy
  -> bounded social expression
```

No positive expression signal overrides a stricter information, identity, safety, or disclosure gate.

## Expression is downstream of authority

A character may strongly believe something, feel an impulse to say it, and still suppress or reframe the expression.

The permanent separation is:

```text
belief
  -> probe / action impulse
  -> action proposal
  -> permission and disclosure evaluation
  -> actual utterance / non-verbal expression
```

This enables characters to remain recognizable without making every internal state visible.

Examples include:

- suspicious but polite;
- emotionally intense but externally controlled;
- bold in conversation but epistemically cautious;
- warm in private and restrained in public;
- playful with one target but formal in a group.

## Relationship-conditioned expression

RelayREL may influence how a character expresses itself with a governed target.

Bounded dimensions may include:

- directness;
- teasing/playfulness;
- warmth;
- familiarity;
- disagreement style;
- unsolicited probing;
- personal-memory reference comfort;
- vulnerability;
- repair style;
- public-familiarity permission;
- private-disclosure permission;
- relationship-conditioned affect gain.

These dimensions remain independent enough that one strong signal does not imply all others.

High trust does not imply permission for public intimacy. High attachment does not imply permission for intrusive probing. Familiarity does not imply private disclosure.

## Scene-conditioned expression

RelaySCN owns the active semantic situation and current audience policy.

Scene may narrow how relationship and affect are expressed:

- a public group scene may suppress intimate references;
- a formal-document scene may suppress teasing or decorative expression;
- a safety-sensitive scene may require clarity over playfulness;
- a recovery scene may reduce nonessential expression;
- a roleplay scene may allow bounded stylistic variation without changing durable identity or privacy authority.

Scene changes expression appropriateness. It does not rewrite relationship state or character identity.

## Affect-conditioned expression

RelayEMO may modulate expression intensity, warmth, pacing, emphasis, display hints, TTS style hints, or avatar hints within the already-permitted range.

Affect does not create permission.

Conceptually:

```text
relationship permission
  + scene allowance
  + current affect pressure
  -> effective expression level
```

If relationship or scene policy says an action is not appropriate, strong affect does not open it.

If affect is uncertain or unavailable, expression degrades toward the approved durable style rather than inventing stronger emotion.

## Durable character identity remains upstream

RelaySOUL / STYLE / OUTPUT policy define durable character identity and ordinary voice.

Social expression adapts that identity to one relationship, scene, and affect state without replacing it.

Stable ordering is:

```text
durable character invariants
  > relationship adaptation
  > current scene and affect variation
```

Relationship learning and affect must not erase the character's durable boundaries or turn one successful interaction into a new persona.

## Information disclosure is separate from expression style

A warm tone and private information are different things.

Social expression may alter how an allowed message is delivered. It does not authorize protected content.

The privacy boundary remains:

```text
character knows or believes content
  != content may be disclosed

content may be disclosed
  != every style of disclosure is appropriate
```

A character can express warmth, concern, familiarity, or restraint without exposing the private fact that motivated the feeling.

## Multi-user social expression

A multi-user scene has three distinct layers:

```text
1. hard audience boundary
   protected information remains within allowed disclosure scope

2. shared expression boundary
   visible familiarity and personality remain acceptable to the group

3. bounded relationship leakage
   subtle relationship-specific social texture may remain
   without revealing protected information
```

A purely lowest-common-denominator personality can be safe but socially flat. The accepted model therefore allows bounded non-content leakage while preserving hard information boundaries.

## Bounded relationship leakage

The permanent invariant is:

> Relationship warmth may leak. Relationship-protected information may not.

Examples that may be acceptable when current policy permits:

- slightly faster acknowledgment of a familiar participant;
- warmer but non-exclusive tone;
- subtle familiarity already acceptable in the group;
- public-history topic selection;
- brief visible concern without revealing private reasons;
- ordinary repair style adapted to a known target.

Examples that remain prohibited without explicit disclosure permission:

- revealing private memories;
- implying a secret learned in another scene;
- using an intimate nickname where public-familiarity permission is absent;
- exposing inferred vulnerabilities;
- excluding other participants through inaccessible private context;
- treating one target's permission as permission from the whole audience.

## Probing is a social action, not a mandatory uncertainty resolver

A character may respond to uncertainty by asking, suggesting, teasing, waiting, reframing, or leaving the matter unresolved.

Probe choice may be influenced by:

- expected information value;
- durable curiosity style;
- relationship permission;
- current relevance;
- scene allowance;
- affect impulse;
- conversational cost.

Conversational cost includes leading the user, demanding self-analysis, interrupting the actual task, intimacy overreach, repeated uncomfortable topics, and group awkwardness.

RelayLM must not probe every uncertain belief merely because additional information could improve prediction.

## Response temperature is weak social evidence

Warmth, length, timing, elaboration, humor, or emotional language may inform interaction comfort and future policy.

They are weak evidence for factual propositions by themselves.

A short positive acknowledgment may reflect politeness or social accommodation. Social expression must not convert response warmth into a durable user fact.

If response temperature informs a future relationship-update candidate, that candidate remains subject to the relationship/Evidence authority rather than being applied synchronously.

## Mismatch and repair

Repair is part of character compatibility.

A character can be wrong without becoming characterless, provided it repairs within policy.

Bounded repair behavior may include:

- acknowledging mismatch;
- accepting correction without argument;
- briefly reframing;
- apologizing when overreach was material;
- avoiding excessive self-explanation;
- temporarily reducing probe pressure;
- changing current expression intensity;
- routing evidence for later belief/relationship update under its owning authority.

The system distinguishes:

```text
belief correction
relationship repair
public-boundary repair
persona revision
```

One mismatch normally does not authorize durable SOUL revision.

## Public-boundary repair

If social expression exceeds an audience or disclosure boundary, repair should restore the boundary rather than rationalize the leak.

Possible response behavior includes:

- stop further disclosure;
- acknowledge inappropriate familiarity where useful;
- move to a safer public formulation;
- reduce expression/probe pressure;
- preserve protected source provenance;
- leave any durable relationship or persona change to the appropriate out-of-band authority.

Repair does not delete or rewrite Evidence simply because the expression was inappropriate.

## Strong relationship is not permission

This concept reinforces the privacy and relationship invariants:

- strong trust is not private-disclosure authority;
- attachment is not group-disclosure authority;
- familiarity is not identity proof;
- affection is not permission for dependency pressure;
- a character's willingness to reveal is not proof the user wants disclosure;
- relationship-conditioned EMO gain is not a capability token.

Expression is composed from permissions; it does not manufacture them.

## Manipulation and dependency boundary

Relationship-sensitive expression must not optimize for dependency, guilt, exclusivity, pressure, or concealed influence.

Character traits such as jealousy, attachment, visible concern, or rejection sensitivity may influence ordinary fictional or conversational expression only within policy.

They do not authorize:

- demanding continued interaction;
- punishing disengagement;
- guilt-based retention language;
- claims that the user owes the character attention;
- concealed use of private vulnerabilities to increase engagement;
- isolation from other people or systems;
- escalating intimacy beyond governed relationship/audience permission.

Character distinctiveness is compatible with user autonomy.

## Expression and memory

Using a memory internally to guide expression does not grant permission to quote or expose that memory.

A selected memory may influence a safe high-level response while protected details remain omitted.

Expression outcomes do not mutate memory lifecycle:

- mentioning a memory does not Pin it;
- suppressing a memory does not Forget it;
- an awkward expression does not Correct it;
- repeated expression does not make it more true.

Any memory mutation follows Memory Mutation Governance independently.

## Expression and relationship updates

A successful or failed interaction can become governed Evidence for a later relationship candidate.

The ordinary response path does not synchronously rewrite `relationships/<target>.md` because a joke landed well, a user responded warmly, or a repair succeeded.

Durable relationship change remains out-of-band and evidence-backed.

## Expression and SOUL updates

Social expression may reveal that the current durable character style fits poorly or well, but output itself is not persona-update authority.

A future SOUL proposal may use governed evidence under a separate accepted workflow. Social expression does not directly edit portable character sources.

## Expression and output adapters

RelayEMO may emit engine-neutral display/TTS/avatar hints after safe output exists.

Social expression treats those hints as presentation surfaces beneath semantic/output authority.

Adapters may map or omit them without changing the meaning of the approved response.

A visual marker, voice style, or avatar motion must not leak private information that the text itself was not allowed to reveal.

## Content-free diagnostics

Default diagnostics for social expression remain content-free.

They may expose bounded classes such as:

- relationship-expression policy class;
- scene-expression gate;
- affect-modulation band;
- public/private/group scene class;
- probe permitted/suppressed;
- disclosure blocked/allowed class;
- repair mode class;
- display/TTS/avatar hint presence;
- reason IDs and counts.

They do not expose by default:

- relationship body text;
- private memories or protected Evidence;
- raw inferred beliefs;
- scene body/participant values;
- visible response text;
- private nicknames or relationship notes;
- affect candidate bodies;
- prompt fragments or internal rationale.

## Fail-closed behavior

When policy inputs disagree or are incomplete, social expression moves toward less risky expression rather than broader access.

```text
relationship permits familiarity
+ scene is public/restrictive
  -> use public-safe familiarity only

strong affect
+ probe permission unresolved
  -> suppress or soften probe

private motivation exists
+ disclosure blocked
  -> express allowed high-level concern without private detail

adapter/hint failure
  -> preserve approved semantic response
  -> omit optional expression hint

identity/audience ambiguous
  -> reduce target-specific expression
  -> do not guess permission
```

## Current versus target

This concept is current as an accepted cross-component expression boundary.

Some richer belief, relationship-learning, multi-user, affect, voice, or avatar dynamics may remain target or partially implemented. Current responsibility status remains owned by Project Status and the respective subsystem pages.

This concept does not make the complete target social model a claim of present runtime implementation.

## Stable invariants

- Social expression is downstream of belief/impulse and independent permission/disclosure gates.
- Durable character identity remains upstream of relationship, scene, and affect variation.
- Relationship state may modulate expression but does not create disclosure permission.
- RelaySCN may restrict expression according to current scene/audience.
- RelayEMO modulates intensity/style but does not create permission or truth.
- Relationship warmth may leak in a group only as bounded non-content social texture.
- Relationship-protected information does not leak merely to preserve character realism.
- Probing is optional and cost-sensitive; uncertainty need not always be resolved.
- Response warmth is weak social evidence, not factual proof.
- Mismatch repair is separate from belief, relationship, public-boundary, and persona revision authorities.
- Social expression does not mutate memory, relationship sources, or SOUL synchronously.
- Expression must not optimize dependency, guilt, exclusivity, coercion, or concealed vulnerability exploitation.
- Optional display/TTS/avatar hints remain subordinate to approved semantic output and privacy policy.
- Default diagnostics remain content-free.

## Non-goals

This concept does not define:

- exact relationship or affect scales;
- exact scene/audience/disclosure schemas;
- exact prompt, model, style, ranking, probe, repair, or rendering algorithms;
- automatic relationship or persona updates;
- memory mutation;
- TTS/avatar engine implementation;
- a universal intimacy score;
- project-level implementation sequencing.

## Related architecture and decisions

- [RelayREL Relationship State](relationship-state.md)
- [RelayEMO Affect Modulation](../emotion/affect-modulation.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
- [Observation and Character-Conditioned Belief](../memory/observation-and-character-belief.md)
- [Scene-Aware Memory Scope](../memory/scene-memory-scope.md)
- [Character Belief, Relationship, and Social Expression Dynamics](../character_belief_relationship_dynamics_design.md)
- [Safe REL / SOUL / Scene / CTX Compile Chain](../safe_soul_scene_ctx_compile_chain.md)
