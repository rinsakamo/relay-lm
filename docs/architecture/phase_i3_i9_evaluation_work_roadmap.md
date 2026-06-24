---
relaylm_doc_type: implementation_plan
relaylm_authority: planned_post_i3_work_and_evaluation_sequence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - a Phase I-3 through I-9 slice begins or lands
  - SOUL Lab real conversation integration changes state
  - I1-G or worker-service sequencing changes
  - an evaluation gate changes its completion claim
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact mutation schemas
  - exact queue or worker contracts
  - RelaySOUL revision schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - memory_lifecycle_design.md
---
# Phase I-3 through I-9 Evaluation and Work Roadmap

## Purpose

This document records the planned work sequence needed to evaluate RelayLM as a text-first local character product after Phase I-2.

The current active implementation boundary remains Phase I-3 auditable Correct. Phase I-4 through I-9 are planned product slices whose exact schemas and contracts must be defined in dedicated documents before implementation.

The roadmap combines three tracks:

```text
Memory governance
  -> Correct, Forget, Pin, Merge, Held review, Secondary MEM, RelaySOUL

SOUL Lab experience
  -> real Home conversation and observable memory lifecycle

Operations
  -> pre-enqueue durability, queue selection, supervision, always-on operation
```

The product should be evaluated incrementally. Implementation must not wait until I-9 before real use begins.

## Target product loop

```text
SOUL Lab Home conversation
  -> RelayLM managed request
  -> existing M2 retrieval and RelayCTX injection
  -> visible response
  -> durable deferred memory processing
  -> Primary MEM formation or held/blocked result
  -> Lab Observation
  -> explicit memory operation when needed
  -> fresh conversation
  -> changed retrieval and response behavior
```

The long-term loop extends this path:

```text
Primary MEM set
  -> Secondary MEM consolidation
  -> stable long-term retrieval
  -> separately governed RelaySOUL proposal
  -> explicit intervention and rollback
```

## Track A: Memory governance phases

### Phase I-3: Auditable Correct

Goal:

> Correct one real observed Primary MEM and prove that a later ordinary retrieval uses the corrected representation.

Work slices:

```text
I-3A  Correct request and preflight contract
I-3B  exact current-memory, character, namespace, and revision validation
I-3C  bounded semantic diff and explicit confirmation identity
I-3D  atomic authoritative update and durable audit receipt
I-3E  Primary page, index, and log convergence
I-3F  SOUL Lab Correct UI integration
I-3G  fresh-conversation M2 / RelayCTX retrieval convergence smoke
```

Completion requires:

- prior representation and provenance remain auditable,
- stale revision and mixed-scope requests fail closed,
- partial page/index/log mutation cannot be exposed as success,
- the browser does not own filesystem paths or memory authority,
- a fresh conversation selects the corrected representation,
- no RelaySOUL mutation occurs.

### Phase I-4: Forget / Hide

Goal:

> Explicitly remove one memory from normal retrieval without destroying auditability.

Preferred semantic boundary:

```text
active
  -> forgotten / hidden / tombstoned
```

Work slices:

```text
I-4A  lifecycle-state and destructive-operation contract
I-4B  exact revision, scope, lineage, and current-state preflight
I-4C  atomic tombstone or hidden-state apply
I-4D  index/log convergence and M2 exclusion
I-4E  SOUL Lab confirmation, refusal, conflict, and receipt UI
I-4F  fresh-conversation exclusion smoke and recovery checks
```

Physical deletion is not the default operation. Any irreversible purge requires a separate future boundary.

### Phase I-5: Pin / Unpin

Goal:

> Let the user raise or restore retrieval priority without changing authority order.

Work slices:

```text
I-5A  pin eligibility and bounded priority contract
I-5B  atomic pin metadata apply and audit receipt
I-5C  unpin convergence to ordinary ranking
I-5D  M2 ranking integration without forced unconditional injection
I-5E  SOUL Lab Pin / Unpin UI
I-5F  ranking, token-budget, scope-isolation, and stale-revision smoke
```

Pinning must not let Primary MEM override Secondary MEM, SOUL, OUTPUT_POLICY, or RELATIONSHIP_ANCHOR.

### Phase I-6: Merge / Supersession

Goal:

> Merge duplicate or sequential Primary memories into one canonical representation while preserving complete lineage.

Work slices:

```text
I-6A  multi-memory eligibility and contradiction preflight
I-6B  bounded merged representation and semantic diff
I-6C  multi-record optimistic concurrency and atomic apply
I-6D  source memories marked superseded without lineage loss
I-6E  index/log and retrieval de-duplication convergence
I-6F  SOUL Lab multi-select and confirmation UI
I-6G  crash, retry, stale-record, and duplicate-retrieval smoke
```

A partial merge must never leave multiple active canonical answers for the same completed operation.

### Phase I-7: Held Apply / Discard

Goal:

> Review exceptional held candidates and explicitly apply, correct-then-apply, or discard them.

Work slices:

