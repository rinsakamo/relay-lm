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
  - ../../../scripts/relaylm_phase55c1_tts_adapter_handoff_smoke.py
  - ../../../scripts/relaylm_phase55c3_tts_adapter_transport_smoke.py
  - ../../../scripts/relaylm_phase55c4_tts_adapter_transport_runtime_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX streaming and output-safety maintainers
  - realtime frontend and external voice-adapter maintainers
  - runtime trace, TTS, avatar, privacy, and output-safety reviewers
relaylm_authority_level: exact_contract
---
# Runtime TTS Transport Contract

## Authority summary

This contract owns the exact current RelayCTX TTS adapter handoff/transport preparation boundary and its stream-final runtime wiring.

The current path is:

```text
backend SSE bytes
  -> RelayCTX B2 suppression wrapper must be in apply mode
  -> C4 observes only the resulting safe-visible SSE bytes
  -> C0 deterministic segmentation hints
  -> C1 runtime-private handoff plan
  -> C3 runtime-private offset-only transport envelope
  -> C0/C1/C3 content-free PipelineNodeResults
  -> optional request PipelineContext + stream-final trace recording
```

The current path stops there.

It does **not**:

```text
send adapter transport
execute TTS
contact a provider endpoint
generate audio
play audio
control an avatar
perform lip-sync
persist visible response text
write RelayCTX/MEM/SOUL/SLP semantic state
```

A current C3 `ready` envelope therefore means only that runtime-private adapter transport metadata was emitted in memory for a later external adapter bridge.

## Current implementation anchors

The exact current handoff/transport/runtime wiring is implemented by:

```text
relaylm/relayctx_tts_adapter_handoff.py
relaylm/relayctx_tts_adapter_transport.py
relaylm/relayctx_tts_adapter_handoff_runtime.py
relaylm/adapter.py
```

It consumes segmentation output from:

```text
relaylm/relayctx_tts_segmentation.py
```

and depends on safe-visible streaming produced by the RelayCTX stream-unpack/suppression boundary.

The current architecture handoffs remain transitional sources:

```text
docs/architecture/phase55c1_tts_adapter_handoff_contract.md
docs/architecture/phase55c3_tts_adapter_transport_contract.md
```

This transaction does not retire those sources.

## Current C1 handoff status values

The exact current handoff status type is:

```text
disabled
dry_run_ready
ready
empty_input
blocked
invalid_input
```

C3 consumes this bounded status rather than inspecting raw visible text itself.

## C1 handoff item shape

`RelayCTXTTSAdapterHandoffItem` is a runtime-private content-free item carrying exactly:

```text
sequence_index
start_char
end_char
char_count
boundary_kind
recommended_flush
reason_ids
```

The item contains offsets/counts and bounded structural metadata only.

It does not contain:

- visible text;
- prompt text;
- audio bytes;
- endpoint information;
- credentials;
- avatar commands.

Its runtime dictionary preserves those fields and marks:

```text
content_free = true
```

## C1 handoff plan shape

`RelayCTXTTSAdapterHandoffPlan` carries exactly:

```text
status
handoff_items
enabled
dry_run_only
source_segmentation_status
source_candidate_count
source_emitted_count
handoff_candidate_count
emitted_handoff_count
transport_requested
tts_execution_requested
audio_generation_requested
avatar_control_requested
persistence_allowed
blocked_reasons
```

Current execution-request/persistence flags remain false.

The runtime-private `handoff_items` tuple may be consumed by C3 but is omitted from generic C1 logging.

## Current C1 plan semantics

The current handoff helper consumes an existing segmentation result. It does not re-read backend SSE and does not recompute visible/internal suppression.

Current handoff lifecycle is bounded to:

