# ADR 0001: One semantic cognitive generation per ordinary turn

- Status: Superseded by #1533 / COGP1 cognition execution policy
- Date: 2026-08-17
- Superseded: 2026-08-20

## Historical context

RelayLM owns persistent identity, evidence, State, and Context outside the language model. The initial v1 ordinary-turn design therefore chose one semantic model generation so character continuity would not depend on a hidden chain of model calls.

That decision reduced latency, cost, failure surface, and ambiguity while the first cognitive-turn boundary was being established.

## Historical decision

The initial ordinary RelayLM turn performed exactly one semantic cognitive model generation that returned the visible response and StateCandidate proposals together. Later ContinuityCandidate support remained part of the same completed result.

Deterministic Context compilation, validation, persistence, retrieval, serialization, and transport processing did not count as additional cognitive generations.

Off-turn crystallization remained a separate explicitly governed workflow. Streaming remained a transport form of the same completed semantic result.

## Supersession

Actual-model evidence later demonstrated that visible conversational quality and structured proposal quality can diverge materially while RelayLM's deterministic authority boundary remains correct. #1533 therefore makes ordinary-turn cognition topology an explicit execution policy rather than an immutable one-generation architecture rule.

Current authority is `docs/contracts/cognition-execution-policy.md` under the existing `cognitive_turn` owner. RelayLM 1.0 recognizes `single_pass`, `two_pass`, `shadow_two_pass`, and `auto` as the closed execution-policy vocabulary.

The former decision is not removed from history: `single_pass` remains the current implemented behavior and a supported measured baseline. What is superseded is only the claim that one generation is the sole valid ordinary-turn topology.

State/Continuity authority is unchanged. Any multi-pass execution still produces proposals that must pass existing deterministic RelayLM validation/lifecycle before becoming authority.
