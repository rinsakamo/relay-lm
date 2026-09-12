# Production-context unresolved-only physical discriminator

Status: repository-owned one-shot llama.cpp carriage for the merged #2672 discriminator. Repository support alone is not physical evidence.

This path tests the next #2616 causal factor after #2664: whether multi-kind Continuity set/no-op/resolve decision competition is sufficient to suppress the already formed T2 `unresolved` meaning under otherwise production-context conditions.

## Held fixed

The transaction keeps fixed:

- current `continuity-lifecycle-v1` T1/T2 contents and Stage R revision;
- ordinary production T1 two-pass execution;
- T1 accepted Continuity entering T2;
- actual production T2 Pass 1 response;
- full T2 `CognitiveInput` and provenance;
- retained #2529 formed observation with run-local T2 source rebound;
- canonical Continuity wire/source/epistemic-role and unresolved lifecycle semantics;
- decoding and explicit reasoning-OFF controls;
- native structured-output transport and canonical candidate/source validation.

The T2 diagnostic removes only referent/active_task and multi-kind projection responsibility. The candidate item JSON Schema remains the same as Continuity-only and is not narrowed to `kind=unresolved`.

## Repository entrypoints

Controller preflight should target:

```text
inner module:
relaylm.actual_model_stage_r_llama_cpp_production_unresolved_only_transaction

wrapper module:
tools.v1_stage_r_llama_cpp_production_unresolved_only_wsl
```

The wrapper requires one explicit repo-external retained-formation artifact using the canonical mechanically validated #2529 envelope:

```json
{
  "diagnostic": "epistemic-formation-t2",
  "mechanical_validation": "pass",
  "items": [
    {
      "subject_span": "<exact current-input span>",
      "unknown_evidence_span": "<exact current-input span>",
      "source_event_id": "<authoritative retained T2 Event ID>"
    }
  ]
}
```

For this transaction, `items` contains exactly one observation. The item contains exactly these three fields and no others:

```text
subject_span
unknown_evidence_span
source_event_id
```

`diagnostic` must equal the canonical epistemic-formation diagnostic identity and `mechanical_validation` must equal `pass`. The host validates the retained source against current Stage-R authority and rebinds it to the run-local T2 Event before model-facing use.

No Continuity kind/key/op/value, expected answer, scorer label, repair hint, or other semantic answer belongs anywhere in the retained artifact. The envelope preserves provenance and prior mechanical validation; the exact three-field restriction applies to the single observation item, not to the top-level artifact.

## Exactly-once semantic ceiling

```text
T1 production Pass 1                   <= 1
T1 production Pass 2                   <= 1
T2 production Pass 1                   <= 1
T2 unresolved-only retained Pass 2     <= 1
formation regeneration                  = 0
T3                                      = 0
retry/replay/reseed/fallback             = 0
LM Studio                                = 0
FastCal                                  = 0
```

T1 Pass 2 must commit before T2 starts.

## T2 request evidence

Before the single diagnostic generation the host retains create-once artifacts for:

1. ordinary production request;
2. ordinary production request plus retained overlay;
3. canonical Continuity-only request;
4. canonical Continuity-only request plus retained overlay;
5. canonical unresolved-only request;
6. canonical unresolved-only request plus the identical retained overlay;
7. the #2672 factor-delta receipt;
8. the retained/run-local provenance binding receipt.

The generated body is exactly item 6. Parsing is performed by the merged #2672 `parse_unresolved_only_completion(...)` contract. The physical host does not rewrite the request or parser.

## Interpretation boundary

The host stops at protocol/mechanical classification and records `semantic_verdict=not_run`.

Later zero-generation review may infer:

```text
valid unresolved-only T2 emits the formed unresolved meaning
  -> strongly supports multi-kind Continuity decision competition

valid unresolved-only T2 still omits/materially misprojects it
  -> multi-kind projection responsibility is not sufficient
  -> next isolate accepted lifecycle context versus Pass1/full-input burden

invalid T1 parity / provenance / transport / schema / reasoning
  -> no causal inference
```

A positive discriminator is not production qualification and does not unblock #1388 FastCal.

> Keep the production context; remove only the competing Continuity decisions.
