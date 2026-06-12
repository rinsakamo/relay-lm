# RelayLM Pipeline Implementation Plan

## Purpose

This document fixes the agreed implementation order for moving RelayLM from the current `app.py`-centered runtime toward a staged pipeline.

It is a phase-order memo, not a full architecture specification. Detailed behavior should continue to live in the dedicated module docs and MVP summaries.

## Current caveats

- Current `RelayRUN` is mostly a request-end artifact writer. It is not yet a true cross-cutting node-state reporter.
- Current `relayref.py` behaves as input-side unresolved reference / quick clarification logic. In target terminology, that behavior is closer to `RelayINT` than `RelayREF`.
- `RelayCTX Unpack` now has a pure non-streaming parser/contract, but runtime backend-response wiring is not yet enabled by default.
- `RelayCTX Repack` overlaps with `request_compiler.py`, memory injection, short-term CTX injection, token budget truncation, and the newer client-message canonicalization boundary. Its large movement is mostly complete, but late boundary hardening remains before client instruction hash/cache behavior can be activated.
- `RelayREF` should start as a lightweight diagnostics-only observer. Accurate answer-quality evaluation may require another model call and is not an early implementation requirement.
- `PipelineContext` and `diagnostics_builder.py` are now present as the first stabilization layer.
  - `PipelineContext` owns request-local forwarded payload state.
  - `diagnostics_builder.py` owns grouped `RequestDiagnostics` mapping helpers.
  - Runtime node execution is still mostly in `app.py`.

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

## Implementation order

### Phase 1: `app.py` lightweight separation — mostly complete

- Stabilize `PipelineContext` as the shared request-local runtime object.
- Centralize `forwarded_payload` replacement through `PipelineContext`.
- Record replacement reasons whenever the forwarded payload changes.
- Keep short-circuit clarification safe and explicit.
- Keep trace / diagnostics / RelayRUN artifact connection behavior stable.
- Preserve existing behavior by default.

Current status:

- `PipelineContext` has been introduced.
- `forwarded_payload` mutation tracking is routed through `PipelineContext.replace_forwarded_payload(...)`.
- `diagnostics_builder.py` now reduces inline `RequestDiagnostics` field mapping in `app.py`.
- Remaining work in this phase should be limited to small safety fixes, not deeper semantic behavior.

### Phase 2: documentation consolidation — in progress

- Document the current pipeline.
- Document the target pipeline.
- Clarify `RelayINT` as the input-side gate.
- Clarify `RelayREF` as the output-side observer.
- Clarify the current `RelayRUN` limitation: request-end artifact writing first, true cross-cutting node-state reporting later.
- Add a failure route table that connects `blocked_reason` / `failure_reason` values to actual behavior.
- Add profile-specific implementation contracts that should not pollute the generic pipeline responsibility document.
  - `docs/ai_vtuber_pipeline_profile.md` owns the text-in / voice-out AI VTuber MVP profile.
  - It documents ASR as out of scope for the MVP.
  - It documents the Return-side EMO hint contract, TTS adapter boundary, avatar adapter boundary, and TTS-safe chunk rules.

Current status:

- `docs/pipeline_responsibility_design.md` now documents the current implementation status.
- It also records the next implementation boundary after PipelineContext and diagnostics-builder cleanup.
- `docs/ai_vtuber_pipeline_profile.md` documents the AI VTuber-specific adapter and output segmentation profile.
- Remaining Phase 2 work should focus on failure route details and implementation handoff notes before deeper code movement.
- The AI VTuber profile now includes the adapter boundary contract and TTS-safe segmentation rules needed before Phase 5.5.

### Phase 3: `RelayCTX Repack` boundary hardening — mostly complete, with late prerequisites

- Separate `request_compiler.py` responsibilities from runtime injection steps.
- Keep memory block injection explicit.
- Keep short-term CTX injection explicit.
- Keep token budget truncation behavior explicit.
- Ensure each payload mutation has a reason and diagnostics trail.
- Keep the AI VTuber profile small-context friendly.
  - Main LLM should receive a token-budgeted payload rather than raw long client history.
  - VTuber-style routes should be compatible with 8k-16k backend context targets when possible.
  - The Main LLM may produce user-visible response text plus a bounded `ctx_working_update` / structured summary delta.

Current status:

- `relaylm/relayctx_repack.py` now owns the main backend-bound payload mutation phases.
- RelayMEM snippet/runtime CTX injection has moved out of `app.py`.
- Token budget truncation runtime application has moved out of `app.py`.
- RelayCTX short-term runtime injection apply has moved out of `app.py`.
- Each moved phase still records forwarded payload replacement through `PipelineContext`.
- `app.py` still owns orchestration order, diagnostics assembly, backend forwarding, and response handling.
- PR #246 added the client-message authority contract and the compatibility fix for `system` / `developer` instruction extraction.
- Remaining Phase 3 work should be treated as late boundary hardening, not a phase rollback.

Late Phase 3 prerequisites before client instruction hash/cache activation:

```text
client_message_canonicalize
  -> current_turn_extract
  -> client_instruction_extract
  -> client_instruction_hash
  -> client_instruction_cache_lookup
  -> cached SCN injection or one-time first-pass evidence
  -> raw client history/system/developer exclusion
```

These prerequisites may be implemented while the project is otherwise in Phase 5, because they are input-side safety gates required by the later Phase 5-B client-instruction flow. They should remain narrow and should not reopen broad CTX Repack migration work.

### Phase 4: `RelayINT` split / alias — complete

- Move current `relayref.py` input-side behavior toward `relayint.py`.
- Keep a compatibility alias or wrapper if needed to avoid large breakage.
- Treat unresolved reference detection as an INT responsibility.
- Treat quick clarification and short-circuit clarification as INT responsibilities.
- Keep Main LLM bypass behavior explicit for high-confidence clarification paths.
- Keep ASR outside RelayINT for the AI VTuber MVP: RelayINT receives text after any external device/OS/browser speech input has already converted voice to text.

Current status:

- `app.py` calls `build_relayint_reference_repair_dry_run(...)` from `relayint.py`.
- The wrapper delegates to the historical `relayref.py` dry-run artifact builder for compatibility.
- The runtime artifact variable and diagnostics key remain `relayref_artifact` to avoid schema churn.
- `scripts/relaylm_relayint_reference_repair_wrapper_smoke.py` fixes the wrapper and compatibility diagnostics contract.
- `relayref.py` remains as an intentional compatibility implementation, not an incomplete Phase 4 task.
- MVP-45 provides the default-off RelayINT Fast Path dry-run artifact for reference, continuation, and prior-memory intent signals.
- MVP-46 provides the default-off quick clarification preflight artifact without user-visible clarification text.
- MVP-47 provides the default-off / dry-run-only quick clarification apply-plan artifact and request compatibility gate.
- RelayRUN recovery artifacts preserve historical `source_node: "relayref"` while also emitting `source_node_alias: "relayint_reference_repair"` and `compatibility_source_node: "relayref"`.
- PR #241 landed in plan-only form. Backend forwarding and backend-owned response bodies remain unchanged.
- Actual user-visible quick clarification, Main LLM/backend bypass, and completed short-circuit RelayRUN wiring are intentionally deferred to Phase 6.
- Destructive removal of historical `relayref` names is deferred to a later compatibility migration.

### Phase 4.5: pipeline node result scaffold — complete

This phase introduced the shared recording shape for pipeline steps before the full failure-route behavior of Phase 6.

- Add a minimal `PipelineNodeResult` / pipeline step record module.
- Add request-local node result collection to `PipelineContext`.
- Record early node results for already-separated runtime phases when safe.
- Keep recorded node results diagnostics-only at first.
- Do not use node results to change runtime routing yet.
- Preserve existing response bodies, headers, diagnostics, trace output, RelayRUN artifacts, and backend forwarding behavior.
- Keep the shape compatible with the full Phase 6 failure route table and future per-node RelayRUN checkpoint reporting.

Current status:

- `relaylm/pipeline_node_result.py` defines the frozen shared result shape and detached log serialization.
- `PipelineContext.node_results` provides an ordered request-local collection.
- `relaylm/pipeline_node_adapter.py` builds content-free summaries from existing RelayINT and RelayCTX artifacts.
- Runtime trace metadata emits `pipeline_node_results` on a best-effort basis.
- Initial recorded nodes are `relayint_reference_repair`, `relayint_quick_clarification`, and `relayctx_repack`.
- Node-result recording does not mutate payload routing state, backend forwarding, response bodies, or RelayRUN behavior.
- Full artifacts containing possible raw CTX handoff values are not copied into node results.
- MVP-48 records the completed Phase 4.5 contract and Phase 5 handoff.

Non-goals for this phase:

- Do not implement full blocked / failed / fallback routing.
- Do not change short-circuit clarification behavior.
- Do not move backend forwarding control to the node result layer yet.
- Do not implement CTX Unpack, RelayREF, Output-side SCN, or cross-cutting RelayRUN checkpoints here.

Implemented minimal shape:

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

