# Phase 5-C4a Instruction-Bearing Managed Apply Handoff

## Status and authority

This is the active one-page implementation handoff for the next RelayLM runtime slice.

It is subordinate to:

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md) for component ownership,
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md) for sequencing,
3. [Client History Authority Contract](client_history_authority_contract.md) and [Client Instruction Authority Contract](client_instruction_authority_contract.md) for authority rules,
4. dedicated current schemas and runtime code for exact implemented behavior.

This handoff does not authorize work beyond the bounded slice below.

## Decision

The next and only active implementation slice is:

```text
Phase 5-C4a
instruction-bearing managed-route history exclusion apply
```

No separate authority, Runtime Compile Gate v1, cache projection, or active-tool-transaction preservation phase is required before starting this slice.

The existing request-local foundations are sufficient:

- `PipelineContext.original_payload` and `forwarded_payload`,
- client-message canonicalization,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0` for the no-instruction compatibility path,
- explicit payload replacement reasons,
- the managed-route backend-forward fail-closed gate.

Missing dependency closure belongs inside Phase 5-C4a rather than in a preceding phase.

## Required result

For a supported instruction-bearing managed `memory_light` request, construct a fresh backend-bound payload that contains only:

```text
one RelayLM-owned compiled prefix
+ at most one bounded escaped low-trust client-instruction evidence block
+ the exact validated current user message
```

The payload must not contain:

- prior client `user` or `assistant` history,
- raw client `system` or `developer` message objects,
- frontend summaries or memory notes,
- old tool results unrelated to an active transaction,
- cache entry bodies or opaque cached scene content.

The current user message must be preserved as a complete message object, including supported multimodal content parts.

## Instruction evidence policy

Use the request-local normalized instruction candidates from `ClientInstructionIdentity`; do not re-read instruction text from the already-compiled backend payload.

The evidence renderer must:

- preserve deterministic source order and role labels,
- combine all current `system` and `developer` candidates into at most one evidence block,
- escape XML-like delimiters and other control-sensitive characters,
- enforce a fixed deterministic size bound,
- label the block explicitly as low-trust current-request evidence,
- place it below RelayLM runtime/safety and approved persona authority,
- remain request-local and content-bearing,
- never enter generic trace, audit, node-result, or exception text.

Do not silently broaden `client_history_exclusion_apply.v0`. Introduce a new explicitly versioned instruction-bearing schema, preferably `client_history_exclusion_apply.v1`, while preserving the current v0 no-instruction behavior during migration.

## Cache posture for this slice

Cache-hit RelaySCN projection remains deferred to Phase 5-C4b.

Therefore Phase 5-C4a must not depend on applying a cache entry. A read-only cache hit does not authorize opaque cache injection and must not make instruction-bearing correctness unavailable.

For this slice:

- use the bounded normalized low-trust evidence block for supported instruction-bearing requests whether lookup is disabled, misses, or reports a hit,
- record only a typed content-free lookup class in diagnostics,
- do not deserialize or inject cached scene state,
- do not write the cache,
- do not claim that repeated instruction evidence has been optimized away.

Phase 5-C4b may later replace repeated evidence with a validated allowlisted RelaySCN projection.

## Dependency closure

Enabling instruction-bearing actual apply must deterministically prepare every required request-local dependency.

The implementation must either:

- make history-exclusion apply imply client-instruction extraction and identity preparation, or
- call a dedicated apply-owned preparation helper that produces the same typed identity result.

It must not require operators to discover and enable unrelated diagnostic flags manually.

Read-only cache lookup remains optional for correctness.

## Compatibility and transaction rules

### Explicit pass-through

`pass_through` remains fully client-authority delegated and unchanged.

### Active tool transaction

The current slice does not implement minimum-chain reconstruction. Existing detection must continue to fail closed with `active_tool_transaction_requires_preservation` before backend forwarding.

This explicit block satisfies the Phase 5-C4a requirement to preserve or block active transactions coherently. Tool-transaction preservation may be implemented later behind a dedicated contract.

### Structured output and request-level options

For requests without an active message-chain transaction, preserve compatible top-level request fields from the compiled payload, including supported `tools`, `tool_choice`, `response_format`, sampling fields, stream choice, and provider-specific options.

The implementation should replace only the backend-bound `messages` list unless a dedicated compatibility contract requires another bounded mutation.

### Streaming

This slice changes backend-bound request construction only. It does not implement Stream Unpack or change SSE response handling.

The backend-forward gate must block both streaming and non-streaming requests when explicit actual apply cannot produce an exact applied result.

## Runtime integration

The apply path must:

1. consume only typed request-local prerequisites,
2. build a detached candidate without mutating inputs,
3. return `ready` in dry-run-only mode,
4. return `applied` only when the exact candidate is selected,
5. replace `PipelineContext.forwarded_payload` through the standard helper,
6. record one stable mutation reason,
7. remain idempotent within one request,
8. emit a typed content-free `PipelineNodeResult`,
9. let the existing backend-forward gate fail closed for every non-applied actual-apply result.

The complete target Runtime Compile Gate taxonomy, forwarded-payload-source typing, and managed fallback builder are not prerequisites. Do not implement them in this slice.

## Start conditions

Implementation may begin when all of these remain true on current `main`:

- the no-instruction v0 contract and runtime smoke pass,
- the backend-forward gate blocks instruction-bearing actual apply before the backend,
- instruction identity is request-local and content-bearing,
- canonicalization and preflight detect active tool transactions,
- default apply remains disabled and dry-run-only remains true,
- generic trace/audit projections remain content-free.

If a start condition is no longer true, fix that regression first without expanding the slice.

## Required smoke coverage

Add deterministic smoke coverage for:

1. v0 no-instruction behavior remains unchanged,
2. `system` only, `developer` only, and mixed deterministic instruction order,
3. bounded escaping and oversize rejection or truncation policy,
4. exact current text-message preservation,
5. exact current multimodal-message preservation,
6. prior user/assistant history exclusion,
7. no raw instruction message object reaches the backend,
8. apply dependency closure when standalone extraction/cache flags are false,
9. cache disabled, miss, and hit classes without cache entry injection or write,
10. dry-run candidate without payload mutation,
11. actual apply with one payload replacement and stable mutation reason,
12. request-local idempotency,
13. explicit `pass_through` preservation,
14. active tool transaction block before backend forwarding,
15. compatible top-level `tools`, `tool_choice`, `response_format`, sampling, stream, and provider fields remain unchanged,
16. streaming and non-streaming blocked paths never reach the backend,
17. node result, trace, and public error remain content-free,
18. runtime exceptions produce only bounded stable reason IDs.

At minimum, run the existing regression smokes:

```bash
python scripts/relaylm_client_message_canonicalization_smoke.py
python scripts/relaylm_client_instruction_identity_contract_smoke.py
python scripts/relaylm_client_instruction_identity_runtime_smoke.py
python scripts/relaylm_client_instruction_cache_lookup_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_preflight_smoke.py
python scripts/relaylm_client_history_exclusion_apply_contract_smoke.py
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
python scripts/relaylm_trace_content_free_contract_smoke.py
python scripts/relaylm_jsonl_trace_smoke.py
python scripts/relaylm_hardening_smoke.py
```

Add the new instruction-bearing contract/runtime/end-to-end smokes to `.github/workflows/onboarding-config-smoke.yml` or a dedicated authority workflow with equivalent `pull_request` and `main` push coverage.

## Non-goals

Do not include:

- cache-hit RelaySCN projection,
- typed client-instruction response parsing,
- instruction-cache write,
- complete Runtime Compile Gate v1 taxonomy,
- authority-safe managed fallback builder,
- active tool-transaction reconstruction,
- RelaySOUL mutation, proposal execution, rollback, or persistence,
- Stream Unpack or TTS-safe segmentation,
- RelayREF,
- output-side RelaySCN,
- full RelayRUN route-table or per-node orchestration promotion,
- new default-on behavior.

## Rollback conditions

Rollback the slice, or return it to dry-run-only, if any of these occurs:

- prior client history reaches a managed backend,
- raw client instruction messages regain backend authority,
- instruction or user content appears in trace, node results, public errors, or exception text,
- current multimodal content is flattened, reordered, or lost,
- pass-through behavior changes,
- active tool transactions reach the backend with an incomplete chain,
- compatible top-level request fields are dropped or rewritten unexpectedly,
- a non-applied explicit actual-apply request reaches the backend,
- the operation is not idempotent,
- default-off or dry-run-by-default posture changes.

Rollback must preserve the current v0 no-instruction path and backend-forward fail-closed behavior.

## Completion criteria

Phase 5-C4a is complete only when:

- supported no-instruction and instruction-bearing managed requests exclude prior client history by apply,
- instruction evidence is bounded, escaped, explicitly low-trust, and not represented as client-authoritative messages,
- current text and multimodal user content remain intact,
- active transactions are preserved by an implemented contract or explicitly blocked,
- every mutation is recorded through `PipelineContext`,
- explicit actual apply fails closed unless an exact applied result exists,
- pass-through remains unchanged,
- all required deterministic smokes and CI pass.

After completion, update [Project Status](../PROJECT_STATUS.md) and [Pipeline Implementation Plan](pipeline_implementation_plan.md) before selecting the next implementation slice.