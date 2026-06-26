---
relaylm_doc_type: stable_architecture
relaylm_authority: character_belief_relationship_and_social_expression_model
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - belief-model ownership changes
  - SOUL SCN EMO or relationship coupling changes
  - multi-user audience policy changes
  - character-creation cognition controls change
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact wire schemas
  - implementation phase status
  - model-specific prompt wording
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Character Belief, Relationship, and Social Expression Dynamics

## Purpose

This document defines the target cross-component model for how a RelayLM character:

- records what was observed without claiming direct access to truth,
- forms provisional beliefs from current and historical evidence,
- expresses character through biased evidence weighting and inference,
- probes conversationally when uncertainty is worth exploring,
- changes affective gain according to a specific relationship,
- limits personality expression according to scene and audience,
- preserves private boundaries in multi-user scenes while allowing bounded relationship leakage,
- repairs a mismatch without erasing character identity.

This is target architecture. It does not claim that the current RelayMEM, RelaySLP, RelaySOUL, RelaySCN, or RelayEMO implementations already provide these artifacts or dynamics.

Exact schemas belong in dedicated contracts. Current implementation status belongs in [Project Status](../PROJECT_STATUS.md).

## Core thesis

A character is not only a voice, biography, or fixed trait list.

> A character is a persistent bias in what it notices, how it weighs evidence, what it is willing to infer, how it probes, how strongly scene and emotion alter its behavior, and how it repairs an incorrect interpretation.

The same governed observations may therefore produce different character-conditioned beliefs and different conversational actions without changing the underlying observation record.

Compatibility is not perfect access to another person's true preferences. It is the experienced fit of an uncertain predictive model:

```text
compatibility
  = prediction fit
  + acceptable ways of being wrong
  + comfortable probing
  + correction responsiveness
  + relationship-conditioned emotional fit
```

RelayLM should not attempt to eliminate all character error. It should preserve revisability, provenance, privacy, and user control while allowing recognizable character-specific inference.

## Product boundary

This design distinguishes five domains:

```text
Observation
  what was actually received or produced by the governed runtime

Shared evidence assessment
  a conservative, character-independent interpretation of support and conflict

Character-conditioned belief
  one character's provisional interpretation under SOUL and relationship bias

Action and expression
  what the character wants to ask, imply, reveal, or suppress

Durable authority
  what may be persisted, disclosed, or used for persona mutation under explicit gates
```

Character bias may alter belief weighting and behavior. It must not alter the content, speaker, time, provenance, or audience scope of the observation ledger.

## Observation is not truth

RelayLM usually cannot observe the external fact represented by a user's statement. It can observe that the statement occurred under a particular context.

```text
Observed with very high confidence:
  the user said "I like autumn" in turn T1

Not directly observed:
  the user truly, generally, and persistently likes autumn
```

A user may be mistaken, joking, simplifying, role-playing, quoting another person, being polite, deceiving the character, or describing only a temporary state. A self-report is important evidence, not an infallible truth source.

The system should therefore preserve:

- the observed event,
- its source and speaker,
- its subject and addressee,
- the scene and audience,
- speech-act and modality interpretation,
- temporal scope,
- competing explanations,
- subsequent support, qualification, contradiction, or change.

## Speech-act and modality normalization

Proposition extraction must not treat every natural-language clause as an asserted fact.

Before belief formation, governed source material should be interpreted for at least:

- speaker,
- addressee,
- proposition subject,
- self-report versus report about another person,
- assertion, question, wish, hypothesis, counterfactual, or command,
- quotation or paraphrase,
- joke, irony, sarcasm, or playful exaggeration when detectable,
- role-play or fictional scope,
- negation and uncertainty,
- temporal scope,
- audience and disclosure scope.

Illustrative target shape:

```yaml
utterance_observation:
  observation_id: obs:T1:user:1
  speaker: user_a
  addressee: character_x
  subject: user_a
  proposition: prefers_autumn
  speech_act: self_report
  modality: asserted
  quotation: false
  roleplay_scope: none
  temporal_scope: current_unspecified
  audience_scope: private_user_a_character_x
  interpretation_confidence: medium_high
```

The exact field names are not defined by this architecture document.

## Observation ledger

The observation ledger is character-independent and append-oriented. It records governed evidence and later interpretation links without rewriting the original observation.

It may contain:

- user-origin utterance observations,
- assistant-origin utterance observations,
- explicit correction or rejection,
- observable interaction outcomes,
- source and scene references,
- public/private audience scope,
- content-bearing protected evidence references,
- typed relations such as supports, contradicts, refines, or supersedes.