Phase 4.5 remains intentionally narrower than Phase 6: it records what happened, but it does not yet decide what the runtime should do next.

### Phase 5-A: minimal non-stream `RelayCTX Unpack` parser — complete

- Extract user-visible response text from a complete backend response string.
- Strip or block internal markers from user output.
- Parse optional `ctx_working_update` only when the format is safe and expected.
- Fail safe: return user-visible text when possible, but block internal updates if unpacking fails.
- Do not write MEM / SOUL / SLP candidates directly from a failed or ambiguous unpack result.
- Record content-free unpack diagnostics through the Phase 4.5 node result scaffold shape.
- Keep backend forwarding, response bodies, RelayRUN behavior, and app-level routing unchanged.

Current status:

- PR #247 added the pure non-streaming `RelayCTX Unpack` parser and contract.
- The accepted MVP marker is a trailing `relayctx_working_update.v0` JSON envelope.
- Malformed, repeated, reversed, or non-trailing internal markers are suppressed fail-closed.
- The parser preserves ordinary backend response text unchanged when no internal marker is present.
- The parser does not guess JSON/YAML from ordinary prose.
- The parser does not persist accepted update candidates.
- `app.py` wiring remains intentionally deferred to Phase 5-B.

### Phase 5-B: non-stream `RelayCTX Unpack` runtime wiring — next

This phase wires the Phase 5-A parser into actual non-streaming backend response handling behind explicit default-off/apply gates.

- Add runtime configuration gates for non-stream Unpack apply.
- Call the Unpack parser at the backend response boundary.
- Replace only the user-visible assistant content with unpacked visible text when apply is enabled and safe.
- Preserve backend-owned response shape when Unpack is disabled, skipped, or failed.
- Record `relayctx_unpack` as a node result at the execution boundary.
- Keep accepted `ctx_working_update` as a non-persistent request-local candidate.
- Block MEM / SOUL / SLP writes from Unpack candidates.
- Preserve Phase 5-A fail-safe behavior for malformed or ambiguous internal markers.
- Do not implement streaming support here.
- Do not implement client-instruction cache persistence here unless the generic Unpack runtime boundary is already stable.

Client-instruction first-pass integration should be treated as a Phase 5-B follow-up after the generic Unpack wiring is stable:

```text
client instruction cache miss
  -> one-time untrusted instruction evidence in CTX Repack
  -> Main LLM visible response + control artifact
  -> RelayCTX Unpack separates visible/control content
  -> strict artifact validation
  -> cache write candidate
```

The generic Unpack path must land before this client-instruction-specific use case, otherwise the instruction cache path would create a second ad hoc output parser.

### Phase 5.5: `RelayCTX Stream Unpack` and output segmentation

This phase is an extension point after non-streaming Unpack runtime wiring is stable.

- Add streaming token/chunk parsing without changing the core meaning of Phase 5-A/5-B.
- Forward user-visible text chunks as early as possible.
- Keep internal marker suppression fail-closed.
- Collect terminal `ctx_working_update` / structured summary delta candidates.
- Add `RelayCTX Output Segmenter` for TTS-safe chunking.
- Classify output chunks before they enter a TTS adapter queue.
- Apply the AI VTuber profile's TTS-safe chunk rules for code blocks, URLs, JSON/YAML, tables, commands, file paths, quotes, and parenthetical notes.
- Keep Return-side EMO lightweight and non-meaning-changing during streaming.
- Extend the same sentinel-buffer principle to later client-instruction control envelopes so internal markers cannot leak to users, captions, or TTS.

### Phase 6: failure route table / node result handling

- Promote the Phase 4.5 node result scaffold from diagnostics-only recording into runtime behavior where appropriate.
- Connect `blocked_reason` and `failure_reason` to actual runtime behavior.
- Define routes for continue, skip, short-circuit, diagnostic-only, fallback, blocked, and failed states.
- Allow RelayRUN to consume node results at request end first.
- Reintroduce RelayINT quick clarification actual apply here, after the #241 plan-only merge and Phase 4.5 node-result scaffold are stable.
  - The actual apply path should be expressed through node results / response adapter / backend-forward routing rather than direct `app.py` response construction.
  - The short-circuit response should keep the same content-free, fixed-template, compatibility-gated constraints established by the reduced #241 plan.
- Keep the shape compatible with future per-node RelayRUN checkpoint reporting.
- Include AI VTuber stream/output adapter failure routes.
  - chunk parse failure,
  - TTS adapter failure,
  - partial stream failure,
  - internal update parse failure,
  - caption-only fallback.

### Phase 7: lightweight `RelayREF` observer

