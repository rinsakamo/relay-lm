---
relaylm_doc_type: contract
relaylm_authority: current_relayctx_tts_safe_segmentation_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relayctx
relaylm_update_trigger:
  - RelayCTX TTS segmentation status, boundary kind, hint/result schema, or character-offset semantics change
  - sentence/newline/length/stream-end boundary algorithm or segment-limit normalization changes
  - internal sentinel blocking or partial-prefix behavior changes
  - C2 runtime safe-output admission, stream-final observation, or C0 invocation behavior changes
  - segmentation node diagnostics or runtime-private hint handling changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - RelayCTX visible/internal stream suppression semantics
  - C1 adapter handoff item/plan schema or C3 transport-envelope semantics
  - concrete TTS provider execution, audio generation, playback, or avatar control
  - browser Home streaming parser or UI speech behavior
  - non-stream RelayCTX structured-update apply
  - CTX/MEM/SOUL/SLP persistence or mutation
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/voice/streaming-and-tts.md
  - ../../architecture/phase55c2_runtime_tts_adapter_handoff_wiring.md
  - ../../architecture/runtime/request-response-pipeline.md
relaylm_related_contracts:
  - stream-suppression.md
  - tts-transport.md
  - ../pipeline_node_result_contract.md
relaylm_verified_by:
  - ../../../scripts/relaylm_relayctx_tts_segmentation_smoke.py
  - ../../../scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX and TTS adapter-handoff maintainers
  - runtime streaming and safe-visible output maintainers
  - TTS transport/provider integration maintainers
  - privacy, security, streaming, and voice reviewers
relaylm_authority_level: exact_contract
---
# RelayCTX TTS Segmentation Contract

## Authority summary

This contract owns the exact current **TTS-safe segmentation hint boundary** implemented by:

```text
relaylm/relayctx_tts_segmentation.py
```

and its current runtime consumption through:

```text
relaylm/relayctx_tts_adapter_handoff_runtime.py
relaylm/adapter.py
```

The responsibility chain is:

```text
backend SSE
  -> RelayCTX stream suppression apply boundary
  -> already-safe visible SSE bytes
  -> C2 stream-final visible-text observation
  -> C0 exact character-offset segmentation
  -> content-free hint/result node
  -> C1 adapter-handoff planning
  -> separately owned C3 transport planning
```

The segmentation helper derives only content-free character ranges and boundary metadata. It does not execute TTS, produce audio, drive an avatar, persist visible text, or become a semantic rewrite authority.

## Relationship to stream suppression

`docs/contracts/runtime/stream-suppression.md` owns the exact current visible/internal SSE safety boundary.

C0 segmentation does **not** replace that boundary.

The current C2 runtime admits stream material into C0 only when the B2 safe-output precondition is met. Raw backend stream bytes and B2 dry-run observation are not valid TTS segmentation sources.

## Relationship to TTS transport

`docs/contracts/runtime/tts-transport.md` explicitly does not own the exact segmentation algorithm.

This contract owns C0 offsets and current C2 admission into C0. `tts-transport.md` owns later C1/C3 handoff/transport metadata.

The authorities are therefore complementary:

```text
stream-suppression.md
  -> safe-visible output

tts-segmentation.md
  -> bounded offset/boundary hints

tts-transport.md
  -> adapter handoff / transport metadata
```

## Historical C0 versus current runtime

The original Phase 5.5-C0 slice introduced `relayctx_tts_segmentation.py` as a pure helper-only boundary.

The current repository later wires that same helper through Phase 5.5-C2 after B2 safe-visible suppression.

Accordingly, this exact contract records both:

- the pure C0 helper semantics;
- the current C2 admission and invocation boundary.

It does not freeze the obsolete statement that C0 is never invoked from request runtime.

## Exact status vocabulary

`RelayCTXTTSHintStatus` accepts exactly:

```text
disabled
dry_run_ready
ready
empty_input
blocked
invalid_input
```

These statuses describe segmentation-hint readiness only.

They do not mean TTS execution succeeded, audio exists, or an avatar was controlled.

## Exact boundary-kind vocabulary

`RelayCTXTTSBoundaryKind` accepts exactly:

```text
sentence_punctuation
newline
length_limit
stream_end
```

No semantic topic, paragraph, token, phoneme, SSML, language-model, prosody, or provider-specific boundary kind is implied by the current contract.

## Internal sentinel source

The segmentation helper imports the same current RelayCTX internal sentinels used by the stream-suppression boundary:

```text
RELAYCTX_UPDATE_OPEN
RELAYCTX_UPDATE_CLOSE
```

The exact literals remain owned by RelayCTX Unpack.

C0 treats any complete internal sentinel or a qualifying terminal partial sentinel prefix as a blocker for hint emission.

## Current segmentation constants

The exact current constants are:

```text
minimum partial-sentinel prefix chars = 5
default max_segment_chars            = 120
default min_segment_chars            = 8
```

The hard sentence-boundary character set is exactly:

```text
。．.!！?？
```

This includes:

- Japanese full stop `。`;
- full-width dot `．`;
- ASCII period `.`;
- ASCII exclamation `!`;
- full-width exclamation `！`;
- ASCII question `?`;
- full-width question `？`.

The newline-boundary character set is exactly:

```text
carriage return
line feed
```

CRLF is treated specially as one two-character newline boundary.

## RelayCTXTTSHint shape

`RelayCTXTTSHint` is immutable and currently contains exactly:

```text
start_char
end_char
char_count
boundary_kind
recommended_flush
reason_ids
```

Its derived property is always:

```text
content_free = true
```

The hint stores no visible substring.

## Offset semantics

Every hint range is half-open:

```text
[start_char, end_char)
```

with:

```text
char_count = end_char - start_char
```

Offsets are Python string character offsets over the already-safe concatenated visible text supplied to C0.

They are not UTF-8 byte offsets, token indexes, grapheme-cluster indexes, audio timestamps, or provider offsets.

## Hint log projection

`RelayCTXTTSHint.to_log_dict()` returns exactly the current content-free fields:

```text
start_char
end_char
char_count
boundary_kind
recommended_flush
reason_ids
content_free = true
```

The visible text for the range is not included.

## RelayCTXTTSHintResult shape

`RelayCTXTTSHintResult` is immutable and contains exactly these current responsibility-level fields:

```text
status
hints
chunk_count
valid_chunk_count
invalid_chunk_count
observed_chars
max_segment_chars
min_segment_chars
enabled
dry_run_only
internal_marker_present
terminal_partial_sentinel
candidate_hint_count
emitted_hint_count
tts_execution_requested
avatar_control_requested
blocked_reasons
```

`hints` is runtime-private segmentation metadata.

The original visible text is intentionally not stored in the result.

## Result derived properties

The exact current derived values are:

```text
content_free = true
persistence_allowed = false
hints_emitted = emitted_hint_count > 0
```

Current code always constructs results with:

```text
tts_execution_requested = false
avatar_control_requested = false
```

## Result diagnostic schema

`RelayCTXTTSHintResult.to_log_dict()` uses exactly:

```text
schema_version = relayctx_tts_segmentation_hints.v0
```

The diagnostic projection includes:

```text
status
chunk_count
valid_chunk_count
invalid_chunk_count
observed_chars
max_segment_chars
min_segment_chars
enabled
dry_run_only
internal_marker_present
terminal_partial_sentinel
candidate_hint_count
emitted_hint_count
hints_emitted
tts_execution_requested = false
avatar_control_requested = false
blocked_reasons
content_free = true
persistence_allowed = false
```

The exact `hints` tuple is intentionally omitted from diagnostics.

## Main helper entry point

The exact current helper is:

```text
build_tts_safe_segmentation_hints(
    chunks,
    *,
    enabled,
    dry_run_only=true,
    max_segment_chars=120,
    min_segment_chars=8,
)
```

It accepts an iterable whose elements may be arbitrary objects, but only exact Python strings are accepted as visible segmentation input.

## Input materialization

The helper materializes the supplied iterable exactly once into a tuple.

The exact counters are then:

```text
chunk_count = number of supplied elements
valid_chunk_count = number of string elements
invalid_chunk_count = number of non-string elements
```

Every valid string contributes its `len(...)` to the concatenated visible text.

## Invalid chunk handling

A non-string input contributes:

```text
non_string_chunk
```

to bounded reasons.

When C0 is enabled and any invalid chunk exists, final status is:

```text
invalid_input
```

with:

```text
candidate_hints = empty
emitted hints = empty
```

The helper does not silently skip invalid material and still emit ready hints.

## Visible text construction

All valid string chunks are concatenated in supplied order:

```text
visible_text = "".join(valid_chunks)
```

Segmentation offsets therefore span chunk boundaries as one logical safe-visible character stream.

Chunk boundaries themselves are not segmentation boundaries unless the text at the boundary contains one of the exact current punctuation/newline/length conditions.

## Complete internal sentinel blocking

C0 checks whether either internal sentinel occurs anywhere in the concatenated visible text.

When present:

```text
internal_marker_present = true
reason includes internal_sentinel_detected
```

If enabled, final status is:

```text
blocked
```

with no candidate or emitted hints.

This defense is redundant with B2 runtime admission by design; C0 still fails closed when called directly on unsafe material.

## Terminal partial sentinel blocking

C0 checks whether the visible text ends with a qualifying prefix of either internal sentinel.

Only prefixes:

```text
length >= 5
AND
length < full sentinel length
```

qualify.

When detected:

```text
terminal_partial_sentinel = true
reason includes partial_internal_sentinel_prefix
```

If enabled, final status is `blocked` with no hints.

## Partial-prefix search order

For each internal sentinel, C0 examines the longest possible suffix prefix first, descending to the five-character minimum.

The returned internal prefix index is used only as a boolean block condition in C0; the prefix content is not projected.

## Segment-limit normalization

The helper normalizes `max_segment_chars` and `min_segment_chars` before any segmentation.

A `max_segment_chars` value is replaced by the current default 120 when it is:

```text
not an int
OR bool
OR < 1
```

A `min_segment_chars` value is replaced by the current default 8 under the same invalid conditions.

## Min greater than max

After individual normalization, when:

```text
min_segment_chars > max_segment_chars
```

C0 sets:

```text
min_segment_chars = max(1, min(8, max_segment_chars))
```

Therefore min never remains greater than max after normalization.

This normalization is deterministic and does not raise for malformed numeric controls.

## Disabled behavior

When:

```text
enabled = false
```

final status is exactly:

```text
disabled
```

with:

```text
candidate_hint_count = 0
emitted_hint_count = 0
hints = empty
```

The helper may still have counted/observed supplied chunks before status selection, but disabled mode never derives candidate offsets for downstream use.

## Status precedence

After input normalization and marker observation, current final status selection is exactly:

```text
if enabled is false
  -> disabled

else if invalid_chunk_count > 0
  -> invalid_input

else if complete internal marker OR terminal partial sentinel
  -> blocked

else if visible_text is empty
  -> empty_input

else
  -> derive candidate hints
     dry_run_only ? dry_run_ready : ready
```

This order matters: invalid input takes precedence over marker blocking, and disabled takes precedence over all enabled-path statuses.

## Empty-input behavior

When enabled input contains no invalid chunks/markers but concatenated visible text is empty:

```text
status = empty_input
candidate_hint_count = 0
emitted_hint_count = 0
hints = empty
```

No synthetic zero-length hint is generated.

