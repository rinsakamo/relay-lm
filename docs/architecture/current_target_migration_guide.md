---
relaylm_doc_type: current_target_migration
relaylm_authority: current_target_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Current / Target / Migration Guide

Last reviewed: 2026-08-08 JST

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed RelayMEM/RelaySLP status lives in [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md), MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md), and repository-wide current status lives in [Project Status](../PROJECT_STATUS.md).

This guide is an interpretation aid. It does not supersede the exact RT-1 cutover authority, lifecycle contracts, current-status authority, or retirement gates.

## RT-1 ordinary-memory authority interpretation

RT-1D-R4 changed how the older Primary-oriented integration material must be read. The ordinary Retrieval facade now resolves one exact reader authority before touching any memory family:

```text
primary_only
  -> retained Primary compatibility reader only

neither
  -> no ordinary durable-memory reader

subjective_only
  -> finalized Subjective reader only
  -> no Primary root resolution, discovery, recall, or fallback
```

Primary and Subjective memories are never ordinary co-authorities for one request. Configuration, store presence, a historical Primary success, an empty Subjective result, or a grounding outcome cannot select or restore reader authority.

Primary mutation is independently fenced by the exact RT-1 writer decision. Primary writes are permitted only before the durable `primary_writer_fenced` state. After the fence, historical worker, formation, Correct/Forget, Pin/Unpin, or recovery paths do not regain Primary mutation authority from a missing, stale, or caller-invented decision.

The older Phase I-1, I-4D, E1-R5, and PM-D8 material therefore remains current only as bounded Primary compatibility, regression, operational, or historical evidence until its owning R5/R6 retirement gate completes. E1-R4 is different: the grounding policy survives authority transfer because RelayCTX repack applies the same E1-R4 evidence-grounding contract to the selected memories of exactly the authority already chosen by Retrieval. It never combines Primary and Subjective evidence.

RT-1D-R5 owns retirement of replaced Primary ordinary reader/fallback and temporary rehearsal/shadow execution surfaces. This guide does not pre-authorize deletion or predict which explicitly read-only historical/operational Primary consumers survive that gate.

## Current Wave 7 / P0-PIPE / ACG / CW compatibility interpretation

This section includes the Wave 7 / E1-R5 compatibility interpretation plus the post-Wave-7 P0-PIPE, ACG-1 through ACG-6, CW-A1 through CW-A5, O2/O3, and PM-D5 through PM-D8 current boundaries.

```text
O1D2 is current implemented as bounded policy wrapper.
O1E is current implemented as bounded caller-invoked operational controls.
O1F is current implemented as validation-only operational hardening.
O2 is current implemented as an opt-in supervised local scheduler service above O1E.
O3 is current implemented as an opt-in local CLI/process wrapper around O2.
I-4E is current implemented as loopback Forget API/UI.
I-4F is current implemented as validation-only Forget product completion.
UI-B1A is current implemented read-only visibility.
I-5A is current implemented contract/read-only preflight only.
I-5B is current implemented as Pin / Unpin apply/API/UI/ranking behavior.
I-7A/B is current implemented contract/read-only preflight only.
I-7C is current implemented as Held Apply / Discard runtime/API/UI/durable governance evidence.
E1 evaluation consolidation is current docs/evidence only.
E1-R1 is current implemented as route-owned trusted Home scene admission.
E1-R2 is current implemented as dry-run-first character-store bootstrap.
E1-R3 is current implemented as provenance-preserving Primary MEM formation summary evidence within the Primary compatibility lineage.
E1-R4 is current implemented as one-authority ordinary-memory retrieval-response grounding and unsupported-detail suppression.
E1-R5 is current implemented only as a bounded scoped Primary-only compatibility candidate fallback until the owning retirement gate completes.
P0-PIPE is current implemented as the shipped RelayREL -> RelaySCN -> RelayEMO request-path ordering correction.
ACG-1 is current implemented as the Analyzer Candidate Governance contract/helper boundary.
ACG-2 is current implemented as Grounded Recall detail safety behind Query Detail Analyzer governance.
ACG-3 is current implemented as RelayMEM retrieval query normalization behind Retrieval Query Analyzer governance.
ACG-4 is current implemented as RelayREF / RelayINT Reference/Intent Analyzer consolidation.
ACG-5 is current implemented as RelayEMO scene ownership cleanup and non-authoritative scene hint governance.
ACG-6 is current implemented as the bounded SCN structured classifier and scene-wiki matching boundary.
CW-A1 is current implemented as file-first source tree and parser contracts.
CW-A2 is current implemented as workspace compiler projections and KV-cache tier summaries.
CW-A3 is current implemented as the presentation-only Character Workspace UI rebuild.
CW-A4 is current implemented as dry-run-first SLP-maintained MEM/SCENE/REL wiki candidate and proposal planning.
CW-A5 is current implemented as deterministic character creation, bundled templates, showcase import, local validation, loopback APIs, CLI dry-run/write commands, zero-character UI routing, and local CW-A2 build generation after approved commit.
PM-D5 is current implemented as RelayMEM flat-store compatibility removal from ordinary runtime discovery and public diagnostics.
PM-D6 is current implemented as RelayINT native artifact ownership after RelayREF wrapper removal from the input-side entrypoint.
PM-D7 is current implemented as explicit dry-run-first runtime install and setup preflight/apply command support.
PM-D8 is implemented historical fold-in evidence for the E1-R5 Primary fallback now confined to the Primary-only compatibility branch.
```

