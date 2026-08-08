---
relaylm_doc_type: contract
relaylm_authority: current_relayctx_tts_handoff_transport_and_stream_final_wiring_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relayctx
relaylm_update_trigger:
  - TTS adapter handoff or transport status/field schema changes
  - offset-only transport-item construction changes
  - stream-final TTS observation/wiring or safe-visible precondition changes
  - TTS transport node-result or diagnostics projection changes
  - concrete external adapter delivery becomes implemented
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - RelayCTX internal-sentinel suppression semantics owned by the stream-unpack boundary
  - exact TTS segmentation algorithm beyond the current handoff input contract
  - concrete TTS provider calls, endpoint credentials, audio generation, playback, lip-sync, or avatar control
  - runtime response semantics, RelayEMO policy, RelayMEM, RelaySOUL, RelaySLP, or persistence
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/voice/streaming-and-tts.md
  - ../../architecture/phase55c1_tts_adapter_handoff_contract.md
  - ../../architecture/phase55c3_tts_adapter_transport_contract.md
  - ../../architecture/phase5_5_stream_unpack_bounded_slice.md
  - ../../architecture/runtime/request-response-pipeline.md
relaylm_verified_by:
  - ../../../scripts/relaylm_relayctx_tts_adapter_handoff_smoke.py
  - ../../../scripts/relaylm_relayctx_tts_adapter_transport_smoke.py
  - ../../../scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX streaming and output-safety maintainers
  - realtime frontend and external voice-adapter maintainers
  - runtime trace, TTS, avatar, privacy, and output-safety reviewers
relaylm_authority_level: exact_contract
---
# Runtime TTS Transport Contract

## Authority summary

This contract owns the exact current RelayCTX TTS handoff/transport-preparation boundary and the stream-final runtime wiring that produces its content-free diagnostics.

The current path is:

```text
RelayCTX B2 safe-visible SSE output
  -> C0 segmentation hints
  -> C1 runtime-private handoff plan
  -> C3 runtime-private offset-only transport envelope
  -> C0/C1/C3 content-free PipelineNodeResults
  -> optional PipelineContext + stream-final trace recording
```

The path stops before adapter delivery. It does not contact a provider, execute TTS, generate or play audio, control an avatar, persist visible text, or mutate RelayCTX/MEM/SOUL/SLP semantic state.

A C3 `ready` result means only that runtime-private offset metadata exists in memory for a later external bridge. It is not a synthesis or playback success state.

## Current implementation anchors

The exact current boundary is implemented by:

```text
relaylm/relayctx_tts_adapter_handoff.py
relaylm/relayctx_tts_adapter_transport.py
relaylm/relayctx_tts_adapter_handoff_runtime.py
relaylm/adapter.py
```

Segmentation remains separately implemented in:

```text
relaylm/relayctx_tts_segmentation.py
```

The Phase 5.5 C1/C3 architecture documents remain transitional handoffs. This contract does not retire them.

## C1 status contract

`RelayCTXTTSAdapterHandoffStatus` currently accepts exactly:

```text
disabled
dry_run_ready
ready
empty_input
blocked
invalid_input
```

These statuses describe handoff planning only.

## C1 handoff item

`RelayCTXTTSAdapterHandoffItem` contains exactly:

```text
sequence_index
start_char
end_char
char_count
boundary_kind
recommended_flush
reason_ids
```

The item is runtime-private and content-free. `to_runtime_dict()` emits those fields plus `content_free=true`.

The item contains no visible text, audio bytes, provider endpoint, credential, or avatar command.

## C1 handoff plan

`RelayCTXTTSAdapterHandoffPlan` contains exactly:

```text
status
handoff_items
enabled
dry_run_only
source_hint_status
source_hint_candidate_count
source_hint_emitted_count
handoff_candidate_count
emitted_handoff_count
tts_execution_requested
audio_generation_requested
avatar_control_requested
persistence_allowed
blocked_reasons
```

The four execution/persistence booleans are false in every current constructor path.

`content_free` always returns true. `handoff_emitted` is exactly `emitted_handoff_count > 0`.

## C1 diagnostics

`RelayCTXTTSAdapterHandoffPlan.to_log_dict()` uses:

```text
schema_version = relayctx_tts_adapter_handoff.v0
```

and emits:

```text
schema_version
status
enabled
dry_run_only
source_hint_status
source_hint_candidate_count
source_hint_emitted_count
handoff_candidate_count
emitted_handoff_count
handoff_emitted
tts_execution_requested
audio_generation_requested
avatar_control_requested
persistence_allowed
blocked_reasons
content_free
visible_text_omitted
hint_array_omitted
handoff_items_omitted
runtime_private
```

