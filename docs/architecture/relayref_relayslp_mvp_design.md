# Archived: RelayREF / RelaySLP MVP Design

This pre-RelayINT responsibility design has moved to the [historical architecture archive](archive/relayref_relayslp_mvp_design.md).

It remains useful for recovery UX and early simulation rationale, but it is not the current RelayREF specification.

Current architecture fixes the boundary as:

```text
RelayINT = before action
RelayREF = after response
```

Wake-time ambiguity, clarification, scene recovery, and runtime recovery orchestration are now split across RelayINT, RelaySCN, and RelayRUN. RelaySLP remains the out-of-band memory / SOUL compilation path.

Use these current documents instead:

- [Pipeline responsibility design](pipeline_responsibility_design.md)
- [Pipeline implementation plan](pipeline_implementation_plan.md)
- [RelayINT MVP design](relayint_mvp_design.md)
- [RelaySCN MVP scene policy](relayscn_mvp_scene_policy.md)
- [RelayRUN runtime checkpoint design](../relayrun_runtime_checkpoint_design.md)
- [RelayMEM SLP execution design](relaymem_slp_execution_design.md)
