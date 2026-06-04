# RelayRUN Runtime Checkpoint Design

Date basis: 2026-06-02 JST

## Purpose

RelayRUN is RelayLM's runtime orchestration layer. It tracks one request/turn as an explicit run so RelayLM can record node progress, failure boundaries, fallback decisions, and future resume points without turning RelayLM into a semantic decision layer.

This design is intentionally narrow for the first implementation. It should not change RelayMEM local tests, request payload mutation, streaming forwarding, backend behavior, or memory retrieval semantics.

## Positioning

RelayLM remains an OpenAI-compatible runtime proxy. RelayRUN sits inside RelayLM and coordinates the runtime path.

```text
OpenAI-compatible API / proxy transport
  -> RelayRUN orchestration
  -> RelaySCN / RelayEMO / RelayMEM / RelayCTX / RelaySOUL nodes
  -> backend adapter
```

RelayRUN is not RelayPRX. RelayPRX remains only a future extraction candidate if transport, backend routing, multi-backend behavior, streaming recovery, or non-OpenAI-compatible adapters become complex enough.

## Core boundary

RelayRUN owns:

- `run_id`, `turn_id`, and request/runtime correlation
- node execution order and `node_status` tracking
- runtime checkpoint artifacts
- failure, blocked, skipped, and waiting-user states
- resume mode metadata
- recovery transition artifacts
- diagnostics and trace linkage
- stream-state boundary metadata
- fallback summary aggregation
- artifact lineage identifiers
- idempotency and duplicate-prevention hooks in later phases

RelayRUN must not own:

- scene classification
- user affect estimation
- memory retrieval ranking or filtering
- memory write/update semantics
- RelaySOUL change decisions
- prompt content construction
- final character style or expression
- backend/KV optimization
- response rewriting after streaming has started

## Trace vs checkpoint

RelayLM must keep trace/diagnostics separate from runtime checkpoints.

```text
Trace = what happened, best-effort observability
Checkpoint = where execution can resume or safely stop
Artifact lineage = what evidence/output allowed the next step
Recovery scene = how RelayLM asks, stops, or transitions safely
```

Initial checkpoint output should be diagnostics-only and metadata-only. It should not capture full prompt text, full messages, raw user affect estimates as long-term facts, or backend API keys.

## Initial node sequence

The current `app.py` handler already behaves like a straight-line runtime. RelayRUN should first model that flow as nodes without changing behavior.

```text
request_parse
route_resolve
ctx_compile
token_policy
scope_resolution
input_relayemo
input_relayscn
relayref
relaymem_retrieval
relaymem_runtime_injection
token_budget_truncation
diagnostics_build
backend_forward
response_trace
```

Later, the node names can converge with the canonical stack:

```text
Input-side RelaySCN
Input-side RelayEMO
RelayMEM Retrieval
RelayCTX Repack
Main LLM
RelayCTX Unpack
Return-side RelayEMO
Output-side RelaySCN
```

## Node status schema

```yaml
run_node:
  schema_version: relayrun-node-0
  node_name: relaymem_retrieval
  node_status: pending | running | completed | failed | blocked | skipped | waiting_user
  started_at: null
  completed_at: null
  fallback_reason: null
  blocked_reasons: []
  input_artifact_id: null
  output_artifact_id: null
  diagnostics_only: true
```

The MVP skeleton may build these dictionaries without writing them to disk or wiring them into every node yet.

## Runtime checkpoint schema

```yaml
runtime_checkpoint:
  schema_version: relayrun-checkpoint-0
  run_id: run_...
  request_id: ...
  turn_id: null
  route_model: relaylm-companion
  backend_name: lmstudio
  character_id: mili
  stream_enabled: false
  node_name: relaymem_retrieval
  node_status: completed
  input_artifact_id: null
  output_artifact_id: relaymem_retrieval_artifact_...
  blocked_reasons: []
  fallback_reason: null
  resume_allowed: false
  resume_mode: none
  stream_state:
    stream_requested: false
    backend_stream_opened: false
    first_token_sent: false
    recovery_response_allowed: true
  created_at: '2026-06-02T00:00:00+09:00'
```


## Checkpoint persistence plan dry-run

