---
relaylm_doc_type: concept_policy
relaylm_authority: protected_source_provenance_and_disclosure_semantics
relaylm_status: current
relaylm_volatility: low
relaylm_owner: privacy
relaylm_update_trigger:
  - protected-source or Evidence provenance authority changes
  - audience, participant, relationship, scene, or disclosure policy changes
  - public/private diagnostics or observation boundaries change
  - memory retrieval, formation, or UI surfaces change protected-content handling
relaylm_not_authoritative_for:
  - exact Evidence, identity, relationship, scene, memory, UI, trace, or diagnostic schemas
  - exact redaction, encryption, authentication, authorization, retention, purge, or consent implementation
  - exact API fields, transport policy, access-control mechanism, or deployment configuration
  - current implementation completion or project sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/character_conditioned_belief_model.md
  - ../../adr/0003-subjective-mem-direction.md
relaylm_related_authority:
  - ../memory/observation-and-character-belief.md
  - ../memory/scene-memory-scope.md
  - ../memory/retrieval-and-grounding.md
  - ../memory/storage-and-recovery.md
  - ../scene/scene-model.md
  - ../relationship/relationship-state.md
  - ../pipeline-responsibilities.md
relaylm_related_contracts:
  - ../../contracts/shared-assessment-subjective-mem.md
  - ../../contracts/subjective-mem-storage-authority-and-commit-protocol.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - privacy and provenance reviewers
  - Evidence, memory, relationship, scene, context, and UI maintainers
  - diagnostics, observability, and integration maintainers
relaylm_authority_level: concept
---
# Protected Source and Disclosure

## Authority summary

RelayLM separates four questions that must never collapse into one:

1. **What protected source or Evidence exists, and what is its provenance?**
2. **Which component is allowed to use that content internally for its own bounded responsibility?**
3. **Which content, if any, may be disclosed to the current audience?**
4. **Which bounded metadata may be emitted to public, audit, diagnostic, or UI surfaces?**

Possession, retrieval, visibility inside one trusted runtime boundary, or relationship familiarity does not automatically answer the later questions.

The stable privacy rule is:

```text
protected content may be available internally
  != permission to disclose it
  != permission to persist it elsewhere
  != permission to expose it in diagnostics
```

This concept owns that cross-subsystem separation. Exact identity, access-control, retention, redaction, encryption, API, and storage mechanisms remain with their owning contracts and components.

## Protected source and provenance

Protected Source Evidence preserves where information came from and under what authority it was admitted.

Depending on the owning Evidence contract, provenance may include source class, speaker or producer, subject, time, audience/scope, route or tool authority, correction/retraction lineage, and other bounded origin facts.

Stable rules are:

- later character interpretation does not rewrite original provenance;
- relationship closeness does not change source origin;
- a scene does not relabel private source as public source;
- a memory page does not become the original Evidence merely because it cites or summarizes it;
- an assistant inference is not backfilled as user-origin Evidence;
- a UI projection or diagnostic record is not promoted into source authority.

If later evidence changes meaning or validity, correction occurs through the owning Evidence/assessment/memory successor model rather than historical provenance mutation.

## Content authority is purpose-bounded

A runtime component may receive protected semantic content only when its responsibility requires that content.

Examples include:

- Shared Assessment reading admitted Evidence;
- Subjective formation reading governed assessment and character authority;
- RelayMEM Retrieval reading eligible memory evidence;
- RelayCTX assembling request-local backend context;
- RelaySCN using bounded participant or scene semantics;
- RelayREL using target-specific relationship policy;
- SOUL Lab rendering an explicitly authorized bounded management view.

Receiving content for one responsibility does not grant ownership of the source or permission to reuse it for another purpose.

A component must not turn incidental visibility into a new persistence, mutation, disclosure, or diagnostics authority.

## Internal use versus external disclosure

The runtime may need more semantic content internally than is safe to reveal externally.

Conceptually:

```text
runtime-private semantic artifact
  -> may contain protected content required by the owning component

public / generic diagnostic projection
  -> content-free by default
  -> exposes bounded state, classes, booleans, counts, and reason IDs only
```

A runtime-private artifact does not become safe merely because one nested field is content-free.

Conversely, a public projection should not require raw protected content simply to report status.

## Disclosure is a separate permission gate

Knowing or retrieving something does not imply permission to say it.

Disclosure may depend on several independent authorities:

- provenance and original audience/source scope;
- authenticated or otherwise governed participant identity;
- target-specific RelayREL policy;
- current RelaySCN scene and audience policy;
- memory scope and lifecycle/currentness;
- explicit privacy/boundary policy;
- safety and product constraints;
- whether the content is observed, inferred, uncertain, private, public, or already disclosed under acceptable authority.

The final result is conservative: all required gates must permit the disclosure.

No single positive signal overrides a negative or unresolved higher-authority gate.

## Relationship is not disclosure permission

