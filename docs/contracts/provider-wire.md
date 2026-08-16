# Provider Wire Contract

Provider wire grammar is adapter detail and must not redefine RelayLM semantic contracts.

Gate B (#1258) validated an OpenAI-compatible local-provider framing where the provider wire uses:

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

The adapter normalizes:

```text
provider `utterance` -> semantic `response`
provider set value   -> semantic set value
provider remove with value:null -> semantic remove with value absent
```

The visible response may stream before the full internal structured object completes. State commit remains fail-closed until the complete candidate structure is valid and authority-valid.

Provider/model-specific prompt wording and schema tricks may change without reopening semantic architecture unless evidence reveals a semantic defect.
