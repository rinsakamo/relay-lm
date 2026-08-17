# Calibration evidence contract

Status: CAL1 experiment/evidence contract for RelayLM v1.

Owning Issue: #1388.

Related semantic owners: #1387 Cognitive Budget, #1386 Actual-model Evaluation, #1247 deterministic evaluation, #1267 Context Compiler / layer-local controls.

This contract fixes **what a calibration experiment must vary and record before any canonical runtime default may be selected**. It does not choose a budget value, profile boundary, model preference, or degradation amount.

## Ownership boundary

Calibration owns the experiment matrix, numeric candidates under test, breakpoint analysis, candidate profiles, default provenance, and later recalibration decisions.

Calibration does not redefine:

- Cognitive Budget protection tiers, legal degradation order, or fail-before-generation semantics;
- Context Compiler selection or State-vs-MEMORY authority;
- Retrieval discovery/ranking semantics;
- Continuity lifecycle or pressure-selection semantics;
- State validation semantics;
- Actual-model quality methodology;
- provider prompt/schema semantics;
- the native deterministic registry or repository-wide scenario count.

If one of those owners does not expose a control or evidence channel required by a calibration question, the result is `PARTIAL` or `BLOCKED`; Calibration must not invent a substitute semantic rule.

## CAL1 version

The experiment contract version is `calibration-contract-v1`.

A future incompatible record shape must receive a new version. Historical evidence must continue to identify the contract version under which it was produced.

## Experiment identity

Every calibration result must be attributable to one exact runtime/evidence freeze point. The record must carry or immutably reference all of the following:

- exact 40-character RelayLM commit;
- exact model artifact identity, not only a mutable model alias;
- tokenizer identity;
- provider identity;
- adapter identity;
- declared provider capability set;
- effective model context window;
- decoding configuration and seed where supported;
- structured-output schema version;
- scenario-set version and scenario-set revision;
- Character fixture identity and revision;
- execution path (`buffered` or `streaming`);
- restart boundary when the scenario includes one;
- replicate identity;
- calibration condition ID;
- calibration contract version.

Where #1386 already owns one of these identity fields, Calibration should reference the immutable #1386 manifest/execution artifact rather than create a competing definition.

## Current legal control set

CAL1 may describe only controls already exposed by current semantic owners.

### Total context control

Record:

- `model_context_window`;
- `reserved_output_tokens`.

These are explicit #1387 inputs. Neither field receives a canonical value in CAL1.

### Canonical State envelope

Record:

- `max_items`;
- `floor_items`.

The budget owner supplies room; Context Compiler remains responsible for deterministic within-layer selection.

### Working Context envelope

Record:

- `max_items`;
- `floor_items`;
- `max_chars`;
- `floor_chars`.

Admission remains atomic according to the current Context Compiler owner contract.

### Retrieved MEMORY envelope

Record:

- `max_items`;
- `floor_items`;
- `max_chars`;
- `floor_chars`.

Retrieval ranking and State-vs-MEMORY authority remain outside Calibration.

### Event Evidence envelope

Record:

- `max_items`;
- `floor_items`;
- `max_chars`;
- `floor_chars`.

Event retrieval semantics and provenance remain outside Calibration.

### Accepted Continuity

Accepted Continuity has no Calibration envelope in `calibration-contract-v1`.

Current #1387 authority intentionally excludes Continuity from `BudgetPlan` until the Continuity/Context semantic owner exposes deterministic pressure selection. Calibration must therefore:

- keep accepted Continuity intact during current legal pressure experiments;
- reduce only current legal degradation targets;
- accept bounded pre-generation failure when no legal fit remains;
- never infer a Continuity subset policy from item order, recency, text similarity, or an arbitrary cap.

A later owner-defined Continuity pressure control requires a new fresh-authority audit before it may enter a calibration matrix.

## Degradation policy record

Every condition that uses total cognitive-budget enforcement must record the complete caller-supplied deterministic policy, not just the final envelope.

For each degradation step record:

- zero-based step index;
- target layer;
- protection tier inherited from #1387;
- target `max_items` and `max_chars` fields applicable to that layer;
- unchanged floor fields applicable to that layer.

The initial plan and the entire ordered step sequence are evidence inputs. CAL1 does not prescribe step magnitudes.

## Runtime token and pressure observations

For every executed turn, preserve the content-free budget observations needed to reconstruct the actual pressure path:

- final serialized input token count;
- final cognitive-input token count;
- required input-framing token count;
- token-count mode (`exact` or approved `conservative_estimate`);
- effective serialized-input capacity after output reservation;
- whether pressure occurred;
- number of applied degradation steps;
- exact applied degradation-step prefix from the recorded policy;
- number of reduced layers;
- number of reduced tiers;
- per-tier reduction counts;
- final outcome (`fit`, `degraded_fit`, or bounded pre-generation failure);
- bounded failure reason when present;
- provider overflow/failure result when a provider call was actually attempted.

A protected-floor failure is a valid deterministic calibration observation even though no semantic provider generation occurs. It must not be converted into a model-quality failure.

## Actual-model evidence linkage

A successful semantic generation used for calibration must cite immutable #1386 evidence identities sufficient to locate the raw model output and its deterministic boundary:

- actual-model run ID;
- scenario execution ID;
- pressure-comparison ID when the result participates in baseline-vs-pressure comparison;
- review ID or review IDs for cited human/product-quality observations;
- deterministic-boundary verdict artifact ID where available;
- cohort ID when the conclusion depends on a controlled multi-model cohort.

Calibration must not rewrite raw #1386 evidence into a new truth source.

## Capability-scoped quality coverage

