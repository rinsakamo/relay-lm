---
relaylm_doc_type: contract
relaylm_authority: current_primary_mem_claimed_worker_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - Primary worker request/result/projection schema changes
  - protected worker-source or request-scope semantics change
  - lease checkpoint or queue-transition behavior changes
  - RelayMEM Primary pipeline/outcome mapping changes
  - caller-carried Primary writer-decision consumption changes
  - protected-source restart rehydration behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - RT-1/R5/R6 cutover state, writer-decision resolution, writer permission policy, or Primary retirement approval
  - RelayMEM page/index/log meaning or memory-policy semantics
  - B3 durable queue state-machine schema
  - queue scanning, scheduling, worker pools, or daemon supervision
  - Secondary MEM consolidation
  - RelaySOUL mutation or visible-response behavior
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase6c1_primary_mem_worker_contract.md
  - ../../architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - ../../architecture/phase6c1_relaymem_primary_pipeline_compose.md
  - ../../architecture/phase6c1_primary_worker_outcome_classifier.md
  - ../../architecture/phase6c1_durable_protected_source_persistence.md
  - ../../architecture/phase6c2_one_queued_primary_worker_integration.md
  - ../../architecture/memory/formation.md
  - durable-queue.md
relaylm_verified_by:
  - ../../../scripts/relaylm_phase6c1_primary_worker_smoke.py
  - ../../../scripts/relaylm_phase6c1_worker_contract_smoke.py
  - ../../../scripts/relaylm_phase6c1_worker_lease_race_smoke.py
  - ../../../scripts/relaylm_phase6c1_primary_worker_security_smoke.py
  - ../../../scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py
  - ../../../scripts/relaylm_phase6c1_durable_source_restart_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM/RelaySLP claimed-worker and queued-job-runner maintainers
  - Primary pipeline, protected-source, queue/recovery, and outcome-classifier maintainers
  - RT-1 cutover integration reviewers consuming this worker as a bounded compatibility surface
  - security, privacy, durability, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Primary MEM Claimed-Worker Contract

## Authority summary

This contract owns the exact current Phase 6-C1 boundary for executing one already-claimed Primary MEM job.

The core flow is:

```text
caller-carried exact Primary writer decision
  + exact active B3 claimed record
  + exact protected worker-source bundle
  + one request-local source scope
  + queue/store roots and worker gates
  -> exact request validation
  -> writer decision must permit
  -> active lease/source correlation validation
  -> RelayMEM Primary M3a-M3h pipeline
  -> pure worker outcome classification
  -> final active-lease fence
  -> B3 retry-release or terminal commit
```

This contract describes how the worker **consumes** writer authorization. It does not decide whether the Primary writer should be permitted, fenced, retired, restored, or replaced.

RT-1/R5/R6 cutover authority remains external to this contract and to Lane D.

## Current implementation anchors

The public worker API is implemented by:

```text
relaylm/relaymem_slp_primary_worker.py
```

Runtime-private worker implementation is split across:

```text
relaylm/_relaymem_slp_primary_worker_types.py
relaylm/_relaymem_slp_primary_worker_validate.py
relaylm/_relaymem_slp_primary_worker_execute.py
relaylm/_relaymem_slp_primary_worker_fence.py
relaylm/_relaymem_slp_primary_worker_pipeline.py
relaylm/_relaymem_slp_primary_worker_outcome_adapter.py
relaylm/_relaymem_slp_primary_worker_view.py
```

Protected source ownership is implemented by:

```text
relaylm/relaymem_slp_primary_worker_source.py
```

and durable source persistence/rehydration remains separately implemented within the current C1-5 source-store boundary.

The RelayMEM Primary pipeline and pure worker outcome classifier remain separately owned implementation components consumed by this worker.

## Current worker schemas

The exact current worker schema identifiers are:

```text
request     = relaymem.slp_primary_worker_request.v0
result      = relaymem.slp_primary_worker_result.v0
projection  = relaymem.slp_primary_worker_projection.v0
```

The exact current protected-source schemas include:

```text
source      = relaymem.slp_primary_worker_source.v0
projection  = relaymem.slp_primary_worker_source_projection.v0
build       = relaymem.slp_primary_worker_source_build.v0
```

The exact governed-experience schema consumed by the source boundary is:

```text
relaymem.governed_experience_summary.v0
```

## Current worker statuses

The exact current `WorkerStatus` vocabulary is:

