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

Last reviewed: 2026-08-01 JST

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
RT-1 Retrieval migration: in progress; RT-1A through RT-1C and the behavior-preserving RT-1D-S1, S2, S3A, S3B, and S3C structural seams are complete. RT-1D-S3C Soul Lab mutation route seams completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Fresh RT-1D runtime P0/P1 architecture authorization PR #800 completed with result `68cc16b9d5ed7b999c22d27457390e53de851335` and fixes the ordered R1-R5 implementation budgets; PR #800 is architecture-only and requires no P8. RT-1D-R1 implementation PR #801 completed with result `90a3c4f1cedf54e007cf5c0a6a9abc69a30d2acd`, and mandatory R1 P8 PR #802 completed with exact resulting main `9ce7de054869ef29cc508d176023a93947489c25`. PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and required no P8. The renewed R2 attempt returned at P1 without mutation after uncovering the managed-response finalization bridge and canonical Pin apply/replay mutation owner, and the live-root budget amendment PR #804 completed with exact result `00ba475c689631520538b7531022603447f11bd0` and required no P8. The following R2 attempt returned at P1 again without mutation as Draft PR #805, which is now closed, unmerged, and tree-neutral at head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95` with zero changed paths. The queued-runner root budget amendment PR #806 completed with exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644` and required no P8. The R2 implementation attempt that followed returned at P1 again without mutation and is recorded in closed tree-neutral Draft PR #807 head `00991760b3070597d6b763a0b3ffc2eb820435f2`. The staged writer-fence and smoke-carriage budget amendment PR #808 completed with exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d` and required no P8. RT-1D-R2A decision owner and managed finalization carriage completed in PR #809 with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, and mandatory R2A P8 PR #810 completed with exact result `5822b01fd4642c89c39a2518672191bf1a8da115`. RT-1D-R2B is complete in PR #811 with exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`; RT-1D-R2C and RT-1D-R2D follow in order, each behind implementation-result verification and a mandatory P8. RT-1D-R2B started from the independently verified R2A P8 result and completed in PR #811, and no stage may bootstrap from the PR #805, PR #807, or PR #809 heads. RT-1B remains default-off and unwired from ordinary Retrieval; RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval. Primary MEM remains the sole ordinary served memory and Retrieval authority; Subjective ordinary Retrieval remains disabled and unwired, and no durable intent, reader fence, writer fence, activation, final receipt, serving or fallback change, writer-authority transfer, or retirement change has occurred.
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

**RT-1D-S1 Reader seams** completed in PR #789, producing main `b272edb78602032009d4882a6244883cce610b86`. S1 extracted the existing managed-chat, Retrieval, and Primary recall reader responsibilities into bounded owners while preserving exact public behavior, stage order, offload, timing, diagnostics, Retrieval artifacts, Primary security/lifecycle/fallback behavior, and the RelayINT `metadata.ctx` / `ctx_handoff_guess` Mapping contract. It is a behavior-preserving structural prerequisite only: it enables no ordinary Subjective MEM Retrieval, changes no Primary MEM serving authority, and adds no RT-1D configuration, binding, durable cutover state, reader or writer decisions, fences, finalized receipt, retirement, persistence, recovery, worker, queue, scheduler, API, or UI behavior.

**RT-1D-S2 Worker seams** completed in PR #791, producing main `31b700a2db0af7819f761d51bd946ff6798eb4c9`. S2 extracted checkpointed Primary pipeline request construction and execution into `relaylm/_relaymem_slp_primary_worker_pipeline.py`, and extracted one-queued-job claim, source preparation, worker invocation, prepared-scope release, and terminal cleanup into `relaylm/_relaymem_slp_one_queued_job_runner_execute.py`. It preserved public request, result, and projection schemas and import locations; patchable module-level callables; claim revalidation, lease renewal counts, checkpoint order, protected-source release order, status/reason bytes, retry and terminal transitions; and durable queue/store/page/index/log bytes plus fault, crash, and recovery behavior. S2 remains a behavior-preserving structural prerequisite only. It added no cutover binding, configuration, authority decision, Primary fence, Subjective serving, fallback change, retirement, scheduler/queue/store semantics, or new persistence/recovery authority.

**RT-1D-S3A Correct core seams** completed in PR #794, producing exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253`. This behavior-preserving structural prerequisite split the production owners into `relaylm/relaymem_primary_correction.py` (122 lines), `relaylm/_relaymem_primary_correction_preflight.py` (269), `relaylm/_relaymem_primary_correction_apply.py` (444), `relaylm/_relaymem_primary_correction_publication.py` (104), `relaylm/_relaymem_primary_correction_recovery.py` (60), and `relaylm/_relaymem_primary_correction_history.py` (137), with a largest touched orchestration span of 73 lines. The facade preserves exact public names, signatures/defaults, constants, `__all__`, canonical exception/state identities, and import locations; the existing `_utc` and `apply_relaymem_primary_page_write` compatibility seams remain effective through explicit internal dependency injection. It introduced no production monkeypatch, pytest monkeypatch fixture, runtime patch installer, temporary patch module, `sys.modules` manipulation, or `importlib` reload. Token claims/TTL, operation keys, lock/validation order, receipts, replay/idempotency, canonical page/index/log bytes, fault positions, caller-invoked recovery, history/current-state behavior, and durable effects remain exact.


