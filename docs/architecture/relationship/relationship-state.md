---
relaylm_doc_type: subsystem_architecture
relaylm_authority: relayrel_relationship_state_and_interaction_policy_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relationship
relaylm_update_trigger:
  - RelayREL target-specific relationship responsibility changes
  - relationship source tree or target identity authority changes
  - relationship-conditioned interaction policy changes
  - RelayREL ordering or integration with SCN, EMO, MEM, CTX, or SLP changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact RELATIONSHIP.md or relationships/<target>.md parser/compiler schemas
  - exact relationship update proposal/apply API or storage protocol
  - exact target authentication, identity resolution, UI, or model behavior
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../relayrel_relationship_design.md
  - ../character_belief_relationship_dynamics_design.md
  - ../pipeline-responsibilities.md
  - ../scene/scene-model.md
  - ../memory/observation-and-character-belief.md
  - ../memory/scene-memory-scope.md
  - ../privacy/protected-source-and-disclosure.md
  - ../safe_soul_scene_ctx_compile_chain.md
  - ../../relaysoul/relaysoul_design.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayREL and Character Workspace maintainers
  - RelaySCN, RelayEMO, RelayMEM, RelayCTX, and RelaySLP integration maintainers
  - privacy, social-expression, and relationship-governance reviewers
relaylm_authority_level: subsystem
---
# RelayREL Relationship State

## Purpose

This page is the canonical subsystem architecture for target-specific relationship state and relationship-conditioned interaction policy.

RelayREL answers one bounded question:

```text
What relationship-specific interaction policy applies between this character and this governed target?
```

It keeps portable character identity separate from target-bound state while allowing the same character to interact differently with different authenticated or otherwise governed targets.

Exact current implementation status remains owned by Project Status. Exact source schemas, parser/compiler behavior, update APIs, and storage mechanics remain with their owning contracts and implementation handoffs.

## Stable source boundary

The permanent source model separates portable character policy from target-specific state:

```text
SOUL.md / STYLE.md / EMOTION.md / BOUNDARY.md
  -> portable character identity and policy

RELATIONSHIP.md
  -> relationship role/dimension/permission vocabulary

relationships/<target>.md
  -> one target-specific relationship instance
```

`RELATIONSHIP.md` describes the vocabulary and bounded policy available to RelayREL. It must not contain one concrete target's private relationship history as though it were portable character identity.

`relationships/<target>.md` is target-bound. It must not be copied to another target or promoted into portable SOUL merely because a relationship is strong or long-lived.

## Relationship state is directional and target-specific

Relationship state is not a global user profile and not one scalar intimacy score.

Stable dimensions may include, where their owning source/contract defines them:

- relationship role;
- trust or confidence in interaction;
- attachment/salience;
- respect for autonomy;
- correction acceptance;
- direct disagreement permission;
- teasing/playfulness permission;
- bold inference permission;
- unsolicited probe permission;
- personal-memory reference permission;
- public familiarity permission;
- private disclosure permission;
- relationship-conditioned affect gain;
- repair style;
- bounded update policy.

The exact field set and scale remain source/contract details.

Different dimensions may move independently. High warmth does not imply high disclosure permission; high trust does not imply high probing permission; strong attachment does not imply reduced autonomy protection.

## Target identity is governed, not guessed

RelayREL applies only after a target identity or target class is resolved through the owning route/session/authentication authority.

Natural-language references, display names, model guesses, scene roles, room IDs, or recent conversation content do not create relationship identity by themselves.

Stable rules are:

- unknown target identity fails closed for target-specific permissions;
- conflicting identity does not merge two relationship instances;
- one target's relationship state is never reused for another target merely to avoid an empty projection;
- group/room membership does not imply individual relationship authority;
- target identity is an input to RelayREL, not an inference side effect of relationship content.

## Portable SOUL versus relationship state

RelaySOUL owns who the character is durably and portably.

RelayREL owns how that character is permitted and inclined to interact with one governed target.

```text
SOUL
  character values honest co-creation

RelayREL policy
  direct disagreement is allowed at a bounded level with this target
```

