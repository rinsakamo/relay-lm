---
relaylm_doc_type: contract
relaylm_authority: current_pre_enqueue_durable_finalization_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - durable-finalization base/segment/seal schema or publication ordering changes
  - one-record replay/completion convergence changes
  - completion/isolation marker schema changes
  - retention classification or cleanup semantics change
  - source-before-queue restart convergence changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - B3 queue claim/retry/terminal lifecycle
  - C2 or worker execution
  - Primary/Secondary memory formation or memory-write semantics
  - O1 scheduler discovery, fairness, polling, or service lifecycle
  - protected-source storage schema beyond exact convergence checks required here
  - RelaySOUL mutation or visible-response semantics beyond the publication ordering boundary
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/i1g_pre_enqueue_durable_finalization_contract.md
  - ../../architecture/i1gd_durable_finalization_retention_cleanup.md
  - ../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - ../../architecture/phase6c1_durable_protected_source_persistence.md
  - ../../architecture/o1b_sealed_i1g_replay_lane.md
  - durable-queue.md
  - primary-worker.md
relaylm_verified_by:
  - ../../../scripts/relaylm_i1gb_durable_finalization_publication_smoke.py
  - ../../../scripts/relaylm_i1gc_durable_finalization_replay_smoke.py
  - ../../../scripts/relaylm_i1gd_durable_finalization_retention_contract_smoke.py
  - ../../../scripts/relaylm_i1gd_durable_finalization_retention_race_smoke.py
  - ../../../scripts/relaylm_i1ge_durable_finalization_security_smoke.py
  - ../../../scripts/relaylm_i1ge_durable_finalization_concurrency_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM/RelaySLP response-finalization, restart-replay, and retention maintainers
  - protected-source and durable-queue maintainers
  - scheduler replay-lane, crash-recovery, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelaySLP Durable Finalization Contract

## Authority summary

This contract owns the exact current pre-enqueue durable-finalization responsibility spanning I1-GB publication, I1-GC one-record replay/completion convergence, and I1-GD bounded retention/isolation/cleanup.

The stable recovery chain is:

```text
final safe visible turn
  -> durable base / zero-or-more stream segments / seal
  -> visible body, protected stream unit, or terminal completion may be released
  -> normal finalizer or caller-selected restart replay
  -> exact protected source convergence
  -> exact durable queue convergence
  -> immutable completion marker
  -> later bounded retention / isolation / cleanup
```

The fundamental ordering rule is:

```text
valid durable protected source
  before
claimable canonical queue record
```

Durable finalization is evidence and restart convergence. It is not a second queue, not worker execution, not memory formation, and not a scheduler loop.

## Current implementation anchors

The exact current record model and store boundaries are implemented by:

```text
relaylm/relaymem_slp_durable_finalization_record.py
relaylm/relaymem_slp_durable_finalization_store.py
```

Replay/completion is implemented by:

```text
relaylm/relaymem_slp_durable_finalization_replay.py
relaylm/_relaymem_slp_durable_finalization_replay_impl.py
```

Retention/isolation is implemented by:

```text
relaylm/relaymem_slp_durable_finalization_retention.py
relaylm/_relaymem_slp_durable_finalization_retention_impl.py
relaylm/relaymem_slp_durable_finalization_isolation.py
relaylm/relaymem_slp_durable_finalization_fence.py
```

The existing I1-G/I1-GD architecture documents remain transitional current sources. This transaction does not retire them.

## Current schema identifiers

The exact current durable evidence schema is:

```text
relaymem.slp_durable_finalization.v0
```

The current durable evidence public projection schema is:

```text
relaymem.slp_durable_finalization_projection.v0
```

The completion schema is:

```text
relaymem.slp_durable_finalization_completion.v0
```

The replay public projection schema is:

```text
relaymem.slp_durable_finalization_replay_projection.v0
```

The retention public projection schema is:

```text
relaymem.slp_durable_finalization_retention_projection.v0
```

The current isolation-marker schema remains:

```text
relaymem.slp_durable_finalization_isolation.v0
```

## Logical record structure

One logical durable-finalization record consists of:

```text
one immutable base record
zero or more immutable ordered segment records
one immutable seal record
optional immutable completion marker
optional isolation marker during retention/cleanup lifecycle
one shared per-locator replay/maintenance fence file
```

The base/segment/seal record revision is currently:

```text
0
```

The completion revision is also currently:

```text
0
```

## Base record fields

The exact current base record key set is:

```text
schema_version
runtime_private
content_included
record_kind
record_revision
locator_digest
run_id
turn_index
character_id
request_correlation
stream_mode
static_finalized_turn_inputs
base_digest
```

A valid base record has:

```text
schema_version = relaymem.slp_durable_finalization.v0
runtime_private = true
content_included = true
record_kind = base
record_revision = 0
```

The base digest is derived from canonical record content excluding the digest field itself.

## Segment record fields

The exact current segment key set is:

```text
schema_version
runtime_private
content_included
record_kind
record_revision
locator_digest
run_id
turn_index
character_id
segment_sequence
previous_segment_digest
content_byte_count
content_b64
segment_digest
```

Each segment is immutable, sequence-numbered, and hash-chained to the previous segment digest.

Segment content must be non-empty UTF-8 bytes before base64 encoding.

The current segment filename uses a zero-padded six-digit sequence number, and the accepted sequence bound is:

```text
0..999999
```

## Seal record fields

The exact current seal key set is:

```text
schema_version
runtime_private
content_included
record_kind
record_revision
locator_digest
run_id
turn_index
character_id
base_digest
segment_count
final_segment_digest
visible_content_byte_count
visible_content_b64
finalized_turn_source
durable_job
job_id
dispatch_idempotency_key
seal_digest
```

A seal contains the exact finalized-turn source and exact B1 durable-job identity required for later replay reconstruction.

It is not a queue record. The nested durable-job candidate is sealed evidence used to verify that replay reconstructs the same dispatch/job identity before downstream convergence.

## Finalized-source field set

The current sealed finalized-source mapping contains exactly:

```text
schema_version
character_id
run_id
turn_index
session_id
namespace
source_event_kind
source_count
persistence_policy_status
source_lineage_artifact
relayscn_scene_policy_artifact
relayemo_artifact
governed_messages
governed_experience_artifact
formation_summary_artifact
```

This is runtime-private protected content. It must not appear in generic public projections.

## Locator identity

The locator digest is derived deterministically from:

```text
record schema
locator version
run_id
turn_index
character_id
```

using canonical JSON and SHA-256.

The current locator version is:

```text
relaymem.slp_durable_finalization_locator.v0
```

A locator is therefore turn/character correlation identity for this recovery record, not a queue job ID and not a memory-write idempotency key.

## Canonical JSON boundary

Durable-finalization records use canonical JSON bytes with:

```text
ensure_ascii = true
sort_keys = true
separators = (",", ":")
allow_nan = false
UTF-8
```

Canonical decode rejects:

```text
durable_finalization_malformed_utf8
durable_finalization_malformed_json
durable_finalization_duplicate_json_key
durable_finalization_json_not_object
durable_finalization_noncanonical_json
```

Readers do not silently rewrite noncanonical evidence into accepted evidence.

## Publication filenames

Current logical record filenames are deterministic from the locator:

```text
durable-finalization-v0-<locator>.base.json
durable-finalization-v0-<locator>.segment-<six-digit-sequence>.json
durable-finalization-v0-<locator>.seal.json
```

Completion uses the separate prefix:

```text
durable-finalization-completion-v0-<locator>.json
```

The shared replay/maintenance fence uses:

```text
.durable-finalization-replay-v0-<locator>.lock
```

Path construction never accepts arbitrary caller filenames.

## Publication ordering

For a non-stream response, the current durable-finalization apply path establishes the complete sealed evidence before visible body release.

For a stream, each protected visible segment is durably published/reread before the corresponding visible bytes are yielded, and the final seal is durable before terminal stream completion is released.

The stable ordering is:

```text
base commit + canonical reread
  -> each segment commit + canonical reread before corresponding yield
  -> exact finalized source + A1/A2/B1 preparation
  -> seal commit + canonical reread
  -> visible release / terminal completion release
```

This closes the crash window in which visible output could otherwise be irrecoverably released before sufficient restart evidence existed.