**RT-1D-S3B Forget core seams** completed in PR #796 from bootstrap/parent main `bc27c25d0b745fc2d9927e9e21179b14cd337141`, with implementation head `126e88dc18c8a61e439a41c8da7e6e0eaa2ccfc2`, commit subject `refactor: extract RT-1D-S3B Forget seams`, and exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427`. Its exact two-path diff was `relaylm/_relaymem_primary_forget_apply.py` (+400/-0) and `relaylm/relaymem_primary_forget_recovery.py` (+127/-274), total +527/-274. The recovery facade is now 632 physical lines (from 779), and the internal apply owner is 400 physical lines (from absent). Touched orchestration spans are public apply wrapper 45, public recovery wrapper 42, locked recovery 48, finalization coordinator 17, hidden-state resolution 16, control convergence 25, tombstone finalization 52, internal apply entry point 65, validated apply coordinator 29, existing-operation replay 34, hidden-successor handoff 42, and reacquisition/finalization 22 lines; both modules are below the approximate 700-line trigger and every touched orchestration is below 80 lines.

The public apply signature remains unchanged. `relaylm/relaymem_primary_forget_recovery.py` remains the canonical public compatibility, recovery, finalization, result-class, schema, and export owner; `relaylm/_relaymem_primary_forget_apply.py` owns bounded apply validation, exact replay, binding, initial lock/reread, hidden-successor handoff, reacquisition, and delegation to canonical finalization. The dependency direction is `relaymem_primary_forget_recovery -> _relaymem_primary_forget_apply`; the internal apply owner does not import the recovery facade. The facade constructs a frozen per-call dependency bundle from current module globals, preserving existing facade patch seams. No replacement public result dataclasses were introduced. Public schemas, signatures/defaults, class identities, inheritance, dataclass metadata, repr, schema behavior, `to_log_dict` projections, exception identity, and facade re-export identities remain exact. No production monkeypatch, pytest monkeypatch fixture, runtime patch installer, temporary patch module, `sys.modules` mutation, `importlib.reload`, or dynamic reverse import was introduced. Immutable facade hashes remain `relaylm/relaymem_primary_forget.py` SHA-256 `4fe026b1c87639c8cb248acce41ac4b2d875e1f05eb14d28fc79059dc0600f92` and `relaylm/relaymem_primary_forget_public_apply.py` SHA-256 `8a0af188df9ee1c037547de60f92fc8cf39e9d09a34f361292ea82133694021e`; both are byte-identical to the exact-main baseline.

Validation/fault order, operation/token/reason binding, lock/replay/handoff/reacquisition behavior, caller-selected recovery, hidden resume, M3f/M3g/control convergence, tombstone publication/reread, deterministic timestamp, durable bytes, result/error/leakage behavior, response-lost, and reconciliation behavior remain exact. Python 3.12.13 validation and every applicable exact-head workflow succeeded for implementation head `126e88dc18c8a61e439a41c8da7e6e0eaa2ccfc2`; legitimate changed-path exclusions were skipped, with no failed, queued, or in-progress check remaining. PR #796 added no cutover, runtime, configuration, persistence, lifecycle, receipt, API, UI, S3C, or P8 behavior. Primary MEM remains the sole ordinary served memory and Retrieval authority.

**RT-1D-S3C Soul Lab mutation route seams** completed in PR #798 from bootstrap/parent main `e221f17906682bdb077d8016e09843d176af5df4`, with implementation head `97e161beab5b037ab1b8505641b9c6091b7b4ca0`, commit subject `refactor: extract RT-1D-S3C Soul Lab mutation seams`, and exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. Its exact four-path diff was `relaylm/soul_lab_memory_correction_routes.py` (+42/-99; 104 lines), `relaylm/soul_lab_memory_correction_runtime.py` (+136/-0; 136 lines), `relaylm/soul_lab_memory_forget_routes.py` (+43/-168; 106 lines), and `relaylm/soul_lab_memory_forget_runtime.py` (+209/-0; 209 lines), total +430/-267, with no optional focused test. Every module is below the approximate 700-line trigger; maximum orchestration is 52 lines, all touched orchestration is below about 80 lines, and no waiver applies. Route metrics are Correction loopback 9, dependency resolution 12, installer 52, nested handlers 10 each; and Forget loopback 9, dependency resolution 13, installer 52, nested handlers 10 each. Correction runtime metrics are dependency owner 9, exact JSON 10, scope 7, error mapping 4, preflight 24, apply 22, history 16. Forget runtime metrics are dependency owner 10, exact JSON 10, scope 7, error mapping 4, preflight projection 20, apply projection 28, preflight 26, apply 27, history 22.

The one-way acyclic owner graph is `soul_lab_memory_correction_routes -> soul_lab_memory_correction_runtime` and `soul_lab_memory_forget_routes -> soul_lab_memory_forget_runtime`. Route owners retain installers, decorators and registration, paths, methods and order, `response_model=None`, namespace `Query` constraints (`min_length=1`, `max_length=128`), global loopback authorization, per-request dependency construction, and module-level patch seams. Runtime owners retain operation-specific JSON parsing, scope resolution, domain invocation, safe projection, error mapping, no-store JSON responses, and separate preflight/apply/history paths. There is no reverse route import, generic mutation runtime, dynamic import, `sys.modules` mutation, `importlib.reload`, production monkeypatch, or patch installer.

