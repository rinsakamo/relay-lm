# Semantic-to-Continuity projection physical carriage

Status: repository-owned preparation contract for a future exactly-once RelayLM 1.0 llama.cpp physical owner under #2539.

This path exists only to answer the next discriminator after #2529 established `FORMATION_PRESENT`:

```text
retained formed epistemic observation
  -> canonical Continuity projection
```

It does not regenerate epistemic formation and does not change production cognition.

## Repository components

The physical path is:

```text
controller preflight
  -> tools.v1_stage_r_llama_cpp_semantic_continuity_projection_wsl
  -> relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection_transaction
  -> transaction-owned llama-server
  -> relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection
  -> one projection generation
```

The generic WSL wrapper and generic llama.cpp transaction carry diagnostic-specific arguments opaquely. They do not read or interpret retained semantic evidence.

The selector declares the producer-result contract explicitly:

```text
host module:
  relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection

host summary:
  semantic-continuity-projection-t2-summary.json
```

## Retained-formation binding

The future physical controller supplies one explicit retained #2529 mechanical-observation artifact:

```text
--retained-formation-artifact <path>
```

The dedicated host, before the scientific projection generation:

1. requires a readable UTF-8 JSON file;
2. computes its exact SHA-256;
3. requires diagnostic identity `epistemic-formation-t2`;
4. requires `mechanical_validation=pass`;
5. accepts only non-empty formed observation items containing exactly:
   - `subject_span`;
   - `unknown_evidence_span`;
   - `source_event_id`;
6. reconstructs the current Stage R `continuity-lifecycle-v1` T2 `CognitiveInput`;
7. revalidates the source Event ID and both source spans against that current T2 Event through the merged semantic-projection primitive.

Any expected Continuity kind, key, operation, value, oracle answer, or evaluator-provided mapping inside a retained item is rejected rather than carried into the model request.

The retained artifact is empirical formation evidence, not production truth or new Grounding.

## Controller setup

Before a future physical owner is spent, reacquire fresh GitHub/repository authority and create a fresh exact clean checkout plus repo-external virtual environment as required by the canonical llama.cpp controller-preflight contract.

The preflight must use the same interpreter that will invoke the wrapper. Because this diagnostic wrapper has a required argument, pass it through the preflight's opaque wrapper-argument tail. `--wrapper-args` must be the final preflight option:

```bash
"$VENV/bin/python3" -m tools.v1_llama_cpp_controller_preflight \
  --repo-root "$REPO_ROOT" \
  --expected-head "$EXPECTED_HEAD" \
  --expected-tree "$EXPECTED_TREE" \
  --inner-module relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection_transaction \
  --wrapper-module tools.v1_stage_r_llama_cpp_semantic_continuity_projection_wsl \
  --wrapper-args \
  --retained-formation-artifact "$RETAINED_FORMATION_ARTIFACT"
```

A valid preflight remains non-generative and must report:

```text
classification = READY
wrapper_consumed = false
server_calls = 0
host_calls = 0
provider_calls = 0
semantic_calls = 0
```

Then execute exactly the emitted `one_shot_command`. Do not reconstruct the command with another interpreter.

The physical controller should separately prove during restartable controller setup that the intended retained artifact path is present. Semantic structure validation remains host-owned so the generic controller does not learn fixture or diagnostic semantics.

## Physical treatment

Unless a later owner explicitly and freshly changes the treatment, preserve the current qualified llama.cpp condition:

```text
origin        http://127.0.0.1:1234
OpenAI base   http://127.0.0.1:1234/v1
context       8192
slots         1
context shift disabled
GPU offload   -ngl 999
reasoning     explicit OFF
wire          reasoning_effort=none
structured    native JSON Schema
LM Studio     0
FastCal       0
```

Derive the GGUF target from the selected current llama.cpp host's `DEFAULT_TARGET_PATH`; do not select another same-family artifact by filename similarity and do not add a manual `--target-path` override merely to satisfy local bytes.

## Scientific accounting

The host performs exactly one scientific generation:

```text
projection generation = 1
formation generation = 0
Pass 1 generation = 0
State generation = 0
T3 generation = 0
semantic retry = 0
replay = 0
reseed = 0
fallback = 0
LM Studio = 0
FastCal = 0
repository mutation = 0
```

Non-generative physical admission/input-count requests remain separately accounted by the current llama.cpp carriage and are not extra scientific generations.

Once the future physical owner's repository wrapper is invoked, that owner is consumed. No same-owner retry or manual rescue is permitted after that boundary.

## Required evidence

A mechanically successful host retains at least:

- exact RelayLM HEAD/tree/Core identity;
- current Stage R scenario authority and T2 Event identity;
- retained formation artifact path and SHA-256;
- mechanically validated formed observation fields;
- exact projection request body;
- raw completion envelope/content;
- parsed canonical Continuity candidates;
- completion/reasoning metadata;
- exact input-count and physical-binding evidence;
- generation/retry/fallback accounting.

A valid completion terminates as:

```text
PROTOCOL_VALID_SEMANTIC_REVIEW_REQUIRED
```

The physical host and Local Codex do not decide P1 versus P2.

## Zero-generation review

After a future physical owner returns retained evidence, #2539 reviews it without another generation:

```text
canonical projection present
  -> reject P1 semantic-to-IR inability
  -> support P2 production multiplexing/interference

canonical projection absent or materially wrong
  -> support P1 semantic-to-IR projection failure

transport/protocol invalid
  -> no P1/P2 semantic inference
```

A successful projection is diagnostic evidence only. It is not a production fix and does not authorize prompt, parser, validator, lifecycle, oracle, or scorer changes by itself.

## Repository-preparation boundary

Issue #2564 owns only repository preparation. It must perform zero model/provider generations and must be merged/reconciled before a new physical owner is created.

PR #2441 remains a separate Continuity writer and must not be modified by this lane. #1388 remains blocked until the broader actual-model product-quality chain earns an unblock.

## Principle

> Hold formation fixed, bind its provenance explicitly, and vary only the projection boundary.
