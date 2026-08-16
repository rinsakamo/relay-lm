# Provider Wire Contract

Provider wire grammar is adapter detail and must not redefine RelayLM semantic contracts.

Gate B (#1258) validated V6 / Framing D against the target local OpenAI-compatible provider. M3 implements the complete-response form of that wire:

```json
{
  "utterance": "...",
  "state_candidates": [
    {
      "state_class": "...",
      "key": "...",
      "op": "set",
      "value": "...",
      "sources": ["..."]
    }
  ]
}
```

Every provider-facing candidate is total: `state_class`, `key`, `op`, `value`, and `sources` are present. The M3 provider schema uses a string-or-null wire value because V6 uses non-null string values for `set` and `null` for `remove`.

The adapter normalizes:

```text
provider `utterance` -> semantic `response`
provider set value   -> semantic set value
provider remove with value:null -> semantic remove with value absent
```

The provider-facing instruction explicitly defines `utterance` as the complete non-empty natural-language reply. This is a wire/model reliability constraint established by the V6 Gate B evidence, not a new semantic field.

M3 buffers the complete provider response. Safe early visible-response streaming while State remains commit-ineligible is deferred to #1269; the semantic `CognitiveOutput(response, state_candidates)` contract remains unchanged.

Provider/model-specific prompt wording and schema constraints may change without reopening semantic architecture unless evidence reveals a semantic defect.
