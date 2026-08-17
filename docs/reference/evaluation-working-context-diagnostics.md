# Working Context Budget Diagnostics Evaluation

`working_context_budget_diagnostics` is the deterministic RelayLM-native evaluation scenario for the Working Context diagnostics introduced by PR #1342.

The scenario calls the real `compile_cognitive_input_with_diagnostics` path. It does not duplicate or replace Working Context selection logic.

It verifies four bounded properties:

- an Event-window cutoff and the resulting unmatched-assistant exclusion are reported as distinct aggregate reasons;
- character-budget pressure is reported separately from Event-window and orphan-assistant effects;
- a zero character budget is attributed to character-budget eviction when the Event window itself is nonzero;
- the diagnostic output contains no seeded Event IDs or dialogue payload.

The scenario also checks that observed diagnostics remain consistent with the existing atomic Working Context residency behavior: a complete newest `user → assistant` exchange remains selected when it fits, while a zero character budget produces empty Working Context.

Current bounded metrics are:

- `event_window_evicted_count`;
- `orphan_assistant_evicted_count`;
- `character_budget_evicted_count`;
- `zero_character_budget_evicted_count`.

This scenario does **not** choose runtime default budgets, measure token cost, evaluate retrieval-stage MEMORY/Event budgets, introduce redundancy suppression, change selector semantics, or make an actual-model quality claim.

The general native-evaluation report contract remains `docs/reference/evaluation.md`; this note owns the detailed boundary for this specific scenario.
