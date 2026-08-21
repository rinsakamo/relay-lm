# Actual-model Fast Screening

Status: #1386 owner-local screening policy for RelayLM v1.

This contract narrows which already-valid actual-model conditions are worth executing. It does not redefine cognition execution, provider reasoning semantics, quality labels, deterministic acceptance, or calibration defaults.

## Stage order

The first screening question is execution topology, not a parameter sweep.

```text
Stage 1
  A: canonical single_pass, reasoning off
  B: canonical two_pass, Pass 1 off / Pass 2 off
        |
        +--> structured semantic quality sufficient
        |      -> stop reasoning expansion
        |
        +--> structured semantic quality insufficient
               -> Stage 2 may run C

Stage 2
  C: canonical two_pass with Pass 1 unchanged
     and only Pass 2 reasoning escalated to the frozen effective condition
```

`topology_screening_condition_ids()` therefore returns only `A` and `B`.
`reasoning_escalation_condition_ids()` returns no condition when structured semantic quality is sufficient, and returns only `C` when it is insufficient.

The historical canonical vLLM A/B/C plan remains loadable evidence. Fast screening controls execution order; it does not rewrite that historical artifact.

## Performance evidence

Fast screening records response/per-pass timing during the same provider execution used for product-quality evidence.

The recorder is transport-only. It does not modify prompts, pass requests, model outputs, State/Continuity candidates, or deterministic decisions.

Each provider-call observation records:

- phase: `single_pass`, `pass1`, or `pass2`;
- provider-call duration in milliseconds;
- first-visible response latency when an actual streaming delta is observed;
- completed/failed outcome.

Buffered execution does not invent TTFT: `first_visible_ms` remains absent. For two-pass execution, Pass 1 timing is the visible response-generation phase and Pass 2 timing is the structured extraction phase.

These values are independent evidence axes. They are not a weighted score and cannot override deterministic-authority or required semantic-quality gates.

## Citable timing sidecar

`FastScreeningTimingArtifact` binds performance observations to the exact screening condition and the existing actual-model execution identity:

- screening ID and condition ID;
- replicate ID;
- scenario ID;
- execution ID and run ID;
- resolved execution mode;
- scenario end-to-end elapsed time;
- per-turn response-provider time;
- per-turn first-visible provider latency when observed;
- per-turn Pass 2 extraction-provider time for `two_pass`.

The sidecar keeps provider-phase timing separate from scenario end-to-end elapsed time. Provider durations are not misrepresented as total RelayLM turn latency.

Artifacts are written under `screening_timing/<run_id>.json`. Rewriting identical bytes is idempotent. Different timing evidence for the same run ID is rejected; a genuine rerun must use a distinct replicate identity.

Timing sidecars do not change the immutable raw execution evidence, deterministic-boundary verdict, or product-quality review sidecars.

## Calibration relationship

#1388 consumes only surviving execution conditions. Reasoning is an escalation mechanism, not a default calibration axis. Fine-grained cognitive-budget/profile calibration follows topology screening rather than preceding it.

The target is a stable low-cost operating region across representative supported model classes, not an exact breakpoint optimized for one model artifact.
