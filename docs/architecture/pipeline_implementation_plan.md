# RelayLM Pipeline Implementation Plan

## Purpose

This document fixes the agreed implementation order for moving RelayLM from the current `app.py`-centered runtime toward a staged pipeline.

It is a phase-order memo, not a full architecture specification. Detailed behavior should continue to live in dedicated module docs and MVP summaries.

## Current caveats

- Current `RelayRUN` is mostly a request-end artifact writer. It is not yet a true cross-cutting node-state reporter.
- Current `relayref.py` behaves as input-side unresolved-reference / quick-clarification logic. In target terminology, that behavior is closer to `RelayINT` than `RelayREF`.
- `RelayCTX Unpack` now has both a pure non-stream parser and a default-off non-stream runtime boundary. Streaming support is still deferred.
- `RelayCTX Repack` has been substantially separated, but managed-route client-message canonicalization and client-instruction hash/cache resolution remain late boundary-hardening work.
- `RelayREF` should start as a lightweight diagnostics-only observer. Accurate answer-quality evaluation may require another model call and is not an early implementation requirement.
- `PipelineContext` and `diagnostics_builder.py` are present as the first stabilization layer.
  - `PipelineContext` owns request-local forwarded-payload state and detached Unpack candidates.
  - `diagnostics_builder.py` owns grouped `RequestDiagnostics` mapping helpers.
  - Runtime node execution and backend-response orchestration are still mostly in `app.py` and adapter/runtime helpers.

## Target responsibility boundary

```text
INT = input-side gate
REF = output-side observer
CTX Repack = stabilize the request payload sent to the Main LLM
CTX Unpack = separate user-visible response text from internal/update candidates
RUN = request/runtime orchestration and checkpointing
SLP = out-of-band memory / SOUL compilation and update preparation
```

The short rule is:

```text
RelayINT = before action
RelayREF = after response
```

RelayINT may decide to continue, block, or short-circuit with clarification before the Main LLM is called.

RelayREF should initially record observations after the Main LLM response. It should not own normal-turn regeneration or user-visible replacement behavior by default.

## Phase-order rule

Phase numbers identify responsibility boundaries and implementation dependencies. They are not a strict waterfall that forbids small prerequisite fixes after a phase is mostly complete.

```text
Current project phase remains Phase 5.
Late Phase 3 hardening may be completed as a prerequisite to Phase 5-C.
This does not roll the project back to Phase 3.
```

## Implementation order

### Phase 1: `app.py` lightweight separation — mostly complete

- Stabilize `PipelineContext` as the shared request-local runtime object.
- Centralize `forwarded_payload` replacement through `PipelineContext`.
- Record replacement reasons whenever the forwarded payload changes.
- Keep short-circuit clarification safe and explicit.
- Keep trace / diagnostics / RelayRUN artifact behavior stable.
- Preserve existing behavior by default.

Current status:

- `PipelineContext` has been introduced.
- `forwarded_payload` mutation tracking is routed through `PipelineContext.replace_forwarded_payload(...)`.
- `diagnostics_builder.py` reduces inline `RequestDiagnostics` field mapping in `app.py`.
- Remaining work should be limited to small safety fixes, not deeper semantic behavior.

### Phase 2: documentation consolidation — in progress

- Document the current and target pipeline.
- Clarify `RelayINT` as the input-side gate.
- Clarify `RelayREF` as the output-side observer.
- Clarify the current `RelayRUN` limitation.
- Maintain failure-route and implementation-handoff notes.
- Keep profile-specific contracts outside the generic pipeline document.

Current status:

- Architecture docs cover pipeline responsibilities, AI VTuber output boundaries, client-history authority, and client-instruction authority.
- Remaining work is maintenance and handoff synchronization as implementation phases land.

### Phase 3: `RelayCTX Repack` boundary hardening — mostly complete, with late prerequisites

Completed main separation:

- `relaylm/relayctx_repack.py` owns the main backend-bound payload mutation phases.
- RelayMEM snippet/runtime CTX injection moved out of `app.py`.
- Token-budget truncation runtime application moved out of `app.py`.
- RelayCTX short-term runtime injection apply moved out of `app.py`.
- Payload mutation still records replacement reasons through `PipelineContext`.
- `app.py` still owns orchestration order, diagnostics assembly, backend forwarding, and response handling.
- PR #246 added the client-message authority contract and compatibility fixes for `system` / `developer` instruction extraction.

#### Late Phase 3 hardening prerequisite

The client-authority contracts add one remaining managed-route input boundary:

```text
client messages
  -> current-turn extraction
  -> current system/developer instruction extraction
  -> instruction normalization/hash
  -> instruction-cache lookup
  -> prior client history/raw instruction exclusion
  -> normalized RelaySCN state
  -> RelayCTX Repack
```

This work is a bounded prerequisite to Phase 5-C, not a new standalone phase.

Required behavior before Phase 5-C can be enabled:

- preserve `pass_through` client-owned behavior,
- add explicit managed-route policy/config gates,
- extract the latest valid user turn without losing current multimodal parts,
- extract both `system` and `developer` instruction evidence,
- normalize and hash instruction evidence deterministically,
- resolve cache hit/miss without using prior conversation history in the key,
- exclude raw client history and raw instruction from normal backend context,
- allow one escaped low-trust instruction-evidence block on cache miss only,
- use cached validated RelaySCN state on cache hit,
- fail closed rather than restoring the original client message array,
- record content-free diagnostics and payload-replacement reasons.

Already landed compatibility/safety work:

- `system` and `developer` roles are both extracted by the historical compatibility helper,
- string and text-part-array instruction content are preserved,
- unsupported non-text instruction parts are not stringified,
- low-trust instruction evidence is escaped before XML-like context rendering.

### Phase 4: `RelayINT` split / alias — complete

- Input-side reference repair is exposed through `relayint.py`.
- Historical `relayref.py` implementation and artifact names remain for compatibility.
- RelayINT Fast Path, quick-clarification preflight, and apply-plan artifacts are default-off / plan-only.
- User-visible quick clarification, backend bypass, and completed short-circuit RelayRUN wiring remain deferred to Phase 6.

### Phase 4.5: pipeline node-result scaffold — complete

- `relaylm/pipeline_node_result.py` defines the frozen shared result shape.
- `PipelineContext.node_results` provides ordered request-local collection.
- `relaylm/pipeline_node_adapter.py` builds content-free summaries.
- Runtime trace metadata emits `pipeline_node_results` best-effort.
- Initial nodes include `relayint_reference_repair`, `relayint_quick_clarification`, and `relayctx_repack`.
- Directly recorded downstream nodes such as `relayctx_unpack` are kept after synthesized input/Repack records.
- Node results remain diagnostics-only and do not yet control runtime routing.

Minimal shape:

```python
@dataclass(frozen=True)
class PipelineNodeResult:
    node_name: str
    status: Literal[
        "applied",
        "skipped",
        "blocked",
        "failed",
        "diagnostic_only",
    ]
    decision: str | None = None
    blocked_reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
```

### Phase 5-A: pure non-streaming `RelayCTX Unpack` contract — complete

PR #247 established the parser contract without runtime mutation.

Implemented:

- `relaylm/relayctx_unpack.py` as a pure parser,
- ordinary response text passes through unchanged when no marker exists,
- one explicit trailing `<relayctx_working_update>` JSON envelope is accepted,
- schema version is fixed to `relayctx_working_update.v0`,
- accepted update fields and nested values are bounded,
- malformed, repeated, reversed, embedded, oversized, or non-trailing markers fail closed,
- visible text is preserved when safely recoverable,
- invalid/ambiguous updates are blocked,
- no CTX, MEM, SOUL, or SLP persistence occurs,
- content-free `RelayCTXUnpackResult` diagnostics are available,
- `build_relayctx_unpack_node_result(...)` produces a Phase 4.5-compatible result,
- contract and marker-safety smoke coverage are present.

