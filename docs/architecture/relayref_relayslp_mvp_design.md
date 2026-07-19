# Compatibility pointer: RelayREF / RelaySLP MVP Design

The pre-RelayINT combined RelayREF / RelaySLP design remains in the [historical architecture archive](archive/relayref_relayslp_mvp_design.md).

It is not current authority for RelayREF, RelaySLP timing, runtime scheduling, or Subjective MEM formation.

Current architecture fixes the timing boundary as:

```text
RelayINT = before action
RelayREF = after the generated response exists
RelaySLP = out of band after the current user-visible answer
```

The ordinary managed conversation path uses one Main LLM response-generation call. Shared Assessment and Subjective MEM formation run later through RelaySLP, preferably across an episode or bounded related-evidence group. Additional adjudication is an optional RelaySLP exception and never blocks the interactive response.

Use these current documents:

- [ADR 0004: Single-call interactive runtime and deferred subjective formation](../adr/0004-single-call-interactive-runtime-deferred-formation.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Runtime Dataflow Modes](runtime_dataflow_modes.md)
- [RelayREF Output Observation Design](relayref_output_observation_design.md)
- [RelayRUN Resource Scheduling Design](relayrun_resource_scheduling_design.md)
- [Subjective MEM Deferred Formation Design](subjective_mem_deferred_formation_design.md)
- [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md)
- [RelayRUN Runtime Checkpoint Design](relayrun_runtime_checkpoint_design.md)
- [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md)
- [RelayEMO MVP Initial Design](relayemo_mvp_initial_design.md)
