# RelayLM Pipeline Implementation Plan

## Purpose

This document fixes the agreed implementation order for moving RelayLM from the current `app.py`-centered runtime toward a staged pipeline.

It is a phase-order memo, not a full architecture specification. Detailed behavior should continue to live in the dedicated module docs and MVP summaries.

## Current caveats

- Current `RelayRUN` is mostly a request-end artifact writer. It is not yet a true cross-cutting node-state reporter.
- Current `relayref.py` behaves as input-side unresolved reference / quick clarification logic. In target terminology, that behavior is closer to `RelayINT` than `RelayREF`.
- `RelayCTX Unpack` is not yet implemented as a real output separation layer. Main LLM output is still mostly returned directly.
- `RelayCTX Repack` overlaps with `request_compiler.py`, memory injection, short-term CTX injection, and token budget truncation. Its boundary should be hardened before adding more downstream behavior.
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

### Phase 3: `RelayCTX Repack` boundary hardening — mostly complete

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
- Remaining Phase 3 work should be limited to small cleanup and handoff notes unless a concrete bug appears.

### Phase 4: `RelayINT` split / alias

- Move current `relayref.py` input-side behavior toward `relayint.py`.
- Keep a compatibility alias or wrapper if needed to avoid large breakage.
- Treat unresolved reference detection as an INT responsibility.
- Treat quick clarification and short-circuit clarification as INT responsibilities.
- Keep Main LLM bypass behavior explicit for high-confidence clarification paths.
- Keep ASR outside RelayINT for the AI VTuber MVP: RelayINT receives text after any external device/OS/browser speech input has already converted voice to text.

Current status:

- `app.py` now calls `build_relayint_reference_repair_dry_run(...)` from `relayint.py`.
- The wrapper delegates to the historical `relayref.py` dry-run artifact builder for compatibility.
- The runtime artifact variable name remains `relayref_artifact` to avoid diagnostics/schema churn.
- `scripts/relaylm_relayint_reference_repair_wrapper_smoke.py` fixes the wrapper contract and verifies that `relayref_artifact` remains the compatibility diagnostics key.
- `relayref.py` remains as the compatibility implementation for now.
- MVP-45 has added the default-off RelayINT Fast Path dry-run artifact for low-latency reference / continuation / prior-memory intent signals.
- MVP-46 has added the default-off RelayINT quick clarification preflight artifact, still diagnostics-only and without user-visible clarification text.
- RelayRUN recovery artifacts now keep historical `source_node: "relayref"` while also emitting `source_node_alias: "relayint_reference_repair"` and `compatibility_source_node: "relayref"` for RelayINT-facing diagnostics.
- PR #241 should be reduced before merge into a Phase 4 completion handoff: keep the RelayINT quick clarification apply plan, request compatibility gate, default-off / dry-run-only config flags, diagnostics / trace wiring, MVP-47 summary, and smoke coverage.
- PR #241 should not land actual user-visible short-circuit behavior in Phase 4. Remove or defer the immediate `app.py` response return path, response-body helper, backend-forward skip behavior, and completed short-circuit RelayRUN artifact wiring until Phase 6.
- The reduced #241 plan-only merge belongs after the existing RelayINT split / preflight work and before Phase 4.5 `PipelineNodeResult` scaffolding.
- Next Phase 4 work should avoid a destructive rename and instead continue moving input-side reference repair terminology toward RelayINT.

### Phase 4.5: pipeline node result scaffold

This phase starts after the reduced #241 plan-only merge has landed. It introduces the shared recording shape for pipeline steps before the full failure-route behavior of Phase 6.

- Add a minimal `PipelineNodeResult` / pipeline step record module.
- Add request-local node result collection to `PipelineContext`.
- Record early node results for already-separated runtime phases when safe.
- Keep recorded node results diagnostics-only at first.
- Do not use node results to change runtime routing yet.
- Preserve existing response bodies, headers, diagnostics, trace output, RelayRUN artifacts, and backend forwarding behavior.
- Keep the shape compatible with the full Phase 6 failure route table and future per-node RelayRUN checkpoint reporting.

Non-goals for this phase:

- Do not implement full blocked / failed / fallback routing.
- Do not change short-circuit clarification behavior.
- Do not move backend forwarding control to the node result layer yet.
- Do not implement CTX Unpack, RelayREF, Output-side SCN, or cross-cutting RelayRUN checkpoints here.

Suggested minimal shape:

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

Phase 4.5 is intentionally narrower than Phase 6: it records what happened, but it does not yet decide what the runtime should do next.

### Phase 5: minimal `RelayCTX Unpack`

- Extract user-visible response text.
- Strip or block internal markers from user output.
- Parse optional `ctx_working_update` only when the format is safe and expected.
- Fail safe: return user-visible text when possible, but block internal updates if unpacking fails.
- Do not write MEM / SOUL / SLP candidates directly from a failed or ambiguous unpack result.
- Record unpack diagnostics through the Phase 4.5 node result scaffold when available.

### Phase 5.5: `RelayCTX Stream Unpack` and output segmentation

This phase is an extension point after minimal non-streaming Unpack is stable.

- Add streaming token/chunk parsing without changing the core meaning of Phase 5.
- Forward user-visible text chunks as early as possible.
- Keep internal marker suppression fail-closed.
- Collect terminal `ctx_working_update` / structured summary delta candidates.
- Add `RelayCTX Output Segmenter` for TTS-safe chunking.
- Classify output chunks before they enter a TTS adapter queue.
- Apply the AI VTuber profile's TTS-safe chunk rules for code blocks, URLs, JSON/YAML, tables, commands, file paths, quotes, and parenthetical notes.
- Keep Return-side EMO lightweight and non-meaning-changing during streaming.

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
  -> RelayINT split / alias
  -> #241 reduced plan-only merge: RelayINT quick clarification apply plan
  -> pipeline node result scaffold
  -> minimal RelayCTX Unpack
  -> RelayCTX Stream Unpack / Output Segmenter
  -> failure route table / node result handling
  -> lightweight REF diagnostics-only observer
  -> Output-side SCN
  -> true cross-cutting RelayRUN
  -> SLP separation
```
