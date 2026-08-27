# Actual-model cognition execution evidence

Status: current #1386 bridge from #1533 cognition execution into reproducible actual-model evidence.

Current Core 1.0 authority is **two-pass reference qualification first**. Historical topology-comparison artifacts remain valid for their exact old question but do not define current execution order.

## Purpose

This bridge makes resolved cognition topology and per-pass requests part of actual-model run identity without duplicating provider or cognition authority.

A citable run may distinguish:

```text
two_pass
  Pass 1 request
  Pass 2 request

single_pass
  single request

shadow_two_pass
  topology identity only where current request carriage supports it
```

For Core 1.0, #1386 qualifies `two_pass` first. `single_pass` is retained for compatibility/historical replay and later optional optimization evidence.

## Historical manifest compatibility

Existing `ActualModelRunManifest` serialization remains unchanged when optional cognition fields are absent.

When `cognition_execution` is absent, no cognition-execution field is emitted. When `cognition_pass_requests` is absent, no per-pass request field is emitted. Historical run IDs therefore remain stable.

New cognition-policy evidence uses an explicit `CognitionExecutionEvidenceIdentity`, so different topologies cannot alias merely because model/provider/scenario fields are otherwise equal.

The topology execution path must equal the manifest `execution_path`; mismatches fail before model execution.

## Resolved per-pass request identity

`ActualModelCognitionPassRequests` records already-resolved `CognitionPassRequest` values. It does not resolve policy and does not prove backend application by itself.

Supported shapes are:

```text
single_pass
  single_pass = CognitionPassRequest

two_pass
  pass1 = CognitionPassRequest
  pass2 = CognitionPassRequest
```

Each request preserves:

```text
reasoning_mode
reasoning_budget
temperature
top_p
max_output_tokens
structured_output_mode
```

`structured_output_mode` is normally `null` outside Pass 2. For Pass 2 it distinguishes an explicit `plain`, `native`, or `auto` request so otherwise identical native/plain runs cannot alias in the run identity. The exact provider-effective choice for `auto` remains provider/capability evidence rather than being invented by the manifest.

Unresolved reasoning `auto` is invalid at this boundary. Pass 2 structured-output `auto` is a valid explicit transport request because its conservative capability-gated resolution occurs at the provider extraction boundary.

Changing an output-affecting Pass 1 or Pass 2 request changes run identity.

Topology and request shape must agree. Unsupported combinations fail closed rather than executing with silently omitted requests.

## Core 1.0 two-pass execution evidence

The current reference path is:

```text
Pass 1 request
  -> run_user_turn_two_pass
  -> generate_conversation
  -> raw visible response

Pass 2 request
  -> originating-turn-bound extraction
  -> structured-output transport selection
  -> generate_extraction
  -> RelayLM-owned proposal IR parse/type construction
  -> raw typed proposals
  -> deterministic State/Continuity validation
```

Pass 1 response becomes `raw_model.response`. Proposal arrays come from the actual Pass 2 output. Deterministic acceptance remains separate evidence owned by the existing validators.

The actual-model scenario harness may await canonical Pass 2 before advancing a multi-turn evaluation trajectory so the next evaluated turn observes the accepted State/Continuity result. This evaluation ordering does not change the product runtime's response-first semantics.

A persisted execution artifact is citable only when its `plan_id` matches the content-derived execution-plan identity, its ordinary or restart evidence `run_id` matches that evidence's canonical run identity, and its outer `execution_id` matches the exact plan plus validated run ID. Those individually valid identities are not sufficient: ordinary evidence must carry the plan's exact manifest and scenario, while restart evidence must carry the plan manifest as its base plus the exact scenario, restart boundary, and Continuity Runtime identity. The execution persistence boundary validates this plan/evidence binding and recomputes all three identity layers before writing an artifact.

For restart evidence, the top-level restart run identity alone is also insufficient because it is derived from the restart manifest and whole scenario rather than from the nested phase evidence objects. Before persistence, `before_restart` and `after_restart` must each carry the restart envelope's exact base manifest, the canonical phase scenario partition for the declared restart boundary, and their own canonical ordinary `run_id`. A valid phase artifact from another replicate is not citable inside the current restart envelope.

A citable product-quality review must be derived only from an execution result that passes the same canonical execution admission. Review construction validates the source plan/run/execution identities and plan-to-evidence binding before applying ratings or projecting proposal metrics; a self-consistent review ID cannot make a non-citable source execution valid review evidence.

A citable deterministic-boundary verdict must likewise be derived only after the source execution passes canonical execution admission. That admission proves source identity and ownership only; the boundary evaluator still independently checks fixture alignment, raw-proposal-to-decision coverage, and restart boundary observations, and may correctly return `fail` when those protocol invariants are violated.

## Proposal evaluator identity and Continuity lifecycle keys

Current derived proposal metrics pin `actual-model-proposal-evaluator-v2` in the review payload. Historical execution evidence, raw proposals, scenario-set identities, and already-written review/score sidecars remain immutable; re-evaluating old raw evidence under a newer evaluator therefore creates new derived review identity rather than rewriting the historical result.

State proposal matching remains exact on the fixture's canonical `state_class + key + op` identity, with exact value comparison where the label requests it.

Continuity labels use their fixture `key` as a fixture-local lifecycle identity, not as a universal lexical spelling rule. On the first expected `set` for that lifecycle, the evaluator may bind the label to a different non-empty model key only when the corresponding deterministic Continuity decision accepted that exact proposal as a new item (`accepted/admit`). Matching still requires the expected `kind + op`, plus exact value semantics when the label requests value matching. There is no fuzzy similarity, semantic aliasing, or deterministic NLU in this path.

