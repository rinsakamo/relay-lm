---
relaylm_doc_type: planning
relaylm_authority: documentation_architecture_source_family_inventory_and_disposition_plan
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - target architecture graph changes
  - cutover inventory dry-run finds an unclassified source family
  - a source document gains or loses normative authority before cutover
relaylm_not_authoritative_for:
  - current documentation placement
  - exact contract wording
  - current runtime implementation status
  - proof that any source file has moved
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
relaylm_related_authority:
  - documentation-target-architecture-graph.md
  - documentation-placement-decisions.md
---
# Documentation Architecture Inventory

This document is the Preparation B decision inventory for restructuring RelayLM design documentation. It assigns current source families to target authority, granularity, and disposition. It does not move files, rewrite contracts, or replace the commit-fixed file-level inventory that Preparation C must generate.

## Baseline and scope

Baseline main commit: `5cfe84fa5831c468a420f542fa8e7ecbebbde8cc`.

Primary scope:

- `docs/architecture/**/*.md`
- architecture-like files at `docs/*.md`
- `docs/relaysoul/**/*.md`
- exact design contracts already under `docs/contracts/**/*.md`
- architecture, contract, planning, strategy, evaluation, and evidence links exposed by current documentation indexes

The inventory is intentionally organized by authority family rather than by current directory. Preparation C must enumerate every baseline file and map it to one of the dispositions defined here.

## Disposition vocabulary

- `retained`: same canonical path and authority.
- `moved`: authority and structure are already suitable; only canonical path changes.
- `split`: one source contains multiple independent authorities.
- `synthesized`: multiple sources form one new canonical document.
- `absorbed`: useful content is incorporated into another canonical document.
- `rebuilt_verbatim`: normative contract blocks move without paraphrase and are digest-verified.
- `deleted_git_history_only`: no continuing active or evidence value.
- `evidence_retained`: source remains as historical evidence under `docs/evidence/`.

A single source may have a primary disposition plus extracted `rebuilt_verbatim` contract blocks.

## Ordered classification rules

Preparation C applies these rules in order and fails closed when no rule or explicit exception matches.

1. `docs/architecture/README.md` is a router source, not architecture authority.
2. Existing `docs/contracts/` documents remain contract candidates and are reviewed for duplication, not relocated merely for consistency.
3. Files with exact schemas, fields, gates, states, transitions, artifacts, APIs, or must/must-not boundaries are contract sources regardless of filename.
4. Files whose durable value is a completed slice, handoff, audit, validation, evaluation, or dated result are evidence sources.
5. Files whose authority is sequence, dependency, roadmap, or migration timing are planning sources.
6. Files whose authority is current/target interpretation, glossary, fields, or lookup information are reference sources.
7. Files whose authority is non-binding future direction are strategy sources. `docs/strategy/` is a transitional placement, so their adopted durable content is split to a permanent planning, reference, or concept-policy owner and their historical direction is retired to Git.
8. Remaining durable design content is mapped to the target system, subsystem, or concept/policy graph.
9. Milestone, phase, wave, PR, and date names do not survive as permanent architecture names.
10. A source with multiple owners, update triggers, lifecycles, or independent consumers is split before placement.

## A. Documentation governance and routers

| Current source | Actual authority | Target | Disposition |
|---|---|---|---|
| `docs/README.md` | repository documentation router | `docs/README.md` | retained, later rewritten as role-based router |
| `docs/architecture/README.md` | current mixed architecture/evidence router | `docs/architecture/README.md` | retained path, rebuilt after graph activation |
| `docs/DOCUMENTATION_MODEL.md` | documentation model | same | retained |
| `docs/adr/*.md` | durable decisions | `docs/adr/` | retained paths until one-time ADR canonicalization |
| `docs/proposals/documentation_restructure_proposal.md` | accepted proposal evidence | `docs/evidence/proposals/` | moved after proposal lifecycle activation |

The current architecture README is inventory evidence, not proof that every linked file belongs in architecture.

## B. Repository and pipeline system architecture

Target synthesis families:

