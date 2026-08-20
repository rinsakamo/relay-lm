# Actual-model LM Studio host runner

This reference describes the #1386 host-local execution entry point for the canonical ordinary-turn actual-model evidence track.

It does **not** define runtime defaults, calibration values, provider tuning, COGP semantic policy, or the #1247 deterministic suite.

## Purpose

The host runner removes handwritten execution glue while preserving the already-owned evidence contracts:

```text
strict host condition + exact target id
        +
exact clean RelayLM checkout
        +
frozen model bytes
        |
        v
target / fixture / foundation-v2 verification
        |
        +--> optional host serving/reasoning attestation
        |
        v
topology-aware OpenAI-compatible provider construction
        |
        v
#1484 LM Studio binding preflight
        |
        v
existing #1386 scenario execution
        |
        +--> immutable *.lm-studio.json execution evidence
        |
        +--> existing #1433 deterministic-boundary evaluator
                 |
                 v
             immutable *.boundary.json verdict
```

Run it as a module:

```text
python -m relaylm.actual_model_host_runner \
  --condition /outside/repo/condition.json \
  --repo-root /path/to/relay-lm \
  --model-artifact /path/to/model.gguf \
  --workspace-root /outside/repo/workspaces \
  --artifact-root /outside/repo/evidence \
  [--counter-proof /outside/repo/counter-proof.json] \
  [--serving-proof /outside/repo/serving-proof.json] \
  [--lmstudio-node /path/to/node] \
  [--lmstudio-sdk-root /path/to/node_modules]
```

`--counter-proof` is used by strict `format_version: 3` total-budget conditions. `--serving-proof` is used by strict `format_version: 5` reasoning-attested cognition conditions. Both use the same already-owned LM Studio serving-proof machinery, but they serve different evidence semantics. Node/SDK paths are host-local dependencies for proof validation; they are not RelayLM runtime defaults.

There is intentionally no `relaylm-eval` registration. `relaylm-eval` remains the #1247 RelayLM-native deterministic suite.

## Canonical first-track inputs

The runner fixes the scenario set and Character fixture and accepts only explicitly allowlisted frozen target IDs.

Current target IDs are:

- `gemma-4-12b-it-q4-k-m-v1`
  - target file: `evaluation/actual_model/targets/gemma-4-12b-it-q4-k-m-v1.json`;
  - artifact repository: `bartowski/gemma-4-12B-it-GGUF`;
  - artifact repository revision: `2ae7d41be21ca62de00a2d320ee9cec50daa3aa6`;
  - artifact size: `7662531872` bytes;
  - artifact SHA-256: `3962624dcd25b947d889dc9ae1bf275b61db6cd4dbe694057f34fffef1671509`.