```text
disabled
dry_run_ready
invalid_input
lease_invalid_before_source
source_invalid
pipeline_blocked
pipeline_held
lease_lost_before_m3e
lease_lost_before_m3g
lease_lost_before_transition
retry_released
terminal_succeeded
terminal_failed
transition_failed
```

No queued/scanning/service-loop status is part of the one-claimed worker contract.

## Current lease checkpoint names

The exact current internal worker checkpoint names are:

```text
before_source_consumption
before_m3e_page_writer
before_m3g_reconciliation_apply
```

A final active-claim check also occurs before the B3 retry/terminal transition.

These are B3 lease/claim fences. They are not independent writer-authorization sources.

## Exact request shape

`RelayMEMSLPPrimaryWorkerRequest` carries exactly:

```text
schema_version
runtime_private
content_included
primary_writer_decision
claimed_record
worker_source
request_scope
queue_root
store_root
enabled
dry_run_only
apply_enabled
lease_duration_seconds
retry_not_before
```

The request is runtime-private and content-bearing because the protected source is part of the worker call.

The public worker diagnostics never expose that protected source body.

## Primary writer-decision boundary

The request must carry the exact immutable Primary writer-decision type supplied by the owning cutover integration.

The worker does not:

- resolve cutover state;
- infer permission from queue state;
- infer permission from existing memory;
- infer permission from protected-source availability;
- infer permission from prior worker success;
- infer permission from dispatch or memory idempotency state;
- mint or refresh a writer decision;
- cache an old writer decision for a future job.

After exact request validation, the worker calls the current permission predicate on the carried decision.

When that predicate does not permit writing, execution returns:

```text
status = invalid_input
reason = primary_writer_decision_rejected
```

before active-claim/source/pipeline execution.

This rejection is an authorization/input boundary, not a memory-policy outcome and not a retry-policy classification.

## Defense-in-depth writer checks

The current Primary compatibility path checks the same caller-carried decision at more than one execution boundary, including the claimed worker and the Primary pipeline compose boundary.

Those checks consume one external decision. They do not make the worker or pipeline owner of RT-1 cutover state.

A caller cannot regain Primary write authority by bypassing an outer wrapper while still entering a current boundary that independently checks the same decision.

## Protected source is not authorization

A protected worker source may remain valid and durable while the writer decision is rejected.

That preserves evidence/work material only.

The stable rule is:

```text
source available
  != active claim valid
  != Primary writer decision permitted
  != memory mutation authorized
```

Neither source persistence nor crash recovery restores writer permission.

## Protected worker-source shape

`RelayMEMSLPPrimaryWorkerSource` is an exact immutable runtime-private content-bearing object containing:

```text
schema_version
runtime_private
content_included
job_id
dispatch_idempotency_key
run_id
turn_index
session_id
namespace
source_event_kind
source_count
source_lineage_fingerprint
relayscn_scene_policy_artifact
relayemo_artifact
governed_messages
governed_experience_artifact
```

It also carries private request-scope ownership/nonce state that is not serialized as public diagnostics.

The source is not reconstructed from the content-free queue record.

## Governed message bounds

The current source helper accepts governed message roles from:

```text
system
developer
user
assistant
```

Current source bounds include:

```text
MAX_MESSAGES            = 32
MAX_SOURCES             = 32
MAX_MESSAGE_CHARS       = 32768
MAX_TOTAL_MESSAGE_CHARS = 128 * 1024
MAX_TITLE_CHARS         = 160
MAX_SUMMARY_CHARS       = 2048
MAX_JSON_DEPTH          = 12
MAX_JSON_NODES          = 4096
```

These are source-validation limits, not general model-context limits.

## Request-local source scope

`RelayMEMSLPPrimaryWorkerSourceScope` owns one in-process source lifetime.

A source is valid only while:

- the exact scope remains active;
- the source belongs to that exact scope;
- the source has not already been consumed.

Closing the scope makes retained sources stale.

Cross-request use is rejected.

Source consumption is one-shot within the scope.

This runtime scope is not a durable source identifier and not writer authority.

## Source build gate

The current source builder uses exact boolean controls:

```text
enabled
dry_run_only
apply_enabled
```

It requires an exact active request scope and one exact canonical claimed record.

When non-dry-run is requested without apply enabled, source construction blocks with:

```text
apply_gate_incomplete
```

A successful build is:

```text
dry_run_ready
```

in dry-run mode and:

```text
ready
```

when apply is enabled.

The source builder performs no queue I/O, worker invocation, RelaySLP execution, memory write, SOUL mutation, or visible-response change.

