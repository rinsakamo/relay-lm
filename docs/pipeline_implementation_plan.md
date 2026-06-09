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

### Phase 1: `app.py` lightweight separation

- Stabilize `PipelineContext` as the shared request-local runtime object.
- Centralize `forwarded_payload` replacement through `PipelineContext`.
- Record replacement reasons whenever the forwarded payload changes.
- Keep short-circuit clarification safe and explicit.
- Keep trace / diagnostics / RelayRUN artifact connection behavior stable.
- Preserve existing behavior by default.

### Phase 2: documentation consolidation

- Document the current pipeline.
- Document the target pipeline.
- Clarify `RelayINT` as the input-side gate.
- Clarify `RelayREF` as the output-side observer.
- Clarify the current `RelayRUN` limitation: request-end artifact writing first, true cross-cutting node-state reporting later.
- Add a failure route table that connects `blocked_reason` / `failure_reason` values to actual behavior.

### Phase 3: `RelayCTX Repack` boundary hardening

- Separate `request_compiler.py` responsibilities from runtime injection steps.
- Keep memory block injection explicit.
- Keep short-term CTX injection explicit.
- Keep token budget truncation behavior explicit.
- Ensure each payload mutation has a reason and diagnostics trail.

### Phase 4: `RelayINT` split / alias

- Move current `relayref.py` input-side behavior toward `relayint.py`.
- Keep a compatibility alias or wrapper if needed to avoid large breakage.
- Treat unresolved reference detection as an INT responsibility.
- Treat quick clarification and short-circuit clarification as INT responsibilities.
- Keep Main LLM bypass behavior explicit for high-confidence clarification paths.

### Phase 5: minimal `RelayCTX Unpack`

- Extract user-visible response text.
- Strip or block internal markers from user output.
- Parse optional `ctx_working_update` only when the format is safe and expected.
- Fail safe: return user-visible text when possible, but block internal updates if unpacking fails.
- Do not write MEM / SOUL / SLP candidates directly from a failed or ambiguous unpack result.

### Phase 6: failure route table / node result handling

- Introduce a common node result shape for pipeline steps.
- Connect `blocked_reason` and `failure_reason` to actual runtime behavior.
- Define routes for continue, skip, short-circuit, diagnostic-only, fallback, blocked, and failed states.
- Allow RelayRUN to consume node results at request end first.
- Keep the shape compatible with future per-node RelayRUN checkpoint reporting.

Suggested conceptual shape:

```python
@dataclass
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

### Phase 7: lightweight `RelayREF` observer

- Add diagnostics-only response checks.
- Do not regenerate by default.
- Do not replace user-visible output by default.
- Detect empty response.
- Detect internal marker leakage.
- Detect obviously unsafe diagnostic leakage.
- Detect likely scene / policy mismatch only as a warning.
- Emit observations for Output-side RelaySCN and future RelayRUN diagnostics.

### Phase 8: Output-side `RelaySCN`

- Evaluate next-turn scene transition.
- Emit recovery hints.
- Emit persistence block reasons.
- Keep immediate output blocking limited to safety, leakage, or recovery-critical cases.
- Treat normal scene transition as next-turn state, not a reason to rewrite the current response.

### Phase 9: `RelayRUN` cross-cutting checkpoint layer

- Move from request-end artifact writing toward per-node status reporting.
- Track node started / completed / blocked / failed states.
- Persist runtime checkpoints with resume metadata.
- Keep RelayRUN semantic-neutral: it should orchestrate runtime state, not decide meaning.
- Route user-visible recovery text through the normal output pipeline unless the failure is transport-level or explicitly non-character system mode.

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
  -> minimal RelayCTX Unpack
  -> failure route table / node result handling
  -> lightweight REF diagnostics-only observer
  -> Output-side SCN
  -> true cross-cutting RelayRUN
  -> SLP separation
```