```text
segmentation unavailable/invalid/blocked
  -> no handoff item emission

segmentation empty
  -> empty_input

segmentation dry-run ready
  -> dry_run_ready
  -> candidate metadata may be counted
  -> emitted handoff item count remains zero

segmentation ready + handoff dry_run_only
  -> dry_run_ready
  -> candidate handoff metadata computed
  -> emitted handoff item count remains zero

segmentation ready + handoff apply
  -> ready
  -> current handoff items emitted in runtime-private memory
```

The handoff plan still requests no external transport or TTS execution.

## Current C3 transport status values

`RelayCTXTTSAdapterTransportStatus` is exactly:

```text
disabled
dry_run_ready
ready
empty_input
blocked
invalid_input
```

These states describe transport-envelope preparation only.

They do not describe provider delivery, synthesis, playback, or avatar state.

## C3 transport item shape

`RelayCTXTTSAdapterTransportItem` is immutable and carries exactly:

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

Its `content_free` property always returns true.

`to_runtime_dict()` emits the exact field set above plus:

```text
content_free = true
```

The item contains no visible text.

A future external adapter may dereference these offsets against its own runtime-private safe-visible buffer, but RelayLM Core does not dereference or deliver the content at this boundary.

## Transport-item derivation

C3 maps C1 handoff items in their existing tuple order.

For each item:

```text
transport_sequence_index = enumerate index starting at 0
handoff_sequence_index   = source item.sequence_index
start_char               = source item.start_char
end_char                 = source item.end_char
char_count               = source item.char_count
boundary_kind            = source item.boundary_kind
recommended_flush        = source item.recommended_flush
reason_ids               = tuple(source item.reason_ids)
```

C3 does not reorder items, combine segments, split them again, or inspect the underlying text.

## Transport envelope shape

`RelayCTXTTSAdapterTransportEnvelope` carries exactly:

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

Its `content_free` property always returns true.

Its `transport_emitted` property is exactly:

```text
emitted_transport_count > 0
```

## Current transport execution flags

Every current transport envelope keeps:

```text
transport_delivery_requested = false
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
```

The current code does not vary these values by `ready`, `dry_run_ready`, route, boundary kind, or segment count.

This is the hard current boundary between RelayLM Core preparation and a future/external execution adapter.

## Invalid handoff-plan input

`build_tts_adapter_transport_envelope(handoff_plan, ...)` first requires:

```text
isinstance(handoff_plan, RelayCTXTTSAdapterHandoffPlan)
```

A non-matching input returns:

```text
status = invalid_input
transport_items = ()
source_handoff_status = null
source_handoff_candidate_count = 0
source_handoff_emitted_count = 0
transport_candidate_count = 0
emitted_transport_count = 0
blocked_reasons = ("invalid_handoff_plan",)
```

The returned object retains the supplied `enabled` and `dry_run_only` values and keeps all execution/persistence flags false.

No exception text or rejected content is copied into the envelope.

## Transport disabled gate

For a valid C1 plan, when C3 `enabled` is false, the envelope is:

```text
status = disabled
enabled = false
candidate_items = ()
emitted_items = ()
blocked_reasons = ()
```

Source handoff status/count fields are still projected from the valid C1 plan by the shared envelope helper.

Disabled transport does not mutate the C1 plan.

## Source handoff invalid-input propagation

If C3 is enabled and:

```text
handoff_plan.status == invalid_input
```

C3 returns `invalid_input` with no transport candidates/emissions and blocked reasons equal to the de-duplicated sequence:

```text
handoff_plan.blocked_reasons
+ source_handoff_invalid_input
```

Order is preserved on first occurrence.

## Source handoff blocked propagation

If C3 is enabled and:

```text
handoff_plan.status == blocked
```

C3 returns `blocked` with no transport candidates/emissions and blocked reasons equal to the de-duplicated sequence:

```text
handoff_plan.blocked_reasons
+ source_handoff_blocked
```

C3 does not reinterpret why the upstream handoff blocked.

## Source handoff disabled while transport enabled

If C3 itself is enabled while the supplied handoff plan has:

```text
status = disabled
```

C3 returns:

```text
status = blocked
blocked_reasons = ("source_handoff_disabled",)
```

with no transport items.

This prevents a downstream transport stage from treating an upstream-disabled handoff as eligible data.

## Source handoff empty input

If the enabled C3 receives:

```text
handoff_plan.status = empty_input
```

C3 returns:

```text
status = empty_input
transport_candidate_count = 0
emitted_transport_count = 0
blocked_reasons = ()
```

No transport execution is requested.

## Source handoff dry-run-ready

If the enabled C3 receives:

```text
handoff_plan.status = dry_run_ready
```

it returns directly with:

```text
status = dry_run_ready
enabled = true
dry_run_only = true
source_handoff_status = dry_run_ready
source_handoff_candidate_count = handoff_plan.handoff_candidate_count
source_handoff_emitted_count = handoff_plan.emitted_handoff_count
transport_candidate_count = handoff_plan.handoff_candidate_count
emitted_transport_count = 0
transport_items = ()
blocked_reasons = ()
```

This branch forces the envelope's recorded `dry_run_only` value to true because the source handoff itself emitted no runtime-private items to convert.

C3 does not synthesize transport items from counts alone.

## Unknown source handoff status

If an enabled valid C1 object carries a status that is neither the known blocked/disabled/empty/dry-run/ready states nor `invalid_input`, current C3 returns:

```text
status = invalid_input
blocked_reasons = ("unknown_source_handoff_status",)
```

with no candidates or emissions.

The helper does not guess a closest state.

## Ready source handoff with no items

For:

```text
handoff_plan.status = ready
```

C3 first converts the runtime-private `handoff_items` to candidate transport items.

If the resulting candidate tuple is empty, it returns:

```text
status = empty_input
transport_candidate_count = 0
emitted_transport_count = 0
```

This prevents a nominal upstream `ready` status from creating an empty current `ready` transport envelope.

## Ready source + transport dry-run

For a ready handoff with at least one candidate item and:

```text
dry_run_only = true
```

C3 returns:

```text
status = dry_run_ready
transport_candidate_count = len(candidate_items)
emitted_transport_count = 0
transport_items = ()
```

The candidate transport items are transient local computation used only to derive the count on this branch.

## Ready source + transport apply

For a ready handoff with at least one candidate item and:

```text
dry_run_only = false
```

C3 returns:

```text
status = ready
transport_candidate_count = len(candidate_items)
emitted_transport_count = len(candidate_items)
transport_items = candidate_items
```

All external-delivery/execution/persistence flags remain false.

The exact current meaning of `ready` is therefore:

```text
runtime-private offset metadata emitted inside RelayLM Core
```

not:

```text
adapter contacted
speech synthesized
audio produced
```

## C3 diagnostics schema

`RelayCTXTTSAdapterTransportEnvelope.to_log_dict()` uses the exact schema value:

```text
relayctx_tts_adapter_transport.v0
```

Its exact diagnostics fields are:

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

The current fixed diagnostics booleans are:

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

`transport_items` is deliberately omitted from logging even though each item is offset-only/content-free.

## C3 PipelineNodeResult mapping

`build_relayctx_tts_adapter_transport_node_result(envelope)` uses:

```text
node_name = relayctx_tts_adapter_transport
decision = envelope.status
blocked_reasons = envelope.blocked_reasons
diagnostics = envelope.to_log_dict()
```

Current node-status mapping is:

```text
envelope invalid_input -> failed
envelope blocked       -> blocked
envelope ready         -> applied
all other statuses     -> diagnostic_only
```

Therefore:

```text
dry_run_ready -> diagnostic_only
empty_input   -> diagnostic_only
disabled      -> diagnostic_only
```

## C3 node artifact projection

The C3 node result includes one content-free artifact projection:

```text
artifact_name = relayctx_tts_adapter_transport
schema_version = relayctx_tts_adapter_transport.v0
present = true
content_free = true
runtime_private = true
visible_text_omitted = true
handoff_items_omitted = true
transport_items_omitted = true
transport_delivery_requested = false
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
external_io_performed = false
```

The artifact projection is diagnostics metadata, not a serialized transport item array.

## C4 runtime wrapper entry

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

The exact default runtime segmentation bounds in this wrapper are:

```text
max_segment_chars = 120
min_segment_chars = 8
```

Route configuration may supply other values under its separately validated config boundary.

## C4 hard safe-visible precondition

The runtime wrapper observes stream content only when both are true:

```text
enabled == true
b2_safe_visible_output_available == true
```

Otherwise it returns a pass-through async iterator that yields the upstream bytes unchanged and records no C0/C1/C3 results from this wrapper.

The safe-visible precondition is essential: C4 is not permitted to read the raw backend stream as a fallback when RelayCTX B2 suppression is not in apply mode.

## Adapter wiring of the safe-visible precondition

Current backend stream wiring first optionally applies:

```text
wrap_stream_with_relayctx_suppression(...)
```

when:

```text
route.relayctx_stream_unpack_dry_run_enabled
```

is true.

Current TTS handoff runtime wrapping occurs only when:

```text
route.relayctx_tts_adapter_handoff_runtime_enabled
```

is true.

The adapter passes:

```text
b2_safe_visible_output_available = (
    route.relayctx_stream_unpack_dry_run_enabled
    and not route.relayctx_stream_unpack_dry_run_only
)
```

Therefore current C4 observation is available only when the RelayCTX stream-unpack feature is enabled **and not dry-run-only**.

A TTS route flag alone does not authorize C4 to observe unsuppressed backend bytes.

## Stream bytes are forwarded before observation work

Inside `_observe_safe_visible_output_stream`, each upstream chunk is yielded before current C4 observation logic processes that chunk.

Conceptually:

```text
async for chunk in upstream:
    yield chunk
    observe chunk for later stream-final TTS planning
```

C4 therefore does not hold a successfully received chunk in order to complete TTS planning before forwarding it.

This contract does not claim that downstream network delivery has physically completed at the instant Python yields the chunk; it records the exact iterator ordering.

## Byte-type observation failure

If an observed stream item is not exact `bytes`, current C4:

- has already yielded the item;
- marks `invalid_observation = true`;
- does not append visible content from that item;
- continues observing subsequent items.

The wrapper does not replace or suppress that upstream item itself.

Type correctness of the backend byte iterator is separately owned by the adapter/stream boundary.

## SSE frame buffering

C4 maintains a runtime-local byte buffer and splits complete frames on the earliest occurrence of either:

```text
\r\n\r\n
\n\n
```

The chosen separator is whichever appears first in the current buffer.

A complete frame includes its separator in the byte slice passed to the content extractor.

Any remainder stays buffered until more bytes arrive or the stream finalizer runs.

## Final buffered frame handling

In the wrapper's `finally` block, if buffered bytes remain, C4 performs one final content-extraction attempt on that remainder even if it was not terminated by a normal SSE separator.

An invalid remainder marks the observation invalid. A returned string is appended to the visible chunk list.

This final observation does not alter bytes already yielded to the downstream consumer.

## SSE data extraction

C4 decodes a frame as UTF-8.

A decode failure returns an invalid observation marker rather than replacement text.

For decoded frames, `_extract_sse_data_payload`:

- normalizes CRLF to LF for line inspection;
- considers only lines beginning exactly with `data:`;
- removes the `data:` prefix;
- removes one leading ASCII space from the remaining value when present;
- joins multiple data lines with `\n`;
- returns `None` when no `data:` line exists.

A payload equal exactly to:

```text
[DONE]
```

is ignored for visible-content accumulation.

## JSON/content extraction

A non-`[DONE]` data payload is parsed with `json.loads`.

