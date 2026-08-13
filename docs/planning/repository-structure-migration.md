---
relaylm_doc_type: planning
relaylm_authority: repository_structure_documentation_canonicalization_and_maintenance_execution_order
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - an active prerequisite PR merges or is superseded
  - LC-1 or RT-1 ordering changes
  - the documentation canonicalization or retirement boundary changes
  - a repository-maintenance stage opens, completes, or is reordered
  - a public import, compatibility, retained-record, or PR-lifecycle rule changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, or API behavior
  - deletion or migration authorization for an unlisted asset
  - repository-wide user-data migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - workstream-orchestration.md
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/documentation-governance.md
  - ../architecture/repository-maintenance-system.md
  - ../operations/documentation-synthesis-and-retirement.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Repository Structure and Documentation Canonicalization Plan

Last reviewed: 2026-08-09 JST

## Purpose

This document owns the execution order for repository simplification, documentation canonicalization, historical retirement, validation-surface consolidation, generated navigation, and domain-package migration.

Current implementation completion remains owned by [Project Status](../PROJECT_STATUS.md). The universal PR lifecycle and shorthand continuation behavior are owned by [Workstream Orchestration, Continuation Command, and PR Convergence](workstream-orchestration.md).

## Current post-RT-1 convergence state

The original planning-adoption prerequisites and the legacy Lane C critical implementation program are complete. Current implementation authority records RT-1D-R5 immediate retirement, its mandatory P8, and the P8 result/current-authority correction as completed. The ordinary Primary reader and its ranking/fallback path are retired; only explicitly classified read-only Primary history/observation/lifecycle/admin projections survive.

This completion releases the prerequisite that kept core memory and Retrieval modules protected from repository package migration. The next repository-maintenance stage is therefore Lane R R5, governed core package migration. Lane D has since advanced into D6; D6 final retirement and legacy cutover-tool retirement is the remaining Lane D work before PD-1, and it continues independently where path and authority safety permit.

The post-RT-1 handoff is:

```text
Lane R  R5 governed core package migration                 now eligible
Lane D  D6 final retirement / cutover-tool retirement      continue to completion

R5 complete + D6 complete
  -> Lane D PD-1 personality responsibility convergence
  -> Lane D PD-2 exact personality contracts
  -> Lane C PC-1..PC-4 Personality Core implementation
  -> 9B end-to-end evaluation
  -> Character Presence implementation
```

Lane R R6 Primary MEM disposition remains required repository cleanup after R5, but it is not a blanket prerequisite for PD/PC. It may proceed in parallel with later personality design or implementation only when exact path, caller, import, retained-authority, and semantic ownership are disjoint. A concrete R6 dependency still blocks the affected PD/PC slice.

For historical context, the plan was originally adopted after:

```text
PR #665  LC-1A Subjective MEM Correct                 merged
PR #667  Documentation Hard Cutover 1C-57             merged
PR #668  ADR / planning adoption                      merged
```

No new one-source-document Documentation Hard Cutover slice is opened after 1C-57.

## Program model

RelayLM uses three coordinated lanes. The first Lane C authority-changing program is complete; the lane is intentionally idle until the post-migration Personality Core gates are satisfied.

```text
Lane C: critical implementation
  legacy program complete:
    LC-1B -> LC-1C -> LC-1D -> LC-1E -> RT-1

  future gated program:
    PC-1 Personality State
      -> PC-2 Working Self
      -> PC-3 SLP automatic personality updates
      -> PC-4 Reflective Distillation

Lane D: documentation canonicalization and historical retirement
  D1 active graph lock
    -> D2 stable-domain synthesis
    -> D3 historical-retirement batches
    -> D4 lifecycle canonicalization after LC-1
    -> D5 Retrieval / Primary MEM canonicalization after RT-1
    -> D6 final retirement and legacy cutover-tool retirement
    -> PD-1 personality responsibility convergence after D6 + Lane R R5
    -> PD-2 exact personality contracts

Lane R: repository maintenance
  R1 classification
    -> R2 test / smoke / validation consolidation
    -> R3 generated navigation and drift checks
    -> R4 low-risk independent package moves
    -> R5 governed core package migration after RT-1
    -> R6 Primary MEM retirement-or-move cleanup
```

Lane C controls authority-changing implementation order. Lanes D and R may proceed in parallel only when path, caller, generated-registry, and semantic-authority ownership are disjoint. PD-1 may not begin until both D6 and Lane R R5 are complete; PC-1 may not begin until PD-2 is complete.

## Universal PR lifecycle

Every PR in every lane follows the same convergence lifecycle:

```text
P0 scope and authority lock
  -> P1 normal implementation
  -> P2 baseline validation and reviewable PR
  -> P3 thorough review
  -> P4 correction and exact-head validation
  -> P5 fresh final review
       -> finding exists? return to P4
       -> clean? proceed to P6
  -> P6 merge gate
  -> P7 expected-head-protected merge
  -> P8 post-merge convergence
```

A passing CI run does not replace P3 or P5. Known in-scope defects cannot be deferred merely to declare the current PR complete.

## Immediate rules

The following rules begin when ADR 0006 merges:

- no new permanent milestone- or slice-ID names in runtime modules, active architecture, contracts, maintained tests, process smoke, permanent CLI entry points, or workflow-owned commands;
- active assets use function- and responsibility-oriented names through their owning atomic migration;
- broad `relaylm/` namespace movement is allowed only through an explicitly governed migration stage such as the now-unblocked Lane R R5; ad-hoc namespace cleanup remains prohibited;
- no permanent import alias, redirect, fallback, dual-read, or dual-write is created merely to ease cleanup;
- every code, document, test, smoke, workflow, and tool is classified before deletion or consolidation;
- planning-only work does not change `docs/PROJECT_STATUS.md`;
- no general `frozen/`, `archive/`, or `legacy/` tree is created for retired Markdown or executable code;
- retired material is deleted from the current tree and recovered through Git history;
- only narrowly typed records with a continuing current function remain in the tree.

## Lane C: critical implementation

### C1: LC-1B Forget

Implement canonical Forget with:

- current-revision and authorization binding;
- retrieval invisibility;
- anti-reformation tombstones;
- deterministic idempotency and recovery;
- exact lineage to the forgotten revision;
- Primary MEM characterization comparison;
- no Purge or heuristic resurrection.