| Source family | Representative current sources | Target authority | Disposition |
|---|---|---|---|
| repository system context | `docs/architecture/pipeline_responsibility_design.md`, `docs/architecture/safe_soul_scene_ctx_compile_chain.md`, current architecture index responsibility text | `architecture/system-overview.md` and `architecture/pipeline-responsibilities.md` | synthesized |
| runtime compile and checkpoint boundary | `docs/runtime_compile_gate_design.md`, `docs/relayrun_runtime_checkpoint_design.md`, `docs/architecture/product_runtime_hardening.md` | `architecture/runtime/compile-and-checkpoint.md` | synthesized; exact gates extracted to contracts |
| context assembly | `docs/architecture/context_packing_design.md`, `docs/architecture/relayctx_wake_loop_design.md` | `architecture/context/context-assembly.md` | synthesized |
| reflex/attention layer | `docs/architecture/relayatn_reflex_layer_design.md` | `architecture/attention/reflex-layer.md` | moved or lightly normalized |
| response-side style | `docs/architecture/relayemo_return_side_style_adapter_design.md` and response-stage handoffs | `architecture/emotion/affect-modulation.md` and `architecture/runtime/request-response-pipeline.md` | split/synthesized |

`pipeline_responsibility_design.md` was the strongest pre-cutover responsibility source. D2-B2b synthesized its durable content into `system-overview.md`, `pipeline-responsibilities.md`, mode-specific runtime pages, and exact contracts; D2-B2b4c28 retires the transitional path after active-consumer migration.

## C. Character Workspace and character-source architecture

| Source family | Representative current sources | Target authority | Disposition |
|---|---|---|---|
| file-first workspace system | `file_first_character_workspace_design.md`, `safe_soul_scene_ctx_compile_chain.md` | `architecture/character-workspace/system.md` | synthesized |
| source tree/parser/compiler | `cw_a1_file_first_source_tree_parser_contracts.md`, `cw_a2_workspace_compiler_projections.md`, relevant RelaySOUL source-set drafts | `architecture/character-workspace/source-compiler.md` | synthesized; exact source/schema blocks rebuilt as contracts |
| creation/templates/import | `character_template_creation_flow.md`, `cw_a5_character_creation_templates_showcase_import.md` | `architecture/character-workspace/creation-and-import.md` | synthesized; implementation result retained as evidence |
| maintenance candidates | `cw_a4_slp_workspace_maintenance_candidates.md` | `architecture/character-workspace/maintenance-candidates.md` | split into concept policy, contract, and evidence |
| UI presentation | `cw_a3_character_workspace_ui_rebuild.md`, SOUL Lab UI sources | `architecture/ui/character-workspace.md` | synthesized |
| durable character identity | `docs/relaysoul/relaysoul_design.md`, approved file-first source-set rationale | `architecture/character/identity-and-source-authority.md` | synthesized |
| experimental character replacement/bootstrap | `docs/relaysoul/experimental_soul_replacement_memory_bootstrap_design.md` | none as an independent current architecture; the overlapping stable source, lifecycle, memory-exclusion, and disclosure responsibilities remain with their already-canonical owners | `deleted_git_history_only`; D6-R29 resolved the placeholder by classifying the actual authority as unimplemented post-MVP experimental replacement/bootstrap design. The non-destructive replacement branch, virtual-memory bootstrap, fresh-relationship bootstrap, and staged SR-A..SR-F sequence are future design and are not promoted; the source carries no implementation or evidence role |
| durable persona update cadence | `docs/relaysoul/persona_update_cadence_design.md` | `architecture/character/personality-and-experience.md`, `architecture/character/identity-and-source-authority.md` | absorbed; D6-R29 classified the actual authority as legacy durable-persona proposal cadence/plasticity design. Current SOUL/SELF/REL/GOAL update-speed semantics and the validated RelaySLP write authority supersede the old compatibility-source and `persona_plasticity` framing, which is not promoted |

Draft/showcase fixtures and templates do not become architecture merely because they explain intended usage.

## D. Memory, observation, belief, and retrieval architecture

