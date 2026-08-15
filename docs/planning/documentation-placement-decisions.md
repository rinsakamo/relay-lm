---
relaylm_doc_type: planning
relaylm_authority: documentation_cutover_placement_and_granularity_decisions
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - inventory review finds a new ambiguous source family
  - target graph ownership changes
  - Preparation C dry-run reports conflicting destinations
relaylm_not_authoritative_for:
  - current documentation placement
  - exact contract wording
  - current runtime behavior
  - proof that any migration has occurred
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
relaylm_related_authority:
  - documentation-architecture-inventory.md
  - documentation-target-architecture-graph.md
---
# Documentation Placement Decisions

This document applies the adopted placement and granularity tie-breakers to ambiguous current RelayLM documentation families. It records target decisions so cutover implementation does not reopen the information-architecture design in each migration PR.

## Decision method

Apply the following questions in order:

1. Does the content define an exact schema, field, gate, artifact, API, state transition, or must/must-not rule?
2. Does it primarily define timing, dependencies, implementation order, or migration sequence?
3. Does it primarily help a reader look up fields, options, terms, or current/target interpretation?
4. Is it a non-binding future direction or product bet?
5. Does it define durable responsibility, structure, ownership, or semantics?
6. Is it a procedure or troubleshooting flow?
7. Is its durable value a dated result, implementation claim, audit, validation, or receipt?
8. Do different sections have different owners, update triggers, lifecycles, or independent consumers?

Questions 1–7 determine placement. Question 8 determines whether the source must be split.

## D1: Exact contract mixed with architecture

**Decision:** split.

- Exact normative blocks go to `docs/contracts/` by verbatim extraction.
- Rationale, ownership, and interaction move to the smallest relevant architecture node.
- Completed implementation narrative moves to evidence.
- Configuration or command lookup moves to reference/operations.

Applies to:

- Phase 6 contract/handoff documents;
- ACG contract/report documents;
- CW-A1 source-tree/parser contracts;
- I-4, I-5, and I-7 governance documents;
- TTS adapter/transport contract documents;
- any design file containing exact field or state tables.

A source is not retained as architecture merely because it contains architectural context around a contract.

## D2: Handoff containing a still-valid boundary

**Decision:** extract and archive.

A completed handoff remains evidence. Stable ownership or invariant text is synthesized into architecture/contracts first. The handoff does not remain active authority after extraction.

Applies to Phase 6, RelayMEM M3, SOUL Lab UI-A/UI-B, E1-R, PM-D, CW-A, ACG, O-series, I-series, and Phase 55 slice documents.

## D3: Current/target document containing architecture

**Decision:** split by consumer.

- Interpretation of whether behavior is current, target, or compatibility moves to reference.
- Durable responsibilities and semantics move to architecture.
- Exact boundaries move to contracts.
- Remaining migration sequence moves to planning.

Applies to:

- `current_target_migration_guide.md`;
- `relaymem_slp_current_target.md`;
- `scene_memory_scope_current_target.md`;
- current-target contracts already in `docs/contracts/`, which remain contracts if their primary authority is exact interpretation of one boundary.

## D4: Architecture file named after a phase or milestone

**Decision:** no permanent node uses the milestone name.

The source is split or absorbed according to content. The milestone name survives only in evidence and migration provenance.

Examples:

- Phase 6-C worker sources -> memory formation architecture + SLP worker/finalization contracts + implementation evidence.
- `phase_i5b_pin_unpin_apply.md` -> memory mutation governance + Pin/Unpin contracts + evidence.
- `acg4_reference_intent_analyzer.md` -> reference/intent analyzer architecture + contract + ACG-4 evidence.
- `cw_a5_character_creation_templates_showcase_import.md` -> creation/import architecture + evidence.

## D5: Architecture versus planning

**Decision:** stable structure remains architecture; sequence leaves it.

- `project_execution_plan.md` moves to planning.
- Roadmap sections inside analyzer, memory, workspace, or UI designs move to planning or are removed when completed.
- Architecture pages may state dependencies required by the design but do not own implementation wave order.

The legacy pipeline implementation plan compatibility stub and `post_i3_evaluation_work_roadmap.md` are deleted rather than preserved as planning.

## D6: Architecture versus strategy

**Decision:** binding ownership and invariants stay architecture; non-binding direction is split by adoption state.

[Documentation Model](../DOCUMENTATION_MODEL.md) is the controlling placement vocabulary. It lists `strategy` under transitional source document types, outside the permanent active-document type allowlist, so `docs/strategy/` is never a permanent destination. Non-binding direction is classified as a strategy source, then split: adopted durable content reaches a permanent planning, reference, or concept-policy owner, and unadopted or historical direction is retired to Git.

