# Gemma 4 cache reuse — post-matrix code narrowing

Diagnostic only. This note records exact-source narrowing after the synthetic cache-boundary × SWA matrix completed with the reported primary classification `NEITHER_INTERVENTION_RESTORES_IDENTITY`.

Reported terminal record SHA256:

`7052a49ccb4d861537427ac40bde899d57224a4912f66dceb0555195f719a393`

The terminal-record bytes are not committed by this note; the digest above is the externally reported identity only.

This note does not mutate protected `v1`, production behavior, RC1, or the completed matrix. The completed matrix remains spent and terminal. Any discriminator below is a new, separately-accounted diagnostic probe.

## Fresh repository state at narrowing time

- protected `v1`: `bf57fa331fc236bc52706c6424a4a11aab32f7b7`
- diagnostic handoff parent HEAD: `e970a34b9850d119a275d5d838dd48879025dcb3`
- exact llama.cpp target remains: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

## What the completed matrix ruled out as sufficient

Reported matrix outcome:

- M maximum reuse vs paired cold: API identity not restored
- A `n_ubatch=512`-aligned reuse vs paired cold: API identity not restored; first token diverged (`.` vs ` through`)
- F `--swa-full` maximum reuse vs paired cold: API identity not restored

Therefore neither of these interventions is sufficient by itself:

1. ending the reused prefix on a physical `n_ubatch` boundary;
2. replacing compact SWA storage with `--swa-full`.

This does **not** prove either mechanism is irrelevant. It proves only that neither restores cold-path API identity under the completed matrix configuration.

## Exact-source narrowing

### 1. `split_equal()` really does use a 512-token first ubatch

At exact e2d2, single-sequence `llama_batch_allocr::split_equal(n_ubatch, ...)` expands until adding another token would exceed `n_ubatch`.

For `n_ubatch=512` this gives the assumed physical geometry:

- 883 tokens -> `512 + 371`
- 2048 tokens -> `512 + 512 + 512 + 512`

So the failed A arm is not explained by an unexpected equalized split such as 442/441.

### 2. KV `prepare()` does not permanently pre-place all future ubatches

`llama_kv_cache::prepare()` simulates slot placement for the complete ubatch vector, records `slot_info`, then restores the original cells/heads before returning.

During real execution `llama_kv_cache_context::apply()` applies only the current ubatch and then recomputes `n_kv` from that current cache state.

Therefore the simple theory

> warm's first 512 tokens execute with an `n_kv` determined by all 883 tokens while cold's first 512 execute with an `n_kv` determined by all 2048 tokens

is not supported by this code path.

### 3. Aligned reuse actually moves the retained prefix to 512

The diagnostic aligned patch changes live-prefix `n_past` from raw LCP 865 to:

`floor(865 / 512) * 512 = 512`

and updates `pos_next` to the 512-token position.

The server later truncates `slot.prompt.tokens` to `n_past` and removes memory after the retained prompt position.

### 4. `seq_rm()` plus subsequent placement tends to restore the expected physical head/index sequence

`llama_kv_cache::seq_rm()` removes the sequence association for cells in the removed position range and moves the search head back to the first newly freed cell when appropriate.

`find_slot()` then searches from that head, and `apply_ubatch()` moves the head to the end of the chosen slot.

For the aligned single-sequence geometry, the obvious "head remains after the old warm suffix" explanation is therefore weak: removing positions >=512 naturally makes index 512 reusable again.

### 5. Outer logical batch metadata is narrower than first assumed

Inside `llama_context`, `n_outputs_all` is counted for the logical batch, but before each graph is processed the code recomputes `n_outputs` from the current ubatch and calls `process_ubatch()` with that current value.

So the graph does not simply consume the outer batch's total output count as the current ubatch output count.

### 6. A still-important difference remains: logical `llama_decode()` boundaries

The server explicitly processes pending prompt work in chunks of `llama_n_batch(ctx_tgt)`.

With the completed matrix configuration:

- `n_batch = 2048`
- `n_ubatch = 512`

this means physical ubatch alignment did **not** align logical decode boundaries.

For the relevant A paths:

#### warm A0, 883-token prompt

One logical prompt batch contains:

`[0..511] | [512..882]`

#### cold AC, 2927-token target

The first logical prompt batch contains:

`[0..511] | [512..1023] | [1024..1535] | [1536..2047]`

#### reuse A1 after retaining 512

A new request / new logical decode sequence starts at position 512:

`[512..1023] | [1024..1535] | [1536..2047] | [2048..2559] | ...`

Therefore position range `512..1023` is:

- cold: the **second physical ubatch inside an existing logical decode**;
- reuse: the **first physical ubatch of a new logical decode**.

That difference survived the prior alignment intervention.

## Upstream context

llama.cpp documents that prompt-cache reuse can be numerically non-neutral because backend results are not guaranteed bit-for-bit identical across different batch sizes / execution shapes.

Upstream issue #28368 additionally reports a reproducible `cache_prompt` numerical difference on Gemma 4 using the CPU backend and a non-recurrent model path. Its fresh-server cold value was reported reproducible across three fresh runs, while toggling `cache_prompt` on the warmed server reproduced two distinct margins. That evidence is not the same commit/backend/fixture as this probe, but it argues against treating CUDA Flash Attention, recurrent rollback, or compact SWA as necessary causes of the broader phenomenon.

## Highest-value next discriminator

Before an FA-off probe or intrusive KV hashing, test whether canonicalizing the **logical** prompt batch boundary restores identity.

Use the same frozen fixture and the same aligned-reuse binary/patch as completed Arm A, but change only:

```text
n_batch  = 512
n_ubatch = 512
```

Keep:

- exact llama.cpp/model/fixture identities
- aligned-reuse patch
- compact/default SWA
- no `--swa-full`
- `--flash-attn on`
- greedy / temperature 0
- one generated token per measured request
- same top-N observation
- same log verbosity

Do **not** include an FA-off arm in this discriminator.

### Predicted logical geometry

Warm 883:

```text
512 | 371
```

Cold target 2927:

```text
512 | 512 | 512 | 512 | 512 | 367
```

Reuse after aligned 512:

```text
      512 | 512 | 512 | 512 | 367
```

Thus:

- cached positions `0..511` are created as the first 512-token logical+physical chunk;
- cold positions `0..511` are created as the same first 512-token logical+physical chunk;
- from position 512 onward, reuse and cold use the same sequence of 512-token logical+physical chunks.

This is stronger than the completed A intervention, which aligned only the physical ubatch boundary.

## Minimal new probe

Exactly three measured requests are sufficient:

1. `L0`: warm 883, `cache_prompt=true`, one token;
2. `L1`: target 2927 on the same server, `cache_prompt=true`, aligned effective reuse 512, one token;
3. `LC`: target 2927 on a fresh paired-cold server, `cache_prompt=false`, one token.

Required hard path for L1:

- raw LCP = 865
- effective reuse = 512
- rollback to 366 absent
- prompt eval = 2415

Required hard path for LC:

- reuse = 0
- prompt eval = 2927

Record first-token identity, exact API-visible top-N identity, per-token reported deltas, prompt timings, cache counts, argv, full logs, and exact artifact hashes.

This is a new probe, not a retry or replay of the completed matrix.

## Interpretation

If `L1 == LC` at the same exact API identity criterion used by the completed matrix:

`LOGICAL_BATCH_BOUNDARY_EXPLAINS_RESIDUAL_DRIFT`

This would make canonical logical prompt chunking a strong production workaround/fix candidate. Candidate implementations would include running `n_batch == n_ubatch` or making prompt-cache creation/cold-prefill follow the same canonical logical chunk schedule, followed by separate performance qualification.

If `L1 != LC`:

`LOGICAL_BATCH_BOUNDARY_INSUFFICIENT`

Then the next discriminator should be direct retained-prefix KV-state identity, before attributing the effect specifically to Flash Attention:

- compare the stored state for the common prefix under matched logical+physical chunk geometry;
- if prefix KV differs, investigate backend/kernel/batch-history numerical provenance;
- if prefix KV is identical but continuation diverges, investigate request-resume graph/scheduler/cache metadata paths.

Only after that split should `--flash-attn off` be promoted as the next mechanism discriminator.

## Production boundary

No production change is authorized by this note.

Even if `n_batch=512` restores numerical identity, it may reduce prompt throughput or alter latency characteristics. Numerical restoration and performance cost must be measured separately before any RelayLM production policy change.
