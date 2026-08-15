---
relaylm_doc_type: planning
relaylm_authority: d6_r35_closure_horizon
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: project_governance
relaylm_update_trigger:
  - a D6-R35 horizon slot is split, merged, skipped, or reclassified
  - a newly discovered active transitional source would require extending R35 beyond the recorded upper bound
  - a cross-lane dependency gate changes the eligibility of an R35 slot
  - D6-R35 closes and D6-R36 becomes eligible
relaylm_not_authoritative_for:
  - exact current implementation completion or current PR state
  - exact runtime schemas, algorithms, APIs, routes, or mutation behavior
  - source-retirement manifest provenance or per-path final disposition
  - Lane R repository asset classification authority
  - Lane C implementation authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project-execution.md
  - ../architecture/project_execution_plan.md
  - documentation-architecture-inventory.md
  - repository-structure-migration.md
relaylm_related_contracts:
  - ../contracts/agent-execution-safety.md
  - ../contracts/documentation-governance.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Lane D controllers and implementation agents
  - project maintainers and documentation migration reviewers
relaylm_authority_level: sequencing
---
# D6-R35 Closure Horizon

## Authority summary

This page fixes the finite closure horizon for **D6-R35 residual non-active and transitional source-family retirement** after completion of the Phase 5.5 stream/TTS bounded-slice family.

The horizon is a sequencing boundary, not a statement that every named slot must become a separate pull request.

At the bootstrap used to establish this horizon:

```text
exact main: b108c98d0fd4f429335b25a38f70f58a144e8ab7
main subject: docs: sync Phase 5.5 retirement authority (#1210)
D6-R35-M implementation: #1209
D6-R35-M mandatory P8: #1210
open PRs: 0
open relaylm:p6-stop: 0
governance epoch: c512626a911d3c603c9d6a5d025a55f49bb367855c4591679ebd51ab6656c3d8
```

Exact current implementation truth still belongs to `docs/PROJECT_STATUS.md`. Exact source-retirement provenance still belongs to `records/documentation/retirement-manifest.json` and the implementing PRs. This page owns only the finite R35 closure map and its dependency order.

## Horizon rule

The authorized R35 horizon after completed slot M is:

```text
N -> O -> P -> Q -> R -> S -> T -> U -> V -> W -> X -> Y -> Z -> AA -> AB -> AC -> AD -> AE
```

`AE` is the **hard planning upper bound** of D6-R35 under the current whole-tree Horizon Audit.

The following rules apply:

1. A fresh P0 and P1 are still required before every repository-changing transaction.
2. Adjacent slots may be merged when fresh P1 proves that they form one Maximum Coherent Cluster with one bounded responsibility, one authority graph, and one safe changed-path budget.
3. A slot may be skipped only when fresh repository authority proves that its responsibility is already fully resolved by another reviewed transaction.
4. Splitting a slot into reviewed sub-slices does not authorize a new horizon family beyond `AE`.
5. A newly discovered family that appears to require work after `AE` is not automatically appended. It is a **Horizon Audit discrepancy** and requires an explicit amendment to this planning authority before repository mutation.
6. Cross-lane dependencies must be detached by their owning lane before Lane D retires the dependent source.
7. Exact-contract gaps are resolved by bounded contract/authority convergence before the dependent source is retired.
8. Frozen historical evidence remains evidence and is not counted as an active R35 source merely because it retains milestone text.
9. R35 remains in progress until every horizon responsibility is resolved and a fresh closure audit proves no unclassified active transitional source remains.
10. D6-R36 does not start merely because a late R35 slot merges. It starts only after R35 closure is independently proven.

## Slot map

### D6-R35-N — Character Workspace maintenance exact-contract promotion

Promote the exact current Character Workspace maintenance candidate/proposal boundary that still lives in implementation/code authority into a permanent exact contract.

Known gate at horizon creation:

- `docs/architecture/cw_a4_slp_workspace_maintenance_candidates.md` remains live;
- stable responsibility exists in `docs/architecture/character-workspace/maintenance-candidates.md`;
- exact candidate/proposal schema identifiers still require permanent contract ownership before retirement.

N is convergence, not retirement.

### D6-R35-O — CW-A4 maintenance source retirement

After N closes the exact-contract gap, retire the CW-A4 implementation handoff and repoint active consumers to the stable maintenance architecture and new exact contract.