The current request path exposes a diagnostics-only checkpoint persistence plan
inside `relayrun_artifact.checkpoint_persistence_plan`. The plan is a preview of
the future writer contract only; it does not persist checkpoint files, create
checkpoint directories, enable resume, retry failed nodes, or apply recovery
transitions. It also must not mutate the backend forwarding payload.

```yaml
checkpoint_persistence_plan:
  schema_version: relayrun.checkpoint_persistence_plan.v0
  diagnostics_only: true
  write_allowed: false
  checkpoint_persisted: false
  target_root: .relayrun/checkpoints
  target_path_preview: .relayrun/checkpoints/<run_id>/<turn_id>.json
  run_id: run_...
  turn_id: request_or_turn_id
  blocked_reasons:
    - checkpoint_persistence_not_implemented
    - checkpoint_write_disabled
  resume_allowed_after_persist: false
```

`target_path_preview` is intentionally a string preview rather than a filesystem
operation. Until RelayLM carries an explicit durable turn id through the full
request path, the preview may use the request id as the turn path segment; this
keeps the planned `<run_id>/<turn_id>.json` layout visible without introducing
new persistence semantics.

The blocked reasons are stable diagnostics for downstream smoke tests and UI
inspection:

- `checkpoint_persistence_not_implemented` means no checkpoint writer exists in
  this phase.
- `checkpoint_write_disabled` means writes remain disabled even if the preview
  can compute a target path.

Future writer preconditions should include all of the following before
`write_allowed` can become true: an explicit operator/config opt-in, a safe
checkpoint root resolved inside the workspace, atomic write behavior, metadata
redaction rules, schema migration/version checks, backend-payload isolation
checks, and tests proving RelayMEM ordering and token truncation ordering remain
unchanged.

Persisting a checkpoint is only a prerequisite for future resume/retry work. This
dry-run plan does not make resume available (`resume_allowed_after_persist:
false`), does not apply `recovery_transition_artifact`, and does not change
stream-boundary recovery behavior.


## Checkpoint writer preflight dry-run

RelayRUN also exposes a diagnostics-only writer preflight at
`relayrun_artifact.checkpoint_writer_preflight`. The preflight is a gate report
for a future checkpoint writer; it does not write checkpoint files, create the
target directory, enable resume/retry, or apply recovery transitions.

```yaml
checkpoint_writer_preflight:
  schema_version: relayrun.checkpoint_writer_preflight.v0
  diagnostics_only: true
  write_allowed: false
  preflight_passed: false
  checkpoint_write_attempted: false
  directory_creation_attempted: false
  target_root: .relayrun/checkpoints
  target_path_preview: .relayrun/checkpoints/<run_id>/<turn_id>.json
  path_safety:
    root_relative: true
    path_traversal_detected: false
    absolute_path_detected: false
  content_policy:
    content_free: true
    backend_payload_included: false
    response_text_included: false
    raw_user_message_included: false
  blocked_reasons:
    - checkpoint_writer_not_implemented
    - checkpoint_write_disabled
  future_writer_required_gates:
    - explicit_config_enabled
    - safe_target_root
    - content_free_payload
    - atomic_write
    - idempotent_run_turn_key
```

The preflight uses the same `target_root` and `target_path_preview` as
`checkpoint_persistence_plan` so diagnostics can compare the intended writer path
without touching the filesystem. The path safety block is metadata-only: it
records whether the preview is root-relative and whether traversal or absolute
path indicators were detected, but it does not resolve, create, or validate a
real directory.

Checkpoint preflight artifacts must remain content-free. They intentionally
exclude backend forwarding payloads, backend response text, and raw user message
content because checkpoints are intended to be resumability/control metadata, not
a second transcript store. Future writers should persist only redacted runtime
state and references to already-governed diagnostics artifacts after all required
gates pass.


## File-backed checkpoint writer default-off

RelayRUN now has a default-off file-backed checkpoint writer for a
content-free checkpoint envelope. The writer remains disabled unless all explicit
operator gates are set:

```yaml
relayrun_checkpoint_write_enabled: true
relayrun_checkpoint_dry_run_only: false
relayrun_checkpoint_root: .relayrun/checkpoints
```