All six routes remain exact and ordered: `POST .../correct/preflight`, `POST .../correct`, `GET .../corrections`, `POST .../forget/preflight`, `POST .../forget`, and `GET .../forget-history`. Exact methods/order, `response_model=None`, namespace constraints, authorization-first order, strict `application/json`, 16,384-byte limit, empty/oversize/UTF-8/JSON/Pydantic errors, scope-before-domain order, the full error map and unknown normalization, exact successful objects, Forget projections, status/detail bytes, `Cache-Control: no-store`, leakage bounds, call arguments/order, and post-app-creation `patch.object` behavior are preserved. `relaylm/soul_lab_app.py` remained byte-identical with baseline/final SHA-256 `877457129d617ed0a90df879e1a41d9807503bb2612b68095812dfc87dea58e4`; configuration, contracts, workflows, documentation, and evidence were unchanged in PR #798.

The external baseline/candidate differential matrix SHA-256 was `44547117872e449294095f240d79f16b8bbd9c7f6c89737fa9c865e461c65dac`. It covered registration/order, authorization and authorization-before-domain access, media/body/UTF-8/JSON/Pydantic failures, valid preflight/apply/history objects and arguments, projections/leakage, every mapped error, unknown normalization, status/detail/cache, and post-install patches; its harness and stores remained outside the repository. Python 3.12 validation passed `scripts/relaylm_soul_lab_memory_routes_split_smoke.py`, `scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py`, `scripts/relaylm_phase_i4e_forget_api_security_smoke.py`, `scripts/relaylm_phase_i4f_forget_validation_security_smoke.py`, focused Correct/Forget security and validation smokes, `py_compile` for all four paths, `compileall` for `relaylm`/`scripts`/`tests`, `git diff --check`, and the isolated differential comparison. Every applicable exact-head workflow for `97e161beab5b037ab1b8505641b9c6091b7b4ca0` succeeded or was legitimately path-skipped; none failed, queued, or remained running.
LC-1 lifecycle migration is complete through Consolidate. RT-1 is in progress with RT-1A, RT-1B, RT-1C, and all behavior-preserving RT-1D structural seams through S3C complete. RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`; its mandatory P8 PR #799 produced exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Fresh RT-1D runtime P0/P1 architecture authorization PR #800 completed with result `68cc16b9d5ed7b999c22d27457390e53de851335` and fixes five non-overlapping implementation slices: durable preparation, writer fencing, rehearsal, authority activation, and immediate retirement. PR #800 requires no P8. RT-1D-R1 implementation is complete in PR #801 and PR #800's independently verified resulting main bootstrapped R1 after merge. Primary MEM remains the sole ordinary served memory and Retrieval authority. Subjective ordinary Retrieval remains disabled and unwired. No cutover, authority switch, serving, fallback, writer fence, durable intent or receipt, or retirement change has occurred.

Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets. R1 implementation is complete and R2 has not started. Subjective ordinary retrieval remains disabled and unwired, and no cutover, authority switch, serving, fallback, writer fence, or retirement change occurred.


### RT-1D-S3 structural P1 amendment

The monolithic S3 P1 Return measured the current owners at 1100 lines for `relaylm/relaymem_primary_correction.py`, 779 lines for `relaylm/relaymem_primary_forget_recovery.py`, 161 lines for `relaylm/soul_lab_memory_correction_routes.py`, and 231 lines for `relaylm/soul_lab_memory_forget_routes.py`. Existing orchestration spans were 72 lines for `preflight_primary_memory_correction`, 123 for `apply_primary_memory_correction`, 71 for `recover_primary_memory_corrections`, 150 for `apply_primary_memory_forget`, 87 for `recover_primary_memory_forget`, 118 for the Correct route installer, and 179 for the Forget route installer. The discarded behavior-preserving candidate still produced a 771-line Correct apply module, a 125-line Correct apply orchestrator, a 120-line publication orchestrator, a 156-line Forget apply orchestrator, an 89-line Forget finalizer, and a 153-line Forget runtime factory. It therefore crossed the approximate 700-line module and 80-line orchestration review triggers. No candidate commit, push, PR, receipt, P8, runtime, or authority update occurred.

The amendment fixes three non-overlapping Primary-only slices:

- **RT-1D-S3A Correct core seams**: production budget `relaylm/relaymem_primary_correction.py`, `relaylm/_relaymem_primary_correction_preflight.py`, `relaylm/_relaymem_primary_correction_apply.py`, `relaylm/_relaymem_primary_correction_publication.py`, `relaylm/_relaymem_primary_correction_recovery.py`, and `relaylm/_relaymem_primary_correction_history.py`; optional focused test only `tests/test_rt1d_s3a_correct_seams.py`.
- **RT-1D-S3B Forget core seams**: production budget `relaylm/relaymem_primary_forget_recovery.py` and `relaylm/_relaymem_primary_forget_apply.py`; optional focused test only `tests/test_rt1d_s3b_forget_seams.py`. `relaylm/relaymem_primary_forget.py` and `relaylm/relaymem_primary_forget_public_apply.py` remain byte-identical.
- **RT-1D-S3C Soul Lab mutation route seams**: production budget `relaylm/soul_lab_memory_correction_routes.py`, `relaylm/soul_lab_memory_forget_routes.py`, `relaylm/soul_lab_memory_correction_runtime.py`, and `relaylm/soul_lab_memory_forget_runtime.py`; optional focused test only `tests/test_rt1d_s3c_soul_lab_mutation_routes.py`. `relaylm/soul_lab_app.py` remains byte-identical, global authorization remains route-owned, and patching route-module callables continues to affect requests.

Every new production module stays below the approximate 700-line trigger and every touched orchestration function stays about 80 lines or less. Each facade retains exact public imports, functions, signatures, schemas, and durable behavior; Correct preserves token, publication, recovery, and history semantics; Forget preserves replay, hidden-successor, recovery, convergence, and receipt semantics; Soul Lab preserves paths, methods, authorization, JSON/projection/error/no-store behavior. No generic mutation framework, second authority, cutover binding, configuration, Subjective serving, fallback, retirement, new persistence authority, API behavior, or UI behavior is authorized. A needed extra owner or path returns that slice to P1 before writing; thresholds are not waived, line-golfed, reinterpreted, or silently expanded. This architecture-only amendment itself requires no separate P8, but its exact resulting main must be independently verified before S3A.

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
       -> RT-1D structural-seam architecture amendment      P1 Return recorded; runtime not started
          -> RT-1D-S1 reader seams                          complete in PR #789; behavior-preserving
             -> S1 mandatory P8 current-authority sync      PR #790; exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b
                -> RT-1D-S2 worker seams                    complete in PR #791; exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9
                   -> S2 mandatory P8 current-authority sync      PR #792; exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba
                      -> RT-1D-S3 P1 architecture amendment   PR #793; exact result 5011eaaddd895b434f3d870dcf2206527725629c
                         -> RT-1D-S3A Correct core seams       complete in PR #794; exact resulting main 2d05a41235e396ac82d536437ed8e5568f617253
                            -> S3A mandatory P8 current-authority sync PR #795 result bc27c25d0b745fc2d9927e9e21179b14cd337141
                               -> RT-1D-S3B Forget core seams complete in PR #796; exact resulting main b75df848bf3982e00f67969c016ba1f28dd93427
                                  -> mandatory S3B P8 current-authority synchronization PR #797 result e221f17906682bdb077d8016e09843d176af5df4
                                     -> RT-1D-S3C Soul Lab mutation route seams complete in PR #798; exact resulting main 56fa66fdba475a3d6e1a4bc4cbc3480ba238720e
                                        -> mandatory S3C P8 current-authority synchronization PR #799 result d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f
                                           -> architecture PR #800 result 68cc16b9d5ed7b999c22d27457390e53de851335; no P8
                                              -> R1 PR #801 result 90a3c4f1cedf54e007cf5c0a6a9abc69a30d2acd
                                                 -> mandatory R1 P8 PR #802 complete; exact resulting main 9ce7de054869ef29cc508d176023a93947489c25
                                                    -> R2 P1 stable-structure amendment PR #803 result eee986422b45c50e0d9ad0528e863457be4db9a1
                                                       -> R2 P1 live-root budget amendment PR #804 result 00ba475c689631520538b7531022603447f11bd0
                                                          -> R2 P1 Return recorded in closed tree-neutral Draft PR #805 head 733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95
                                                             -> R2 P1 queued-runner root budget amendment PR #806 result cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644
                                                                -> R2 P1 Return recorded in closed tree-neutral Draft PR #807 head 00991760b3070597d6b763a0b3ffc2eb820435f2
                                                                   -> R2 staged writer-fence / smoke-carriage budget amendment PR #808 result 758c160e1ee71bb9ad67fe10234e5a38c03c6a3d
                                                                      -> RT-1D-R2A complete in PR #809; exact resulting main 0f0b88a0bd601d1cd14b830ca209a26107f62430
                                                                         -> mandatory R2A P8 PR #810 complete; exact result 5822b01fd4642c89c39a2518672191bf1a8da115
                                                                            -> RT-1D-R2B complete in PR #811 exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d` -> verify -> mandatory R2B P8 -> verify
                                                                               -> RT-1D-R2C -> verify -> mandatory R2C P8 -> verify
                                                                                  -> RT-1D-R2D -> verify -> mandatory R2D P8 -> verify
                                                                                     -> R3 may become next; not started by this amendment

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