| Source family | Representative current sources | Target authority | Disposition |
|---|---|---|---|
| memory system | `memory_lifecycle_design.md`, `relaymem_mvp_design.md`, `relaymem_slp_execution_design.md`, `relaymem_slp_current_target.md` | `architecture/memory/system.md` | synthesized; current/target interpretation moves to reference |
| formation pipeline | Phase 6 A/B/C sources, RelayMEM M3 formation/writer sources, integration I1 source | `architecture/memory/formation.md` | synthesized; exact queue/worker contracts rebuilt; slice records to evidence |
| retrieval and grounding | `e1r4_retrieval_response_grounding.md`, `e1r5_primary_mem_recall_candidate_bridge.md`, ACG retrieval sources | `architecture/memory/retrieval-and-grounding.md` | synthesized; current slice evidence retained |
| mutation governance | I-3 Correct, I-4 Forget/Hide, I-5 Pin/Unpin, I-7 Held Apply/Discard sources | `architecture/memory/mutation-governance.md` | synthesized; exact commands/states extracted to contracts |
| pinned memory | `pinned_normal_memory_pages.md`, I-5 sources | `architecture/memory/pinned-memory.md` | concept-policy synthesis |
| scene-scoped memory | `scene_memory_scope_design.md`, `scene_memory_scope_current_target.md` | `architecture/memory/scene-memory-scope.md` | design moved; interpretation to reference |
| observation and character belief | `character_belief_relationship_dynamics_design.md`, ADR character-conditioned belief | `architecture/memory/observation-and-character-belief.md` | synthesized concept policy; ADR remains decision authority |
| index/log reconciliation | `relaymem_m3f_primary_index_log_reconciliation_preflight.md`, `relaymem_m3g_primary_index_log_reconciliation_apply.md`, `relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md` | architecture content absorbed into memory storage/recovery; records to evidence | split/absorbed/evidence_retained |

### Phase 6 and Primary MEM source disposition

The following filename families are not permanent architecture names:

- `phase6a*`, `phase6b*`, `phase6c*`
- `integration_i1_*`
- `phase_i2_*`, `phase_i3_*`, `phase_i4*`, `phase_i5*`, `phase_i7*`
- `i1g*`
- `relaymem_m3*`

Their stable responsibilities are synthesized into memory system, formation, retrieval, mutation, storage/recovery, and scheduler pages. Their exact normative blocks are rebuilt under contracts. Their completed implementation and validation narratives become `docs/evidence/implementation/` or `docs/evidence/evaluations/`.

## E. Relationship, scene, emotion, attention, and social expression

| Source family | Representative current sources | Target authority | Disposition |
|---|---|---|---|
| relationship state | `relayrel_relationship_design.md` | `architecture/relationship/relationship-state.md` | moved or split if exact file schema is embedded |
| scene model | scene portions of workspace, ACG-6, P0 ordering, SCN documents | `architecture/scene/scene-model.md` | synthesized |
| emotion modulation | RelayEMO design/cleanup/style sources | `architecture/emotion/affect-modulation.md` | synthesized |
| social expression | `character_belief_relationship_dynamics_design.md` | `architecture/relationship/social-expression.md` | split from belief semantics and synthesized |
| request ordering | `p0_relayrel_relayscn_relayemo_ordering_fix.md`, pipeline design | `architecture/pipeline-responsibilities.md` | architecture absorbed; completed fix to evidence |
| analyzer-governed scene classification | `acg6_scene_wiki_classifier.md` | scene model plus analyzer policy | split; implementation to evidence |

## F. Analyzer and candidate governance

| Current source family | Target | Disposition |
|---|---|---|
| `analyzer_candidate_governance.md` | `architecture/analyzers/candidate-governance.md` plus any remaining roadmap in planning | split |
| `acg1_analyzer_candidate_governance_contract.md` | `contracts/analyzer-candidate.md` | rebuilt_verbatim |
| `acg2_grounded_recall_detail_safety.md` | analyzer policy/contract plus implementation evidence | split |
| `acg3_retrieval_query_normalization.md` | retrieval architecture/contract plus evidence | split |
| `acg4_reference_intent_analyzer.md` | `architecture/analyzers/reference-and-intent.md` plus contract/evidence | split/synthesized |
| `acg5_relayemo_scene_cleanup.md` | emotion/scene ownership architecture plus evidence | split/absorbed |
| `acg6_scene_wiki_classifier.md` | scene/analyzer architecture plus contract/evidence | split |

The permanent names describe semantic responsibility, not ACG slice numbers.

## G. Scheduler, worker, and local operation

| Source family | Representative current sources | Target authority | Disposition |
|---|---|---|---|
| scheduler architecture | `o1a_two_lane_scheduler_contract.md` through `o1f_operational_validation.md`, `o2_supervised_scheduler_service.md`, `o3_always_on_local_scheduler.md` | `architecture/runtime/scheduler.md` | synthesized; exact gates/contracts rebuilt; validation to evidence |
| one-job runner and production-round slices | `o0_local_one_job_runner.md`, `o1d1_production_scheduler_round.md` | scheduler architecture/evidence | split/absorbed |
| operator procedures | existing manual runbooks and service operation instructions | `docs/operations/scheduler/` | moved during operations cutover |
| durable queue/worker | Phase 6 queue and worker contracts/handoffs | memory formation plus contracts | synthesized/rebuilt/evidence |

