# Actual-model vLLM execution binding

This reference defines the #1386-owned binding between the frozen vLLM repository-snapshot target, live vLLM/model capability authority, the canonical OpenAI-compatible provider, and one citable actual-model run manifest.

It does not define cognition policy, reasoning defaults, a new evaluation runner, or a second provider mapping. Provider semantics remain owned by #1545/#1533; this binding only proves that the already-resolved execution condition is the one actually being used by #1386.

## Canonical target

The current vLLM execution target is:

- target: `gemma-4-12b-it-qat-w4a16-vllm-v1`;
- repository artifact: `unsloth/gemma-4-12B-it-qat-w4a16@626f3b2f8a3799cb2b64ca5fc09443c90fe2cbb2`;
- target format: repository snapshot with exact required file sizes/SHA-256 values;
- serving tokenizer and chat-template roles are part of the frozen target identity.

Before a run may be cited, `verify_actual_model_repository_snapshot(...)` must verify the local snapshot and the resulting verification must bind to the exact target revision and full frozen file count.

## Runtime/capability authority

The binding consumes `VLLMReasoningCapabilityAttestation` rather than inferring capability from model names or request acceptance.

That attestation already binds:

- backend `vllm` and exact version;
- request/served model identity from `/version` and `/v1/models`;
- live `model_root` and `max_model_len` when reported;
- exact frozen target/repository revision;
- reasoning parser and template thinking control;
- separately classified OFF and numeric bounded reasoning controls;
- protocol acceptance, semantic effect, repeatability, and ambiguity facts.

For the current canonical path, both OFF and bounded capability must be `semantically_attested`. `low`/`medium`/`high` effort labels are not numeric bounded substitutes and are not a COGP5 product-quality axis.

## Fail-before-generation binding

`bind_vllm_execution_condition(...)` rejects the run before scenario generation unless all of the following agree:

1. repository-snapshot verification target ID/revision and verified file count match the frozen target;
2. reasoning capability target ID/revision, model artifact identity, and repository revision match the same target;
3. the live vLLM `model_root` resolves to the verified snapshot root;
4. live `max_model_len`, the configured context window, and the manifest effective context window agree;
5. the provider carries the exact same `VLLMReasoningCapabilityAttestation` that the binding cites;
6. provider model and attested request model agree;
7. manifest provider/adapter/model/tokenizer/decoding/capability/seed identity agrees with the constructed provider and target;
8. the manifest contains explicit #1562 cognition pass-request identity;
9. current COGP5 request evidence uses the buffered execution path.

The manifest `provider_identity` is a deterministic secret-free serialization of the exact vLLM reasoning capability attestation. The binding sidecar also keeps that capability separately visible; a requested reasoning value is never promoted to applied capability by the evidence layer.

## Execution reuse

`run_vllm_actual_model_scenario_definition(...)` does not create a parallel evaluation architecture. After binding succeeds it calls the existing `run_actual_model_scenario_definition(...)` path unchanged.

The canonical OpenAI-compatible provider remains responsible for turning the #1562 `CognitionPassRequest` into the #1558 vLLM wire realization. Therefore:

```text
#1386 scenario + explicit pass request identity
        -> existing actual-model scenario harness
        -> existing Turn single-pass/two-pass path
        -> canonical OpenAI-compatible provider
        -> #1558 vLLM reasoning realizer
        -> exact vLLM request
```

A completed condition-bound result can be persisted as immutable `<execution_id>.vllm.json`. Same-ID/different-evidence replacement is rejected and requires a distinct replicate identity.

## COGP5 screening boundary

The first vLLM product-quality screening stays serial and hypothesis-driven:

```text
A: single_pass
   reasoning = off

B: two_pass
   Pass 1 = off
   Pass 2 = off

C: two_pass
   Pass 1 = off
   Pass 2 = bounded(16)
```

`bounded(64)` is eligible only if the first bounded comparison shows a meaningful product/budget difference that justifies deeper screening. Do not add `low`/`medium`/`high`, invalid-wire probes, streaming permutations, parser permutations, or template-conflict permutations to the product-quality matrix; those are provider capability/conformance evidence rather than product conditions.

## Deliberate boundary

This binding module consumes already-obtained live backend/reasoning attestations; it does not itself perform network discovery or re-run the R3B capability probe. Host orchestration may acquire those facts, but must feed the same typed attestation into both the provider and this binding.

No actual-model A/B/C execution, quality conclusion, calibration decision, or runtime default is created merely by this contract.