## Candidate versus emitted hints

For non-empty safe visible input, C0 always derives candidate hints first.

Then:

```text
dry_run_only = true
  -> status = dry_run_ready
  -> candidate_hint_count = derived count
  -> emitted_hint_count = 0
  -> result.hints = empty

 dry_run_only = false
  -> status = ready
  -> candidate_hint_count = derived count
  -> emitted_hint_count = derived count
  -> result.hints = exact candidate tuple
```

Dry-run therefore exposes only counts/diagnostics, not runtime-private offset arrays.

## Segmentation scan order

The exact current segmentation algorithm scans the concatenated visible text left-to-right using:

```text
segment_start
index
```

For each position it computes a candidate boundary end.

A CRLF pair consumes two characters as one boundary end; all other positions use `index + 1`.

## CRLF boundary rule

When current character is carriage return and the next character is line feed:

```text
boundary_end = index + 2
segment_len = boundary_end - segment_start
```

If:

```text
segment_len >= min_segment_chars
```

C0 emits one hint:

```text
boundary_kind = newline
recommended_flush = true
reason_id = crlf_newline_boundary_detected
range = [segment_start, index + 2)
```

Then:

```text
segment_start = index + 2
index = index + 2
```

and the loop continues without processing the LF separately.

## Short CRLF behavior

If a CRLF is encountered before the current segment reaches `min_segment_chars`, the CRLF is not emitted as a segmentation boundary at that point.

The scan continues, so the CR/LF characters remain inside a later segment unless another qualifying boundary occurs.

## Single newline rule

For a non-consumed carriage return or line feed where:

```text
segment_len >= min_segment_chars
```

C0 emits:

```text
boundary_kind = newline
recommended_flush = true
reason_id = newline_boundary_detected
range = [segment_start, index + 1)
```

and advances:

```text
segment_start = index + 1
```

## Sentence punctuation rule

When current character belongs to the exact hard sentence-boundary set and:

```text
segment_len >= min_segment_chars
```

C0 emits:

```text
boundary_kind = sentence_punctuation
recommended_flush = true
reason_id = sentence_boundary_detected
range = [segment_start, index + 1)
```

and sets:

```text
segment_start = index + 1
```

The punctuation character itself is included in the preceding segment.

## Minimum-length precedence

Newline and sentence-punctuation boundaries are soft with respect to the current minimum.

They do not split a segment shorter than `min_segment_chars`.

The algorithm does not backtrack to a previous whitespace or punctuation when the minimum is later met.

## Length-limit rule

After CRLF/newline/sentence checks, when:

```text
segment_len >= max_segment_chars
```

C0 emits:

```text
boundary_kind = length_limit
recommended_flush = false
reason_id = max_segment_chars_reached
range = [segment_start, index + 1)
```

and sets:

```text
segment_start = index + 1
```

Length-limit boundaries therefore guarantee forward progress for long text without a qualifying punctuation/newline boundary.

## Boundary precedence at the same character

The exact current precedence at one scan position is:

```text
qualifying CRLF newline
  -> qualifying single newline
  -> qualifying hard sentence punctuation
  -> length limit
```

A qualifying punctuation/newline boundary therefore wins over a simultaneous length-limit boundary.

## Stream-end rule

After the scan completes, if:

```text
segment_start < len(text)
```

C0 emits exactly one final hint:

```text
boundary_kind = stream_end
recommended_flush = true
reason_id = stream_end_boundary
range = [segment_start, len(text))
```

The final stream-end hint is emitted even when its `char_count` is smaller than `min_segment_chars`.

## No zero-length segment

The stream-end condition and forward boundary updates ensure that C0 does not emit an empty final range.

Every emitted hint satisfies:

```text
end_char > start_char
char_count > 0
```

for normal non-empty input.

## Contiguous coverage

For a safe non-empty input that reaches segmentation, the emitted candidate ranges are contiguous in scan order:

```text
first.start_char = 0
next.start_char = previous.end_char
last.end_char = len(visible_text)
```

No character is intentionally omitted or duplicated by the offset generator.

The current smoke explicitly reconstructs the input from hint slices to prove exact preservation.

## No semantic rewrite

C0 never changes the underlying text.

The segmentation result is character-offset metadata over already-safe visible text retained separately by the caller.

It does not:

- trim whitespace;
- remove punctuation;
- normalize Unicode;
- insert punctuation;
- translate text;
- convert to SSML;
- alter wording;
- synthesize pronunciation text.

## Recommended-flush semantics

Current exact values are:

```text
sentence_punctuation -> true
newline              -> true
length_limit         -> false
stream_end           -> true
```

This is a bounded handoff hint only.

A downstream adapter remains responsible for deciding whether/how to execute speech within its own authority.

## Exact reason IDs per hint

Each current hint is created with exactly one reason ID:

```text
sentence_punctuation -> sentence_boundary_detected
newline CRLF          -> crlf_newline_boundary_detected
newline other         -> newline_boundary_detected
length_limit          -> max_segment_chars_reached
stream_end            -> stream_end_boundary
```

The current hint builder stores that one value as a one-element tuple.

## Segmentation node result

The exact node builder is:

```text
build_relayctx_tts_segmentation_node_result(result)
```

The node name is:

```text
relayctx_tts_segmentation_hints
```

The node decision is the exact C0 status.

## Node status mapping

The current mapping is:

```text
invalid_input -> failed
blocked       -> blocked
ready         -> applied
all others    -> diagnostic_only
```

In particular:

```text
dry_run_ready -> diagnostic_only
disabled      -> diagnostic_only
empty_input   -> diagnostic_only
```

## Node artifact

The current artifact is:

```text
artifact_name = relayctx_tts_segmentation_hints
schema_version = relayctx_tts_segmentation_hints.v0
present = true
content_free = true
hint_ranges_content_free = true
visible_text_omitted = true
tts_execution_requested = false
avatar_control_requested = false
persistence_allowed = false
```

The raw hint array is not copied into the content-free artifact.

## No visible text in diagnostics

Neither result diagnostics nor node artifacts include:

- the safe visible text;
- any text slice corresponding to an offset;
- sentence contents;
- punctuation context;
- backend SSE frame;
- internal RelayCTX candidate;
- audio content.

Offsets/counts/boundary kinds are content-free runtime metadata.

## Current C2 runtime wrapper

The current runtime consumer is:

```text
wrap_stream_with_tts_adapter_handoff(
    body_iter,
    *,
    enabled,
    dry_run_only=true,
    upstream_safe_output_applied=false,
    max_segment_chars=120,
    min_segment_chars=8,
    pipeline_context=None,
)
```

It is a pass-through observer over bytes that have already crossed B2 stream suppression.

The public SSE bytes are not rewritten by C2 for segmentation.

## C2 safe-output admission

C2 may invoke C0/C1 only when both are true:

```text
enabled = true
upstream_safe_output_applied = true
```

If `enabled=false`, C2 passes bytes through and returns without C0/C1 invocation.

If enabled but `upstream_safe_output_applied=false`, C2 passes bytes through and records a bounded blocked/non-admitted runtime result rather than treating raw/only-observed stream data as TTS source.

## Adapter config gates

Current C2 route/config fields are:

```text
relayctx_tts_adapter_handoff_runtime_enabled
relayctx_tts_adapter_handoff_runtime_dry_run_only
relayctx_tts_adapter_handoff_max_segment_chars
relayctx_tts_adapter_handoff_min_segment_chars
```

Current defaults are:

```text
enabled = false
dry_run_only = true
max_segment_chars = 120
min_segment_chars = 8
```

## B2 prerequisite configuration

Current adapter wiring permits C2 safe-output observation only when the B2 suppression boundary is configured for actual apply rather than dry-run-only observation:

```text
relayctx_stream_unpack_dry_run_enabled = true
relayctx_stream_unpack_dry_run_only = false
```

C2's own enablement does not elevate a disabled or dry-run-only B2 stream into safe-visible authority.

## Stream-final observation

C2 passes every backend-safe byte chunk downstream unchanged while request-locally collecting only recognized visible content strings from already-safe OpenAI-compatible SSE events.

C0 is not invoked once per SSE chunk.

At stream end, C2 calls C0 exactly once with the accumulated visible string chunks.

This means C0 offsets describe the complete stream-final safe-visible text observed by the current C2 wrapper.

## C2 SSE content source

The current C2 runtime recognizes only the same bounded OpenAI-compatible visible content fields needed by its observer.

It does not treat raw SSE frames, internal sentinel material, headers, usage metadata, response IDs, or arbitrary extension fields as segmentation text.

The exact C2 wrapper remains responsible for its own SSE extraction details; this contract owns only the admission of its already-extracted visible chunks into C0.

## C2 invalid safe-output observation

If the safe-output observer detects invalid/ambiguous material such that its current `invalid_chunk_count` is nonzero or its safety condition fails, C2 does not invoke C0/C1 as if valid segmentation input existed.

It fails closed with content-free diagnostics.

The runtime smoke covers invalid safe-output observation blocking handoff.

## C2 C0 invocation parameters

When admitted at stream end, C2 invokes C0 with:

```text
visible_chunks

enabled = true

dry_run_only = C2 dry_run_only

max_segment_chars = configured C2 max

min_segment_chars = configured C2 min
```

No provider/audio/avatar setting is passed into C0.

## C2 dry-run behavior

When C2 is admitted but:

```text
dry_run_only = true
```

C0 derives candidate offsets but emits no hint array in its result:

```text
status = dry_run_ready
candidate_hint_count > 0 when text segments
emitted_hint_count = 0
hints = empty
```

C1 therefore receives only the current dry-run-compatible input path and no actual TTS execution follows.

## C2 ready behavior

When admitted and non-dry-run:

```text
dry_run_only = false
```

C0 returns `ready` and makes its runtime-private hint tuple available to C1 adapter-handoff planning.

This still does **not** execute TTS.

The downstream `tts-transport.md` contract remains authoritative for C1/C3 plan/envelope behavior.

## C2 pass-through output invariant

The current runtime wrapper returns the same safe-visible SSE byte chunks it receives.

Segmentation is observation/planning metadata and does not change the public text stream.

TTS segmentation therefore cannot become an alternate text rewrite path.

## C2 diagnostics

Current C2 records the existing content-free C0 node result and the separately owned C1 handoff node result through `PipelineContext` when available.

Diagnostics may expose:

- statuses;
- counts;
- booleans;
- configured segment limits;
- reason IDs;
- content-free artifact metadata.

They do not include:

- visible text;
- raw SSE;
- hint arrays;
- handoff item arrays;
- provider payloads;
- audio/avatar commands.

## Runtime-private hint application

A downstream C1 planner that receives C0 `ready` hints must apply offsets only against the same already-safe visible text retained request-locally for that C2 observation.

A hint range is meaningless without that exact same text instance.

The current `RelayCTXTTSHintResult` intentionally does not persist or carry the text itself.

## No TTS execution

C0 and current C2 do not:

- contact a TTS provider;
- allocate an audio device;
- synthesize audio;
- store audio;
- enqueue playback;
- animate an avatar;
- perform lip sync;
- send Live2D commands.

The result flags explicitly remain false for TTS execution and avatar control.

## No persistence

C0 does not persist:

- visible text;
- hint ranges;
- adapter handoff data;
- audio;
- CTX working state;
- MEM/SOUL/REL/SCN state.

The current result projection explicitly reports:

```text
persistence_allowed = false
```