```text
I-7A  held-candidate identity, reason, evidence, and expiry contract
I-7B  current policy, character, namespace, and source revalidation
I-7C  Apply path into authoritative Primary MEM
I-7D  Discard path into durable reviewed rejection
I-7E  optional bounded correction before Apply
I-7F  SOUL Lab held-review UI
I-7G  sensitive, contradictory, stale, cross-scope, and replay smoke
```

Held review remains an exception path. Ordinary safe memory formation must not become a mandatory approval queue.

### Phase I-8: Secondary MEM Consolidation

Goal:

> Consolidate related Primary MEM into stable, lineage-backed Secondary MEM suited to long-term retrieval.

Work slices:

```text
I-8A  grouping and consolidation-candidate discovery
I-8B  duplicate, supersession, contradiction, and namespace analysis
I-8C  stable summary, relationship, project, concept, claim, and relation candidates
I-8D  SOUL-anchor validation without SOUL mutation
I-8E  idempotent and rollback-friendly Secondary apply or hold
I-8F  M2 Secondary-priority retrieval integration
I-8G  Lab observation and lineage inspection
I-8H  long-horizon retrieval and contradiction smoke
```

Primary correction and governance operations must be usable before Secondary consolidation becomes the ordinary long-term path.

### Phase I-9: RelaySOUL Proposal / Intervention / Rollback

Goal:

> Derive identity-level proposals from governed memory evidence, require explicit intervention, and support auditable rollback.

Work slices:

```text
I-9A  proposal identity, evidence, scope, and risk contract
I-9B  bounded SOUL semantic diff and protected-anchor validation
I-9C  explicit approval, hold, and discard decisions
I-9D  atomic SOUL revision with prior revision preservation
I-9E  rollback contract and revision convergence
I-9F  Pod / SOUL Intervention real UI integration
I-9G  fresh-conversation behavior validation
I-9H  stale proposal, cross-character, conflict, and rollback smoke
```

RelayMEM and RelaySLP may produce proposal candidates. They must never directly mutate SOUL.

## Track B: SOUL Lab conversation and evaluation experience

Real conversation should begin immediately after Phase I-3 rather than waiting for I-9.

### UI-B0: Real Home Conversation

Goal:

> Use SOUL Lab Home as a minimal real frontend for the existing RelayLM Chat Completions path.

Work slices:

```text
UI-B0A  server-owned character and model-route resolution
UI-B0B  real non-stream request path
UI-B0C  streaming render and completion-state handling
UI-B0D  soft stop, abort, failure, and retry behavior
UI-B0E  character-switch request generation and stale-chunk rejection
UI-B0F  explicit Real runtime / Local preview separation
UI-B0G  new-conversation and session-reset control
UI-B0H  existing M2 / RelayCTX memory-use validation
```

The browser must not create SOUL authority, filesystem paths, memory namespaces, backend credentials, or hidden system prompts.

### UI-B1: Memory lifecycle visibility

Goal:

> Make conversation, memory processing, observation, and intervention understandable as one product loop.

Work slices:

```text
UI-B1A  conversation-to-Lab navigation and latest-run correlation
UI-B1B  not-scheduled / queued / processing / formed / held / blocked / failed states
UI-B1C  operation receipt and current revision display
UI-B1D  fresh-conversation verification entry point
UI-B1E  strict separation of runtime state, observation evidence, and mutation authority
```

### UI-B2: Evaluation scenarios and evidence

Goal:

> Provide repeatable manual and automated scenarios for product evaluation.

Required scenarios:

- incorrect preference corrected and used in a fresh conversation,
- false or unwanted fact forgotten and excluded,
- important commitment pinned without authority inversion,
- duplicate memories merged into one retrieval result,
- held candidate applied or discarded,
- several Primary memories consolidated into Secondary MEM,
- SOUL proposal approved and rolled back,
- character and namespace isolation across every operation.

## Track C: Operational work phases

### O0: Local one-job runner

Goal:

> Process one eligible queued job locally using existing B3, C1-5, C2, and C1-2 authority.

Initial form:

```text
relaylm-worker --once
```

Work slices:

```text
O0A  bounded eligible-record selection
O0B  canonical reread before claim
O0C  unchanged B3 claim and lease fencing
O0D  unchanged C1-5 rehydration and C2 execution
O0E  content-free result projection and exit status
O0F  duplicate, retry-time, terminal, and corruption smoke
```

The browser must not be the worker or queue-selection authority.

### I1-G: Pre-enqueue durability

Goal:

> Close the process-exit window after visible response delivery but before durable protected-source and B2 queue publication.

Work slices must begin with a dedicated contract. The implementation may use an outbox, journal, durable finalization record, or another bounded mechanism, but the exact design must preserve:

- visible response independence,
- source-before-queue ordering,
- dispatch idempotency,
- content separation,
- restart recovery,
- no duplicate logical memory formation.

Suggested work slices:

```text
I1-GA  failure-window and durable-finalization contract
I1-GB  atomic or convergent durable publication boundary
I1-GC  restart replay and duplicate suppression
I1-GD  retention and cleanup
I1-GE  crash-at-every-boundary smoke
```

### O1: Queue scanner and retry scheduler

Goal:

> Select eligible queued records and invoke existing one-job execution without redefining queue or memory semantics.

