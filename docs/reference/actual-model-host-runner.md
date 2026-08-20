# Actual-model LM Studio host runner

This reference describes the #1386 host-local execution entry point for the first canonical actual-model evidence track.

It does **not** define runtime defaults, calibration values, provider tuning, or the #1247 deterministic suite.

## Purpose

The host runner removes handwritten Python glue from the first real-evidence path while preserving the already-merged evidence contracts:

```text
explicit host condition + explicit target id
        +
exact clean RelayLM checkout
        +
frozen Gemma GGUF bytes
        |
        v
allowlisted target / fixture / foundation-v2 verification
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
  --model-artifact /path/to/gemma-4-12B-it-Q4_K_M.gguf \
  --workspace-root /outside/repo/workspaces \
  --artifact-root /outside/repo/evidence \
  --counter-proof /outside/repo/lmstudio-counter-proof-v1/counter-proof.json \
  --lmstudio-node /path/to/node \
  --lmstudio-sdk-root /path/to/node_modules
```

The last three options are used only by a strict `format_version: 3` condition. They
are optional CLI paths because the LM Studio SDK is a host-local dependency; v2 and
v4 runs never resolve the total-budget counter through this path. For v3, omitting
the proof or an available SDK runtime fails before provider construction and before
semantic generation.

There is intentionally no `relaylm-eval` registration. `relaylm-eval` remains the #1247 RelayLM-native deterministic suite.

## Canonical first-track inputs

The runner fixes the scenario-set and Character-fixture identities and accepts only explicitly allowlisted frozen target IDs.

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

The LM Studio Community target deliberately freezes the exact historical bytes observed in the local LM Studio cache. A later upstream commit replaced the Q4_K_M object, so a mutable `main` alias or the quantization name alone is not sufficient evidence.

The remaining fixed repository-side identities are:

- scenario set: `evaluation/actual_model/scenario_sets/foundation-v2.json`;
- Character fixture: `evaluation/actual_model/characters/foundation-v1`.

There is no implicit target default. The host condition must name one allowlisted `target_id`, and the local model file must pass the exact size and SHA-256 verification owned by `actual_model_targets.py` before a provider is constructed.

The repository checkout must be at exactly the `relaylm_commit` declared by the condition and must be clean, including no untracked files. Keep the condition file, mutable workspaces, model artifact, and generated evidence outside the repository unless they are already part of a clean tracked snapshot.

## Host condition

The condition is strict JSON. Unknown, missing, and duplicate fields are rejected.

Target selection was made explicit before the first real canonical execution, so legacy host conditions remain strict `format_version: 2`. Version 1 conditions do not silently acquire a target default. Total cognitive-budget conditions use strict `format_version: 3`; a v2 condition is never reinterpreted as total-budget evidence. Cognition-execution topology conditions use strict `format_version: 4`; a v2/v3 condition never silently acquires a COGP topology identity.

The legacy v2 shape is:

```text
{
  "format_version": 2,
  "target_id": "<one exact allowlisted target id>",
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

### Total-budget condition (`format_version: 3`)

The total-budget mode replaces `budgets` with the existing manifest-shaped `cognitive_budget` identity. It has no numeric defaults:

```text
{
  "format_version": 3,
  "target_id": "<one exact allowlisted target id>",
  "relaylm_commit": "<exact 40-character v1 commit>",
  "lm_studio": { "...": "the same strict v2 fields" },
  "effective_context_window": <explicit host context integer>,
  "decoding": { "temperature": <number or null>, "top_p": <number or null>, "seed": <integer or null> },
  "supported_decoding_controls": ["<explicit controls>"],
  "execution_path": "buffered",
  "continuity_runtime": null,
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
  },
  "condition_id": "<explicit evidence condition name>",
  "replicate_id": "<explicit replicate identity>",
  "scenario_ids": ["<one or more exact foundation-v2 scenario ids>"]
}
```

The parser constructs the existing `TotalBudgetConfig`, `BudgetPlan`, `BudgetDegradationPolicy`, and owner envelope types. It therefore rejects malformed envelopes, tier drift, invalid reduction order, mixed legacy/total shapes, unknown fields, and a total `model_context_window` that differs from the effective host context before workspace or model generation.

The host must register a `HostTokenCounterCapability` for the declared capability when calling `prepare_actual_model_host_run`. That capability must return the canonical `OpenAICompatibleSerializedInputCounter`, whose callback receives the exact existing `_request_body(...)` model-input shape. The runner does not select a tokenizer, infer a provider endpoint, or apply a byte/character heuristic. If the capability is absent, its model/decoding identity drifts, its identity differs from the condition, or its truthfulness attestation is not satisfied, execution fails closed before generation.

`exact` is accepted only for a registered capability whose exact behavior has been demonstrated for the configured serving path. `conservative_estimate` is accepted only for a registered capability with a demonstrated safe upper-bound proof. The mode is recorded both in the counter identity and in existing #1467 per-turn diagnostics. A returned count whose mode differs from the declared identity is rejected.

### Cognition-execution condition (`format_version: 4`)

The cognition-execution mode keeps the legacy explicit MEMORY/Event budget shape and adds a required resolved topology declaration:

```text
{
  "format_version": 4,
  "target_id": "<one exact allowlisted target id>",
  "relaylm_commit": "<exact 40-character v1 commit>",
  "lm_studio": { "...": "the same strict v2 fields" },
  "effective_context_window": <explicit host context integer>,
  "decoding": { "temperature": <number or null>, "top_p": <number or null>, "seed": <integer or null> },
  "supported_decoding_controls": ["<explicit controls>"],
  "execution_path": "buffered | streaming",
  "continuity_runtime": null,
  "budgets": {
    "memory_max_chunks": <integer or null>,
    "memory_max_chars": <integer or null>,
    "event_max_events": <integer or null>,
    "event_max_chars": <integer or null>
  },
  "cognition_execution": {
    "mode": "single_pass | two_pass | shadow_two_pass"
  },
  "condition_id": "<explicit evidence condition name>",
  "replicate_id": "<explicit replicate identity>",
  "scenario_ids": ["<one or more exact foundation-v2 scenario ids>"]
}
```

`auto` is unresolved policy and is rejected as evidence identity. The runner constructs the existing `CognitionExecutionEvidenceIdentity` with the exact same `execution_path` carried by the host condition, then places that identity directly in `ActualModelRunManifest.cognition_execution`.

Explicit `single_pass` uses the canonical `OpenAICompatibleProvider`. `two_pass` and `shadow_two_pass` use the already-implemented `OpenAICompatibleTwoPassProvider`, which keeps the same Chat Completions transport and provider-owned decoding configuration while exposing the conversation/extraction methods required by the merged COGP runtime.

Format v4 deliberately cannot carry the v3 total Cognitive Budget identity. The current #1386 total-budget diagnostics contract is single-generation evidence; combining it with non-single topology remains fail-closed until a separately owned bridge exists.

Format v4 also does not add or imply a per-request reasoning control. The current canonical provider has no per-request reasoning/thinking or bounded reasoning-budget carriage. A later ordinary-turn host attestation may establish the effective model-wide reasoning environment for reproducible A/B evidence, but that environment fact is not a Pass-2-only override.

### Frozen LM Studio Community capability

The canonical host CLI resolves one bounded host-only capability for
`gemma-4-12b-it-q4-k-m-lmstudio-community-v1`:

```text
capability:    lmstudio.gemma4.loaded-sdk.serialized-input.v1
implementation: lmstudio-js-loaded-model-counter
version:       2
mode:          exact
```

The bridge is in `relaylm.actual_model_lm_studio_counter`. It talks to the optional
`@lmstudio/sdk` package through a short-lived Node worker, so the SDK is not an
ordinary RelayLM runtime dependency. It selects exactly one loaded instance by the
attested serving request model key and uses that instance's `applyPromptTemplate(messages)` followed by
`countTokens(formatted_prompt)`. The messages are copied losslessly from the
`_request_body(...)` `messages` array; no second handwritten prompt is constructed.

`--counter-proof` must point to a secret-free host artifact with these evidence
classes:

- current RelayLM commit, frozen target id/size/SHA, request model, LM Studio
  version/build/deployment identity, SDK package/version, loaded model key/path/
  quantization, and a hash of the loaded instance reference;
- a request-model-to-loaded-instance binding verdict, a frozen-entrypoint linkage
  verdict, and a prompt-template parity verdict;
- at least the eight required synthetic probe classes: minimal identity/current
  event, Japanese input, ASCII input, accepted State, Working Context, retrieved
  MEMORY, Event Evidence, and a larger mixed input. Each records only a request
  identity/hash, SDK prompt count, server `usage.prompt_tokens`, the proof-attested
  accounted count, and raw/accounted equality;
- a controlled structured-output comparison proving whether the JSON-schema
  `response_format` adds prompt tokens, plus reproducible empty-user framing
  accounting.

The SDK-loaded model identity may be a logical serving key and its reported size may
be an aggregate package size. It must nevertheless link through host-local LM Studio
model metadata to the exact frozen GGUF entrypoint, including the target path, size,
and SHA-256. A family name, quantization label, or upstream tokenizer assumption is
not such a link. If that metadata hop is unavailable, the capability is rejected; it
is never downgraded to a heuristic or an unproven conservative estimate. No base URL,
API key, token, or secret value is stored in the counter identity or proof schema.

The serving endpoint may be a host-local deployment detail supplied by the condition
(for example, a LAN address when a WSL process cannot use the host loopback). It is
not a RelayLM runtime default and is not embedded in this capability implementation.

For the currently attested LM Studio serving path, the SDK-derived messages-only
count has a deterministic server prompt-token offset. The proof records that offset
from the same empty-user framing baseline and every required probe must satisfy:

```text
accounted_prompt_tokens = sdk_prompt_tokens + server_prompt_offset
accounted_prompt_tokens = server usage.prompt_tokens
```

The returned `SerializedInputTokenCount` uses the accounted total and the likewise
accounted framing baseline as its hard-fit authority. A raw SDK/server mismatch is
therefore visible in the proof; it is not mislabeled as direct equality. A different
serving path must produce a new proof rather than inheriting this offset.

The frozen LM Studio Community GGUF embeds tokenizer metadata, and the installed LM Studio 0.4.x SDK exposes native `applyPromptTemplate` and `countTokens` operations. Those facts do not by themselves prove that an OpenAI-compatible request has been counted by the loaded serving model. The host integration must prove the loaded model/artifact and the message/template mapping before registering an exact capability; otherwise it must register a demonstrated conservative bound or remain fail-closed. No separately published upstream `tokenizer.json` is assumed equivalent. The proof's controlled schema/no-schema pair must also show that the JSON-schema `response_format` contributes no hidden prompt tokens; if it does, that contribution must be included in the accounted counter.

The canonical OpenAI-compatible provider declares the `continuity_candidates` semantic channel even when a selected scenario does not require a Continuity proposal. Therefore an actual-model execution whose manifest declares `continuity_candidates` must also carry explicit `continuity_runtime`. This is a capability-safety requirement: the provider may emit an optional ContinuityCandidate on any turn, and ordinary-turn commit cannot truthfully accept or reject that proposal without a runtime. The runner never invents Continuity capacity or lifetime and no numeric default is implied.

## Target truthfulness

`target_id` selects repository-owned frozen metadata; it does not accept an arbitrary path or mutable model alias. The selected target metadata must itself declare the same `target_id`, then the supplied `--model-artifact` bytes must match that target's exact size and SHA-256.

The run manifest derives `model_artifact` and effective serving-tokenizer identity from the selected frozen target. This keeps two Q4_K_M files with different bytes as different evidence identities even when LM Studio displays the same model family and quantization label.

## Decoding truthfulness

`temperature`, `top_p`, and `seed` are optional only in the sense that the operator may explicitly set them to null. There is no numeric default in this runner.

`supported_decoding_controls` is also explicit. The OpenAI-compatible provider rejects requested controls not declared supported. The #1484 binding then verifies that the manifest records exactly the decoding controls and seed actually carried by the constructed provider.

This means a condition cannot claim `seed: 7`, for example, while sending no seed upstream. The topology-aware provider subclass does not add hidden decoding or reasoning controls; it consumes the same validated decoding mapping as the base adapter.

## Secrets and endpoint identity

The host condition may name an environment variable through `api_key_env`. The secret value is read only at execution time and is never copied into the manifest or LM Studio evidence envelope.

`base_url` is required to construct the live provider but is not persisted by the #1484 secret-free LM Studio binding. `deployment_identity`, exact LM Studio version/build, and request model are the citable runtime identity.

## Manifest generation

The operator does not hand-author an `ActualModelRunManifest`.

The runner derives it from:

- exact clean Git HEAD;
- explicitly selected frozen target and verification receipt;
- canonical scenario-set and Character-fixture revisions;
- the actual constructed provider P4 identity;
- explicit host condition values;
- for v4, the resolved `CognitionExecutionEvidenceIdentity`.

The #1484 binding rechecks target/provider/manifest agreement before scenario execution. This avoids metadata that merely looks reproducible but does not describe the provider request that actually ran.

## Output

Each successful selected scenario writes two immutable #1386 artifacts:

```text
<execution_id>.lm-studio.json
<verdict_id>.boundary.json
```

The execution artifact is persisted first. The runner then passes the already-produced `ActualModelScenarioExecutionResult` directly to the existing #1433 `evaluate_actual_model_deterministic_boundary(...)` implementation and persists its verdict sidecar. The host runner does not duplicate or reinterpret any deterministic State/Continuity rule.

A boundary `pass` means only that the observed RelayLM deterministic/runtime boundary satisfied the #1433 protocol invariants for that execution. A boundary `fail` remains citable evidence. It is **not** a judgment that the model response or semantic proposals were good or bad.

The command also prints a content-free index containing:

- RelayLM commit;
- selected target id;
- condition and replicate identity;
- scenario id;
- execution id;
- run id;
- execution artifact path;
- deterministic-boundary verdict id;
- deterministic-boundary outcome;
- deterministic-boundary artifact path;
- `score: null`.

Human/product-quality review remains a separate #1386 sidecar. The host runner does not synthesize human ratings, a model-quality verdict, or a composite score.

## Current boundary

The legacy v2 path continues to carry the already-existing explicit MEMORY/Event condition through `ExplicitBudgetConfiguration` with unchanged semantics.

The v3 path carries the complete caller-supplied total condition through `CognitiveBudgetRuntimeConfig` and the existing #1467 evidence bridge. It preserves the content-free serialized count, count mode, effective capacity/output reserve, degradation observations, fit/degraded-fit, and bounded pre-generation failure evidence. It does not change #1387 degradation order or semantics.

The v4 path carries explicit `single_pass`, `two_pass`, or `shadow_two_pass` topology into the existing #1540 execution evidence identity. Non-single modes use the already-merged two-pass-capable provider surface; explicit single-pass keeps the canonical base provider. V4 does not mix total Cognitive Budget and does not invent reasoning controls.

Accordingly:

- a v2 condition can produce the historical foundation-v2 real-model executions plus deterministic-boundary verdict sidecars;
- a v3 condition can produce total-budget evidence only when its provider/model counter capability is explicitly registered and truthful;
- a v4 condition can produce topology-aware execution evidence under an explicitly resolved COGP mode;
- actual citable COGP A/B comparison still requires ordinary-turn reasoning-environment attestation so both conditions bind the same effective environment;
- bounded Pass 2 reasoning remains unsupported for the current canonical provider and must not be represented as an applied C condition;
- total-budget evidence is experimental calibration evidence and does not select #1388 numeric defaults or runtime profiles;
- CAL2 candidates remain measurement inputs, not runtime defaults.

## Failure behavior

The command fails before semantic generation when, among other cases:

- checkout HEAD differs from `relaylm_commit`;
- checkout is dirty;
- `target_id` is outside the repository allowlist;
- selected target metadata does not match the condition target id;
- the GGUF bytes do not match the selected frozen target;
- a scenario id is outside canonical foundation-v2;
- the provider declares `continuity_candidates` but explicit Continuity Runtime identity is missing;
- a declared decoding control is unsupported;
- provider/runtime/manifest identity drifts at the #1484 binding boundary;
- a v3 total-budget condition has malformed total/policy/envelope identity;
- `model_context_window` differs from the effective host context;
- the declared serialized-input counter is unavailable, unreproducible, mismatched, or lacks the required exact/conservative truthfulness basis;
- a v4 cognition-execution condition is malformed, unresolved as `auto`, or uses a mode outside `single_pass`, `two_pass`, and `shadow_two_pass`;
- a v4 cognition-execution path disagrees with the host `execution_path`;
- a workspace path for the run already exists;
- an immutable evidence id already exists with different bytes.

After a model execution has completed, a filesystem/conflict failure while writing the boundary sidecar causes the command to fail rather than pretending the evidence chain is complete. The already-written execution artifact remains immutable evidence and no automatic semantic retry is introduced.

No automatic retry is introduced by this runner. V2/v3 preserve their existing single-generation semantics; v4 executes exactly the explicit topology recorded in its cognition-execution identity.