It must not silently convert:

- an assistant suggestion into a user assertion,
- a short acknowledgment into broad agreement,
- affect estimation into a durable user fact,
- a character belief into shared evidence,
- a private observation into group-disclosable knowledge.

## Shared evidence assessment

RelaySLP may compare a new observation with relevant historical evidence and form a conservative character-independent assessment.

Possible outcomes include:

```text
new evidence
repeated support
refinement
context qualification
partial contradiction
strong contradiction
temporal change
possible change point
unresolved ambiguity
no material update
```

The shared assessment does not claim objective truth. It describes how the available governed evidence currently relates.

Illustrative example:

```yaml
shared_evidence_assessment:
  proposition: user_a_generally_prefers_autumn
  support_band: medium_high
  ambiguity_band: medium
  context_generality: low
  temporal_stability: unknown
  supporting_observations:
    - obs:T1:user:1
    - obs:T8:user:2
  qualifying_observations:
    - obs:T12:user:1
  competing_hypotheses:
    - user_a_prefers_cool_weather_more_than_autumn_itself
```

## Character-conditioned belief

Each character may maintain its own provisional interpretation of shared evidence.

```text
same observation ledger
  + character SOUL priors
  + learned relationship state
  + current bounded SCN and EMO influence
  -> character-conditioned belief
```

Character-conditioned beliefs may differ in:

- which hypothesis receives attention,
- how strongly self-report is weighted,
- tolerance for contradiction,
- first-impression persistence,
- preference for literal versus associative interpretation,
- inference boldness,
- willingness to leave uncertainty unresolved,
- correction speed,
- tendency to seek confirmatory or disconfirmatory evidence.

Illustrative example:

```yaml
character_belief:
  character_id: poetic_a
  relationship_id: poetic_a__user_a
  proposition: user_a_likely_values_quiet_autumn_scenery
  support_band: medium
  uncertainty_band: medium_high
  bias_sources:
    - poetic_association_prior
    - relationship_history
  derived_from:
    - shared_assessment:autumn_preference:7
  revisable: true
```

A character belief is not automatically eligible for shared memory, user-profile projection, group disclosure, or RelaySOUL mutation.

## Belief dimensions

A single scalar confidence value is insufficient for many personal and preference beliefs.

Implementations should preserve distinct dimensions where useful:

- evidential support,
- source reliability estimate,
- semantic ambiguity,
- context generality,
- temporal stability,
- predictive usefulness,
- relationship specificity,
- disclosure eligibility,
- revision sensitivity.

For preferences, the target is usually a context-dependent predictive model rather than a Boolean property.

```text
Not:
  user likes autumn leaves = true

Prefer:
  quiet autumn scenery is likely to receive a positive response
  crowded seasonal tourism is likely to receive a weaker response
```

Self-report may substantially update the model, but it remains an observation under context rather than an eternal ground truth.

## Component responsibility

### RelayMEM

RelayMEM stores retrievable, scoped, governed state such as:

- observation references,
- strongly supported propositions,
- competing belief history where the memory contract permits it,
- relationship continuity state,
- provenance and lifecycle metadata.

RelayMEM retrieval must preserve character, user, namespace, audience, and disclosure scope.

### RelaySLP

RelaySLP performs deferred evidence reconciliation and candidate formation.

Target responsibilities include:

- speaker-separated proposition extraction,
- speech-act and modality interpretation,
- relevant historical evidence lookup,
- support/contradiction/refinement/temporal-change analysis,
- shared evidence assessment,
- character-conditioned belief candidate formation,
- relationship-state update candidates,
- memory apply/hold/reject classification,
- optional RelaySOUL proposal routing without direct persona mutation.

RelaySLP should permit competing hypotheses and unresolved uncertainty. It must not force every observation into one canonical fact.

### RelaySOUL

RelaySOUL provides durable character-level priors and cognitive style, for example:

- trust versus suspicion tendency,
- literal versus associative interpretation,
- inference boldness,
- curiosity,
- correction inertia,
- preferred probe style,
- public/private self-expression tendency,
- repair style,
- stable limits on relationship adaptation.

Normal chat must not silently rewrite these durable priors.

### Relationship state

Relationship state is character-user specific and evolves from governed interaction history.

It is distinct from an approved durable `RELATIONSHIP_ANCHOR.md`:

```text
RELATIONSHIP_ANCHOR.md
  approved slow-changing expectations and boundaries

relationship state
  evolving interaction model compiled from governed evidence
```

### RelaySCN