- Add diagnostics-only response checks.
- Do not regenerate by default.
- Do not replace user-visible output by default.
- Detect empty response.
- Detect internal marker leakage.
- Detect obviously unsafe diagnostic leakage.
- Detect likely scene / policy mismatch only as a warning.
- Emit observations for Output-side RelaySCN and future RelayRUN diagnostics.
- For stream/output adapter profiles, observe chunk and marker leakage diagnostics but do not directly rewrite normal visible output.

### Phase 8: Output-side `RelaySCN`

- Evaluate next-turn scene transition.
- Emit recovery hints.
- Emit persistence block reasons.
- Keep immediate output blocking limited to safety, leakage, or recovery-critical cases.
- Treat normal scene transition as next-turn state, not a reason to rewrite the current response.
- For AI VTuber routes, treat TTS/avatar failure as output-adapter state unless it also implies semantic leakage, safety mismatch, or recovery-critical failure.

### Phase 9: `RelayRUN` cross-cutting checkpoint layer

- Move from request-end artifact writing toward per-node status reporting.
- Track node started / completed / blocked / failed states.
- Persist runtime checkpoints with resume metadata.
- Keep RelayRUN semantic-neutral: it should orchestrate runtime state, not decide meaning.
- Route user-visible recovery text through the normal output pipeline unless the failure is transport-level or explicitly non-character system mode.
- Eventually track stream chunk lifecycle and TTS/avatar adapter diagnostics as runtime artifacts, not semantic decisions.

### Phase 10: `RelaySLP` separation

- Keep memory and SOUL update compilation outside the normal response path.
- Route candidates through persistence gates.
- Separate retrieval-time memory reads from SLP-time memory writes.
- Keep raw evidence, compiled memory pages, lineage, and approval state distinct.
- Do not let normal response generation directly mutate long-term memory or SOUL.

## Failure route principles

### INT clarification

When RelayINT emits a high-confidence clarification decision, the default path should be:

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

Blocked or empty retrieval should usually continue without memory:

```text
RelayMEM retrieval empty/blocked
  -> CTX Repack without retrieved memory block
  -> diagnostics records blocked reasons
  -> Main LLM continues
```

Only memory-dependent user requests should surface a user-visible memory unavailable or clarification response.

### CTX Repack token pressure

Token pressure should degrade in a defined order:

1. Remove diagnostics / trace-only context.
2. Reduce retrieved memory.
3. Reduce short-term CTX blocks.
4. Shorten conversation history.
5. Use a safe fallback response if no valid payload can be produced.

### CTX Unpack failure

Unpack failure should not destroy an otherwise usable response:

```text
Return user-visible response text when available.
Block ctx_working_update / MEM / SOUL / SLP candidates.
Record unpack_failed diagnostics.
```

### Stream / output adapter failure

Stream and output adapter failures should not invalidate already-safe visible text:

```text
partial visible chunks emitted
  -> preserve emitted chunks
  -> block incomplete internal update candidates
  -> record partial stream / chunk / adapter diagnostics
  -> allow Output-side SCN and RelayRUN to prepare next-turn recovery hints when needed
```

TTS adapter failure should normally fall back to caption/text output and diagnostics.

### REF warning

Early RelayREF findings should be diagnostics-only unless they detect leakage, empty output, or a safety-critical mismatch.

## Near-term sequencing rule

Do not make RelayREF smart before the input and context boundaries are stable.

The near-term order is:

```text
app.py lightweight separation
  -> docs consolidation
  -> CTX Repack boundary hardening
  -> RelayINT split / alias (complete)
  -> RelayINT quick clarification plan-only handoff (complete)
  -> pipeline node result scaffold (complete)
  -> minimal non-stream RelayCTX Unpack parser (complete)
  -> non-stream RelayCTX Unpack runtime wiring
  -> client instruction hash/cache first-pass integration
  -> RelayCTX Stream Unpack / Output Segmenter
  -> failure route table / node result handling
  -> lightweight REF diagnostics-only observer
  -> Output-side SCN
  -> true cross-cutting RelayRUN
  -> SLP separation
```

## Phase boundary note after client-instruction contract

PR #246 intentionally introduced both input-side and output-side design obligations:

```text
input-side obligation
  client message canonicalization / instruction hash / cache lookup / raw context exclusion

output-side obligation
  visible/control separation / strict validation / cache write candidate
```

This does not require returning to Phase 3 as the main project phase. The correct implementation posture is:

```text
Phase 5 remains active.
Late Phase 3 hardening may be done as narrow prerequisites.
Client-instruction cache activation waits until generic Phase 5-B Unpack runtime wiring is stable.
```