## Record evidence is not downstream success

A valid seal means the finalized turn and expected B1 dispatch identity can be reconstructed exactly.

It does not mean:

- C1-5 protected source is already durable;
- B2 queue record is already durable;
- B3 job is claimed or terminal;
- a worker ran;
- Primary memory formed or persisted;
- retrieval will use the memory.

Those later states retain their own authorities.

## Completion marker fields

The exact current completion key set is:

```text
schema_version
runtime_private
content_included
record_kind
record_revision
locator_digest
sealed_record_schema
sealed_record_revision
seal_digest
durable_job_digest
protected_source_integrity_digest
completion_digest
```

The completion marker is content-free relative to the protected source: it carries digests/proof, not the sealed user/model/source body.

The exact current maximum completion-file size is:

```text
16 KiB
```

## Meaning of completion

A valid completion marker means I1-GC has canonically verified convergence of:

```text
sealed durable-finalization evidence
  + exact reconstructed finalized-turn source / B1 identity
  + exact durable protected source
  + exact B2 durable queue record
  + source-before-queue ordering
```

It does not mean B3 terminal success, worker execution, memory formation, memory apply, or semantic quality.

## One-record replay entry

The current public replay entry is:

```text
replay_relaymem_slp_durable_finalization_record(
    config,
    *,
    locator_digest,
    registry,
    fault_injector=None,
)
```

The caller supplies exactly one locator digest.

I1-GC does not scan the durable-finalization root, choose a locator, poll, sleep, or run a retry loop.

Discovery is separately owned by the O1B scheduler replay lane.

## Replay status vocabulary

The exact current replay status vocabulary is:

```text
disabled
dry_run_ready
invalid_input
record_missing
not_replayable
already_complete
replay_lock_busy
source_pending
queue_pending
completion_pending
completed
exact_duplicate
content_collision
corrupt
schema_unsupported
unsafe_path_or_type
invariant_violation
blocked
ambiguous
failed
```

These statuses describe one replay/convergence attempt only.

## Replay fault-stage vocabulary

The exact current replay fault-stage vocabulary is:

```text
none
after_lock_before_reread
after_source_commit_before_queue
after_queue_commit_before_completion
during_queue_outcome_ambiguity
during_completion_publish
after_completion_publish_before_return
```

Fault injection is a test/validation seam, not production client authority.

## Replay fence

I1-GC uses one nonblocking exclusive per-locator cross-process fence.

Unsafe lock-file type/link state fails closed.

Contention returns the bounded replay-lock-busy outcome rather than blocking indefinitely or running a second concurrent convergence for the same locator.

The same locator fence is shared with I1-GD maintenance.

## Replay reread rule

After acquiring the fence, I1-GC canonically rereads durable evidence and completion state before deciding what work remains.

It never trusts an earlier in-memory view as current durable truth.

A valid existing completion returns `already_complete` without recreating downstream artifacts.

Malformed, unsupported, isolated, collision, unsafe, or impossible evidence fails closed without worker execution.

## Reconstruction and identity proof

Replay reconstructs the exact finalized-turn production type from sealed evidence and reruns existing A1/A2/B1 preparation.

The reconstructed B1 durable job and dispatch identity must equal the identity sealed in the durable-finalization record.

Replay does not invent replacement values for:

- time;
- run/turn/session identity;
- namespace;
- source lineage;
- job ID;
- dispatch idempotency key;
- governed content.

An identity mismatch is a collision/invariant failure, not a repair opportunity.

## Source-before-queue convergence

I1-GC always converges the protected source before the B2 queue record.

The current decision sequence is:

```text
inspect protected source
  -> absent: publish under existing C1-5 authority
  -> exact: continue
  -> collision/corrupt/unsafe/ambiguous: fail closed

only after exact source proof:
inspect B2 durable queue record
  -> absent: publish under B2 authority
  -> exact: continue
  -> collision/corrupt/unsafe/ambiguous: fail closed
```

A queue-present/source-absent state is an invariant violation. Replay does not fabricate the missing source from the queue and does not delete the queue record.

## Ambiguous mutation outcomes

If a source, queue, or completion mutation reports an ambiguous outcome, I1-GC resolves it only by canonical durable reread.