## RT-1D-R2A completion and mandatory P8 (current)

RT-1D-R2A decision owner and managed finalization carriage is complete. The staged writer-fence and smoke-carriage budget amendment PR #808 completed with exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d` and required no P8. RT-1D-R2A implementation PR #809 used branch `agent/rt1d-r2a-decision-finalization` and that exact bootstrap; it is closed and merged with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, which is exact current main.

PR #809 carries exactly three normal commits: `62bb2a8ae4bff175ae8169210cbcf2e604b48835` `chore: bootstrap RT-1D-R2A execution` (tree-neutral, zero changed paths); `3a8f33a5b9c59108f5c2d4b3289481f587d1e090` `feat: implement RT-1D-R2A writer decision carriage`; and `eafdc0629fd307ed7c136488280ddb449c5787f1` `fix: bound malformed RT-1D-R2A writer decisions`. The final head is `eafdc0629fd307ed7c136488280ddb449c5787f1`. It changed exactly 9 paths, +829/-7, with exactly one execution receipt, no comments, no reviews, and no review threads. The full suite was 1041/1041 and every applicable exact-head workflow completed with no candidate-caused failure.

The exact nine-path R2A inventory and final evidence is: `relaylm/subjective_mem_retrieval_cutover.py` +146/-0, blob `dd21090a80ec`, 549 lines; `relaylm/managed_chat_runtime.py` +6/-0, blob `65ffa7983b24`, 490 lines; `relaylm/managed_chat_response.py` +10/-0, blob `7d4c3e8a207a`, 553 lines; `relaylm/relaymem_slp_runtime_finalization.py` +57/-0, blob `a6be671c66a1`, 585 lines; `tests/test_subjective_mem_retrieval_cutover.py` +268/-0, blob `638bc77dad54`, 581 lines; `scripts/_relaylm_i1ge_crash_child.py` +9/-1, blob `f4732cda4fa6`, 584 lines; `scripts/relaylm_e1r1_trusted_home_scene_admission_smoke.py` +106/-4, blob `e396228045ed`, 474 lines; `scripts/relaylm_i1gc_durable_finalization_replay_smoke.py` +81/-0, blob `c855eb0cebc3`, 734 lines; and `tests/test_response_service.py` +146/-2, blob `f226d495bbd0`, 479 lines. A tenth R2A path is invalid.

