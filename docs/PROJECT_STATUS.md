# RelayLM Project Status

Last reviewed: 2026-06-18 JST

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It summarizes what works now, what remains gated, and the next implementation choices.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated module and contract documents own exact schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines compatibility and target interpretation.
5. `docs/mvp/` is historical implementation evidence only.

## Documentation audit closure

The repository-wide documentation audit, audit Phases 1–8, is complete as of 2026-06-17 JST. Documentation-audit numbering is independent of implementation-phase numbering. Future documentation work is maintenance driven by runtime changes.

## Current implementation position

```text
Current implementation phase: Phase 5-C — in progress

Latest completed bounded slice:
  Phase 5-C4a instruction-bearing managed apply
  + explicit instruction-source provenance
  + bounded low-trust evidence rendering
  + prior-history/raw-instruction exclusion
  + exact backend-forward gate
```

Phase 5-C4a adds `client_history_exclusion_apply.v1` without broadening the existing no-instruction `client_history_exclusion_apply.v0` contract.

Later candidates remain independently sequenced:

- Phase 5-C4b: validated cache-hit RelaySCN projection,
- Phase 5-C5: typed parse and cache write,
- Phase 5-D: pre-stream hardening,
- Phase 5.5: Stream Unpack and output segmentation.

## Current implemented boundary

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- current profile compilation and RelayCTX Repack phases,
- RelayINT-facing reference-repair compatibility boundary,
- selected RelayMEM retrieval and gated CTX injection,
- pure and gated non-stream RelayCTX Unpack,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests,
- request-level RelayRUN diagnostics/checkpoint/recovery foundations,
- RelaySOUL dry-run/preflight governance foundations.

The safe defaults remain unchanged:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
```

Default `memory_light` compatibility compilation may therefore still preserve frontend history until the bounded apply path is explicitly enabled.

## No-instruction apply

`client_history_exclusion_apply.v0` supports a managed `memory_light` compiled payload with no client `system` or `developer` messages.

It retains:

```text
one RelayLM-owned compiled prefix
+ exact validated current user message
```

Its existing behavior is unchanged:

- disabled: no result or mutation,
- dry-run-only: request-local candidate only,
- actual apply: replace only for an exact `applied` result,
- non-applied explicit actual apply: block before backend forwarding,
- explicit `pass_through`: exempt and unchanged,
- active tool transaction: blocked.

## Instruction-bearing apply

`client_history_exclusion_apply.v1` supports bounded instruction-bearing managed requests only when explicit instruction provenance is present.

The reserved request-local control envelope is:

```json
{
  "relaylm": {
    "instruction_evidence": {
      "schema_version": "client_instruction_source.v1",
      "message_indices": [0]
    }
  }
}
```

The selected indices must be strictly increasing, non-duplicated, in range, point to `system` or `developer` messages before the current user turn, and match the request-local instruction identity.

Role, content, and position alone are not accepted as provenance. Missing or invalid provenance blocks actual apply. This prevents frontend summaries, frontend memory notes, and replayed persona blocks from being silently promoted merely because a frontend encoded them with `system` or `developer` role.

A successful v1 candidate contains:

```text
one RelayLM-owned compiled system message containing:
  approved runtime/profile/context blocks
  + one bounded escaped low-trust instruction-evidence block

+ exact validated current user message
```

The backend candidate excludes:

- prior client user/assistant history,
- raw client instruction message objects,
- unselected system/developer candidates,
- the reserved top-level `relaylm` control envelope,
- opaque instruction-cache entry content.

The evidence builder keeps raw typed canonical JSON. The managed compiler renderer performs escaping and enforces the rendered-size bound immediately before final render.

## Fail-closed and diagnostics posture

Actual managed apply requires an exact typed `applied` result. For v1, the payload presented to the adapter must exactly equal the selected request-local candidate; downstream mutation causes backend blocking.

Active tool transactions remain blocked because minimum-chain reconstruction is not implemented.

Runtime-private candidates may contain content. Persisted trace, audit, public errors, and node-result projections expose only bounded counts, booleans, status values, source mode, and reason IDs. Source indices, instruction text, hashes, cache bodies, and payload candidates are not persisted.

## Not yet implemented

The runtime does not yet provide:

- cache-hit RelaySCN projection,
- typed client-instruction response parsing or cache write,
- complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy,
- active tool-chain reconstruction,
- Stream Unpack and TTS-safe segmentation,
- dedicated output-side RelayREF and complete output-side RelaySCN,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution.

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

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Authority Contract](architecture/client_history_authority_contract.md)
- [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md)
- [Phase 5-C4a implementation handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Runtime Compile Current / Target Boundary](contracts/runtime_compile_current_target.md)
- [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page whenever a boundary moves between design, dry-run, read-only, and apply; a default changes; a supported request shape changes; or a current schema/producer/consumer changes. Later sequencing belongs in the implementation plan.
