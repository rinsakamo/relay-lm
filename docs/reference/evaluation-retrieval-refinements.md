# Retrieval refinement native evaluations

This document records the deterministic native evaluation coverage for three bounded #1267 refinement slices merged before this serial integration transaction.

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

## Registration

PR #1361 registers these three scenarios after the existing 22-scenario native suite, bringing the deterministic `relaylm-native` baseline to 25 scenarios.

The scenarios call current runtime owners rather than reproducing their implementation. They add no runtime authority and define no weighted or composite score.
