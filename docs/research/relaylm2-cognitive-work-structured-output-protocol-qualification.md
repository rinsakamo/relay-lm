# RelayLM 2.0 Cognitive Work — structured-output protocol qualification

Owner: #2302  
Parent experiment: #2187  
Forensic prerequisite: #2301

## Status boundary

#2301 classified #2300 as:

```text
WRAPPER_ONLY_PROTOCOL_DEFECT
```

The failed BANK:THINK response contained exactly one schema-valid JSON object inside a Markdown JSON code fence and no semantic prose. #2300 remains permanently `R2_REPLACEMENT_INCOMPLETE` at 3/136.

This qualification does not reinterpret or resume #2300 and does not use any R2 campaign task.

## Purpose

Before another R2 task seed is spent, qualify provider-side JSON-Schema structured output as the measuring transport under the intended Gemma 4 / LM Studio / reasoning lineage.

The protocol question is mechanical:

> Can the provider constrain answer-like and allocator-like responses to whole-response strict JSON that RelayLM's strict parsers accept, including reconsideration-shaped prompts that previously drifted into a Markdown fence?

Scientific allocator efficacy is out of scope.

## Provider capability lineage

Current LM Studio developer documentation describes OpenAI-compatible `/v1/chat/completions` structured output through a JSON-Schema `response_format`. For GGUF models, LM Studio uses llama.cpp grammar-based sampling for structured output.

Documentation is not physical qualification. A concrete model/runtime/binding must still be tested fail-closed.

## Frozen schemas

### Answer schema

```json
{
  "type": "object",
  "properties": {
    "answer": {"type": "string"}
  },
  "required": ["answer"],
  "additionalProperties": false
}
```

RelayLM additionally requires the returned string to remain non-empty after trimming.

The provider schema is deliberately string-only. This removes string-vs-integer serialization trivia at generation time while remaining compatible with the accepted replacement evaluator/parser path.

### Operation schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["ZERO", "THINK", "RETRIEVE", "OBSERVE"]
    }
  },
  "required": ["operation"],
  "additionalProperties": false
}
```

The exact schema canonical JSON, schema names, schema digests and complete `response_format` mappings are qualification identity.

## Frozen response-format wire

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "<frozen schema name>",
    "strict": true,
    "schema": {"...": "frozen schema"}
  }
}
```

No fallback to prompt-only JSON, `json_object`, tool calls, function calls or parser-side wrapper stripping is legal.

## Frozen corpus

Exactly 12 non-R2 calls:

```text
8 answer-schema calls
  2 x direct
  2 x reconsider
  2 x added-context
  2 x symbolic

4 operation-schema calls
  ZERO
  THINK
  RETRIEVE
  OBSERVE
```

The repeated answer fixtures are preregistered protocol reliability probes, not retries.

No model-facing call may contain:

```text
R2 task id
R2 generator prompt
hidden regime
expected answer
retrieval packet
observation packet
historical campaign task text
```

## Physical binding

A physical qualification requires fresh exact model/runtime/hardware/tokenizer/template/context/decoding/reasoning authority.

The intended historical lineage is:

```text
google/gemma-4-12b
context 8192
reasoning native default on
request reasoning override omitted
stream false
sampling/seed overrides omitted
```

Historical runtime/backend/hardware identities are anchors only and must be re-observed.

Before any calibration generation:

```text
native listener A = success
native listener B = success
material state equal
full binding probe A = frozen binding
full binding probe B = frozen binding
```

The runner then requires a fresh binding probe before every provider attempt.

## Durable attempt semantics

Provider attempt registration precedes provider invocation.

```text
provider failure
  -> attempt remains visible
  -> no retry
  -> qualification INCOMPLETE

protocol failure after a completion
  -> completed raw response remains visible
  -> no wrapper extraction / repair
  -> qualification INCOMPLETE

binding drift
  -> no next provider attempt
  -> qualification INCOMPLETE
```

## Qualification PASS

`STRUCTURED_OUTPUT_PROTOCOL_QUALIFIED` requires all of:

```text
planned calls = 12
attempts = 12
completions = 12
strict whole-response JSON = 12/12
frozen schema compatibility = 12/12
RelayLM strict parser compatibility = 12/12
finish_reason stop = 12/12
wrapper/prose defects = 0
binding drift = 0
retries/fallbacks/repairs = 0
```

Any started qualification failure is preserved. `qualification-result.json` exists only for a fully qualified transaction.

## Scientific boundary

Even a positive protocol qualification establishes only:

> provider-side JSON Schema is mechanically qualified as a candidate measuring transport under the exact tested physical lineage.

It does not establish A2 efficacy and does not itself authorize another R2 campaign.

A positive result must be consumed by a new versioned R2 preregistration/host identity with a fresh unseen task seed and the structured-output transport frozen before another scientific execution.

```text
scientific allocator verdict = NONE
production scheduler authority = NONE
architecture consequence = NONE
```

> Qualify the measuring instrument before spending the next proof seed.

> Constrain syntax at the transport; do not teach the parser to guess.