Every calibration conclusion must declare which quality dimensions are actually covered by the provider capability set and scenario requirements.

At minimum distinguish:

- response correctness/coherence;
- persona / self-identity continuity;
- StateCandidate quality;
- unsupported recalled-detail behavior;
- Continuity proposal/retention quality when `continuity_candidates` is genuinely supported;
- deterministic budget/authority invariants.

An unsupported semantic output channel is `not covered`, never a false negative.

For example, a provider that exposes response text and `state_candidates` but not `continuity_candidates` may support response/persona, StateCandidate, and token-pressure conclusions. It cannot support a full Continuity-aware product-quality breakpoint.

## Controlled comparison rule

When the question is a budget effect, keep the semantic fixture and non-budget runtime conditions fixed as far as the current owner contracts allow.

A baseline/pressure pair must use the same:

- RelayLM freeze commit;
- model artifact and tokenizer;
- provider/adapter capability contract;
- decoding configuration and seed policy;
- scenario definition/revision;
- Character fixture revision;
- structured-output schema;
- execution path;
- restart placement;
- Continuity Runtime identity, unless Continuity Runtime itself is the explicitly isolated variable in a separately owned experiment.

Only the declared budget condition and condition identity may differ for a budget-effect comparison.

If unrelated semantic/runtime drift occurs, the pair is not valid breakpoint evidence.

## Required pressure families

CAL2 must eventually obtain evidence for the following families when the current semantic owner controls make them representable:

1. `baseline_fit` — the normal fixture fits without global degradation;
2. `retrieval_pressure` — optional MEMORY/Event Evidence pressures the total envelope;
3. `working_context_pressure` — recent dialogue competes for total capacity;
4. `current_authority_pressure` — Canonical State exceeds its unconstrained projection while its explicit floor and protected Tier 0 remain valid;
5. `near_protected_floor` — little capacity remains beyond required framing, Identity, Current Event, output reserve, and any still-legal floor;
6. `impossible_protected_floor` — required framing + Identity + Current Event + output reserve cannot fit, and RelayLM fails before generation.

Do not manufacture a pressure family by violating an owner contract. A family may be explicitly `not representable` under the current freeze point.

## Candidate sweep matrix

CAL1 defines the matrix shape, not its numbers.

A matrix row identifies:

- one exact capability/capacity class;
- one exact semantic fixture/scenario revision;
- one explicit initial `BudgetPlan`;
- one explicit deterministic degradation policy;
- one output-reserve value under test;
- one replicate identity;
- one pressure family;
- one expected deterministic invariant set.

Candidate values may be round numbers, but selection into the matrix and later selection as a default must be justified by evidence rather than numerology or vendor folklore.

## Breakpoint observations

CAL3 will compare candidate conditions using boundary-labeled observations rather than a weighted universal score.

A breakpoint analysis should preserve at least:

- response correctness/coherence delta;
- persona/identity continuity delta;
- StateCandidate precision/correction/comparative/degree observations when supported by the scenario set;
- unsupported recalled-detail observations;
- available Continuity quality dimensions;
- deterministic authority invariant result;
- overflow/bounded-failure behavior;
- observed degradation order;
- repeated-run stability.

The target is the smallest sufficient budget region that does not materially reduce supported product-quality dimensions relative to a meaningfully larger explicit condition while preserving deterministic safety.

## Deterministic evidence requirement

A candidate later proposed for canonicalization must cite deterministic evidence that the explicit policy under test preserves:

- #1387 Tier 0 protection;
- lower-protection reduction before higher-protection reduction;
- expected within-layer owner controls;
- final serialized fit enforcement;
- fail-before-generation on impossible floor/exhausted legal degradation;
- no silent mutation or loss of semantic authority;
- one semantic provider generation on successful ordinary turns.

The native #1247 registry remains owned by deterministic evaluation / Serial Integration. Calibration records references to that evidence; it does not register scenarios itself.

## Current CAL2 dependency gate

At the CAL1 authoring freeze point, current #1386 can represent reproducible actual-model identity and controlled baseline/pressure evidence, but its `ExplicitBudgetConfiguration` and ordinary actual-model scenario runner do not yet carry the full #1387 `CognitiveBudgetRuntimeConfig` path.

Therefore CAL2 total-budget sweeps are blocked until the #1386 owner can execute and persist evidence for conditions containing at least:

- total context capacity and output reserve;
- full initial layer plan/floors;
- ordered degradation policy;
- final serialized token diagnostics;
- bounded protected-floor/degradation-exhaustion outcomes;
- successful semantic output through the same real ordinary-turn budgeted path.

This dependency must be solved in the #1386 evidence implementation or another explicitly delegated owner surface. Calibration must not fork a second actual-model runner merely to unblock itself.

## Freeze-point rule before CAL2

Immediately before any canonical actual-model sweep:

1. reacquire exact `v1` authority;
2. enumerate open writers affecting Context Compiler, Retrieval, Cognitive Budget, provider serialization, tokenizer/counting, or actual-model evidence carriage;
3. verify the scenario-set and Character fixture revisions;
4. verify provider capability coverage;
5. reject or explicitly supersede stale runs whose within-layer selection/serialization baseline materially differs from the candidate default target.

Runs made before a semantic or serialization change remain historical evidence; they do not automatically remain valid default evidence.

## Canonical-default prohibition

`calibration-contract-v1` contains no canonical numeric runtime default and no profile boundary.

A value may become canonical only in CAL6 after supported actual-model evidence, deterministic regression validation, breakpoint analysis, applicability rules, limitations, and historical provenance are all present.

Refs #1388 #1387 #1386 #1247 #1267