## Source correlation

The source is correlated to the claimed record through the current exact queue/worker identity fields, including:

- job ID;
- dispatch idempotency key;
- run/turn/session correlation;
- namespace;
- source-event kind;
- source count;
- source-lineage fingerprint.

Mismatch blocks source use.

The worker does not reconstruct missing source content from queue metadata, generic trace, public projections, or visible-response logs.

## Protected content boundary

The source can contain governed message content and governed experience title/summary material needed by RelayMEM formation.

That protected content must not enter:

- the durable B2/B3 queue record;
- generic `PipelineNodeResult` diagnostics;
- public worker projections;
- generic trace;
- public error payloads;
- SOUL Lab observation receipts.

The content-free queue carries correlation and lineage references only.

## Source public projection

The source projection is intentionally content-free and may report bounded metadata such as:

```text
status
enabled
dry_run_only
source_bundle_present
source_correlation_valid
message_count
governed_experience_present
scene_policy_present
relayemo_present
blocked_reason_ids
```

It explicitly omits raw text/messages, governed title/summary, memory body, paths, hashes, identifier values, idempotency keys, lease tokens, and exception text.

## Restart-complete source principle

The current C1 source persistence path stores protected worker-source material separately from the content-free queue before durable queue publication and can rehydrate it for a later exact claim.

A later rehydrated claim receives a fresh in-process source object and fresh request-local scope.

The durable source does not become a general public record and does not embed itself into the queue JSON.

A missing/corrupt durable source after restart fails closed; queue metadata is not used as a content substitute.

The rehydrated worker call must still carry a currently valid external Primary writer decision.

## Claimed-record prerequisite

The worker consumes one complete canonical `relaymem.slp_durable_job.v0` record in:

```text
state = claimed
```

with current claim/lease invariants such as:

```text
claim_owner present
lease_token present
claim_generation >= 1
attempt_count == claim_generation
lease_acquired_at < lease_expires_at
retry_not_before = null
terminal_reason_id = ""
```

A public queue projection is never a substitute for the private canonical record.

## Active-claim fence

The current execution fence contains the canonical combination of:

```text
job_id
dispatch_idempotency_key
record_revision
state = claimed
claim_owner
claim_generation
lease_token
unexpired lease
```

A stale worker must not begin a new side effect after losing this fence.

## Checkpoint sequence

After the writer-decision gate, the current worker uses claim/lease checks around critical execution boundaries.

Conceptually:

```text
writer decision permitted
  -> initial active-claim check
  -> source validation/consumption checkpoint
  -> pipeline execution
       -> before M3e publication checkpoint
       -> before M3g reconciliation apply checkpoint
  -> pure outcome classification
  -> final active-claim check
  -> B3 transition
```

Successful renewals update the worker's current canonical record/revision before later checks.

## Lease loss

On lease expiry, stale recovery, revision conflict, owner mismatch, generation mismatch, token mismatch, or other active-fence loss:

- no new side effect begins after the failed checkpoint;
- the worker does not claim success;
- stale retry/terminal transition is not attempted;
- already completed durable effects are not rolled back;
- a later exact claim may converge through durable idempotency, subject to a fresh caller-carried writer decision.

Lease validity is necessary execution authority but not Primary writer permission.

## RelayMEM pipeline boundary

The worker calls the existing RelayMEM Primary compose function rather than duplicating M3 semantics.

The current canonical stage order is:

```text
M3a formation candidate
M3b source lineage + write preflight
M3c deterministic page candidate
M3d writer handoff
M3e atomic page publication
M3f reconciliation plan
M3g index-before-log apply
M3h read-only recovery audit
```

Each underlying validator remains authoritative for its own stage.

The worker owns orchestration and fence placement, not memory meaning or page/index/log schemas.

## Dry-run worker behavior

When the exact request remains in dry-run mode, the worker executes the dry-run-safe Primary pipeline path under the same source/claim/writer-decision boundary and does not apply a B3 terminal/retry transition.

Current pipeline result mapping includes:

```text
pipeline dry_run_ready -> worker dry_run_ready
pipeline held          -> worker pipeline_held
other non-success      -> worker pipeline_blocked
```

Dry-run is not a writer-decision bypass; the decision check still occurs before worker/pipeline execution.

## Apply worker behavior

In apply mode, after pipeline execution the worker uses the pure C1 outcome classifier and then rechecks the current active claim before queue transition.

A successful outcome transition is one of:

```text
commit_succeeded -> worker terminal_succeeded
retry_release    -> worker retry_released
commit_failed    -> worker terminal_failed
```

The queue transition must itself be exact, applied, and durability-confirmed.

Otherwise worker status is:

```text
transition_failed
```

## Pure outcome classification boundary

RelayMEM owns the meaning of M3 stage evidence.

The worker outcome classifier maps exact bounded RelayMEM evidence to an existing B3 transition kind.

Writer-decision rejection occurs before that classifier and is not translated into:

- memory policy hold;
- retry release;
- terminal memory-policy failure;
- reconciliation state;
- recovery classification.

## Terminal success rule

A worker may reach terminal success only after the existing RelayMEM chain establishes durable exactness and the final B3 claim fence remains valid.

Current successful durability conditions include exact/idempotently exact page publication, applied/already-applied reconciliation, and a recovery audit that does not require recovery.

The queue terminal success reason remains bounded and content-free.

No durable success evidence can retroactively override a rejected future writer decision for another invocation.

## Retry-release boundary

The worker may request B3 retry release only for current bounded retryable classifications such as transient resource contention or verified reconciliation partial progress.

B3 stores the queue-control retry metadata; the worker/outcome layer provides the bounded classification.

A queued retry preserves work availability, not Primary writer permission.

Each future invocation must independently carry the external writer decision required by current execution boundaries.

## Policy/corruption/recovery failure direction

Memory-policy held/blocked, manual confirmation, uncertain/corrupt/diverged store state, source corruption/correlation mismatch, and unsupported recovery conditions never become terminal success.

They are mapped to the current bounded terminal/retry/block outcomes under the owning classifier and queue transition contracts.

The worker does not repair an uncertain memory store by guessing from the queue record or protected source.

## Dispatch and memory-write idempotency

The worker carries the Phase 6 dispatch identity through its claimed record, but memory-write idempotency remains produced/owned by RelayMEM M3b and propagated through the RelayMEM pipeline.

The domains remain separate:

```text
dispatch idempotency
  -> queue/execution scheduling identity

memory-write idempotency
  -> durable Primary memory-apply identity
```

Neither identity is writer authorization.

## Current worker result shape

`RelayMEMSLPPrimaryWorkerResult` contains:

```text
schema_version
status
runtime_private
content_included
enabled
dry_run_only
apply_enabled
initial_claim_valid
source_checkpoint_passed
m3e_checkpoint_passed
m3g_checkpoint_passed
final_checkpoint_passed
lease_renewal_count
pipeline_result
outcome_result
queue_transition_result
side_effect_started
queue_transition_performed
reason_ids
```

The nested pipeline/outcome/queue results are runtime-private and omitted from the public projection.

## Current worker projection shape

`RelayMEMSLPPrimaryWorkerProjection` contains:

```text
status
enabled
dry_run_only
apply_enabled
initial_lease_valid
source_checkpoint_passed
m3e_checkpoint_passed
m3g_checkpoint_passed
final_checkpoint_passed
lease_renewed
lease_renewal_count
pipeline_status
outcome_transition_kind
queue_transition_performed
retryable
terminal
succeeded
failed
reason_ids
```

Its exact schema is:

```text
relaymem.slp_primary_worker_projection.v0
```

## Public projection omissions

The projection's log dictionary explicitly reports that it omits:

- raw messages;
- governed title/summary;
- source body;
- page/index/log content;
- queue/store roots and queue filename;
- namespace and runtime identifier values;
- lineage fingerprint;
- dispatch and memory idempotency keys;
- claim owner and lease token;
- record revision and claim generation;
- exact timestamps/retry timestamps;
- exception text;
- private pipeline/outcome/queue results.

Generic worker diagnostics therefore remain content-free even though the worker itself operates in a protected content-bearing domain.

## Projection validation

The public wrapper validates the private worker result before returning its projection.

It also verifies the exact lease-renewal checkpoint ledger:

```text
lease_renewal_count
  == int(m3e_checkpoint_passed)
   + int(m3g_checkpoint_passed)
```

A malformed result ledger does not silently produce a trusted public projection.

## PipelineNodeResult mapping

The current worker node is:

```text
relaymem_slp_primary_worker
```

Current explicit node-status mapping includes:

```text
disabled            -> skipped
dry_run_ready       -> diagnostic_only
terminal_succeeded  -> applied
retry_released      -> blocked
terminal_failed     -> failed
invalid_input       -> failed
transition_failed   -> failed
other statuses      -> blocked
```

