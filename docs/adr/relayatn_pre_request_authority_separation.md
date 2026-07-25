---
relaylm_doc_type: adr
relaylm_authority: decision_to_separate_relayatn_turn_admission_from_evidence_context_and_memory_authority
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - the RelayATN charter is superseded or folded into another component
  - pre-request turn admission ownership changes
  - evidence admission, RelayCTX working-state, or durable-memory authority is reassigned
relaylm_not_authoritative_for:
  - current runtime implementation status
  - RelayATN component-name registration
  - implementation phase sequencing
  - governed SourceEvent, ingress, catch-up, CTX-OVL, or Reflex Snapshot exact contracts
  - multi-user partition, scene-epoch, attention-profile, or semantic-sidecar schemas
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# ADR: RelayATN pre-request authority separation

## Status

Accepted as target architecture. Implementation remains gated and pending.

`RelayATN` remains a provisional working name. This ADR accepts the authority boundary, not the final component vocabulary or an implementation plan.

## Context

Continuous-input environments need a resident decision before a normal RelayRUN request shell exists:

```text
should anything wake now?
which competing input deserves a turn?
```

That decision is semantically meaningful but intentionally narrow. It has a different error cost from evidence retention, current-session context, scene classification, response intent, and durable memory formation.

Combining these authorities would create unsafe or ambiguous failure modes:

- rejecting a reply candidate could erase governed evidence;
- a cheap resident classifier could mutate RelayCTX working state or durable memory;
- admission scores could become confidence, salience, or relationship authority;
- raw CTX-OVL or memory content could leak into a pre-request process;
- scene-change detection could become scene classification or disclosure permission;
- catch-up and multi-user isolation contracts could be defined by the wrong owner.

## Decision

RelayLM will keep pre-request turn admission separate from evidence, context, scene, intent, and memory authorities.

The fixed ownership boundary is:

```text
RelayATN
  owns pre-request turn admission only
  -> reject / hold / select / content-free flag

Evidence-admission path
  owns consent, retention, source authority, and governed evidence

RelayCTX
  owns current-request context and current-session working state

RelaySCN
  owns authoritative scene classification and scene policy

RelayINT
  owns intent and response-mode decisions for an admitted turn

RelaySLP / RelayMEM
  own assessment, subjective formation, relation, lifecycle,
  canonical identity, persistence, strength, and durable retrieval authority
```

The following invariants are accepted:

1. Turn admission, evidence admission, provisional continuity, and durable memory formation are orthogonal decisions.
2. RelayATN never writes, retracts, collapses, acknowledges, evicts, or otherwise mutates RelayCTX working state or CTX-OVL.
3. RelayATN receives no durable-memory disclosure, relation, lifecycle, canonical-identity, confidence, salience, or persistence authority.
4. CTX-derived input exposed to RelayATN must be content-free and conform to an owning RelayCTX contract.
5. RelayATN may detect possible scene escalation but does not classify the scene, infer a downgrade, or relax disclosure and packing fences.
6. RelayATN Tier 3 cannot repair semantic sidecars, create provisional-memory candidates, or substitute for the normal admitted-turn pipeline.
7. RelayATN scores and flags remain transient admission signals and cannot become evidence confidence, MEM strength, CTX-OVL interpretation, or persistent attention policy.
8. RelayATN failure cannot erase or rewrite evidence owned elsewhere.
9. Exact SourceEvent, catch-up, Reflex Snapshot, multi-user partition, scene-epoch, and persistent attention-profile contracts remain separate owning decisions.

## Consequences

### Positive

- Cheap resident models can reduce unnecessary wake-ups without gaining disclosure or persistence authority.
- A missed reply and a lost observation remain distinct failure classes.
- RelayCTX, RelaySCN, RelayINT, RelaySLP, and RelayMEM retain clear ownership.
- CTX-OVL may evolve without making RelayATN a short-term memory subsystem.
- Multi-user privacy and scene escalation can fail closed in their owning contracts.
- Exact schemas can evolve independently while preserving a stable cross-component boundary.

### Costs

- Governed ingress, catch-up, content-free CTX projection, and multi-user isolation require separate contracts.
- Some turn-rejected evidence may not affect provisional continuity until an owning RelayCTX path processes it.
- RelayATN cannot use raw durable-memory or CTX-OVL content to improve admission accuracy.
- Validation must cover authority leakage in addition to latency and wake quality.

## Rejected alternatives

### Put pre-request admission inside RelayRUN

Rejected because RelayRUN owns orchestration and recovery, not semantic wake judgment, and a request shell does not yet exist when the admission decision is needed.

### Extend RelayINT into a resident pre-turn component

Rejected because RelayINT owns intent and response-mode decisions inside an admitted turn. Admission and intent remain a cleaner seam than a structural rewrite.

### Extend RelaySCN to own continuous admission

Rejected because scene classification and policy are not the same as resident attention selection. RelayATN may report a possible change, but RelaySCN remains authoritative.

### Let RelayATN write CTX-OVL for rejected inputs

Rejected because this would make a pre-request classifier a provisional-context mutation authority and bypass the normal interpretation and validation pipeline.

### Let RelayATN inspect raw CTX-OVL or durable MEM

Rejected because it expands content exposure, creates disclosure risk, and encourages admission scores to become memory authority.

### Define exact catch-up and multi-user schemas in the RelayATN architecture

Rejected because those contracts belong to governed ingress, RelayCTX, and scene/scope owners. RelayATN records only the required non-write and content-free boundaries.

## Fixed boundaries

- RelayATN owns only pre-request `reject`, `hold`, `select`, and content-free `flag` decisions.
- RelayATN does not own evidence admission.
- RelayATN never mutates RelayCTX working state or CTX-OVL.
- RelayATN receives no durable-memory authority.
- CTX-derived RelayATN input is content-free.
- Scene escalation detection cannot relax scene policy.
- Failure of RelayATN cannot delete governed evidence.
- Implementation remains gated by the Project Execution Plan and the RelayATN design preconditions.

## Related architecture

- [RelayATN Reflex Layer Design](../architecture/relayatn_reflex_layer_design.md)
- [Pipeline Responsibilities](../architecture/pipeline-responsibilities.md)
- [RelayRUN Runtime Checkpoint Design](../architecture/relayrun_runtime_checkpoint_design.md)
- [RelayINT MVP Design](../architecture/relayint_mvp_design.md)
- [RelaySCN MVP Scene Policy](../architecture/relayscn_mvp_scene_policy.md)
- [Project Execution Plan](../architecture/project_execution_plan.md)
