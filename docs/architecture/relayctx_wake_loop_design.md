# Archived: RelayCTX Wake Loop Design

The pre-RelayINT Wake-loop source has been retired from the live documentation tree after its durable context-selection principles were absorbed into current RelayCTX architecture and contracts. Its exact historical text remains recoverable from Git history.

The retired source assigned reference resolution and response-mode selection to RelayCTX and Wake-time recovery to RelayREF. Those responsibilities no longer define the current architecture.

Use these current authorities instead:

- [Pipeline Responsibilities](pipeline-responsibilities.md) for component ownership and stage ordering
- [RelayCTX Context Assembly](context/context-assembly.md) for working-state selection, smallest-sufficient packing, and backend context assembly
- [RelayCTX Short-Term Runtime Contract](../contracts/relayctx_short_term_runtime_contract.md) for exact current short-term runtime behavior
- [RelayINT MVP design](relayint_mvp_design.md) for current reference/clarification responsibility
- [Request / Response Pipeline](runtime/request-response-pipeline.md) for current managed-route and recovery-side runtime boundaries

This redirect is compatibility-only and does not define current implementation status or semantic authority.
