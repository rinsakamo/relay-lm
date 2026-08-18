# Actual-model LM Studio host runner

This reference describes the #1386 host-local execution entry point for the first canonical actual-model evidence track.

It does **not** define runtime defaults, calibration values, provider tuning, or the #1247 deterministic suite.

## Purpose

The host runner removes handwritten Python glue from the first real-evidence path while preserving the already-merged evidence contracts:

```text
explicit host condition
        +
exact clean RelayLM checkout
        +
frozen Gemma GGUF bytes
        |
        v
canonical target / fixture / foundation-v2 verification
        |
        v
OpenAI-compatible provider construction
        |
        v
#1484 LM Studio binding preflight
        |
        v
existing #1386 scenario execution
        |
        v
immutable *.lm-studio.json evidence
```

Run it as a module:

```text
python -m relaylm.actual_model_host_runner \
  --condition /outside/repo/condition.json \
  --repo-root /path/to/relay-lm \
  --model-artifact /path/to/gemma-4-12B-it-Q4_K_M.gguf \
  --workspace-root /outside/repo/workspaces \
  --artifact-root /outside/repo/evidence
```

There is intentionally no `relaylm-eval` registration. `relaylm-eval` remains the #1247 RelayLM-native deterministic suite.

## Canonical first-track inputs

The runner fixes these repository-side identities rather than accepting arbitrary alternatives:

- target: `evaluation/actual_model/targets/gemma-4-12b-it-q4-k-m-v1.json`;
- scenario set: `evaluation/actual_model/scenario_sets/foundation-v2.json`;
- Character fixture: `evaluation/actual_model/characters/foundation-v1`.

The local model file must pass the exact size and SHA-256 verification owned by `actual_model_targets.py` before a provider is constructed.

The repository checkout must be at exactly the `relaylm_commit` declared by the condition and must be clean, including no untracked files. Keep the condition file, mutable workspaces, model artifact, and generated evidence outside the repository unless they are already part of a clean tracked snapshot.

## Host condition

The condition is strict JSON. Unknown, missing, and duplicate fields are rejected.

The shape is:

```text
{
  "format_version": 1,
  "relaylm_commit": "<exact 40-character v1 commit>",
  "lm_studio": {
    "version": "<observed LM Studio version>",
    "build": "<observed LM Studio build identity>",
    "deployment_identity": "<operator-defined stable identity for this deployment>",
    "base_url": "<actual OpenAI-compatible /v1 endpoint>",
    "request_model": "<exact model identifier sent to LM Studio>",
    "api_key_env": null
  },
  "effective_context_window": <explicit observed/configured integer>,
  "decoding": {
    "temperature": <explicit number or null>,
    "top_p": <explicit number or null>,
    "seed": <explicit integer or null>
  },
  "supported_decoding_controls": [
    "<only controls actually supported by this deployment>"
  ],
  "execution_path": "buffered",
  "continuity_runtime": {
    "max_items": <explicit integer>,
    "lifetime_revisions": <explicit integer>
  },
  "budgets": {
    "memory_max_chunks": <explicit integer or null>,
    "memory_max_chars": <explicit integer or null>,
    "event_max_events": <explicit integer or null>,
    "event_max_chars": <explicit integer or null>
  },
  "condition_id": "<explicit evidence condition name>",
  "replicate_id": "<explicit replicate identity>",
  "scenario_ids": [
    "<one or more exact foundation-v2 scenario ids>"
  ]
}
```

The snippet is schema-shaped pseudodata, not a canonical condition. No number shown as a placeholder above is a RelayLM default.

`memory_max_chunks` and `memory_max_chars` must either both be supplied or both be null. The same rule applies to `event_max_events` and `event_max_chars`.

If any selected scenario requires `continuity_candidates`, `continuity_runtime` must be explicit. The runner never invents Continuity capacity or lifetime.

## Decoding truthfulness

`temperature`, `top_p`, and `seed` are optional only in the sense that the operator may explicitly set them to null. There is no numeric default in this runner.

`supported_decoding_controls` is also explicit. The OpenAI-compatible provider rejects requested controls not declared supported. The #1484 binding then verifies that the manifest records exactly the decoding controls and seed actually carried by the constructed provider.

This means a condition cannot claim `seed: 7`, for example, while sending no seed upstream.

## Secrets and endpoint identity

The host condition may name an environment variable through `api_key_env`. The secret value is read only at execution time and is never copied into the manifest or LM Studio evidence envelope.

`base_url` is required to construct the live provider but is not persisted by the #1484 secret-free LM Studio binding. `deployment_identity`, exact LM Studio version/build, and request model are the citable runtime identity.

## Manifest generation

The operator does not hand-author an `ActualModelRunManifest`.

The runner derives it from:

- exact clean Git HEAD;
- canonical scenario-set and Character-fixture revisions;
- canonical frozen GGUF target and verification receipt;
- the actual constructed provider P4 identity;
- explicit host condition values.

The #1484 binding rechecks target/provider/manifest agreement before scenario execution. This avoids metadata that merely looks reproducible but does not describe the provider request that actually ran.

## Output

Each successful selected scenario writes the existing immutable condition-bound artifact:

```text
<execution_id>.lm-studio.json
```

The command also prints a content-free index containing:

- RelayLM commit;
- condition and replicate identity;
- scenario id;
- execution id;
- run id;
- artifact path;
- `score: null`.

Human/product-quality review and deterministic-boundary verdicts remain separate #1386 sidecars. The host runner does not synthesize a composite score.

## Current boundary

This first host runner supports the already-existing legacy explicit MEMORY/Event budget condition carried by `ExplicitBudgetConfiguration`.

It deliberately does **not** manufacture a #1387 total `CognitiveBudgetRuntimeConfig` token counter. Total-budget pressure/calibration evidence requires a demonstrably correct serialized-input token counter for the actual tokenizer/provider path and remains a separate bounded transaction.

Accordingly:

- this runner can produce the first citable foundation-v2 real-model executions;
- those executions do not, by themselves, justify #1388 numeric defaults;
- #1388 pressure/default decisions still require the separately controlled total-budget evidence path.

## Failure behavior

The command fails before semantic generation when, among other cases:

- checkout HEAD differs from `relaylm_commit`;
- checkout is dirty;
- the GGUF bytes do not match the frozen target;
- a scenario id is outside canonical foundation-v2;
- Continuity identity is required but missing;
- a declared decoding control is unsupported;
- provider/runtime/manifest identity drifts at the #1484 binding boundary;
- a workspace path for the run already exists;
- an immutable evidence id already exists with different bytes.

No automatic retry is introduced by this runner. One RelayLM semantic turn remains one model generation.