- `post_v01_strategic_direction_vision.md` is a bounded split/cutover responsibility, not a move into a permanent strategy collection. A section map assigns its adopted durable content to permanent planning, reference, concept-policy, or existing architecture owners; its historical and unadopted vision is retired to Git history.
- VTuber/persona-specialized proxy documents are classified as strategy sources and split the same way unless current code and ownership justify an independently maintained subsystem.
- AI character product principles are strategy sources when they describe product direction; specific safety or disclosure invariants are extracted to concept policy/contracts.

A strategy source never overrides current status, accepted contracts, or execution planning, and never establishes a permanent collection of its own.

## D7: Architecture versus reference

**Decision:** lookup and interpretation move to reference.

- Canonical glossary and terminology are reference.
- Current/target interpretation is reference.
- Code-derived fields, enums, defaults, CLI options, and schema listings are reference or generated output.
- Architecture explains why a field family exists and links to the canonical source; it does not duplicate the table.

## D8: Architecture versus operations

**Decision:** ownership stays architecture; procedures move to operations.

For scheduler and local services:

- process ownership, mutation authority, idempotency, and supervision model remain architecture/contracts;
- commands, startup, shutdown, troubleshooting, and smoke steps move to operations;
- dated successful runs move to evidence.

The same rule applies to workspace creation commands, SOUL Lab management flows, TTS operation, and maintenance tooling.

## D9: Evaluation method versus evaluation result

**Decision:** split.

- Repeatable scenario, rubric, measurement method, acceptance interpretation, and fixture role are evaluation-method sources. [Documentation Model](../DOCUMENTATION_MODEL.md) lists `evaluation_method` under transitional source document types, so `docs/evaluation/` is never a permanent destination: durable method content reaches `docs/operations/`, `docs/reference/`, or `docs/release/` as its operator scope requires.
- Dated outputs, local runs, completed result inventories, and human judgments move to `docs/evidence/evaluations/`.
- A release-readiness synthesis moves to `docs/release/` only while it is an active gate; the frozen result becomes evidence.

`e1_evaluation_consolidation.md` and similar mixed documents must not remain both method and result authority.

## D10: Validation receipt versus release authority

**Decision:** receipts are evidence.

A receipt identifies the exact commit, date, checks, results, and source of truth. It does not remain in architecture and does not become current release status.

Active criteria and pending readiness belong in release; completed validation belongs in evidence/releases.

## D11: Convergence audit versus architecture

**Decision:** convergence audits move to evidence/waves.

Any unique stable invariant found during audit is moved into architecture or contracts. The audit itself remains historical proof and does not become a parent in the target architecture graph.

Applies to all `wave*_cross_slice_convergence_audit.md` and post-wave correction audits.

## D12: Design history and archive directories

**Decision:** do not preserve a parallel historical architecture tree.

- Unique decision evidence required to understand an ADR may move to evidence.
- Superseded copies, compatibility explanations, and reconstructable rationale remain in Git history only.
- `docs/architecture/archive/` is removed by final cutover.

## D13: Root-level design files

**Decision:** classify by authority, not by their current root placement.

- `docs/runtime_compile_gate_design.md` and `docs/relayrun_runtime_checkpoint_design.md` synthesize into runtime compile/checkpoint architecture, with exact gates extracted to contracts.
- Other root-level design files discovered by Preparation C must be mapped to a target graph node or a non-architecture destination before cutover.

No root-level design document is grandfathered solely because current CI or links reference it.

## D14: RelaySOUL directory

**Decision:** dissolve the product-area top-level directory as a placement axis.

- durable identity/source authority moves to character architecture;
- exact patch/source contracts move to contracts;
- experiments and drafts move to evidence or Git history, never to a permanent strategy collection;
- guides and operations move by role.

`docs/relaysoul/` is removed by final cutover, but RelaySOUL remains a system concept and component name.

## D15: Analyzer governance

**Decision:** split policy, subsystem, contracts, and slice evidence.

- shared candidate lifecycle and multilingual output policy -> concept/subsystem architecture;
- reference/intent ownership -> analyzer subsystem architecture;
- exact candidate/schema/fallback gates -> contracts;
- ACG-1 through ACG-6 completion records -> evidence;
- remaining roadmap -> planning if still active.

## D16: File-first Character Workspace sources

**Decision:** synthesize around independent lifecycle boundaries.

