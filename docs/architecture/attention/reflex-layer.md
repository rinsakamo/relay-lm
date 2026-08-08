---
relaylm_doc_type: subsystem_architecture
relaylm_authority: pre_request_attention_and_turn_admission_architecture
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: attention
relaylm_update_trigger:
  - pre-request turn-admission responsibility changes
  - continuous-input attention or bounded aggregation ownership changes
  - the RelayATN component boundary or naming is superseded
  - content-free RelayCTX-to-attention input authority changes
  - scene-escalation or overload admission boundaries change
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact SourceEvent, admission, snapshot, cursor, hold, score, or classifier schemas
  - evidence consent, retention, source authority, or persistence
  - RelayCTX working-state, CTX-OVL, catch-up, or partition mutation semantics
  - RelaySCN classification, RelayINT action semantics, or durable memory behavior
  - scheduler, checkpoint, transport, ASR, TTS, or interruption implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../pipeline-responsibilities.md
  - ../runtime/request-response-pipeline.md
  - ../relayatn_reflex_layer_design.md
  - ../../adr/relayatn_pre_request_authority_separation.md
  - ../context/context-assembly.md
  - ../scene/scene-model.md
  - ../analyzers/reference-and-intent.md
  - ../memory/formation.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_related_contracts:
  - ../../contracts/governed-source-capture-admission.md
  - ../../contracts/relayctx-session-evidence-overlay.md
  - ../../contracts/relayrun-checkpoint-and-recovery.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - future continuous-input and attention-layer maintainers
  - RelayRUN, RelayCTX, RelaySCN, and RelayINT maintainers
  - governed-ingress, scheduler, privacy, and multi-user reviewers
relaylm_authority_level: subsystem
---
# Attention / Reflex Layer Architecture

## Purpose

This page is the canonical responsibility map for RelayLM's target pre-request attention/reflex layer.

Its only semantic authority is deciding whether a candidate input should start a normal turn now, remain transiently held, be rejected as a turn candidate, or carry a bounded advisory flag into the normal request path.

The stable boundary is:

```text
continuous or competing input
  -> governed source/evidence path remains independent
  -> bounded pre-request attention decision
       reject | hold | select | flag
  -> selected candidate enters the normal RelayRUN request path
```

The attention layer decides **whether and on what a turn starts**. It does not decide what the admitted turn means, what may be disclosed, what becomes memory, or how the final response is produced.

`RelayATN` remains the current working component name in the source architecture. The durable authority described by this page does not depend on that name remaining permanent.

## Current versus target implementation

The authority separation in this page is accepted architecture, but the attention/reflex component is not a current default runtime stage.

The current interactive pipeline continues to operate without this target layer. Continuous-input admission, resident attention scoring, bounded hold state, and related contracts remain future work unless Project Status explicitly records otherwise.

Therefore this page is authoritative for the target responsibility boundary, not proof that RelayATN is implemented, enabled, default-on, or scheduled.

Project Status remains authoritative for exact implementation completion.

## Turn admission is an independent decision

RelayLM keeps four decisions separate:

```text
turn admission
  != evidence admission
  != current-session continuity
  != durable memory formation
```

A candidate may be rejected as a reason to start a response while its source occurrence is still retained by the governed evidence path.

Likewise, selecting a candidate to start a turn does not by itself authorize evidence retention, context mutation, scene classification, memory formation, or disclosure.

No attention score or wake decision collapses these boundaries.

## Permitted decision classes

The target attention layer has only a narrow family of externally meaningful outcomes:

- **reject** — do not start a normal turn for this candidate;
- **hold** — keep a bounded transient reference for later admission consideration;
- **select** — admit the candidate into the normal request/response pipeline;
- **flag** — attach bounded advisory state that downstream owners may independently inspect.

These classes describe admission behavior only.

They are not intent classes, scene classes, memory lifecycle values, disclosure permissions, evidence outcomes, or response modes.

Exact enum values, score shapes, timeout values, and wire schemas remain contract or implementation detail.

## Selection creates a normal turn, not a privileged path

A selected candidate enters the same governed request path as any other admitted input.

```text
attention select
  -> RelayRUN request shell
  -> normal semantic owners
  -> context construction
  -> compile gate
  -> backend execution
  -> normal response finalization
```

