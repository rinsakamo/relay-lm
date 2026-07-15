---
relaylm_doc_type: evidence
relaylm_authority: relayatn_ctx_ovl_boundary_review_record
relaylm_status: historical
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - the RelayATN or CTX-OVL boundary changes materially
  - governed ingress or SourceEvent ownership is accepted
  - multi-user scene or participant fencing changes
relaylm_not_authoritative_for:
  - accepted RelayATN architecture
  - accepted CTX-OVL architecture
  - exact runtime order, schema, or implementation sequence
  - current runtime behavior or implementation completion
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 5d60433713574c042afe5ceab15b865a48824ae5
relaylm_source_pr: 586
relaylm_recorded_on: 2026-07-15
relaylm_related_proposals:
  - ../../proposals/subjective-memory-formation-consolidation-and-retrieval.md
relaylm_related_authority:
  - ../../architecture/relayatn_reflex_layer_design.md
  - ../../architecture/pipeline_responsibility_design.md
  - ../../architecture/safe_soul_scene_ctx_compile_chain.md
  - ../../architecture/context_packing_design.md
  - ../../architecture/relaymem_slp_execution_design.md
---

# RelayATN / CTX-OVL Boundary Review

## Status and scope

This record reviews the design input `relayatn_ctx_ovl_boundary_proposal.txt` against:

- PR #586 head `707d81523b9eec8469f0e1a23f2842bd6da514dd`;
- current `main` at `5d60433713574c042afe5ceab15b865a48824ae5`;
- the current RelayATN, RelayCTX, RelaySCN, RelaySLP, and RelayMEM ownership documents.

The input is treated as design evidence, not accepted authority. This record does not amend the authoritative RelayATN architecture document and does not authorize implementation.

## Overall result

The proposed separation is **sound after bounded revisions**.

The central ownership model is retained:

```text
RelayATN
  pre-request reject / hold / select / content-free flag only

RelayCTX / CTX-OVL
  admitted-request short-term continuity selection and non-durable overlay state

RelaySCN
  authoritative scene classification and scene policy

RelaySLP
  deferred assessment, relation decision, and subjective formation

RelayMEM
  durable canonical state, lifecycle, confidence, and persistence authority
```

The main corrections are:

1. RelayATN still observes raw incoming candidates for admission scoring. It consumes only a content-free RelayCTX Reflex Snapshot **for CTX-OVL-derived session state**.
2. Turn-rejected governed SourceEvents are eligible for bounded catch-up consideration; they are not automatically converted into CTX-OVL semantic candidates.
3. Catch-up must preserve the canonical semantic pipeline. RelayCTX may select and pack bounded unassessed governed evidence, but it must not reparse rejected raw text into relationship, scene, affect, intent, or memory authority.
4. Unknown participant evidence goes to quarantine, not the shared-scene partition.
5. RelayATN may flag possible private-to-group escalation. RelaySCN classifies the scene, and RelayCTX enforces the pre-pack quarantine/epoch fence.
6. The governed SourceEvent envelope, ingress sequence, evidence-admission owner, and pre-node hydration point do not yet exist as accepted contracts and remain prerequisites.

## Accepted design decisions

### RelayATN never writes CTX-OVL

RelayATN must never create, update, retract, collapse, acknowledge, or shadow a CTX-OVL candidate.

It may emit only its existing pre-request decisions and content-free advisory flags. RelayCTX remains the only owner of CTX-OVL mutation paths.

### Turn admission and evidence admission are orthogonal

```text
turn admission
  whether a RelayRUN request shell starts

evidence admission
  whether a governed SourceEvent is retained under consent,
  retention, source-authority, and privacy policy

provisional continuity
  whether retained current-session evidence is selected into
  RelayCTX working state or CTX-OVL

durable formation
  whether RelaySLP and RelayMEM form or update durable memory
```

A RelayATN `reject` means only that no turn starts from that candidate. It must not delete Protected Source Evidence, change evidence-admission results, prohibit later bounded catch-up, or prohibit independent RelaySLP processing.

### Immediate-continuity candidates are not terminal-reject eligible

A candidate identified through deterministic metadata, trusted ingress classification, or RelayATN advisory detection as requiring immediate continuity must not receive a terminal `reject`.

Representative candidate classes include:

- direct address;
- explicit correction or retraction;
- current-state change;
- active question requiring continuity;
- explicit stop, continue, or confirm signal;
- possible participant or scene-scope escalation;
- urgent or safety-relevant input.

The allowed outcome is policy-controlled `select`, bounded `hold`, or a fail-safe escalation path. RelayATN does not authoritatively classify the final intent, scene, relationship, or memory semantics.

