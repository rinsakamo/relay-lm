---
relaylm_doc_type: status
relaylm_authority: current_project_state
relaylm_status: current
relaylm_volatility: high
relaylm_owner: project_status
relaylm_update_trigger:
  - boundary moves between design, dry-run, read-only, and apply
  - default behavior changes
  - supported request shape changes
  - current schema producer or consumer changes
  - active integration milestone changes state
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - MVP boundary and roadmap sequencing
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/release/v0.1-release-readiness.md
  - docs/architecture/project_execution_plan.md
  - docs/architecture/asm1_shared_assessment_runtime_foundation.md
  - docs/architecture/sm1_subjective_mem_create_runtime.md
  - docs/architecture/st1_subjective_mem_commit_runtime.md
  - docs/architecture/lc1a_subjective_mem_correct.md
  - docs/architecture/subjective-mem-forget-runtime.md
  - docs/architecture/subjective-mem-restore-runtime.md
  - docs/architecture/subjective-mem-consolidate-runtime.md
  - docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md
  - docs/contracts/governed-evidence-contract-family.md
  - docs/contracts/relayctx-session-evidence-overlay.md
  - docs/contracts/shared-assessment-subjective-mem.md
  - docs/contracts/subjective-mem-canonical-markdown-v1.md
  - docs/reference/project-status-reference-map.md
---
# RelayLM Project Status

Last reviewed: 2026-07-29 JST

## Purpose and authority

This page owns current implementation status and active caveats. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering. Completed-slice detail, historical handoffs, and evidence links live in the [Project Status Reference Map](reference/project-status-reference-map.md).

## Release position

v0.1 readiness is recorded in [v0.1 Release Readiness](release/v0.1-release-readiness.md). The MVP execution lanes and local durable-memory value smoke are complete. Content-bearing comparison artifacts remain local-only under `local/value_smoke/`.

## Current implementation position

```text
RelayLM Core managed route, pre-stream hardening, Stream Unpack, and RelaySLP orchestration: complete for the accepted v0.1 boundary
O1 local scheduler boundary: complete; O2/O3 remain opt-in local operation and are not app-embedded or default-on
RelayMEM Primary path: current production memory/retrieval authority while the Subjective MEM Retrieval hard cutover remains incomplete
Character Workspace, Analyzer Candidate Governance, and current SOUL Lab management surfaces: complete for their bounded shipped slices

EV-1 Governed Evidence runtime foundation: complete in PR #629; default-off
OVL-1 CTX-OVL participant-private vertical slice: complete in PR #639; default-off and participant-private only
ASM-1 Shared Assessment runtime foundation: complete in PR #636; default-off
SM-1 Subjective MEM create decision/result vertical slice: complete in PR #646; default-off and prepared-only
ST-1 Markdown + operations commit protocol: complete; default-off, create-only, POSIX apply
LC-1 lifecycle migration: complete; LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, LC-1D Restore, and LC-1E Consolidate implemented; default-off, POSIX apply
RT-1 Retrieval migration: in progress; RT-1A contract and projection foundation complete in PR #774; RT-1B projection builder and deterministic rebuild complete in PR #779; RT-1C shadow adapter, grounding handoff, and usage ledger complete in PR #784; RT-1B remains default-off and unwired from ordinary Retrieval; RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval; RT-1D hard cutover and retirement is architecture-authorized as the next ordered Lane C slice and is not started
```

## Contract-aligned implementation migration boundary

**EV-1** provides route-owned current-user and canonical assistant-response Evidence capture, immutable records, authorization state, projections, checkpoints, and a bounded local Evidence store for one private managed-conversation boundary. It does not itself implement overlay materialization, Shared Assessment, Subjective MEM, multi-user Evidence, export, replication, or purge.

**OVL-1** consumes EV-1 for process-local, bounded, rebuildable, non-durable `participant` / `participant_private` RelayCTX working state. Shared-scene, relationship, quarantine, durable memory formation, and RelayATN mutation authority remain unsupported.

**ASM-1** consumes EV-1 directly and provides character-independent Shared Assessment revisions, one logical current selector, formation-time revalidation, and transaction-bound formation receipts. ASM-1 does not itself write Subjective MEM or inject assessments into the normal response path.

**SM-1** consumes one exact current ASM-1 revision and atomically creates one immutable `create` decision plus one revision-1 prepared Subjective MEM result. The result remains non-canonical and unavailable to ordinary Retrieval until ST-1 finalizes the exact prepared linkage.