JSON decode failure marks the observation invalid.

For a decoded JSON value, C4 currently recognizes content only when the top level is a dictionary containing a `choices` list.

For each dictionary choice it may collect:

```text
choice["delta"]["content"]
```

when both nesting dictionaries exist and the content is a string, and/or:

```text
choice["text"]
```

when it is a string.

Non-dictionary choices and non-string candidate fields are ignored.

## Single-content-field requirement per frame

After scanning a frame:

```text
no recognized string content fields -> ignore frame
exactly one string content field     -> append that string
more than one recognized field       -> invalid observation
```

C4 does not concatenate two alternative choice contents from the same frame and guess which one was user-visible.

## Invalid observation closes downstream planning

At stream finalization, C4 builds the segmentation input as:

```text
if invalid_observation:
    (object(),)
else:
    tuple(visible_chunks)
```

The opaque invalid object intentionally drives the current C0 segmentation helper into its invalid-input path instead of allowing already observed partial strings to produce apparently valid TTS metadata.

C1 and C3 then derive their own blocked/invalid statuses from the upstream result under their exact current helpers.

C4 does not fall back to raw SSE content.

## Stream-final C0/C1/C3 construction order

At finalization, current C4 constructs exactly:

```text
hint_result = build_tts_safe_segmentation_hints(...)
hint_node = build_relayctx_tts_segmentation_node_result(hint_result)

handoff_plan = build_tts_adapter_handoff_plan(hint_result, ...)
handoff_node = build_relayctx_tts_adapter_handoff_node_result(handoff_plan)

transport_envelope = build_tts_adapter_transport_envelope(handoff_plan, ...)
transport_node = build_relayctx_tts_adapter_transport_node_result(transport_envelope)
```

The returned node-result tuple is exactly:

```text
(hint_node, handoff_node, transport_node)
```

C3 never runs before C1, and C1 never runs before the stream-final segmentation result exists.

## Runtime enablement passed to C0/C1/C3

Once the outer C4 wrapper has entered its observing branch, stream-final construction calls C0, C1, and C3 with:

```text
enabled = true
dry_run_only = outer wrapper dry_run_only
```

C4 does not independently disable only C3 after C1 succeeds under this current wiring.

The route's C4 runtime dry-run flag therefore controls all three current planning stages in this wrapper invocation.

## PipelineContext recording

If a `pipeline_context` object is supplied, C4 records the three node results in tuple order by calling:

```text
pipeline_context.record_node_result(node_result)
```

for each result.

The wrapper does not mutate the pipeline's backend-bound request payload, memory state, scene state, relationship state, or response bytes through this recording step.

The results are stream-final observability/planning results.

## Finalize callback

If `on_finalize` is supplied, current C4 calls it exactly once from the wrapper's `finally` block with the three-node tuple produced by `_record_tts_adapter_handoff_results`.

The callback is an internal runtime seam. This contract does not grant it external adapter-delivery authority.

The callback runs before the current trace-runtime stream-final recording call.

## Stream-final trace recording

After the optional finalization callback, C4 calls:

```text
trace_runtime_stream_final_pipeline_node_results(
    pipeline_context=pipeline_context,
    node_results=node_results,
)
```

The trace path consumes the content-free PipelineNodeResult projections.

This does not permit visible text, handoff arrays, transport arrays, endpoint details, or audio into generic trace by implication.

## Iterator teardown propagation

In the adapter, when any stream wrapper has replaced the base backend iterator, current code wraps the resulting iterator in `_ClosePropagatingAsyncIterator` with the base backend iterator as a close target.

C4 therefore participates in the existing wrapper stack rather than taking ownership of the shared HTTP client or backend-response lifetime.

Backend response/stream ownership remains with the adapter.

## Current route-controlled runtime inputs

The adapter supplies current C4 values from the selected route:

```text
relayctx_tts_adapter_handoff_runtime_enabled
relayctx_tts_adapter_handoff_runtime_dry_run_only
relayctx_tts_adapter_handoff_max_segment_chars
relayctx_tts_adapter_handoff_min_segment_chars
```

and derives the B2 safe-visible availability from the stream-unpack route settings as described above.

This contract owns how those values are consumed by C4, not the entire route configuration schema.

## C4 does not change stream bytes

The runtime wrapper is observational with respect to SSE output bytes.

It yields the same upstream objects in order and does not:

- rewrite SSE JSON;
- add TTS metadata to SSE frames;
- remove visible chunks;
- inject audio references;
- delay chunk emission until segmentation completes;
- send a second response stream.

C0/C1/C3 planning occurs as stream-final bookkeeping over observed safe-visible output.

## Partial-stream failure boundary

Because bytes are yielded before observation/finalization, a C4 planning failure cannot retract already yielded output.

The current safe behavior is therefore to record invalid/blocked/failed content-free node results rather than:

- replaying the response;
- substituting raw backend content;
- opening another semantic generation path;
- attempting speech from uncertain partial observation.

This preserves the broader irreversible-stream boundary.

## No external I/O in C3

`build_tts_adapter_transport_envelope` performs no network or filesystem I/O.

It does not:

- resolve an endpoint;
- open a socket;
- serialize an HTTP request;
- read credentials;
- call a TTS SDK;
- write an audio file;
- enqueue playback;
- control an avatar;
- persist visible text.

The current `external_io_performed=false` diagnostics field is therefore literal current behavior.

## No persistence authority

The C1/C3/C4 path does not write:

- RelayCTX working state;
- RelayMEM stores;
- RelaySOUL source/workspace state;
- RelayREL state;
- RelaySCN state;
- RelayEMO durable state;
- RelaySLP queues/candidates;
- Character Workspace source/build artifacts;
- audio files;
- visible response transcripts for later TTS recovery.

Pipeline node-result/trace recording remains content-free observability under the separately owned trace boundary.

## RelayEMO and presentation hints remain separate

The current C3 transport item carries only segmentation/handoff offset metadata and no affect/prosody/persona payload.

This contract therefore does not make TTS transport the owner of RelayEMO output, expression policy, voice identity, or semantic response style.

A future external adapter may consume separately governed presentation hints, but such a mapping is not current C3 authority.

## No provider/credential contract

There is no current RelayLM Core contract here for:

- provider name;
- endpoint URL;
- voice ID;
- API key/token;
- audio format;
- synthesis options;
- retry policy;
- provider timeout;
- billing/account metadata.

Adding those fields to C3 by documentation alone would falsely imply concrete adapter execution.

## No audio or avatar lifecycle

Current statuses do not include:

```text
synthesizing
audio_ready
playing
played
cancelled_audio
avatar_applied
lip_sync_complete
provider_failed
```

Those states are not hidden aliases of C3 `ready`.

They require a later external/runtime execution contract if implemented.

## Cancellation/interruption non-authority

C4 currently observes a stream and finalizes planning when the iterator exits or closes.

It does not define an authenticated barge-in/cancel protocol and does not independently stop backend generation, queued audio, or avatar motion.

A stream close still triggers its `finally` bookkeeping over whatever safe-visible content was validly observed before closure.

Concrete cancellation semantics belong to the owning runtime/adapter layer.

## Content-free public/logging boundary

The generic C1/C3/PipelineNodeResult/trace projections remain content-free.

They may contain:

- status;
- enabled/dry-run booleans;
- offsets/counts only in runtime-private item objects;
- boundary kind;
- recommended-flush boolean;
- bounded reason IDs;
- candidate/emitted counts;
- fixed omitted/execution flags.

They do not expose:

- the observed visible string;
- raw SSE frames;
- hidden RelayCTX content;
- C1 item arrays in generic logs;
- C3 item arrays in generic logs;
- endpoint/credential values;
- audio bytes;
- avatar commands.

