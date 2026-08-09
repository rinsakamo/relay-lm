---
relaylm_doc_type: contract
relaylm_authority: current_relayctx_stream_visible_internal_suppression_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relayctx
relaylm_update_trigger:
  - RelayCTX stream sentinel observation or suppression status/schema changes
  - internal sentinel literals or partial-prefix handling changes
  - stream suppression runtime SSE parsing, buffering, fail-closed, or pass-through semantics change
  - stream suppression config gates or bounded buffer behavior changes
  - adapter stream-wrapper ordering or close-propagation behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - non-streaming RelayCTX Unpack structured-update schema or update-application semantics
  - exact TTS segmentation algorithm, handoff, transport, or concrete voice execution
  - backend semantic generation, route selection, RelayMEM, RelaySOUL, RelaySLP, or persistence
  - browser-side Home SSE parser semantics
  - runtime checkpoint/recovery semantics beyond stream close/fail-closed behavior
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/voice/streaming-and-tts.md
  - ../../architecture/phase5_5_stream_unpack_bounded_slice.md
  - ../../architecture/runtime/request-response-pipeline.md
relaylm_related_contracts:
  - tts-transport.md
  - ../pipeline_node_result_contract.md
  - ../runtime_compile_artifact_contract.md
relaylm_verified_by:
  - ../../../scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
  - ../../../scripts/relaylm_relayctx_stream_suppression_runtime_smoke.py
  - ../../../tests/test_stream_wrapper_close_propagation.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX streaming and output-safety maintainers
  - runtime adapter and SSE forwarding maintainers
  - TTS segmentation/handoff maintainers consuming safe visible output
  - privacy, security, streaming, and failure-closure reviewers
relaylm_authority_level: exact_contract
---
# RelayCTX Stream Suppression Contract

## Authority summary

This contract owns the exact current RelayCTX **stream visible/internal separation** boundary implemented by:

```text
relaylm/relayctx_stream_unpack.py
relaylm/relayctx_stream_suppression_runtime.py
relaylm/adapter.py
```

The current boundary has three related responsibilities:

```text
Phase 5.5-A observation
  -> content-free detection only

Phase 5.5-B suppression helper
  -> deterministic string-chunk preservation/suppression result

Phase 5.5-B2 runtime wrapper
  -> bounded OpenAI-compatible SSE byte-stream suppression
  -> safe visible prefix preservation
  -> internal candidate suppression
  -> content-free PipelineNodeResult recording
```

The implementation does not parse or persist the internal candidate as a new semantic authority. It stops disclosure at the stream boundary.

## Internal sentinel authority

The exact current internal delimiters are owned by non-stream RelayCTX Unpack and consumed by this contract:

```text
RELAYCTX_UPDATE_OPEN  = <relayctx_working_update>
RELAYCTX_UPDATE_CLOSE = </relayctx_working_update>
```

The stream boundary recognizes both delimiters as internal sentinels.

The longest current sentinel length defines the minimum safe look-behind needed for cross-chunk detection.

This contract does not redefine the JSON/update schema carried inside a complete non-stream structured update.

## Current constants

The exact current stream helper constants are:

```text
minimum partial-sentinel prefix chars = 5
default max buffer chars              = 256
SSE frame separators                  = CRLF CRLF or LF LF
```

The configured/argument `max_buffer_chars` is normalized to the default when it is:

- not an integer;
- a boolean;
- smaller than the longest internal sentinel.

The helper does not use an invalid small buffer as permission to weaken sentinel detection.

## Stream observation status vocabulary

`RelayCTXStreamUnpackStatus` accepts exactly:

```text
clean
sentinel_detected
partial_sentinel
invalid_input
```

These statuses are observation-only and do not authorize persistence or TTS emission.

## Stream suppression status vocabulary

`RelayCTXStreamSuppressionStatus` accepts exactly:

```text
disabled
dry_run_clean
dry_run_suppression_candidate
clean
suppressed
partial_blocked
invalid_input
```

These are stream-safety outcomes. They do not replace Core request status, backend status, or TTS handoff status.

## Observation result shape

`RelayCTXStreamUnpackObservation` is immutable and contains exactly these responsibility-level fields:

```text
status
chunk_count
valid_chunk_count
invalid_chunk_count
observed_chars
max_buffer_chars
retained_buffer_chars
marker_present
complete_sentinel_detected
split_sentinel_detected
terminal_partial_sentinel
update_candidate_present
blocked_reasons
```

Its derived properties are fixed:

```text
emitted_chunks_unchanged = true
content_free = true
persistence_allowed = false
tts_hints_emitted = false
```

The retained buffer content itself is not returned.

## Observation diagnostic schema

`RelayCTXStreamUnpackObservation.to_log_dict()` uses:

```text
schema_version = relayctx_stream_unpack_observation.v0
```

and emits only counters, booleans, bounded reason IDs, and the fixed non-authority booleans.

It does not emit:

- visible chunk text;
- internal sentinel text;
- internal update body;
- retained request-local buffer;
- backend response payload;
- filesystem or memory content.

## Suppression result shape

`RelayCTXStreamSuppressionResult` is immutable and contains exactly these responsibility-level fields:

```text
status
output_chunks
chunk_count
valid_chunk_count
invalid_chunk_count
observed_chars
emitted_chars
suppressed_chars
max_buffer_chars
enabled
dry_run_only
marker_present
complete_sentinel_detected
split_sentinel_detected
terminal_partial_sentinel
suppression_applied
suppression_would_apply
output_mutated
blocked_reasons
```

`output_chunks` is runtime-private output material. It is not emitted through diagnostics.

The fixed derived properties are:

```text
content_free = true
persistence_allowed = false
tts_hints_emitted = false
```

## Suppression diagnostic schema

`RelayCTXStreamSuppressionResult.to_log_dict()` uses:

```text
schema_version = relayctx_stream_suppression.v0
```

and intentionally omits `output_chunks`.

It exposes only bounded status/counters/booleans/reasons plus:

```text
content_free = true
persistence_allowed = false
tts_hints_emitted = false
```

## Observation helper

The exact observation entry point is:

```text
observe_stream_sentinel_buffer(
    chunks,
    *,
    max_buffer_chars=256,
)
```

It is pure observation and never returns modified output text.

Every supplied element increments `chunk_count`.

A string increments:

```text
valid_chunk_count
observed_chars by len(chunk)
```

A non-string increments:

```text
invalid_chunk_count
```

and adds:

```text
non_string_chunk
```

while observation continues over later elements.

## Cross-chunk detection

For each valid string chunk, observation compares:

```text
previous retained tail + current chunk
```

where the previous tail is bounded to at most:

```text
longest-sentinel-length - 1
```

characters.

A sentinel occurring within the current chunk sets:

```text
complete_sentinel_detected = true
```

A sentinel detectable only when the previous tail and current chunk are concatenated additionally sets:

```text
split_sentinel_detected = true
```

The bounded reasons are:

```text
internal_sentinel_detected
split_internal_sentinel_detected
```

as applicable.

## Terminal partial sentinel

After each valid observation chunk, the request-local retained buffer is truncated to `max_buffer_chars` and checked for a terminal prefix of either internal sentinel.

Only prefixes of at least five characters and shorter than the complete sentinel count as terminal partial markers.

Detection adds:

```text
partial_internal_sentinel_prefix
```

and sets `terminal_partial_sentinel=true`.

If the current retained tail no longer ends in a qualifying prefix, the boolean becomes false.

## Observation result precedence

The exact final observation status precedence is:

```text
if any invalid chunk
  -> invalid_input
else if complete sentinel detected
  -> sentinel_detected
else if terminal partial sentinel OR split sentinel detected
  -> partial_sentinel
else
  -> clean
```

The final derived flags are:

```text
marker_present
  = complete_sentinel_detected OR terminal_partial_sentinel

update_candidate_present
  = marker_present OR split_sentinel_detected
```

Observation never claims that a detected candidate is a valid/accepted RelayCTX update.

## String suppression helper

The exact helper is:

```text
apply_stream_internal_suppression_gate(
    chunks,
    *,
    enabled,
    dry_run_only=true,
    max_buffer_chars=256,
)
```

It materializes the input iterable once and keeps only string chunks as valid visible candidates.

Non-string chunks increment the invalid count and add `non_string_chunk`.

The helper concatenates valid strings only for bounded deterministic sentinel analysis.

## First complete sentinel rule

For the string helper, the first occurrence of either internal sentinel in concatenated visible text is the suppression boundary.