The artifact projection is content-free and omits the private result/source/pipeline/outcome/queue record/fence.

It may report whether a queue transition occurred and whether a memory side effect had started.

## Observation boundary

The public worker wrapper may capture a Phase I-2 observation after execution through the existing observation subsystem.

Observation is read-only evidence/projection. It is not:

- a worker replay command;
- source content authority;
- queue-transition authority;
- memory-write authority;
- writer-decision authority.

Observation failure does not redefine the worker's underlying durable result.

## Crash/restart convergence

The current worker design supports bounded crash/restart convergence around stages including:

- after claim before source consumption;
- after page publication before reconciliation planning;
- after index publication before log publication;
- after full reconciliation before B3 terminal commit;
- lease expiry followed by stale recovery.

A later claim revalidates/re-hydrates the exact protected source, reruns the deterministic RelayMEM chain, and relies on memory-write idempotency plus B3 fencing to converge.

It must also carry a writer decision accepted for that later invocation.

## Worker does not scan the queue

This C1 worker receives one already-claimed record.

It does not:

- discover a queued record;
- choose among queued jobs;
- perform scheduler fairness;
- claim a queued record on its own;
- run a worker pool;
- sleep/poll forever;
- supervise a daemon.

The C2/runner/scheduler layers remain separate.

## Worker does not own writer retirement

The worker remains a compatibility execution surface only for as long as the external current authority supplies a permitted writer decision.

This contract must not be cited as evidence that:

- Primary remains the current writer indefinitely;
- R5 has or has not completed final retirement;
- a fenced writer can be reactivated;
- Lane D may change cutover status;
- a stored source/queue item preserves historical writer permission.

Those decisions remain under RT-1/R5/R6 authority outside this document.

## Visible-response independence

The worker executes detached memory work after the owning response-finalization/queue boundaries.

Worker failure must not:

- replace an already selected HTTP response;
- rewrite visible response text;
- initiate a second backend generation;
- synchronously force memory persistence into the request response path;
- trigger TTS/audio/avatar execution;
- mutate RelaySOUL as a fallback.

## Stable invariants

- The worker consumes one already-claimed canonical B3 record only.
- The worker requires an exact caller-carried Primary writer decision and rejects non-permitted decisions before claim/source/pipeline execution.
- The worker does not resolve, cache, infer, or restore writer permission.
- Protected source availability is not writer authorization.
- Protected source content remains separate from the content-free durable queue and generic diagnostics.
- Worker-source scope is request-local and one-shot.
- Source/claim correlation must be exact before content consumption.
- Active B3 claim/lease fencing is rechecked around irreversible pipeline effects and before queue transition.
- Lease loss prevents new stale-worker effects but does not roll back already durable effects.
- RelayMEM owns M3 meaning and memory-write idempotency; the worker owns orchestration/fencing only.
- Dispatch and memory-write idempotency remain separate and neither is authorization.
- Dry-run still requires writer permission.
- Apply outcome transitions remain limited to current B3 retry/terminal operations.
- Public worker/source projections remain content-free.
- Crash recovery never reconstructs protected content from queue metadata and never restores writer permission.
- C1 does not scan, claim, schedule, pool, or daemonize work.
- RT-1/R5/R6 remain the only owners of writer cutover/retirement authority.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- RT-1/R5/R6 cutover state or permission policy;
- Primary writer activation/retirement disposition;
- queue scanning/claim selection;
- scheduler fairness/backoff/service loops;
- Secondary MEM consolidation;
- exact RelayMEM page/index/log schemas or memory-policy meaning;
- memory-write idempotency schema;
- protected-source storage-format details beyond the worker's required boundary;
- RelaySOUL mutation;
- visible response, TTS, audio, or avatar execution;
- source retirement;
- repository-level sequencing.

## Related architecture and contracts

- [Phase 6-C1 transitional worker contract](../../architecture/phase6c1_primary_mem_worker_contract.md)
- [One Claimed Primary Worker](../../architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Primary Pipeline Compose](../../architecture/phase6c1_relaymem_primary_pipeline_compose.md)
- [Primary Worker Outcome Classifier](../../architecture/phase6c1_primary_worker_outcome_classifier.md)
- [Durable Protected Source Persistence](../../architecture/phase6c1_durable_protected_source_persistence.md)
- [Durable Queue Contract](durable-queue.md)
- [Memory Formation Architecture](../../architecture/memory/formation.md)
