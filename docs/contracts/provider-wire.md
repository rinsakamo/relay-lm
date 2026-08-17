# Provider Wire Contract

Provider wire grammar is adapter detail and must not redefine RelayLM semantic contracts.

Gate B (#1258) validated V6 / Framing D against the target local OpenAI-compatible provider. The current adapter implements both buffered and safe streaming delivery forms of that same wire.

## Complete provider response

```json
{
  "utterance": "...",
  "state_candidates": [
    {
      "state_class": "user.preference",
      "key": "coffee",
      "op": "set",
      "value": "likes",
      "sources": ["event-id"]
    }
  ]
}
```

Every provider-facing candidate is total: `state_class`, `key`, `op`, `value`, and `sources` are present.

The semantic StateCandidate contract still treats `value` as a set-only semantic field, but the provider wire carries a total field so strict structured-output schemas remain reliable.

## Wire value forms

For `set`, provider `value` may be either:

```json
"likes"
```

or the reserved optional degree-hint object:

```json
{
  "semantic": "likes",
  "degree_hint": 0.85
}
```

The structured form is exact and closed:

- `semantic` is a non-empty string;
- `degree_hint` is a finite number in inclusive range `0.0..1.0`;
- no additional properties are allowed.

For `remove`, provider `value` is always `null`.

The strict provider schema therefore accepts:

```text
string | {semantic, degree_hint} | null
```

but operation semantics constrain the combinations:

```text
set     -> string or degree-hint object
remove  -> null
```

The adapter fails closed on invalid combinations.

## Degree-hint semantics

The provider instruction defines `degree_hint` as a soft relative semantic/intensity cue only.

It is not confidence, probability, evidence strength, authority, retrieval relevance, salience, or a removal threshold. The model is instructed not to add false precision and not to re-estimate an adequate existing hint unless the current Input materially changes the comparison or intensity.

Provider wire support for the degree-hint object does not change source authority, Validator ownership, or the frozen top-level StateCandidate shape.

## Adapter normalization

```text
provider `utterance`
    -> semantic `response`

provider set with string value
    -> semantic set with string value

provider set with {semantic, degree_hint}
    -> semantic set with the same bounded JSON object

provider remove with value:null
    -> semantic remove with value absent
```

No semantic normalization or calibration is performed by the adapter.

## CognitiveInput context provenance

Provider-facing `CognitiveInput.context` may include RelayLM-prepared Working Context items such as:

```json
{
  "content": "持ち運び重視？",
  "sources": ["assistant-event-id"],
  "actor": "assistant"
}
```

Actor/source provenance must be preserved. The provider instruction explicitly states that assistant-authored Context supports conversational continuity only and does not prove user facts, preferences, goals, experiences, or external events.

User-authored Context records what the user said but remains bounded by that utterance's temporal and semantic scope; prompt placement does not promote it to timeless external truth.

This authority distinction belongs to RelayLM semantics even though provider-specific wording may evolve.

## Response framing

The provider-facing instruction defines `utterance` as the complete non-empty natural-language reply shown to the user. This is a wire/model reliability constraint established by the V6 Gate B evidence, not a new semantic field.

For buffered generation, RelayLM waits for the complete provider response and then normalizes the structured object into `CognitiveOutput`.

For streaming generation, the provider still generates the same single structured object. The adapter accumulates the complete structured text while incrementally decoding only characters that can be proven to belong to the leading top-level `utterance` JSON string. Those safe characters may be delivered to the client before the candidate tail completes.

`state_candidates` are never parsed or made commit-eligible incrementally. Only after the provider stream reaches completion does RelayLM parse the complete JSON object, normalize it through the same wire rules, and return the semantic `CognitiveOutput(response, state_candidates)`. If the stream is truncated or malformed, no semantic `CognitiveOutput` is accepted and no candidate becomes eligible for State mutation.

If the adapter cannot safely identify an incremental `utterance` prefix, it may buffer visible text until the complete object is validated; safety takes precedence over early display. Streaming does not introduce a second semantic generation or change the semantic output contract.

Provider/model-specific prompt wording and schema constraints may change without reopening semantic architecture unless evidence reveals a semantic defect.