When apply is enabled and a complete sentinel exists:

```text
safe output = text before first sentinel
status = suppressed
suppression_applied = true
output_mutated = true
```

All text at and after the first sentinel is omitted from the safe output.

The helper does not attempt to parse or recover internal candidate content.

## Partial-only apply rule

When no complete sentinel exists but the concatenated text ends with a qualifying partial sentinel prefix:

```text
safe output = text before partial prefix
status = partial_blocked
suppression_applied = true
output_mutated = true
```

The terminal partial prefix itself is not exposed.

## Disabled helper rule

When `enabled=false`:

```text
status = disabled
output_chunks = all valid string chunks unchanged
suppression_applied = false
output_mutated = false
```

Detection booleans/reasons may still describe what exists in the material, but disabled mode does not rewrite valid strings.

## Dry-run helper rule

When enabled and `dry_run_only=true`, valid output strings remain unchanged.

The status is:

```text
dry_run_suppression_candidate
```

when a marker/partial/split condition would cause suppression, otherwise:

```text
dry_run_clean
```

The exact dry-run invariants are:

```text
suppression_applied = false
output_mutated = false
```

## Invalid helper input rule

When enabled and at least one non-string chunk is present before apply semantics are selected:

```text
status = invalid_input
output_chunks = empty
suppression_applied = false
output_mutated = true
```

The helper fails closed rather than emitting a partial subset as successful safe output.

## Clean helper rule

When enabled, non-dry-run, and no complete or terminal-partial sentinel requires suppression:

```text
status = clean
output_chunks = valid chunks unchanged
suppression_applied = false
output_mutated = false
```

## Suppressed character count

For the string helper and runtime result, the exact derived count is:

```text
suppressed_chars = max(0, observed_chars - emitted_chars)
```

This is a count only and cannot be used to reconstruct suppressed text.

## PipelineNodeResult: observation

The current observation node builder is:

```text
build_relayctx_stream_unpack_node_result(observation)
```

The node name is exactly:

```text
relayctx_stream_unpack
```

Node status maps as:

```text
invalid_input -> failed
update candidate present -> blocked
otherwise -> diagnostic_only
```

The node decision is the exact observation status.

The current artifact is:

```text
artifact_name = relayctx_stream_unpack_observation
schema_version = relayctx_stream_unpack_observation.v0
present = true
content_free = true
emitted_chunks_unchanged = true
persistence_allowed = false
```

## PipelineNodeResult: suppression

The current suppression node builder is:

```text
build_relayctx_stream_suppression_node_result(result)
```

The node name is exactly:

```text
relayctx_stream_suppression_gate
```

Node status maps as:

```text
result.status == invalid_input -> failed
suppression_applied == true -> applied
suppression_would_apply == true -> blocked
otherwise -> diagnostic_only
```

The node decision is the exact suppression status.

The artifact is runtime-private/content-free and marks:

```text
artifact_name = relayctx_stream_suppression
schema_version = relayctx_stream_suppression.v0
present = true
content_free = true
output_chunks_runtime_private = true
persistence_allowed = false
```

## Runtime SSE wrapper

The exact runtime entry point is:

```text
wrap_stream_with_relayctx_suppression(
    body_iter,
    *,
    enabled,
    dry_run_only=true,
    max_buffer_chars=256,
    pipeline_context=None,
)
```

The input iterator is expected to yield backend SSE bytes.

The returned object is an async iterator of response bytes.

## Runtime default-off behavior

When `enabled=false`, the runtime wrapper is byte-for-byte pass-through for backend chunks.

It does not inspect/rewrite SSE content.

It records a final content-free suppression result with:

```text
status = disabled
output_mutated = false
suppression_applied = false
```

The focused runtime smoke proves that the emitted byte sequence equals the input byte sequence.

## Runtime dry-run behavior

When `enabled=true` and `dry_run_only=true`, the runtime wrapper emits backend bytes byte-for-byte unchanged while observing complete/partial/split markers from parsed SSE content fields.

A suppression candidate records:

```text
status = dry_run_suppression_candidate
suppression_would_apply = true
output_mutated = false
```

Dry-run detection must never be presented as actual suppression.

## Runtime apply behavior

When enabled and non-dry-run, the wrapper parses bounded SSE frames and rewrites only the one supported visible content field needed to preserve safe visible text.