**ST-1** consumes one exact SM-1 prepared `create` bundle, publishes deterministic canonical Subjective MEM Markdown, commits the matching durable content-free operations receipt, and finalizes the logical selector to `mutation_state: none` / `retrieval_eligible: true`. The bounded slice remains default-off, create-only, single-host, and POSIX-apply-only.

**LC-1A Correct** consumes one exact current active canonical revision, current selector, current receipt, current admitted Shared Assessment, and explicit correction authority. It appends one immutable successor revision, retains the predecessor, atomically fences the selector during publication, and finalizes content-free transition/receipt/idempotency records. It remains default-off, active-to-active only, single-host, and POSIX-apply-only.

**LC-1B Forget** consumes one exact current active canonical revision and appends an immutable hidden successor while retaining the predecessor. It finalizes the shared lifecycle transition, receipt, selector, and content-free anti-reformation tombstone under one Evidence-space transaction, with deterministic idempotency and caller-invoked forward recovery. Exact forgotten semantics are rejected through one canonical public/locked anti-reformation evaluator. The slice remains default-off, single-host, and POSIX-apply-only.

**LC-1C Pin/Unpin** consumes one exact current canonical revision, selector, receipt, predecessor authority, and explicit management authority. It appends an immutable `active -> pinned` or `pinned -> active` successor while preserving semantic payload, scope, formation snapshot, strength, memory kind, and formation stage. It uses shared lifecycle reservation, canonical publication, exact replay, and caller-invoked forward recovery; its durable lifecycle records remain content-free. The slice remains default-off, single-host, and POSIX-apply-only.

**LC-1D Restore** consumes one exact current hidden canonical revision, selector, receipt, predecessor authority, original Forget receipt, and immutable anti-reformation tombstone. It appends an immutable `hidden -> active` successor, authenticates the complete Forget lineage, finalizes one exact immutable release record for the singleton tombstone, and uses shared lifecycle reservation, exact replay, and caller-invoked forward recovery. The slice remains default-off, single-host, and POSIX-apply-only.

**LC-1E Consolidate** consumes one exact current active Primary canonical revision, selector, receipt, and predecessor authorization authority. It appends one immutable active Secondary successor while preserving semantic payload, assessment linkage, character, scope, formation snapshot, strength, memory kind, lifecycle state, and retrieval visibility. It enforces the exact lifecycle and lower-commit gate triples before durable reads, uses shared lifecycle publication, deterministic replay, and caller-invoked forward recovery, and remains default-off, single-host, and POSIX-apply-only.

**RT-1A Contract and projection foundation** defines the storage-neutral retrieval request, exact projection row and manifest, closed exclusion, bounded selection, and content-free usage-event identities with pure validation and digest binding. It performs no filesystem scan, projection persistence or rebuild, ordinary Retrieval, RelayCTX handoff, durable usage-event write, Primary MEM change, shadow comparison, or cutover.

**RT-1B Projection builder and deterministic rebuild** derives one complete, deterministic, content-free projection generation from one fixed canonical source snapshot, and separates that derivation from a disposable replace-only file store. Persisted state is accepted only through exact-source rebuild comparison, never through its own recomputable digests. It reuses the shared committed receipt and authorization authority instead of introducing a second evaluator, refuses legacy unbound current selectors, and fails closed on malformed or non-canonical source input. It performs no ordinary Retrieval, query matching or ranking, RelayCTX/E1-R4 handoff, usage-event persistence, Primary MEM change, shadow comparison, or cutover.

**RT-1C Shadow adapter, grounding handoff, and usage ledger** selects exact current eligible Subjective revisions from one complete verified RT-1B projection generation and prepares one bounded runtime-private handoff. Selected prose comes only from bounded canonical page bytes parsed through the existing canonical Markdown owner, with exact page, block, revision, scope, memory-kind, formation-stage, lifecycle, retrieval-visibility, and authorization binding proven against the exact projection row and admitted request scope; caller-attested prose with a matching caller digest cannot be admitted. Each item's token estimate is derived deterministically from that parsed canonical prose. The prepared handoff stays non-admitted and exposes no evidence-release path; the durable ledger revalidates it against canonical bytes, finalizes exact content-free usage event and result pairs, and only then seals an admitted handoff that materializes fresh grounding dictionaries. A separate temporary owner performs content-free Primary-vs-Subjective characterization over admitted public projections only. It performs no ordinary request-path wiring, RelayCTX injection, Primary MEM access or fallback, E1-R4 behaviour change, canonical mutation, or RT-1D cutover.