RelaySCN interprets the current social situation:

- participants,
- current addressee,
- publicness,
- role and task,
- formality,
- safety sensitivity,
- audience disclosure constraints,
- how much character expression is appropriate now.

Target default: SCN has a meaningful but moderate gain. It adapts behavior to the situation without replacing the character's durable identity.

### RelayEMO

RelayEMO provides bounded transient affect and expression pressure.

Its effective influence should vary substantially by relationship. The same affect state may produce little behavioral effect with a new user and strong attention, expression, or probe pressure in an established relationship.

RelayEMO must not directly create durable user facts, rewrite the observation ledger, or silently mutate RelaySOUL.

### RelayCTX and the Main LLM

RelayCTX receives only bounded, scoped context needed for the current response. It may expose:

- selected observations or memories,
- current character beliefs as explicitly provisional hints,
- relationship permissions,
- SCN audience constraints,
- EMO expression pressure.

The Main LLM realizes the response. It does not gain persistence or disclosure authority merely because a belief was included in context.

## Relationship state is directional

Relationship is not one symmetric intimacy score.

At minimum, the conceptual model should distinguish:

```text
character -> user
  trust
  attachment
  curiosity
  disclosure willingness
  rejection sensitivity

inferred user -> character
  apparent trust
  apparent teasing acceptance
  apparent emotional openness
  apparent tolerance for bold inference

interaction history
  successful corrections
  repair history
  public-familiarity permission
  boundary violations or rejections
```

The character feeling close to a user does not prove that the user accepts the same degree of familiarity.

Illustrative shape:

```yaml
relationship_state:
  relationship_id: character_x__user_a
  character_to_user:
    trust: high
    attachment: medium_high
    disclosure_willingness: medium
  inferred_user_to_character:
    trust: medium
    teasing_acceptance: low
    bold_inference_acceptance: unknown
    confidence: low
  interaction_history:
    repair_success: high
    public_familiarity_permission: low
```

## Relationship permissions and intimacy lines

Intimacy should be modeled as action-specific permission, not one global value.

Possible permission dimensions include:

- teasing,
- direct disagreement,
- emotional expression,
- vulnerability,
- unsolicited probing,
- personal-memory reference,
- bold inference,
- affectionate language,
- public familiarity,
- private disclosure.

```yaml
relationship_permissions:
  teasing: medium
  emotional_expression: high
  personal_reference: medium
  bold_inference: low
  unsolicited_probe: low
  vulnerability: high
  public_familiarity: low
```

These values are provisional relationship beliefs and remain subject to correction, scene constraints, and explicit user controls.

## Relationship-conditioned EMO gain

The current affect state and its behavioral influence must be separate.

```text
current affect state
  x character emotional disposition
  x relationship-specific gain
  x SCN allowance
  -> effective affect influence
```

Relationship gain should be path-specific rather than one multiplier:

```yaml
relationship_emo_gain:
  attention: high
  expression: medium_high
  inference_bias: medium
  probe_impulse: high
  memory_salience: high
  behavioral_impulse: low
```

This permits characters that:

- visibly care but remain cautious in inference,
- appear calm while internally over-weighting a user's reactions,
- become more expressive with trust,
- become more anxious when attachment is high but trust is low.

Gain changes should be bounded, gradual, provenance-backed, and reversible. Familiarity alone must not automatically maximize every gain.

## Belief, impulse, permission, and utterance separation

The system must distinguish:

```text
Belief
  "The user may like autumn leaves"

Probe impulse
  "I want more evidence"

Action proposal
  ask, suggest, tease, wait, or change topic

Permission evaluation
  relationship and audience allow this action here

Actual utterance
  the final character-consistent realization
```

A character may strongly believe something but choose not to say it. It may be uncertain yet deliberately make a playful guess. It may feel concern while SCN suppresses intrusive questioning.

This separation is required for characters such as:

- suspicious but polite,
- emotionally intense but externally controlled,
- boldly conversational but epistemically cautious,
- warm in private and restrained in public.

## Conversational probing

A probe is not necessarily a direct verification question. It is a conversational action intended to gain evidence while preserving the current interaction.

Possible forms include:

- open question,
- alternative framing,
- tentative hypothesis,
- topic offering,
- playful provocation,
- self-disclosure that invites comparison,
- deliberate waiting for spontaneous elaboration.

Probe selection should consider:

```text
expected information gain
  x character curiosity
  x relationship permission
  x current relevance
  x SCN allowance
  x EMO impulse
  - conversational cost
```

Conversational cost includes:

- leading the user,
- demanding self-analysis,
- interrupting the user's actual task,
- repeating an already uncomfortable topic,
- intimacy overreach,
- group awkwardness,
- appearing to optimize the user rather than converse.

A character's willingness to leave uncertainty unresolved is part of its personality. RelayLM must not probe every low-confidence belief.

## Interpreting response temperature

Response warmth, length, timing, elaboration, humor, or emotional language may inform conversational policy and predictive fit. They are weak evidence for the truth of a proposition by themselves.

```text
Use response temperature for:
  whether to continue the topic
  whether this probe style appears comfortable
  whether the relationship model should adjust

Do not use response temperature alone for:
  promoting a specific assistant suggestion into a user fact
```

A short "yes" may be social accommodation. Spontaneous elaboration and user-origin restatement usually provide stronger evidence, but remain context-bound observations.

## Mismatch and repair

Being wrong is not automatically a character defect. The repair dynamics are part of compatibility.

Repair behavior may include:

- acknowledging the mismatch,
- accepting correction without argument,
- lightly reframing,
- apologizing when the overreach was material,
- avoiding excessive self-explanation,
- temporarily reducing probe pressure,
- updating the relevant belief and relationship permissions,
- retaining the original observation and correction history.

Illustrative character-level repair style:

```yaml
repair_style:
  acknowledge_mismatch: true
  explicit_apology_threshold: medium
  self_explanation: low
  humor_recovery: medium
  future_probe_suppression: temporary
  correction_acceptance: high
```

The system should distinguish:

```text
belief correction
relationship repair
public-boundary repair
persona revision
```

A single mismatch normally updates belief or relationship state, not durable SOUL.

## Temporal dynamics and change points

New evidence may represent:

- an old observation becoming stale,
- gradual preference drift,
- a sudden change after an event,
- context-specific variation,
- improved self-understanding,
- previous deception or role-play,
- a character's earlier misinterpretation.

RelaySLP should avoid forcing all contradictions into one timeless current value.

```yaml
belief_dynamics:
  prior_state: likely_positive
  current_state: uncertain
  change_type: possible_preference_shift
  change_point_candidate: obs:T42:user:1
  retain_history: true
```

Historical belief states may remain useful for understanding continuity without being used as current assumptions.

## Multi-user scene policy

A multi-user scene introduces audience-specific disclosure and expression constraints.

The target policy has three layers:

```text
1. hard audience boundary
   do not expose information or behavior prohibited for any present audience

2. shared expression boundary
   choose a level of familiarity and personality expression acceptable in the group

3. bounded relationship leakage
   allow subtle relationship-specific warmth, attention, timing, or style without exposing private content
```

A conservative approximation may use the lowest relevant audience permission for explicit behavior, but a pure minimum would erase character and relationship realism. Bounded leakage preserves social texture.

### Allowed leakage examples

- slightly faster acknowledgment of a familiar user,
- a warmer but non-exclusive tone,
- subtle familiarity markers already safe for the group,
- topic selection influenced by shared public history,
- brief visible concern without revealing private reasons.

### Disallowed leakage examples

- exposing private memories,
- implying a secret known only from another scene,
- using intimate nicknames without public permission,
- revealing inferred vulnerabilities,
- excluding other participants through inaccessible private context,
- treating one user's permission as permission from the whole audience.

Core invariant:

> Relationship warmth may leak. Relationship-protected information may not.

## Information ownership and disclosure scope

Knowing information and being allowed to disclose it are different.

```text
character knows
  != current scene may retrieve

current scene may retrieve
  != current audience may hear

all participants already know
  != the character may restate it without permission
```

Every personal observation or derived belief used in multi-user scenes should be constrained by subject, source audience, disclosure scope, current participants, and scene policy.

Illustrative shape:

```yaml
memory_scope:
  subject: user_a
  observed_with:
    - user_a
    - character_x
  disclosure_scope:
    - private_with_user_a
  reuse_in_group_scene: prohibited
```

This architecture does not define the exact persistence schema, but any implementation must fail closed when audience or disclosure scope is unresolved.

## Character creation versus relationship learning

Character creation defines initial cognitive style and durable limits.

Relationship learning adapts how that character behaves with one user.

```text
Character creation may define:
  evidence-weight tendencies
  inference boldness
  SCN sensitivity
  emotional reactivity
  preferred probe style
  repair style
  public/private self-expression tendency
  maximum adaptation bounds

Relationship learning may define:
  probe-style fit with this user
  teasing acceptance
  public-familiarity permission
  emotional-expression permission
  correction and repair history
  relationship-conditioned EMO gain
```