The durable character value remains portable. The target-specific permission does not.

Relationship state may modulate expression of a SOUL trait; it does not silently rewrite SOUL.

## Relationship state versus memory

Relationship state and memory are related but distinct authorities.

```text
memory
  what happened, what was said, what is known or remembered

relationship state
  how this character is permitted and inclined to interact with this target
```

Memory Evidence may support a relationship-update candidate. Relationship state may constrain whether personal memory is appropriate to reference. Neither authority directly rewrites the other during the ordinary response path.

A remembered event is not automatically a relationship-state update. A strong relationship parameter is not proof of a user fact.

## Relationship state versus scene

RelaySCN owns the current semantic scene, participants/audience interpretation, and request-local scene policy.

RelayREL owns target-specific relationship policy.

When they conflict, the effective interaction policy is conservative. A restrictive public/formal/sensitive scene is not overridden by target familiarity.

```text
RelayREL
  normally direct and familiar with this target

RelaySCN
  public group scene, low personal-disclosure allowance

result
  familiarity may affect tone within bounds
  personal disclosure remains suppressed
```

Scene transition does not rewrite relationship state. Relationship closeness does not select the scene.

## Relationship state versus affect

RelayEMO owns transient affect and expression pressure.

RelayREL may supply relationship-conditioned gain or limits that modulate expression, salience, repair, and probe comfort.

It does not own affect classification.

Strong affect does not itself update relationship state, and strong relationship gain does not make affect durable memory or truth.

## Relationship-conditioned policy surfaces

RelayREL may provide bounded policy to downstream components.

### RelaySCN

May consume target-specific familiarity, public/private tolerance, intimacy/disclosure bounds, or role-relevant interaction policy while retaining scene authority.

### RelayEMO

May consume relationship-conditioned expression gain, repair preference, attachment-sensitive salience, or probe bounds while retaining affect authority.

### RelayINT

May consume permissions for disagreement, clarification, playful challenge, probing, or other interaction style while retaining intent/reference authority.

### RelayMEM

May consume whether personal-memory reference is appropriate for this target, subject to reader authority, lifecycle, scene scope, provenance, and privacy/disclosure gates.

### RelayCTX

May consume a bounded relationship-policy projection for context assembly while retaining prompt layout and token-budget authority.

### RelaySLP

May use governed Evidence to classify whether an outcome remains Evidence/memory, becomes a relationship candidate, is held, or becomes a separately governed proposal.

These surfaces are constraints/modulation inputs. RelayREL does not acquire downstream component authority merely because its policy is consumed there.

## Permission is bounded and compositional

Relationship permissions are not global capability tokens.

For any action or disclosure, RelayREL is one policy layer among others:

```text
runtime / safety / product policy
  + portable BOUNDARY / SOUL policy
  + exact target identity
  + RelayREL relationship policy
  + RelaySCN current scene/audience policy
  + privacy / provenance / memory scope
  -> bounded effective interaction
```

A positive relationship permission cannot override a stricter higher-authority or current-scene restriction.

## Strong relationship does not imply disclosure permission

This is a permanent invariant.

High trust, attachment, familiarity, or salience may make a reference feel natural, but disclosure still requires the owning privacy, scene, participant, memory, and provenance gates.

A private fact known about one target is not automatically appropriate in a group scene.

A relationship instance can distinguish private-disclosure permission from public-familiarity permission; these are not interchangeable.

## Belief and inference boundary

Character-conditioned provisional belief may be influenced by relationship context, but relationship state does not rewrite observation or Shared Assessment.

A character may trust one target more than another and therefore choose a different conversational stance. That does not change what the Evidence proves.

Relationship dynamics may affect probing comfort, repair, or expression. They do not convert inference into source fact.

## Update path is out-of-band

Normal response generation does not silently mutate relationship sources.

The stable target path is:

```text
governed Evidence
  -> RelaySLP relationship candidate
  -> authority / confidence / compatibility / safety checks
  -> reject | hold | memory-only | relationship proposal
  -> explicit approval where required
  -> versioned target-specific relationship-source update
```