- `gemma-4-12b-it-q4-k-m-lmstudio-community-v1`
  - target file: `evaluation/actual_model/targets/gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json`;
  - artifact repository: `lmstudio-community/gemma-4-12B-it-GGUF`;
  - artifact repository revision: `65fe312c53d8b4579f444382adf078bacb1972d0`;
  - artifact size: `7381384864` bytes;
  - artifact SHA-256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`.

The LM Studio Community target freezes the exact historical bytes observed in the local LM Studio cache. A mutable `main` alias, model family name, or quantization label alone is not sufficient evidence identity.

The remaining fixed repository-side identities are:

- scenario set: `evaluation/actual_model/scenario_sets/foundation-v2.json`;
- Character fixture: `evaluation/actual_model/characters/foundation-v1`.

There is no implicit target default. The supplied model artifact must pass exact size and SHA-256 verification before provider construction.

The repository checkout must be exactly at the `relaylm_commit` declared by the condition and must be clean, including no untracked files. Conditions, mutable workspaces, model artifacts, serving proofs, and generated evidence should remain outside the repository unless they are part of the exact clean tracked snapshot.

## Strict host-condition versions

The condition is strict JSON. Unknown, missing, and duplicate fields are rejected. A version is never silently reinterpreted as a newer evidence class.

- `format_version: 2` — legacy explicit MEMORY/Event budget evidence.
- `format_version: 3` — total Cognitive Budget evidence with an explicit serialized-input counter identity.
- `format_version: 4` — explicit cognition execution topology evidence.
- `format_version: 5` — explicit cognition topology plus attested model-wide reasoning environment.

Version 1 is not accepted.

## Common host fields

All supported versions carry the same host/model identity boundary:

```text
{
  "format_version": <2 | 3 | 4 | 5>,
  "target_id": "<one exact allowlisted target id>",
  "relaylm_commit": "<exact lowercase 40-character v1 commit>",
  "lm_studio": {
    "version": "<observed LM Studio version>",
    "build": "<observed LM Studio build identity>",
    "deployment_identity": "<operator-defined stable deployment identity>",
    "base_url": "<actual OpenAI-compatible /v1 endpoint>",
    "request_model": "<exact model identifier sent to LM Studio>",
    "api_key_env": null
  },
  "effective_context_window": <explicit positive integer>,
  "decoding": {
    "temperature": <explicit number or null>,
    "top_p": <explicit number or null>,
    "seed": <explicit integer or null>
  },
  "supported_decoding_controls": ["<explicit supported control>"],
  "execution_path": "buffered | streaming",
  "continuity_runtime": <explicit object or null>,
  "condition_id": "<explicit condition identity>",
  "replicate_id": "<explicit replicate identity>",
  "scenario_ids": ["<exact foundation-v2 scenario id>"]
}
```

The schema-shaped examples in this document do not establish numeric defaults.

## Legacy MEMORY/Event condition (`format_version: 2`)

V2 adds:

```text
"budgets": {
  "memory_max_chunks": <integer or null>,
  "memory_max_chars": <integer or null>,
  "event_max_events": <integer or null>,
  "event_max_chars": <integer or null>
}
```

`memory_max_chunks` and `memory_max_chars` must either both be supplied or both be null. The same rule applies to Event count/character limits.

V2 cannot carry total Cognitive Budget, cognition-execution identity, or reasoning-environment identity.

## Total-budget condition (`format_version: 3`)

V3 replaces legacy `budgets` with the existing manifest-shaped `cognitive_budget` identity:

```text
"cognitive_budget": {
  "model_context_window": <caller-supplied integer equal to effective_context_window>,
  "reserved_output_tokens": <caller-supplied integer>,
  "initial_plan": {
    "canonical_state": { "max_items": <integer>, "floor_items": <integer> },
    "working_context": { "max_items": <integer>, "floor_items": <integer>, "max_chars": <integer>, "floor_chars": <integer> },
    "retrieved_memory": { "max_items": <integer>, "floor_items": <integer>, "max_chars": <integer>, "floor_chars": <integer> },
    "event_evidence": { "max_items": <integer>, "floor_items": <integer>, "max_chars": <integer>, "floor_chars": <integer> }
  },
  "degradation_steps": [
    { "layer": "<canonical BudgetLayer>", "tier": <canonical tier>, "target": { "...": "owner-shaped envelope" } }
  ],
  "token_counter": {
    "format_version": 1,
    "capability": "<registered host capability>",
    "implementation": "<provider/model counter implementation>",
    "version": "<stable implementation identity>",
    "mode": "exact | conservative_estimate",
    "tokenizer_identity": "<artifact actually consumed by the counter>",
    "parameters": { "<explicit reproducibility parameter>": "<scalar>" }
  }
}
```

The parser constructs the existing `TotalBudgetConfig`, `BudgetPlan`, `BudgetDegradationPolicy`, and owner envelope types. It rejects malformed envelopes, tier drift, invalid reduction order, mixed legacy/total shapes, unknown fields, and a `model_context_window` different from the effective host context before generation.

The host must supply the declared `HostTokenCounterCapability`. The capability must return the canonical `OpenAICompatibleSerializedInputCounter` over the actual existing provider request body. There is no tokenizer inference, byte/character fallback, or hidden conservative mode.

`exact` is accepted only for an explicitly demonstrated exact capability. `conservative_estimate` is accepted only for an explicitly demonstrated safe upper bound. Counter identity, model, decoding configuration, and count mode must all agree with the condition and provider or execution fails closed.

V3 cannot carry cognition execution or reasoning environment evidence.

## Cognition-execution condition (`format_version: 4`)

V4 keeps the legacy explicit MEMORY/Event budget shape and requires:

```text
"cognition_execution": {
  "mode": "single_pass | two_pass | shadow_two_pass"
}
```

`auto` is unresolved policy and is rejected as evidence identity. The host constructs the existing `CognitionExecutionEvidenceIdentity` using the exact same `execution_path` as the host condition and binds that identity into `ActualModelRunManifest.cognition_execution`.

Explicit `single_pass` uses the canonical `OpenAICompatibleProvider`. `two_pass` and `shadow_two_pass` use the already-implemented `OpenAICompatibleTwoPassProvider`. The subclass keeps the same Chat Completions transport and provider-owned decoding configuration while exposing the conversation/extraction methods required by the merged COGP runtime.

V4 deliberately cannot carry the V3 total Cognitive Budget identity. It also does not add or imply a reasoning request control.

## Reasoning-attested cognition condition (`format_version: 5`)

V5 keeps the V4 topology and legacy MEMORY/Event budget shape and additionally requires:

```text
"reasoning": {
  "required_setting": "<explicit LM Studio model-wide default required by this evidence condition>"
}
```

The required setting is an **environment requirement**, not a request option. The current canonical OpenAI-compatible Chat Completions adapter still has no per-request reasoning/thinking, reasoning-effort, or bounded-reasoning carriage.

V5 requires `--serving-proof` before provider construction or semantic generation. The runner validates the proof against the condition, frozen target, artifact, and loaded serving instance using the existing LM Studio SDK attestation path, then reads live native LM Studio model metadata from `/api/v1/models`.

The reasoning attestation requires all of the following:

- serving-proof request model and loaded model key equal the condition request model;
- exactly one matching live model exists;
- the live object is an LLM;
- live model size equals the serving-proof loaded size;
- live quantization equals the frozen target quantization;
- exactly one unambiguous loaded instance exists and matches the proof model key;
- `capabilities.reasoning` contains exactly `allowed_options` and `default`;
- `allowed_options` is non-empty, string-only, and duplicate-free;
- the required setting is in `allowed_options`;
- the live default equals the required setting.

No response text, chain-of-thought style, or visible reasoning text is inspected to infer the setting.

The resulting content-free `ActualModelReasoningEnvironmentIdentity` records:

- required setting;
- effective setting;
- sorted allowed options;
- live default;
- `control_source = lmstudio_model_default`;
- `control_mode = attested_default_without_per_request_override`;
- SHA-256 identity of the exact serving-proof bytes used for attestation.

V5 uses `ActualModelReasoningRunManifest`, a derived ordinary-turn manifest. It carries the ordinary manifest fields plus `reasoning_environment`. This makes the attested environment participate in the stable run identity without widening or changing historical V2/V3/V4 manifest serialization.

V5 cannot carry V3 total Cognitive Budget evidence. The provider request remains the same request shape used by V4: no `reasoning`, `reasoning_effort`, or hidden provider-specific field is inserted.

## Frozen LM Studio Community serving/counter proof

The canonical host-only counter capability for `gemma-4-12b-it-q4-k-m-lmstudio-community-v1` is:

```text
capability:     lmstudio.gemma4.loaded-sdk.serialized-input.v1
implementation: lmstudio-js-loaded-model-counter
version:        2
mode:           exact
```

The bridge is owned by `relaylm.actual_model_lm_studio_counter`. It uses the optional `@lmstudio/sdk` package through a short-lived Node worker, selects exactly one attested loaded instance by request-model key, applies that instance's prompt template to the exact request messages, and counts the resulting prompt with the loaded model.

The proof is secret-free and binds, at minimum:

- RelayLM commit and frozen target id/size/SHA;
- request model and exact LM Studio version/build/deployment identity;
- SDK package/version;
- loaded model key/path/quantization and loaded-instance reference identity;
- frozen-entrypoint linkage;
- request-model-to-loaded-instance linkage;
- prompt-template parity;
- synthetic prompt-count probes, including Japanese, ASCII, State, Working Context, MEMORY, Event Evidence, and mixed input;
- controlled structured-output schema/no-schema comparison;
- any deterministic server framing offset needed to reconcile SDK prompt count with server `usage.prompt_tokens`.

The SDK-loaded model key may be a logical serving key and its reported size may be an aggregate package size. It must still link through host-local LM Studio metadata to the exact frozen GGUF entrypoint. Family name, quantization label, or an assumed upstream tokenizer is not enough. If that link is unavailable, the capability remains unavailable rather than falling back to a heuristic.

The same serving proof can be consumed by V5 for loaded-model/reasoning attestation, but this does not turn the reasoning setting into a token-counter property or provider request control.

## Continuity capability safety

The canonical OpenAI-compatible provider declares the `continuity_candidates` semantic channel even when a selected scenario does not require a Continuity proposal. Therefore a run whose provider manifest declares that channel must carry explicit `continuity_runtime` whenever selected scenarios can rely on it.

The runner never invents Continuity capacity or lifetime. Ordinary-turn commit must be able to truthfully accept or reject an optional ContinuityCandidate if the provider emits one.

## Target truthfulness

`target_id` selects repository-owned frozen metadata; it does not accept an arbitrary mutable model alias. The supplied local artifact must match the selected target's exact size and SHA-256.

The run manifest derives model-artifact and serving-tokenizer identity from that selected frozen target, keeping different GGUF bytes distinct even when display names or quantization labels match.

## Decoding truthfulness

`temperature`, `top_p`, and `seed` are explicit carriage fields and have no numeric default in the runner. Null means omitted.

`supported_decoding_controls` is also explicit. The provider rejects a requested control not declared supported. The #1484 binding then verifies that manifest decoding identity matches the request configuration actually carried by the provider.

The topology-aware provider subclass and V5 attestation add no hidden decoding or reasoning request fields.

## Secrets and endpoint identity

The condition may name an API-key environment variable. The secret value is read only for live access and is not copied into the manifest, serving-proof identity, or LM Studio evidence envelope.

`base_url` is required to reach the live deployment but is not itself persisted as semantic evidence authority. `deployment_identity`, exact LM Studio version/build, request model, frozen target, and serving-proof identity provide citable runtime identity.

## Manifest generation

The operator does not hand-author the run manifest. The runner derives it from:

- exact clean Git HEAD;
- selected frozen target and verification receipt;
- canonical scenario-set and Character-fixture revisions;
- actual constructed provider P4 identity;
- explicit host-condition values;
- V4/V5 resolved `CognitionExecutionEvidenceIdentity` where present;
- V5 live-attested reasoning environment where present.

The #1484 binding rechecks target/provider/manifest agreement before scenario execution.

Historical V2/V3 runs use ordinary `ActualModelRunManifest`. V4 uses the same manifest with optional cognition-execution identity. Only V5 reasoning-attested runs use `ActualModelReasoningRunManifest` and emit `reasoning_environment`.

## Output

Each successful selected scenario writes:

```text
<execution_id>.lm-studio.json
<verdict_id>.boundary.json
```

The execution artifact is persisted first. The already-produced execution result is then passed to the existing deterministic-boundary evaluator; the host runner does not duplicate or reinterpret State/Continuity semantics.

A boundary `pass` means only that the observed RelayLM deterministic/runtime boundary satisfied the #1433 protocol invariants. It is not a product-quality score.

The command prints a content-free index carrying the commit, target, condition/replicate identities, scenario, execution/run IDs, artifact paths, boundary verdict identity/outcome, and `score: null`.

Human/product-quality review remains a separate #1386 sidecar.

## Current COGP5 boundary

Repository-side support now includes:

- V4 topology-aware host execution;
- V5 pre-generation model-wide reasoning-environment attestation;
- run identity that distinguishes the attested reasoning environment;
- unchanged provider request semantics.

Therefore supported A/B COGP conditions can be executed on a real host once both use matching frozen target, serving proof, LM Studio deployment, decoding, scenarios, and effective reasoning environment.

For the current canonical provider capability class:

```text
A = explicit single_pass under the attested environment
B = explicit two_pass under the same attested environment
C = unsupported: bounded Pass 2 reasoning cannot be carried or attested per request
```

C must not be represented as a generated run. Explicit unsupported/not-executed evidence remains a separate #1386 transaction.

Nothing in V5 selects a #1388 profile or default.

## Failure behavior

The command fails before semantic generation when, among other cases:

- checkout HEAD differs from `relaylm_commit` or the checkout is dirty;
- target id is outside the allowlist or frozen bytes do not match;
- a scenario is outside canonical foundation-v2;
- required Continuity Runtime identity is missing;
- a declared decoding control is unsupported;
- provider/runtime/manifest identity drifts at the #1484 boundary;
- a V3 total-budget identity is malformed, mismatched, or lacks a truthful registered counter;
- a V4/V5 cognition mode is `auto`, unknown, or has an execution-path mismatch;
- V5 omits the serving proof;
- the serving proof does not bind the selected target/request model/loaded instance;
- live LM Studio reasoning metadata is missing or malformed;
- the required reasoning setting is unavailable or differs from the live default;
- a workspace path already exists;
- an immutable evidence id already exists with different bytes.

After semantic execution, a filesystem/conflict failure while writing a required sidecar fails the command rather than pretending the evidence chain is complete. Existing immutable evidence remains immutable and no automatic semantic retry is introduced.

V2/V3 preserve their existing single-generation semantics. V4/V5 execute exactly the topology recorded in their cognition-execution identity. V5 additionally proves the model-wide reasoning environment but does not alter the provider request.
