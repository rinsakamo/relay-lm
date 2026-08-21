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

Actual-model evidence later demonstrated that visible conversational quality and structured proposal quality can diverge materially while RelayLM's deterministic authority boundary remains correct. #1533 therefore made ordinary-turn cognition topology an explicit execution policy rather than an immutable one-generation architecture rule.

The supersession established `docs/contracts/cognition-execution-policy.md` under the `cognitive_turn` owner as the execution-policy contract. At that point RelayLM recognized `single_pass`, `two_pass`, `shadow_two_pass`, and `auto` as the closed execution-policy vocabulary.

At the time of supersession, `single_pass` remained the implemented behavior and a supported measured baseline. What was superseded was the claim that one generation was the sole valid ordinary-turn topology.

The supersession did not change State/Continuity authority. Any multi-pass execution still produced proposals that had to pass the existing deterministic RelayLM validation/lifecycle before becoming authority.
