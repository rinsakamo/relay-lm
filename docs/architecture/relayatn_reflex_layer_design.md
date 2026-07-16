---
relaylm_doc_type: architecture
relaylm_authority: relayatn_reflex_layer_target_boundary
relaylm_status: target
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - reflex-layer component naming or charter decisions
  - continuous-input / multi-user admission design decisions
  - RelayRUN pre-request boundary decisions
  - RelayCTX-to-RelayATN content-free input boundary decisions
  - evidence-admission boundary decisions that affect pre-request admission
  - O3 always-on operation scoping
relaylm_not_authoritative_for:
  - current implementation status
  - governed SourceEvent exact schema or ingress sequencing contract
  - evidence admission, retention, consent, or source authority
  - RelayCTX Session Evidence Overlay exact schema, catch-up state machine, or partition contract
  - RelayCTX Reflex Snapshot exact schema
  - scene-epoch identifier issuance or transition protocol
  - persistent character-conditioned attention-policy compilation
  - RelayRUN checkpoint/recovery contract
  - RelayINT intra-turn intent ownership
  - RelaySCN scene classification ownership
  - RelaySLP or RelayMEM formation, consolidation, retrieval, lifecycle, or strength semantics
  - v0.1 release scope and committed sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/relayatn_pre_request_authority_separation.md
  - relayrun_runtime_checkpoint_design.md
  - relayint_mvp_design.md
  - relayscn_mvp_scene_policy.md
  - pipeline_responsibility_design.md
  - project_execution_plan.md
  - o3_always_on_local_scheduler.md
  - soul_lab_runtime_mvp.md
  - ../PROJECT_STATUS.md
---
# RelayATN Reflex Layer Design (Target)

Last reviewed: 2026-07-15 JST

## Status of this document

This is a **target design boundary** for a component that does not exist. Its stable authority separation is fixed by [ADR: RelayATN pre-request authority separation](../adr/relayatn_pre_request_authority_separation.md). It authorizes no implementation, changes no current contracts, and defers current-state claims to [Project Status](../PROJECT_STATUS.md).

Implementation is explicitly sequenced after voice-out (SOUL Lab Runtime MVP); see [Project Execution Plan](project_execution_plan.md). `RelayATN` (Relay Attention) remains a provisional working name.

The open subjective-memory and RelayCTX Session Evidence Overlay (`CTX-OVL`) work is a design input, not accepted authority for this document. This document owns only RelayATN's stable side of the boundary:

```text
turn admission
  != evidence admission
  != RelayCTX provisional continuity
  != durable memory formation
```

Exact governed-ingress, catch-up, CTX-OVL, multi-user partition, scene-epoch, and content-free CTX snapshot contracts belong to their owning future documents.

## Purpose

RelayATN is a resident pre-request reflex layer for continuous-input environments such as streaming chat, group voice, and always-listening contexts. It decides **whether and on what to start a turn** before a RelayRUN request shell exists.

RelayATN does not decide:

- whether an observation becomes governed evidence;
- whether governed evidence contributes to RelayCTX working state or CTX-OVL;
- how provisional state affects durable Retrieval candidates;
- how a scene is authoritatively classified;
- what response mode an admitted turn uses;
- whether evidence forms or changes durable MEM.

## Motivating limits of the current single-call architecture

```text
L1  Session-state staleness
      State compiled for the previous turn may become stale as new
      inputs, held candidates, participant changes, or scope changes
      arrive between Main-LLM calls.

L2  Nobody watches between turns
      Continuous input needs a bounded decision outside the normal turn:
      should anything wake, and which candidate deserves the turn?
```

## Dual-loop and evidence structure

```text
Reflex loop (RelayATN)              Deliberation loop (existing)
  resident, CPU-side                  turn-based, GPU-side
  content-light                       full pipeline + Main LLM
  continuous cadence                  one call per admitted turn
  reject / hold / select / flag       full semantic authority
```

The deliberation loop remains the existing canonical pipeline. Once a candidate is admitted, semantic interpretation, scene classification, context selection, safety, provisional continuity, memory, and response decisions remain inside their existing owners.

Continuous ingress also has an independent governed-evidence path:

```text
observed input
  ├─ evidence-admission path
  │    -> consent / retention / source-authority decision
  │    -> Protected Source Evidence when authorized
  │
  └─ RelayATN turn-admission path
       -> reject / hold / select / flag
       -> RelayRUN only when selected
```

Turn admission does not authorize, prohibit, create, rewrite, or delete governed evidence.

## Position relative to existing components

### RelayRUN