E1-R5 was merged after W7-INT and remains post-Wave-7 evidence for the Primary recall gap it closed. Inside an exact `primary_only` reader decision, M2 remains preferred and the folded E1-R5 behavior may bridge the no-eligible-scoped-M2-candidate case under bounded exact-namespace, lifecycle, and relevance checks. The same evidence must not be read as authorizing E1-R5 after `subjective_only`, as a second reader, or as a fallback from failed/empty Subjective retrieval.

PM-D8 in [Project Execution Plan](project_execution_plan.md) is complete historical implementation work. PR #491 folded the former E1-R5 runtime bridge behavior into canonical Primary recall while leaving the former bridge module as compatibility no-op only. RT-1D now places that folded behavior behind the exact Primary-only reader fence; R5/R6 own its final retirement disposition.

P0-PIPE is complete in PR #458. Current request-path interpretation must not describe RelayEMO as the same-turn normalized `scene_state` owner for RelaySCN. RelayREL now precedes RelaySCN, RelaySCN no longer consumes a RelayEMO artifact fallback, and input-side RelayEMO runs after RelaySCN scene policy ownership is established.

A stable opt-in local operation stack is now implemented through O2 and O3. O2 wraps O1E in a supervised service loop and carries bounded O1D2 policy state across repeated invocations. O3 is a local CLI/process wrapper around O2. Both remain explicit operator-invoked boundaries: they are not app-embedded, not browser authority, not default-on, and do not add memory mutation, queue, worker, stale-recovery, or durable-finalization authority.

PM-D5 through PM-D8 are completed post-MVP debt slices. PM-D5 removed legacy flat RelayMEM runtime discovery. PM-D6 replaced the input-side RelayREF-shaped RelayINT compatibility artifact with a native RelayINT artifact. PM-D7 added an explicit dry-run-first `relaylm-runtime-install` command for local setup/preflight and allowlisted safe directory creation under `--write`. PM-D8 folded E1-R5 into canonical Primary recall; RT-1 subsequently fences that Primary behavior behind the exact reader authority and assigns retirement to R5/R6.

ACG-1 through ACG-6 are current as bounded analyzer-governance slices. They establish shared candidate authority rules, Grounded Recall detail safety, RelayMEM retrieval query normalization, RelayREF / RelayINT reference-intent consolidation, RelayEMO scene ownership cleanup, and the first SCN structured classifier / scene-wiki matching boundary. They do not implement scene-wiki page mutation, broad retrieval/update authority from heuristic or LLM candidates, RelayEMO scene ownership restoration, live LLM classifier calls, or SOUL/source mutation authority.

CW-A1 through CW-A5 are current as bounded Character Workspace reset slices. They establish the file-first parser contract, compiler projections, presentation-only UI rebuild, dry-run-first MEM/SCENE/REL proposal planning, and explicit character creation/template/import flow. They do not implement direct uppercase source rewrites, automatic active-character selection, browser-owned authority, remote template registries, unbounded downloads, RelaySOUL apply/rollback, runtime prompt injection changes, media runtime execution, or permissive authority from template/import content alone.

The durable-memory E2 value smoke after O2/O3 scheduler draining is complete as local, human-reviewed v0.1 readiness evidence. Its content-bearing comparison artifacts remain local-only under `local/value_smoke/`; the committed documentation records only the content-free completion boundary.