### C2: LC-1C Pin / Unpin

Port pinning without creating ranking authority outside the accepted current revision and lifecycle state.

### C3: LC-1D Restore

Restore only through exact Forget lineage and current authorization. Restore does not imply Purge reversal or heuristic resurrection.

### C4: LC-1E Consolidate

Implement exact source identity, supersession, false-merge controls, audit lineage, and deterministic rollback or recovery boundaries.

### C5: RT-1 Retrieval cutover

RT-1 must establish:

- exact-current Subjective MEM selection;
- lifecycle and mutation fail-closed behavior;
- rebuild-equivalent projections;
- old/new characterization comparison;
- durable content-free usage records;
- writer fencing;
- one ordinary Retrieval authority;
- removal of temporary adapters and replaced readers or writers.

RT-1 is complete. The core memory and Retrieval namespace is no longer protected merely because LC-1/RT-1 authority is still changing; later moves are nevertheless authorized only through Lane R R5/R6 with exact caller, compatibility, retained-authority, and rollback evidence.

### Future Lane C: Personality Core

The next Lane C authority-changing program is not a continuation of RT-1. It opens only after Lane R R5 establishes the governed core package boundary and Lane D completes D6 plus PD-1/PD-2 responsibility and contract convergence.

The ordered implementation program is:

```text
PC-1 Personality State
  -> PC-2 Working Self
  -> PC-3 SLP automatic personality updates
  -> PC-4 Reflective Distillation
```

Personality semantics for this later program remain owned by the accepted [Character Personality and Experience Architecture](../architecture/character/personality-and-experience.md); only repository execution ordering is governed by `docs/architecture/project_execution_plan.md`. This repository-maintenance plan does not define personality semantics or authorize those runtime changes by itself.

## Lane D: documentation canonicalization and historical retirement

### D1: canonical active graph and retained-record lock

D1 defines the intended active documentation graph before large-scale retirement.

The active tree contains current authority and current guidance only:

```text
docs/
  README.md
  PROJECT_STATUS.md
  DOCUMENTATION_MODEL.md
  adr/
  architecture/
  contracts/
  planning/
  reference/
  operations/
  guides/
  release/
  templates/
```

D1 also defines a narrow retained-record allowlist. Representative current record classes are:

```text
release or tag validation receipt
irreversible or stateful migration receipt
security, privacy, or external audit record
current recovery or rollback checkpoint
retirement manifest
machine-readable current registry required by CI or operation
```

`records/` is not a free-form historical archive.

D1 must fix:

- canonical active document list or deterministic generation rules;
- document granularity by owner, update trigger, lifecycle, primary consumer, and authority level;
- retained-record classes and schemas;
- retirement-manifest schema;
- domain synthesis order;
- generic active-document, retained-record, normative-extraction, Git-recoverability, link, authority, and generated-index checks;
- retirement path for bespoke per-document guards, receipts, and ledger entries.

### Canonical granularity

Documents share one permanent active page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

Shared milestone history or similar length is not a reason to combine. Implementation slices do not survive as permanent architecture pages merely because they landed separately.

### D2: stable-domain synthesis

Each domain PR:

1. identifies final active authority and target granularity;
2. enumerates source documents and code, contract, status, and test anchors;
3. extracts durable architecture and exact normative content;
4. creates or revises canonical active documents;
5. distinguishes current implementation from accepted target;
6. classifies any continuing record against the allowlist;
7. repairs current links, routers, and generated navigation;
8. records retiring paths and replacement authorities;
9. deletes consumed historical sources from the current tree;
10. verifies Git recoverability and updates one retirement manifest.

Recommended stable-domain order before LC-1 and RT-1 completion:

```text
D2-A documentation governance and repository system
D2-B runtime pipeline and compile/checkpoint
D2-C Governed Evidence, CTX-OVL, and Shared Assessment
D2-D Character Workspace
D2-E Relationship, Scene, Emotion, and Analyzer governance
D2-F scheduler and local operation
D2-G voice, streaming, TTS, and latency
D2-H stable memory formation and storage boundaries unaffected by LC-1 or RT-1
```

Multiple D2 PRs may coexist only when they share no target document, source ownership, router, generated registry, or semantic authority.

### D3: historical-retirement batches

Retired documentation is deleted from the current tree after replacement and omission checks pass. One generated manifest records fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

A source containing still-live architecture or normative content is not retired until an active replacement or explicit reviewed disposition exists.

No redirect stub, duplicate archived Markdown copy, or second live path is created solely to preserve an old link.

### D4, D5, D6, and Personality Design gates

D4 lifecycle and mutation canonicalization begins only after LC-1B through LC-1E stabilize lifecycle semantics. That prerequisite is complete.

D5 Retrieval and Primary MEM canonicalization begins only after RT-1 establishes one ordinary Retrieval authority. That prerequisite is complete, and Lane D has since advanced into D6; D6 final retirement and legacy cutover-tool retirement continues according to its own current Lane D authority and status.

After D6 and Lane R R5 are both complete, Lane D opens a new bounded Personality Design convergence program:

```text
PD-1 responsibility convergence
  SOUL / SELF boundary
  REL / OTHER MODEL
  GOAL / commitments / prospection
  Character Workspace ownership
  SLP update ownership
  Working Self vs RelayCTX responsibility

PD-2 exact contracts
  personality-state write authority
  provenance / confidence / evidence binding
  Working Self input/output and projection boundary
  SOUL automatic-write prohibition
  Reflective Distillation candidate/adoption boundary
```

PD-1/PD-2 revise only the responsibility nodes actually changed by the accepted personality target. They do not reopen stable Evidence, storage, retrieval, or lifecycle authorities unless an exact dependency requires it.

### D6: final retirement and tooling cleanup

D6 completes the documentation program by:

- retiring remaining non-active documents;
- completing the generated retirement manifest;
- removing retired path routers and hand-maintained long lists;
- retiring bespoke one-document guards, receipts, and active ledger bookkeeping;
- retaining only generic metadata, link, authority, normative-extraction, Git-recoverability, retained-record, and generated-index checks.

#### Remaining D6 forward order