### Hold state references governed source identity

When a governed SourceEvent store exists, retained RelayATN hold state should contain:

- opaque SourceEvent IDs;
- expiry;
- content-free reason classes;
- ordering and grouping metadata.

It should not duplicate raw bodies into durable or diagnostic ATN state. RelayATN may still use bounded transient raw buffers for admission scoring as already allowed by its architecture.

### Multi-user CTX-OVL is partitioned

Multi-user enablement requires, at minimum:

```text
shared_scene
participant:<resolved participant>
relationship:<RelayREL-resolved target>
quarantine:<unresolved or conflicting identity/scope>
```

These partitions are a multi-user capability gate, not a requirement that the first trusted 1:1 CTX-OVL implementation carry all group-scene complexity.

### Unknown identity cannot shadow durable personal state

Evidence with missing, stale, or conflicting participant identity:

- enters quarantine only;
- is not group-visible prompt content;
- cannot shadow participant-scoped or REL-scoped durable MEM;
- cannot increase participant-specific confidence;
- cannot create relationship interpretation;
- cannot be promoted through participant or relationship partitions.

### Private-to-group escalation is fail-closed

RelayATN may emit `possible_scope_escalation` or the existing equivalent content-free flag. It must not classify the scene or authorize a downgrade.

Before any group-visible packing:

1. prior private partitions are excluded or quarantined;
2. participant and relationship shadowing is suspended when scope is unresolved;
3. RelaySCN performs authoritative scene classification and disclosure/persistence policy;
4. RelayCTX packs only the partitions permitted by the resolved scene policy and current scene epoch.

The exact component that issues the monotonic scene-epoch identifier remains an open contract. The stable ownership requirement is that RelaySCN owns classification and RelayCTX owns the packing fence.

### RelayATN receives only a content-free CTX-derived snapshot

RelayCTX may publish a bounded read-only projection such as `relayctx.reflex_snapshot.v0` containing only:

- schema and revision identifiers;
- covered ingress sequence or lag class;
- scene epoch;
- unresolved-direct-address, correction, scope-escalation, or identity-conflict booleans;
- bounded counts;
- content-free freshness flags.

It must exclude source text, semantic objects, subjective interpretation, affect content, durable MEM IDs, private REL content, confidence, salience, and sidecar bodies.

This restriction applies to **CTX-derived state**. It does not remove RelayATN's existing need to observe the raw incoming candidate being scored.

### No silent memory authority

RelayATN receives no `silent_select`, `memory_only_select`, CTX-OVL update, or RelaySLP trigger authority. Whether an admitted turn replies or observes without reply remains inside the normal deliberation and response-policy path.

### No Tier 3 sidecar repair

RelayATN Tier 3 may resolve only ambiguous pre-request admission. It must not repair, complete, regenerate, or validate semantic sidecars.

Malformed or absent sidecars preserve visible output and fall back to evidence-only deferred handling or no overlay update.

### No provisional-to-attention feedback loop

Semantic sidecars, CTX-OVL interpretations, hot affect, provisional shadow state, and RelayATN scores must not directly update a resident `attention_profile`, durable MEM confidence, salience, subjective conviction, REL state, or scene policy.

## Revised bounded catch-up model

### Why the original wording is too broad

The input proposed:

```text
rejected governed SourceEvent
  -> RelayCTX semantic and temporal validation
  -> CTX-OVL update
  -> final context compile
```

As written, this would leak semantic parsing into RelayCTX and conflict with the canonical rule that RelayCTX does not reconstruct relationship, scene, affect, intent, or memory authority by reparsing raw user text.

### Accepted two-stage model

```text
governed SourceEvent retained independently of RelayATN
  -> next admitted request
  -> bounded ingress coverage scan
  -> consent / retention / source / identity / scene fences
  -> bounded unassessed recent-evidence selection
  -> normal REL / SCN / EMO / INT / MEM / CTX pipeline
  -> Main LLM response and optional validated sidecar
  -> RelayCTX-owned CTX-OVL update when a valid candidate exists
```

Before semantic validation, catch-up may contribute only:

- governed source references;
- system-owned speaker, time, room, participant, and sequence metadata;
- deterministic source classes;
- bounded source text when the client-authority and scene policy permit it;
- content-free catch-up status.

It may not immediately:

- create a character projection;
- choose a durable MEM shadow target;
- resolve REL identity from text;
- classify final scene or intent;
- increase evidence confidence;
- infer temporal validity beyond system-owned or explicitly encoded metadata.

### Watermark requirements

A single `last_hydrated_seq` is insufficient when events are skipped, delayed, quarantined, or arrive out of order.