Once suppression begins, later content-bearing/internal frames are not emitted as visible content.

A visible prefix already established before the sentinel is preserved.

The wrapper never falls back to the original raw backend stream after detecting an internal boundary.

## SSE frame splitting

Runtime frame buffering recognizes the earliest occurrence of either:

```text
\r\n\r\n
\n\n
```

and returns complete byte frames plus an unconsumed remainder.

A separator may be split across backend byte chunks because splitting operates over the accumulated byte buffer.

This framing boundary is internal to the RelayCTX runtime wrapper and does not redefine the browser Home SSE parser.

## SSE UTF-8 handling

Each complete frame processed for observation/apply must decode as UTF-8.

Decode failure adds:

```text
stream_chunk_decode_failed
```

and contributes to invalid input.

In apply mode, invalid decoding emits no unsafe reconstructed frame.

## SSE data payload extraction

The current runtime extractor:

- normalizes CRLF to LF for line inspection;
- considers only lines beginning with `data:`;
- removes at most one leading space after the colon;
- joins multiple `data:` line values with `\n`;
- returns null when there are no `data:` lines.

It does not interpret SSE comments, ids, retry fields, or other event fields as visible content authority.

## `[DONE]` behavior

An exact data payload:

```text
[DONE]
```

is not JSON-decoded as a content event.

In apply mode the wrapper first flushes any safe pending visible text at the event boundary, then emits the `[DONE]` frame.

Suppressed internal material is not re-emitted before `[DONE]`.

## JSON handling

A non-sentinel SSE data payload must parse as JSON for RelayCTX content inspection.

Malformed JSON adds:

```text
sse_data_json_invalid
```

and fails the apply path closed for the affected stream rather than forwarding the malformed content as trusted safe visible material.

## Current visible content field recognition

The runtime wrapper inspects OpenAI-compatible choices and recognizes string content at:

```text
choices[i].delta.content
choices[i].text
```

Only string values are considered visible content fields.

Other fields are not interpreted as hidden RelayCTX content.

## Ambiguous multi-content frame

Apply mode requires at most one recognized string visible content field in a frame.

When one frame contains multiple recognized content fields, the wrapper records:

```text
multiple_stream_content_fields
```

and fails closed rather than choosing one branch and forwarding the other.

The focused runtime smoke verifies this condition yields no output from the ambiguous stream path and a failed node result.

## Non-content frame behavior

Before suppression begins, a parsed frame with no recognized content field is emitted unchanged after flushing any safe pending visible text.

After suppression begins, non-content frames other than the explicit `[DONE]` handling are not used to recover or reveal internal material.

The runtime stream-safety boundary does not infer semantic content from arbitrary extension fields.

## Pending visible buffer

Apply mode maintains only a request-local `pending_visible` string needed to retain the tail that could become part of a split sentinel.

When no sentinel/partial prefix is present and the pending buffer is longer than:

```text
longest sentinel length - 1
```

all earlier characters are safe to emit and only that final bounded tail is retained.

This prevents normal visible output from being held until stream completion while still preserving cross-frame sentinel detection.

## Split sentinel across SSE frames

A sentinel whose prefix appears at the end of one content event and suffix at the start of a later content event is detected using the retained tail.

The previously safe prefix is emitted; sentinel/candidate material is suppressed.

The focused runtime smoke verifies this exact case.

## Split sentinel across backend byte chunks

A sentinel may also be split merely because the same SSE frame is split across backend byte chunks.

The accumulated byte frame is reassembled before UTF-8/JSON/content processing, so the sentinel remains detectable.

The focused runtime smoke verifies this case.

## Terminal partial marker behavior

At an event or stream boundary, if the pending visible buffer ends in a qualifying sentinel prefix, the prefix is withheld.

The safe text before that prefix may be emitted.

The runtime records:

```text
terminal_partial_sentinel = true
suppression_started = true
partial_internal_sentinel_prefix
```

and final result status becomes `partial_blocked` when no complete sentinel was observed.

The partial marker is never emitted as successful visible output.

## Re-rendered content frame

When only a safe prefix of one parsed content event may be emitted, the runtime deep-copies that event JSON object and replaces only the exact recognized content path with the safe text.

The re-rendered SSE frame is encoded as compact UTF-8 JSON:

```text
data: <json>\n\n
```