A strong or long-lived relationship may influence tone, salience, probing comfort, or whether personal-memory reference is normally appropriate.

It does not independently authorize private disclosure.

Stable rules are:

- strong trust does not imply public familiarity permission;
- attachment does not imply access to every private memory;
- familiarity with one target does not authorize disclosure to a group;
- a relationship role does not prove the current audience identity;
- relationship policy cannot override stricter scene, privacy, boundary, or safety restrictions.

RelayREL contributes one bounded policy input to disclosure; it is not the universal privacy owner.

## Scene and audience narrow disclosure

RelaySCN may identify a public, private, formal, sensitive, roleplay, recovery, or otherwise constrained situation.

Scene policy can narrow disclosure that might otherwise be permitted. It cannot expand protected-content authority beyond provenance, identity, relationship, memory, or privacy rules.

Examples:

- a public group scene may suppress personal details that are acceptable in private conversation;
- a formal scene may suppress familiar or intimate references;
- a medical/safety scene may require conservative handling even if the relationship is close;
- a roleplay scene cannot expose unrelated private memory merely because the role invites familiarity;
- an unknown or ambiguous audience fails closed where exact audience scope is required.

Scene transition does not rewrite the original audience scope of stored Evidence or memory.

## Memory retrieval and disclosure are separate

Ordinary Retrieval first obeys exact reader authority, canonical currentness, lifecycle, scope, and provenance rules.

After retrieval, disclosure may still reject or suppress a selected memory detail.

```text
reader authority
  -> canonical eligible memory
  -> scene / participant / relationship scope
  -> privacy / disclosure permission
  -> grounding may use or omit the detail
```

A disclosure refusal does not authorize fallback to another memory family.

An empty, refused, or privacy-suppressed Subjective result does not restore Primary access.

A selected memory may remain useful internally for response planning even when direct content disclosure is prohibited, but the owning grounding/output policy must prevent unsupported or revealing surface text.

## Formation and persistence are separate from disclosure

A fact that may be disclosed is not automatically eligible for durable memory formation.

A fact that is eligible for governed durable formation is not automatically safe to disclose in every future audience.

Formation must preserve source/provenance and applicable scope under its own contracts. Scene or relationship policy may gate persistence, but neither authorizes a memory write by itself.

Stable distinctions are:

```text
may observe
  != may persist as durable memory

may persist
  != may retrieve in every request

may retrieve
  != may disclose to every audience
```

## Observation and UI visibility

A management or observation UI is a visibility surface, not a new source of authority.

A UI may show bounded protected content only when its exact server-side authority and interface permit it. Browser state, cached data, local preview, stale responses, or a rendered label cannot authorize a durable mutation or wider disclosure.

Historical SOUL Lab observation receipts illustrate the stable rule: read-only observation evidence does not repair queues, publish memory, alter retrieval, or become canonical source truth.

Current UI behavior remains owned by its UI/runtime architecture and Project Status.

## Content-free diagnostics

Generic diagnostics, workflow artifacts, public status endpoints, logs intended for broad operational consumption, and governance checks remain content-free by default.

They may expose bounded fields such as:

- source or authority class;
- content-present boolean;
- audience/disclosure decision class;
- reader/writer authority class;
- lifecycle or recovery state;
- counts and limits;
- confidence/stability bands;
- reason IDs or validation-error IDs;
- whether data was omitted, redacted, blocked, or unavailable.

They should not expose, merely for convenience:

- raw user or assistant text;
- memory prose or subjective meaning;
- relationship body text;
- scene body text or participant names;
- raw client instructions or prompt blocks;
- unrestricted file paths or namespace values;
- raw idempotency keys, tokens, claims, leases, or internal credentials;
- unrestricted digests or lineage values when those identifiers can reveal or correlate protected state;
- unbounded exception strings containing semantic input.

A diagnostic surface that needs semantic content must be explicitly reclassified and governed rather than quietly widening the definition of "diagnostic".

## Public versus private evidence

"Public" and "private" are policy states about audience/disclosure, not intrinsic truth labels.

Evidence may be:

- already public under an accepted source;
- private to one target;
- shared with a bounded participant set;
- operator-only or management-only;
- runtime-private because it contains internal semantic processing;
- content-free and suitable for broad diagnostics.

Moving content between these classes requires the owning authority. Merely storing the same bytes in a different artifact does not change their disclosure class.

A private source summarized into memory does not become public by summarization alone.

## Participant identity and scope

Participant labels, display names, room IDs, session IDs, and scene roles are not interchangeable with authenticated or governed identity.

Where disclosure depends on participant identity:

- identity must come from the owning trusted source;
- ambiguous or conflicting identity fails closed;
- one participant's relationship state is not reused for another participant;
- room membership does not imply permission to disclose every member's private memory;
- session continuity does not prove audience continuity;
- a character's guess about who is present does not create disclosure authority.

## Inference and uncertainty

Inferred content may be more sensitive than explicit observations because it can expose assumptions the user never stated directly.

