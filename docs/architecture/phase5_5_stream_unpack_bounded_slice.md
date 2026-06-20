---
relaylm_doc_type: implementation_plan
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Stream Unpack slice status changes
  - streaming response boundary changes
  - TTS-safe segmentation contract changes
  - output-side internal candidate handling changes
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact final stream transport schema
  - TTS engine execution
  - Live2D or avatar adapter behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_responsibility_design.md
  - pipeline_implementation_plan.md
  - current_target_migration_guide.md
---
# Phase 5.5 Stream Unpack Bounded Slice

## Status

Phase 5.5 is the next product-critical streaming boundary. It is planned and should be implemented in bounded slices before additional RelaySOUL execution-gate design expansion.

This document turns Stream Unpack from a broad target into an implementation-ready sequence.

## Purpose

Current streaming primarily preserves backend SSE forwarding. Non-stream RelayCTX Unpack already separates visible output from bounded internal candidates, but safe streaming requires additional chunk-level behavior.

Phase 5.5 exists to support:

- safe visible chunk forwarding,
- buffering across chunk boundaries for internal sentinels or envelopes,
- incomplete internal-candidate blocking,
- cancellation and partial-stream failure diagnostics,
- TTS-safe segmentation hints without owning TTS execution.

## Non-goals

Phase 5.5 does not:

- execute TTS,
- control Live2D or avatar adapters,
- persist MEM, SOUL, or SLP state,
- perform RelaySOUL apply, rollback, or storage writes,
- implement response/control-envelope extraction for client-instruction cache writing,
- rewrite visible response meaning,
- change backend model behavior,
- require RelaySOUL execution gates.

## Default posture

All apply-like behavior must remain gated.

```text
stream_unpack_enabled = false
stream_unpack_dry_run_only = true
stream_tts_segmentation_hints_enabled = false
```

Default behavior must preserve ordinary backend SSE forwarding.

When Stream Unpack is enabled for a bounded slice:

- visible chunks are preserved when safely recoverable,
- internal candidate markers are never exposed after detection,
- incomplete or malformed internal candidates are blocked,
- partial-stream failure records content-free diagnostics,
- no duplicate replay is allowed after a partial visible stream,
- TTS segmentation emits hints only; it does not call a TTS engine.

## Slice sequence

### Phase 5.5-A: stream sentinel buffer dry-run

Goal: add a pure/dry-run helper that can observe streamed text fragments and detect internal sentinel risk across chunk boundaries without changing emitted chunks.

Implemented behavior should include:

- per-request stream buffer state,
- bounded lookbehind/lookahead window,
- detection of complete internal sentinels,
- detection of partial sentinel prefixes across chunks,
- content-free diagnostics only,
- no mutation to outgoing SSE events,
- no TTS hints.

Exit criteria:

- ordinary SSE stream is unchanged,
- internal marker split across chunks is detected in diagnostics,
- incomplete candidate at stream end is blocked as internal evidence,
- emitted diagnostics contain no raw streamed text.

### Phase 5.5-B: visible chunk preservation and internal suppression gate

Goal: safely suppress or block internal candidate material while preserving already-safe visible chunks.

Implemented behavior should include:

- explicit gate for stream unpack apply,
- safe visible chunk forwarding,
- internal envelope suppression after detection,
- malformed candidate blocking,
- partial-stream failure summary,
- duplicate replay prevention,
- content-free PipelineNodeResult projection.

Exit criteria:

- normal streaming remains compatible,
- visible text preceding a blocked internal candidate remains preserved when safe,
- internal markers are not exposed after detection,
- malformed internal candidates do not trigger MEM/SOUL/SLP updates,
- cancellation produces a bounded content-free artifact.

### Phase 5.5-C: TTS-safe segmentation hints

Goal: emit bounded segmentation hints for downstream TTS/adapters without owning audio generation.

Implemented behavior should include:

- punctuation and sentence-boundary hinting,
- conservative Japanese/Kana/CJK handling,
- bounded segment length hints,
- no TTS execution,
- no avatar control,
- no meaning-changing rewrite,
- no persistence side effect.

Exit criteria:

- TTS hints are optional and default-off,
- hints are derived from safe visible output only,
- hints contain no internal candidate text,
- fallback preserves raw visible text when segmentation is uncertain.

## Smoke matrix

Minimum smoke coverage should include:

| Case | Expected result |
|---|---|
| ordinary SSE chunks | unchanged forwarding in default mode |
| internal sentinel in one chunk | detected, content-free diagnostic emitted |
| internal sentinel split across chunks | detected by buffer state |
| visible text followed by internal candidate | safe visible text preserved, internal candidate blocked/suppressed |
| malformed internal candidate | candidate blocked, visible text preserved when safe |
| incomplete candidate at stream end | candidate blocked, no persistence update |
| cancellation after visible chunks | no duplicate replay, partial state recorded |
| backend stream failure before visible output | runtime failure recorded, no fabricated output |
| backend stream failure after visible output | emitted chunks preserved, recovery hint recorded |
| TTS hint disabled | no segmentation hint emitted |
| TTS hint enabled | hints derived only from safe visible text |

## Safety invariants

Phase 5.5 must preserve these invariants:

- streaming compatibility by default,
- visible text is not rewritten for meaning,
- internal markers and candidate envelopes are not user-visible after detection,
- runtime-private content is not persisted in generic diagnostics,
- no MEM/SOUL/SLP mutation is triggered by malformed or incomplete candidates,
- no TTS or avatar execution is owned by RelayLM,
- RelayRUN handles runtime failures, cancellation, and checkpoint summaries,
- RelayCTX Unpack owns visible/internal separation; RelayREF and Output-side RelaySCN remain observation/policy consumers.

## RelaySOUL design freeze

Until Phase 5.5-A and 5.5-B are complete, new RelaySOUL execution-gate design documents should not be added unless they directly unblock a current runtime safety issue.

Existing RelaySOUL gate documents remain valid historical/current governance references. The freeze is about avoiding additional design expansion while the streaming product-critical path is still planned.

## Next implementation handoff

The next implementation handoff should be:

```text
Phase 5.5-A stream sentinel buffer dry-run
```

The handoff should include:

- target helper/module name,
- default-off config fields,
- content-free diagnostic schema,
- direct smoke script,
- unchanged ordinary SSE compatibility check,
- explicit non-goals for TTS execution, RelaySOUL persistence, and response rewriting.