## No marker bypass

Direct callers cannot make sentinel-bearing or terminal-partial internal material become speech hints merely by invoking C0 outside C2.

C0 independently blocks those inputs even though current runtime admission is already downstream of B2.

This is a defense-in-depth invariant.

## No candidate text leakage

Because hints contain only character offsets, counts, boundary kinds, booleans, and reason IDs, a content-free diagnostic consumer cannot reconstruct the visible text from C0 alone.

A runtime consumer holding both the safe visible text and the runtime-private hint tuple may use the ranges locally, but that relationship does not authorize logging or persistence.

## Determinism

For identical:

```text
ordered visible string chunks
enabled
dry_run_only
max_segment_chars
min_segment_chars
```

C0 produces identical status, candidate ranges, emitted ranges, counters, boundary kinds, flush flags, and reason IDs.

There is no randomness, wall-clock dependency, backend call, tokenizer dependency, language-model call, or provider state in the segmentation algorithm.

## Language and tokenizer independence

The current algorithm is intentionally character-boundary based.

It does not:

- detect language;
- tokenize words/subwords;
- use phoneme dictionaries;
- use sentence-transformer or LLM inference;
- depend on model context windows;
- inspect speech rate or voice profile.

The only semantic-looking boundaries are the fixed punctuation/newline characters listed in this contract.

## Exact preservation evidence

The current C0 smoke applies every emitted `ready` hint to the original safe visible string and concatenates the slices.

The reconstruction must equal the original input exactly.

This proves segmentation is offset partitioning rather than text mutation.

## Representative current behavior

Current smoke evidence includes:

- one sentence followed by another sentence using sentence punctuation;
- CRLF newline boundary treated atomically;
- long text split by max length with `recommended_flush=false` on length-limit ranges;
- stream-end range for a short final remainder;
- dry-run candidate counts with no emitted hints;
- disabled state;
- empty input;
- invalid non-string input;
- complete and partial internal sentinel blocking;
- segment-limit normalization;
- content-free node-result diagnostics.

The exact examples are evidence, not a separate algorithm definition.

## Fail-closed invariants

The exact current segmentation invariants include:

1. disabled mode emits no candidate or runtime hint ranges;
2. any invalid non-string input blocks enabled hint generation;
3. complete internal sentinels block hint generation;
4. qualifying terminal partial sentinels block hint generation;
5. empty input emits no zero-length hint;
6. malformed segment limits normalize deterministically rather than widening unbounded behavior;
7. min never remains greater than max after normalization;
8. punctuation/newline boundaries require current minimum length;
9. length-limit boundaries guarantee bounded forward progress;
10. stream-end emits the remaining non-empty suffix even below min;
11. ready ranges form contiguous exact text coverage;
12. dry-run exposes counts but not the runtime-private hint tuple;
13. diagnostics never include visible text or hint arrays;
14. C2 runtime invokes C0 only after the actual B2 safe-output precondition;
15. C2 does not mutate public SSE bytes as a side effect of segmentation;
16. C0/C2 never execute TTS/audio/avatar behavior;
17. C0 does not persist visible text or segmentation ranges.

## Current focused evidence

The exact contract is guarded by:

```text
scripts/relaylm_relayctx_tts_segmentation_smoke.py
scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py
```

The first smoke is the direct C0 algorithm contract.

The second verifies the current C2 runtime admission/wiring over B2-safe visible output, including dry-run/ready handoff and fail-closed non-admission when the safe-output precondition is absent.

## Relationship to voice architecture

`docs/architecture/voice/streaming-and-tts.md` owns stable responsibility placement and intentionally does not freeze the exact segmentation algorithm.

This document supplies that exact current algorithm and runtime admission boundary.

## Source-retirement boundary

This transaction does not retire historical C0/C2 handoffs, implementation modules, focused smokes, or Phase 5.5 evidence.

Any source retirement requires a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
