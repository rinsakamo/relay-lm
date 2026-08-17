# Retrieval refinement native evaluations

This document records deterministic native evaluation coverage for bounded #1267 refinement slices whose runtime authority already exists on current `v1`.

## `boolean_state_memory_authority`

This scenario calls the real Context Compiler with active `notifications_enabled = true` Canonical State and three already-retrieved MEMORY chunks.

It verifies that:

- an explicitly State-addressing chunk containing the opposite boolean is suppressed;
- an explicitly State-addressing chunk containing the current boolean remains resident;
- general historical prose that does not explicitly address the canonical State key remains resident.

The scenario evaluates only the explicit boolean authority rule introduced by PR #1360. It does not infer free-form contradiction, historical/current intent, degree conflicts, or broader semantic equivalence.

## `retrieval_aggregate_diagnostics`

This scenario runs two real ordinary diagnostic turns through `run_user_turn_with_retrieval_diagnostics(...)`.

With both MEMORY and Event retrieval enabled it verifies that the turn-owned aggregate reports:

- two enabled retrieval layers;
- the arithmetic sum of configured retrieval character budgets;
- the arithmetic sum of selector-owned selected character usage;
- the count and any/none reduction of selector-owned character-budget pressure flags.

A second turn with no retrieval budgets verifies the zero-layer aggregate. The provider must be called exactly once per turn.

This scenario does not define runtime defaults, total prompt/token cost, Identity/State/Working Context budgeting, or degradation policy.

## `cjk_retrieval_relevance`

This scenario calls the real MEMORY and Event selector APIs against Japanese fixtures.

It verifies that:

- query `コーヒーが好き` positively retrieves persisted `最近はコーヒーが好きです` from MEMORY;
- unrelated Japanese MEMORY remains omitted;
- MEMORY diagnostic and ordinary selectors return identical selected chunks;
- the same CJK phrasing match selects the relevant Event;
- generic iterable and `EventDiscoveryIndex` paths return the same selected Event set and order;
- Event diagnostic and ordinary selectors return identical selected Events;
- Latin whole-token protection remains intact, so query `likes` does not match content containing only `dislikes`.

The scenario evaluates the deterministic shared lexical feature rule introduced by PR #1358. It does not claim embedding/vector/LLM semantic retrieval or actual-model response quality.

## `distinct_query_feature_relevance`

This scenario calls the real MEMORY and Event retrieval owners after PRs #1363 and #1366.

It verifies that:

- repeated `coffee` query evidence does not outweigh a candidate matching the distinct `fukuoka` and `trip` features in MEMORY;
- the same distinct-feature rule selects the corresponding Event through the generic iterable path;
- generic Event retrieval and `EventDiscoveryIndex` retrieval remain equivalent;
- `EventDiscoveryIndex.candidate_scores(...)` itself counts a repeated supplied query feature at most once, so the derived discovery boundary cannot reintroduce multiplicity weighting outside the normal selector path.

The scenario observes the merged distinct-query-feature contract only. It does not define new lexical features, ranking weights, budgets, temporal relevance, semantic/vector retrieval, or Event occurrence authority.

## `degree_state_memory_authority`

This scenario calls the real Context Compiler after PR #1364 with active `user.preference / tea = {semantic: likes, degree_hint: 0.85}` State and already-retrieved MEMORY chunks.

It verifies that:

- an explicitly State-addressing Tea section with the current semantic but stale explicit degree is suppressed;
- a matching explicit degree remains resident;
- a matching numeric degree cannot rescue conflicting semantic text;
- an inline canonical-key assignment associates `degree_hint` only on that same assignment line;
- another key's degree claim is not borrowed by the active key;
- unaddressed historical prose containing a degree-like field remains available rather than being reclassified as current State conflict.

The scenario evaluates only the merged reserved structured-degree authority rule. It does not infer degree from adjectives or arbitrary prose, define tolerance or ordering between degree values, compare degrees across keys or semantic axes, or perform general historical/current contradiction classification.

## Registration

PR #1361 registered the first three scenarios after the existing 22-scenario native suite, bringing the deterministic `relaylm-native` baseline to 25 scenarios.

PR #1368 registers `distinct_query_feature_relevance` and `degree_state_memory_authority` after their component authorities are merged, bringing the deterministic native baseline to 27 scenarios.

All five scenarios call current runtime owners rather than reproducing their implementation. They add no runtime authority and define no weighted or composite score.
