# RelayLM 1.0 Core Architecture

## Thesis

> **Relay a persistent character identity and the governed present state into a replaceable cognitive substrate, then accept only validated state change back.**

Short form:

> **Identity + Now + LM**

## Core flow

```text
Identity Core
+ Event Journal
+ Canonical State
      |
      v
Context Compiler
      |
      v
CognitiveInput
      |
      v
LLM x 1
      |
      v
CognitiveOutput
  response
  state_candidates
    |           |
    |           v
    |        Validator
    |           |
    |           v
    |      Canonical State
    v
Assistant Event
    |
    v
Event Journal
    |
    +----> possible future Working Context
```

The return path is deliberately split. `response` becomes an Assistant Event for future conversational continuity, while `state_candidates` remain non-authoritative until deterministic validation accepts them. Assistant-authored dialogue therefore does not become factual State merely because the character said it.

## Invariants

1. The model is not the character.
2. Identity Core is stable, human-authored normative identity and is not ordinary mutable State.
3. Event Journal records occurrence/provenance; it is not automatically truth.
4. Canonical State is accepted current understanding, not history.
5. Conversation history is not automatically Cognitive Context.
6. An ordinary turn targets exactly one cognitive LLM generation.
7. The model proposes meaning; RelayLM validates and commits State.
8. Present emotion may be generated; claims about past continuity require accepted State or trusted Context.
9. Assistant-authored text does not self-certify external or user facts.
10. Different meaning does not imply different machinery.

## Expansion rule

A new psychological concept should first be expressible as State, Context, a class/view, or a rule. A new subsystem requires evidence that distinct machinery is necessary.

## Degradation rule

> **RelayLM may degrade memory before it degrades identity.**

If Identity Core plus the minimum valid current-request kernel cannot fit, fail explicitly rather than produce a de-characterized response.

Evidence/design freeze: #1257. Provider/streaming proof: #1258.
