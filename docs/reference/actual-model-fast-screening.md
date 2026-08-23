# Actual-model Fast Screening

Status: current #1386 owner-local screening policy for RelayLM 1.0.

Current authority is **two-pass reference qualification first**. Historical topology-winner A/B/C plans remain immutable evidence for their exact old question but do not define current execution order.

## Purpose

Fast screening narrows which already-valid actual-model conditions are worth executing. It does not redefine #1533 cognition semantics, provider capability truth, deterministic acceptance, quality labels or #1388 defaults.

For Core 1.0 the screening question is:

> Can the exact current two-pass release path achieve sufficient conversation and semantic quality at the lowest effective execution effort?

It is **not**:

> Should single-pass or two-pass win before either has an established reference quality?

## Stage order

The currently frozen historical vLLM plan contains:

```text
A: single_pass, reasoning off
B: two_pass, Pass 1 off / Pass 2 off
C: two_pass, Pass 1 unchanged / Pass 2 bounded reasoning
```

Current screening uses only the two-pass conditions for Core 1.0 qualification:

```text
Stage R0 — two-pass reference baseline
  B: canonical two_pass
     Pass 1 reasoning off
     Pass 2 reasoning off
       |
       +--> Pass 1 conversation quality insufficient
       |      -> stop and classify the Pass 1/model/prompt defect
       |
       +--> Pass 1 sufficient + Pass 2 semantic quality sufficient
       |      -> reference condition survives; do not add reasoning
       |
       +--> Pass 1 sufficient + Pass 2 semantic quality insufficient
              -> Stage R1 may execute C

Stage R1 — Pass 2-only escalation when justified
  C: canonical two_pass
     Pass 1 identical to B
     Pass 2 uses the already-attested bounded condition
```

The historical single-pass condition A is not returned by current Core 1.0 reference-screening helpers.

A later post-reference optimization transaction may explicitly reuse or replace a single-pass condition, but only to compare it against a qualified two-pass reference.

## Current helper semantics

`reference_screening_condition_ids(plan)` returns only the two-pass no-reasoning baseline condition `B` after validating that it is actually a two-pass Pass1/Pas2 OFF/OFF condition.

`reasoning_escalation_condition_ids(plan, pass2_semantic_quality_sufficient=...)` returns:

- no condition when Pass 2 semantic quality is sufficient;
- only `C` when Pass 2 semantic quality is insufficient and C preserves Pass 1 while escalating only Pass 2 reasoning.

There is no current `topology_screening_condition_ids()` API because topology winner-selection is not the Core 1.0 first-stage policy.

## Quality decision inputs

The boolean used to decide whether Stage R1 is justified must come from current #1386 quality evidence, not from JSON parse success alone.

Pass 2 semantic sufficiency includes the applicable current rubric/evidence for:

- proposal precision/recall;
- grounding;
- source/subject attribution;
- assistant-to-user contamination;
- correction/negation/uncertainty behavior;
- transient/durable discipline;
- no-op/churn behavior;
- protocol failure rate.

Pass 1 conversation quality is evaluated independently and must not be hidden by strengthening Pass 2.

## Performance evidence

Fast screening may record timing during the same provider execution used for product-quality evidence.

Timing observation is transport-only and must not modify prompts, pass requests, model outputs, proposals or deterministic decisions.

Each provider-call observation can record:

- phase: `single_pass`, `pass1`, or `pass2`;
- provider-call duration;
- first-visible latency only when a real streaming delta is observed;
- completed/failed outcome.

The `single_pass` phase remains representable for later optimization evidence; its presence in the timing type does not make single-pass a Core 1.0 qualification condition.

For the two-pass reference:

- Pass 1 timing is the visible response-generation phase;
- Pass 2 timing is semantic extraction;
- scenario end-to-end / turn-settle timing remains distinct from provider-call duration.

Buffered execution must not invent TTFT.

## Citable timing sidecars

When timing sidecars are produced, they must bind to the exact screening condition and existing actual-model execution identity, including run/execution IDs, replicate identity, scenario identity, resolved execution mode and per-turn phase timing.

A consumer that projects timing-derived observations into a citable host summary must reconstruct the canonical timing artifact, recompute its content-derived `timing_id`, and require that identity plus the sidecar `run_id` and `scenario_id` to match the timing identity retained by the host result before deriving provider-failure counts. A parseable timing JSON object or canonical-looking run ID alone is not sufficient summary evidence.

Timing sidecars do not alter raw execution evidence, deterministic-boundary verdicts or product-quality reviews.

## Historical plan handling

The historical A/B/C artifact remains loadable and immutable. Current code may use B/C from that artifact when their exact current-wire/capability identity is still valid.

Do not:

- rewrite the historical artifact to pretend A never existed;
- infer current execution order from the artifact's A/B/C names;
- execute A merely because it is present;
- cite an old serialized footprint after a prompt/wire/runtime change invalidates exact capacity identity.

The current execution plan comes from #1533, #1386 and this contract.

## Calibration relationship

#1388 consumes only a #1386-qualified two-pass reference for Core 1.0 calibration.

Reasoning is an escalation mechanism, not a default sweep dimension. Fine-grained capacity/profile calibration follows reference qualification.

If the qualified two-pass path has unacceptable latency/resource behavior, first investigate two-pass-preserving execution-engine tuning. Single-pass becomes relevant only as a later explicit optimization candidate against the frozen reference.

## Non-goals

- single-pass versus two-pass winner-selection before Core 1.0 reference qualification;
- reasoning sweeps without demonstrated semantic need;
- treating timing as a weighted quality score;
- provider/model parameter combinations whose effective behavior is unverified;
- changing deterministic State/Continuity semantics to make a model condition pass.

## Principle

> Qualify the two-pass product first. Escalate only the deficient pass, and optimize architecture only after a reference exists.
