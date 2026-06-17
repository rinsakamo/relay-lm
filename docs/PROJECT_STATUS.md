# RelayLM Project Status

Last reviewed: 2026-06-17 JST

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It summarizes what works now, what remains gated or incomplete, and the one active implementation boundary.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status, dependencies, and sequencing.
3. Dedicated module and contract documents own exact current schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines how compatibility and target material are interpreted.
5. `docs/mvp/` remains historical implementation evidence only.

## Documentation audit closure

The repository-wide documentation audit, audit Phases 1–8, is complete as of 2026-06-17 JST.

That audit numbering is independent of implementation Phase numbers. In particular, documentation-audit Phase 8 does not mean implementation Phase 8 has started.

The completed audit established:

- current, compatibility, target, migration, and historical boundaries,
- canonical authority and ownership precedence,
- current onboarding/config/runtime behavior,
- safe default-off and dry-run posture,
- active-document and historical-document separation,
- one formal handoff to the next implementation slice.

Future documentation work is maintenance driven by runtime changes rather than another open-ended audit phase.

## Current implementation position

```text
Current implementation phase: Phase 5-C — in progress

Latest completed bounded slice:
  Phase 5-C1a no-instruction managed-route history exclusion apply
  + request-local runtime wiring
  + backend-forward fail-closed gate

Next and only active slice:
  Phase 5-C4a instruction-bearing managed apply
```

The active implementation instructions are in [Phase 5-C4a Instruction-Bearing Managed Apply Handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md).

## Current implemented boundary

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, model routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- current profile compilation and RelayCTX Repack phases,
- RelayINT-facing reference-repair compatibility boundary,
- selected RelayMEM retrieval and gated CTX injection,
- pure and gated non-stream RelayCTX Unpack,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0` for the no-instruction case,
- exact actual-apply payload replacement through `PipelineContext`,
- backend-forward blocking when explicit managed actual apply has no exact applied result,
- request-level RelayRUN diagnostics/checkpoint/recovery foundations,
- RelaySOUL dry-run/preflight governance foundations.

Current safe posture remains:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
```

On the default `memory_light` compatibility path, prior frontend-supplied user/assistant history may still remain backend-bound unless the bounded actual-apply path is explicitly enabled and supported.

## Current no-instruction apply

The current contract is:

```text
client_history_exclusion_apply.v0
```

It supports a managed `memory_light` compiled payload with no client `system` or `developer` messages. It retains one RelayLM-owned compiled prefix and the exact validated current user message.

- disabled: no result or mutation,
- dry-run-only: request-local candidate only,
- actual apply: mutate only for an exact `applied` result,
- non-applied explicit actual apply: block before backend forwarding,
- explicit `pass_through`: exempt and unchanged,
- active tool transaction: blocked because minimum-chain reconstruction is not implemented.

Runtime-private payload candidates may contain content. Persisted trace, audit, public error, and node-result projections remain typed and content-free.

## Not yet implemented

The current runtime does not yet provide:

- instruction-bearing managed-route history exclusion apply,
- identity-derived bounded low-trust instruction evidence apply,
- replacement of the current legacy `incoming_system_prompt` compiler block on the managed authority path,
- cache-hit RelaySCN projection,
- typed client-instruction response parsing or cache write,
- complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy,
- Stream Unpack and TTS-safe segmentation,
- dedicated output-side RelayREF and complete output-side RelaySCN,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution.

These items are not all active work. Detailed later sequencing remains only in the implementation plan.

## Next implementation decision

The next slice is Phase 5-C4a. No separate authority, compile-gate, or tool-transaction-preservation slice must precede it.

Existing request-local foundations are sufficient. The remaining dependency and compiler-path closure belongs inside 5-C4a:

- instruction-bearing apply must automatically prepare its typed instruction identity dependency,
- read-only cache lookup must remain optional for correctness,
- the legacy compiler `incoming_system_prompt` block must be replaced rather than retained alongside identity-derived evidence,
- active tool transactions must continue to fail closed until a dedicated minimum-chain preservation contract exists,
- complete Runtime Compile Gate v1 and managed fallback remain later target work.

The required backend payload for a supported instruction-bearing request is:

```text
one RelayLM-owned compiled system message containing:
  approved runtime / profile / context blocks
  + at most one bounded escaped low-trust instruction-evidence block

+ exact validated current user message
```

Raw client instruction message objects, duplicate legacy evidence, and prior client history must not regain backend authority.

## Start conditions

5-C4a may begin while current `main` continues to prove:

- v0 no-instruction contract/runtime behavior passes,
- instruction-bearing actual apply blocks before backend forwarding,
- instruction identity is request-local and content-bearing,
- canonicalization and preflight detect active tool transactions,
- the legacy instruction block is identifiable through typed compiler construction,
- apply remains default-off and dry-run-only by default,
- generic trace/audit surfaces remain content-free.

A regression in these foundations is repaired first without expanding the slice.

## Non-goals and rollback

5-C4a must not include cache-hit RelaySCN projection, typed response parsing, cache write, Runtime Compile Gate v1, managed fallback construction, active tool-chain reconstruction, RelaySOUL mutation, Stream Unpack, RelayREF, output-side RelaySCN, full RelayRUN route promotion, or new default-on behavior.

Return the slice to dry-run-only or roll it back if it leaks prior history or instruction/user content, duplicates legacy and identity-derived evidence, changes pass-through authority, loses current multimodal content, forwards an incomplete tool transaction, changes compatible top-level request fields unexpectedly, permits a non-applied actual-apply request to reach the backend, breaks idempotency, or changes safe defaults.

The complete smoke matrix and rollback contract are in the active handoff document.

## Usable runtime paths

Primary local path:

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

Optional frontend path:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM does not own frontend UI, ASR, TTS execution, or avatar execution. Current streaming remains primarily backend SSE forwarding; safe Stream Unpack is not implemented.

## Where to read next

- [Phase 5-C4a implementation handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Authority Contract](architecture/client_history_authority_contract.md)
- [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md)
- [Runtime Compile Current / Target Boundary](contracts/runtime_compile_current_target.md)
- [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page when the active slice changes, a boundary moves between design/dry-run/read-only/apply, a default changes, supported request/response behavior changes, or a current schema/producer/consumer changes. Do not duplicate the full roadmap here; later sequencing belongs in the implementation plan.