No Character Workspace runtime behavior change is implied.

### D6-R35-P — Phase 6 admission, response-handoff, and durable-queue family

Converge and retire the remaining Phase 6 A/B admission and queue milestone sources whose stable and exact responsibilities are already represented by permanent SLP architecture/contracts, including the current job-admission, response-handoff, and durable-queue contract families.

The exact source set is frozen only by fresh P1.

### D6-R35-Q — Phase 6 worker, source-capture, and finalization family

Converge the remaining Phase 6 C / worker / governed-source-capture / durable-finalization milestone sources onto permanent memory-formation and SLP worker/finalization owners.

No worker, queue, source-capture, or persistence semantics may change as part of documentation retirement.

### D6-R35-R — Primary writer and index/log recovery source family

Dispose the residual Primary writer, durable finalization, and index/log reconciliation milestone sources after proving exact coverage in permanent storage/recovery/formation authority.

This slot includes the remaining M3/I1G-style source family only to the extent fresh P1 proves one coherent responsibility graph.

### D6-R35-S — Shared Assessment / Subjective MEM transitional runtime family

Retire residual milestone-named Shared Assessment and Subjective MEM runtime source documents whose durable semantics are already owned by current memory architecture and contracts.

This slot does not reopen Lane C implementation work.

### D6-R35-T — Grounded Recall exact-contract promotion

Promote the exact current Grounded Recall response-grounding artifact boundary required to remove the remaining E1-R4 handoff dependency.

Known horizon gate:

- `docs/architecture/e1r4_retrieval_response_grounding.md` remains live;
- stable retrieval architecture exists in `docs/architecture/memory/retrieval-and-grounding.md`;
- the exact Grounded Recall context/result identity must have a permanent exact owner before retirement.

T is convergence, not retirement.

### D6-R35-U — E1 retrieval / grounding / evaluation-source retirement

After T, retire the residual E1 retrieval and response-grounding architecture handoffs and move or retain evaluation material only according to the evidence model.

Permanent retrieval architecture and exact retrieval/analyzer contracts remain semantic owners.

### D6-R35-V — legacy stable Character / Relationship / Scene source family

Retire pre-canonical stable-design sources whose durable content has already been synthesized into permanent Character Workspace, relationship, scene, affect, context, privacy, and pipeline architecture.

Representative legacy families include file-first workspace design, safe SOUL/scene/context compile-chain design, relationship design, and character-belief/relationship-dynamics design. Fresh P1 defines the exact coherent source set.

### D6-R35-W — legacy Memory / pinned / scene-scope / current-target source family

Converge legacy memory lifecycle, pinned-memory, scene-memory-scope, and memory current/target interpretation sources onto permanent memory architecture and reference authority.

This slot must preserve the distinction between semantic architecture and current/target interpretation.

### D6-R35-X — SOUL Lab legacy MVP source family

Retire residual milestone-named SOUL Lab UI/runtime MVP source documents after proving that stable SOUL Lab architecture and exact UI contracts already own all durable current semantics.

No React, route, API, browser-state, or server behavior change is authorized.

### D6-R35-Y — latency, VTuber profile, and residual evaluation-method family

Classify and dispose remaining milestone/profile/evaluation-method sources into permanent performance architecture, reference, operations, templates, or evidence according to their actual authority.

Measured evidence remains evidence; a method or blank template is not promoted as measured evidence.

### D6-R35-Z — request-ordering exact-contract promotion

Promote the exact current request-ordering boundary required to retire the P0 relationship -> scene -> affect ordering handoff.

Known horizon gate:

- `docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md` remains live;
- stable pipeline/scene/relationship/affect architecture exists;
- exact measured ordering assertions still require a reviewed permanent exact-authority disposition.

Z is convergence, not retirement.

### D6-R35-AA — P0 request-ordering source retirement

After Z, retire the P0 ordering source and repoint active consumers to permanent pipeline and subsystem authority.

The ordering behavior itself must remain byte/semantics-equivalent.

### D6-R35-AB — current-target and execution-plan authority transfer

Complete the authority transfer from milestone-oriented planning/interpretation sources to the already-created permanent planning and reference destinations.

Expected conceptual transfers include:

```text
docs/architecture/project_execution_plan.md
  -> docs/planning/project-execution.md

docs/architecture/current_target_migration_guide.md
  -> docs/reference/current-target-interpretation.md
```

The source paths remain live until their own fresh provenance, consumer migration, replacement validation, and final disposition gates pass.

This horizon page does not itself retire either source.

### D6-R35-AC — scheduler / O-family retirement, Lane R dependency gated

Retire residual O0/O1/O2/O3 scheduler milestone sources only after current Lane R repository-asset classification no longer depends on those source paths as active evidence/authority.

Permanent scheduler architecture/contracts already exist, but Lane D must not edit Lane R classification authority to force this slot through.

### D6-R35-AD — PM-D5/D6/D7 retirement, Lane R dependency gated

Retire residual PM-D compatibility/fold-in source records only after Lane R detaches current repository-asset classification references and fresh P1 proves no remaining cross-lane consumer.

Lane D may repair its own documentation consumers after that detachment; it may not mutate the Lane R classification source or mirror in this slot.

### D6-R35-AE — remaining Primary compatibility I-series closure

Resolve the final still-live Primary compatibility / I-series transitional authorities that cannot yet be retired safely.

At horizon creation, `docs/architecture/phase_i5_pin_unpin_contract.md` remains explicitly live because it still owns the Primary token and read-only preflight boundary, while permanent Subjective MEM Pin/Unpin authority explicitly excludes Primary compatibility/migration responsibility.

AE must therefore perform whatever bounded authority convergence is required before any final retirement. It is not permission to delete I-5A by filename alone.

AE is the last planned R35 slot.

## Cross-lane gates

The following files remain outside Lane D write authority while they are owned by Lane R classification work:

```text
docs/reference/repository-asset-classification.md
records/repository/asset_classification_v1.yaml
```

If AC or AD is blocked by those authorities, Lane D waits for reviewed Lane R detachment rather than editing them.

A cross-lane wait does not create a new R35 slot.

## Stay-live and evidence rules

A source remains live when it still owns an exact current responsibility that no permanent owner has accepted. Such a source is not retired merely to satisfy the horizon schedule.

Conversely, a completed implementation report or exact source snapshot under a governed evidence collection is not counted as an active transitional source simply because it retains the historical milestone name.

The closure distinction is:

```text
active semantic / exact authority still needed
  -> converge before retirement

active transitional source with permanent replacement proven
  -> retire through reviewed atomic gate

frozen historical evidence
  -> retain as evidence

superseded narrative without evidence role
  -> Git history only
```

## R35 closure gate

D6-R35 closes only when a fresh exact-main audit proves all of the following:

1. every N-through-AE responsibility is resolved, merged into another reviewed slot, or explicitly proven already satisfied;
2. no active non-canonical milestone/handoff source remains merely because it was missed by the horizon inventory;
3. no retired path remains a live current-authority consumer;
4. retirement-manifest coverage is complete for every path retired through R35;
5. qualifying frozen evidence remains byte-identical except where an independently reviewed evidence correction is explicitly authorized;
6. no duplicate semantic owner, redirect, compatibility stub, or archive copy was introduced by retirement;
7. Lane R and Lane C authority boundaries remain uncontaminated;
8. current-boundary, semantic-audit, governance, retirement-reference, and link validators are green at exact main;
9. D6 remains incomplete until the subsequent R36-R39 remediation and completion-audit sequence finishes.

Only after this gate passes does D6-R36 become eligible.

## After R35

The fixed post-R35 order remains:

```text
D6-R36  root documentation router rebuild
  -> D6-R37  bespoke guard / receipt / ledger retirement
  -> D6-R38  retirement-manifest closure and current-tree classification audit
  -> D6-R39  D6 completion audit replay
```

This page does not authorize any of those stages early.

## Amendment rule

The horizon is intentionally finite.

If fresh exact-main evidence later identifies a genuinely active transitional family not represented by N through AE, the controller must:

1. stop before repository mutation for that newly discovered family;
2. classify why the Horizon Audit missed it;
3. prove whether it can be absorbed into an existing slot without scope distortion;
4. if not, amend this page through a separate reviewed planning transaction;
5. only then authorize an extension or replacement of the upper bound.

Therefore `AE` is a hard upper bound under current authority, not an invitation to silently continue with `AF`.