With the default configuration (`relayrun_checkpoint_write_enabled: false` and
`relayrun_checkpoint_dry_run_only: true`), RelayRUN does not create directories,
does not write files, and reports `checkpoint_persisted: false` with
`checkpoint_write_attempted: false`. When writing is enabled but dry-run-only
remains true, the writer still does not touch the filesystem and reports
`checkpoint_dry_run_only` as a blocked reason.

When all gates pass, the writer persists only `relayrun.checkpoint_envelope.v0`,
a content-free control envelope containing safe runtime metadata such as run/turn
ids, route/model identifiers, node statuses, blocked reason summaries, the
checkpoint persistence plan summary, and the checkpoint writer preflight summary.
The envelope must not contain backend forwarding payloads, raw messages, raw user
message text, backend response text, full prompt text, snippet text, full RelayMEM
page bodies, API keys, or URLs containing secrets. The artifact reports
`content_free: true`, `checkpoint_write_attempted: true`, `checkpoint_persisted:
true`, `persisted_path`, and `persisted_bytes` only after a successful write.

Path safety is enforced before any directory creation. The writer blocks path
traversal, absolute paths, unsafe target roots, content-policy failures, and
existing checkpoint file collisions. Directory creation happens only after the
write gates and path/content checks pass. The write flow is temp-file then rename
and uses a no-overwrite policy for the final checkpoint path; an existing file is
reported as `checkpoint_file_exists` and is not replaced.

This writer is persistence-only. It does not implement resume, retry, recovery
transition apply, or stream recovery behavior. Rollback remains operationally
simple: keep `relayrun_checkpoint_write_enabled: false`, keep
`relayrun_checkpoint_dry_run_only: true`, or point `relayrun_checkpoint_root` at
a disposable workspace-local directory and remove that directory.


## Checkpoint index / listing diagnostics

RelayRUN exposes a diagnostics-only checkpoint index artifact at
`relayrun_artifact.checkpoint_index`. The index is a safe listing and validation
summary for checkpoint-root contents only. It does not select a checkpoint for
resume, retry failed nodes, apply a recovery transition, expose raw checkpoint
content to the backend, or change the response body.

Checkpoint index diagnostics are default-off:

```yaml
relayrun_checkpoint_index_enabled: false
relayrun_checkpoint_index_dry_run_only: true
relayrun_checkpoint_index_max_files: 100
```

Default requests still include the artifact for observability, but they do not
scan the filesystem:

```yaml
checkpoint_index:
  schema_version: relayrun.checkpoint_index.v0
  diagnostics_only: true
  index_enabled: false
  dry_run_only: true
  scan_attempted: false
  root_path: .relayrun/checkpoints
  root_exists: false
  scanned_files: 0
  indexed_checkpoints: []
  blocked_files: []
  truncated: false
  blocked_reasons:
    - checkpoint_index_disabled
    - checkpoint_index_dry_run_only
  content_policy:
    content_free_only: true
    raw_user_message_included: false
    backend_payload_included: false
    response_text_included: false
    snippet_text_included: false
```

RelayRUN scans only when `relayrun_checkpoint_index_enabled: true` and
`relayrun_checkpoint_index_dry_run_only: false`. The scan is capped by
`relayrun_checkpoint_index_max_files`, considers only `.json` files under the
checkpoint root, blocks path traversal, symlinks, and any file that resolves
outside the root, and marks `truncated: true` when the cap is hit.

Malformed JSON, wrong schema, `content_free: false`, and envelopes containing
forbidden raw-content keys are reported in `blocked_files`. A valid
`relayrun.checkpoint_envelope.v0` contributes only a metadata summary to
`indexed_checkpoints`: checkpoint path, run id, turn id, route model, backend
name, run status, persisted flag, node count, blocked-reason count, optional
`created_at`, and `content_free: true`. Raw messages, raw user content, backend
payloads, response text, prompt text, snippet text, and full page bodies must not
appear in indexed summaries.

This index is listing diagnostics only. It does not implement resume selection,
multi-run lookup semantics, retry execution, multi-run recovery apply, or
user-visible recovery output.


## Resume preflight dry-run

