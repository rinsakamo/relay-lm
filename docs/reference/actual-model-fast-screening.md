# Actual-model Fast Screening

Status: current #1386 owner-local screening policy for RelayLM 1.0.

Current authority is **two-pass reference qualification first**. Historical topology-winner A/B/C plans remain immutable evidence for their exact old question but do not define current plan structure, execution order, or operator vocabulary.

## Purpose

Fast screening narrows which already-valid actual-model conditions are worth executing. It does not redefine #1533 cognition semantics, provider capability truth, deterministic acceptance, quality labels or #1388 defaults.

For Core 1.0 the screening question is:

> Can the exact current two-pass release path achieve sufficient conversation and semantic quality at the lowest effective execution effort?

It is **not** a pre-reference single-pass-versus-two-pass winner selection.

## Current Stage R roles

Current policy and the current canonical screening plan expose semantic roles directly:

```text
reference_baseline
  two_pass
  Pass 1 reasoning off
  Pass 2 reasoning off
    |
    +--> Pass 1 conversation quality insufficient
    |      -> stop and classify the Pass 1/model/prompt defect
    |
    +--> Pass 1 sufficient + Pass 2 semantic quality sufficient
    |      -> reference survives; do not add reasoning
    |
    +--> Pass 1 sufficient + Pass 2 semantic quality insufficient
           -> pass2_reasoning_escalation may be executed

pass2_reasoning_escalation
  two_pass
  Pass 1 identical to reference_baseline
  Pass 2 uses the already-attested non-OFF reasoning condition
```

The current shared vLLM host CLI accepts those same role names. For the current plan, a role resolves directly to the identically named plan key; there is no A/B/C translation step.

The current canonical plan contains only those two two-pass roles. It does not retain a single-pass A condition merely for historical symmetry.

Existing capacity/timing/run artifacts keep their immutable payload `condition_id` values. In particular, changing the current plan key from historical `B` to `reference_baseline` does not rewrite or invalidate an artifact whose citable identity is the unchanged underlying condition ID plus its exact target/request/scenario/runtime identity.

## Current helper semantics

`reference_screening_condition_roles(plan)` validates that the plan contains exactly one two-pass Pass 1 OFF / Pass 2 OFF reference and returns `reference_baseline`.

`reasoning_escalation_condition_roles(plan, pass2_semantic_quality_sufficient=...)` returns:

- no role when Pass 2 semantic quality is sufficient;
- `pass2_reasoning_escalation` only when there is exactly one two-pass condition that preserves the reference Pass 1 and unrelated Pass 2 decoding controls while using non-OFF Pass 2 reasoning.

`screening_condition_key_for_role(plan, role)` has two bounded behaviors:

- for current semantic-plan format v2, it resolves directly to the role key itself;
- for immutable historical format v1, it remains the compatibility adapter that identifies the corresponding A/B/C coordinate from condition semantics.

Current policy callers therefore do not need to know historical coordinates. Historical evidence can still be replayed without turning those coordinates back into current product vocabulary.

There is no current topology-winner helper because topology winner-selection is not the Core 1.0 first-stage policy.

## Quality decision inputs

The boolean used to decide whether Pass 2 escalation is justified must come from current #1386 quality evidence, not from JSON parse success alone.

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

The `single_pass` timing phase remains representable for historical/later optimization evidence; its presence in the timing type does not make single-pass a Core 1.0 qualification role or a current-plan condition.

For the two-pass reference:

- Pass 1 timing is the visible response-generation phase;
- Pass 2 timing is semantic extraction;
- scenario end-to-end / turn-settle timing remains distinct from provider-call duration.

Buffered execution must not invent TTFT.

## Citable timing sidecars

When timing sidecars are produced, they bind to the exact underlying screening condition and existing actual-model execution identity, including run/execution IDs, replicate identity, scenario identity, resolved execution mode and per-turn phase timing.

A current operator-facing semantic role does not rewrite citable evidence identity. A consumer projecting timing-derived observations must reconstruct the canonical timing artifact, recompute its content-derived `timing_id`, and require that identity plus the sidecar `run_id` and `scenario_id` to match the timing identity retained by the host result before deriving provider-failure counts.

Timing sidecars do not alter raw execution evidence, deterministic-boundary verdicts or product-quality reviews.

## Historical plan handling

Format v1 is the historical A/B/C compatibility format. The frozen `cogp5-vllm-screening-v1.json` artifact remains loadable and immutable. The semantic resolver identifies its two-pass OFF/OFF and Pass-2-only escalation coordinates without promoting `B` or `C` into current policy.

Format v2 is the current semantic plan format. It requires exactly `reference_baseline` followed by `pass2_reasoning_escalation`; both are two-pass in the current canonical plan. Historical single-pass A remains available only through historical evidence or a later separately governed optimization transaction.

Do not:

- rewrite historical artifacts merely to rename coordinates;
- rename existing evidence payload `condition_id` values;
- infer current execution order from A/B/C names;
- execute a single-pass condition merely because it is present historically;
- reintroduce A/B/C keys into a current format-v2 plan;
- cite an old serialized footprint after a prompt/wire/runtime change invalidates exact capacity identity.

The current execution plan comes from #1533, #1386 and this contract.

## Pilot capacity boundary

The current Stage R0 plan still cites the measured effective context window and capacity artifact required to execute that exact pilot trajectory. Those values are **pilot evidence inputs**, not release defaults or #1388 calibration outputs.

Moving from format v1 coordinates to semantic format v2 does not remeasure capacity: the reference condition retains the same immutable `condition_id` and exact pass requests, so the existing capacity artifact remains valid under the normal compatibility checks.

## Calibration relationship

#1388 consumes only a #1386-qualified two-pass reference for Core 1.0 calibration.

Reasoning is an escalation mechanism, not a default sweep dimension. Fine-grained capacity/profile calibration follows reference qualification.

If the qualified two-pass path has unacceptable latency/resource behavior, first investigate two-pass-preserving execution-engine tuning. Single-pass becomes relevant only as a later explicit optimization candidate against the frozen reference.

## Non-goals

- single-pass versus two-pass winner-selection before Core 1.0 reference qualification;
- reasoning sweeps without demonstrated semantic need;
- rewriting immutable evidence identity to improve naming;
- treating Stage R0 capacity as a release/default value;
- treating timing as a weighted quality score;
- provider/model parameter combinations whose effective behavior is unverified;
- changing deterministic State/Continuity semantics to make a model condition pass.

## Principle

> Qualify the two-pass product first. Name current decisions by semantic role; keep historical evidence identity historical.