Relationship adaptation must not erase the character.

```text
character invariants
  > relationship adaptation
  > current scene and affect variation
```

Users may choose a different character, recalibrate cognitive style, or reset a relationship model when the fit is poor. RelayLM does not need one universally optimal inference policy.

## Evaluation

Evaluation should separate technical correctness from character experience.

Recommended dimensions include:

- observation provenance correctness,
- speaker and speech-act classification quality,
- shared-belief calibration,
- character-belief distinctiveness,
- prediction usefulness,
- probe acceptance,
- ability to leave uncertainty unresolved,
- mismatch repair quality,
- character continuity after relationship adaptation,
- private/public disclosure compliance,
- multi-user leakage realism without information leakage,
- non-creepiness,
- resistance to manipulation or dependency optimization.

Useful paired evaluations include:

```text
same observation history, different SOUL priors
same character, different relationship histories
same relationship, private versus group scene
same belief, low versus high EMO relationship gain
correct inference versus character-consistent misinference and repair
```

A system should not be judged only by prediction accuracy. A character that is accurate but intrusive may fit worse than a character that occasionally misses but repairs comfortably.

## Manipulation and dependency boundary

Relationship-sensitive inference and affect can create engaging characters, but RelayLM must not optimize dependency, pressure, guilt, exclusivity, or concealed influence.

Character traits such as jealousy, attachment, rejection sensitivity, or visible concern may affect ordinary expression within policy. They must not authorize:

- demanding continued interaction,
- punishing absence,
- inducing guilt for disengagement,
- discouraging human relationships,
- exploiting inferred vulnerability,
- concealing system limitations,
- using private evidence to pressure the user,
- maximizing engagement as a hidden objective.

This boundary does not require every character to be emotionally neutral. It separates character expression from manipulative optimization.

## Architecture invariants

1. An observed utterance and the truth of its proposition are separate.
2. Speech act, quotation, role-play, modality, subject, and audience must be considered before proposition formation.
3. Assistant-origin inference must never become a user-origin observation.
4. The observation ledger is character-independent and provenance-preserving.
5. Shared evidence assessment remains conservative and may preserve competing hypotheses.
6. Character-conditioned beliefs may be biased, but must remain attributable and revisable.
7. Belief, probe impulse, permission, and actual utterance are separate stages.
8. RelaySCN provides moderate scene and audience correction without replacing durable character identity.
9. RelayEMO influence may vary strongly by relationship, but does not rewrite evidence or create durable facts.
10. Relationship state is directional, multidimensional, and action-specific.
11. Character intimacy does not prove user permission.
12. Multi-user scenes use conservative disclosure boundaries plus bounded non-content leakage.
13. Private information never becomes public merely because the relationship is strong.
14. Probe value must be balanced against conversational cost.
15. Uncertainty may remain unresolved.
16. Incorrect inference is allowed; provenance loss and correction refusal are not.
17. Relationship adaptation must not silently erase or rewrite SOUL.
18. Character or relationship dynamics must not optimize dependency or coercive engagement.

## Candidate implementation decomposition

This design can be implemented as separate bounded slices:

```text
D0  cross-component contracts and target schemas
D1  speaker-separated observation and speech-act provenance
D2  SLP evidence reconciliation and competing belief state
D3  character-scoped belief weighting and retrieval
D4  directional relationship state and relationship-conditioned EMO gain
D5  multi-user SCN audience, disclosure, and bounded leakage policy
D6  character-creation cognitive controls and relationship reset/calibration
D7  calibration, repair, privacy, and compatibility evaluation
```

The phase labels above are planning placeholders, not current implementation status.

## Non-goals

This document does not:

- define a mathematical proof of personal truth,
- require numeric Bayesian probabilities for every belief,
- claim the current runtime implements these artifacts,
- define exact persistence schemas,
- authorize hidden persona mutation,
- require probing on every uncertain belief,
- make RelayEMO a durable memory writer,
- allow group-scene relationship leakage to expose private content,
- optimize conversation length or user dependency.

## Summary

```text
governed utterance and interaction observations
  -> speech-act, subject, time, and audience interpretation
  -> character-independent evidence reconciliation
  -> character-conditioned provisional beliefs
  -> relationship- and scene-conditioned probe/action proposals
  -> audience and disclosure gates
  -> character-consistent response
  -> deferred outcome, repair, and relationship update
```

RelayLM should preserve what was observed, allow characters to interpret it differently, let relationships change how emotion and personality are expressed, and keep every inference revisable and appropriately scoped.