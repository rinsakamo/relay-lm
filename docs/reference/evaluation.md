# RelayLM Native Evaluation

RelayLM native evaluation is the deterministic repository-owned boundary suite exposed by `relaylm-eval`.

It answers a narrow question:

> Do the deterministic RelayLM contracts exercised by the registered scenarios still hold on this exact build?

It is not an actual-model quality benchmark, a leaderboard, or a weighted product score.

## Report contract

`relaylm-eval` emits JSON using:

- `format_version: 1`;
- `suite: relaylm-native`;
- one ordered list of deterministic scenarios;
- boundary-labeled checks with explicit expected/observed values;
- optional bounded metrics;
- aggregate `pass` only when every scenario passes.

There is deliberately no weighted score, severity arithmetic, or attempt to collapse independent boundary failures into one quality number.

A scenario result is evidence about the exact deterministic behavior it executes. It does not establish actual-model conversational quality.

## Registry architecture

Current aggregate registration is declarative in `src/relaylm/evaluation.py` through `NATIVE_EVALUATION_SCENARIOS`.

Each registry entry contains:

- a stable `scenario_id`;
- a current semantic group;
- the module/function that owns the scenario implementation.

The registry is the aggregate execution surface. Scenario implementations remain with the boundary they exercise.

Do not add another aggregate wrapper, registration test, or prose section merely because a scenario is added. A new scenario should normally require:

1. one owner-local scenario implementation;
2. its meaningful dedicated regression coverage;
3. one declarative registry entry;
4. an authority update only when the owner surfaces change.

Historical PR/slice order is evidence in Git history and Issues, not current registry semantics.

## Current semantic groups

The current 43-scenario suite is grouped for navigation only. Group labels are not new runtime authorities.

### Runtime safety

- `provider_failure_safety`
- `restart_continuity`
- `streaming_safety`

### State / authority

- `assistant_self_certification_prevention`
- `comparative_preference_preservation`
- `degree_hint_integrity`
- `correction_remove_semantics`

### Context / retrieval

- `working_context_budget_atomicity`
- `state_selection_diagnostics`
- `cross_layer_context_diagnostics`
- `working_context_budget_diagnostics`
- `memory_heading_retrieval`
- `memory_cognitive_projection`
- `ordinary_turn_memory_retrieval`
- `state_memory_authority_filter`
- `targeted_event_retrieval`
- `event_evidence_cognitive_projection`
- `ordinary_turn_event_retrieval`
- `retrieval_stage_diagnostics`
- `boolean_state_memory_authority`
- `retrieval_aggregate_diagnostics`
- `cjk_retrieval_relevance`
- `degree_state_memory_authority`
- `retrieval_query_features`
- `freeform_current_state_shadow`

### Continuity

- `continuity_lifecycle`
- `continuity_turn`
- `continuity_context_retention`
- `continuity_active_task_retention`
- `continuity_cognition_wiring`

### Persistence / durable memory

- `persistence_integrity`
- `event_snapshot_reuse`
- `crystallization_integrity`
- `memory_temporal_provenance`

### Budget / provider serialization

- `total_budget_accounting`
- `budget_degradation_plan`
- `budget_owner_controls`
- `serialized_input_fit`
- `openai_serialized_counter`
- `serialized_fit_enforcement`
- `protected_serialized_floor`
- `cognitive_budget_turn_wiring`
- `cognitive_budget_turn_diagnostics`

The registry order is stable report identity. The groups make the current responsibilities readable without encoding the order in which the scenarios were historically implemented.

## Boundary attribution

Every check names the boundary it observes. Typical labels include provider, Event/provenance, Canonical State, Validator, Context Compiler, persistence, Continuity, diagnostics, and serialized budget enforcement.

Boundary labels are diagnostic metadata. They do not become competing semantic owners.

The key distinction remains:

```text
response behavior
  != State correctness
  != authority correctness
  != continuity correctness
  != persistence correctness
```

## Native evaluation versus actual-model evaluation

Deterministic native evaluation and actual-model product evaluation are separate systems.

`relaylm-eval` verifies deterministic mechanics suitable for repository gating. Actual-model evidence under #1386 evaluates model-dependent conversation, semantic proposal quality, Character realization, timing, capacity, and related empirical behavior.

Do not add probabilistic model-quality checks to the native registry merely to obtain one unified score or command.

## Change rule

When a deterministic scenario is added, removed, or intentionally replaced:

- start from a concrete owner-local contract;
- keep one stable aggregate registry entry per current scenario;
- avoid duplicate root tests that only restate registration;
- keep detailed behavior assertions with the scenario or its owning subsystem;
- update this grouped inventory and `.ai/authority/evaluation.yaml` when current surfaces change;
- preserve report-format compatibility unless an explicit format-version transaction changes it.

When semantics are merely refactored, characterize and preserve the existing scenario IDs/order/results rather than manufacturing a new semantic RED.

## Principle

> Evaluate current boundaries by current responsibility, not by the sequence of PRs that created them.