O2/O3 remain architecture only for their durable process-ownership boundaries. Commands, service operation, and troubleshooting move to operations/reference.

## H. SOUL Lab and management UI

| Source family | Target authority | Disposition |
|---|---|---|
| `soul_lab_runtime_mvp.md` | `architecture/ui/soul-lab-runtime.md` | synthesized with durable server/browser ownership rules |
| `soul_lab_ui_mvp.md` | `architecture/ui/soul-lab.md` | synthesized |
| UI-A0/A1 foundation / mock-Home and UI-A2 first-launch / adoption handoffs | stable browser/UI semantics in `architecture/ui/soul-lab.md`; current implementation completion in `architecture/soul_lab_ui_mvp.md`; durable creation/import semantics in `architecture/character-workspace/creation-and-import.md` | retired/absorbed; recoverable from Git history plus the central retirement manifest; no duplicate evidence copy |
| UI-A3 Communication, UI-A4 Pod, and UI-A5 Memory Inspector preview handoffs | stable browser/UI semantics in `architecture/ui/soul-lab.md`; current implementation completion and pending integration status in `architecture/soul_lab_ui_mvp.md` | retired/absorbed; exact rollout/preview implementation detail is Git-history-only; no new implementation-evidence handoff was created because that collection is closed and these sources have no continuing retained-record function |
| UI-A6 shared shell / Settings and UI-A7 management projection handoffs | stable UI semantics in `architecture/ui/soul-lab.md`; exact management-read semantics in `contracts/ui/soul-lab-management.md` | retired; recoverable from Git history plus the central retirement manifest |
| `soul_lab_ui_b0_real_home_conversation.md`, `soul_lab_ui_b1a_lifecycle_visibility.md` | UI/runtime architecture plus evidence | split |
| UI-facing I-4E/I-4F/I-5B/I-7C documents | memory mutation contracts/architecture plus UI evidence | split |

Browser non-authority, loopback mutation ownership, and content-free diagnostic boundaries remain normative and must be preserved in architecture/contracts before evidence sources are retired.

## I. Voice, streaming, and latency

| Source family | Target authority | Disposition |
|---|---|---|
| `phase55a_*`, `phase55b1_*`, `phase55c0_*` through `phase55c4_*` | `architecture/voice/streaming-and-tts.md` plus exact transport contracts | synthesized/rebuilt/evidence_retained |
| `lat2_mobile_perceived_latency.md` | `architecture/performance/perceived-latency.md` if it contains durable design; dated measurements to evidence | split |
| `docs/evaluation/lat1_retrieval_scaling_report.md` | repeatable method to `docs/operations/` + `docs/templates/evaluation/lat1-retrieval-scaling-report.md` (template) | split (Cutover 1C-39: this source mixed a repeatable method with a blank, unfilled template; it was never itself measured evaluation evidence, so `evidence_retained` was a stale assumption. No evidence exists until a real run is filled in and added to `docs/evidence/evaluations/`.) |
| `ai_vtuber_pipeline_profile.md`, `vtuber_memory_proxy_design.md` | reference or concept policy unless a current independently owned subsystem exists | moved or absorbed; not automatically core architecture |

## J. Planning, reference, and strategy sources

| Current source | Target | Disposition |
|---|---|---|
| `project_execution_plan.md` | `docs/planning/project-execution.md` | moved after v0.1 receipt; repository sequencing authority preserved |
| `current_target_migration_guide.md` | `docs/reference/current-target-interpretation.md` | moved/synthesized |
| `relaymem_slp_current_target.md` | reference interpretation plus memory architecture sources | split |
| `scene_memory_scope_current_target.md` | reference interpretation | moved/absorbed |
| `post_v01_strategic_direction_vision.md` | adopted durable content to permanent planning, reference, concept-policy, or existing architecture owners by section map; historical and unadopted vision to Git history | split/cutover; no permanent strategy destination |
| `persona_specialized_proxy_design.md` | concept policy or planning according to adoption state | manual section split |
| `vtuber_memory_proxy_design.md`, `ai_vtuber_pipeline_profile.md` | reference or concept policy | moved or absorbed |
| legacy pipeline implementation plan compatibility stub | none | deleted_git_history_only |
| legacy post-I3 evaluation and work roadmap compatibility stub | none | deleted_git_history_only |
| legacy RelayMEM MVP implementation plan compatibility stub | none | deleted_git_history_only |

## K. Exact contract sources

### Retain and normalize

