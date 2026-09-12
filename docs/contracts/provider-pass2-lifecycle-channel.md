# Pass 2 Accepted Continuity Lifecycle Channel

This contract owns the OpenAI-compatible two-pass provider representation of already-accepted Continuity during Pass 2 extraction.

It does not change Continuity lifecycle authority, the Context Compiler, candidate wire shape, parser/Validator/materializer/oracle behavior, or Pass 1 conversation semantics.

## Motivation and evidence boundary

The #2043 / #2616 investigation established the following causal chain under current Stage R:

```text
formed unresolved meaning exists
  -> isolated Continuity projection can emit it
  -> full production suppresses it
  -> removing State projection responsibility is insufficient
  -> unresolved-only responsibility is insufficient
  -> removing Pass 1 response conditioning is insufficient
  -> removing accepted Continuity from generic model-facing Pass 2 context restores it
```

The supported mechanism class is therefore representation/conditioning from accepted lifecycle state residing in the generic semantic-discovery Context channel. This evidence does not imply that accepted Continuity is invalid or may be deleted globally.

## Canonical compilation remains authoritative

Turn and Context Compiler behavior is unchanged.

Before either model pass, RelayLM still compiles the ordinary `CognitiveInput` with accepted Continuity present. Accepted Continuity may therefore participate in the existing State working-set selection exactly as before.

Pass 1 receives the ordinary canonical `CognitiveInput` unchanged.

The Pass 2 view is derived only after that canonical compilation. RelayLM never recompiles the turn with `continuity_context=None` to obtain the extraction view.

## Pass 2 extraction view

Current canonical compilation has the structural form:

```text
CognitiveInput.context
  = projected accepted Continuity ContextItems
  + ordinary user/assistant Working Context
```

For ordinary production Pass 2, the provider derives:

```text
semantic-discovery CognitiveInput
  context = ordinary user/assistant Working Context

accepted lifecycle channel
  referent    = exact accepted referent items
  unresolved  = exact accepted unresolved items
  active_task = exact accepted active_task items
```

Every non-context `CognitiveInput` coordinate is identical to the canonical compiled object, including the already-selected State.

The split is structural and fail-closed. A leading actor-less Context item must be canonical accepted-Continuity JSON with preserved Event sources. After the accepted prefix ends, every remaining Context item must be ordinary `actor=user|assistant` Working Context. An actor-less/noncanonical/interleaved boundary is a provider protocol error rather than permission to guess or rewrite context.

An ordinary turn with no accepted Continuity keeps its Working Context unchanged and carries empty lifecycle buckets.

## Accepted lifecycle block

The Pass 2 prompt carries one read-only block:

```text
<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>
{
  "referent": [...],
  "unresolved": [...],
  "active_task": [...]
}
</ACCEPTED_CONTINUITY_LIFECYCLE_JSON>
```

Each retained accepted item contains exactly the lifecycle information needed for reconciliation:

```text
kind
key
value
sources
 ep istemic_role
```

(`epistemic_role` is serialized without the spacing shown above.)

The block is prior accepted lifecycle state. It is not a new proposal and does not establish current-turn evidence by itself.

## Decision order

Pass 2 uses one model generation and preserves the existing State + Continuity output schema.

The model-facing contract is:

1. discover current-turn Continuity meanings from current Input plus non-lifecycle CognitiveInput;
2. only after a current-turn meaning is identified, consult the same-kind accepted lifecycle bucket;
3. use that same-kind bucket for no-op, existing-key reuse, or resolve;
4. accepted items of other kinds do not suppress discovery of a distinct current-turn meaning;
5. a new transition still cites the current Input Event ID in `sources` under the existing provenance rules.

Existing Continuity kind semantics and set/no-op/resolve semantics remain unchanged.

## Invariants

This realization must preserve all of the following:

- Pass 1 request construction and canonical `CognitiveInput` are unchanged;
- Context Compiler output and State selection are unchanged;
- ordinary Working Context content/order/actor/source provenance is unchanged;
- Identity, State classes, selected State, Input, Knowledge, Memory, and Event Evidence are unchanged;
- candidate schema, native structured-output schema, parser, source validation, materialization, and oracle are unchanged;
- no extra model call is added;
- no benchmark-specific key, answer, language rule, or deterministic semantic inference is added;
- reasoning/decoding behavior is independent of this representation split;
- serialized-input budget accounting uses the same production Pass 2 representation sent to the provider.

Closed historical diagnostic builders may retain their historical request composition so immutable factor evidence remains reproducible. Ordinary production generation and production serialized-input accounting use this contract.