Exact candidate taxonomy, thresholds, review UX, source commit protocol, and automation policy remain separately governed.

A relationship update proposal is not the relationship state until its owning apply/commit authority succeeds.

## One-turn impressions are not durable relationship state

The current turn may create a transient impression such as warmth, frustration, confidence, or uncertainty.

Such impressions may influence current affect or become Evidence for later assessment. They are not copied automatically into `relationships/<target>.md`.

This prevents temporary emotion, roleplay, one disagreement, or one highly successful interaction from silently rewriting durable relationship policy.

## Recovery and stale-state behavior

Relationship state consumed by a request must correspond to the exact governed target/source revision accepted by its owning compile boundary.

Stale browser state, old projections, cached target selection, or previous-request relationship policy cannot override a newer governed target/source revision.

If exact relationship state is unavailable or invalid, the system fails closed toward less target-specific permission rather than borrowing another target's state.

## Public diagnostics are content-free

Default diagnostics may expose bounded classes such as:

- relationship-target present/absent;
- projection status;
- source-authority class;
- bounded policy/permission bands;
- restrictive reason IDs;
- target scope present/validated boolean;
- content-free marker.

They do not expose by default:

- relationship source body text;
- private target names where not already public;
- raw user/assistant text;
- relationship notes;
- protected Evidence snippets;
- unrestricted filesystem paths, namespaces, or source internals.

A content-bearing relationship management surface requires its own explicit access/visibility authority; it is not made safe by being called diagnostics.

## Current versus target

This page is current as the canonical responsibility map for RelayREL.

The accepted full file-first relationship source/compiler/update architecture may be ahead of current runtime implementation. Current request-path RelayREL projection/order and any existing bounded consumers do not prove every target source/parser/update capability is complete.

Project Status remains authoritative for implementation completion.

## Primary compatibility and memory migration

Relationship policy does not select Primary versus Subjective ordinary-memory authority.

RT-1 reader/writer decisions remain independent. Relationship policy may narrow memory reference/disclosure within the selected authority; it cannot restore a retired or fenced memory family.

R5/R6 retirement therefore does not transfer memory-family authority into RelayREL.

## Stable invariants

- RelayREL owns target-specific relationship state and relationship-conditioned interaction policy.
- Portable SOUL identity and target-specific relationship state remain separate.
- Relationship state is directional/multidimensional; no single intimacy or trust scalar controls all behavior.
- Target identity comes from governed route/session/authentication authority, not free-text guessing.
- Relationship state is not memory and does not rewrite observation/Shared Assessment.
- Relationship state may constrain scene, affect, intent, memory reference, context, and deferred proposals without owning those components.
- Strong relationship does not imply private or group disclosure permission.
- Restrictive scene/privacy/boundary/safety policy is not overridden by familiarity.
- One-turn affect or impression does not automatically become durable relationship state.
- Normal response generation does not silently mutate relationship source files.
- Missing/invalid relationship state fails closed toward less permission and never borrows another target's state.
- Default public diagnostics remain content-free.
- Relationship policy cannot select or restore an ordinary-memory reader family.

## Non-goals

This architecture does not define:

- exact relationship source schemas or dimensions;
- exact parser/compiler/update implementation;
- automatic target discovery from free text;
- authentication or account identity implementation;
- an intimacy score that overrides all other policy;
- automatic relationship mutation during ordinary conversation;
- durable memory or SOUL mutation;
- exact UI/API behavior;
- current implementation completion or project sequencing.

## Related architecture

- [RelayREL Relationship Design](../relayrel_relationship_design.md)
- [Observation and Character-Conditioned Belief](../memory/observation-and-character-belief.md)
- [Scene-Aware Memory Scope](../memory/scene-memory-scope.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Safe REL / SOUL / Scene / CTX Compile Chain](../safe_soul_scene_ctx_compile_chain.md)
- [RelaySOUL Design](../../relaysoul/relaysoul_design.md)
