# Compatibility pointer: RelayREF / RelaySLP MVP Design

The pre-RelayINT combined RelayREF / RelaySLP source has been retired from the live documentation tree. Its exact historical text remains recoverable from Git history and is not current authority.

Current architecture fixes the timing boundary as:

```text
RelayINT = before action
RelayREF = response-complete observation after generated output exists
RelaySLP = out of band after the current user-visible answer
```

Use these current documents:

- [ADR 0004: Single-response-call ordinary conversation and deferred subjective formation](../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md)
- [Pipeline Responsibilities](pipeline-responsibilities.md)
- [Request / Response Pipeline](runtime/request-response-pipeline.md)
- [Runtime Scheduler](runtime/scheduler.md)
- [Subjective Memory Formation](memory/formation.md)
- [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md)
- [Runtime Compile and Checkpoint Architecture](runtime/compile-and-checkpoint.md)
- [RelayRUN Checkpoint and Recovery Contract](../contracts/relayrun-checkpoint-and-recovery.md)
- [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md)
- [RelayEMO MVP Initial Design](../relayemo_mvp_initial_design.md)

This redirect is compatibility-only and does not define RelayREF, RelaySLP, recovery, scheduling, or Subjective MEM semantics.