It does not convert an uncertain write exception into success from process-local assumptions.

Exact durable state after reread is the deciding evidence.

## Existing terminal B3 record

A B2/B3 queue record that has already progressed to a valid terminal B3 state is left unchanged.

If it remains exactly correlated with the sealed source/dispatch identity, it may still satisfy I1-G completion proof.

I1-GC never rewinds a terminal queue record to `queued` merely to recreate an earlier state.

## Completion publication

The completion marker is published with no-clobber semantics and directory durability, then canonically reread.

Exact repeated completion converges as a duplicate.

Different valid content at the same completion identity is a collision and fails closed.

Completion is the last I1-GC durable marker after source/queue proof.

## Replay projection

`RelayMEMSLPDurableFinalizationReplayProjection` exposes bounded content-free state including:

```text
status
enabled
dry_run_only
apply_enabled
record_present
sealed
replayable
source_present
queue_present
queue_terminal
completion_present
source_created
queue_created
completion_created
exact_duplicate
lock_acquired
failure_stage
reason_ids
```

Its public log projection fixes content/privacy omissions including:

```text
content_free = true
content_included = false
raw_text_included = false
raw_messages_included = false
governed_title_included = false
governed_summary_included = false
identifier_values_included = false
namespace_value_included = false
locator_value_included = false
digest_values_included = false
path_values_included = false
timestamp_values_included = false
lease_token_included = false
exception_text_included = false
nested_protected_result_included = false
```

It also reports that worker/C2/B3-memory/SOUL/visible-response/cleanup effects did not occur in replay.

## Replay private result

`RelayMEMSLPDurableFinalizationReplayResult` may retain runtime-private nested reconstruction, preparation, source-store, queue, and durable-runtime results.

Those nested objects are excluded from public projection and `repr` content.

They do not become a public replay API surface.

## Retention entry

The current public maintenance entry is:

```text
maintain_relaymem_slp_durable_finalization_retention(
    *,
    config,
    now_provider=...,
    fault_injector=None,
)
```

One invocation performs one bounded deterministic non-recursive pass and returns.

It never polls, sleeps, starts replay, mutates C1-5/B2/B3/C2/worker state, or performs memory apply.

## Retention status vocabulary

The exact current retention result statuses are:

```text
disabled
dry_run_ready
maintenance_complete
invalid_input
blocked
capacity_exceeded
timeout_reached
failed
```

## Retention classification vocabulary

The exact current locator classifications are:

```text
fresh_incomplete
expired_incomplete_orphan
sealed_pending
complete_retained
complete_retention_expired
isolated_retained
isolated_retention_expired
corrupt_known_locator
unsupported_known_locator
unsafe_or_unclassifiable
ambiguous
```

Classification is refreshed under the owning fences before destructive cleanup.

## Retention inventory rule

I1-GD builds a complete bounded non-recursive inventory before inferring absence.

If the complete scan exceeds the configured logical record count bound, the pass becomes `capacity_exceeded` rather than assuming unobserved records are absent.

Unknown/unsafe objects do not become cleanup candidates merely because they contain a locator-looking substring.

## Sealed-pending retention

A valid sealed record without completion is a pending replayable record.

I1-GD retains `sealed_pending` records and provides no age-only deletion path for them.

Retention must not erase restart evidence that is still needed to converge source/queue/completion.

## Isolation-before-cleanup

Before reclaiming any known durable-finalization components, I1-GD publishes an immutable content-free isolation marker, fsyncs the directory, and canonically rereads the marker.

Only after exact isolation proof may cleanup reclaim stable known components.

The isolation marker is removed last, after the logical components are gone and the configured isolated-retention horizon permits marker cleanup.

This makes interruption during cleanup forward-convergent rather than reopening replay authority halfway through deletion.

## Isolation authority consistency

When an isolation marker exists, current retention hardening checks that:

- marker classification/reason belongs to the current allowed isolation authority;
- observed component flags are structurally valid;
- components did not reappear after isolation;
- components are not newer than the isolation marker.

A violation becomes `ambiguous` or `unsafe_or_unclassifiable` and blocks destructive cleanup.

## Retention shared fence ordering