RelayRUN exposes a diagnostics-only `resume_preflight` artifact in
`relayrun_artifact`. It is a readiness check for future resume/retry work only;
it does not resume a run, retry a node, apply a recovery transition, or alter
backend forwarding behavior. Resume preflight is default-off with
`relayrun_resume_preflight_enabled: false` and remains dry-run-only with
`relayrun_resume_dry_run_only: true`.

```yaml
resume_preflight:
  schema_version: relayrun.resume_preflight.v0
  diagnostics_only: true
  resume_allowed: false
  resume_attempted: false
  resume_applied: false
  checkpoint_read_attempted: false
  checkpoint_read_ok: false
  checkpoint_schema_valid: false
  content_free: null
  source_checkpoint_path: null
  blocked_reasons:
    - resume_not_implemented
    - resume_disabled
    - resume_dry_run_only
  future_resume_required_gates:
    - explicit_config_enabled
    - valid_checkpoint_schema
    - content_free_checkpoint
    - safe_resume_mode
    - user_or_policy_confirmation
```

When a checkpoint path is provided to the helper, RelayRUN may read and validate
a candidate `relayrun.checkpoint_envelope.v0` file. Validation is limited to
path safety, JSON parsing, checkpoint schema, and content-free policy checks.
Malformed JSON, wrong schema, missing files, path traversal, absolute paths,
`content_free: false`, or forbidden raw content keys all keep
`resume_allowed: false` and add blocked reasons.

Future resume work must still add explicit config enablement, a valid
content-free checkpoint, safe resume-mode selection, user or policy confirmation,
and dedicated retry/recovery-transition apply gates before any runtime behavior
can change.


## Recovery transition artifact dry-run

RelayRUN emits a diagnostics-only `recovery_transition_artifact` inside
`relayrun_artifact`. The artifact proposes how a future orchestrator might move
from a blocked or failed node toward a safe next step, but it is never applied in
this phase. RelayRUN must not produce direct character output, must not mutate the
backend payload, and must not replace the response body with recovery text. Any
future user-visible recovery must pass through the full RelayLM output pipeline.

```yaml
recovery_transition_artifact:
  schema_version: relayrun.recovery_transition.v0
  diagnostics_only: true
  user_visible: false
  apply_allowed: false
  applied: false
  transition_created: false
  proposed_transition_type: none
  source_node: null
  next_node: null
  resume_mode: none
  required_user_action: null
  blocked_reasons:
    - recovery_transition_not_implemented
    - recovery_transition_disabled
    - recovery_transition_dry_run_only
  safety:
    passes_through_output_pipeline: true
    direct_user_output_allowed: false
    contains_user_content: false
    contains_backend_payload: false
    contains_response_text: false
```

For recovery scenes or context-blocked paths, RelayRUN may propose
`context_repair` or `ask_user_confirmation`. For backend failures, it may propose
`retry_safe_node` or `explain_blocked_state`. These are diagnostics only: they do
not set `resume_allowed`, do not retry backend calls, do not apply a recovery
transition, and do not enter `waiting_user` behavior yet.

Future apply gates must include explicit operator config, a validated
content-free checkpoint or current-context state, safe resume/retry mode, user or
policy confirmation when required, and output-pipeline rendering for any
user-visible text.

## Stream boundary rule

Streaming is the main recovery boundary.

```text
Before backend stream opens:
  recovery response, OpenAI-compatible error, or fallback may be selected.

After backend stream opens but before first token:
  recovery is limited and must preserve transport semantics.

After first token is sent:
  user-visible text must not be replaced or rewritten by RelayRUN.
```

RelayRUN may record a stream failure checkpoint after first token, but it should not synthesize character-facing text directly in normal character or VTuber modes.

## Recovery transition artifact

RelayRUN may create a recovery transition artifact, but character-facing recovery text must still pass through the full RelayLM output pipeline.

```yaml
recovery_transition_artifact:
  schema_version: relayrun-recovery-transition-0
  run_id: run_...
  transition_type: resume_from_checkpoint | blocked | fallback
  recovery_intent: ask_user_confirmation | explain_blocked_state | request_minimal_reentry
  blocked_reasons: []
  required_user_action:
    type: confirm | restate_topic | approve_artifact | choose_option | none
    prompt_intent: null
  user_visible_allowed: false
  diagnostics_only: true
```