Selection does not bypass RelayREL, RelaySCN, RelayEMO, RelayINT, Retrieval, RelayCTX, safety, compile, recovery, or output boundaries.

The attention layer cannot create a reduced-authority shortcut merely because the input was classified as urgent, direct, familiar, or likely to deserve a reply.

## Evidence admission remains external

Governed evidence authority owns source identity, consent/authorization, retention, provenance, and durable source records.

The attention layer may observe incoming material needed to score a turn candidate, but it does not own whether that material becomes governed Evidence.

Consequences:

- `reject` must not delete, suppress, or rewrite evidence owned elsewhere;
- `select` must not force evidence admission;
- `hold` must not create a second durable raw-input store;
- `flag` must not become provenance, source authority, or evidence confidence.

A missed wake and a lost governed observation remain different failure classes.

## RelayRUN owns orchestration after admission

RelayRUN owns the request shell, run identity, orchestration, checkpoints, retry/fallback routing, stream state, and response finalization under its own contracts.

The attention layer is semantically before the normal request shell.

It may be supervised by runtime/service infrastructure in a future deployment, but supervision does not transfer attention semantics into RelayRUN.

RelayRUN does not reinterpret an attention result into scene, intent, memory, or disclosure authority.

The attention layer likewise does not own checkpoint persistence or recovery semantics merely because a held/selected candidate must survive some local scheduling boundary.

## RelayINT owns admitted-turn intent

The separation is:

```text
Attention layer: should this candidate start a turn?
RelayINT:       what should the admitted turn do?
```

The attention layer does not perform final intent classification, reference resolution, clarification planning, memory-retrieval need selection, tool/action selection, or response-mode choice.

A high-confidence wake or direct-address signal does not replace RelayINT interpretation after admission.

Reference and intent candidates remain governed by the analyzer/RelayINT boundary.

## RelaySCN owns scene authority

The attention layer may detect a possible scene or audience change cheaply enough to influence admission caution.

That detection is advisory and restrictive-only.

It may cause downstream owners to re-check their own state, but it cannot:

- classify the authoritative scene;
- infer that a scene became less restrictive;
- authorize private-to-group disclosure;
- migrate participant scope;
- relax memory or context packing fences.

RelaySCN remains the scene-policy owner for the admitted request.

Possible escalation must never be interpreted as permission to downgrade privacy controls before owning classification completes.

## RelayCTX owns working and packed context

The attention layer is not a short-term memory subsystem.

It must not write, retract, reconcile, acknowledge, collapse, evict, or otherwise mutate RelayCTX working state or CTX-OVL.

Any state RelayCTX exposes to pre-request attention must be a bounded content-free projection owned by RelayCTX.

Such a projection may communicate admission-relevant facts such as:

- revision/freshness class;
- bounded counts;
- coverage or completeness class;
- conservative scope-change state;
- opaque state versioning needed to detect staleness.

It must not expose raw working-context content, private relationship content, durable memory bodies, semantic sidecars, evidence confidence, salience, or reversible content-derived identifiers merely to improve attention accuracy.

Missing or invalid freshness data yields uncertainty; the attention layer does not repair RelayCTX state.

## Catch-up remains an owning RelayCTX/ingress concern

A source occurrence that did not start a turn may later affect an admitted turn only through the governed ingress and context paths that own that behavior.

The attention layer does not hydrate rejected raw text directly into working context and does not advance evidence-coverage cursors.

Any future catch-up path must still preserve normal identity, consent, scene, interpretation, and context fences.

The attention layer may notice that continuity appears stale, but it cannot synthesize the missing semantics itself.

## RelayMEM and RelaySLP remain durable-memory owners

Attention scoring is not memory scoring.

The attention layer has no authority over:

- Shared Assessment;
- Subjective MEM formation;
- ordinary Retrieval reader selection;
- memory ranking or grounding;
- canonical memory identity;
- lifecycle state;
- evidence confidence;
- memory strength or salience;
- persistence or mutation.

A wake score, urgency score, aggregation score, or classifier confidence never becomes memory confidence, conviction, relation authority, or durable importance.

The attention layer cannot select a memory reader, choose a durable memory to boost/shadow, or create cross-family fallback.

## Relationship and affect are not admission authority shortcuts

RelayREL and RelayEMO may provide bounded policy or expression context to their owning pipeline stages after admission.

