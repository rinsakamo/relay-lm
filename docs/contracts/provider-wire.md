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
  ],
  "continuity_candidates": [
    {
      "kind": "unresolved",
      "key": "coffee.followup",
      "op": "set",
      "value": {"question": "Which coffee?"},
      "sources": ["event-id"],
      "epistemic_role": "assistant_inference"
    }
  ]
}
```

Both proposal channels are explicit top-level fields. A supported provider that produced no proposal for a channel returns an explicit empty array. A missing `continuity_candidates` field is a provider protocol error and is not normalized into an empty semantic result.

Every provider-facing State candidate is total: `state_class`, `key`, `op`, `value`, and `sources` are present.

Every provider-facing Continuity candidate is also total: `kind`, `key`, `op`, `value`, `sources`, and `epistemic_role` are present.

The semantic StateCandidate and ContinuityCandidate contracts still treat `value` as an operation-specific semantic field. The provider wire carries a total `value` field so strict structured-output schemas remain reliable.

## State wire value forms

For State `set`, provider `value` may be either:

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

For State `remove`, provider `value` is always `null`.

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

## ContinuityCandidate wire

Continuity proposal meaning is owned by #1371 and `relaylm.continuity`. The OpenAI-compatible adapter only carries the existing semantic fields.

The current wire supports exactly these canonical kinds:

```text
referent
unresolved
active_task
```

and these operations:

```text
set
resolve
```

Each candidate also carries exactly one canonical epistemic role:

```text
user_assertion
assistant_inference
assistant_commitment
```

For Continuity `set`, `value` is the proposed JSON semantic value. Nested arrays/objects and JSON scalars are preserved without adapter reinterpretation. Non-finite numbers or otherwise non-JSON values fail closed during provider-side normalization.

For Continuity `resolve`, wire `value` is `null` and is normalized to the semantic resolve form where the value field is absent.

Candidate `sources` remain Event IDs. The provider adapter does not promote Memory document locations into provenance and does not decide whether a proposal is accepted.

The strict structured-output schema closes the Continuity candidate object itself: unknown candidate fields, unsupported kinds/operations/epistemic roles, missing required fields, and malformed source arrays fail closed. The semantic `value` remains the JSON payload owned by Continuity rather than being narrowed into a provider-specific value vocabulary.

## Degree-hint semantics

The provider instruction defines State `degree_hint` as a soft relative semantic/intensity cue only.

It is not confidence, probability, evidence strength, authority, retrieval relevance, salience, or a removal threshold. The model is instructed not to add false precision and not to re-estimate an adequate existing hint unless the current Input materially changes the comparison or intensity.

Provider wire support for the degree-hint object does not change source authority, Validator ownership, or the frozen top-level StateCandidate shape.

## Adapter normalization

```text
provider `utterance`
    -> semantic `response`

provider State set with string value
    -> semantic State set with string value

provider State set with {semantic, degree_hint}
    -> semantic State set with the same bounded JSON object

provider State remove with value:null
    -> semantic State remove with value absent

provider Continuity set with JSON value
    -> semantic Continuity set with the same JSON value

provider Continuity resolve with value:null
    -> semantic Continuity resolve with value absent
```

No semantic acceptance, lifecycle interpretation, or calibration is performed by the adapter. State validation and Continuity validation remain downstream deterministic RelayLM authority.

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

## CognitiveInput crystallized memory

Provider-facing `CognitiveInput.memory` is a separate optional layer for already-selected crystallized synthesis:

```json
{
  "content": "## Coffee\n\nRin currently prefers coffee over tea.",
  "location": "memory/MEMORY.md#memory/coffee"
}
```

The metadata is intentionally not Event provenance:

```text
Context.sources[]     Event provenance
Memory.location       current Markdown document locator
```

A memory `location` is not an Event ID and must never be copied into proposal `sources`.

Crystallized memory is readable synthesis rather than accepted current State. The provider instruction therefore treats active State as current understanding if already-projected memory conflicts with it, and explicitly states that memory prose cannot establish new user truth by itself.

RelayLM also applies the current deterministic explicit-key State-shadow filter before memory projection. Provider wording is defense in depth, not the only authority mechanism. The adapter does not reinterpret a Markdown location as provenance or perform hidden retrieval.

## CognitiveInput Event evidence

Provider-facing `CognitiveInput.event_evidence` is a distinct optional layer for already-selected persisted Event occurrences:

```json
{
  "event_id": "019b...",
  "type": "message",
  "actor": "user",
  "timestamp": "2026-08-17T00:00:00+00:00",
  "content": "以前は北海道に住んでいた"
}
```

Event evidence remains separate from Working Context, crystallized Memory, active State, and Current Input. It preserves the real persisted Event ID plus occurrence type, actor, timestamp, and content.

Authority remains source-role-aware:

- user-authored Event evidence supports what the user said at that recorded occurrence, subject to temporal and semantic scope;
- assistant-authored Event evidence remains assistant-authored and cannot establish user facts or external truth merely because it was retrieved;
- a retrieved occurrence is not automatically accepted current State.

Real Event-evidence IDs are eligible proposal provenance. The provider wire instruction therefore restricts candidate `sources` to Event IDs present through State, Context, Event Evidence, or the current Input. Memory `location` values remain explicitly ineligible.

The adapter only serializes already-projected Event evidence. It does not widen retrieval scope, read the Event Journal, or choose an Event retrieval budget.

## Response framing

The provider-facing instruction defines `utterance` as the complete non-empty natural-language reply shown to the user. This is a wire/model reliability constraint established by the V6 Gate B evidence, not a new semantic field.

For buffered generation, RelayLM waits for the complete provider response and then normalizes the structured object into `CognitiveOutput`.

For streaming generation, the provider still generates the same single structured object. The adapter accumulates the complete structured text while incrementally decoding only characters that can be proven to belong to the leading top-level `utterance` JSON string. Those safe characters may be delivered to the client before the candidate tail completes.

`state_candidates` and `continuity_candidates` are never parsed or made commit-eligible incrementally. Only after the provider stream reaches completion does RelayLM parse the complete JSON object, normalize it through the same wire rules, and return the semantic `CognitiveOutput(response, state_candidates, continuity_candidates)`. If the stream is truncated or malformed, no semantic `CognitiveOutput` is accepted and no candidate becomes eligible for deterministic State or Continuity processing.

If the adapter cannot safely identify an incremental `utterance` prefix, it may buffer visible text until the complete object is validated; safety takes precedence over early display. Streaming does not introduce a second semantic generation or change the semantic output contract.

Provider/model-specific prompt wording and schema constraints may change without reopening semantic architecture unless evidence reveals a semantic defect.
