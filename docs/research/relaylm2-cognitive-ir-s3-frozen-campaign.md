# RelayLM 2.0 Cognitive IR — frozen S3 semantic-invariance campaign

Scientific owner: #2211. Preregistration owner: #2461. Implementation owner: #2466. Physical procedure owner: #2363.

Canonical preregistration schema:

```text
relaylm2-cognitive-ir-s3-prereg-v1
```

Canonical preregistration SHA-256:

```text
2448d147e8bbb1ab17446fbc54e464fa6d8746a18d19fad7f92627a039384c69
```

This repository surface encodes that frozen preregistration. It does not reinterpret the #2457 S2 smoke, does not change RelayLM v1, and does not authorize architecture or ontology mutation.

## Frozen campaign

The task class remains the S2-admitted bounded class: modulus 10, vector width 4, identity permutation, non-zero coordinate offsets in 1..3, four source examples, and no-wrap generated application inputs. Twelve fresh deterministic families are divided into four fixed shards:

```text
shared    408671368 1152794703 2087212991
null      292304948 865761977 509247258
mismatch  1201776179 630460040 1118062807
shift     5662972 445070522 1853464615
```

Every family forms P2 ordinary summary, P3 semantic cache, and P4 Memory+Structure exactly once from the same public source packet. P5 and P6 are deterministic derivatives of the exact P4 formation. P4/P6 canonical semantic digests must match and P4/P5/P6 must retain one-formation lineage before probes proceed.

Each non-shift family executes:

```text
3 formation
7 canonical P0-P6 held-out probes
8 P4/P6 meaning-preserving surface probes
16 P4/P6 semantic-intervention probes
7 P0-P6 option-value probes
= 41 semantic calls
```

Each shift family adds two P4/P6 preregistered pre-shift anchors, giving 43 calls.

The exact shard ledger is therefore:

```text
shared    123
null      123
mismatch  123
shift     129
----------------
total     498 semantic Chat Completions
          996 exact /input_tokens requests
```

Shard order is fixed `shared -> null -> mismatch -> shift`. The campaign stops on the first non-completed shard. There is no shard retry, replay, reseed, alternate family, model swap, context change, provider fallback, or LM Studio fallback.

## Surface and semantic panels

P4/P6 meaning-preserving surface variants are frozen as:

```text
S1_ROLE_LABEL_NEUTRAL
S2_KEY_RENAME_REORDER
S3_LOSSLESS_LIST_PROSE_SERIALIZATION
S4_PROMPT_PARAPHRASE_FORMAT
```

Every rendered surface material is deterministically canonicalized back to the original semantic payload before it is eligible for scoring.

Meaning-changing interventions are frozen as:

```text
M1_RULE_OFFSET_FLIP
M2_EXCEPTION_CHANGE
M3_SCOPE_CHANGE
M4_RELATION_REPLACE
```

Each is crossed with `STALE_ORIGINAL` and `UPDATED_INTERVENED`. A provenance-root replacement remains audit-only and consumes no provider call.

The all-arm option-value query is unchanged from #2461: return the smallest source-example index whose input vector has maximum coordinate sum, with smallest-index tie break. P4/P5/P6 may use only their declared reconstruction path; P2/P3 receive no rescue retrieval.

## Primary discriminator

The executable gate preserves the preregistered thresholds:

```text
semantic_intervention_effect >= 0.20
surface_perturbation_effect <= 0.15
semantic_intervention_effect - surface_perturbation_effect >= 0.15
```

Effects are paired correctness deltas, reported by shard and pooled. They are not promoted into an IID significance claim. The transaction summary leaves the final #2211 scientific verdict conservative; `architecture_consequence` remains `NONE` regardless of result.

## Observable Cognitive Work

The runner records external work only: actual model calls, exact input/output tokens, projected bytes, reconstruction/retrieval operations, deterministic verification operations, and failures. It does not estimate hidden chain-of-thought work. Natural cost is preserved rather than padded with filler.

## llama.cpp physical transaction

The stable future WSL command is:

```text
python3 -m tools.v2_cognitive_ir_s3_llama_cpp_wsl
```

The WSL envelope binds the inner process to the exact clean checkout through `cwd=<repo>` and `<repo>/src` first on `PYTHONPATH`, while relocating only writable transaction state to a fresh repo-external HOME. Real llama.cpp and GGUF paths remain operator-home identities.

The inner transaction owns one campaign invocation. It acquires the same kernel-backed localhost/GPU lifecycle lock and creates one fresh llama-server lifetime and unique log for each planned shard. Every shard uses:

```text
--host 127.0.0.1
--port 1234
-ngl 999
-c 8192
-np 1
--no-context-shift
-lv 4
--log-prefix
--log-timestamps
--log-file <unique shard log>
```

Every semantic request carries `reasoning_effort="none"`, temperature 0, request seed null, maximum output 512, and timeout at least 1800 seconds. llama.cpp exact input accounting sends the exact generation body plus one empty-message framing body before each semantic request. Response `usage.prompt_tokens` must equal the exact full count and any exposed reasoning token count must be zero.

Material attestation has two deliberately distinct costs. At the start and end of every shard, the transaction performs full runtime/material attestation, including SHA-256 validation of the llama-server binary and GGUF against the frozen controller identity. Before every semantic request it instead performs a lightweight live-binding check: the owned server process must still be alive; `/health`, `/v1/models`, `/props`, and `/slots` must match the shard-start model/build/path/ftype/context/slot identity; and binary/GGUF filesystem stat identity must remain unchanged. This preserves a per-request drift gate without re-reading the multi-gigabyte GGUF 498 times. A completed campaign therefore requires exactly 498 lightweight pre-call checks and eight full shard-boundary material attestations.

The full runtime/material identity must remain equal across all four independently started shard servers. Any boundary hash mismatch, lightweight live-binding drift, process exit, context/slot change, or stat change makes the current shard incomplete and prevents all later shards. The transaction never contacts LM Studio.

A completed campaign is citable only within the frozen same-model S3 scope if all four shards complete and the exact 498/996 ledger, 498 lightweight live-binding checks, eight full material attestations, runtime/material binding, lineage/equality checks, and cleanup conditions pass. Any incomplete shard makes the transaction `S3_INCOMPLETE` and `citable=false`; later shards are not executed.

Repository implementation/CI under #2466 performs no model, provider, GPU, S2, or S3 physical execution. A later fresh physical owner must reacquire repository/runtime/material authority before consuming the one-command wrapper.
