# Actual-model crystallization host runner

RelayLM provides a dedicated host-local runner for producing citable **off-turn crystallization** evidence against an explicitly attested LM Studio target.

This runner connects existing authority only:

- frozen actual-model target metadata and local GGUF verification;
- the LM Studio serving-instance attestation established by the actual-model host tooling;
- the live LM Studio native reasoning capability/default attestation;
- `OpenAICompatibleCrystallizer` from the crystallization contract;
- `ActualModelCrystallizationManifest` and evidence artifacts from the actual-model crystallization evidence contract.

It does not change ordinary-turn host execution, crystallization semantics, Validator behavior, State grammar, or MEMORY authority.

## Execution path

```text
strict crystallization host condition
+ clean repo at exact RelayLM commit
+ canonical frozen target metadata
+ local GGUF size/SHA verification
+ exact Character fixture revision
+ LM Studio serving proof + live loaded-instance attestation
        |
        v
OpenAICompatibleCrystallizer
        |
        v
fresh copied Character workspace
        |
        v
run_actual_model_crystallization(...)
        |
        v
<run_id>.json CRY2 evidence
```

The host runner is implemented in:

```text
relaylm.actual_model_crystallization_host_runner
```

Run it as a module. No new package console entry point is required:

```bash
python -m relaylm.actual_model_crystallization_host_runner \
  --condition /path/to/crystallization-condition.json \
  --repo-root /path/to/relay-lm \
  --model-artifact /path/to/frozen-model.gguf \
  --serving-proof /path/to/lm-studio-serving-proof.json \
  --workspace-root /path/to/workspaces \
  --artifact-root /path/to/evidence \
  --lmstudio-node /path/to/node \
  --lmstudio-sdk-root /path/to/sdk-project
```

`--lmstudio-node` and `--lmstudio-sdk-root` are optional when the existing LM Studio SDK attestation machinery can resolve them from the host environment. The condition, model artifact, serving proof, workspace root, and artifact root are always explicit.

## Host condition

The current condition format is version 3 and is specific to off-turn crystallization:

```json
{
  "format_version": 3,
  "target_id": "gemma-4-12b-it-q4-k-m-lmstudio-community-v1",
  "relaylm_commit": "<exact-lowercase-40-character-git-sha>",
  "lm_studio": {
    "version": "<observed-version>",
    "build": "<observed-build>",
    "deployment_identity": "<operator-defined-host-deployment-id>",
    "base_url": "<explicit-openai-compatible-base-url>",
    "request_model": "<exact-loaded-request-model-key>",
    "api_key_env": null
  },
  "effective_context_window": 32768,
  "decoding": {
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 7
  },
  "supported_decoding_controls": [
    "temperature",
    "top_p",
    "seed"
  ],
  "reasoning": {
    "required_setting": "on"
  },
  "character_fixture": {
    "id": "<stable-fixture-id>",
    "path": "evaluation/actual_model/characters/<fixture>",
    "revision": "sha256:<exact-fixture-revision>"
  },
  "case": {
    "id": "<crystallization-case-id>",
    "version": "1"
  },
  "max_events": 100,
  "condition_id": "<condition-id>",
  "replicate_id": "0"
}
```

All fields are explicit. Unknown or missing fields fail closed.

The host condition is format version `3`. It requires an explicit reasoning
setting. The runner does not invent a `reasoning_effort` request parameter and
does not change the OpenAI-compatible Chat Completions transport.

The crystallization condition intentionally does **not** carry ordinary-turn-only fields such as:

- `scenario_ids`;
- Continuity runtime configuration;
- buffered/streaming cognitive execution path;
- legacy MEMORY/Event cognitive budgets;
- total cognitive-budget policy.

`max_events` is the existing crystallization input bound, not an ordinary cognitive Context budget.

The fixture path must be repository-relative and resolve inside `repo_root`. Its declared revision is verified from path names and file bytes before provider construction, and the same revision is checked again while copying the immutable fixture into the fresh mutable workspace.

## Target and LM Studio attestation

Preparation fails before crystallizer generation unless all of these agree:

1. `repo_root` is clean and its exact `HEAD` equals `relaylm_commit`;
2. `target_id` is one of the canonical frozen actual-model targets already registered by the ordinary host tooling;
3. the selected local GGUF matches the target's exact byte size and SHA-256;
4. the Character fixture matches the declared fixture revision;
5. the existing LM Studio serving proof matches the same RelayLM commit, target, request-model key, LM Studio version/build/deployment identity, artifact path, quantization, size, and SHA-256;
6. live LM Studio SDK attestation still resolves the loaded request-model instance to that frozen target artifact;
7. live `GET /api/v1/models` returns exactly one matching request model and one
   unambiguous loaded instance matching the existing serving proof;
8. that live model exposes `capabilities.reasoning.allowed_options` and
   `capabilities.reasoning.default`, the required setting is allowed, and the
   live default equals the required setting;
9. the condition's decoding controls are supported and are the exact controls passed to `OpenAICompatibleCrystallizer`.

For the current Chat Completions crystallizer, LM Studio's attested model
default is the effective reasoning control. RelayLM does not claim a
per-request reasoning override on this surface. Missing, malformed, ambiguous,
or mismatched reasoning metadata fails closed before workspace creation or
generation.

CRY3 reuses the existing #1508 serving proof machinery for **loaded-instance-to-frozen-artifact attestation**. The crystallization runner does not consume its token counts as a cognitive budget and does not claim a new token-counter semantic contract.

The SHA-256 of the validated serving-proof file is included in the CRY2 manifest `provider_identity` alongside the secret-free LM Studio environment identity. Therefore two runs cannot silently share a run identity while citing different serving-attestation evidence.

Endpoint URLs and API-key values are not stored in the CRY2 evidence manifest. If `api_key_env` names an environment variable, preparation fails closed when that variable is absent.

## Manifest derivation

The host runner derives the CRY2 manifest from verified or actually applied values:

- exact RelayLM commit from the condition/repository check;
- exact fixture ID and verified revision;
- secret-free LM Studio environment identity plus validated serving-proof digest;
- crystallizer adapter identity `relaylm.providers.OpenAICompatibleCrystallizer:v2`;
- frozen model-artifact identity and embedded-tokenizer identity from canonical target metadata;
- declared effective context window;
- the exact decoding controls supplied to the crystallizer;
- seed from those controls;
- structured-output schema version `relaylm_crystallization_output:v2`;
- evaluation contract `actual-model-crystallization-v2`;
- condition ID, `max_events`, and replicate ID.

The runner then verifies that the constructed crystallizer exposes the same request model and effective decoding controls before returning a prepared run.

The resulting manifest includes the deterministic reasoning identity: required
and effective setting, sorted live allowed options, live default, and the
control source/mode. Changing that identity changes the content-addressed run
ID.

## Fresh workspace and one-pass execution

Execution always targets:

```text
<workspace-root>/<condition-id>/<replicate-id>/<case-id>/
```

That workspace must not already exist. RelayLM copies the verified fixture into it and then executes exactly one existing `run_actual_model_crystallization(...)` pass.

The resulting evidence is persisted with the existing CRY2 immutable writer. Identical same-run evidence is idempotent; different evidence under the same run ID is rejected and requires a distinct `replicate_id`.

The crystallizer client is closed whether execution succeeds or fails.

## CLI output

A successful invocation prints only a compact execution receipt:

```json
{
  "format_version": 3,
  "suite": "actual-model-crystallization-lm-studio-v1",
  "relaylm_commit": "...",
  "target_id": "...",
  "condition_id": "...",
  "replicate_id": "0",
  "result": {
    "case_id": "...",
    "run_id": "...",
    "artifact_path": "..."
  },
  "score": null
}
```

This receipt is not a quality verdict. The citable semantic evidence is the CRY2 `<run_id>.json` artifact, and product-quality conclusions belong to the bounded seven-axis review contract.

## Current limitation

CRY3 makes real target-model crystallization execution reproducible from an attested host. It does **not** include a canonical crystallization-quality fixture, does not execute the user's local LM Studio from CI, and does not establish that the current prompt improves taxonomy/key drift, transient over-persistence, correction handling, temporal nuance, MEMORY organization, or semantic stability.

CRY8 evidence predates this reasoning identity and therefore must not be used
for causal attribution of Thinking ON versus OFF. CRY9B is the first planned
canonical crystallization stability tranche with explicit Gemma reasoning
attestation; it remains a fresh tranche, not a controlled ON/OFF comparison
against CRY8.

Those are subsequent actual-model evidence transactions. Any prompt/schema refinement remains evidence-driven and separately owned by the crystallization provider contract.