Accepted form:

```text
user-visible response
<relayctx_working_update>
{"schema_version":"relayctx_working_update.v0","ctx_working_update":{...}}
</relayctx_working_update>
```

### Phase 5-B: non-stream runtime wiring — complete

PR #249 wired the Phase 5-A parser into supported non-stream backend responses behind safe default-off gates.

Implemented configuration:

```text
relayctx_unpack_enabled
relayctx_unpack_apply_enabled
relayctx_unpack_dry_run_only
relayctx_unpack_max_update_chars
```

Implemented runtime behavior:

- Unpack runs after a successful JSON backend response is decoded and before Return-side RelayEMO handling.
- Disabled, dry-run-only, unsupported, and non-success paths preserve the backend response body.
- Apply mode replaces only the single supported assistant message `content` field.
- Response IDs, model metadata, usage, finish reasons, and unrelated provider fields remain intact.
- Malformed internal updates may expose only the safely recovered visible prefix while blocking the candidate.
- Accepted `ctx_working_update` is stored only as a detached request-local `PipelineContext` candidate.
- `relayctx_unpack` is recorded directly at the execution boundary.
- Synthesized RelayINT/Repack trace records remain ordered before directly recorded Unpack results.
- No CTX persistence, RelayMEM write, RelaySOUL mutation, RelaySLP write, RelayRUN routing change, or streaming mutation was introduced.

Supported MVP response boundary:

```text
successful non-stream JSON response
  + exactly one choice
  + assistant role
  + string content
```

Unsupported response shapes are skipped without guessing or mutation.

Phase 5-B completion does not activate client-instruction cache behavior. It stabilizes the generic output separation boundary needed by Phase 5-C.

### Phase 5-C: client-instruction first-pass and cache integration — next

Connect the client-instruction authority contract only after the generic Phase 5-B boundary is stable.

This phase combines the late Phase 3 input prerequisite with a typed output-artifact path:

```text
unknown instruction hash
  -> one escaped low-trust instruction-evidence block
  -> Main LLM normal response + typed instruction-parse artifact
  -> RelayCTX visible/internal separation boundary
  -> strict schema and policy validation
  -> normalized RelaySCN cache entry

known instruction hash
  -> raw instruction excluded
  -> cached validated RelaySCN state injected
  -> no repeated instruction parsing
```

Required constraints:

- do not overload `relayctx_working_update.v0` with unrelated fields,
- use a separately versioned artifact such as `client_instruction_parse.v1`,
- add either a bounded control-artifact registry or a separate parser adapter sharing the same visible/internal separation boundary,
- accept only allowlisted scene role/context/constraint fields,
- block runtime-policy and tool-authority override attempts,
- keep durable persona fragments as candidates only,
- write cache only after schema and policy validation,
- keep visible-response delivery separate from cache-write success,
- bound retries and never reparse forever,
- keep diagnostics content-free,
- never restore raw client history/system/developer messages as fallback.

Phase 5-C does not include RelaySOUL mutation. Durable candidate review and approval remain later work.

### Phase 5.5: `RelayCTX Stream Unpack` and output segmentation

Start after the non-stream Phase 5-B boundary is stable and the typed-artifact rules needed by Phase 5-C are fixed.

- Add streaming token/chunk parsing without changing non-stream semantics.
- Forward user-visible chunks as early as possible.
- Hold a trailing sentinel buffer so partial internal markers cannot leak.
- Keep marker suppression fail closed.
- Collect terminal structured candidates internally.
- Add `RelayCTX Output Segmenter` for TTS-safe chunking.
- Classify output chunks before they enter a TTS queue.
- Apply AI VTuber TTS-safe rules for code, URLs, JSON/YAML, tables, commands, paths, quotes, and parenthetical notes.
- Keep Return-side RelayEMO lightweight and non-meaning-changing during streaming.

### Phase 6: failure-route table / node-result handling

