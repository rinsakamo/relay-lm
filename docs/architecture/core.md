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
Cognition Execution Policy (#1533)
      |
      v
replaceable LM
      |
      v
response + proposal channels
    |          |               |
    |          |               v
    |          |        Continuity Validator
    |          |               |
    |          |               v
    |          |        Continuity Context
    |          v
    |       State Validator
    |          |
    |          v
    |     Canonical State
    v
Assistant Event
    |
    v
Event Journal
    |
    +----> possible future Working Context
```

The cognition execution owner may realize these semantic channels through `single_pass`, `two_pass`, or another explicitly supported policy without changing this core authority graph. `auto` is policy resolution, not an extra authority.

The return path is deliberately split. `response` becomes an Assistant Event for future conversational continuity. State proposals remain non-authoritative until deterministic State validation accepts them. Continuity proposals remain non-authoritative until deterministic Continuity validation accepts them into bounded temporary Continuity Context. Assistant-authored dialogue therefore does not become factual State or accepted temporary continuity merely because the character said it.

## Continuity Context extension

The semantic boundary for bounded non-durable cross-turn continuity is frozen in `docs/architecture/continuity-context.md` and tracked by #1371.

K1 implements the typed `ContinuityCandidate`, `ContinuityItem`, and immutable explicitly bounded `ContinuityContext` boundary in `relaylm.continuity`. K2 implements deterministic provenance validation plus admit/duplicate/supersede/resolve/expire/evict lifecycle transitions in `relaylm.continuity_validation`. K3 exposes the Continuity proposal channel and routes the current `single_pass` buffered or streamed ordinary cognitive result through K2 using an explicitly configured process-local `ContinuityRuntime`.

The runtime holder requires caller-supplied capacity and lifetime boundaries and chooses no defaults. Under the current implemented `single_pass` path it advances the K2 lifecycle once per successfully completed ordinary cognitive result when configured, including results without candidates, so revision-based expiry remains deterministic. Streamed response deltas do not commit Continuity Context before the current single-pass provider result completes.

Future execution-policy implementations must preserve the same owner boundary: execution topology may change when Continuity proposals are produced, but only deterministic Continuity validation may accept them and lifecycle advancement must remain explicit under the selected policy.

Continuity Context is temporary semantic authority, not Canonical State, Event occurrence authority, crystallized MEMORY, or current-turn Working Context. It is not persisted by this foundation.

The Context Compiler consumes accepted continuity under its own current authority; it does not become the producer or acceptance owner for referent, unresolved, or active-task semantics. Turn/runtime orchestration does not implement that selection/retention work.

## Invariants

1. The model is not the character.
2. Identity Core is stable, human-authored normative identity and is not ordinary mutable State.
3. Event Journal records occurrence/provenance; it is not automatically truth.
4. Canonical State is accepted current understanding, not history.
5. Conversation history is not automatically Cognitive Context.
6. Ordinary-turn execution topology is owned by the cognition execution policy; changing pass topology never grants model output additional State or Continuity authority.
7. The model proposes meaning; RelayLM validates State and temporary Continuity through separate deterministic authorities.
8. Present emotion may be generated; claims about past continuity require accepted State or trusted Context.
9. Assistant-authored text does not self-certify external or user facts.
10. Different meaning does not imply different machinery.

## Expansion rule

A new psychological concept should first be expressible as State, Context, a class/view, or a rule. A new subsystem requires evidence that distinct machinery is necessary.

## Degradation rule

> **RelayLM may degrade memory before it degrades identity.**

If Identity Core plus the minimum valid current-request kernel cannot fit, fail explicitly rather than produce a de-characterized response.

Evidence/design freeze: #1257. Provider/streaming proof: #1258. Ordinary-turn cognition execution policy: #1533.