I1-GD uses the same per-locator fence as I1-GC.

During fresh reread/cleanup it also uses the existing I1-GB root mutation lock under the current storage authority.

This prevents cleanup from racing a publication or replay for the same durable evidence.

The per-record lock file itself is not deleted by retention.

## Completion proof during retention

Retention does not trust a completion file merely because it exists.

For complete-record classification, it reconstructs the exact I1-GC completion proof from validated seal evidence and requires canonical equality with the existing completion marker.

A completion identity collision is not treated as ordinary expired-complete cleanup.

## Retention public projection

The current retention projection may report bounded counts and booleans such as:

```text
status
enabled
dry_run_only
apply_enabled
inventory_complete
bounded_entry_count
bounded_record_count
processed_record_count
retained_count
isolated_count
cleaned_component_count
removed_isolation_count
lock_busy_count
blocked_count
capacity_exceeded
timeout_reached
reason_ids
```

The projection is content-free and omits identifier, namespace, locator, digest, path, timestamp, exception, and nested protected values.

## Default-off apply gates

Durable-finalization publication/replay are default-off and dry-run-first under the current config family:

```text
relaymem_slp_durable_finalization_enabled = false
relaymem_slp_durable_finalization_dry_run_only = true
relaymem_slp_durable_finalization_apply_enabled = false
```

Retention has its own separate default-off/dry-run-first gate:

```text
relaymem_slp_durable_finalization_retention_enabled = false
relaymem_slp_durable_finalization_retention_dry_run_only = true
relaymem_slp_durable_finalization_retention_apply_enabled = false
```

No accepted gate combination creates a scanner loop, polling loop, daemon, worker, or general scheduler.

## Current configured publication bounds

The current durable-finalization configuration includes bounded values for:

```text
root
max_record_bytes
max_segment_bytes
max_segment_count
max_record_count
publication_timeout_ms
```

The current example/default architecture values are:

```text
max_record_bytes = 524288
max_segment_bytes = 65536
max_segment_count = 256
max_record_count = 1024
publication_timeout_ms = 5000
```

These are operational bounds, not permission to broaden record content or path authority.

## Current retention bounds

The current retention family includes:

```text
completed_retention_seconds
orphan_grace_seconds
isolated_retention_seconds
cleanup_max_records_per_pass
cleanup_timeout_ms
```

The public retention facade enforces positive bounded integers and rejects values beyond its current safety maximums.

The current example/default architecture values are:

```text
completed_retention_seconds = 604800
orphan_grace_seconds = 86400
isolated_retention_seconds = 2592000
cleanup_max_records_per_pass = 64
cleanup_timeout_ms = 5000
```

## Secure filesystem boundary

Durable-finalization roots are runtime-private pre-existing roots accepted only through the owning configuration/storage boundary.

Current read/write/fence/cleanup code fails closed on unsafe filesystem states such as:

- symlinked components;
- unexpected file types;
- hard-link anomalies;
- changed inode/type during reread;
- oversized records;
- malformed/noncanonical JSON;
- duplicate JSON keys;
- unsupported schemas/fields;
- path escape or unsafe locator-derived names.

Cleanup does not convert an unsafe object into a known component by guesswork.

## Idempotency and duplicate convergence

Repeated exact publication/replay converges without creating a second logical source/queue/completion.

The stable distinctions are:

```text
same identity + exact canonical content
  -> duplicate/exact convergence

same deterministic location + different valid identity/content
  -> collision

malformed/noncanonical content
  -> corrupt/unsupported/unsafe
```

Collisions and corrupt records are never silently overwritten as duplicates.

## Window-A restart guarantee

The durable-finalization responsibility exists to close the pre-enqueue crash window:

```text
visible output became irreversible
  but
protected source / queue publication had not yet completed
```

I1-GB makes restart evidence durable before the corresponding visible release.

I1-GC can later reconstruct and converge exact source/queue/completion from a caller-selected sealed record.

I1-GD prevents retention from erasing pending replay evidence and makes cleanup crash-convergent.

I1-GE validation proves these existing boundaries with real child-process exit/restart scenarios; I1-GE itself owns validation, not production semantics.

## Window-B remains downstream

