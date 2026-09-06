# RelayLM 2.0 Cognitive IR S2 host v2 — post-timeout execution contract

Status: owner-local supplement for #2211. This document changes only the physical S2 host boundary. It does not change P0-P6 semantics, seed, source packet, target task, representation formation instructions, or S3 admission criteria.

## Why this supplement exists

The first two physical S2 transactions exposed host-boundary defects without producing scientific evidence.

1. A preflight transaction correctly failed before any model request when a loaded-model authority could not be established.
2. A later LM Studio transaction established the loaded model but the first `form-p2` request exceeded the generic OpenAI-compatible client's 120-second timeout. LM Studio subsequently completed generation after the client had already timed out.
3. That failed physical request was persisted as `provider_calls=0` because the original host counted only completed exchanges.
4. The LM Studio response log showed a reasoning-only completion with an empty visible message. Hidden reasoning must not be silently promoted to the answer expected by S2.

These are host/protocol findings only. They do not establish or weaken any Cognitive IR treatment.

## Provider attempt accounting

The durable physical ledger must distinguish:

```text
provider_attempt
!=
provider_completion
```

A request that reaches the provider and later times out or fails still consumed physical Cognitive Work.

The v2 host therefore preserves historical `provider_calls` as completed exchanges for compatibility and additionally persists:

```text
provider_attempts
provider_completions
```

Required examples:

```text
successful ten-call smoke:
  provider_attempts    = 10
  provider_completions = 10
  provider_calls       = 10

first request times out:
  provider_attempts    = 1
  provider_completions = 0
  provider_calls       = 0
```

Failed work must not disappear from the Cognitive Work ledger merely because no completion object returned.

## Transport identity is part of the frozen physical condition

The physical S2 identity must now contain a transport mapping that exactly matches the constructed client.

At minimum it freezes:

```text
API / wire contract
model + loaded instance identity where applicable
transport timeout
reasoning policy
maximum output tokens
context length
stateful-storage behavior
request-level decoding overrides or their explicit omission
```

This is an execution identity, not a cognitive primitive.

A transport timeout is a safety bound, not a scientific latency threshold. S2 does not interpret latency as a treatment winner. The timeout must therefore be explicit and sufficiently loose to avoid turning an incidental client default into the experiment.

## LM Studio physical path

For the next LM Studio S2 transaction, use the native public REST interface rather than relying on the OpenAI-compatible endpoint for a provider-specific reasoning contract.

Current frozen candidate transport for the next fresh smoke:

```text
api               = lmstudio-native-chat-v1
reasoning         = off
max_output_tokens = 512
context_length    = 8192
timeout_seconds   = 300
store             = false
temperature       = omitted
top_p             = omitted
```

The values above are frozen before the next result is observed. They must not be tuned arm-by-arm or after seeing the outcome.

`reasoning=off` is not a claim that reasoning is cognitively undesirable. It is an output-contract control: S2 asks whether the declared representation can be consumed to produce the visible protocol answer. Hidden reasoning is not the requested answer and is not rescued into one after the fact.

The native LM Studio API supports explicit `reasoning`, `max_output_tokens`, and `context_length` request fields. The adapter must require exactly one non-empty visible message and reject tool output, hidden-reasoning-only output, loaded-instance drift, malformed token statistics, or any other protocol mismatch.

For token accounting, native `total_output_tokens` is charged as model output work. With `reasoning=off`, `reasoning_output_tokens` must be zero for this S2 path.

## Single JSON envelope normalization

A later fresh S2 transaction reached all three formation calls and exposed a narrower parser defect: the model returned the required P4 JSON object inside a single Markdown JSON code fence. Treating that wrapper as a semantic failure would make an incidental formatting convention an admission gate, which conflicts with #2211's separation of semantic effects from nuisance surface effects.

For model outputs whose contract is exactly one JSON value, the S2 parser therefore normalizes only this surface-equivalent pair:

```text
{"key":"value"}

```json
{"key":"value"}
```
```

The accepted fenced form must satisfy all of the following:

- the complete visible response is exactly one code fence;
- the opening fence has either no info string or exactly `json`;
- there is no prose before or after the fence;
- there is no nested or second fence;
- the payload is non-empty;
- after unwrapping, the existing strict JSON parser and semantic validators run unchanged.

The same envelope rule applies to the P4 formation JSON object and to target JSON-array responses. It does **not** turn arbitrary prose into JSON and does not inspect hidden reasoning.

Still rejected:

```text
Here is the answer:
```json
{...}
```

```python
{...}
```

```json
{...}
```
extra prose

multiple fenced values
malformed JSON
duplicate JSON members
non-standard numeric constants
wrong P4 keys
non-bijective permutation
invalid offset range
wrong modulus
```

This normalization is a protocol-surface repair only. It does not retroactively reinterpret the historical failed transaction as a successful arm result and does not authorize semantic retry.

## No semantic retry

This host repair does not authorize changing:

```text
regime           = shared
seed             = 2211
step_index       = 0
examples_visible = 0
P0-P6 definitions
P4/P6 semantic identity rule
formation prompts
target prompt/evaluator semantics
model identity after the run begins
```

The next physical transaction is fresh and uses a new empty detached artifact root.

Any provider failure, live-binding drift, malformed visible response, unexpected reasoning output, output truncation/protocol failure, or undeclared extra request remains terminal.

## S3 gate remains unchanged

```text
COMPLETED + MECHANICALLY_DISCRIMINATING
  -> a new S3 preregistration transaction may begin

otherwise
  -> S3 remains BLOCKED
```

A completed S2 remains `NON_CITABLE_S2_SMOKE`. It cannot choose a winning IR or mutate architecture authority.