`SubjectiveMemRetrievalPrimaryWriterDecision` is the sole immutable decision. It carries no default on any field, no Optional permit compatibility, and no unbound class. Exact `primary_only` posture derives a binding-free `primary_stable` permit with no store, store root, binding digest, or durable access. Rehearsal-bound posture reconstructs only through the existing exact reconstruction owner. The writer permit exists only for complete valid states strictly before `primary_writer_fenced`; the fence, every later state, recovery-required, and malformed values reject. Unhashable corrupted values converge to `False` or a stable owner error and never to an uncontrolled `TypeError`; the guard was not broadened into a generic exception swallower. The decision is derived exactly once at the managed runtime root and carried exactly to both stream and non-stream finalization. The public finalization guard rejects before any replay, source, or queue side effect, and the permitted path delegates to the preserved byte-identical effect owner. No decision is persisted in any queue record.

Mandatory R2B P8 PR #812 completed with exact result `ca4eae55ab2dd053978d1dc7a4dd4b55fee5e5a8`. It is documentation-only, requires no further P8, and changes no production, runtime, test, config, workflow, durable state, serving, fallback, or retirement behavior. RT-1D-R2B is complete in PR #811 with exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`; it may start only from this P8's independently verified exact resulting main on a fresh branch, never from a PR head and never from the PR #805, PR #807, or PR #809 heads. RT-1D-R2C is complete in PR #814; at that historical point, RT-1D-R2D and RT-1D-R3 had not started. R2B queue, runner, worker, and Primary pipeline carriage is complete. Primary MEM remains the sole ordinary served authority, Subjective ordinary Retrieval remains disabled and unwired, and no durable intent, fence, activation, receipt, readiness, usage, probe, fallback, authority-transfer, or retirement change has occurred.

## RT-1D-R2 staged writer-fence and smoke-carriage budget amendment

The queued-runner root budget amendment PR #806 completed with exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644` and required no P8. The R2 implementation attempt that followed it returned at P1 without mutation and is recorded in Draft PR #807, now closed, unmerged, and tree-neutral at head `00991760b3070597d6b763a0b3ffc2eb820435f2` with one bootstrap commit, zero changed paths and exactly one execution receipt. PR #807 is an audit record only and must never be reopened, marked Ready, merged, deleted, reset, moved, or used as an implementation bootstrap.

PR #807 proved that every required production seam fits inside the accepted twenty-three production paths, and that no queue-schema change, direct M3e/M3g change, or twenty-fourth production path is needed for the carriage itself. It also proved the exact conflict: strict `missing/malformed -> fail closed`, no permit-valued default, and no leaf re-derivation cannot coexist with a frozen `scripts/` surface while every exact-head workflow must still succeed, because the changed entry points are called directly from existing smoke, support, and characterization callers.

That architecture-only staged-budget amendment was Draft PR #808; it required no P8 and completed with exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d`. It resolved that conflict without weakening any semantics: the strict writer-fence contract is retained in full, a permit-preserving unbound or default class is rejected, and the single over-broad R2 transaction is replaced by four ordered, independently bounded implementation stages that each authorize only the exact existing non-production call sites they must mechanically update.

RT-1D-R2A is complete in PR #809 with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, and mandatory R2A P8 PR #810 completed with exact result `5822b01fd4642c89c39a2518672191bf1a8da115`. RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4` and, at that historical point, RT-1D-R2D was next and had not started, each gated behind independent verification of the preceding implementation result and its mandatory P8 current-authority synchronization. No stage may bootstrap from a PR head or an audit branch.

### Strict semantics retained for every stage

