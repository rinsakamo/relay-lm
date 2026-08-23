# Provider Wire Contract

Provider wire grammar is adapter detail and must not redefine RelayLM semantic contracts. For ordinary single-pass cognition, the combined JSON IR grammar itself is RelayLM-owned; the OpenAI-compatible backend transports it as ordinary message content and does not need provider-native JSON-schema/grammar enforcement.

Gate B (#1258) validated V6 / Framing D against the target local OpenAI-compatible provider. The current adapter implements both buffered and safe streaming delivery forms of that same semantic wire, with exact shape enforcement performed by RelayLM.

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

The model returns exactly one JSON object with exactly these three top-level fields. Both proposal channels are explicit. A model that produced no proposal for a channel returns an explicit empty array. Missing or additional top-level fields are RelayLM protocol errors and are not normalized away.

Duplicate JSON object member names anywhere in the combined IR are protocol errors and are not normalized by last-wins decoding.

Every model-facing State candidate is total and exact: `state_class`, `key`, `op`, `value`, and `sources` are present and no additional candidate fields are accepted.

Every model-facing Continuity candidate is also total and exact: `kind`, `key`, `op`, `value`, `sources`, and `epistemic_role` are present and no additional candidate fields are accepted.

The semantic StateCandidate and ContinuityCandidate contracts still treat `value` as an operation-specific semantic field. The combined IR carries a total `value` field so RelayLM can parse one closed deterministic grammar before constructing typed semantic candidates.

Provider-native `response_format`, JSON Schema, grammar, or constrained-decoding features may exist, but they are not required to define or enforce this RelayLM contract.

## State wire value forms

For State `set`, model-facing `value` may be either:

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

For State `remove`, model-facing `value` is always `null`.

The RelayLM combined-IR grammar therefore accepts:

```text
string | {semantic, degree_hint} | null
```

but operation semantics constrain the combinations:

```text
set     -> string or degree-hint object
remove  -> null
```

RelayLM fails closed on invalid combinations.

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

For Continuity `set`, `value` is the proposed JSON semantic value. Nested arrays/objects and JSON scalars are preserved without adapter reinterpretation. Non-finite numbers or otherwise non-JSON values fail closed during RelayLM parsing/normalization.

For Continuity `resolve`, wire `value` is `null` and is normalized to the semantic resolve form where the value field is absent.

Candidate `sources` remain Event IDs. The provider adapter does not promote Memory document locations into provenance and does not decide whether a proposal is accepted.

RelayLM closes the Continuity candidate object itself: unknown candidate fields, unsupported kinds/operations/epistemic roles, missing required fields, and malformed source arrays fail closed. The semantic `value` remains the JSON payload owned by Continuity rather than being narrowed into a provider-specific value vocabulary.

## Degree-hint semantics

The provider instruction defines State `degree_hint` as a soft relative semantic/intensity cue only.

It is not confidence, probability, evidence strength, authority, retrieval relevance, salience, or a removal threshold. The model is instructed not to add false precision and not to re-estimate an adequate existing hint unless the current Input materially changes the comparison or intensity.

Provider wire support for the degree-hint object does not change source authority, Validator ownership, or the frozen top-level StateCandidate shape.

## Adapter normalization

```text
provider message JSON `utterance`
    -> semantic `response`

provider message State set with string value
    -> semantic State set with string value

provider message State set with {semantic, degree_hint}
    -> semantic State set with the same bounded JSON object

provider message State remove with value:null
    -> semantic State remove with value absent

provider message Continuity set with JSON value
    -> semantic Continuity set with the same JSON value

provider message Continuity resolve with value:null
    -> semantic Continuity resolve with value absent
```

Before this normalization, RelayLM verifies the exact combined-IR top-level and candidate shapes. No semantic acceptance, lifecycle interpretation, or calibration is performed by the adapter. State validation and Continuity validation remain downstream deterministic RelayLM authority.

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

The model-facing instruction defines `utterance` as the complete non-empty natural-language reply shown to the user. This is a RelayLM wire/model reliability constraint established by the V6 Gate B evidence, not a new semantic field.

At the current OpenAI-compatible transport boundary, each buffered response envelope and each non-`[DONE]` streaming data envelope must contain exactly one provider choice. Empty or multiple `choices` are protocol errors; RelayLM does not rank or select among upstream completions.

Successful buffered provider response bodies are decoded from their raw bytes as strict UTF-8 before JSON parsing. Invalid UTF-8 is a provider protocol error; RelayLM does not replacement-decode, transcode, or repair malformed response bytes into different semantic content. Streaming SSE `data:` payload bytes are likewise decoded as strict UTF-8 before envelope parsing.

Before RelayLM interprets any buffered response envelope or non-`[DONE]` streaming data envelope, it decodes that upstream JSON with recursive duplicate-object-member rejection. Duplicate `choices`, `message`, `delta`, `content`, `finish_reason`, or any other object member is a provider protocol error and is never normalized by last-wins decoding. This provider-envelope rule is separate from the duplicate-member rejection applied later to RelayLM-owned combined/proposal IR content.

The same parse boundary admits only standard JSON numeric syntax. Python-specific `NaN`, `Infinity`, and `-Infinity` constants are provider protocol errors anywhere in an upstream envelope, including fields RelayLM would otherwise ignore; malformed non-standard JSON is never allowed to become semantic success.

If that single choice carries a non-null `finish_reason`, only the string `stop` is accepted as successful ordinary cognition completion. Explicit `length`, `content_filter`, `tool_calls`, `function_call`, unknown values, or invalid non-string values are protocol errors even when the accumulated message content is otherwise non-empty or syntactically valid. An omitted or null `finish_reason` remains tolerated on otherwise-supported transports; this rule does not add a new presence requirement.

For streaming, an explicit `finish_reason: "stop"` is terminal for provider data envelopes. After it, RelayLM permits only the optional `[DONE]` transport sentinel or stream EOF. Any later non-`[DONE]` data envelope is a protocol error and is rejected before its content can be parsed, emitted, or appended to the successful cognitive result.

For buffered generation, RelayLM waits for the complete ordinary provider message, parses its content as the exact combined IR, constructs typed `CognitiveOutput`, and only then allows the existing deterministic commit path to proceed.

For streaming generation, the provider still generates the same single JSON object as ordinary content. The adapter accumulates the complete text while incrementally decoding only characters that can be proven to belong to the leading top-level `utterance` JSON string. Those safe characters may be delivered to the client before the candidate tail completes.

`state_candidates` and `continuity_candidates` are never parsed or made commit-eligible incrementally. Only after the provider stream reaches completion does RelayLM parse the complete JSON object, enforce exact shape, normalize it through the same wire rules, and return the semantic `CognitiveOutput(response, state_candidates, continuity_candidates)`. If the stream is truncated or malformed, no semantic `CognitiveOutput` is accepted and no candidate becomes eligible for deterministic State or Continuity processing.

If the adapter cannot safely identify an incremental `utterance` prefix, it may buffer visible text until the complete object is validated; safety takes precedence over early display. Streaming does not introduce a second semantic generation or change the semantic output contract.

Provider/model-specific prompt wording and external transport details may change without reopening semantic architecture unless evidence reveals a semantic defect. The exact RelayLM IR grammar and fail-closed parse/type-construction boundary remain RelayLM-owned.