[RelayRUN Runtime Checkpoint Design](relayrun_runtime_checkpoint_design.md) owns orchestration, checkpoint, recovery, and idempotency, and must not make semantic decisions. RelayATN operates before the request shell exists and is orchestrated by, not owned by, the runtime.

Once RelayATN selects a candidate, RelayRUN owns the normal turn exactly as today. RelayRUN may record only content-free admission summaries.

### RelayINT

```text
RelayATN decides IF and ON WHAT a turn starts.
RelayINT decides WHAT TO DO with the admitted turn input.
```

RelayATN must not perform full intent classification, resolve references, choose `observe_without_reply`, or select response modes. It receives no separate `silent_select` or memory-only-turn verb.

### RelaySCN

RelaySCN retains authoritative scene classification and scene-policy ownership. RelayATN may perform cheap scene-change detection and emit a content-free escalation signal.

- RelayATN may flag possible escalation.
- RelaySCN classifies the admitted scene.
- RelayCTX applies the owning packing and disclosure fence.
- RelayATN never infers a downgrade.
- RelayATN never authorizes private-to-group disclosure or partition migration.

The owner that issues or rotates a scene-epoch identifier remains an open contract decision. Possible escalation must not relax policy before authoritative reclassification and packing fences complete.

### RelayCTX and CTX-OVL

CTX-OVL is RelayCTX-owned current-session working state. RelayATN is outside its semantic interpretation and mutation path.

RelayATN must never:

- write, retract, collapse, acknowledge, evict, or mutate CTX-OVL;
- decide which durable MEM candidate is boosted or shadowed;
- consume raw semantic-sidecar or CTX-OVL candidate content;
- repair or regenerate a semantic sidecar;
- normalize temporal, participant, relationship, lifecycle, or scene facets.

RelayATN may consume only bounded, content-free state conforming to a future RelayCTX-owned contract. It may expose admission-relevant classes, counts, revision/freshness state, and conservative scope-change signals. It must not expose raw user content, provisional interpretation, private REL content, durable MEM identities, evidence confidence, salience, or reversible identifiers.

Turn-rejected governed evidence may affect a later admitted turn only through a future RelayCTX-owned catch-up contract. That contract must preserve the normal interpretation path and must not hydrate rejected raw text directly into CTX-OVL as authoritative semantic state:

```text
governed recent evidence
  -> bounded coverage and identity / consent / scene fences
  -> bounded unassessed evidence selection
  -> normal REL / SCN / EMO / INT / MEM / CTX pipeline
  -> validated sidecar or deterministic owning operation
  -> optional CTX-OVL update
```

Exact cursors, sequence fields, gap handling, truncation, replay, and idempotency belong to ingress and RelayCTX contracts. RelayATN neither performs catch-up nor advances coverage.

### Evidence admission, RelaySLP, and RelayMEM

Evidence admission owns consent, retention, source authority, source identity, speaker, timing, and correction origin.

RelaySLP and RelayMEM own Shared Assessment, subjective formation, existing-MEM relation decisions, evidence confidence, lifecycle, canonical identity, persistence, and durable Retrieval authority.

RelayATN scores and flags can never become evidence confidence, MEM salience, subjective conviction, CTX-OVL interpretation, or durable relation authority.

### O3 and the bounded scheduler

The O3 always-on lane in [Project Execution Plan](project_execution_plan.md) is the natural home for RelayATN supervision and lifecycle. Admitted user turns must be able to preempt SLP or other off-turn work. RelayATN never runs on the Main-LLM GPU.

## Responsibilities

RelayATN may own:

- attention scoring over continuous input;
- wake decision;
- interruption-value judgment as an advisory candidate or flag;
- bounded input aggregation for one response candidate;
- coarse, transient urgency or affect estimation used only for admission;
- scene-change detection signals, not classification;
- content-free session-state freshness detection;
- bounded backpressure, rate-limited hold, and overload admission behavior under an owning policy contract.

## Authority constraints

RelayATN's permitted verbs are exactly:

```text
reject   do not start a turn for the candidate
hold     defer the candidate using bounded transient references
select   admit the candidate as a normal turn
flag     attach content-free advisory signals
```

RelayATN flags may cause downstream owners to re-check their own inputs or choose conservative defaults. They never override RelaySCN, RelayINT, RelayCTX, RelaySLP, RelayMEM, RelayEMO, disclosure, or safety decisions.

RelayATN must not:

- authorize disclosure of memory;
- own evidence admission or delete governed evidence;
- mutate MEM, SOUL, REL, SCN, RelayCTX working state, or CTX-OVL;
- emit persistence candidates or durable relation decisions;
- generate user-visible text;
- bypass, reorder, or pre-empt a safety gate;
- perform interruption side effects such as stopping audio or cancelling generation;
- learn or mutate persistent attention policy from sidecars, CTX-OVL, current EMO, or its own scores.

A character-conditioned persistent attention profile is a separate proposal or architecture decision and is not adopted here.

## Decision semantics and continuity classes

### `select`

Creates a normal RelayRUN request shell. All later context, scene, sidecar, CTX-OVL, memory, and response behavior remains owned by the admitted-turn pipeline.

### `hold`

Retains bounded opaque references and content-free scheduling metadata. It must not create a second durable raw-input store. The exact SourceEvent reference envelope belongs to the ingress contract.

### `reject`

Means only that RelayATN does not start a turn. It does not change evidence admission, retention, later RelayCTX processing eligibility, or RelaySLP processing.

### Hard non-reject classes

The following require a trusted owning signal and are not eligible for ordinary reject:

- authenticated control signals;
- trusted direct-address metadata;
- explicit continuation of an active transaction or protocol state.

They remain subject to safety shutdown, invalid scope, and system-wide overload policy owned outside RelayATN.

### Soft non-reject candidates

The following classifier detections are important but not authoritative:

- possible correction or retraction;
- urgency estimate;
- possible current-state change;
- possible direct address inferred only from content;
- possible scene escalation.

They are not forced to `select`. The owning policy may use rate-limited `hold`, aggregation, prioritization, or explicit backpressure. They must not cause unbounded wake amplification in multi-user scenes.

## Input aggregation boundary

RelayATN aggregation exists only to reduce redundant wake-ups and construct one bounded response candidate. It is not evidence consolidation, CTX-OVL reconciliation, or MEM consolidation.

Aggregation must preserve or reference enough source identity for downstream owners to reconstruct distinctions. At minimum it preserves:

- member SourceEvent references;
- speaker identity when known;
- event order;
- trusted address-target metadata when available.

RelayATN may emit a content-free disagreement-present flag. It must not authoritatively normalize polarity, modality, temporal validity, relationship scope, scene scope, or evidence independence.

Aggregation must not rewrite Protected Source Evidence, reconcile CTX-OVL, declare independent corroboration, decide semantic-MEM identity, emit a durable relation, or reuse a response-grouping threshold as a memory-consolidation threshold.

## Implementation tiers

```text
Tier 1  heuristics / regex / rate rules            deterministic
Tier 2  embedding model + light classifier         CPU
Tier 3  small LLM fallback                         rare ambiguous cases
```

Tier 3 inputs and outputs remain bounded. Tier 3 may output only RelayATN verbs and flags. It may not repair sidecars, create CTX-OVL candidates, resolve identity from durable memory, normalize semantic facets, or choose durable-MEM boosts, shadows, or relations.

## Session-state freshness

The Main-LLM structured self-report remains owned by the Main LLM and RelayCTX Unpack. RelayATN never writes it.

RelayATN may perform a read-only freshness check using only content-free state exposed by owners, such as revision comparisons, bounded counts, coverage completeness, and conservative scene-change status.

The exact snapshot and catch-up cursor are future contracts. RelayATN may emit only stale, unknown, or advisory flags. It must not infer missing semantic content, repair CTX state, or block a turn solely because freshness information is unavailable.

Missing, invalid, or incomplete freshness input resolves to `unknown`, not a false claim of freshness.

## Content boundary

RelayATN observes raw incoming input because it must score candidates. Its outputs remain decision classes, scores, opaque transient references, and content-free flags.

Default traces and diagnostics must not contain input bodies, sidecar or CTX-OVL bodies, private REL content, raw scoped identifiers, source-lineage fingerprints, or reversible content encodings.

Retained reflex state is bounded, transient, and non-durable. RelayATN is not a memory store, evidence store, or CTX-OVL replica. Loss of RelayATN state must not delete evidence owned elsewhere.

## Failure behavior

- RelayATN failure must not break ordinary turn-based operation.
- Every-input-admitted fallback is allowed only when RelaySCN established a trusted 1:1 scene before failure and the channel is not multi-source.
- Unknown, stale, broadcast-class, or multi-source scenes fail closed to no admission.
- Failure must not authorize, prohibit, erase, or rewrite evidence capture.
- Failure must not mutate or clear RelayCTX working state or CTX-OVL.
- Tier 3 timeout resolves as `hold`, never `select`.
- Freshness-input failure resolves to `unknown`; it does not block a turn or authorize downgrade.
- Aggregation failure resolves to separate candidates or bounded `hold`; member references are not silently dropped.
- Hold-state loss may lose scheduling state but not governed evidence.
- Missing participant identity cannot be repaired from durable memory by RelayATN.
- Possible private-to-group escalation tightens caution until RelaySCN and RelayCTX complete their owning work.
- RelayCTX catch-up failure is not repaired by RelayATN.