A missing decision fails closed and a malformed decision fails closed, both before any side effect. There is no `primary_writer_unbound` or equivalent third class, no missing-value compatibility path, no permit-valued dataclass, request, or function default, and no Optional decision used as an implicit permitted state. Every direct caller supplies an exact immutable bound decision. Production construction roots derive only through the sole semantic owner `relaylm/subjective_mem_retrieval_cutover.py`; runner, worker, pipeline, Correct, Forget, Pin, and Unpin leaves may validate the immutable value but may not resolve configuration or reconstruct state. Equality across durable boundaries is exact immutable semantic-value equality, never Python object identity. No queue schema or persistence field carries the decision, direct M3e/M3g implementations remain byte-identical, and no durable cutover, fence, activation, receipt, readiness, usage, probe, or retirement record is introduced by RT-1D-R2A through RT-1D-R2D.

### Ordered stage budgets

RT-1D-R2A — decision owner and managed finalization carriage. Production paths 1-4: `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/managed_chat_runtime.py`, `relaylm/managed_chat_response.py`, `relaylm/relaymem_slp_runtime_finalization.py`. Non-production budget: exactly 4 frozen existing caller files.

RT-1D-R2B — queue, runner, worker, and Primary pipeline carriage. Production paths 5-13. Non-production budget: exactly 29 frozen existing caller files, including the two existing shared support modules `scripts/relaylm_phase6c1_primary_worker_test_support.py` and `scripts/_relaylm_phase6c1_durable_source_support.py`.

RT-1D-R2C — Correct and Forget carriage. Production paths 14-20. Non-production budget: exactly 23 frozen existing caller files.

RT-1D-R2D — Pin and Unpin carriage. The reviewed P1 expansion authorized exactly 4 production paths, adding the shared semantic owner to paths 21-23, and exactly 6 non-production paths, adding the direct semantic-owner test to the five frozen callers.

The independently reproduced inventory is 58 distinct existing files and 61 stage assignments; three files appear in two stages for disjoint call sites and are recorded explicitly.

Call-site granularity is the accepted and final stage-assignment unit; file granularity is rejected. A stage assignment is one direct call site, request-construction site, patch target, or explicitly named support-factory site, and each individual site belongs to exactly one stage. A repeated path never grants whole-file authority: there are exactly three overlap files, each stage changes only its own enumerated sites plus the minimum stage-owned scaffolding, and every other-stage site and unrelated behavior in that file stays byte-identical for that stage. Every stage P1 remeasures the then-current blob after the preceding implementation and its mandatory P8 result, never the pre-R2 or amendment-time blob. If an edit cannot be isolated without touching another stage's site or unrelated behavior, the stage returns to P1 rather than broadening file authority. Every path, blob, and line count is frozen in the RT-1D architecture. There is no wildcard `scripts/` or `tests/` authority, no stage authorizes all 58 files, and no new test, smoke, or support file may be created in any stage.

### Superseded transaction record

PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and required no P8. The initial R2 attempt returned at P1 without repository mutation after structural review of the existing large Primary pipeline and Pin owners. The renewed R2 attempt also returned at P1 without mutation: negative live-root inspection found two independent current consumers outside the accepted twenty-path budget. The live-root budget amendment PR #804 recorded those two roots and completed with exact result `00ba475c689631520538b7531022603447f11bd0`; it was architecture-only and required no P8.

The following R2 attempt returned at P1 a third time without mutation and is recorded in Draft PR #805, which is now closed, unmerged, and tree-neutral at head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95` with exactly one bootstrap commit, zero changed paths, a tree identical to main, and exactly one execution receipt. PR #805 is an audit record only and must not be reopened, marked Ready, or merged. That architecture-only queued-runner root amendment was Draft PR #806; it required no P8. R2 restarted only after that amendment merged and its exact resulting main was independently verified. The amendment PR head cannot bootstrap R2, and no renewed R2 branch may bootstrap from the PR #805 head; each renewed R2 stage uses a fresh branch cut from the independently verified preceding result.

The exact blocker recorded by the PR #805 P1 Return is `relaylm/relaymem_slp_queue_candidate.py`. Its `build_relaymem_slp_one_queued_job_request(...)` is the sole production constructor of `RelayMEMSLPOneQueuedJobRunnerRequest`, it already receives `RelayLMConfig`, and both the live CLI worker root `relaylm/local_worker_once.py` and the live scheduler root `relaylm/relaymem_slp_scheduler_queue_lane.py` already delegate request construction to it and remain byte-identical. Adding only the shared builder is the minimal complete authority correction; adding either caller would duplicate derivation responsibility and expand scope unnecessarily. Its baseline is blob `3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 physical lines; final maximum 510 and net growth +48. `build_relaymem_slp_one_queued_job_request` may gain at most 8 physical lines and remains at or below 60 physical lines, with at most one new same-owner decision derivation or validation helper of at most 40 physical lines.