The current fixed diagnostic booleans are:

```text
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
content_free = true
visible_text_omitted = true
hint_array_omitted = true
handoff_items_omitted = true
runtime_private = true
```

The runtime-private `handoff_items` tuple is not copied into generic logging.

## C1 source handling

`build_tts_adapter_handoff_plan(...)` requires a `RelayCTXTTSHintResult` instance. Any other object returns `invalid_input` with:

```text
blocked_reasons = ("invalid_hint_result",)
```

For a valid source result, current propagation is conservative:

```text
C1 disabled
  -> disabled

source invalid_input
  -> invalid_input
  -> de-duplicated source reasons + source_invalid_input

source blocked
  -> blocked
  -> de-duplicated source reasons + source_blocked

source disabled while C1 enabled
  -> blocked
  -> source_hints_disabled

source empty_input
  -> empty_input

source dry_run_ready
  -> dry_run_ready
  -> dry_run_only forced true
  -> candidate count copied from source candidate count
  -> emitted handoff count zero

unknown source status
  -> invalid_input
  -> unknown_source_hint_status
```

For source `ready`, C1 converts source hints to candidate handoff items in source tuple order. If no candidates exist, C1 returns `empty_input`. With `dry_run_only=true`, it returns `dry_run_ready` with candidate count only. With `dry_run_only=false`, it returns `ready` and emits the candidate handoff items into runtime-private memory.

## C1 item derivation

For each source hint, C1 currently derives:

```text
sequence_index = enumerate index from zero
start_char = hint.start_char
end_char = hint.end_char
char_count = hint.char_count
boundary_kind = hint.boundary_kind
recommended_flush = hint.recommended_flush
reason_ids = tuple(hint.reason_ids)
```

C1 does not embed the visible substring in the handoff item.

## C1 PipelineNodeResult

`build_relayctx_tts_adapter_handoff_node_result(...)` maps current plan state as:

```text
invalid_input -> failed
blocked       -> blocked
ready         -> applied
all others    -> diagnostic_only
```

The node name is `relayctx_tts_adapter_handoff`. The node diagnostics are the content-free C1 log projection and the artifact projection omits hint/handoff arrays and all execution side effects.

## C3 status contract

`RelayCTXTTSAdapterTransportStatus` currently accepts exactly:

```text
disabled
dry_run_ready
ready
empty_input
blocked
invalid_input
```

These states describe transport-envelope preparation only.

## C3 transport item

`RelayCTXTTSAdapterTransportItem` contains exactly:

```text
transport_sequence_index
handoff_sequence_index
start_char
end_char
char_count
boundary_kind
recommended_flush
reason_ids
```

The item is runtime-private and content-free. `to_runtime_dict()` emits those fields plus `content_free=true`.

C3 does not put visible text, endpoint URLs, credentials, audio bytes, or avatar commands in the item.

## C3 item derivation

C3 maps C1 handoff items in existing tuple order:

```text
transport_sequence_index = enumerate index from zero
handoff_sequence_index = item.sequence_index
start_char = item.start_char
end_char = item.end_char
char_count = item.char_count
boundary_kind = item.boundary_kind
recommended_flush = item.recommended_flush
reason_ids = tuple(item.reason_ids)
```

C3 does not reorder, merge, split, or dereference the text described by those offsets.

## C3 transport envelope

`RelayCTXTTSAdapterTransportEnvelope` contains exactly:

```text
status
transport_items
enabled
dry_run_only
source_handoff_status
source_handoff_candidate_count
source_handoff_emitted_count
transport_candidate_count
emitted_transport_count
transport_delivery_requested
tts_execution_requested
audio_generation_requested
avatar_control_requested
persistence_allowed
blocked_reasons
```

`content_free` always returns true. `transport_emitted` is exactly `emitted_transport_count > 0`.

Every current envelope keeps:

```text
transport_delivery_requested = false
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
```

Those values do not change when status is `ready`.

## C3 source handling

`build_tts_adapter_transport_envelope(...)` first requires a `RelayCTXTTSAdapterHandoffPlan` instance. Any other object returns `invalid_input` with no transport items and:

```text
blocked_reasons = ("invalid_handoff_plan",)
```

For a valid C1 plan, current propagation is:

```text
C3 disabled
  -> disabled

C1 invalid_input
  -> invalid_input
  -> de-duplicated C1 reasons + source_handoff_invalid_input

C1 blocked
  -> blocked
  -> de-duplicated C1 reasons + source_handoff_blocked

C1 disabled while C3 enabled
  -> blocked
  -> source_handoff_disabled

C1 empty_input
  -> empty_input

C1 dry_run_ready
  -> dry_run_ready
  -> dry_run_only forced true
  -> transport_candidate_count = C1 handoff_candidate_count
  -> emitted_transport_count = 0
  -> transport_items = ()

unknown C1 status
  -> invalid_input
  -> unknown_source_handoff_status
```

For C1 `ready`, C3 builds candidate transport items from `handoff_items`. No candidates yields `empty_input`. With C3 `dry_run_only=true`, it returns `dry_run_ready`, records the candidate count, and emits no items. With `dry_run_only=false`, it returns `ready` and emits those offset-only items into runtime-private memory.

## C3 diagnostics

`RelayCTXTTSAdapterTransportEnvelope.to_log_dict()` uses:

```text
schema_version = relayctx_tts_adapter_transport.v0
```

and emits:

```text
schema_version
status
enabled
dry_run_only
source_handoff_status
source_handoff_candidate_count
source_handoff_emitted_count
transport_candidate_count
emitted_transport_count
transport_emitted
transport_delivery_requested
tts_execution_requested
audio_generation_requested
avatar_control_requested
persistence_allowed
blocked_reasons
content_free
visible_text_omitted
handoff_items_omitted
transport_items_omitted
runtime_private
external_io_performed
```

The current fixed diagnostic booleans are:

```text
transport_delivery_requested = false
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
content_free = true
visible_text_omitted = true
handoff_items_omitted = true
transport_items_omitted = true
runtime_private = true
external_io_performed = false
```

Generic diagnostics never include the transport item tuple.

## C3 PipelineNodeResult

`build_relayctx_tts_adapter_transport_node_result(...)` maps:

```text
invalid_input -> failed
blocked       -> blocked
ready         -> applied
all others    -> diagnostic_only
```

The node name is `relayctx_tts_adapter_transport`. The artifact projection is content-free, runtime-private metadata and explicitly records that transport delivery, TTS execution, audio generation, avatar control, persistence, and external I/O did not occur.

## C4 runtime wrapper

Current stream-final wiring enters through:

```text
wrap_stream_with_tts_adapter_handoff(
    body_iter,
    *,
    enabled,
    dry_run_only=True,
    b2_safe_visible_output_available,
    max_segment_chars=120,
    min_segment_chars=8,
    pipeline_context=None,
    on_finalize=None,
)
```

The wrapper observes stream content only when both are true:

```text
enabled == true
b2_safe_visible_output_available == true
```

Otherwise it is a pass-through iterator and records no C0/C1/C3 results from this wrapper.

## Adapter safe-visible gate

`open_chat_completion_stream(...)` first applies the RelayCTX suppression wrapper when `route.relayctx_stream_unpack_dry_run_enabled` is true.

It applies the TTS handoff wrapper when `route.relayctx_tts_adapter_handoff_runtime_enabled` is true and passes:

```text
b2_safe_visible_output_available = (
    route.relayctx_stream_unpack_dry_run_enabled
    and not route.relayctx_stream_unpack_dry_run_only
)
```

Therefore the TTS runtime flag alone never authorizes observation of raw backend output. C4 observes only when the B2 stream-unpack path is in apply mode.

Current route-controlled C4 inputs are:

```text
relayctx_tts_adapter_handoff_runtime_enabled
relayctx_tts_adapter_handoff_runtime_dry_run_only
relayctx_tts_adapter_handoff_max_segment_chars
relayctx_tts_adapter_handoff_min_segment_chars
```

The route/config schema itself remains separately owned.

## Stream-byte ordering

Inside the observing wrapper, every upstream item is yielded before C4 processes it for later TTS planning:

```text
async for chunk in upstream:
    yield chunk
    observe chunk
```

C4 does not rewrite the yielded object or wait for stream-final segmentation before yielding it.

If an observed item is not `bytes`, it has already been yielded; C4 then marks the observation invalid and continues without extracting visible content from that item.

## SSE observation

C4 keeps a runtime-local byte buffer. Complete frames are split on the earliest occurrence of either:

```text
\r\n\r\n
\n\n
```

The separator remains in the frame passed to the extractor. Any remainder stays buffered until more bytes arrive or the wrapper finalizes.

At finalization, any remaining buffer is inspected once even if it lacks a normal separator.

## SSE data parsing

C4 decodes each frame as UTF-8. Decode failure is an invalid observation.

For decoded frames, only lines beginning exactly with `data:` are considered. C4 removes the prefix, removes one following ASCII space when present, joins multiple `data:` lines with `\n`, and ignores frames with no data payload.