The attention layer does not infer disclosure permission from familiarity, relationship strength, or affect.

A coarse transient urgency/affect estimate may be useful for admission prioritization, but it remains an attention-only signal.

It must not become current relationship state, durable emotion truth, scene policy, or memory importance.

Persistent character-conditioned attention policy would be a separate authority decision; this page does not grant the reflex layer permission to learn or mutate such policy from its own scores.

## Bounded aggregation is response-candidate grouping only

Continuous environments may produce several nearby inputs that would cause redundant wake-ups if each became an independent turn.

The attention layer may perform bounded transient aggregation for admission purposes.

Aggregation must preserve enough source identity for downstream owners to recover distinctions such as:

- member source references;
- known speaker identity;
- event order;
- trusted direct-address metadata when supplied by an owning ingress source.

Aggregation is not evidence consolidation, semantic reconciliation, context collapse, or memory consolidation.

It must not decide that two observations are semantically identical, independently corroborating, corrected, relationship-equivalent, scene-equivalent, or one durable memory.

If those distinctions matter, the admitted request path and owning deferred systems decide them.

## Trusted signals and inferred signals remain different

Some admission-relevant properties may arrive as trusted metadata from an owning source, while others may be inferred from content by heuristics or models.

The attention layer must preserve that distinction.

Authenticated control/direct-address metadata may carry stronger admission significance than a lexical or classifier guess, but neither bypasses downstream safety and semantic ownership.

Inferred urgency, correction, direct address, state change, or scene escalation remains a candidate signal rather than source authority.

Classifier confidence does not turn inferred metadata into authenticated metadata.

## Heuristics and model tiers remain non-authoritative

An implementation may use deterministic rules, lightweight classifiers, embeddings, or a bounded small-model fallback to estimate attention value.

Regardless of implementation tier:

- outputs stay within admission decisions and bounded flags;
- model prose is not a policy protocol;
- the model cannot repair semantic sidecars or context state;
- the model cannot resolve durable identity from memory;
- the model cannot create memory, relationship, or scene authority;
- timeout/uncertainty cannot silently broaden admission or disclosure authority.

The canonical boundary depends on the allowed effect, not the chosen model architecture.

## Backpressure and hold remain bounded

`hold` is a transient admission mechanism, not a queue for durable semantic work.

A future owning contract may define expiration, capacity, rate limits, backpressure, or overload behavior.

The stable architectural requirements are:

- held state is bounded;
- held state uses opaque/source references rather than becoming a second content archive;
- loss of hold scheduling state does not delete governed evidence;
- overload does not authorize broader disclosure or semantic shortcuts;
- multi-source wake pressure cannot create unbounded turn amplification.

Scheduler/service policy owns exact cadence and priority; the attention layer owns only the admission meaning of its decisions.

## Failure preserves ordinary turn-based operation

Because this is an optional target layer, failure must not corrupt the existing ordinary request/response pipeline.

A deployment that does not require continuous-input admission can continue through the normal turn-based path without RelayATN.

For a profile that does require pre-request attention, uncertainty closes toward less autonomous admission in ambiguous or multi-source contexts.

Failure must not:

- erase or rewrite governed evidence;
- clear RelayCTX state;
- infer a less restrictive scene;
- select or mutate durable memory;
- create a user-visible response outside the normal pipeline;
- bypass safety, recovery, or output authority.

Where a trusted single-source/1:1 policy explicitly authorizes a simpler fallback, that fallback remains an owning deployment/scene-policy decision rather than a general reflex-layer entitlement.

## Scene escalation fails conservatively

Possible movement from a narrower/private context to a broader/group context is safety-significant.

The attention layer may emit a conservative escalation flag, but only RelaySCN and RelayCTX can complete the authoritative scene and packing decisions.

Until they do, no attention result may authorize use of private context in a broader audience.

Failure to classify the escalation never becomes evidence that no escalation occurred.

## Content boundary

The attention process may need to inspect raw incoming input in runtime-private memory in order to score it.

Its outward artifacts remain bounded decision classes, scores/bands, opaque references, and content-free advisory state.

Default diagnostics must not expose:

- raw input bodies;
- CTX-OVL or semantic-sidecar bodies;
- memory bodies;
- private relationship content;
- free-form model rationale;
- raw participant/source identifiers when a safer opaque identifier suffices;
- reversible content encodings or content hashes used as public fingerprints.