## RelaySLP and ordinary-memory migration

The Primary pipeline below is implemented historical/current compatibility evidence, not the unconditional ordinary path after RT-1D-R4:

```text
ordinary finalized turn
  -> I1-B source-before-queue publication and B2 enqueue
  -> C2 / C1 worker path or O0 / O1D1 caller path
  -> O1D2 bounded policy hints for later caller decisions
  -> O1E bounded caller-invoked recovery/cancellation/shutdown controls
  -> O1F validation-only operational hardening
  -> O2 opt-in supervised local scheduler service when explicitly invoked
  -> O3 opt-in local CLI/process wrapper when explicitly invoked
  -> Primary formation only while the exact writer decision permits it

later ordinary request
  -> exact RT-1 reader decision first
  -> primary_only: M2-preferred Primary compatibility retrieval
       -> bounded E1-R5 fallback only if eligible scoped M2 selection is empty
       -> Primary lifecycle/currentness filtering
  -> neither: no durable-memory retrieval
  -> subjective_only: finalized Subjective retrieval only; no Primary read/fallback
  -> RelayCTX bounded injection from the one selected authority
  -> E1-R4 common request-side grounded recall context
```

The surrounding completed program boundaries remain unchanged: I-4E/I-4F loopback Forget product work, UI-B1A visibility, I-5A/I-5B Pin/Unpin, I-7A/B/I-7C Held governance, E1-R1 trusted Home admission, E1-R2 character-store bootstrap, E1-R3 provenance-preserving formation evidence, RelayREL/RelaySCN/RelayEMO ordering, ACG-1 through ACG-6, CW-A1 through CW-A5, PM-D5 through PM-D8, and the scheduler/operational stack remain implemented as recorded by their owning authorities.

Completed historical implementation must not be re-listed as future work merely because RT-1 later narrowed or retired its ordinary-serving role. Conversely, an old completion receipt does not keep a replaced Primary reader/writer/fallback authoritative after the exact RT-1 fences.

Remaining migration is deliberately narrower:

```text
RT-1D-R5/R6 Primary ordinary-reader/fallback and temporary cutover-surface retirement
final documentation retirement/canonical path migration after exact consumers are proved
full RelayREL relationship Markdown parsing
RelayINT / RelayREF broad naming cleanup after PM-D6, if still needed
TTS/audio/avatar runtime adapter execution
```

## Safe defaults

Current apply, worker, durable-finalization, retention, scheduler, Character Workspace, and E1 evaluation settings remain default-off, explicit caller/operator invoked, or explicit user-approved where applicable. O1E operational controls and O1F validation do not authorize polling, sleep, loops, service supervision, or always-on processing. O2 and O3 are opt-in local operation boundaries, not app startup or browser authority, and do not turn scheduler gates on by default. E1-R1 defaults disabled and admits Home-origin persistence only through route-owned configuration, never browser-owned hidden metadata. E1-R2 is dry-run-first and may only prepare safe store layout. E1-R3 keeps public provenance projections content-free.

E1-R4 keeps public grounded-recall projections content-free, performs no post-hoc visible response rewriting, and consumes selected evidence only from the ordinary memory authority already named by RT-1. E1-R5 keeps Primary compatibility fallback diagnostics content-free, preserves M2 as preferred relevance owner inside `primary_only`, fails closed without required relevance/scope evidence, and cannot run as Subjective failure/empty-result fallback. PM-D8 records the fold-in history but does not bypass the RT-1 reader fence.

P0-PIPE keeps ordering diagnostics content-free and does not expose relationship bodies, scene bodies, memory bodies, raw messages, private state, or assistant output. ACG-1 through ACG-6 keep public analyzer and classifier projections content-free and do not expose raw user text, free-form LLM rationale, source Markdown, memory text, scene Markdown, relationship Markdown, paths, queue payload bodies, scene-wiki body text, or unvalidated external signal bodies. CW-A1 through CW-A5 keep public workspace/creation projections content-free, require explicit approval before persistence, reject imported `.relaylm/**` runtime/build/state artifacts, and do not auto-activate a newly created character. PM-D5 through PM-D8 keep public projections content-free and do not expose raw paths, memory text, queue payloads, protected source bodies, config secrets, or runtime-private identifiers. No migration step may silently expose content-bearing runtime state in generic diagnostics or imply recurring scheduling/TTS/avatar execution from helper or handoff metadata alone.