After exact protected source and B2 queue publication, restart convergence belongs to the durable queue, C2/worker, and RelayMEM idempotent persistence boundaries.

I1-G completion does not replace:

- B3 claim/lease/retry/terminal state;
- C2 queued-record coordination;
- Primary worker claim fences;
- M3 memory-write idempotency/recovery.

## O1 scheduler boundary

O1B may discover at most one eligible sealed I1-G record and call I1-GC once.

O1B does not reconstruct protected content or decide I1-G completion independently.

After replay, an O1 queue lane may independently discover a newly converged queue record, but replay output is not passed directly as queue/worker authority.

I1-G itself does not scan, poll, sleep, schedule, or supervise.

## Visible-response boundary

Durable-finalization publication participates in the irreversible response-release ordering, but later replay/retention failure must not create a second visible response path.

Replay/retention do not:

- regenerate backend text;
- rewrite an already released response;
- invoke TTS/audio/avatar execution;
- mutate RelaySOUL as fallback;
- synchronously force memory apply into the response path.

## Content boundary

Base/segment/seal evidence is runtime-private and content-bearing where required for exact restart reconstruction.

Completion and public projections remain content-free.

Generic logs/public node results must omit:

- user/assistant/governed message text;
- governed title/summary;
- namespace value;
- run/session/turn/job/dispatch identity values;
- locator and digest values;
- filesystem paths;
- claim/lease tokens;
- exact timestamps;
- raw exceptions;
- nested protected-source/queue/replay results.

## Failure direction

Durable finalization always fails toward less downstream authority:

```text
publication cannot establish exact durable evidence
  -> do not claim sealed/releasable success

replay evidence missing/incomplete/isolated/corrupt/unsupported/unsafe
  -> no downstream convergence

source collision or corruption
  -> no queue publication

queue collision/corruption with exact source present
  -> no completion publication

completion uncertain
  -> canonical reread before success

retention unsafe/ambiguous/incomplete inventory
  -> no destructive cleanup
```

No failure path guesses protected content or broadens queue/worker/memory authority.

## Stable invariants

- The current durable evidence schema is `relaymem.slp_durable_finalization.v0`.
- One logical record is base + ordered segment chain + seal, with completion/isolation as separate lifecycle markers.
- Locator identity is deterministic from run/turn/character correlation.
- Durable JSON must already be canonical; readers do not normalize evidence in place.
- Stream segments are durable before the corresponding protected visible bytes are yielded.
- Seal is durable before final response/stream completion release.
- A valid seal is restart evidence, not queue/worker/memory success.
- I1-GC replays exactly one caller-selected locator and performs no discovery loop.
- I1-GC requires exact reconstruction of the sealed B1 job/dispatch identity.
- Protected source must converge before durable queue publication.
- Queue-present/source-absent is an invariant violation, never a repair shortcut.
- Ambiguous mutation outcomes are resolved by canonical reread only.
- Completion is published last after exact source/queue correlation proof.
- Exact existing terminal B3 state is not rewound by replay.
- I1-GC and I1-GD share the same per-locator replay/maintenance fence.
- Sealed-pending records are retained; age alone cannot erase replay-required evidence.
- Cleanup is isolation-first and marker-last.
- Unsafe/ambiguous retention state is non-destructive.
- Public replay/retention diagnostics are content-free.
- I1-G does not execute C2/workers, perform B3 transitions, write memory, mutate SOUL, or schedule loops.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- O1 replay discovery/fairness/service-loop policy;
- B3 claim/retry/terminal transition semantics;
- C2 or worker execution;
- Primary/Secondary memory formation or persistence semantics;
- protected-source file schema beyond exact convergence requirements;
- memory-write idempotency;
- queue repair/migration;
- TTS/audio/avatar execution;
- RelaySOUL mutation;
- source retirement;
- repository-level sequencing.

## Related architecture and contracts

- [I1-G transitional contract](../../architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD Retention and Cleanup](../../architecture/i1gd_durable_finalization_retention_cleanup.md)
- [Phase 6 I1-B Runtime Enqueue Source Capture](../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Durable Queue Contract](durable-queue.md)
- [Primary Worker Contract](primary-worker.md)
