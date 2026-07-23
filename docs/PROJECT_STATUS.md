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
  - docs/contracts/governed-evidence-contract-family.md
  - docs/contracts/relayctx-session-evidence-overlay.md
  - docs/contracts/shared-assessment-subjective-mem.md
  - docs/contracts/subjective-mem-canonical-markdown-v1.md
  - docs/reference/project-status-reference-map.md
---
# RelayLM Project Status

Last reviewed: 2026-07-23 JST

## Purpose and authority

This page owns current implementation status and active caveats. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering. Completed-slice detail, historical handoffs, and evidence links live in the [Project Status Reference Map](reference/project-status-reference-map.md).

## Release position

v0.1 readiness is recorded in [v0.1 Release Readiness](release/v0.1-release-readiness.md). The MVP execution lanes and local durable-memory value smoke are complete. Content-bearing comparison artifacts remain local-only under `local/value_smoke/`.

## Current implementation position

```text
RelayLM Core managed route, pre-stream hardening, Stream Unpack, and RelaySLP orchestration: complete for the accepted v0.1 boundary
O1 local scheduler boundary: complete; O2/O3 remain opt-in local operation and are not app-embedded or default-on
RelayMEM Primary path: current production memory/retrieval authority while the Subjective MEM migration remains incomplete
Character Workspace, Analyzer Candidate Governance, and current SOUL Lab management surfaces: complete for their bounded shipped slices

EV-1 Governed Evidence runtime foundation: complete in PR #629; default-off
OVL-1 CTX-OVL participant-private vertical slice: complete in PR #639; default-off and participant-private only
ASM-1 Shared Assessment runtime foundation: complete in PR #636; default-off
SM-1 Subjective MEM create decision/result vertical slice: complete in PR #646; default-off and prepared-only
ST-1 Markdown + operations commit protocol: complete; default-off, create-only, POSIX apply
LC-1 lifecycle migration: in progress; LC-1A Correct implemented, default-off, active-to-active only, POSIX apply
```

## Contract-aligned implementation migration boundary

**EV-1** provides route-owned current-user and canonical assistant-response Evidence capture, immutable records, authorization state, projections, checkpoints, and a bounded local Evidence store for one private managed-conversation boundary. It does not itself implement overlay materialization, Shared Assessment, Subjective MEM, multi-user Evidence, export, replication, or purge.

**OVL-1** consumes EV-1 for process-local, bounded, rebuildable, non-durable `participant` / `participant_private` RelayCTX working state. Shared-scene, relationship, quarantine, durable memory formation, and RelayATN mutation authority remain unsupported.

**ASM-1** consumes EV-1 directly and provides character-independent Shared Assessment revisions, one logical current selector, formation-time revalidation, and transaction-bound formation receipts. ASM-1 does not itself write Subjective MEM or inject assessments into the normal response path.

**SM-1** consumes one exact current ASM-1 revision and atomically creates one immutable `create` decision plus one revision-1 prepared Subjective MEM result. The result remains non-canonical and unavailable to ordinary Retrieval until ST-1 finalizes the exact prepared linkage.

**ST-1** consumes one exact SM-1 prepared `create` bundle, publishes deterministic canonical Subjective MEM Markdown, commits the matching durable content-free operations receipt, and finalizes the logical selector to `mutation_state: none` / `retrieval_eligible: true`. The bounded slice remains default-off, create-only, single-host, and POSIX-apply-only.

**LC-1A Correct** consumes one exact current active canonical revision, current selector, current receipt, current admitted Shared Assessment, and explicit correction authority. It appends one immutable successor revision, retains the predecessor, atomically fences the selector during publication, and finalizes content-free transition/receipt/idempotency records. It remains default-off, active-to-active only, single-host, and POSIX-apply-only. LC-1 is not complete: Forget, Pin/Unpin, Restore, and Consolidate remain ordered later slices. Logical eligibility still does not wire ordinary Retrieval, projection, ranking, cache, or request-path readers; RT-1 remains later.

## Current caveats

- EV-1, OVL-1, ASM-1, SM-1, ST-1, and LC-1A remain fully default-off.
- OVL-1 supports only `participant` / `participant_private` process-local overlay state.
- SM-1 performs no LLM, translation, embedding, classifier, RelaySOUL, queue, worker, scheduler, normal response-path, Primary MEM, or Retrieval call.
- ST-1 supports revision-1 `create`; LC-1A supports only exact current `active -> active` Correct successors on the checked POSIX single-host apply boundary. Windows startup remains supported while secure apply fails closed there.
- ST-1 logical `retrieval_eligible: true` does not implement ordinary Subjective MEM Retrieval or projection.
- Primary MEM remains the current ordinary memory and Retrieval authority until required lifecycle migration and RT-1 hard cutover are accepted.
- O2/O3 remain explicit local process layers, not browser authority, app-embedded services, or new memory mutation authority.
- RelayCTX short-term runtime injection apply remains default-off and dry-run-only by default.
- Open decision debt remains PM-D1 RelaySOUL gate design-freeze relation, PM-D2 legacy intent-artifact closure/absorption, PM-D4 client-history exclusion deployment policy, and PM-D9 multilingual analyzer/proposal policy.

## Immediate dependency-first work

```text
LC-1 lifecycle migration                                    in progress; LC-1A Correct implemented
  -> LC-1B Forget                                           next ordered slice; not started
  -> LC-1C Pin/Unpin -> LC-1D Restore -> LC-1E Consolidate registered; not started
  -> RT-1 Retrieval projection and hard cutover             registered; not started

Parallel decision work:
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D9 analyzer candidate governance and multilingual schema policy follow-through
  PM-D2 closure or absorption after PM-D6
```

## Not yet implemented

- Subjective MEM Forget, Pin/Unpin, Restore, Consolidate, and every lifecycle transition beyond LC-1A active-to-active Correct;
- ordinary Subjective MEM Retrieval projection, ranking, cache, request-path wiring, and RT-1 hard cutover;
- Primary MEM migration, Subjective MEM backup/restore completion, and multi-host publication;
- shared-scene, relationship, and quarantine CTX-OVL partitions;
- full RelayREL relationship Markdown parsing;
- restore/unhide or physical purge;
- Merge / Supersession runtime apply;
- Secondary MEM consolidation;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- media runtime execution;
- ASR and peer communication transport.