After binding, every expected supersede or resolve transition for that lifecycle must reuse the accepted model key exactly. A later invented key therefore remains an unmatched raw proposal plus a missing expected transition. Missing expected kinds, wrong kinds/operations, duplicate or unchanged-item churn, and other extra proposals remain ordinary false negatives/false positives. A successful resolve ends that fixture-local lifecycle binding so a later genuinely new lifecycle may bind independently.

This is evaluator semantics only. It does not canonicalize producer key spelling or change Continuity runtime lifecycle behavior.

## Reference-screening order

The historical frozen vLLM plan contains conditions named A/B/C. Current Core 1.0 screening interprets them only through the current #1386 screening contract:

```text
B
  two_pass
  Pass 1 = off
  Pass 2 = off
  -> first reference qualification condition where exact OFF is attested

C
  two_pass
  Pass 1 identical to B
  Pass 2 = attested bounded condition
  -> execute only if B shows Pass 1 sufficient but Pass 2 semantic quality insufficient

A
  single_pass
  -> historical/compatibility data or later optimization candidate
  -> not a current first-stage release condition merely because it exists
```

Do not execute A as a prerequisite to qualifying B.

Do not execute C unless the current #1386 quality decision demonstrates a Pass 2 semantic need and the exact backend/model bounded control is attested.

Unsupported or ineffective parameter combinations are not screening conditions.

LM Studio and vLLM evidence runs remain serial backend executions.

## Provider application remains separate authority

Recording a `CognitionPassRequest` proves what RelayLM requested at the provider-neutral boundary. It does not prove that the backend applied the control or that the control had semantic effect.

For Pass 2, recording `structured_output_mode=native` proves the native transport was requested. Recording `auto` proves the capability-gated policy was requested; provider capability evidence and the actual external request remain the authority for whether `auto` resolved to native or plain.

Provider owners retain exact request serialization and capability truth.

For vLLM, citable reasoning comparisons require the current provider-owned attestation/realization for the exact model/backend. No `low`/`medium`/`high` label is treated as equivalent to a numeric bounded budget without explicit owner authority.

For LM Studio, model/backend-specific capability evidence remains separate; do not infer vLLM-style bounded semantics from a related model family.

## Raw model versus deterministic authority

Raw model evidence records what Pass 1 said and what Pass 2 proposed.

Deterministic evidence records what RelayLM accepted or rejected.

A Pass 2 provider/protocol failure records no fabricated proposal output and cannot reuse a previous turn's extraction.

Per-pass request identity contains no prompt, model response, State, Continuity, Event, MEMORY or secret content.

## Failure / stale evidence

Two-pass evidence must preserve terminal extraction status:

```text
committed
stale
failed
```

A valid Pass 1 response remains valid when Pass 2 is stale or failed. Such an extraction contributes no State/Continuity mutation.

Rapid-next-turn/pending extraction behavior is a required current #1386 product-quality dimension rather than a reason to force single-pass.

## Streaming boundary

Resolved per-pass evidence may only claim streaming carriage after the runtime path actually carries the same Pass 1/Pass 2 semantics.

Until that implementation is complete, a streaming manifest must fail closed rather than claim requests were applied when Turn-level carriage omitted them.

## Cognitive Budget boundary

Actual-model evidence must not fabricate two-pass total-budget diagnostics that current runtime/evidence contracts do not produce.

Where a combination of cognition-pass requests and total `CognitiveBudgetRuntimeConfig` is not implemented, the manifest/plan must fail explicitly instead of silently dropping one authority.

Capacity acquisition remains a separate #1386 evidence path and #1388 remains the only owner that interprets those observations into numeric profile/default values.

## Restart boundary

Restart evidence must carry the same resolved cognition semantics if it claims to evaluate a cognition profile across restart.

If current restart execution cannot preserve the resolved pass requests, that combination fails planning rather than executing under a different implicit policy.

## Quality separation

Reference qualification independently observes:

- Pass 1 conversation/persona/language quality;
- Pass 2 semantic precision/recall;
- grounding/source attribution;
- assistant-to-user contamination;
- correction/negation/uncertainty;
- transient/durable discipline;
- no-op/churn behavior;
- protocol validity;
- failure/stale behavior;
- timing/resource evidence where captured.

JSON parse success alone is not semantic-quality sufficiency. A native structured-output run must still be evaluated for the same semantic quality as a plain run; structural validity alone does not qualify the model.

## Later single-pass optimization

Only after a two-pass reference has been qualified may #1386 compare a single-pass candidate against it for optimization.

That comparison must preserve the same semantic fixture and explicitly report both:

```text
quality / grounding / authority regression
and
latency / token / resource benefit
```

A single-pass candidate that does not qualify is simply not adopted; it does not block Core 1.0.

A persisted multi-model cohort is citable only when its `cohort_id` matches the content-derived identity of its exact scenario-set/scenario identity, ordered member labels and manifests, and member execution IDs. The cohort persistence boundary recomputes that identity and rejects a caller-supplied mismatch before writing an artifact.

## Ownership

#1533 owns topology/pass semantics and provider-neutral request semantics, including Pass 2 structured-output transport semantics.

#1386 owns:

- manifest/run identity composition, including the exact Pass 2 structured-output request;
- raw/deterministic execution evidence;
- scenario/review/cohort/comparison methodology;
- two-pass reference qualification;
- justified Pass 2 escalation comparisons;
- later optional single-pass optimization comparisons;
- host-side evidence binding.

Provider owners retain backend capability and applied-wire truth. #1388 owns calibrated two-pass profile/default selection.

## Principle

> Evidence records the exact policy that ran; it never aliases plain and native extraction under one run identity.