Shared Assessment or character belief may preserve uncertainty, competing hypotheses, or provisional interpretation.

Disclosure should preserve that epistemic boundary rather than presenting inference as certain private fact.

Stable rules are:

- inference is not upgraded to observation by fluent wording;
- strong model confidence is not provenance;
- affective salience is not evidence confidence;
- a user-visible answer should not reveal a private inferred profile merely because the system can compute one internally;
- uncertainty that matters to safe disclosure is retained or causes omission/abstention.

## Correction, Forget, and Purge boundaries

Privacy does not redefine lifecycle operations.

Correct changes governed memory meaning through its own successor authority.

Forget/Hide changes ordinary retrieval visibility through its own lifecycle authority.

Purge, where authorized, is a separate irreversible authority.

A disclosure block is not equivalent to Forget, and Forget is not proof that all underlying Evidence has been purged.

Likewise, a private memory may remain canonically stored while being ineligible for disclosure in one scene.

## Storage and projection boundaries

Canonical content, durable operations, rebuildable projections, and public diagnostics remain distinct authority classes.

A projection may contain indexes or bounded metadata required for search. Persistence does not make that projection canonical or public.

Operational receipts may be durable without carrying memory prose.

Public projections must be derived from bounded allowlisted state rather than serializing runtime-private objects wholesale.

Recovery, idempotency, locks, or store existence do not create disclosure permission.

## Compile-chain boundary

The managed compile chain may assemble approved durable sources, relationship policy, scene policy, selected memory evidence, working context, and the current user turn into a backend-bound request.

That backend-bound context is purpose-bounded runtime-private content. It must not be treated as a generic trace payload or durable public artifact.

Downstream response finalization remains responsible for ensuring internal instructions, protected evidence, and private context do not leak merely because they were present in the compiled request.

## Fail-closed behavior

When required privacy authority is missing, ambiguous, stale, or conflicting, the system narrows or omits rather than guesses permission.

Examples:

```text
unknown participant identity
  -> do not disclose participant-private memory

ambiguous audience
  -> choose conservative disclosure

retrieved content but scene forbids disclosure
  -> omit or reframe
  -> do not switch memory family

private semantic artifact on a generic diagnostics path
  -> project bounded content-free status
  -> do not serialize the artifact wholesale

stale UI response after scope change
  -> discard/fail closed
  -> do not render under the new scope
```

## Current versus target

This concept is current as an accepted privacy/provenance boundary. It does not claim that every desired identity, consent, redaction, encryption, retention, or multi-user privacy mechanism is fully implemented.

Current components already enforce multiple bounded instances of these rules: content-free projections, loopback/management isolation, exact character/workspace scoping, reader authority, scene narrowing, relationship permissions, stale-response rejection, and protected runtime-private artifacts.

Project Status remains the authority for exact implementation completion.

## Stable invariants

- Protected Source provenance is not rewritten by character belief, relationship, scene, memory, or UI state.
- Internal content access is purpose-bounded and does not imply disclosure or persistence permission.
- Retrieval eligibility and disclosure permission are separate gates.
- Strong relationship does not imply private disclosure permission.
- Scene/audience policy may narrow but never expand protected-content authority.
- Participant identity is governed independently from scene labels, room IDs, roles, or model guesses.
- Shared Assessment and character belief preserve inference/uncertainty boundaries rather than fabricating source truth.
- Public and generic diagnostic surfaces are content-free by default.
- Runtime-private content-bearing artifacts are not safe to persist or expose wholesale.
- UI/observation projections do not become canonical Evidence, memory, or mutation authority.
- A disclosure block is not a lifecycle mutation; Forget is not Purge; Purge is separately governed.
- Primary/Subjective reader authority is not changed by disclosure success or failure.
- Privacy failure closes toward less disclosure, not broader fallback.

## Non-goals

This concept does not define:

- exact authentication or authorization systems;
- exact consent, retention, deletion, purge, export, or legal-compliance mechanisms;
- exact encryption, key management, redaction, or secret-storage implementation;
- exact Evidence, relationship, scene, memory, UI, or diagnostics schemas;
- exact prompt, response, or transport filtering implementation;
- a universal privacy score;
- automatic reclassification of private content as public;
- R5/R6 implementation or Primary retirement;
- project-level implementation sequencing.

## Related architecture and decisions

- [Observation and Character-Conditioned Belief](../memory/observation-and-character-belief.md)
- [Scene-Aware Memory Scope](../memory/scene-memory-scope.md)
- [Ordinary Memory Retrieval and Grounding](../memory/retrieval-and-grounding.md)
- [Memory Storage and Recovery](../memory/storage-and-recovery.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
- [Pipeline Responsibilities](../pipeline-responsibilities.md)
- [ADR: Character-conditioned belief without rewriting observation](../../adr/character_conditioned_belief_model.md)
- [ADR 0003: Subjective MEM direction](../../adr/0003-subjective-mem-direction.md)