Runtime-private access required for admission does not make that content suitable for logs, generated indexes, or public UI diagnostics.

## Public diagnostics are content-free

Default attention diagnostics may expose bounded values such as:

- decision class;
- candidate count;
- hold/select/reject counts;
- score or urgency band rather than raw rationale;
- trusted-versus-inferred signal class;
- possible scene-escalation boolean;
- freshness known/stale/unknown class;
- bounded aggregation count;
- overload/backpressure class;
- reason/validation identifiers.

These diagnostics describe the decision process without becoming another transcript, evidence store, relationship store, or memory index.

## No persistent policy learning from reflex state

Attention state is transient by default.

The layer does not update a character's durable persona, relationship, scene profile, memory, or persistent attention preferences from observed wake outcomes or its own scores.

If RelayLM later adopts character-conditioned durable attention preferences, their source, approval, compilation, lifecycle, and mutation authority must be defined separately.

Until then, transient attention observations cannot silently become character source authority.

## Stable authority flow

```text
source occurrence
  |\
  | `-> governed evidence admission/retention
  |
  `-> target attention/reflex evaluation
        -> reject | hold | select | flag
                    |
                    `-> selected candidate
                          -> RelayRUN
                          -> RelayREL / RelaySCN / RelayEMO / RelayINT
                          -> RelayMEM Retrieval when allowed
                          -> RelayCTX
                          -> compile/backend/output

Attention result never feeds durable Evidence/MEM/REL/SCN/CTX mutation directly.
```

The two branches may refer to the same source occurrence, but their authorities remain independent.

## Stable invariants

- Pre-request turn admission is separate from evidence admission, continuity, and durable memory formation.
- The attention layer owns only bounded `reject`, `hold`, `select`, and advisory `flag` effects.
- `select` creates a normal governed turn; it does not create a privileged response path.
- `reject` does not erase or prohibit governed evidence owned elsewhere.
- `hold` remains bounded/transient and does not become a durable raw-input store.
- Attention scores and flags are not provenance, evidence confidence, memory strength, relationship authority, scene authority, or disclosure permission.
- RelayRUN owns orchestration after admission and does not inherit semantic wake authority.
- RelayINT owns admitted-turn interpretation.
- RelaySCN owns authoritative scene classification and scene policy.
- RelayCTX owns working/context state; the attention layer never mutates CTX-OVL.
- Any RelayCTX input exposed to the attention layer is bounded and content-free under RelayCTX authority.
- RelayMEM/RelaySLP retain assessment, formation, retrieval, lifecycle, identity, persistence, and mutation authority.
- Bounded aggregation preserves member/source distinctions and is not semantic or memory consolidation.
- Trusted source metadata remains distinct from classifier inference.
- Possible scene escalation can only increase caution until owning scene/context gates run.
- Default diagnostics are content-free.
- Attention state does not silently become persistent character policy.
- Attention-layer failure cannot delete evidence or weaken normal safety/privacy gates.
- Current implementation status is never inferred from this target architecture page.

## Non-goals

This architecture does not define:

- current RelayATN implementation or enablement;
- exact SourceEvent or governed-ingress schemas;
- exact attention score, threshold, classifier, embedding, or model design;
- exact hold queues, expiry, rate limits, or scheduler cadence;
- exact RelayCTX reflex snapshot or catch-up protocol;
- multi-user partition or scene-epoch schemas;
- persistent attention-policy compilation;
- evidence admission/retention policy;
- scene classification;
- intent/reference semantics;
- memory formation, retrieval, lifecycle, or mutation;
- ASR/audio capture;
- TTS/avatar output or interruption execution;
- runtime checkpoint/recovery details;
- repository-level implementation sequencing.

## Related architecture

- [RelayLM Pipeline Responsibilities](../pipeline-responsibilities.md)
- [Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [RelayATN Reflex Layer Design](../relayatn_reflex_layer_design.md)
- [ADR: RelayATN pre-request authority separation](../../adr/relayatn_pre_request_authority_separation.md)
- [RelayCTX Context Assembly](../context/context-assembly.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Reference and Intent Architecture](../analyzers/reference-and-intent.md)
- [Memory Formation Architecture](../memory/formation.md)
