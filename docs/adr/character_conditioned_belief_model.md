---
relaylm_doc_type: adr
relaylm_authority: decision_to_separate_observation_shared_belief_and_character_belief
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - decision is superseded
  - observation or belief authority changes
relaylm_not_authoritative_for:
  - exact wire schemas
  - current runtime implementation status
  - implementation phase sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# ADR: Character-conditioned belief without rewriting observation

## Status

Accepted as target architecture. Implementation remains pending.

## Context

RelayLM aims to produce characters that feel continuous, relationship-aware, and recognizably different from one another.

A naive memory model stores statements such as "the user likes autumn leaves" as facts. This loses several important distinctions:

- RelayLM observed an utterance, not the external truth of its proposition.
- A user may be uncertain, joking, role-playing, simplifying, mistaken, or deceptive.
- Preferences are usually context-dependent latent variables rather than Boolean properties.
- Different characters may reasonably weight the same evidence differently.
- Scene, affect, and relationship may change what a character notices or says without changing the source evidence.
- In multi-user scenes, knowing something does not imply permission to disclose it.

Without a durable decision, character inference can either contaminate shared memory or be normalized away until all characters reason and behave identically.

## Decision

RelayLM will separate:

```text
1. observation ledger
2. character-independent shared evidence assessment
3. character-conditioned provisional belief
4. probe/action impulse
5. relationship, scene, audience, and disclosure permission
6. actual character utterance
```

The observation ledger preserves speaker, subject, time, provenance, speech-act interpretation, and audience scope. Character components may not rewrite it.

RelaySLP may compare current observations with historical evidence and form support, contradiction, refinement, temporal-change, or unresolved outcomes. It may preserve competing hypotheses rather than forcing one timeless fact.

RelaySOUL supplies durable cognitive priors and repair style. RelaySCN supplies moderate scene and audience correction. RelayEMO supplies transient affect whose effective gain may vary strongly by relationship. Relationship state is directional, multidimensional, action-specific, and separate from durable approved relationship anchors.

Character-specific weighting may change what a character believes and how it probes. It does not automatically authorize shared memory promotion, group disclosure, or RelaySOUL mutation.

Multi-user scenes will apply conservative audience and disclosure boundaries while allowing bounded non-content relationship leakage such as warmth, timing, and already-public familiarity.

## Consequences

### Positive

- Characters may disagree or misread the same evidence in recognizable ways.
- Incorrect inference can remain characterful without corrupting provenance.
- Preference modeling can remain context-dependent and revisable.
- Relationship-specific EMO gain can create meaningful private-versus-public behavior.
- Multi-user privacy can be enforced independently from personality expression.
- Character creation can expose cognitive style rather than only voice and biography.
- Repair after mismatch becomes an explicit part of compatibility.

### Costs

- More state classes and stronger scope discipline are required.
- Evaluation must measure calibration, probe comfort, repair, and privacy in addition to answer quality.
- Exact contracts are required before persistence or retrieval implementation.
- Relationship adaptation must be bounded so that it does not erase durable character identity.
- A single scalar confidence or intimacy score will be insufficient for many cases.

## Rejected alternatives

### Store user self-report as certain fact

Rejected because self-report is strong evidence but not direct access to truth, and because preferences may change or depend on context.

### Store only observations and prohibit character inference

Rejected because it removes an important source of character identity, compatibility, and natural conversational probing.

### Let every character write its belief into a shared user profile

Rejected because character bias would contaminate shared evidence and leak across characters.

### Let SCN or EMO rewrite durable memory directly

Rejected because transient scene and affect must not become unreviewed durable truth or persona state.

### Use the lowest group permission for all behavior with no leakage

Rejected as the sole policy because it is safe but socially flat. The selected design preserves the hard boundary while allowing bounded non-content relationship leakage.

## Fixed boundaries

- Assistant-origin inference never becomes user-origin observation.
- Character bias never modifies observation provenance.
- Strong relationship does not imply disclosure permission.
- Private content does not leak through group-scene personality expression.
- Affective gain does not authorize durable memory or SOUL mutation.
- Character dynamics do not optimize dependency, guilt, exclusivity, or coerced engagement.

## Related architecture

- [Character Belief, Relationship, and Social Expression Dynamics](../architecture/character_belief_relationship_dynamics_design.md)
- [AI Character Product Principles](../architecture/ai_character_product_principles.md)
- [RelayMEM SLP Execution Design](../architecture/relaymem_slp_execution_design.md)
- [RelaySCN MVP Scene Policy](../architecture/relayscn_mvp_scene_policy.md)
- [RelayEMO MVP Initial Design](../relayemo_mvp_initial_design.md)
- [RelaySOUL Design](../relaysoul/relaysoul_design.md)