`relaylm/subjective_mem_retrieval_cutover.py` remains the sole decision semantic owner. The queue candidate may call one semantic-owner resolver and may not duplicate state-machine logic, reason identities, validation, or binding interpretation. The writer decision is never persisted in the B3 durable queue record, and R2 creates no intent, fence, activation, receipt, readiness, usage, probe, or retirement record. Python object identity cannot and need not survive the durable queue boundary: the same decision means exact immutable semantic value equality — same schema version, reconstructed state class, allow/reject class, `recovery_required` value, stable bounded reason identities, and `runtime_private_evidence_omitted` value. The runtime-finalization and queued-runner construction roots independently obtain an exactly equal immutable decision from the same authoritative configuration posture, and no arbitrary Mapping reconstruction is allowed.

Current configuration validation requires the entire cutover binding tuple to be empty when `subjective_mem_retrieval_cutover_mode == "primary_only"`, so the semantic owner explicitly defines a binding-free result for exact `primary_only` posture: state `primary_stable`, Primary writer permitted, `recovery_required` false, no `EvidenceRecordStore` access, no store root or path, no binding digest, and no durable record read or write. This is an explicit mode-derived decision, not an implicit fallback and not a silently substituted dataclass default. For exact supported rehearsal-bound posture the semantic owner reconstructs only from complete authorized binding and store inputs already defined by R1/R2; missing, partial, malformed, unsupported, unreadable, or divergent binding or state returns reject plus `recovery_required`. No queue candidate path may infer permission from projection presence or config booleans outside the semantic-owner resolver. No permit-valued request-field default may conceal missing construction-root supply, and downstream queued-runner execution, worker request, worker execution, worker pipeline, and Primary pipeline invocation may validate the exact decision but may not re-derive or downgrade it.

The first root recorded by PR #804 is `relaylm/managed_chat_response.py`: `managed_chat_runtime.py` calls `build_managed_chat_response`, while this bridge alone constructs both stream and non-stream `run_relaymem_slp_runtime_enqueue_after_response` calls. It must accept the exact immutable Primary-writer decision through an explicit keyword-only argument and carry the same decision to both finalization constructions, without resolving durable state, inferring config permission, replacing an explicit decision, or taking over the finalization side-effect gate. Its baseline is blob `bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 543 physical lines; final maximum 559 and net growth +16. `build_managed_chat_response` may gain at most 8 physical lines and no branch, loop, persistence responsibility, or state resolution.

The second root recorded by PR #804 is `relaylm/relaymem_primary_pin_apply.py`: Soul Lab routes call the Pin facade, but this canonical apply/replay owner performs the durable operations. Route-only Pin fencing is insufficient because `_apply_operation` can publish state during receipt replay and publishes receipt and state for a new operation. Both public apply entries must accept the exact immutable decision, carry it without boolean or Mapping conversion, and validate it before the first mutation. Fenced or recovery-required decisions dominate and prevent replay `_publish_state`, `_publish_receipt`, new-operation `_publish_state`, shared-fence mutation, and every other durable Pin/Unpin mutation. Its baseline is blob `9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 617 physical lines; final maximum 697 and net growth +80. `_apply_operation` remains at or below 80 physical lines; if its exact baseline already exceeds 80, only a bounded same-owner decision helper is allowed and its span cannot grow.

The exact twenty-three-path R2 production budget, in authoritative order, is:

1. `relaylm/subjective_mem_retrieval_cutover.py`
2. `relaylm/managed_chat_runtime.py`
3. `relaylm/managed_chat_response.py`
4. `relaylm/relaymem_slp_runtime_finalization.py`
5. `relaylm/relaymem_slp_queue_candidate.py`
6. `relaylm/relaymem_slp_one_queued_job_runner.py`
7. `relaylm/_relaymem_slp_one_queued_job_runner_execute.py`
8. `relaylm/relaymem_slp_primary_worker.py`
9. `relaylm/_relaymem_slp_primary_worker_types.py`
10. `relaylm/_relaymem_slp_primary_worker_execute.py`
11. `relaylm/_relaymem_slp_primary_worker_pipeline.py`
12. `relaylm/relaymem_primary_pipeline.py`
13. `relaylm/_relaymem_primary_pipeline_impl.py`
14. `relaylm/relaymem_primary_correction.py`
15. `relaylm/_relaymem_primary_correction_apply.py`
16. `relaylm/_relaymem_primary_correction_recovery.py`
17. `relaylm/relaymem_primary_forget_recovery.py`
18. `relaylm/_relaymem_primary_forget_apply.py`
19. `relaylm/soul_lab_memory_correction_runtime.py`
20. `relaylm/soul_lab_memory_forget_runtime.py`
21. `relaylm/soul_lab_memory_pin_routes.py`
22. `relaylm/relaymem_primary_pin.py`
23. `relaylm/relaymem_primary_pin_apply.py`

No twenty-fourth production path is authorized. `relaylm/local_worker_once.py`, `relaylm/relaymem_slp_scheduler_queue_lane.py`, `relaylm/relaymem_slp_scheduler_round.py`, `relaylm/cli/worker.py`, every queue-record schema or persistence path, every worker validator path, and every direct M3e/M3g path remain unchanged and unauthorized. If a twenty-fourth production path is required, stop at P1 and raise a new architecture amendment. Direct M3e/M3g implementations remain unchanged because their current worker/pipeline checkpoints dominate them. Preserved PR #803 limits are: `_relaymem_primary_pipeline_impl.py` baseline 1,033, final maximum 1,083 and net +50; `relaymem_primary_pin.py` baseline 742, final maximum 777 and net +35; `subjective_mem_retrieval_cutover.py` baseline 403 and final maximum 550; every new function maximum 80 and every new orchestration function maximum 60. No line-golfing, validation removal, unrelated cleanup, extraction, rename, formatting sweep, schema redesign, or ownership movement is authorized.