The legacy plan compatibility stubs are retired: the Post-I3 evaluation and work roadmap stub in PR #1017, the RelayMEM MVP implementation plan stub in PR #1035, and the pipeline implementation plan stub in PR #1036. Their exact retired paths, replacement authorities, and recovery identities are recorded in `records/documentation/retirement-manifest.json`. No redirect stub and no bespoke one-document handoff cutover guard remains, and the transitional-asset registry is empty.

The remaining D6 criteria are not met. Documents still live outside both the permanent active locations and frozen evidence, and `docs/architecture/README.md` remains a hand-maintained router list. The ordered remainder is:

```text
D6-R19 root reference relocation
  -> D6-R20 root guide relocation
  -> D6-R21 operator procedure batch
  -> D6-R22 evaluation procedure relocation
  -> D6-R23 smoke snapshot retirement and collection removal
  -> D6-R24 character direction cutover
  -> D6-R25 RelayEMO affect absorption
  -> D6-R26 RelaySOUL durable architecture synthesis
  -> D6-R27 RelaySOUL execution-gate and persistence synthesis
  -> D6-R28 RelaySOUL dry-run and preflight evidence cutover
  -> D6-R29 RelaySOUL experimental and cadence disposition
  -> D6-R30 RelaySOUL router retirement and collection removal
  -> D6-R31 asset collection disposition
  -> D6-R32 strategic direction vision split
  -> D6-R33 architecture router rebuild
  -> D6-R34 D6 completion audit
```

Each slice is one bounded exact-main PR under the ordinary P0-P8 lifecycle:

- **D6-R19** is complete. The root configuration and token-policy references now live at `docs/reference/configuration.md` and `docs/reference/token-policy-profiles.md` as canonical graph documents. Their old root paths are recorded in the retirement manifest, so this bullet names only the current paths.
- **D6-R20** is complete. The OpenWebUI and LM Studio operator setup now lives at `docs/guides/openwebui-lmstudio-integration.md`, a canonical graph document whose name carries no milestone token. Its old root path is recorded in the retirement manifest, so this bullet names only the current path.
- **D6-R21** is complete. The seven operator documents now live in `docs/operations/` as canonical graph documents: the value smoke runbook, troubleshooting, preset checklist, route-differentiation checks, and the three RelayMEM evaluation procedures. Their old collection paths are recorded in the retirement manifest, so this bullet names only current paths.
- **D6-R22** is complete. The LAT-1 retrieval scaling method and Mobile Dogfood observation procedure now live at `docs/operations/lat1-retrieval-scaling.md` and `docs/operations/mobile-dogfood-observation.md` as independent canonical operations documents. Their old collection paths are recorded in the retirement manifest, the empty transitional collection is gone, and D6 remains incomplete until D6-R23 through D6-R34 converge.
- **D6-R23** is complete. The reviewed historical scripts-inventory snapshot now lives at `docs/evidence/evaluations/scripts_inventory.md` as frozen evidence, current row-level reviews use the generated `scripts-inventory` CI artifact, the obsolete smoke router is retired, and the empty transitional collection is gone. D6 remains incomplete; D6-R24 is next.
- **D6-R24** is complete. Rin / ReLM maker-side creative direction now lives at `docs/architecture/character/showcase-character-direction.md`; showcase ownership and publication constraints remain consolidated in `docs/architecture/character-workspace/showcase-starter-product-knowledge.md`. The historical narrative and emptied transitional collection are retired to Git history. D6 remains incomplete; D6-R25 is next.
- **D6-R25** is complete. The durable RelayEMO affect estimation, expression, and modulation architecture lives at `docs/architecture/emotion/affect-modulation.md` as the sole canonical authority; the reviewed section map confirmed that authority already carried the still-durable semantics, so only the optional-affect-probe isolation boundary was added. The old root MVP design source is retired to Git history with its exact recovery identity in the retirement manifest, and its live related-authority consumers now point at the canonical owner. D6 remains incomplete; D6-R26 is next.
- **D6-R26** is complete. Durable RelaySOUL portable identity and source architecture lives at `docs/architecture/character/identity-and-source-authority.md` as the sole canonical authority; the reviewed section map confirmed it already carried most durable semantics, so only the creator-side-meta and renderer-evidence source-authority boundaries were added, with the source-set-candidate and explicit-workflow clarifications. ReLM-specific creative, showcase, and product-knowledge ownership remains with the D6-R24 owners rather than being duplicated into the general identity page. Both transitional RelaySOUL sources are retired to Git history with their exact recovery identities in the retirement manifest, and their live consumers now point at the canonical owner. `docs/relaysoul/` remains a transitional collection for the R27-R30 documents. D6 remains incomplete; D6-R27 is next.
- **D6-R27** is complete. The six transitional RelaySOUL execution and persistence design sources were split by authority rather than moved: exact gate scopes, decision artifacts, allowed flags, and dependency ordering now live at `docs/contracts/relaysoul-execution-gates.md` as the canonical execution-gate authority; exact artifact-persistence identity, the current dry-run helper posture, and the target storage model live at `docs/contracts/relaysoul_persistence_contract.md`, whose current artifact-kind list and ID extraction were repaired to match `relaylm/relaysoul_persistence.py` exactly; conceptual portable-source lifecycle and execution-scope separation remain under `docs/architecture/character/identity-and-source-authority.md`. The proposed gate CLI scripts and implementation ordering were not created and remain Git history only, and the R26-deferred stale three-file target wording is corrected to file-first source ownership across the RelaySOUL contracts without changing current `mvp-soul-0` compatibility behavior. All six sources are retired to Git history with their exact recovery identities in the retirement manifest. `docs/relaysoul/` remains a transitional collection for the R28-R30 documents. D6 remains incomplete; D6-R28 is next.
- **D6-R28** is complete (PR #1098). The four completed RelaySOUL dry-run chain, preflight chain, persistence preflight, and gate design consistency review records are retained under `docs/evidence/implementation/` as frozen bounded implementation evidence, explicitly non-authoritative for current architecture and contracts. Their completion-era current/target statements, next-phase plans, gate-field lists, and component vocabulary are not promoted to current authority and remain recoverable through Git history; the R27 canonical gate, persistence, and identity owners are unchanged. The four old `docs/relaysoul/` paths are retired with exact recovery identities in the retirement manifest and no redirect or stub. `docs/relaysoul/` remains a transitional collection routing the R29 sources and the R30 README. D6 remains incomplete; D6-R29 is next.
- **D6-R29** is complete (PR #1101). The two remaining transitional RelaySOUL child sources were disposed by review rather than moved. `persona_update_cadence_design.md` is absorbed into the existing canonical authorities `docs/architecture/character/personality-and-experience.md` and `docs/architecture/character/identity-and-source-authority.md`, which already own the durable SOUL/SELF/REL/GOAL update-speed boundary, the rule that one unusual turn does not redefine SELF, the validated RelaySLP automatic personality-state write authority, and the rule that ordinary chat does not silently rewrite portable identity; no new architecture owner was created, and the obsolete `persona_plasticity` model and legacy `OUTPUT_POLICY.md`/`RELATIONSHIP_ANCHOR.md` target framing were not promoted. `experimental_soul_replacement_memory_bootstrap_design.md` is retired to Git history only, because its general source, lifecycle, memory-exclusion, disclosure, and relationship principles are already independently canonical and it carries no independent current architecture, implementation, or evidence role; its non-destructive replacement branch, virtual-memory bootstrap, fresh-relationship bootstrap, and staged SR-A..SR-F design were not promoted. Both old `docs/relaysoul/` paths are retired with exact recovery identities in the central retirement manifest and no redirect or stub. The transitional RelaySOUL README router remains for R30. D6 remains incomplete; D6-R30 is next.
- **D6-R30** is complete (PR #1109). The empty transitional RelaySOUL README router is retired to Git history and the now-empty `docs/relaysoul/` collection is removed. Root English/Japanese documentation navigation now points directly to the permanent character identity/source authority, `docs/README.md` routes RelaySOUL content by durable role to character architecture, exact contracts, and implementation evidence, and the semantic-audit required-metadata set no longer treats the retired router as a live document. The router carried no independent semantic authority, no redirect or stub remains, and its exact recovery identity is recorded in the central retirement manifest. D6 remains incomplete; D6-R31 is next.
- **D6-R31** is complete (PR #1114). Current-consumer proof found the README hero used only by the English/Japanese root README hero blocks and found no current consumer for the two Soul Lab reference binaries. The EN/JA hero blocks are removed together; with no current consumer left for any documentation asset, the two asset-collection Markdown notes and all three binaries are retired to Git history with exact recovery identities in the central retirement manifest. No asset router, note, binary, redirect, or stub remains under the former documentation-asset subtree. D6 remains incomplete; D6-R32 is next.
- **D6-R32** is complete (PR #1116). The non-binding post-v0.1 strategic vision is split by adoption state rather than preserved as a strategy document. Current sequencing remains with the Project Execution Plan; local/private/user-owned character-data direction remains with character identity and local-first privacy; generalized external-source ingestion remains with the governed-ingestion concept; continuous/competing-input turn admission remains with the attention/reflex architecture; and public/private persona, fictional shadow, owner-versus-relationship separation, audience-conditioned expression, scene/disclosure narrowing, and social-expression composition remain with their existing character, privacy, scene, memory-scope, and relationship owners. ASR/full-duplex execution, proactive character-initiated contact, publication-oriented longitudinal research, exact broadcast/group taxonomy, collective/N-ary relationship storage, multi-agent runtime, and other unadopted strategic implementation proposals are retired to Git history rather than promoted. The old architecture router and the two canonical documents' transitional source dependencies are removed, exact recovery identity is recorded centrally, no permanent strategy destination is created, and D6 remains incomplete; D6-R33 is next.
- **D6-R33** is complete (PR #1125). The hand-maintained `docs/architecture/README.md` list is replaced by a deterministic navigation-only projection generated from the canonical active architecture graph in bytewise full repository-relative path order. `scripts/relaylm_documentation_governance_validate.py`, under the existing `documentation_governance` owner, is the accepted generator and drift-check implementation: ordinary governance validation rejects direct edits or graph/output divergence as `generated_index_drift`, and `--write-architecture-index` is the sole regeneration path. The stale current-boundary smoke dependency on five hand-maintained README milestone prose anchors is retired while the README remains in current-boundary stale scanning through an empty required-anchor tuple. The projection carries no architecture, contract, status, or sequencing authority. Its removal gate requires every current architecture-navigation consumer to migrate to an accepted replacement and the same reviewed atomic change to remove this path's generated-index validation requirement. No second generator, workflow, or Lane R asset-classification authority was created. D6 remains incomplete; D6-R34 is next.
- **D6-R34** re-runs the five D6 criteria against exact current `main`. D6 is declared complete only when every criterion passes, and PD-1 opens only after that declaration and Lane R R5.

No slice admits `docs/evaluation/` or `docs/strategy/` as a permanent active location, and no slice adds an allowed `relaylm_doc_type` for either. [Documentation Model](../DOCUMENTATION_MODEL.md) is the controlling placement vocabulary and places both under transitional source document types, so entrenching them would put the governance validator in conflict with the placement authority. Both collections disappear through R22 and R24, and R32 closes the last strategy-destination claim without recreating one.

Source-family disposition for every document named above is owned by [Documentation Architecture Inventory](documentation-architecture-inventory.md) Section N. This order authorizes sequencing only; each slice still proves its own current consumers, replacement authority, and retirement record before writing.

## Lane R: repository maintenance

### R1: responsibility classification

Classify each repository asset into its supported responsibility and operational state.

Responsibility classes include:

```text
ordinary_test
process_smoke
operator_cli
offline_tooling
generator
migration_or_maintenance
benchmark
repository_validation
planned_inactive
unclassified
```

Operational states are:

```text
active
transitional
retired
```

An unreferenced asset is only a triage signal. `retired` requires proof that no supported runtime, operator, migration, rollback, characterization, or repository-governance responsibility remains.

### Transitional assets

Characterization, compatibility, rollback, and migration assets remain executable only when they identify:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

### R2: test, smoke, and validator consolidation

Preferred order:

1. remove proven wrapper/core or duplicate-entry-point pairs;
2. move pure regression into maintained pytest or integration suites;
3. retain process-level validation for crash, restart, subprocess, security, concurrency, filesystem, platform, CLI, and operator boundaries;
4. place migration characterization in a maintained location with an explicit removal gate;
5. consolidate repository validators and generated registries;
6. update workflow invocations only after one canonical entry point is selected;
7. rename retained assets by supported function through their owning atomic migration.

Do not convert operator commands, process-isolation smoke, migrations, generators, or benchmarks into pytest solely to reduce file count.

Retired code, smoke, wrappers, migrations, and tools are deleted from the current tree and remain recoverable through Git history. A general executable archive is prohibited.

### R3: generated navigation

After D1 fixes active placement and record classes:

- keep `docs/README.md` curated and short;
- generate active architecture, ADR, contract, planning, reference, and operations indexes;
- generate retained-record navigation separately;
- make generated files navigation-only;
- add reproducibility and drift checks;
- remove hand-maintained long lists only after equivalence is reviewed.

### R4: low-risk package moves

A package move may occur before RT-1 only when it does not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

Candidate domains may include:

```text
clients/
tokens/
diagnostics/
scheduler/
interfaces/openai/
interfaces/soul_lab/
cli/
character/workspace/
```

Each move must preserve console scripts, `python -m` entry points, dynamic callers, subprocess roots, and operator invocations, and must not create a second public import authority.

### R5: governed core package migration

RT-1 is complete, so the R5 prerequisite is satisfied. R5 is the next governed core repository migration and proceeds in dependency order:

```text
evidence
  -> context overlay
  -> shared assessment
  -> subjective memory
  -> retrieval
  -> request and product interfaces
```

Each R5 wave must preserve one semantic authority, migrate callers atomically, reject old-path forwarding aliases unless a concrete governed compatibility consumer exists, and prove negative old-path/import references before its merge. R5 establishes the stable package/dependency substrate required before PD-1/PD-2 can freeze the new personality responsibility graph.

The Evidence wave completed in PR #947 with exact resulting main `ab7b07cfdd7a4886d71c335a55011da87c6572f7`; `relaylm.evidence` is its sole canonical package. The context-overlay wave completed in PR #951 with exact resulting main `1529bf38220e489300fdff322865a11a4d66406f`; `relaylm.context_overlay` is its sole canonical import package. The persisted `relaylm.ctx_ovl_*` schema identities remain byte-stable data-contract identities, not Python import compatibility surfaces. No old-path alias remains. The Shared Assessment wave completed in PR #956 with exact resulting main `5f85995678d01c8a0e4853fd38ae23eaa15bd303`; `relaylm.shared_assessment` is its sole canonical Python package, while persisted `relaylm.shared_assessment_*` schema identities remain unchanged. The Subjective Memory models slice completed in PR #966 with exact resulting main `1153af8b001b36ec625304234178f27bd7229b4f`; `relaylm.subjective_mem.models` is the sole model owner and persisted schema identities remain unchanged. The Subjective Memory commit-owner slice completed in PR #968 with exact resulting main `7399f7b0fa82e138a32406ef25a8930741916dd9`; `relaylm.subjective_mem.commit`, `commit_io`, and `commit_runtime` are canonical while persisted platform/schema identities remain unchanged. The Subjective Memory Markdown-owner slice completed in PR #971 with exact resulting main `6f7e51c21cae4aca0c26a4b1e1bbde7e11e1a8d1`; `relaylm.subjective_mem.markdown` is canonical while persisted Markdown schema identities remain unchanged. The Subjective Memory lifecycle-record slice completed in PR #973 with exact resulting main `6d3394fbe2d107c0f355161423d808432d581705`; `relaylm.subjective_mem.lifecycle` is canonical while persisted lifecycle schema identities remain unchanged. The Subjective Memory lifecycle-authority slice completed in PR #975 with exact resulting main `f64c60ce11173a050e2250e4ef721331c1f40f9e`; `relaylm.subjective_mem.lifecycle_authority` is canonical with one committed-predecessor evaluator. The Subjective Memory lifecycle-engine slice completed in PR #978 with exact resulting main `154b4e280e43c41b096116cffe51027b90654371`; `relaylm.subjective_mem.lifecycle_engine` is the sole lifecycle publication, replay, and recovery engine. The Subjective Memory lifecycle-runtime slice completed in PR #981 with exact resulting main `691190bdec0eb1fd64167259f2dc47b647ad405d`; `relaylm.subjective_mem.lifecycle_runtime` is the canonical Correct/lifecycle operation owner. The Subjective Memory Forget-record slice completed in PR #988 with exact resulting main `76c4907c1f990ee0406a543dc24af2d6a56b5e4c`; `relaylm.subjective_mem.forget` is the canonical storage-neutral Forget record owner while persisted tombstone schema identities remain unchanged. The Subjective Memory Forget-runtime slice completed in PR #1004 with exact resulting main `e4f7cf825f91087a936dcbb2a2600aece26883ff`; `relaylm.subjective_mem.forget_runtime` is the canonical Forget execution and recovery owner. The Subjective Memory reformation-authority slice completed in PR #1007 with exact resulting main `9b3f6db67747849a4ae2d1b17df681ffe59df043`; `relaylm.subjective_mem.reformation` is the sole anti-reformation semantic evaluator. The Subjective Memory Pin-record slice completed in PR #1009 with exact resulting main `2fdd42b63a1a25cd41375ba04a4ef81406644719`; `relaylm.subjective_mem.pin` is the canonical storage-neutral Pin/Unpin record owner. The Subjective Memory Pin-runtime slice completed in PR #1019 with exact resulting main `5bf2cafb1663f4716b5b8e60f004f2f5c5eec1f0`; `relaylm.subjective_mem.pin_runtime` is the canonical Pin/Unpin execution and recovery owner. The Subjective Memory Restore-record slice completed in PR #1021 with exact resulting main `fadb4193ef14a14522513d020f9038bac2af49e2`; `relaylm.subjective_mem.restore` is the canonical storage-neutral Restore record owner. The Subjective Memory Restore-plan slice completed in PR #1023 with exact resulting main `5e72cbb1d22ca2b15f199a462ae672b0deda1aab`; `relaylm.subjective_mem.restore_plan` is the canonical Restore publication-planning owner. The Subjective Memory Restore-replay slice completed in PR #1026 with exact resulting main `1a663d10699a277f3b4edc480bb9b8811144f4da`; `relaylm.subjective_mem.restore_replay` is the canonical Restore replay-validation owner. The Subjective Memory Restore-runtime slice completed in PR #1029 with exact resulting main `02f7f27e099f96157d313ce6f6a3a6b358d29f9a`; `relaylm.subjective_mem.restore_runtime` is the canonical Restore execution and recovery owner. The Subjective Memory tombstone-release slice completed in PR #1031 with exact resulting main `38f51919751956c68c30081fef2bff0a764c0fed`; `relaylm.subjective_mem.tombstone_release` is the canonical tombstone-release record owner. The Subjective Memory Consolidate-record slice completed in PR #1034 with exact resulting main `e53a4549e19a102db4d5a2a2cdf92e3b0d02e6ac`; `relaylm.subjective_mem.consolidate` is the canonical storage-neutral Consolidate record owner. The Subjective Memory Consolidate-runtime slice completed in PR #1038 with exact resulting main `1e3092464e69906f4bdefb376f10328bf475a067`; `relaylm.subjective_mem.consolidate_runtime` is the canonical Consolidate execution and recovery owner. The Subjective Memory create-runtime slice completed in PR #1040 with exact resulting main `a69c65c8506628d8f2a57edfa91315557a743260`; `relaylm.subjective_mem.create_runtime` is the canonical one-shot create transaction owner. The Subjective Memory Retrieval-record slice completed in PR #1043 with exact resulting main `dc55872999f0fc6083ae2ec7f963d0fbb540b6a1`; `relaylm.subjective_mem.retrieval` is the canonical storage-neutral Retrieval contract and canonical-digest owner. The Subjective Memory Retrieval-projection slice completed in PR #1052 with exact resulting main `956b8a2e4d9f0075d7bc34aa6a86301c4674b555`; `relaylm.subjective_mem.retrieval_projection` is the canonical disposable projection builder. The Subjective Memory Retrieval-projection-store slice completed in PR #1054 with exact resulting main `ababffff4d8d87da999874e6439f44d8552b5986`; `relaylm.subjective_mem.retrieval_projection_store` is the canonical disposable projection bundle store. The Subjective Memory Retrieval-selection slice completed in PR #1056 with exact resulting main `93a4ba00f2984143b665483f6db19bc6e5bc95cd`; `relaylm.subjective_mem.retrieval_selection` is the canonical bounded selection owner. The Subjective Memory Retrieval-usage-ledger slice completed in PR #1059 with exact resulting main `b858e89e3ab895ebf564bab5dfec4e419a4b983d`; `relaylm.subjective_mem.retrieval_usage_ledger` is the canonical durable content-free usage-event owner. The Subjective Memory Retrieval-cutover-owner slice completed in PR #1061 with exact resulting main `17433b016fb86fabe162d68d6f2a48df715743fd`; `relaylm.subjective_mem.retrieval_cutover` is the sole public semantic cutover owner and no old-path alias remains. The Retrieval-priority owner slice completed in PR #1063 with exact resulting main `8bc7ba561cdd7c514eebffb5e15a80d77529e05e`; `relaylm.retrieval.priority` is canonical and no old-path alias remains. The Retrieval-snippet owner slice completed in PR #1065 with exact resulting main `4faa64c49aa0b65e3f4db7e098327d88da1c2ccd`; `relaylm.retrieval.snippet` is canonical and no old-path alias remains. The Retrieval-query-analyzer owner slice completed in PR #1069 with exact resulting main `c12975a5f36c21bdaa599650e9202cf362da9898`; `relaylm.retrieval.query_analyzer` is canonical and no old-path alias remains. The Retrieval-candidate owner slice completed in PR #1071 with exact resulting main `51192866aef4301117da464150fc9d50c8219d2c`; `relaylm.retrieval.candidates` is canonical and no old-path alias remains. The Retrieval dry-run owner slice completed in PR #1075 with exact resulting main `adeac0d65ecd9bb3e406c57d6a63fff55da00f8e`; `relaylm.retrieval.dry_run` is canonical and no old-path alias remains. The Subjective Memory Retrieval-runtime-projection owner slice completed in PR #1077 with exact resulting main `c6764bc97510a2c2b17fa007e726a7c3c4b25287`; `relaylm.subjective_mem.retrieval_runtime_projection` is canonical and no old-path alias remains. The ordinary Retrieval-runtime owner slice completed in PR #1080 with exact resulting main `21a98ed1ce98773ea8e8785a9e28e6bbc44c5860`; `relaylm.retrieval.runtime` is the sole semantic ordinary Retrieval runtime owner, no concrete governed consumer required an old-path facade, no old-path alias remains, and helper consumers use their canonical lower owners. The Subjective Memory Retrieval-cutover-activation owner slice completed in PR #1083 with exact resulting main `343163b17b2c69f7c6a51234233024d5a2ce2914`; `relaylm.subjective_mem.retrieval_cutover_activation` is canonical with no old-path alias while `relaylm.subjective_mem.retrieval_cutover` remains sole semantic cutover authority. The inert Retrieval-priority compatibility no-op retired in PR #1085 with exact resulting main `c27ce58911a5abd4562905b562218d3e9ee7fce6`; its sole purity-smoke consumer was removed and canonical `relaylm.retrieval.priority` behavior is unchanged. The R5 Retrieval wave is complete: every retained non-Primary Retrieval semantic owner is in `relaylm.retrieval` or `relaylm.subjective_mem`, no old-path alias remains, and Primary retrieval eligibility is reserved for R6 disposition. The OpenAI client-message canonicalization owner slice completed in PR #1087 with exact resulting main `66c588be9231ccf74d10959c53a84a99628d110b`; `relaylm.interfaces.openai.client_message_canonicalization` is canonical with unchanged persisted schema identity and no old-path alias. The OpenAI client-instruction extraction owner slice completed in PR #1091 with exact resulting main `70caf9b30af9e1a2403a2c239cdc468e54c4f312`; `relaylm.interfaces.openai.client_instruction_extraction` is canonical with unchanged `client_instruction_extraction_dry_run.v0` schema identity and no old-path alias. The OpenAI client-instruction identity owner slice completed in PR #1093 with exact resulting main `f7089100661cea040ea0267c4fa8727aed6915be`; `relaylm.interfaces.openai.client_instruction_identity` is canonical with unchanged `client_instruction_identity.v0` schema identity, unchanged runtime-private/content-bearing non-projection boundary, and no old-path alias. The OpenAI client-instruction source owner slice completed in PR #1097 with exact resulting main `70fc0ab019b269b4ec42f02e74b615d56fc55b0a`; `relaylm.interfaces.openai.client_instruction_source` is canonical with unchanged `client_instruction_source.v1` schema identity, unchanged explicit provenance envelope, system/developer role restriction, runtime-private selection, and fail-closed blocked-reason semantics, and no old-path alias. The OpenAI client-instruction cache lookup owner slice completed in PR #1102 with exact resulting main `606da7576d4d1d0fbda9d0be4da27a8540939e59`; `relaylm.interfaces.openai.client_instruction_cache_lookup` is canonical with unchanged `client_instruction_cache_lookup.v0` and `relaylm.client_instruction_cache.v0` schema identities, unchanged runtime-private/content-bearing result and fail-closed validation boundaries, and no old-path alias. The OpenAI client-instruction cache reader owner slice completed in PR #1104 with exact resulting main `b8f063e0a4d1e725263f5de8a811aaa2bee066ba`; `relaylm.interfaces.openai.client_instruction_cache_reader` is canonical with unchanged `client_instruction_cache_reader.v0` schema identity, read-only filesystem behavior, bounded-read and path-hardening policies, runtime-private/content-bearing result boundary, and no old-path alias. The OpenAI client-instruction cache lookup runtime owner slice completed in PR #1110 with exact resulting main `cc7af496d00c18bc4f6be52be39d099777db957e`; `relaylm.interfaces.openai.client_instruction_cache_lookup_runtime` is canonical with unchanged `client_instruction_cache_lookup_runtime.v0` schema identity, fail-closed read-only preparation, runtime-private non-applied content-bearing results, content-free diagnostics, and no old-path alias. The OpenAI client-instruction typed-parse owner slice completed in PR #1112 with exact resulting main `81fd9b3badc7c359025a53379d7e8a8a9ab41ea5`; `relaylm.interfaces.openai.client_instruction_typed_parse` is canonical with unchanged `client_instruction_parse.v1` and `client_instruction_typed_parse_runtime.v0` schema identities, unchanged runtime-private content-bearing non-persisted artifact boundary, fail-closed allowlist validation, content-free diagnostics, and no old-path alias. The OpenAI client-instruction cache-write preflight owner slice completed in PR #1118 with exact resulting main `26a6c5216bba2d4d2de868a9dfee3ae002167f52`; `relaylm.interfaces.openai.client_instruction_cache_write` is canonical with unchanged `client_instruction_cache_write_preflight.v0`, `relaylm.client_instruction_cache.v0`, `client_instruction_cache_key.v0`, and `client_instruction_authority.v1` schema and policy identities, unchanged default-off dry-run-first bounded atomic-write semantics, unchanged runtime-private result and content-free diagnostic boundaries, and no old-path alias or forwarder. The OpenAI client-instruction cache-write runtime orchestration slice completed in PR #1121 with exact resulting main `687dd25152371160f219c1d2272aa156581e2888`; `relaylm.interfaces.openai.client_instruction_cache_write_runtime` is canonical with unchanged trusted in-process typed-parse sourcing, instruction-identity dependency, default-off dry-run-first gates, preflight/write delegation, runtime-private result boundary, content-free diagnostics, fail-closed preparation, and no old-path alias or forwarder. The OpenAI client-history exclusion preflight owner slice completed in PR #1123 with exact resulting main `0d3514faebacdbdc8536778d238647a036e1f728`; `relaylm.interfaces.openai.client_history_exclusion_preflight` is canonical with unchanged `client_history_exclusion_preflight.v0` schema identity, runtime-private content-bearing current-user candidate, content-free diagnostics, managed/pass-through classification, cache hit/miss/blocked resolution, active-tool fail-closed semantics, and no old-path alias or forwarder. The OpenAI client-history exclusion v0 pure apply owner slice completed in PR #1126 with exact resulting main `77c6ec6ead5717d9f628af02fd45ce27aadd29ad`; `relaylm.interfaces.openai.client_history_exclusion_apply` is canonical with unchanged `client_history_exclusion_apply.v0` schema identity, runtime-private content-bearing forwarded-payload candidate, content-free diagnostics and node projection, no-instruction semantics, managed/pass-through classification, default-off dry-run-only posture, exact current-user preservation, active-tool fail-closed behavior, no raw-history fallback, and no old-path alias or forwarder. The OpenAI client-history exclusion v1 typed result/schema owner slice completed in PR #1128 with exact resulting main `2f1fe000199328a6c934229ab007f91a8f0e6e08`; `relaylm.interfaces.openai.client_history_exclusion_apply_v1_types` is canonical with unchanged `client_history_exclusion_apply.v1` schema identity, exact status/resolution/source/blocked-reason vocabularies, runtime-private content-bearing forwarded-payload result, forced-false raw-instruction, RelayLM-control, cache-entry-content, and cache-projection flags, existing result-builder semantics, and no old-path alias or forwarder. The OpenAI client-history exclusion v1 validation owner slice completed in PR #1130 with exact resulting main `4b4006e4215e95e0520d001b0ab3a1f3e6f3539a`; `relaylm.interfaces.openai.client_history_exclusion_apply_v1_validation` is canonical with unchanged validated-input shape, preflight and instruction-identity schema/type/runtime-private checks, candidate count/source and current-user consistency checks, active-tool fail-closed behavior, instruction-evidence and compiler-block validation, blocked-reason semantics, runtime-private content-bearing input boundary, content-free public diagnostic boundary, and no old-path alias or forwarder. The OpenAI client-history exclusion v1 prepare owner slice completed in PR #1132 with exact resulting main `2983720f38e8290c884cbc9f8191a11ce6a2b63e`; `relaylm.interfaces.openai.client_history_exclusion_apply_v1_prepare` is canonical with unchanged validated-input consumption, explicit provenance, identity/source and preflight/current-user consistency, compiler-block and instruction-evidence construction, active-tool fail-closed behavior, runtime-private content-bearing prepared state, forwarding/cache safety and blocked-reason semantics, content-free public boundary, and no old-path alias or forwarder. The OpenAI client-history exclusion v1 render owner slice completed in PR #1135 with exact resulting main `b43039a43e5c391d1d350a0b7ececa3d14a16aba`; `relaylm.interfaces.openai.client_history_exclusion_apply_v1_render` is canonical with unchanged rendered-result shape, prepared-artifact dependency, instruction-source and RelayLM-control stripping, request-compiler rendering and evidence escaping/bounds, exact current-user preservation, runtime-private content-bearing candidate, forwarding/cache safety, fail-closed render and content-free public boundaries, and no old-path alias or forwarder. The OpenAI client-history exclusion v1 runtime selection owner slice completed in PR #1137 with exact resulting main `74fc3dc6c9e520d8321dc92814fc49394f21b863`; `relaylm.interfaces.openai.client_history_exclusion_apply_v1_runtime` is canonical with unchanged request-local eligibility from canonical preflight and instruction identity plus the existing bounded role classification, no payload mutation, persisted/public content, result-union, pipeline-node, backend-block, or backend-forward authority, and no old-path alias or forwarder. The OpenAI client-history exclusion outer apply runtime owner slice completed in PR #1139 with exact resulting main `d8f8a958986302eac6995fd59ce79f0c09f894bf`; `relaylm.interfaces.openai.client_history_exclusion_apply_runtime` is canonical and owns the v0/v1 result union, request-local idempotent apply orchestration, detached forwarded-payload mutation, pipeline-node publication, and content-free backend-block/failure projection with unchanged managed/pass-through, default-off dry-run, privacy, and fail-closed boundaries and no old-path alias or forwarder. The OpenAI client-history backend-forward gate policy slice completed in PR #1141 with exact resulting main `bb6aec1f4b5d4b8101221aed69db1b2dbeef75c1`; `relaylm.interfaces.openai.client_history_exclusion_backend_forward_gate` is canonical and consumes the outer-runtime result plus exact forwarded payload to produce one content-free allow/block decision and bounded failure reason. Adapter transport retains active-context lookup and `BackendRequestError` ownership, applies the same fail-closed policy before stream and non-stream I/O, and contains no duplicate policy or reverse interface-to-adapter dependency. The OpenAI backend request payload projection owner slice completed in PR #1144 with exact resulting main `05d9a6a09bb7c29a5fd457fe9c071663fda26e75`; `relaylm.interfaces.openai.backend_request_payload` is canonical and owns the detached stream/non-stream backend-bound payload construction with unchanged pass-through copying, managed RelayLM-control stripping, backend-model projection, input non-mutation, and runtime-private content-bearing boundaries. The exact forwarded payload still reaches the backend-forward gate before projection, adapter retains transport and backend-I/O authority, and no duplicate owner, old-path alias, or forwarder exists. The OpenAI client-instruction evidence owner slice completed in PR #1146 with exact resulting main `d1686f0c20575eff31289a767eeb4ff32fdfa6f6`; `relaylm.interfaces.openai.client_instruction_evidence` is canonical and owns deterministic low-trust request-local content-bearing evidence-block construction, the shared rendered-size limit, and fail-closed exactly-one legacy typed-block replacement while generic compiler structures, request-compiler rendering/enforcement, and v1 preparation orchestration remain separate; no old-path alias or forwarder exists. Remaining request/product interface candidates require fresh P0/P1 evidence; `client_instruction_relayscn_projection` remains independent.

### R6: Primary MEM disposition

Do not automatically move every Primary MEM module. Classify each remaining asset as:

```text
retired_after_cutover
migration_or_characterization_dependency
rollback_dependency
operator_or_recovery_dependency
retained_current_component
```

Delete only through reviewed atomic waves. Move only the subset that remains a supported current component.

R6 follows R5 as repository cleanup. It is not a blanket gate on Personality Design or Personality Core, because the ordinary Primary reader has already retired; however any PD/PC slice that touches a still-undisposed Primary path, caller, recovery surface, or retained authority must wait for that exact R6 disposition.

## Post-R5 handoff to Personality Design and Personality Core

Repository maintenance does not own the new character semantics. Its handoff is structural:

```text
Lane R R5 complete
       +
Lane D D6 complete
       ↓
Lane D PD-1 responsibility convergence
       ↓
Lane D PD-2 exact contracts
       ↓
Lane C PC-1 Personality State
       ↓
Lane C PC-2 Working Self
       ↓
Lane C PC-3 SLP automatic personality updates
       ↓
Lane C PC-4 Reflective Distillation
       ↓
9B end-to-end evaluation
       ↓
Character Presence
```

This handoff preserves the accepted distinction between repository structure, documentation/contract authority, and authority-changing runtime implementation. Package movement must not silently implement SELF, GOAL, OTHER MODEL, Working Self, SLP personality writes, or Reflective Distillation.

## Parallel portfolio

Default capacity:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three PRs are a ceiling, not a target. A new PR requires a bounded scope, owner, exact path and authority non-overlap, and a validation plan.

Until PD-2 completes, the Lane C slot has no Personality Core work merely because capacity is free. R6, remaining Lane D canonicalization, and later PD work may overlap only under the ordinary path/authority disjointness rules.

Two items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, imports, or precedence rules.

## Atomic PR requirements

Every execution PR states:

```text
lane and stage
scope and exact paths
current responsibility and callers
accepted replacement mapping
behavioral and authority non-goals
public and operator entry-point effect
state migration or no-state rationale
compatibility and removal gate
validation matrix
rollback boundary
negative-reference checks
parallel-safety analysis
current P0-P8 stage
```

A documentation synthesis or retirement PR additionally states:

```text
canonical target documents
source-document set
normative extraction result
retained-record decisions
retiring-path manifest effect
Git-recoverability proof
retired bespoke guards or receipts
```

## Completion criteria

The program is complete only when:

- permanent milestone-oriented naming is rejected;
- active documentation is complete at stable responsibility-level granularity;
- retired documentation and code are absent from the current tree and recoverable through Git;
- retained records are narrowly typed and current-function-owned;
- one-document cutover guards, receipts, and ledger growth are retired;
- generated navigation is reproducible and drift-checked;
- retained scripts have one clear responsibility and canonical invocation;
- ordinary tests, process smoke, transitional characterization, operator tools, and repository validators are distinguishable;
- accepted domain packages enforce dependency direction;
- Subjective MEM and Retrieval have one canonical package and authority path;
- remaining Primary MEM assets have an explicit retained, transitional, rollback, or retired disposition;
- no permanent migration aliases or duplicate semantic authorities remain.