For MVP, this remains diagnostics-only. Direct RUN responses are reserved for transport-level failures, streaming-before-start complete failures, diagnostics-only internal records, or explicitly non-character system modes.

## Fallback summary

Fallback should be normal product behavior, not an exceptional crash path.

```yaml
run_fallback:
  fallback_applied: false
  from_mode: null
  to_mode: null
  node_name: null
  reason: null
  user_visible: false
```

RelayRUN records which node caused fallback, but it does not decide memory semantics or SOUL updates.

## Artifact lineage

RelayRUN should link existing diagnostics artifacts by ID or metadata reference, not duplicate full payloads.

```yaml
artifact_lineage:
  input_payload_artifact_id: null
  compiled_request_artifact_id: null
  relayemo_artifact_id: null
  relayscn_artifact_id: null
  relayref_artifact_id: null
  relaymem_retrieval_artifact_id: null
  runtime_ctx_injection_artifact_id: null
  backend_response_artifact_id: null
```

The first skeleton can expose lineage keys as `null` until app-level wiring is added.

## MVP implementation order

1. Add this design document and README link.
2. Add a pure `relaylm/relayrun.py` diagnostics skeleton.
3. Add optional `relayrun_artifact` to `RequestDiagnostics` and trace metadata.
4. Keep payload, MEM retrieval, injection order, token truncation order, backend forwarding, streaming, and error payloads unchanged.
5. Later, wire `app.py` node updates in diagnostics-only mode.
6. Later, add metadata-only checkpoint JSONL behind an explicit disabled-by-default config flag.

## Runtime dry-run wiring

The next request-path step is diagnostics-only wiring inside `app.py`.

- Each runtime request emits a diagnostics-only `relayrun_artifact`.
- The first wired artifact is metadata-only:
  - no checkpoint persistence
  - no resume
  - no recovery transition apply
  - no payload mutation from RelayRUN itself
- The runtime artifact should currently expose:
  - `schema_version: relayrun.runtime_checkpoint.v0`
  - `diagnostics_only: true`
  - `applied: false`
  - `run_id`
  - `turn_id`
  - `route_model`
  - `node_statuses`
  - `stream_started`
  - `first_token_sent`
  - `resume_allowed: false`
  - `resume_mode: none`
  - `checkpoint_persisted: false`
  - `recovery_transition_created: false`
  - `blocked_reasons`

## Initial node status coverage

The first runtime dry-run wiring should summarize these request-path nodes:

- `request_received`
- `relayscn`
- `relayref`
- `relaymem_retrieval`
- `relaymem_runtime_ctx`
- `token_budget_truncation`
- `backend_forward`

These node statuses are diagnostics summaries, not executable orchestration state. They must not change existing runtime ordering or apply behavior.

## Interaction with existing runtime layers

- RelaySCN:
  - RelayRUN may summarize fail-closed scene-policy outcomes as blocked node states.
  - It must not change scene classification or persistence rules.
- RelayREF:
  - RelayRUN may summarize unresolved-reference or reflect-style paths as blocked node states.
  - It must not rewrite context or force resume behavior.
- RelayMEM retrieval:
  - RelayRUN may summarize retrieval dry-run fallback or blocked apply decisions.
  - It must not change retrieval ranking, candidate selection, or evidence extraction.
- RelayMEM runtime ctx / snippet injection:
  - RelayRUN may summarize whether runtime context was applied, blocked, or skipped.
  - It must not change metadata-only vs snippet-bearing ordering.
- Token budget truncation:
  - RelayRUN may summarize whether truncation was skipped, completed, or blocked.
  - It must not change truncation timing or preserved-message rules.

## Safety invariants for current work

- Do not mutate forwarded payloads from RelayRUN.
- Do not change RelayMEM local retrieval test inputs.
- Do not change snippet/runtime ctx injection priority.
- Do not change token-budget truncation timing.
- Do not change streaming forwarding behavior.
- Do not replace backend errors with recovery text yet.
- Do not enable checkpoint file writes by default.