- workspace system authority;
- source compiler;
- creation/import;
- maintenance candidates;
- UI presentation;
- exact source/parser/projection/commit contracts;
- implementation evidence.

CW-A1–A5 are source slices, not target filenames.

## D17: Memory governance slices

**Decision:** organize by enduring operation, not feature completion order.

- formation;
- retrieval/grounding;
- mutation governance;
- storage/recovery;
- pinned-memory policy;
- scene-memory scope;
- exact operation contracts;
- implementation/evaluation evidence.

Correct, Forget/Hide, Pin/Unpin, and Held Apply/Discard may have separate contracts while sharing one mutation-governance architecture parent.

## D18: Relationship, scene, emotion, and belief

**Decision:** separate durable semantic models but connect them through concept policy.

- relationship state is a subsystem authority;
- scene is a subsystem authority;
- emotion is transient modulation authority;
- observation/belief and social expression are cross-component concept policies;
- disclosure permission is a privacy concept/contract and is not implied by relationship strength.

The current combined character-belief/relationship/social-expression design is therefore split, not moved intact.

## D19: SOUL Lab UI documents

**Decision:** preserve server/browser ownership in architecture, move screen/slice history to evidence.

- browser non-authority and loopback server authority remain active architecture/contracts;
- Home conversation, observation, lifecycle visibility, and governance action responsibilities synthesize into UI architecture;
- UI-A/UI-B phase narratives and screenshots/results become evidence;
- user procedures become guides/operations.

## D20: Scheduler and always-on operation

**Decision:** one scheduler subsystem architecture with layered contracts and operations.

O0, O1A–F, O2, and O3 are not eight permanent architecture nodes. Their durable distinctions are synthesized into:

- scheduler subsystem architecture;
- one-round/two-lane/supervision contracts;
- operator runbooks;
- implementation and validation evidence.

The opt-in, local-only, non-browser, non-default-on, and no-new-mutation-authority boundaries must survive the split.

## D21: TTS and streaming slices

**Decision:** synthesize one voice subsystem and retain exact transport contracts.

- stream sentinel, suppression, segmentation, adapter wiring, transport envelope, and runtime integration form one subsystem architecture;
- exact envelope and adapter boundaries are contracts;
- Phase 55 slice records are evidence;
- dated latency measurements are evidence, while stable latency budget ownership may become performance architecture.

## D22: Generated reference

**Decision:** generator implementation is not part of cutover completion.

During cutover:

- do not create new hand-written exact-table duplicates;
- delete existing duplicates or replace them with links to code/contracts;
- record generator candidates as deferred work.

Generated reference and drift enforcement remain a post-cutover track.

## D23: Templates and examples

**Decision:** templates are non-authoritative support files.

- templates remain under `docs/templates/`;
- examples are non-authoritative unless explicitly marked as conformance fixtures;
- measured results never use a blank template's document type or status merely because they share structure;
- example config does not become the canonical default source.

## D24: Granularity threshold

Split when at least one condition holds:

- different owner;
- different update trigger;
- different lifecycle or retirement condition;
- one section can be replaced independently;
- exact contract and rationale are mixed;
- current implementation and target design are mixed;
- milestone-dependent narrative and stable concept are mixed;
- sections have independent consumers or verification.

Do not split only because a file is long. Do not retain a mixed file only because each resulting document would be short.

## D25: Evidence retention threshold

Retain evidence in the repository when it is needed to explain:

- an accepted decision;
- an exact release or validation result;
- a significant implementation boundary not reconstructable from code/tests alone;
- an evaluation conclusion still used for future comparison;
- the documentation cutover provenance itself.

Delete to Git history when the file is only:

- a redundant progress snapshot;
- a superseded summary;
- a duplicate handoff;
- a compatibility pointer;
- a milestone note no longer used in decisions or validation.

## D26: Migration sequencing does not create compatibility

Repository-wide old/new structure may coexist between cutover PRs. This is sequencing, not compatibility.

Each migrated authority has one live path after its PR merges. The same PR updates all path-bound scripts, workflows, tests, links, and metadata. No old/new enum allowance, redirect stub, or legacy exception list is introduced.

## Preparation C handoff

Preparation C must convert these decisions into an executable dry-run with:

- commit-fixed full file inventory;
- ordered classifier and explicit exception map;
- section-level split/synthesis map;
- normative-block extraction and digest data;
- path-bound audit/workflow dependency inventory;
- duplicate target-authority detection;
- unresolved classification failure;
- migration receipt preview.

A Preparation C result may refine a file's source-section mapping, but changing a decision above requires an explicit Preparation B amendment rather than a silent script exception.