Work slices:

```text
O1A  secure bounded queue discovery
O1B  deterministic eligibility and retry-time ordering
O1C  canonical reread before B3 claim
O1D  bounded idle and polling behavior
O1E  stale, corrupt, terminal, and concurrent scanner smoke
```

The scanner does not construct protected source, bypass leases, or call M3a-M3h directly.

### O2: Supervised worker service

Goal:

> Run bounded workers with controlled lifecycle and recoverable local operation.

Work slices:

```text
O2A  process lifecycle and configuration contract
O2B  bounded worker concurrency and backpressure
O2C  graceful shutdown and lease-aware cancellation
O2D  health, content-free diagnostics, and operator status
O2E  restart, lock, saturation, and repeated-failure smoke
```

### O3: Always-on local operation

Goal:

> Operate RelayLM, SOUL Lab, and worker processing over extended sessions with predictable startup and recovery.

Work slices:

```text
O3A  local startup and shutdown integration
O3B  static SOUL Lab bundle serving or equivalent packaged launch
O3C  retention, cleanup, and disk-capacity policy
O3D  upgrade and schema-compatibility procedure
O3E  multi-day soak and restart testing
```

TTS, audio, Live2D, ASR, and public remote access are not required for the text-first evaluation gates in this document.

## Recommended implementation order

The memory phase numbering remains linear, but UI and operations should be interleaved to begin real evaluation early.

```text
1. Phase I-3 Correct

2. In parallel after the I-3 contract stabilizes:
     UI-B0 Real Home Conversation
     O0 Local one-job runner

3. Evaluation Gate E1
     conversation -> memory -> observation -> Correct -> fresh conversation

4. Phase I-4 Forget / Hide
5. Phase I-5 Pin / Unpin
6. Phase I-6 Merge / Supersession
7. Phase I-7 Held Apply / Discard
8. UI-B1 memory lifecycle visibility

9. Evaluation Gate E2
     Primary MEM governance and Lab usability

10. I1-G pre-enqueue durability
11. O1 queue scanner / retry scheduler
12. O2 supervised worker service

13. Phase I-8 Secondary MEM consolidation
14. Phase I-9 RelaySOUL proposal / intervention / rollback
15. UI-B2 evaluation scenarios and evidence
16. O3 always-on local operation and soak

17. Evaluation Gate E3
     long-term memory, SOUL evolution, rollback, and operational reliability
```

I1-G and the supervised operation path may be implemented earlier in parallel. They become mandatory before interpreting long-duration memory-formation rates or multi-day consolidation results as reliable product evidence.

## Evaluation gates

### E1: Core RelayLM product hypothesis

Required:

```text
Phase I-3
+ UI-B0
+ O0 or another explicit one-job execution method
```

Proves:

- the user can converse in SOUL Lab,
- a real Primary MEM can form and be observed,
- the user can Correct it,
- a fresh conversation retrieves the corrected representation,
- the effect is distinct from stale frontend conversation history.

### E2: Primary MEM governance product

Required:

```text
Phase I-4 through I-7
+ UI-B1
+ repeatable real conversation use
```

Proves:

- unwanted memory can be excluded,
- important memory can be prioritized safely,
- duplicates can converge,
- held exceptions can be resolved,
- ordinary memory remains autonomous rather than approval-driven,
- Lab intervention is understandable and not excessive user labor.

### E3: Long-term character system

Required:

```text
Phase I-8 and I-9
+ I1-G
+ O1 and O2
+ O3 soak evidence
```

Proves:

- Primary experience can consolidate into stable Secondary MEM,
- long-term retrieval improves rather than accumulates noise,
- identity-level change remains proposal-driven and explicitly approved,
- SOUL revisions can be rolled back,
- restart and always-on operation do not silently lose or duplicate work.

## Measurement guidance

Evaluation should record at least:

- memory formation, held, blocked, failed, and lost-or-unknown counts,
- correction, forgetting, pinning, merge, and held-review outcomes,
- stale revision and mixed-scope refusal counts,
- retrieval selection before and after each operation,
- injected revision and backend-bound inclusion evidence,
- duplicate and contradiction rates,
- Primary-to-Secondary consolidation precision,
- SOUL proposal acceptance, rejection, and rollback outcomes,
- queue age, retry count, worker failure, and restart recovery behavior,
- user effort required to keep the character memory useful.

Raw prompts, protected source, credentials, full traces, and unrestricted memory pages must not be copied into generic evaluation telemetry.

## Preserved boundaries

This roadmap does not change current authority:

- Phase I-3 remains the active next implementation boundary.
- Phase I-4 through I-9 are planned and require dedicated contracts.
- RelayMEM owns memory meaning and persistence.
- M2 and RelayCTX own retrieval selection and backend-bound injection.
- RelaySLP may form ordinary memory and produce held or proposal candidates.
- SOUL Lab provides bounded observation and explicit operations through server APIs.
- RelaySOUL changes require explicit intervention.
- queue scanning and worker supervision must reuse B3, C1-5, C2, and C1-2 rather than bypass them.
- UI conversation is text-first; TTS and avatar execution remain a separate Runtime MVP track.
