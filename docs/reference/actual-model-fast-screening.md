# Actual-model Fast Screening

Status: current #1386 owner-local screening policy for RelayLM 1.0.

Current authority is **two-pass reference qualification first**. Historical topology-winner A/B/C plans remain immutable evidence for their exact old question but do not define current execution order or operator vocabulary.

## Purpose

Fast screening narrows which already-valid actual-model conditions are worth executing. It does not redefine #1533 cognition semantics, provider capability truth, deterministic acceptance, quality labels or #1388 defaults.

For Core 1.0 the screening question is:

> Can the exact current two-pass release path achieve sufficient conversation and semantic quality at the lowest effective execution effort?

It is **not** a pre-reference single-pass-versus-two-pass winner selection.

## Current Stage R roles

Current policy exposes semantic roles rather than historical artifact coordinates:

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

The current shared vLLM host CLI accepts those role names. It resolves a role to the loaded immutable screening-plan coordinate only at the evidence boundary.

Historical plan keys such as `A`, `B`, and `C` are therefore transport/evidence coordinates, not current product semantics. Existing capacity/timing/run artifacts keep their original payload `condition_id` values and remain citable for the exact identity they measured.

## Current helper semantics

`reference_screening_condition_roles(plan)` validates that the plan contains exactly one two-pass Pass 1 OFF / Pass 2 OFF reference and returns `reference_baseline`.

`reasoning_escalation_condition_roles(plan, pass2_semantic_quality_sufficient=...)` returns:

- no role when Pass 2 semantic quality is sufficient;
- `pass2_reasoning_escalation` only when there is exactly one two-pass condition that preserves the reference Pass 1 and unrelated Pass 2 decoding controls while using non-OFF Pass 2 reasoning.

`screening_condition_key_for_role(plan, role)` is the bounded adapter that maps those semantic roles back to the immutable plan coordinate used by existing host/capacity/evidence machinery.

The resolver does not require current policy callers to know whether an underlying historical artifact named those coordinates `B` and `C`.

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

The `single_pass` timing phase remains representable for later optimization evidence; its presence in the timing type does not make single-pass a Core 1.0 qualification role.

For the two-pass reference:

- Pass 1 timing is the visible response-generation phase;
- Pass 2 timing is semantic extraction;
- scenario end-to-end / turn-settle timing remains distinct from provider-call duration.

Buffered execution must not invent TTFT.

## Citable timing sidecars

When timing sidecars are produced, they bind to the exact underlying screening condition and existing actual-model execution identity, including run/execution IDs, replicate identity, scenario identity, resolved execution mode and per-turn phase timing.

A current operator-facing semantic role does not rewrite that historical/citable evidence identity. A consumer projecting timing-derived observations must reconstruct the canonical timing artifact, recompute its content-derived `timing_id`, and require that identity plus the sidecar `run_id` and `scenario_id` to match the timing identity retained by the host result before deriving provider-failure counts.

Timing sidecars do not alter raw execution evidence, deterministic-boundary verdicts or product-quality reviews.

## Historical plan handling

The frozen A/B/C artifact remains loadable and immutable. For the currently cited artifact, the semantic resolver identifies its two-pass OFF/OFF and Pass-2-only escalation coordinates without promoting the names `B` or `C` into current policy.

Do not:

- rewrite historical artifacts merely to rename coordinates;
- rename existing evidence payload `condition_id` values;
- infer current execution order from A/B/C names;
- execute a single-pass condition merely because it is present historically;
- cite an old serialized footprint after a prompt/wire/runtime change invalidates exact capacity identity.

The current execution plan comes from #1533, #1386 and this contract.

## Calibration relationship

#1388 consumes only a #1386-qualified two-pass reference for Core 1.0 calibration.

Reasoning is an escalation mechanism, not a default sweep dimension. Fine-grained capacity/profile calibration follows reference qualification.

If the qualified two-pass path has unacceptable latency/resource behavior, first investigate two-pass-preserving execution-engine tuning. Single-pass becomes relevant only as a later explicit optimization candidate against the frozen reference.

## Non-goals

- single-pass versus two-pass winner-selection before Core 1.0 reference qualification;
- reasoning sweeps without demonstrated semantic need;
- rewriting immutable evidence identity to improve naming;
- treating timing as a weighted quality score;
- provider/model parameter combinations whose effective behavior is unverified;
- changing deterministic State/Continuity semantics to make a model condition pass.

## Principle

> Qualify the two-pass product first. Name current decisions by semantic role; keep historical evidence identity historical.
