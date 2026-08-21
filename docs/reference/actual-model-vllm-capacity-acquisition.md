# Actual-model vLLM capacity acquisition

This reference defines the #1386-owned producer that acquires real serialized-input capacity footprints for the frozen vLLM screening trajectories.

It is deliberately separate from product-quality screening and from #1388 numeric calibration. The producer observes the exact inputs reached by the real production trajectory; it does not choose an `effective_context_window`, output reserve, runtime profile, or default.

## Responsibility

The acquisition path connects existing authorities rather than introducing another prompt or provider implementation:

```text
frozen screening condition + scenario
        -> real ordinary-turn trajectory
        -> canonical single/two-pass provider request realization
        -> exact serving-tokenizer count immediately before delegation
        -> real provider delegation
        -> content-free footprint observation
        -> immutable amcap artifact
```

`VLLMCapacityMeasurementProvider` is a measurement proxy only. It never serializes a prompt itself. Single-pass counting uses `OpenAICompatibleSerializedInputCounter`; two-pass counting uses `OpenAICompatibleTwoPassSerializedInputCounter`; both continue to call the same production request builders and pass-request resolver used by generation.

## Exact trajectory rule

Capacity evidence is dynamic trajectory evidence, not a static prompt estimate.

For single-pass execution, each reached turn is counted from the exact `CognitiveInput` produced by the real runtime immediately before the corresponding provider call.

For two-pass execution:

- Pass 1 is counted from the real turn `CognitiveInput`;
- the provider produces the real Pass 1 visible response;
- Pass 2 is counted from the exact extraction input containing that actual Pass 1 response;
- accepted State/Continuity results then affect later turns through the normal runtime path.

Placeholder Pass 1 responses, synthetic State, reconstructed later-turn context, or language-level prompt approximations are not citable capacity evidence.

## Count-before-delegate ordering

For every reached provider call the order is strict:

```text
validate exact selected pass request
  -> exact serialized-input count
  -> append footprint observation
  -> delegate to real provider
```

This ordering is intentional. If provider generation subsequently fails, an exact footprint already proved by the serving tokenizer remains available as partial evidence.

No observation is fabricated for a call that was never reached or for a count that did not complete successfully.

The measurement proxy also rejects topology/order drift. A selected single-pass condition cannot receive two-pass calls. In two-pass mode the next Pass 1 cannot begin until the preceding Pass 2 has completed, and Pass 2 requires exactly one preceding Pass 1 for the same turn sequence.

## Coverage identity

Each observation uses the existing #1581 content-free coverage identity:

- canonical condition ID;
- topology (`single_pass` or `two_pass`);
- pass ID (`single_pass`, `pass1`, or `pass2`);
- scenario ID;
- one-based turn index;
- exact `amcpr-<sha256>` pass-request identity;
- total serialized-input tokens;
- required input-framing tokens;
- exact/conservative count mode.

No prompt text, model response, Character State value, Continuity value, Event/MEMORY text, provider URL, or API-key material is persisted in `VLLMCapacityFootprintObservation`.

## Acquisition preparation

`prepare_vllm_capacity_acquisition(...)` is intentionally not the product-screening preparation path and does not require a previously cited capacity artifact. Requiring capacity evidence in order to produce capacity evidence would be circular.

Preparation instead verifies and binds current acquisition facts directly:

1. the repository is clean at the exact requested RelayLM commit;
2. the canonical frozen vLLM repository target is loaded and the local snapshot is verified;
3. the frozen R3B reasoning proof is rebound to fresh `/version` and `/v1/models` identity;
4. live `model_root` resolves to the verified snapshot;
5. live `max_model_len` is present and becomes the observed acquisition runtime capacity;
6. the live `VLLMServingTokenizerCounter` is constructed against that exact target/runtime;
7. the canonical scenario set and selected A/B/C condition are validated;
8. the canonical single-pass or two-pass OpenAI-compatible provider is constructed with the selected condition's explicit cognition pass requests;
9. the resulting manifest/binding uses the observed live `max_model_len` for acquisition identity.

The historical screening plan's diagnostic `effective_context_window=1024` is not promoted into acquisition authority merely because it remains in the historical plan. Acquisition records the current live runtime fact; #1388 remains responsible for later interpreting the measured demand and choosing any evidence-resolving candidate.

## Complete and partial artifacts

`execute_vllm_capacity_acquisition(...)` runs one selected condition over its frozen scenarios serially.

On complete success, all reached observations are assembled into `VLLMRuntimeCapacityEvidence`, written through the existing immutable content-addressed writer, and checked against the existing exact selected-condition coverage validator before the acquisition is reported complete.

If execution fails after one or more exact observations were recorded, the producer writes an immutable partial `amcap` artifact containing only those reached observations and raises `VLLMCapacityAcquisitionFailure` with the artifact receipt. The partial artifact is citable footprint evidence, but it is not screening authorization: missing scenario/turn/pass coverage continues to fail `validate_capacity_coverage(...)`.

If failure occurs before any exact observation exists, no empty/fabricated `amcap` artifact is written.

The producer does not infer an `input_context_overflow` classification merely from a generic provider failure. Independent failure classification remains separate evidence and is attached only when actually proved by the corresponding capacity contract.

## Host facade

The shared `python -m relaylm.actual_model_host` facade exposes two explicit vLLM operations:

```text
--operation screening   # default; existing capacity-gated product path
--operation capacity    # capacity-footprint producer
```

Omitting `--operation` preserves the historical vLLM screening dispatch. LM Studio dispatch remains unchanged.

A capacity invocation still accepts exactly one `A | B | C` condition; there is no `all` mode or Cartesian parameter exploration. Its receipt identifies the operation, condition, RelayLM commit, target, replicate, observed live `max_model_len`, and resulting capacity-evidence receipt. It does not emit product execution/boundary/review artifacts and does not report a model-quality score.

On partial failure the facade reports the partial capacity receipt, when one exists, and returns failure without reinterpreting that partial footprint as a completed condition.

## Deliberate boundary

This producer does not:

- select a numeric context window, output reserve, profile, or default;
- modify #1387 budget/degradation semantics;
- repeat the #1545 reasoning-effort experiment;
- add `bounded(64)` or `low|medium|high` product conditions;
- tune prompts, schemas, fixtures, or model output;
- run LM Studio simultaneously with vLLM;
- persist product-quality execution/review/boundary evidence;
- authorize COGP5 screening by itself.

Its only job is to turn the real current production trajectory into truthful, content-free, immutable capacity-demand evidence. Product screening may resume only after the required complete capacity evidence exists and a later authority explicitly selects an evidence-resolving runtime condition.