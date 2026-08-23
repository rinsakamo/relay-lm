# Actual-model LM Studio execution binding

Status: #1386 Actual-model Evaluation execution-condition binding for the canonical local OpenAI-compatible evidence path.

This reference does not choose runtime defaults, decoding values, Cognitive Budget values, or a second model. It defines how externally observed LM Studio runtime facts, the frozen model artifact, the constructed OpenAI-compatible provider, and `ActualModelRunManifest` must agree before a citable real-model generation may begin.

## Canonical evidence path

```text
verified frozen GGUF
  -> exact LM Studio runtime/deployment
  -> canonical OpenAI-compatible provider
  -> provider-owned P4 capability/config identity
  -> #1386 binding preflight
  -> existing scenario-set execution harness
```

The binding is an evidence guard around the existing #1386 execution machinery. It does not create a second semantic model call or a parallel scoring system.

## LM Studio runtime identity

`LMStudioExecutionEnvironment` requires externally observed, secret-free values for:

- exact LM Studio version;
- exact LM Studio build;
- deployment identity chosen by the evidence operator;
- exact provider request model identifier.

These values serialize canonically into `ActualModelRunManifest.provider_identity`. This lets the existing immutable execution artifact retain the runtime identity without changing historical manifest serialization or historical run IDs.

The runtime identity deliberately excludes API keys and does not automatically serialize `base_url`. A deployment identity must be explicit and secret-free; it is not inferred by hashing credentials or endpoint strings.

## Fail-before-generation binding

`bind_lm_studio_execution_condition(...)` requires all of the following to agree before generation:

1. frozen target ID/revision and the local artifact verification receipt;
2. manifest `model_artifact` and the frozen target's exact GGUF artifact identity;
3. manifest `tokenizer_identity` and the tokenizer embedded in those exact GGUF bytes;
4. externally configured context window and manifest effective context window;
5. LM Studio request model and the actual constructed provider's request model;
6. canonical adapter identity;
7. exact provider-owned capability tokens;
8. exact decoding controls carried by the provider request;
9. manifest seed and the seed actually carried by the provider, including omission;
10. canonical LM Studio runtime/deployment identity and manifest provider identity.

A mismatch raises `ActualModelLMStudioBindingError` before scenario execution, mutable Character workspace creation, or provider generation.

## Evidence artifact

`run_lm_studio_actual_model_scenario_definition(...)` performs the binding first and then delegates to the existing `run_actual_model_scenario_definition(...)` path.

The returned envelope contains:

- the condition binding and its stable ID;
- frozen target + artifact verification identity;
- provider-owned P4 identity;
- configured context window;
- complete run manifest;
- the existing scenario execution result and run ID;
- `score: null`.

`write_lm_studio_actual_model_execution_result(...)` persists this envelope immutably. Before filesystem mutation it recomputes the LM Studio `binding_id`, preserves the backend-specific nested and outer execution-ID checks, requires the nested scenario execution to pass the same generic citable admission used by `write_actual_model_execution_result(...)`, and requires the LM Studio binding manifest to equal the nested execution plan manifest. The generic admission covers the content-derived plan ID, canonical ordinary/restart run ID, plan/evidence binding, and generic execution ID. Identical same-ID bytes are idempotent. Different evidence under the same ID is rejected and requires a distinct `replicate_id` through the existing run identity contract.

## Remaining external facts

Repository code cannot manufacture the runtime values required for a real local run. Before the first canonical Gemma execution, the operator still must supply truthful observed values for at least:

- the exact local GGUF path, which must pass the #1472 size/SHA256 verifier;
- LM Studio version/build;
- deployment identity;
- request model identifier;
- effective context window;
- explicit decoding configuration and seed, using only provider-declared supported controls;
- explicit Cognitive Budget condition when the run is intended for calibration evidence.

The provider binding proves that manifest metadata matches the constructed RelayLM provider request authority. It does not claim a cryptographic proof that a remote OpenAI-compatible server loaded a particular file internally; the frozen local artifact load remains an operator-controlled deployment fact that must be kept truthful and auditable.

## Ownership boundaries

This binding does not modify:

- provider wire/prompt semantics (#1456 owner); 
- Continuity, State, Retrieval, or Context Compiler semantics;
- Cognitive Budget semantics or degradation policy (#1387);
- Calibration candidate/default values (#1388);
- Release Runtime configuration precedence/operator UX (#1446);
- #1247 deterministic evaluation registry/count;
- shared authority/navigation surfaces.