LC-1 lifecycle migration is complete through Consolidate. RT-1 is in progress with RT-1A, RT-1B, and RT-1C complete; RT-1D hard cutover and retirement is architecture-authorized as the next ordered Lane C slice and is not started. A disposable RT-1B projection builder and store plus a default-off shadow-only RT-1C selection, characterization, and usage ledger existing does not mean ordinary Retrieval is wired: logical eligibility still does not wire ordinary Retrieval, ranking, cache, or request-path readers.

## Current caveats

- EV-1, OVL-1, ASM-1, SM-1, ST-1, LC-1A, LC-1B, LC-1C, LC-1D, and LC-1E remain fully default-off.
- OVL-1 supports only `participant` / `participant_private` process-local overlay state.
- SM-1 performs no LLM, translation, embedding, classifier, RelaySOUL, queue, worker, scheduler, normal response-path, Primary MEM, or Retrieval call.
- ST-1 supports revision-1 `create`; LC-1A supports exact current `active -> active` Correct successors; LC-1B supports exact current `active -> hidden` Forget successors and exact anti-reformation blocking; LC-1C supports exact current `active -> pinned` and `pinned -> active` successors; LC-1D supports exact current `hidden -> active` Restore successors with authenticated Forget lineage and atomic immutable release-record finalization; LC-1E supports exact current active Primary-to-Secondary Consolidate successors without semantic rewrite. These secure apply paths remain limited to the checked POSIX single-host boundary. Windows startup remains supported while secure apply fails closed there.
- RT-1C is default-off, explicit shadow-only, and unwired from ordinary request-path Retrieval.
- RT-1A through RT-1C together provide the pure contract and digest foundation, one bounded projection builder and store, and one default-off shadow-only selection, characterization, and usage-ledger boundary; they still do not implement ordinary served Subjective MEM Retrieval, query matching or ranking, cache, request-path wiring, or authority cutover. RT-1B projection I/O is disposable, default-off, and is not a served reader.
- Durable RT-1C usage persistence exists only for an explicitly non-shadow prepared handoff that passed exact canonical revalidation and exact durable event/result finalization; no ordinary request-path use of it exists.
- ST-1 revision-1 `create` still publishes a legacy unbound current selector, so those revision-1 memories cannot enter the RT-1B projection until a later accepted slice publishes authority-bound selectors.
- ST-1 and LC-1 logical `retrieval_eligible: true` do not implement ordinary Subjective MEM Retrieval.
- Primary MEM remains the sole ordinary served memory and Retrieval authority until a future RT-1D implementation is validated, merged, and its cutover receipt is finalized.
- O2/O3 remain explicit local process layers, not browser authority, app-embedded services, or new memory mutation authority.
- RelayCTX short-term runtime injection apply remains default-off and dry-run-only by default.
- Open decision debt remains PM-D1 RelaySOUL gate design-freeze relation, PM-D2 legacy intent-artifact closure/absorption, PM-D4 client-history exclusion deployment policy, and PM-D9 multilingual analyzer/proposal policy.

## Immediate dependency-first work

```text
LC-1 lifecycle migration                                    complete; LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, LC-1D Restore, and LC-1E Consolidate implemented
  -> RT-1 Retrieval projection and hard cutover             in progress
       -> RT-1A contract and projection foundation           complete in PR #774
       -> RT-1B projection builder and rebuild               complete in PR #779
       -> RT-1C shadow adapter, grounding handoff, usage ledger complete in PR #784; default-off, shadow-only, unwired
       -> RT-1D hard cutover and retirement                  next ordered Lane C slice; architecture-authorized / not started

Parallel decision work:
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D9 analyzer candidate governance and multilingual schema policy follow-through
  PM-D2 closure or absorption after PM-D6
```

## Not yet implemented

- RT-1D hard cutover and retirement;
- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;
- Subjective MEM authority cutover and Primary MEM reader/writer retirement;
- Primary MEM migration, Subjective MEM backup/restore completion, and multi-host publication;
- shared-scene, relationship, and quarantine CTX-OVL partitions;
- full RelayREL relationship Markdown parsing;
- physical purge;
- Merge / Supersession runtime apply;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- media runtime execution;
- ASR and peer communication transport.