- Promote the Phase 4.5 node-result scaffold into runtime behavior where appropriate.
- Connect blocked/failure reasons to continue, skip, short-circuit, fallback, blocked, and failed routes.
- Allow RelayRUN to consume node results at request end first.
- Reintroduce RelayINT quick-clarification actual apply through node results and response adapters.
- Keep compatibility with future per-node RelayRUN checkpoint reporting.
- Include stream/output-adapter failure routes.

### Phase 7: lightweight `RelayREF` observer

- Add diagnostics-only response checks.
- Do not regenerate or replace normal visible output by default.
- Detect empty response, internal-marker leakage, obvious diagnostic leakage, and likely scene/policy mismatch warnings.
- Emit observations for Output-side RelaySCN and future RelayRUN diagnostics.

### Phase 8: Output-side `RelaySCN`

- Evaluate next-turn scene transitions.
- Emit recovery hints and persistence-block reasons.
- Keep immediate output blocking limited to safety, leakage, or recovery-critical cases.
- Treat normal transitions as next-turn state rather than current-response rewriting.

### Phase 9: `RelayRUN` cross-cutting checkpoint layer

- Move from request-end artifacts toward per-node started/completed/blocked/failed reporting.
- Persist checkpoints with resume metadata.
- Keep RelayRUN semantic-neutral.
- Route visible recovery text through the normal output pipeline unless the failure is transport-level or explicitly non-character system mode.

### Phase 10: `RelaySLP` separation

- Keep memory and SOUL compilation outside the normal response path.
- Route candidates through persistence gates.
- Separate retrieval reads from SLP-time writes.
- Keep raw evidence, compiled pages, lineage, and approval state distinct.
- Do not let normal response generation directly mutate long-term memory or SOUL.

## Failure-route principles

### INT clarification

```text
RelayINT
  -> SHORT_CIRCUIT_CLARIFICATION
  -> RelayRUN records artifact/checkpoint summary
  -> quick clarification template response
  -> minimal output-side processing
  -> user output
```

The Main LLM should be bypassed unless a later configuration explicitly chooses model-generated clarification.

### MEM retrieval blocked or empty

```text
RelayMEM retrieval empty/blocked
  -> CTX Repack without retrieved memory block
  -> diagnostics records blocked reasons
  -> Main LLM continues
```

Only memory-dependent requests should surface a visible memory-unavailable or clarification response.

### CTX Repack token pressure

Degrade in this order:

1. remove diagnostics/trace-only context,
2. reduce retrieved memory,
3. reduce short-term CTX blocks,
4. shorten selected conversation context,
5. use a safe fallback if no valid payload can be produced.

### CTX Unpack failure

```text
return user-visible response text when available
block ctx_working_update / client-instruction / MEM / SOUL / SLP candidates
record content-free unpack diagnostics
never expose internal markers
```

### Stream/output-adapter failure

```text
partial safe visible chunks emitted
  -> preserve emitted chunks
  -> block incomplete internal candidates
  -> record stream/chunk/adapter diagnostics
  -> allow next-turn recovery preparation
```

TTS failure should normally fall back to caption/text output and diagnostics.

### REF warning

Early RelayREF findings remain diagnostics-only unless they detect leakage, empty output, or a safety-critical mismatch.

## Near-term sequencing rule

Do not make RelayREF smart before input and context boundaries are stable.

```text
Phase 5-A pure RelayCTX Unpack contract (complete)
  -> Phase 5-B non-stream runtime wiring (complete)
  -> late Phase 3 client canonicalization prerequisite
  -> Phase 5-C client-instruction first-pass/cache integration
  -> Phase 5.5 Stream Unpack / Output Segmenter
  -> Phase 6 failure-route handling
  -> Phase 7 lightweight RelayREF
  -> Phase 8 Output-side RelaySCN
  -> Phase 9 cross-cutting RelayRUN
  -> Phase 10 RelaySLP separation
```

The project remains in Phase 5 throughout Phase 5-A, 5-B, and 5-C. Completing the bounded client-input prerequisite before Phase 5-C is not a phase rollback.