Existing canonical `docs/contracts/**/*.md` files remain contract sources. They are reviewed for duplicate authority keys and hand-written code-derived tables, but are not moved merely because of the cutover.

### Rebuild from architecture

At minimum, Preparation C must detect normative blocks in:

- `acg1_analyzer_candidate_governance_contract.md`
- `cw_a1_file_first_source_tree_parser_contracts.md`
- `phase6a1_relayslp_job_admission_contract.md`
- `phase6a2_relayslp_response_handoff_contract.md`
- `phase6b0_relayslp_durable_queue_contract.md`
- `phase6c1_primary_mem_worker_contract.md`
- `o1a_two_lane_scheduler_contract.md`
- `i1g_pre_enqueue_durable_finalization_contract.md`
- `phase_i4_primary_mem_forget_hide_contract.md`
- `phase_i5_pin_unpin_contract.md`
- `phase_i7ab_held_apply_discard_contract.md`
- `managed_route_fallback_contract.md`
- `phase55c1_tts_adapter_handoff_contract.md`
- `phase55c3_tts_adapter_transport_contract.md`

Filename matching is not sufficient. Other architecture/handoff sources must be scanned for normative markers, exact field tables, states, gates, and literal anchors.

## L. Evaluation, validation, audit, and completion evidence

The following families move out of architecture unless a durable rule is extracted first:

- `wave*_cross_slice_convergence_audit.md`
- `e1*_evaluation*.md`
- `phase*_validation*.md`
- `*_recovery_audit.md`
- completed implementation `*_handoff.md`
- PM-D completion/fold-in records
- ACG and CW implementation slice records
- Phase 6, I-series, O-series, UI-series, and TTS-series completion narratives

Target collections:

- implementation proof -> `docs/evidence/implementation/`
- wave convergence -> `docs/evidence/waves/`
- evaluation result -> `docs/evidence/evaluations/`
- validation/release receipt -> `docs/evidence/releases/`

`e1_evaluation_consolidation.md` is split: repeatable evaluation interpretation goes to a permanent `docs/operations/`, `docs/reference/`, or `docs/release/` owner as its operator scope requires, while dated or completed result inventory goes to evidence.

`docs/architecture/e1_local_runtime_evaluation_2026_06_25.md` (Cutover 1C-40: `moved` to `docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md`, `evidence`/`frozen`, verbatim content) was the first concrete instance of the `e1*_evaluation*.md` family above to actually move; `e1_evaluation_consolidation.md`'s own split, and the remaining `e1r1`-`e1r5` architecture-handoff records this document consolidates, remain open for a later batch.

## M. Archive and obsolete material

- `docs/architecture/archive/` is not retained as a parallel historical architecture tree.
- Historical rationale still required by an ADR may move to evidence.
- Superseded design copies and redirect stubs are deleted from the active tree and remain available through Git history.
- Runtime compile/checkpoint history files under the archive are absorbed only when they contain unique decision evidence; otherwise they are `deleted_git_history_only`.

## N. Operator smoke, evaluation method, root reference, and asset sources

These families were live in the baseline tree but carried no disposition until the D6 completion audit found them unclassified. They are classified here under the ordered rules above.

| Current source | Actual authority | Target | Disposition |
|---|---|---|---|
| `docs/config_schema.md` | exact configuration field lookup | `docs/reference/` | moved (rule 6) |
| `docs/token_policy_profiles.md` | token policy shadow-profile lookup | `docs/reference/` | moved (rule 6) |
| `docs/openwebui_lmstudio_mvp.md` | operator integration setup | `docs/guides/` | moved; the MVP milestone name does not survive (rules 6, 9) |
| `docs/relayemo_mvp_initial_design.md` | early RelayEMO affect design | `docs/architecture/emotion/affect-modulation.md` | absorbed; the MVP milestone name does not survive (rules 8, 9) |
| `docs/smoke/README.md` | non-canonical smoke collection router | none | deleted_git_history_only (rule 1 analogue) |
| `docs/smoke/e2_value_smoke_runbook.md` | operator smoke runbook | `docs/operations/` | moved |
| `docs/smoke/openwebui_lmstudio_troubleshooting.md` | operator troubleshooting | `docs/operations/` | moved |
| `docs/smoke/openwebui_model_preset_checklist.md` | operator preset checklist | `docs/operations/` | moved |
| `docs/smoke/openwebui_response_differentiation_checks.md` | operator route differentiation checks | `docs/operations/` | moved |
| `docs/smoke/relaymem_local_llm_eval_guide.md` | repeatable operator evaluation procedure | `docs/operations/` | moved |
| `docs/smoke/relaymem_local_response_comparison.md` | repeatable operator evaluation procedure | `docs/operations/` | moved |
| `docs/smoke/relaymem_runtime_payload_eval.md` | repeatable operator evaluation procedure | `docs/operations/` | moved |
| `docs/smoke/scripts_inventory.md` | reviewed historical inventory snapshot | `docs/evidence/evaluations/` | evidence_retained (rule 4) |
| `docs/evaluation/lat1-retrieval-scaling.md` | repeatable evaluation procedure | `docs/operations/` | moved |
| `docs/evaluation/mobile-dogfood-observation.md` | repeatable evaluation procedure | `docs/operations/` | moved |
| `docs/strategy/rin-relm-character-vision.md` | durable creative direction plus historical vision narrative | `docs/architecture/character/showcase-character-direction.md`, with overlap to `docs/architecture/character-workspace/showcase-starter-product-knowledge.md` | split |
| `docs/assets/*.webp`, `docs/assets/readme/*.webp` | referenced binary assets | `docs/assets/` | retained as resources while a current consumer exists |
| `docs/assets/README.md`, `docs/assets/readme/images.md` | asset-collection notes | none | deleted_git_history_only after current-consumer proof |

