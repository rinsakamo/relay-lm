# Production-context Continuity-only physical discriminator

Status: repository-owned one-shot llama.cpp carriage for the merged #2624 discriminator. Repository support alone is not physical evidence.

This path tests one remaining #2616 causal factor: whether simultaneous new-State extraction / the combined State+Continuity output responsibility is sufficient to suppress an already formed `unresolved` meaning under full production context.

## Held fixed

The transaction keeps fixed:

- current `continuity-lifecycle-v1` T1/T2 contents and Stage R revision;
- ordinary production T1 two-pass execution;
- T1 accepted State and Continuity entering T2;
- actual production T2 Pass 1 response;
- full T2 `CognitiveInput` and provenance;
- canonical Continuity rules/examples/component;
- retained #2529 formed observation with run-local T2 source rebound;
- decoding and explicit reasoning-OFF controls;
- native structured output transport and canonical candidate/source validation.

The only diagnostic Pass 2 responsibility removed is new-State projection:

```text
production Pass 2
  -> state_candidates + continuity_candidates

Continuity-only diagnostic Pass 2
  -> continuity_candidates only
```

Accepted State remains in `CognitiveInput`.

## Repository entrypoints

Controller preflight should target:

```text
inner module:
relaylm.actual_model_stage_r_llama_cpp_production_continuity_only_transaction

wrapper module:
tools.v1_stage_r_llama_cpp_production_continuity_only_wsl
```

The wrapper requires one explicit repo-external retained-formation artifact. The retained payload remains the same opaque three fields used by #2611:

```text
subject_span
unknown_evidence_span
source_event_id
```

No Continuity kind/key/op/value, expected answer, scorer label, or repair hint belongs in that artifact.

## Exactly-once semantic ceiling

```text
T1 production Pass 1                   <= 1
T1 production Pass 2                   <= 1
T2 production Pass 1                   <= 1
T2 Continuity-only retained Pass 2     <= 1
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
2. ordinary production request plus retained-formation overlay;
3. canonical Continuity-only request;
4. canonical Continuity-only request plus the identical retained overlay;
5. the non-model-facing factor-delta receipt;
6. the retained/run-local provenance binding receipt.

The generated body is exactly item 4. Parsing is performed by the merged #2624 `parse_continuity_only_completion(...)` contract. The physical host does not rewrite either the request or the completion parser.

## Interpretation boundary

The host stops at protocol/mechanical classification and records `semantic_verdict=not_run`.

Later zero-generation review may infer:

```text
valid Continuity-only T2 emits the formed unresolved meaning
  -> strongly supports State/Continuity co-extraction or combined-schema interference

valid Continuity-only T2 still omits/materially misprojects it
  -> State co-extraction is not sufficient
  -> continue #2616 with lifecycle-context / multi-kind / Pass1/full-input factors

invalid T1 parity / provenance / transport / schema / reasoning
  -> no causal inference
```

A positive discriminator is not production qualification and does not authorize a permanent multi-call production split. It does not unblock #1388 FastCal.

> Remove one responsibility once; preserve everything else and let the evidence discriminate.
