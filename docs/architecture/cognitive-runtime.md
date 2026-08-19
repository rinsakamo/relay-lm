# Cognitive Runtime

Ordinary-turn cognition is governed by `docs/contracts/cognition-execution-policy.md`.

RelayLM 1.0 recognizes:

```text
single_pass
two_pass
shadow_two_pass
auto
```

Execution topology may vary, but semantic authority does not:

```text
model cognition
      |
      v
response + proposal channels
      |
      v
existing deterministic State / Continuity validation
      |
      v
RelayLM authority
```

`response` is user-visible natural language. `state_candidates` and `continuity_candidates` remain non-authoritative proposals.

## `single_pass` runtime

The existing ordinary-turn APIs retain the one-generation baseline:

```text
CognitiveInput
      |
      v
provider.generate / stream_generate
      |
      v
CognitiveOutput
  response
  state_candidates
  continuity_candidates
      |
      v
common deterministic commit boundary
```

Buffered execution performs one `provider.generate()` call. Streaming performs one `stream_generate()` call. The complete valid output is required before the Assistant Event, State validation, and Continuity validation commit.

## `two_pass` runtime

COGP3 adds an explicit response-first runtime in `relaylm.two_pass_turn`:

```text
prepare one originating CognitiveInput
          |
          v
Pass 1: conversation
          |
          +--> complete visible response
          +--> Assistant Event
          |
          v
return response-first turn result
          |
          +---- background ---->
                            Pass 2: extraction
                                  |
                         StateCandidate[]
                         ContinuityCandidate[]
                                  |
                    turn/revision + snapshot guards
                                  |
                                  v
                       existing deterministic validators
                                  |
                                  v
                         State / Continuity authority
```

The same provider object is used for Pass 1 and Pass 2. The initial OpenAI-compatible extension inherits the canonical adapter's client/model/endpoint/decoding configuration and therefore does not create a second resident online model requirement.

Pass 1 outputs only `CognitionConversationOutput(response)`. Pass 2 receives `CognitionExtractionInput`, which contains the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context, and outputs only `CognitionExtractionOutput` proposals.

The explicit two-pass APIs are:

```text
run_user_turn_two_pass(...)
run_user_turn_two_pass_streaming(...)
```

They require an explicit process-local `CognitionExecutionRuntime`. COGP3 does not silently switch the existing single-pass APIs or choose a release default.

## Response-first boundary

After a valid Pass 1 completes, the Assistant Event is persisted and the caller receives a `TwoPassTurnResult` containing the response and a separately completing extraction task.

Pass 2 provider failure does not retroactively remove the Assistant Event or invalidate the response. Its bounded result becomes `failed`; it commits no State/Continuity mutation.

If Pass 2 produces Continuity proposals without an explicit `ContinuityRuntime`, the entire extraction commit fails before State mutation. Cross-channel partial mutation is not allowed for that failure.

## Ordering / concurrency boundary

`CognitionExecutionRuntime` separates long model work from short ordering/commit work.

### Conversation lock

A conversation lock serializes preparation and Pass 1 generation for turns sharing one execution runtime. This preserves deterministic ordinary Event ordering.

The lock is released before Pass 2 inference completes. A pending Turn N Pass 2 therefore does not by itself prevent Turn N+1 Pass 1 from starting.

### Authority lock

A separate short authority lock is held only for:

- reserving a newly arrived two-pass turn revision;
- binding that revision to the newly persisted User Event;
- the final Pass 2 stale-check / validation / mutation boundary.

A new turn reservation advances the execution revision before the new turn is prepared, so older pending extraction becomes stale immediately when the newer two-pass turn enters this runtime.

Pass 2 inference itself never holds the authority lock.

At commit time the lock makes these checks and any resulting mutation one process-local ordering boundary:

```text
origin revision is still latest
origin User Event is still latest bound turn
persisted State == origin State snapshot
accepted Continuity == origin Continuity snapshot (when configured)
```

Any mismatch returns `stale` with no mutation. The runtime thereby prevents a late old extraction from interleaving its save with a newer turn reservation inside the same process-local execution runtime.

This does not invent a durable State revision or redefine cross-process persistence concurrency.

## Context / Retrieval / Budget reuse

The two-pass runtime reuses the existing ordinary-turn preparation owner. It consumes the same:

- Character configuration and Identity;
- Canonical State;
- Context Compiler;
- optional MEMORY retrieval;
- optional Event Evidence retrieval;
- accepted Continuity projection;
- Cognitive Budget enforcement.

COGP3 does not duplicate relevance, projection, token-budget, or lifecycle semantics. One prepared `CognitiveInput` is the authoritative origin for both passes.

## Continuity lifecycle

`relaylm.continuity` and `relaylm.continuity_validation` remain the Continuity owners.

In `single_pass`, Continuity validation runs at the existing common output commit boundary.

In `two_pass`, the origin accepted Continuity snapshot is supplied to Pass 1 through the same Context Compiler path. Pass 2 proposals are validated only at the guarded extraction commit boundary. If the accepted Continuity snapshot has advanced meanwhile, that Pass 2 result is stale and cannot mutate it.

A successful current Pass 2 validation still applies the existing lifecycle exactly once for that extraction result, including revision advancement with an empty candidate tuple when a Continuity runtime is configured.

## Streaming

Two-pass streaming exposes only Pass 1 `utterance` deltas. The complete conversation-only structured result must validate before Assistant Event creation and Pass 2 scheduling.

Pass 2 is non-streaming in COGP3 and never creates a second visible response.

## Provider boundary

Provider-specific wire grammar remains an adapter concern. The COGP3 OpenAI-compatible extension uses two strict schemas over the same adapter resources:

```text
relaylm_conversation_output
  utterance

relaylm_structured_cognition_output
  state_candidates
  continuity_candidates
```

The candidate schemas and parser are reused from the canonical OpenAI-compatible provider; the extension does not create another State/Continuity candidate grammar.

Provider reasoning/decoding capability truth remains provider-owned. COGP3 does not choose per-pass numeric defaults.

## Deferred

`shadow_two_pass` evidence carriage is COGP4. Actual-model A/B/C execution, calibrated defaults, and release-config selection remain owned by #1386, #1388, and #1446 respectively.