`docs/smoke/` holds no permanent authority. The collection disappears once its runbook, evaluation-method, snapshot, and router members reach the targets above.

`docs/smoke/scripts_inventory.md` is a reviewed snapshot, not a live list. The current inventory artifact is generated by `scripts/relaylm_generate_scripts_inventory.py`, so the snapshot is frozen evidence rather than a hand-maintained document to keep.

`docs/strategy/rin-relm-character-vision.md` splits three ways. Durable creative direction becomes one `concept_policy` at `docs/architecture/character/showcase-character-direction.md`. Ownership and publication content that duplicates `docs/architecture/character-workspace/showcase-starter-product-knowledge.md` is absorbed into that existing authority rather than restated. Pure historical vision narrative is retired to Git history.

`docs/assets/` is not retained as a family. Its binary assets stay only while a current consumer references them, and its Markdown notes are retired to Git history once that consumer check proves no active reader.

### Transitional placement under the Documentation Model

`docs/evaluation/` and `docs/strategy/` are not permanent collections. [Documentation Model](../DOCUMENTATION_MODEL.md) places `evaluation_method` and `strategy` under transitional source document types, explicitly outside the permanent active-document type allowlist, and requires evaluation method content to reach reference, release, or operations and strategy content to reach planning, reference, or concept policy with historical direction retired to Git.

The governance validator therefore correctly omits both from the permanent active locations. No D6 slice admits either collection as a permanent active location or adds an allowed `relaylm_doc_type` for them, because that would entrench a transitional path and place the validator in conflict with the Documentation Model. Both collections disappear once the rows above are executed. [Documentation Model](../DOCUMENTATION_MODEL.md) is the controlling placement vocabulary for this inventory: wherever an older section named `docs/strategy/` or `docs/evaluation/` as a destination, the Documentation Model governs placement permanence and those targets have been reconciled to permanent owners.

## Inventory completeness contract for Preparation C

Preparation C must produce one record for every baseline Markdown source in scope with:

```yaml
old_path: docs/architecture/example.md
old_blob_sha: <sha>
current_doc_type: <value or null>
current_status: <value or null>
primary_authority: <classified authority>
target_doc_type: <type>
target_paths:
  - docs/...
disposition: <inventory disposition>
contains_normative_blocks: true | false
requires_manual_section_map: true | false
```

The dry-run fails when:

- any baseline source is absent;
- any source has no disposition;
- any architecture source is mapped only by filename without a content review marker;
- a contract-like source lacks a normative-block decision;
- two source families claim the same target authority without an explicit synthesis relation;
- one source maps to multiple authorities without `split`;
- a planned deletion lacks a Git-history-only classification.

## Preparation B conclusion

The current design corpus does not support a safe one-to-one move. The dominant actions are:

1. synthesize a small stable architecture graph from durable design sources;
2. extract exact normative blocks to contracts without paraphrase;
3. move completed slice narratives, audits, validation, and evaluations to evidence;
4. move sequence and interpretation to planning and reference, split adopted future direction into permanent planning, reference, or concept-policy owners, and retire historical direction to Git;
5. delete compatibility stubs and low-value superseded copies from the active tree.

No file move is authorized by this inventory alone.