Other JSON fields in that copied event remain structurally preserved.

The runtime does not create a second semantic completion.

## Runtime apply error handling

A non-byte item yielded by the backend iterator in apply mode records:

```text
non_bytes_stream_chunk
```

sets invalid input, and ends the safe output loop.

Backend iterator exceptions record:

```text
backend_stream_iterator_error
```

and end apply processing without replaying already emitted visible data.

A raw exception string is not included in the content-free node result.

## Runtime dry-run iterator error

Dry-run mode preserves byte pass-through behavior while observing.

If the backend iterator raises, the wrapper records `backend_stream_iterator_error` in final diagnostics and re-raises the backend iterator exception because dry-run is compatibility pass-through rather than active fail-closed rewriting.

This distinction is current runtime behavior and must not be silently normalized into apply semantics.

## No duplicate replay after apply-side error

Apply mode may already have emitted a visible prefix before a later backend error.

The wrapper must not replay the original raw chunk sequence or emit that visible prefix again as fallback.

The focused runtime smoke asserts a visible prefix occurs at most once after a synthetic backend iterator error.

## Runtime result derivation

The runtime state derives final result status exactly in this precedence:

```text
if invalid_chunk_count > 0
  -> invalid_input

else if dry_run_only
  -> dry_run_suppression_candidate when marker/split/partial would apply
     otherwise dry_run_clean

else if suppression_started AND terminal_partial_sentinel AND no complete sentinel
  -> partial_blocked

else if suppression_started
  -> suppressed

else
  -> clean
```

The apply-mode `suppression_applied`/`output_mutated` booleans are true for `suppressed` and `partial_blocked`, false for clean.

Invalid input records `output_mutated=true` because the safe wrapper did not preserve the original stream as a successful pass-through.

## PipelineContext recording

When a `PipelineContext`-like object is supplied, the runtime wrapper records exactly one final suppression node result through its existing node-result recording surface.

The recorded node result is content-free even when visible or internal text was processed request-locally.

No visible/internal text is copied into trace diagnostics by this contract.

## Stream adapter configuration

The current route/config projection exposes these exact stream-safety settings:

```text
relayctx_stream_unpack_dry_run_enabled
relayctx_stream_unpack_dry_run_only
relayctx_stream_unpack_max_buffer_chars
```

Current default-compatible values are:

```text
enabled = false
dry_run_only = true
max_buffer_chars = 256
```

The name retains historical `dry_run` wording even though current non-dry-run apply wiring exists.

These gates are an upper stream wrapper gate only; enabling them does not authorize persistence, TTS execution, or backend mutation.

## Adapter ordering

For OpenAI-compatible streaming backend responses, the adapter preserves this current responsibility order when optional wrappers are enabled:

```text
backend response byte iterator
  -> RelayCTX stream suppression wrapper
  -> TTS stream-final observation/handoff wrapper when enabled
  -> public response iterator
```

TTS therefore consumes the stream after the RelayCTX visible/internal safety boundary rather than reparsing the raw backend stream as an alternate disclosure path.

## TTS relationship

`docs/contracts/runtime/tts-transport.md` begins from B2 safe-visible SSE output.

It does not own the suppression semantics described here.

This contract does not own exact segmentation or TTS handoff/transport semantics.

The relationship is:

```text
stream-suppression.md
  -> establishes safe visible stream

future/current segmentation contract
  -> divides approved visible text into bounded speech units

tts-transport.md
  -> plans handoff/transport metadata
```

## Close propagation

Stream wrappers must not hide the close operation of the direct backend response iterator.

The adapter uses a close-propagating async iterator wrapper so that:

- abandoning the public wrapped stream before the first `__anext__` closes the backend target;
- terminal completion of an outer wrapper still closes the direct backend target;
- the HTTP client object itself remains separately owned by the caller.

This invariant is especially important when a later fail-closed branch abandons a just-opened stream before iteration begins.

## Unstarted-wrapper close invariant

Plain `aclose()` on an unstarted async generator does not necessarily execute that generator body's `finally` block.

The adapter therefore preserves a direct close target rather than relying only on nested generator finalization.

`tests/test_stream_wrapper_close_propagation.py` proves the backend stream closes when the wrapped iterator is closed before any body chunk is requested.

## Wrapper terminal-completion close invariant

