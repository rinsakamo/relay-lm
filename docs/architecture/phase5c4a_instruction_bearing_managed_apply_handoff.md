# Phase 5-C4a Instruction-Bearing Managed Apply Handoff

## Authority and decision

This is the active implementation handoff for the next RelayLM runtime slice. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), sequencing in [Pipeline Implementation Plan](pipeline_implementation_plan.md), and authority rules in the [Client History Authority Contract](client_history_authority_contract.md) and [Client Instruction Authority Contract](client_instruction_authority_contract.md).

The next and only active slice is:

```text
Phase 5-C4a
instruction-bearing managed-route history exclusion apply
```

No separate authority, Runtime Compile Gate v1, cache-projection, or tool-transaction-preservation phase is required first. Existing `PipelineContext`, canonicalization, runtime-private instruction identity, read-only cache lookup, history-exclusion preflight, v0 no-instruction apply, and backend-forward fail-closed gate are sufficient foundations. Missing dependency closure belongs inside 5-C4a.

## Required result

For a supported instruction-bearing managed `memory_light` request, build a fresh backend payload containing only:

```text
one RelayLM-owned compiled prefix
+ at most one bounded escaped low-trust instruction-evidence block
+ the exact validated current user message
```

Exclude prior client user/assistant history, raw client system/developer message objects, frontend summaries or memory notes, unrelated old tool results, and cache-entry bodies. Preserve the complete current user message, including supported multimodal parts.

Use normalized candidates from request-local `ClientInstructionIdentity`. Do not recover instruction text from the compiled payload. The renderer must preserve deterministic role/order, combine candidates into at most one block, escape control-sensitive delimiters, enforce a deterministic size bound, label the block as low-trust current-request evidence, and keep it below RelayLM runtime/safety and approved persona authority.

Do not silently broaden `client_history_exclusion_apply.v0`. Add an explicitly versioned instruction-bearing contract, preferably `client_history_exclusion_apply.v1`, while preserving v0 behavior during migration.

## Dependency and cache posture

Enabling instruction-bearing apply must prepare its required instruction extraction/identity dependency automatically or through an apply-owned helper. Operators must not need unrelated diagnostic flags. Read-only cache lookup remains optional for correctness.

Cache-hit RelaySCN projection remains deferred to Phase 5-C4b. In 5-C4a, supported instruction-bearing requests may use the bounded normalized evidence block when lookup is disabled, misses, or reports a hit. Do not inject opaque cache content, write cache entries, or claim repeated-prompt optimization.

## Compatibility rules

- `pass_through` remains client-authority delegated and unchanged.
- Active tool transactions remain explicitly blocked with `active_tool_transaction_requires_preservation`; minimum-chain reconstruction is not part of this slice.
- Preserve compatible top-level request fields, including supported `tools`, `tool_choice`, `response_format`, sampling, stream, and provider options. Replace only `messages` unless a dedicated contract requires another bounded mutation.
- This slice changes backend-bound request construction only. It does not implement Stream Unpack or change SSE response handling.
- Streaming and non-streaming requests must both stop before backend forwarding when explicit actual apply has no exact applied result.

## Runtime integration

The apply path must:

1. consume typed request-local prerequisites,
2. build a detached candidate without mutating inputs,
3. return `ready` in dry-run-only mode,
4. return `applied` only for the selected exact candidate,
5. replace `PipelineContext.forwarded_payload` through the standard helper,
6. record one stable mutation reason,
7. remain request-local and idempotent,
8. emit only a typed content-free `PipelineNodeResult`,
9. preserve the existing fail-closed backend-forward gate for every non-applied actual-apply result.

The complete Runtime Compile Gate v1 taxonomy, explicit forwarded-payload-source typing, and a managed fallback builder are not prerequisites or goals of this slice.

## Start conditions

Implementation may start while current `main` still proves:

- the v0 no-instruction contract/runtime path passes,
- instruction-bearing actual apply is blocked before backend forwarding,
- instruction identity remains request-local and content-bearing,
- canonicalization and preflight detect active tool transactions,
- apply is default-off and dry-run-only by default,
- generic trace/audit projections remain content-free.

Fix any regression in these foundations before expanding the slice.

## Required smoke coverage

Add deterministic contract, runtime, and end-to-end coverage for:

1. unchanged v0 no-instruction behavior,
2. system-only, developer-only, and mixed deterministic instruction order,
3. escaping and oversize policy,
4. exact text and multimodal current-message preservation,
5. prior history exclusion and no raw instruction-message forwarding,
6. dependency closure with standalone extraction/cache flags disabled,
7. cache disabled/miss/hit classes without cache injection or write,
8. dry-run mutation neutrality and exact actual-apply replacement,
9. request-local idempotency and stable mutation reason,
10. unchanged `pass_through`,
11. active tool-transaction block before backend forwarding,
12. preservation of compatible top-level request fields,
13. streaming and non-streaming fail-closed paths,
14. content-free node results, trace, public errors, and bounded exception reasons.

Run the existing regressions at minimum:

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

Add the new instruction-bearing smokes to `onboarding-config-smoke.yml` or an equivalent authority workflow with pull-request and `main` push coverage.

## Non-goals

Do not include cache-hit RelaySCN projection, typed instruction-response parsing, cache write, Runtime Compile Gate v1, managed fallback construction, active tool-chain reconstruction, RelaySOUL mutation/persistence, Stream Unpack, RelayREF, output-side RelaySCN, full RelayRUN route promotion, or new default-on behavior.

## Rollback conditions

Rollback the slice, or return it to dry-run-only, if prior client history reaches a managed backend; raw client instruction messages regain authority; content appears in trace/node results/public errors; multimodal content is lost or reordered; pass-through changes; incomplete tool chains reach the backend; compatible top-level fields are unexpectedly changed; a non-applied actual-apply request reaches the backend; idempotency fails; or safe defaults change.

Rollback must preserve the v0 no-instruction path and its backend-forward fail-closed behavior.

## Completion criteria

5-C4a completes only when supported no-instruction and instruction-bearing managed requests exclude prior client history by apply; instruction evidence is bounded, escaped, explicitly low-trust, and not represented as client-authoritative messages; current text/multimodal input remains intact; active transactions are preserved or explicitly blocked; all mutations use `PipelineContext`; explicit actual apply fails closed without an exact applied result; pass-through remains unchanged; and all required deterministic smokes and CI pass.

After completion, update [Project Status](../PROJECT_STATUS.md) and the implementation plan before selecting another slice.