This amendment changes documentation authority only. Primary MEM remains the sole ordinary served memory and Retrieval authority; Subjective ordinary Retrieval remains disabled and unwired. It changes no production, runtime, config, durable state, serving, fallback, or retirement behavior.

## RT-1D-R2B completion and mandatory P8 (historical)

RT-1D-R2B completed in implementation PR #811 from bootstrap `5822b01fd4642c89c39a2518672191bf1a8da115`, final reviewed head `9672a593b90dca06848e936c1099f828f913ae28`, and exact resulting main `a1fac7e4d3dee844990b680aa27130cee9051c3d`. The implementation contains exactly three commits, 15 changed paths, and +187/-0. External Python 3.12 validation completed with 1041 passed; every applicable exact-head check succeeded. Queue, runner, worker, and Primary pipeline carriage now requires the exact immutable decision owned by `subjective_mem_retrieval_cutover.py`; foreign or rejected decisions fail closed before governed effects, and the durable queue schema remains unchanged.

The mandatory R2B P8 current-authority synchronization completed historically in PR #812 and requires no recursive P8. RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started. R2C may bootstrap only from this authority-correction transaction's independently verified exact resulting main. At that historical point, R2D, R3, R4, and R5 had not started. Primary remains the sole ordinary reader and writer; no intent, reader fence, writer fence record, readiness, activation, receipt, serving, fallback, or retirement change occurred.


## RT-1D-R2C completion and mandatory P8 (historical)

RT-1D-R2C completed in implementation PR #814 from bootstrap `ed078788e89d74caaa9219dec66fc3b1278dcb45`, final reviewed head `f2f42788348c00368085bba51bdb9130363564c9`, and exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`. Its two commits changed exactly 30 authorized paths, +260/-58: seven production Correct/Forget carriage paths and 23 frozen non-production caller assignments. External Python 3.12 validation passed 1049 tests in 683.23 seconds; every applicable exact-head workflow succeeded.

Correct and Forget roots derive the immutable Primary writer decision only through `relaylm/subjective_mem_retrieval_cutover.py`; public and internal apply/recovery boundaries fail closed before governed effects. No decision enters a durable schema or byte representation. R2B runner and R2D Pin/Unpin sites in the three overlap files remained byte-exact. Primary remains the sole ordinary authority; Subjective ordinary Retrieval remains disabled and unwired. No intent, fence record, readiness, activation, receipt, serving, fallback, or retirement behavior changed.

The mandatory R2C P8 authority sync was the transaction at that historical point and requires no recursive P8. After its independently verified result, at that historical point, RT-1D-R2D was next and had not started; at that historical point, R3, R4, and R5 had not started.


## RT-1D-R2D completion and mandatory P8 (current)

RT-1D-R2D completed in implementation PR #818 from reviewed head `992496748efc70d51a7ed356e23aea650220902c` with exact squash result `a2197e9f92a8067d733f8adba524bf54eb2708b6`. Its two pre-squash commits changed exactly 10 paths, +119/-43: four production paths (`relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/relaymem_primary_pin.py`, `relaylm/relaymem_primary_pin_apply.py`, and `relaylm/soul_lab_memory_pin_routes.py`) and six non-production paths (the semantic-owner test, four I-5B Pin/Unpin smokes, and lifecycle characterization).

`SubjectiveMemRetrievalPrimaryWriterDecision` remains the sole exact immutable Primary writer decision and `primary_writer_decision_permits_write` remains the sole semantic predicate. The P6 correction totalized malformed exact-type validation for uninitialized and partial instances, missing fields, wrong primitive types, unhashable values, and hostile equality values; all return `False`. The predicate retains its exact-type check and catches only `SubjectiveMemRetrievalCutoverError`. The downstream generic `except Exception` wrapper was removed. Pin/Unpin apply validates the exact decision before request validation, store-root resolution, store access, locking, replay, publication, or any durable effect. Soul Lab roots derive only through the sole resolver and carry that exact value.

Focused semantic-owner/lifecycle validation passed 126 tests, all four I-5B Pin/Unpin smokes passed, the external Python 3.12 suite passed 1063 tests with one dependency deprecation warning, execution safety passed, and every applicable exact-head GitHub check passed. No decision is serialized or persisted and no durable schema or bytes changed. Primary MEM remains the sole ordinary served memory and Retrieval authority; Subjective ordinary Retrieval remains disabled and unwired. No durable intent, fence record, readiness, activation, transfer receipt, serving, fallback, retirement, or R3 behavior was introduced.

The current transaction is the mandatory RT-1D-R2D P8 authority synchronization. This documentation-only P8 requires no recursive P8. Only after this P8 is merged and its exact resulting main is independently verified may RT-1D-R3 become uniquely next; RT-1D-R3 is not started, and RT-1D-R4 and RT-1D-R5 remain not started. R3 may bootstrap only from that verified P8 result, never PR #818 head or an unmerged P8 head.
