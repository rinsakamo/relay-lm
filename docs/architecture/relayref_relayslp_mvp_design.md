# Compatibility pointer: RelayREF / RelaySLP MVP Design

The pre-RelayINT combined RelayREF / RelaySLP design remains in the [historical architecture archive](archive/relayref_relayslp_mvp_design.md).

It is not current authority for RelayREF, RelaySLP timing, runtime scheduling, or Subjective MEM formation.

Current architecture fixes the timing boundary as:

```text
RelayINT = before action
RelayREF = response-complete observation after generated output exists
RelaySLP = out of band after the current user-visible answer
```

The ordinary managed no-tool conversation path requires one Main LLM response-generation call. Streaming output does not wait for response-complete RelayREF observation. Shared Assessment and Subjective MEM formation run later through the split RelaySLP reference path, preferably across an episode or bounded related-evidence group. Additional adjudication is an optional RelaySLP exception and never blocks the interactive response.

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
