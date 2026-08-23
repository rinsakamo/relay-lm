# Actual-model vLLM capacity acquisition

Status: current #1386 producer contract for real serialized-input capacity footprints on the exact vLLM production trajectory.

Capacity acquisition is separate from product-quality qualification and #1388 calibration. It measures demand; it does not choose a context window, output reserve, runtime profile or default.

## Current Core 1.0 condition policy

The historical frozen plan may contain conditions A/B/C. Current Core 1.0 authority uses:

```text
B
  two_pass reference baseline
  Pass 1 off / Pass 2 off

C
  two_pass Pass 2 escalation
  only when #1386 shows B has sufficient Pass 1 quality
  but insufficient Pass 2 semantic quality

A
  historical / optional later single-pass optimization
  not a current capacity prerequisite merely because it exists
```

Capacity acquisition operates on one explicitly selected condition at a time. It does not decide which condition is authorized; current #1386 screening authority does.

## Responsibility

The acquisition path measures the real production serializer/trajectory:

```text
selected condition + scenario
  -> real ordinary-turn trajectory
  -> canonical provider request realization
  -> exact serving-tokenizer count immediately before delegation
  -> real provider delegation
  -> content-free footprint observation
  -> immutable amcap artifact
```

`VLLMCapacityMeasurementProvider` is a measurement proxy only. It never reconstructs prompts itself.

Single-pass counting, where explicitly used for historical/optimization evidence, continues through the canonical single-pass serializer. Two-pass counting uses the canonical Pass 1 / Pass 2 serializers.

## Exact trajectory rule

Capacity evidence is dynamic trajectory evidence, not a static prompt estimate.

For two-pass execution:

1. Pass 1 is counted from the actual runtime `CognitiveInput`;
2. the real Pass 1 response is generated;
3. Pass 2 is counted from the exact extraction input containing that response;
4. accepted State/Continuity affects later evaluated turns through normal runtime semantics.

Placeholder Pass 1 responses, synthetic State, reconstructed later context or language-level prompt approximations are not citable capacity evidence.

If a later explicit single-pass optimization is measured, each turn is counted from its exact single-pass `CognitiveInput` and current production combined-IR request.

## Model-runner trajectory identity

Current capacity artifacts use format version 3 and include an explicit
`model_runner` identity, currently `v1` or `v2`. The acquisition producer
requires this resolved identity from the exact runtime path; it does not infer
it from an unset `VLLM_USE_V2_MODEL_RUNNER` environment variable. The host
preparation gate compares the expected execution runner with the cited
artifact runner and rejects mismatches or omitted identities before repository,
snapshot, or provider preparation.

Format-version-2 artifacts remain strictly loadable for historical inspection,
but their omitted runner identity cannot authorize current Stage R0 screening.
The WSL pinned-memory setting remains a runtime prerequisite for a supported
V2 environment and is not promoted to model-output identity by this contract.

## Count-before-delegate ordering

For every reached provider call:

```text
validate exact selected pass request
  -> exact serialized-input count
  -> append footprint observation
  -> delegate to real provider
```

If provider generation later fails, a successfully completed exact count remains partial footprint evidence.

No observation is fabricated for a provider call that was never reached or for a failed count.

## Coverage identity

Each `VLLMCapacityFootprintObservation` records content-free identity including:

- canonical condition ID;
- topology;
- pass ID;
- scenario ID;
- one-based turn index;
- exact `amcpr-<sha256>` resolved pass-request identity;
- total serialized-input tokens;
- framing tokens;
- exact/conservative count mode.

No prompt text, response text, State/Continuity values, Event/MEMORY content, provider URL or secret is stored in the footprint observation.

## Preparation

`prepare_vllm_capacity_acquisition(...)` does not require pre-existing capacity evidence; doing so would be circular.

Preparation binds current facts directly, including as applicable:

1. exact clean requested RelayLM commit;
2. frozen vLLM repository target and verified local snapshot;
3. fresh live backend/model identity combined with current frozen reasoning proof;
4. live `model_root` agreement;
5. observed live `max_model_len`;
6. exact `VLLMServingTokenizerCounter` identity;
7. canonical scenario set;
8. the explicitly selected condition and exact pass requests;
9. canonical provider construction;
10. matching run manifest/binding identity.

The historical plan's diagnostic context-window values do not become current acquisition authority.

## Current selected-condition requirements

Core 1.0 capacity work should acquire only evidence needed for the currently authorized two-pass condition.

- For B: acquire complete B Pass 1 and B Pass 2 coverage over the selected reference scenarios/turns.
- For C: acquire complete C Pass 1 and C Pass 2 coverage only after current #1386 authority justifies Pass 2 escalation.
- Do not acquire A as a prerequisite to B/C. A is measured later only if an explicit single-pass optimization comparison is authorized.

The technical host may retain ability to replay historical condition IDs. Technical availability does not determine current evaluation order.

## Complete and partial artifacts

`execute_vllm_capacity_acquisition(...)` runs one selected condition serially across its frozen scenarios.

On success, reached observations are assembled into immutable `VLLMRuntimeCapacityEvidence` and checked against exact selected-condition coverage.

If execution fails after at least one exact observation was recorded, the producer may write an immutable partial artifact containing only reached observations and return/raise the bounded acquisition failure receipt defined by current code.

Partial evidence is citable for the footprints actually observed but does not authorize product screening when required selected-condition coverage is incomplete.

If no exact observation exists, no empty/fabricated artifact is written.

A generic provider failure is not automatically classified as input-context overflow; that requires the corresponding independent evidence.

## Host facade

The shared host facade exposes vLLM product screening and capacity acquisition as distinct operations.

A capacity invocation accepts one explicitly selected condition; there is no `all` mode or Cartesian parameter search.

For Core 1.0 current authority, the planner should select B first and C only if justified. A may remain technically replayable but is not automatically executed.

A capacity receipt identifies operation/condition/RelayLM commit/target/replicate/live capacity and the resulting capacity-evidence receipt without emitting semantic payload or a product-quality score.

The vLLM facade requires an explicit `--model-runner v1|v2` for both capacity
acquisition and screening preparation.

LM Studio and vLLM runs remain serial rather than simultaneous.

## Relationship to product-quality evidence

Capacity completion only establishes input-demand evidence for the selected trajectory. It does not establish:

- Pass 1 conversation quality;
- Pass 2 semantic quality;
- reasoning necessity;
- output headroom sufficiency;
- release defaults.

After complete selected-condition capacity evidence exists, #1386 may execute the matching quality condition when current screening authority allows it. #1388 later interprets qualified quality + capacity evidence.

## Relationship to reasoning

Do not repeat reasoning parameter exploration merely because capacity acquisition invokes a reasoning-bearing condition.

The selected request must already be valid under current provider/model capability authority.

C is not acquired/run until Pass 2 escalation is justified by B quality evidence. Larger bounded budgets or effort labels are not added unless a separate current evidence question requires them.

## Immutability / provenance

Capacity artifacts remain content-addressed and immutable. Identical rewrites may be idempotent; conflicting same-ID bytes are rejected.

Measurement commit is provenance, not a release default. Later code may cite a reviewed artifact only if all semantic identity that can affect the footprint remains compatible under the current capacity-validation contract.

## Deliberate boundary

This producer does not:

- select a numeric context window, output reserve, profile or default;
- modify #1387 degradation semantics;
- choose single-pass versus two-pass;
- authorize C without #1386 semantic need;
- add A merely for topology symmetry;
- repeat backend reasoning experiments;
- tune prompts/fixtures/model output;
- persist product-quality review as capacity evidence;
- run LM Studio and vLLM simultaneously.

## Principle

> Measure only the exact trajectory that current authority has selected; historical condition availability is not a reason to execute it.
