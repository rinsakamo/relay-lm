# #3013 resident-SWA cache repair CUDA qualification

Status: proposal-only qualification carriage. Repository readiness does not
authorize a physical run or establish `CACHE_CORRECTNESS_FIXED_LOCAL_PATCH`.

## Ownership and queue boundary

Issue #3013 owns this candidate qualification contract and its wrapper. It
consumes the existing actual-model llama.cpp transaction and the #2660
physical-execution queue. The queue registry receives one data-only target row
for `diagnostic:3006-cache-correctness-repair-qualification`; the queue engine,
lease, receipt, target schema, and invocation lifecycle remain owned by
`physical_execution_queue` and are not changed here.

The target is preparation-only until a later #3013 comment grants one exact
descriptor. The checked-in descriptor policy remains
`PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY`.

## Repaired candidate

The candidate applies the prepared #3006 production patch to llama.cpp base
`e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d` (base tree
`6d39fd93dc91fc0a4bc86dffe9782d4f26318004`). The production patch SHA256 is
`e054a1a6e02567eaa72d56fb3ca4fe29c5f59f6fdd07d7b7618bbb21ba137e18`; its
resulting production tree is
`84cf2ff7781a3228e7ff65ec95083a4de6534cec`. Its only behavior change is the
demonstrated resident-SWA equality boundary: use strict `pos_min > threshold`
when `n_swa > 0`, retaining the prior `>=` behavior when `n_swa == 0`. This
does not establish a universal maximal-SWA-reuse policy; conservative restore
cases outside this boundary remain valid.

A separate #3013 trace patch records checkpoint-decision and prompt-reuse
facts without changing cache behavior or recording prompt contents. Its SHA256
is `84df09168eea2299bbb1c73be051a08f426a866b1428b95a6a1f0416050c54e3`, and
the resulting qualification-observed source tree is
`e05cb0eef33743c73ead9eb0185fb2e1f846a6f5`. It records an explicit
empty-slot/full-prompt row for the first generation in each fresh server.
The candidate builder applies both patches to a clean exact-base clone and
rejects any other source tree.

The CUDA builder records the source and patch hashes, production and observed
trees, CMake cache/configuration, C++ and CUDA compiler identities, toolkit,
architecture flags, build commands, relevant environment, binary hashes, and
resolved shared-library paths and hashes. It builds Release shared libraries
and `llama-server` for CUDA architecture 86, with checkpointing enabled and
`--swa-full` absent. Candidate startup uses one slot and context 8192. The
runtime gate checks the process argv and environment, rechecks the live loaded
library closure before each post, and requires the CUDA backend, CUDA runtime,
cuBLAS, and driver libraries to be mapped from the frozen closure.

The only model is
`/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf` with SHA256
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`. The
builder and descriptor gate reject a different path or digest.

## Matched comparison

The qualification runs two isolated arms, cold first and reused second. Each
arm owns one fresh candidate server process, one slot, and fresh installed
profile roots. The slot is retained only within that arm, across this frozen
generation order:

1. buffered Pass1;
2. buffered Pass2;
3. streaming Pass1;
4. streaming Pass2.

The two arms use separate server processes and fresh copies of the same
canonical profile fixture. Profile files remain in their arm evidence roots
for review, but no server or profile state is shared across arms.

The cold arm forwards RelayLM's `cache_prompt=false` generation requests
unchanged. The reused arm changes only the candidate transport's generation
`cache_prompt` field from false to true. RelayLM's product provider policy stays
cache-off in both arms. Input-token requests remain byte-identical in both
arms. The descriptor freezes the exact full/framing counter request order as
well as the four generation phases.

Model, quantization, canonical fixture and scenario, prompt/state/continuity
semantics, reasoning mode `none`, temperature `0`, top-p `1`, omitted seed
field, `max_tokens=256`, request-construction source, context, GPU geometry,
and treatment policy remain fixed. Pass2 is constructed after its Pass1
response. Each exact eventual body is therefore written, fsynced, hashed, and
checked against the matching treatment immediately before one candidate POST;
only the explicit serialized Pass1 response region is normalized when
comparing the arms.

The maximum transaction is two candidate server/model-load attempts, eight
generation requests, 24 input-token requests, and 32 model-facing POSTs. A
durable per-request record and both exact request bodies are fsynced before the
single upstream POST. That durable record is the request-consumption boundary.
The target checks the exact #3013 authority comment, descriptor hash, local
clean `v1` checkout, and fresh `origin/v1` before writing the record and again
immediately before sending.

## Evidence and pass contract

Per-generation observables include request id/order, task and slot ids, input
tokens, LCP, live position bounds, effective SWA size and threshold, candidate
checkpoint set, selected checkpoint or `NONE`, pre/post `n_past`, prompt-eval
tokens, reused `cache_n`, finish reason, native structured-output validity,
provider response parsing, and read-only State/Continuity materialization
facts. Semantic State and Continuity payloads are not copied into observer
evidence.

The repaired equality-boundary cell must show resident required SWA history,
`pos_min == pos_min_thold`, no older checkpoint rollback, and the live reusable
prefix retained. The reused arm must show real positive `cache_n` and fewer
processed prompt tokens than that same request's full input-token count where
a prefix is reusable. The first empty-slot request is not treated as a reuse
cell. Cold requests must process their full prompt.

The candidate's deterministic `test-chat` regression also proves that
checkpoint restore still occurs when required history is missing. It checks
the two frozen missing-history controls in source tests; no extra model
generation is spent for this control.

Both arms must complete four generations with `finish_reason=stop`, valid
native Pass2 structured output, successful RelayLM provider parsing, and valid
State/Continuity materialization. Arms are semantically matched on their
frozen request surface; byte-identical generated text is not required.

Any failed gate or request stops the first transaction. There is no retry,
replay, reseed, fallback, alternate port/root, or manual completion of a later
arm. A failure before a durable request record is mechanically recorded as
unconsumed; a failure after that record is consumed even if the POST does not
complete. The target seals request records, attempt counts, and failure state.

Preparation must end at
`CACHE_CORRECTNESS_REPAIR_CUDA_QUALIFICATION_READY`, with physical calls,
model loads, and generation requests all zero and the attempt unconsumed. Only
a later exact #3013 execution-authority comment may authorize a physical run.
The discarded #3006 Layer0 projection interpretation is outside this owner
and is not used as live-activation evidence.