The contract should distinguish:

```yaml
ingress_coverage:
  highest_contiguous_examined_seq: 179
  current_ingress_seq: 184
  catch_up_incomplete: true
  scene_epoch: 14
```

Non-contiguous or late events require source-lineage idempotency in addition to the monotonic sequence.

Rules:

- advance coverage only through events actually examined under the applicable scope and epoch;
- never advance past an unexamined gap merely because later events were processed;
- record no raw content in diagnostics;
- on budget exhaustion, leave `catch_up_incomplete: true`;
- replay is an idempotent no-op by SourceEvent identity and source lineage;
- a scene-epoch change invalidates or quarantines incompatible prior coverage.

### Catch-up limits

The exact budgets remain open, but the contract must bound:

- events;
- bytes or tokens;
- wall time;
- age;
- per-participant contribution;
- quarantine capacity;
- maximum lag.

If no later admitted turn occurs, CTX-OVL catch-up does not occur. That is an explicit limitation, not permission for RelayATN to create a silent memory turn.

## Multi-user and scene failure behavior

### Partition rules

- `shared_scene` contains only group-safe scene facts and shared progression.
- `participant:<id>` requires trusted participant identity and speaker lineage.
- `relationship:<target>` requires a RelayREL-resolved target and scene-policy permission.
- `quarantine` is non-shadowing and non-packable until identity and scope are resolved.

Unknown identity must not be placed in `shared_scene` merely to preserve continuity.

### Scope escalation

On a trusted participant-roster change or RelayATN escalation flag:

- old private CTX-OVL content is not packed into the potential group turn;
- the request carries a conservative scope-escalation marker;
- RelaySCN reclassifies the scene;
- RelayCTX applies a new or quarantined scene epoch before packing;
- only group-safe partitions may be selected;
- downgrade is never inferred by RelayATN.

## Required failure behavior

| Failure | Required result |
|---|---|
| SourceEvent body/reference unavailable | no overlay mutation; content-free diagnostic; continue with safe current input |
| evidence retention expired before catch-up | accept loss of provisional continuity; do not synthesize evidence |
| catch-up budget exhausted | stop at bounded coverage; set incomplete; no broad shadow |
| stale or conflicting watermark | revision-fenced no-op or retry outside the visible critical path |
| duplicate or replayed SourceEvent | idempotent no-op |
| missing/conflicting participant identity | quarantine; no participant/REL shadow or packing |
| private-to-group escalation unresolved | block private partitions; fail closed |
| Reflex Snapshot missing or stale | no CTX-derived assumption; use conservative admission policy |
| RelayATN process failure | evidence admission and Protected Source Evidence remain unchanged |
| CTX-OVL eviction or restart loss | short-term continuity may degrade; Protected Source Evidence and durable MEM remain intact |
| malformed semantic sidecar | preserve visible response; no ATN repair; evidence-only fallback or no overlay update |
| RelaySLP acknowledgement race | source-lineage and revision-fenced idempotent reconciliation |

## Exact counterpart changes required in RelayATN Reflex Layer Design

These are **required future changes to the RelayATN-owned architecture document** if the proposal is accepted. They are listed here for review traceability and are not active RelayATN authority.

### Purpose and dual-loop boundary

Add:

> Turn admission, evidence admission, RelayCTX provisional continuity, and RelaySLP/MEM durable formation are orthogonal. RelayATN decides only whether and on what a turn starts.

### Relationship to RelayCTX

Add a dedicated subsection stating:

- RelayATN never writes, retracts, collapses, acknowledges, or shadows CTX-OVL;
- RelayATN may consume only a content-free RelayCTX Reflex Snapshot for CTX-derived session state;
- RelayATN still observes the bounded raw ingress candidate required for admission scoring;
- CTX-OVL and semantic sidecar bodies are forbidden ATN inputs;
- RelayCTX owns catch-up selection and overlay mutation;
- RelayCTX does not grant ATN durable or provisional semantic authority.

### Authority constraints

Extend the `must not` list:

- no CTX-OVL mutation;
- no semantic sidecar repair;
- no temporal, participant, relationship, lifecycle, or shadow-target normalization;
- no MEM confidence, salience, conviction, or lifecycle effect;
- no attention-profile update from provisional state;
- no evidence-admission or Protected Source Evidence retention effect.

### Decision semantics

Clarify:

- `reject` means no RelayRUN turn and no immediate CTX-OVL guarantee;
- `reject` does not delete or de-authorize governed evidence;
- immediate-continuity candidates are not terminal-reject eligible;
- `hold` retains SourceEvent IDs and content-free metadata when the governed source store exists;
- RelayATN receives no silent or memory-only turn verb.