## Validation requirements

Measure direct-address and control-signal misses, unnecessary wakes, soft-candidate backpressure, false aggregation, hold expiry, escalation recall, freshness accuracy, CPU p50/p95, resident RAM, GPU interference, and trace leakage.

The structural target is zero for:

```text
Protected Source Evidence lost because RelayATN rejected a turn
RelayATN mutation of RelayCTX working state or CTX-OVL
Raw sidecar or CTX-OVL candidate content exposed to RelayATN
RelayATN selection of a durable-MEM boost or shadow target
Tier 3 repair or regeneration of a semantic sidecar
Authenticated hard non-reject signal treated as ordinary reject
Aggregation member SourceEvent reference silently dropped
RelayATN declaration of evidence independence
RelayATN durable relation or consolidation decision
RelayATN score directly updating CTX-OVL interpretation or MEM strength
Unknown-participant input shadowing participant- or REL-scoped durable MEM
Private context packed group-visible before owning fences
```

Exact gap, cursor, replay, partition, and scene-epoch validation belongs to later owning contract PRs.

## Non-goals

RelayATN does not own multi-user policy content, SourceEvent schema, evidence admission, CTX-OVL schema, catch-up state machine, partition model, scene-epoch issuance, semantic-sidecar validation, temporal normalization, Shared Assessment, memory formation, consolidation, Retrieval, persistent attention policy, ASR, audio capture, speech execution, disclosure matrices, or REL scaling.

It does not replace RelayINT, RelayCTX, RelaySCN, RelaySLP, RelayMEM, or RelayRUN and is not in v0.1 scope or a currently committed lane.

## Implementation-plan placement

RelayATN may enter the execution plan only as a **post-v0.1 / post-voice-out candidate lane** under O3. The first change is planning-only and authorizes no runtime work.

```text
ATN-0  planning registration only
ATN-1  voice-out and latency measurement prerequisites
ATN-2  contract-only admission and failure boundaries
ATN-3  disabled deterministic Tier-1 skeleton
ATN-4  trusted local/dev experimental admission
ATN-5  opt-in CPU classifier / small-LLM experiments
```

Exact catch-up, content-free CTX snapshot, multi-user CTX-OVL partition, scene-epoch, and persistent attention-policy contracts are separate follow-up PRs.

## Preconditions before implementation

```text
P1  voice-out (SOUL Lab Runtime MVP) functional
P2  latency baseline measured through content-free per-node and first-audio trace
P3  component name registered in canonical vocabulary
    or an explicit decision made to fold the charter elsewhere
P4  single-primary-user assumption documented in current contracts
P5  execution plan lists RelayATN only as a gated post-v0.1 / O3 candidate
    before any implementation PR is cut
P6  turn admission and evidence admission are contractually separated
P7  RelayATN receives only future contract-defined content-free CTX state
P8  RelayCTX-owned catch-up preserves the normal interpretation pipeline
    and defines bounded gap and replay behavior
P9  multi-user identity, room, scene, quarantine, and packing fences exist
P10 hard/soft continuity classes, rate limits, aggregation, backpressure,
    and overload behavior are defined
P11 failure fallback retains strict trusted-1:1 prerequisites
P12 cross-boundary invariants are covered by machine-readable tests
```

## Design decision record

Four placements were considered:

1. **Amend RelayRUN** — rejected because it violates RelayRUN's no-semantic-decisions principle.
2. **New component, RelayATN** — adopted because it preserves existing charters and expresses the narrow verb boundary.
3. **Extend RelayINT to pre-turn** — rejected because RelayINT is an in-turn node and admission versus intent is the cleaner seam.
4. **Extend RelaySCN to own admission** — rejected because scene classification and policy are not continuous attention selection.

CTX-OVL and subjective-memory work do not change this placement decision:

```text
RelayATN  owns pre-request turn admission only.
RelayCTX  owns current-session context and CTX-OVL.
RelaySCN  owns authoritative scene classification and policy.
RelaySLP  owns deferred assessment and subjective formation.
RelayMEM  owns durable governed memory authority.
```

Turn admission, evidence admission, provisional continuity, and durable reflection have different error costs and remain separate authorities.
