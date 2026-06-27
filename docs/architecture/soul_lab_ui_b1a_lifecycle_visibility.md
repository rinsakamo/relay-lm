---
relaylm_doc_type: implementation_handoff
relaylm_authority: soul_lab_ui_b1a_lifecycle_visibility
relaylm_status: implemented
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_b0_real_home_conversation.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4d_primary_retrieval_exclusion.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1gd_durable_finalization_retention_cleanup.md
  - i1ge_durable_finalization_crash_validation.md
  - o1d1_production_scheduler_round.md
  - wave3_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - Forget apply
  - Pin apply
  - Held apply
  - SOUL apply
  - queue or scheduler execution
  - recovery, repair, cleanup, restore, purge, or unhide
---
# SOUL Lab UI-B1A Lifecycle Visibility

## Scope and status

UI-B1A adds read-only lifecycle and operation visibility to SOUL Lab after W3-INT. It is implemented as a loopback-only Lab API projection plus UI panels on Home and Lab Observation. The slice does not add a mutation route, command payload, scheduler control, queue control, repair action, recovery action, durable transcript persistence, audio/TTS/avatar behavior, or public/remote binding.

The product goal is interpretability: a user can understand whether current Primary MEM is active or excluded, whether durable-finalization evidence is pending, complete, or isolated, whether queue/worker evidence is queued, processing, formed, held, blocked, or failed, and what New Conversation means without changing runtime state.

## Read-only projection schema

The backend projection schema is:

```text
relaylm.lab.lifecycle_visibility.v0
```

The route is:

```text
GET /lab/api/characters/{character_id}/lab/lifecycle-visibility?namespace=...
```

The route is loopback-only and returns `Cache-Control: no-store`. Character, namespace, and store resolution are server-owned through the existing SOUL Lab observation scope resolver. Browser-provided store paths, namespace authority, queue roots, protected-source roots, scheduler settings, backend credentials, or command payloads are not accepted.

The projection includes:

```text
schema
source = relaylm_runtime
read_only = true
availability
character_id
namespace
memory_items[]
durable_finalization
queue_worker
fresh_conversation
mutation_controls_exposed = false
scheduler_controls_exposed = false
repair_controls_exposed = false
raw_content_included = false
raw_paths_included = false
raw_private_identifiers_included = false
bounded_reason_ids[]
```

The durable-finalization and queue/worker sections are content-free. They report bounded status and counts only. They do not include raw durable-finalization locators, queue filenames, job IDs, dispatch IDs, claim owners, lease tokens, protected-source locators, timestamps, store paths, or exception text.

## UI surfaces

Home shows a read-only Lifecycle Visibility panel after the real Home conversation view. The panel is explicitly labeled as real runtime visibility and explains that local Home transcript state is browser-local and not durable source evidence.

Lab Observation shows the same UI-B1A panel after the existing Phase I-2/I-3 observation and Correct surface. This keeps the existing Correct-only mutation authority unchanged while adding lifecycle interpretation around the selected character and namespace.

Both UI wrappers guard stale character and generation results before committing fetched projections. Character switching must not cause an older result to update the active view.

## Supported lifecycle and operation vocabulary

Primary MEM current-state vocabulary:

```text
active
hidden
prepared
recovery_required
corrupt
unknown
```

Durable-finalization vocabulary:

```text
pending
complete
isolated
mixed
none
unknown
unavailable
not_connected
```

Queue/worker vocabulary:

```text
queued
processing
formed
held
blocked
failed
mixed
none
unknown
unavailable
not_connected
```

These statuses are display-only. They do not imply that the UI can run replay, run a worker, retry a job, repair state, cleanup retention, or override lower authorities.

## Fresh-conversation verification meaning

UI-B1A describes Fresh Conversation as a browser-local Home session reset only:

```text
New Conversation
  -> browser-local Home session reset is visible
  -> durable memory store is not reset
  -> active current memories remain available to later ordinary retrieval
  -> hidden/current-ineligible memories remain excluded
  -> Home transcript is not durable source evidence
```

No new persistence semantics are introduced. UI-B1A does not persist Home transcripts as durable source, does not delete durable memory, and does not rewrite historical used-memory receipts.

## Security and leakage boundary

The projection and UI must not expose:

```text
raw MEM page
raw protected source
raw queue record
raw job/dispatch/claim/locator
raw tombstone
raw exception text
store path
backend credential
apply token
lease token
claim owner
private timestamp
```

Content-bearing memory title or summary should use existing bounded projection surfaces where needed. UI-B1A itself keeps durable-finalization and queue/worker visibility content-free and uses only bounded current-state status for memory lifecycle.

The UI uses React text rendering only and does not use `dangerouslySetInnerHTML`.

## Explicit non-goals

UI-B1A does not implement:

```text
Forget apply / Correct apply expansion / Pin apply / Held apply / SOUL apply
queue run / scheduler run / worker run / replay run
recovery / repair / cleanup control
restore / purge / unhide
durable transcript persistence
browser-owned namespace/store/backend/route authority
TTS / audio / avatar / Live2D / ASR
public or remote management binding
```

The existing Phase I-3 Correct UI remains the only mutation surface present in Lab Observation. UI-B1A adds no new mutation.

## Handoff

- I-4E owns loopback-only Forget API/UI and must keep consuming I-4B/I-4C/I-4D authorities rather than using UI-B1A as apply authority.
- I-4F owns product-level Forget validation including fresh-conversation exclusion proof.
- I-5A owns Pin/Unpin contract and preflight work.
- I-7A/B owns Held Apply/Discard contract and preflight work.
- O1D2 owns scheduler ordering/fairness/retry-time/backoff/jitter/pacing policy; UI-B1A only displays bounded status if present.
- O1E owns stale recovery, cancellation, and shutdown orchestration.