## Failure behavior

The current boundary closes toward less TTS preparation and never toward broader execution:

```text
C4 disabled or no B2 safe-visible apply
  -> pure stream pass-through
  -> no C0/C1/C3 result from C4

invalid SSE observation
  -> segmentation invalid input
  -> downstream C1/C3 invalid/blocked planning
  -> no external transport/TTS request

C1 invalid
  -> C3 invalid_input

C1 blocked
  -> C3 blocked

C1 disabled while C3 enabled
  -> C3 blocked / source_handoff_disabled

C1 dry-run
  -> C3 dry_run_ready
  -> no emitted transport items

C1 ready + C3 dry-run
  -> transport candidates counted
  -> no emitted transport items

C1 ready + C3 apply
  -> offset-only transport items emitted in memory
  -> external I/O still false
  -> TTS/audio/avatar requests still false
```

There is no current fallback from invalid safe-visible observation to raw backend speech input.

## Current exact safety boundary

The most important cross-stage invariant is:

```text
B2 safe-visible output available
  -> C4 may observe

B2 only dry-run / disabled
  -> C4 must not observe raw backend output
```

The adapter enforces this by deriving `b2_safe_visible_output_available` only from B2 enabled-and-apply route state.

This is independent of whether the TTS handoff runtime flag itself is enabled.

## Stable invariants

- C3 consumes C1 handoff metadata; it never reparses visible response text.
- C3 transport items are offset/count based and content-free.
- C3 preserves handoff item order and creates zero-based transport sequence indices.
- C3 current execution/persistence flags are always false.
- C3 `ready` means only runtime-private metadata emission, not adapter delivery or TTS execution.
- Invalid/blocked/disabled/empty/dry-run upstream handoff states do not become current ready transport.
- Generic C3 logs omit transport item arrays.
- C3 PipelineNodeResult maps only `ready` to `applied`, `blocked` to `blocked`, and `invalid_input` to `failed`; other current statuses are diagnostic-only.
- C4 observes stream content only when enabled and B2 safe-visible output is actually available in apply mode.
- TTS runtime enablement alone never authorizes observation of an unsuppressed/raw backend stream.
- C4 yields upstream chunks before observation work and does not rewrite their bytes.
- C4 buffers only enough bytes to split/inspect SSE frames and builds C0/C1/C3 results at stream finalization.
- More than one recognized content field in one SSE frame is treated as invalid observation rather than concatenated.
- Any invalid observation makes final segmentation input invalid instead of accepting partial observed text.
- C0 -> C1 -> C3 node results are produced in exact order.
- PipelineContext and trace receive content-free node results, not visible text or transport arrays.
- The current path performs no external transport, TTS, audio, avatar, or persistence side effect.
- Current TTS transport status is not audio/provider execution state.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- RelayCTX B2 sentinel-detection/suppression internals;
- the full C0 segmentation algorithm/threshold policy beyond current runtime inputs;
- a provider adapter implementation;
- endpoint or credential management;
- network transport delivery;
- TTS synthesis or provider retries;
- audio codec, queue, playback, or device behavior;
- lip-sync or avatar execution;
- ASR or microphone input;
- presentation-hint/RelayEMO mapping;
- interruption/barge-in execution;
- durable visible-text/audio retention;
- runtime response semantic generation;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related architecture and transitional sources

- [Voice Streaming and TTS Architecture](../../architecture/voice/streaming-and-tts.md)
- [Phase 5.5 Stream Unpack Bounded Slice](../../architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Phase 5.5-C1 TTS Adapter Handoff Contract Handoff](../../architecture/phase55c1_tts_adapter_handoff_contract.md)
- [Phase 5.5-C3 TTS Adapter Transport Contract Handoff](../../architecture/phase55c3_tts_adapter_transport_contract.md)
- [Request / Response Pipeline](../../architecture/runtime/request-response-pipeline.md)
