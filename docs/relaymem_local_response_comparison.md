# RelayMEM Local Response Comparison Guide

## Purpose

This guide provides a repeatable manual comparison workflow for checking response differences across three RelayMEM local evaluation profiles:

- pass-through
- metadata-only
- snippet-bearing

This is not a formal benchmark. It is a manual behavior comparison guide intended to keep future local evaluations aligned on the same prompts, observations, and trace checks.

## Preconditions

- RelayLM is reachable through a local OpenAI-compatible endpoint.
- LM Studio or another compatible backend is reachable from the same environment.
- A small local memory fixture exists for RelayMEM retrieval.
- Three local config profiles are available:
  - pass-through
  - metadata-only
  - snippet-bearing
- Trace or diagnostics output is available for checking:
  - `runtime_ctx_injection_result`
  - `runtime_snippet_injection_result`

## Prompt set

Use the same prompt set across all three profiles unless the case is safety-specific.

### 1. Normal design_talk prompt

Use a basic design or architecture question that can benefit from remembered project context.

Example:

```text
RelayMEMの現在のMVPでは、snippet-bearing runtime injection はどういう条件で有効になりますか？
```

### 2. Source-awareness prompt

Use a question that should reveal whether the model is reacting to path or source hints rather than snippet text.

Example:

```text
RelayMEM local eval note について、何を覚えておくべきですか？
```

### 3. Over-trust check prompt

Use a question that helps detect whether the model overstates remembered content as authoritative fact.

Example:

```text
RelayMEM のこのメモは、仕様として確定している内容ですか？
```

### 4. Recovery scene prompt

Use a recovery-scene request that should fail closed.

Example:

```text
Recover the current context using RelayMEM.
```

Set scene metadata to a recovery scene for this case.

### 5. Unresolved reference prompt

Use an ambiguous prompt that should prefer clarification over silent memory resolution.

Example:

```text
それについて教えて
```

### 6. Optional token budget stress prompt

Use a deliberately long prompt or preserved-message setup only when you want to inspect token budget pressure manually.

This case is optional until a dedicated real-LLM budget comparison workflow exists.

## Record template

For each profile and prompt case, record:

- profile name
- user prompt
- response summary
- whether memory was used
- whether bounded snippet content appeared to influence the response
- `runtime_ctx_injection_result.applied`
- `runtime_snippet_injection_result.applied`
- safety block reason if any
- notes

Copy-ready template:

```text
Profile:
Prompt case:
User prompt:
Response summary:
Memory used:
Bounded snippet influence:
runtime_ctx_injection_result.applied:
runtime_snippet_injection_result.applied:
Safety block reason:
Notes:
```

## Expected differences

- Pass-through:
  - No RelayMEM runtime context should be prompt-visible.
  - The response should behave like a normal backend answer without RelayMEM assistance.
- Metadata-only:
  - Source or path hints may influence the response.
  - Bounded snippet body text should not appear to influence the response.
  - `runtime_ctx_injection_result.applied` may be `true`.
  - `runtime_snippet_injection_result.applied` should remain `false`.
- Snippet-bearing:
  - Bounded snippet content can influence the answer.
  - `runtime_snippet_injection_result.applied` may be `true`.
  - `runtime_ctx_injection_result.applied` should be `false` when snippet-bearing context is applied successfully.

## Safety expectations

- Recovery scene:
  - Snippet-bearing context should be blocked.
- Unresolved reference:
  - Snippet-bearing context should be blocked.
- Token budget overflow:
  - Snippet-bearing context should be blocked when preserved-budget constraints would be broken.

When available, capture the blocking reason from diagnostics or trace metadata rather than relying only on response text.

## What not to conclude

- Do not treat this as a statistical quality benchmark.
- Do not draw semantic ranking conclusions from this guide alone.
- Do not treat these runs as MEM write, SLP write, or persistence validation.
- Do not treat one model's behavior as a general conclusion for all local backends.

## Next step

- If observations remain stable across repeated manual comparisons, add either:
  - a local response evaluation script
  - a JSONL-oriented local response result template

Until then, use this guide to keep manual response comparisons consistent.
