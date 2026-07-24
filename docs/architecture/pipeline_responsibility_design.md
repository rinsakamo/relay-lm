---
relaylm_doc_type: system_architecture
relaylm_authority: transitional_pipeline_responsibility_current_implementation_note
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - current pipeline compatibility names or implemented stage posture changes
  - the D2-B2b consumer migration and removal gate closes
relaylm_not_authoritative_for:
  - canonical RelayLM system context
  - canonical component responsibility or target stage order
  - exact schemas, fields, defaults, or state machines
  - repository-wide current implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - system-overview.md
  - pipeline-responsibilities.md
  - runtime/request-response-pipeline.md
  - runtime/compile-and-checkpoint.md
relaylm_related_contracts:
  - ../contracts/pipeline_node_result_contract.md
  - ../contracts/relayctx_short_term_runtime_contract.md
---
# Transitional Pipeline Responsibility Implementation Note

## Status

This path is a closed transitional current-implementation note retained for the broad existing documentation consumer set. Canonical system context is [RelayLM System Overview](system-overview.md), canonical component ownership and target order are [Pipeline Responsibilities](pipeline-responsibilities.md), and mode-specific dataflow is [Request / Response Pipeline](runtime/request-response-pipeline.md).

This page no longer owns the canonical target order or component responsibility model. It must not gain new consumers. Its owner, current consumer class, removal gate, and replacement validation are registered in `records/documentation/transitional-assets.json`.

## Current implementation posture

The current runtime already uses the following responsibility vocabulary across code, diagnostics, contracts, tests, and documentation:

```text
RelayRUN
PipelineContext
RelayREL
RelaySCN
RelayEMO
RelayINT
RelayMEM Retrieval
RelayCTX Repack / Unpack
Runtime Compile Gate
Main LLM / backend
RelayREF
RelaySLP
adapters
```

Current implementation remains mixed in posture:

- some component handoffs are wired and current;
- some target artifacts remain default-off, dry-run, shadow, preflight, or diagnostics-only;
- some diagnostics and scripts retain compatibility or milestone-oriented node names;
- the complete target order must not be inferred from one legacy node label or one target artifact name;
- current completion remains owned by Project Status, code, implemented schema/version, and focused validation.

## Current compatibility boundary

Existing documents may continue to link this path only until D2-B2b migrates them to the smallest owning canonical authority:

- system context -> `system-overview.md`;
- component ownership and target order -> `pipeline-responsibilities.md`;
- mode-specific timing, streaming, finalization, correction, and pass-through -> `runtime/request-response-pipeline.md`;
- compile, fallback, checkpoint, resume, and recovery responsibility -> `runtime/compile-and-checkpoint.md` and its contracts;
- domain-specific semantics -> the owning relationship, scene, emotion, context, memory, attention, voice, or UI authority.

The old path is not a fallback semantic authority. If canonical documents disagree with this transitional summary, the canonical documents and exact contracts govern.

## RelayCTX Repack current-order ownership

The exact current RelayCTX Repack mutation order and final token-budget gate now belong only to the [RelayCTX Short-Term Runtime Contract](../contracts/relayctx_short_term_runtime_contract.md#current-runtime-position-and-stage-ordering). This transitional path no longer provides an ordering anchor or restates that rule.

## Stable current safeguards

- semantic components and runtime orchestration remain separate;
- RelayINT precedes an authorized action, RelayREF follows generated output, and RelaySLP runs after the current answer;
- RelayMEM Retrieval is read-only in the interactive path;
- RelayCTX owns context construction, not scene, intent, relationship, or memory meaning;
- RelayRUN records and coordinates execution without becoming a semantic component;
- adapters own protocol and transport, not persona or memory policy;
- content-bearing runtime data is not copied into generic content-free diagnostics;
- user-visible text uses the normal output and transport boundary.

Exact canonical component ownership and target order are defined only by the canonical pipeline page.

## Removal gate

Delete this path after every current consumer links directly to `system-overview.md`, `pipeline-responsibilities.md`, `runtime/request-response-pipeline.md`, `runtime/compile-and-checkpoint.md`, or the owning domain authority; generic authority and link validation are green; and the retirement manifest records this path. Historical wording remains recoverable through Git.