The exact payload `[DONE]` is ignored.

Other payloads are parsed with `json.loads`. JSON decode failure is an invalid observation.

From a top-level dictionary with a `choices` list, C4 collects string values from:

```text
choice["delta"]["content"]
choice["text"]
```

when their required containers exist.

No recognized string field means the frame is ignored. Exactly one recognized string field is appended to the visible chunk list. More than one recognized string field makes the observation invalid rather than selecting or concatenating a value.

## Invalid observation fails planning closed

At finalization C4 uses:

```text
if invalid_observation:
    hint_input = (object(),)
else:
    hint_input = tuple(visible_chunks)
```

The opaque object deliberately drives current C0 into its invalid-input path. C4 does not recover by using partial visible strings or by re-reading raw backend output.

## Stream-final construction order

C4 constructs exactly:

```text
C0 hint result + node
C1 handoff plan + node
C3 transport envelope + node
```

and returns the node-result tuple in this order:

```text
(hint_node, handoff_node, transport_node)
```

Once the observing branch is entered, C0, C1, and C3 are all called with `enabled=true` and the same outer `dry_run_only` value.

## PipelineContext and trace

When a `pipeline_context` exists, C4 records the three node results in tuple order through `pipeline_context.record_node_result(...)`.

If `on_finalize` exists, it receives the three-node tuple after result construction and before stream-final trace recording.

C4 then calls `trace_runtime_stream_final_pipeline_node_results(...)` with the content-free node results.

Neither generic node-result recording nor trace is authority to persist the visible string or the C1/C3 private item arrays.

## Teardown ownership

When the adapter stack has wrapped the base backend iterator, `adapter.py` uses `_ClosePropagatingAsyncIterator` so close propagation still reaches the base response iterator.

C1/C3/C4 do not own the shared HTTP client or backend response lifecycle.

## External execution boundary

The current path performs no:

```text
provider lookup
endpoint resolution
credential read
network send
TTS SDK call
audio-file write
playback enqueue
avatar command
lip-sync command
visible-text persistence
```

No current TTS transport status means any of those actions occurred.

## Failure-direction invariant

The current boundary always fails toward less TTS preparation:

```text
C4 disabled or B2 safe-visible unavailable
  -> stream pass-through
  -> no TTS planning nodes from C4

invalid SSE observation
  -> invalid C0 input
  -> downstream C1/C3 cannot become execution-ready

C1 invalid/blocked/disabled
  -> C3 invalid/blocked

C1 dry-run
  -> C3 dry_run_ready
  -> no transport item emission

C1 ready + C3 dry-run
  -> candidates counted
  -> no transport item emission

C1 ready + C3 apply
  -> offset-only transport items emitted in memory
  -> external I/O still false
```

There is no fallback from an unsafe observation to raw backend speech input.

## Stable invariants

- C1 and C3 status vocabularies remain bounded to their six current values.
- C1 handoff items and C3 transport items contain offsets/counts and structural metadata, not visible text.
- C1 and C3 preserve source tuple order and derive zero-based sequence indices.
- All current transport/TTS/audio/avatar/persistence request flags remain false.
- C3 `ready` means in-memory transport metadata only.
- C3 diagnostics omit transport items even though those items are content-free.
- C4 observes only B2 safe-visible apply output.
- A TTS route flag never authorizes raw backend observation by itself.
- C4 yields upstream objects before observation and does not rewrite them.
- Any invalid observation fails final planning closed instead of accepting partial text.
- Stream-final node order is C0, then C1, then C3.
- PipelineContext and trace receive content-free node results, not visible text or private item arrays.
- C1/C3/C4 perform no external TTS, audio, avatar, or semantic-state persistence side effect.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- RelayCTX B2 suppression internals;
- the full C0 segmentation algorithm;
- a TTS provider or transport adapter;
- endpoint or credential management;
- network delivery;
- TTS synthesis or provider retry policy;
- audio codec, queue, playback, or device behavior;
- lip-sync or avatar execution;
- ASR or microphone input;
- RelayEMO/presentation-hint mapping;
- interruption or barge-in execution;
- durable visible-text or audio retention;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [Voice Streaming and TTS Architecture](../../architecture/voice/streaming-and-tts.md)
- [Phase 5.5 Stream Unpack Bounded Slice](../../architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Phase 5.5-C1 Handoff](../../architecture/phase55c1_tts_adapter_handoff_contract.md)
- [Phase 5.5-C3 Transport Handoff](../../architecture/phase55c3_tts_adapter_transport_contract.md)
- [Request / Response Pipeline](../../architecture/runtime/request-response-pipeline.md)