The same regression evidence proves that an outer wrapper that terminates without yielding still closes its direct backend close target when `StopAsyncIteration` is observed.

This resource-lifecycle rule is part of the current exact streaming boundary and must survive future wrapper composition.

## No persistence authority

Neither observation nor suppression may persist:

- visible stream content;
- suppressed candidate content;
- sentinel bodies;
- CTX working updates;
- memory records;
- SOUL/REL/SCN state;
- TTS text.

Every current diagnostic result explicitly reports `persistence_allowed=false`.

## No TTS execution authority

Neither observation nor suppression emits TTS hints or executes TTS.

Every current diagnostic result reports:

```text
tts_hints_emitted = false
```

Segmentation/handoff/transport remain separate downstream responsibilities.

## No raw fallback after suppression

Once apply-mode suppression has begun, a later malformed event or backend error does not authorize fallback to the raw unsuppressed backend stream.

The safe direction is fail closed while preserving only already-established safe visible output.

This prevents a safety wrapper failure from becoming an internal-candidate disclosure path.

## No internal-candidate parsing in stream path

The stream suppressor detects delimiter boundaries; it does not accept, validate, apply, or persist the JSON inside the candidate.

Non-stream `RelayCTX Unpack` remains the separately owned contract for explicit trailing structured updates.

Stream safety therefore answers only:

```text
may this material remain visible?
```

not:

```text
is this a valid CTX update and should it be applied?
```

## Content-free privacy boundary

Public/node diagnostics from this contract must not include:

- visible response text;
- full or partial internal sentinel strings from processed content;
- internal candidate JSON/body;
- backend SSE payload;
- request prompt/history;
- route/backend credentials;
- memory or character content;
- raw exceptions.

Only bounded counts, statuses, booleans, reason IDs, and fixed schema/artifact metadata are emitted.

## Fail-closed invariants

The exact current stream-safety invariants include:

1. default-off runtime behavior is byte-for-byte pass-through;
2. dry-run behavior is byte-for-byte pass-through even when a suppression candidate is observed;
3. apply mode never emits a complete internal sentinel or candidate body after first detection;
4. a terminal partial sentinel prefix is withheld rather than exposed;
5. sentinels split across content events and backend byte chunks are detected;
6. ambiguous multiple content fields in one apply-mode frame fail closed;
7. invalid UTF-8 or JSON in apply mode does not fall back to raw unsafe output;
8. backend apply-side errors never duplicate/replay previously emitted visible output;
9. `[DONE]` may still be emitted after safe pending text while suppressed internal content remains omitted;
10. only bounded sentinel look-behind/pending visible state is retained request-locally;
11. output chunks are runtime-private and omitted from diagnostics;
12. diagnostics never acquire persistence or TTS authority;
13. TTS wiring is downstream of safe-visible suppression;
14. outer stream wrappers preserve direct backend close propagation even before first iteration;
15. this boundary does not parse or apply the internal structured-update body.

## Current focused evidence

The exact current boundary is guarded by:

```text
scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
scripts/relaylm_relayctx_stream_suppression_runtime_smoke.py
tests/test_stream_wrapper_close_propagation.py
```

The runtime smoke specifically covers:

- default-off byte pass-through;
- dry-run byte pass-through with detection;
- apply-mode visible-prefix preservation;
- split sentinel across SSE frames;
- split sentinel across byte chunks;
- terminal partial marker blocking;
- invalid UTF-8 fail-closed behavior;
- ambiguous multi-content frame fail closure;
- backend iterator error without duplicate replay;
- content-free node-result diagnostics.

## Relationship to voice architecture

`docs/architecture/voice/streaming-and-tts.md` owns the stable responsibility chain and intentionally does not own exact SSE/sentinel schemas.

This exact contract supplies the current stream visible/internal separation implementation beneath that architecture.

## Relationship to TTS transport contract

`docs/contracts/runtime/tts-transport.md` explicitly excludes RelayCTX internal-sentinel suppression semantics.

It consumes the safe-visible result produced by this boundary and owns later handoff/transport metadata only.

There is no duplicate authority between the two contracts.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/phase5_5_stream_unpack_bounded_slice.md
```

Nor does it retire Phase55A/B1/B2 evidence, implementation modules, smokes, adapter wiring, or tests. Any retirement requires a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