### Self-report freshness

Replace the self-report-only interaction with a bounded session-state freshness rule:

- consume snapshot revisions, ingress coverage, scene epoch, and content-free lag flags;
- never inspect raw CTX-OVL or repair stale state;
- a stale or missing snapshot does not authorize unsafe select or disclosure;
- freshness flags remain advisory.

### Relationship to RelaySCN

Clarify:

- `possible_scope_escalation` tightens caution only;
- RelaySCN retains authoritative classification and downgrade;
- RelayCTX enforces the private-partition packing fence;
- RelayATN does not issue scene epochs or disclosure policy.

### Content and hold boundary

Clarify:

- transient raw input remains bounded and non-durable for scoring;
- retained hold state references governed SourceEvent IDs rather than duplicating bodies;
- candidate IDs remain opaque and non-reversible;
- SourceEvent storage and evidence admission are external prerequisites.

### Tier 3 boundary

Add:

> Tier 3 is an admission fallback only. It is not a semantic sidecar, CTX-OVL, RelaySCN, RelayINT, RelaySLP, or RelayMEM fallback.

### Failure behavior

Add:

- ATN failure never changes evidence-admission or Protected Source Evidence outcomes;
- unavailable/stale Reflex Snapshot falls back to conservative admission without CTX interpretation;
- held SourceEvent expiry is explicit and must not synthesize missing evidence;
- private/group ambiguity fails closed.

### Preconditions

Append:

```text
P6  governed SourceEvent identity, evidence admission, consent, retention,
    and source-authority ownership are contractually defined
P7  held SourceEvent IDs have bounded availability and expiry semantics
P8  multi-user CTX-OVL has participant, room, scene, and relationship fencing
P9  turn-rejected governed evidence has an explicit bounded catch-up or
    accepted no-provisional-continuity rule
P10 a content-free RelayCTX Reflex Snapshot contract exists
P11 ingress coverage and source-lineage replay rules are monotonic,
    revision-fenced, and idempotent
P12 private-to-group escalation blocks private packing until RelaySCN
    classification and a compatible scene epoch
P13 identity conflicts fail closed to quarantine and cannot authorize shadow
```

## Required counterpart contracts outside PR #586

Acceptance would require separate owning documents for:

1. governed SourceEvent envelope and evidence-admission ownership;
2. ingress sequence, coverage watermark, replay, retention, and out-of-order semantics;
3. RelayCTX catch-up hydration and selected-recent-evidence schema;
4. CTX-OVL multi-user partition and quarantine schema;
5. RelayCTX Reflex Snapshot schema;
6. scene epoch issuance and RelaySCN-to-RelayCTX packing-fence handoff;
7. RelayATN hold record and decision semantics;
8. RelaySLP source-lineage acknowledgement.

PR #586 may name these required contracts but must not define their exact production schemas as accepted authority.

## Remaining open decisions

1. Which component issues and persists the monotonic ingress sequence.
2. Which component invokes the RelayCTX-owned pre-node catch-up hydration and where it appears in canonical runtime order.
3. Whether bounded raw governed events may be exposed to RelaySCN/RelayINT before RelayCTX Repack, or whether a separate typed recent-evidence projection is required.
4. Exact event/byte/time/age and per-participant catch-up budgets.
5. Contiguous coverage versus late-event lineage representation.
6. Scene-epoch issuer and restart persistence.
7. Quarantine TTL, overflow, and inspection policy.
8. Whether relationship partitions exist in the first multi-user release or follow participant partitioning.
9. Exact immediate-continuity detection inputs and false-positive policy.
10. Reflex Snapshot freshness and failure thresholds.
11. Whether evidence-authorized rejected events may trigger RelaySLP independently when no later admitted turn occurs.
12. Privacy and retention policy for SourceEvent bodies used by catch-up.

## Conclusion

RelayATN and CTX-OVL may be integrated only through a narrow, directional boundary:

```text
raw ingress candidate
  -> RelayATN admission decision

governed retained SourceEvent
  -> bounded RelayCTX catch-up selection on a later admitted request

CTX-OVL
  -> content-free RelayCTX Reflex Snapshot
  -> RelayATN advisory freshness and attention flags

RelayATN
  -/-> CTX-OVL mutation
  -/-> semantic sidecar repair
  -/-> durable memory authority
```

This preserves RelayATN as pre-request admission, CTX-OVL as RelayCTX-owned non-durable continuity, RelaySCN as scene authority, and RelaySLP/MEM as the only durable interpretation and persistence path.
