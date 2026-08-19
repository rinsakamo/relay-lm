# Actual-model crystallization evidence

RelayLM records actual-model crystallization separately from ordinary-turn actual-model evidence.

This surface evaluates one explicit **off-turn** crystallization operation. It does not add a second generation to the ordinary cognitive turn and it does not redefine the crystallization, State, Validator, or MEMORY authority contracts.

## Execution boundary

The evaluation path is:

```text
frozen Character evidence
  Identity
  Canonical State
  persisted Events
  optional prior MEMORY.md
        |
        v
existing run_crystallization(...)
        |
        +--> recording Crystallizer wrapper
        |      captures exact bounded CrystallizationInput
        |      captures raw CrystallizationOutput
        |
        +--> existing Validator / State engine
        |
        v
actual-model crystallization evidence
  exact input
  raw model output
  deterministic RelayLM decisions
  resulting State
  resulting MEMORY.md
  optional product-quality review
```

The recording wrapper delegates to the supplied `Crystallizer` and does not reinterpret its input or output. `run_actual_model_crystallization(...)` invokes the existing `run_crystallization(...)` operation exactly once.

## Manifest identity

`ActualModelCrystallizationManifest` records the reproducibility identity required for an off-turn crystallization run:

- exact RelayLM commit;
- Character fixture ID and revision;
- provider and adapter identities;
- exact model artifact and tokenizer identity;
- effective context window;
- explicit decoding configuration and optional seed;
- structured-output schema version;
- crystallization evaluation-contract version;
- condition ID;
- `max_events`;
- explicit replicate ID.

The manifest declares `execution_kind = off_turn_crystallization`. It deliberately does not reuse ordinary-turn-only Continuity runtime or scenario-set fields.

A run ID is a SHA-256 digest over canonical JSON containing the manifest, semantic case, and the **exact pre-pass `CrystallizationInput` observed by the recording wrapper**. Therefore a model/runtime/configuration change or a change in Identity, current State, bounded Events, or prior MEMORY produces a distinct run identity.

## Exact input evidence

The evidence records exactly what the existing crystallization core supplied to the crystallizer:

- Identity content;
- current State records, including their existing identity/provenance/validity fields;
- the bounded Event snapshot selected by `max_events`, including Event actor and payload;
- prior MEMORY Markdown or `null`.

The evaluation layer does not reconstruct a parallel crystallization input model. Full persisted Event history may still be consulted by the existing Validator after generation, exactly as defined by the crystallization contract.

## Raw output and deterministic decisions

Raw model behavior and RelayLM acceptance are separate evidence channels.

`raw_model` records:

- complete generated `memory_markdown`;
- every generated `StateCandidate` before deterministic validation.

`deterministic_relay` records:

- each existing Validator decision and its status/action/reason;
- resulting Canonical State;
- whether MEMORY changed;
- resulting persisted MEMORY Markdown.

A rejected candidate remains visible as raw model behavior. The evaluation layer never converts rejection into success and has no privileged State mutation path.

This separation is important for crystallization quality: a model can produce useful readable consolidation while proposing an invalid State change, or it can produce a valid State proposal while organizing MEMORY poorly. Those are distinct observations.

## Product-quality review

CRY2 defines a bounded manual/product review sidecar with no weighted composite score.

The exact axes are:

1. `durable_information_selection` — durable information is retained without promoting incidental conversation merely because it is recent.
2. `state_taxonomy_key_normalization` — durable concepts use appropriate existing State classes/keys and avoid unnecessary vocabulary or alias drift.
3. `transient_durable_discipline` — short-lived referents, unresolved questions, and active tasks are not silently promoted into durable State/MEMORY.
4. `correction_supersession_preservation` — corrections and supersession preserve the new current understanding without erasing historical occurrence evidence.
5. `temporal_provenance_fidelity` — current/historical/unknown meaning and governed Event/State provenance are preserved without invented authority.
6. `memory_organization_readability` — generated MEMORY is readable, useful long-term synthesis rather than a chronological transcript dump.
7. `semantic_stability` — repeated evidence can be reviewed for semantic churn, duplicate aliases, and unstable organization across passes.

Each axis is rated `pass`, `fail`, or `not_rated`, with an optional note. A review names the exact evidence run IDs it covers and receives its own stable content-addressed review ID. The review contract intentionally has no `score` field.

`semantic_stability` normally requires multiple evidence runs or a controlled repeated-pass protocol. CRY2 defines the review axis and citable evidence identity; it does not claim stability from a single pass.


## Semantic-stability replication rule

CRY2 `semantic_stability` is a product-quality axis for repeated actual-model crystallization evidence. Its authority identity is:

```text
actual-model-crystallization-stability-rule-v1
```

This rule is owned by Actual-model Evaluation (#1386). It evaluates whether independently generated semantic outputs materially churn when the same crystallization input, target, provider, and decoding condition are repeated. It is separate from:

- output correctness by itself;
- deterministic Validator correctness;
- provider protocol reliability;
- sequential re-crystallization of already-mutated MEMORY;
- cognitive-budget boundary attribution;
- population-level statistical stability.

A model can therefore be stable-but-wrong: the other six CRY2 axes may fail while `semantic_stability` passes for the same repeatable failure.

### Independent same-input replicate identity

Every replicate in one crystallization-stability tranche must preserve:

- the same exact RelayLM freeze commit;
- the same Character fixture ID and revision;
- the same case ID and version;
- the same exact initial Canonical State;
- the same exact Event snapshot;
- the same exact prior MEMORY;
- the same `max_events`;
- the same target, model artifact, and tokenizer identity;
- the same provider and adapter identity;
- the same structured-output schema;
- the same effective context window;
- the same decoding controls and seed policy;
- the same LM Studio runtime/deployment identity; and
- the same `condition_id`.

Only `replicate_id`, the resulting content-addressed run/review IDs, and the model-generated output may vary. Each replicate starts from a fresh workspace copied from the same immutable fixture. A preceding replicate's resulting State or MEMORY must never become the next replicate's input. This is independent same-input replication, not sequential repeated-pass crystallization.

Within this rule, the exact RelayLM commit is part of the cohort identity. Runs from different commits, including docs-only commits, must not be combined into one canonical stability tranche. The existing CRY4 run remains historical first product-quality evidence and is not a member of a later CRY5 tranche created from a new exact freeze.

### Material semantic comparison

Exact string equality is not required. Non-material differences may include Markdown wording, heading wording, section ordering, candidate ordering, or harmless prose formatting.

Review material meaning at the concept level, including:

1. durable semantic units selected or omitted;
2. transient information retained or discarded;
3. unsupported assistant-only information promoted or rejected;
4. current versus historical meaning;
5. correction and supersession meaning;
6. StateCandidate semantic identity: `state_class`, `key`, `op`, and semantic value;
7. unnecessary alias or key proliferation; and
8. MEMORY semantic organization.

Exact candidate count/order and exact Markdown surface are not oracles. A CRY2 pass/fail result from another quality axis must not be copied into `semantic_stability`; the comparison must be made directly from the repeated raw and deterministic semantic evidence.

### Minimal stopping rule

Use at most three successful replicates for one exact-freeze crystallization-stability tranche:

```text
replicate 0 = initial observation
replicate 1 = independent replication
```

If replicates 0 and 1 materially disagree, rate `semantic_stability = fail` and stop. Do not add a run to manufacture a majority.

If replicates 0 and 1 are materially consistent, run replicate 2 as confirmation when confirmation is required. If all three are materially consistent, rate `semantic_stability = pass`. If replicate 2 materially disagrees, rate `semantic_stability = fail`.

Three successful runs are the maximum tranche. This is an engineering reproducibility gate, not a statistical significance, confidence, probability, or population-level model-property claim.

### Failed execution handling

A provider, protocol, or bounded execution failure that produces no successful CRY2 `<run_id>.json` is not a semantic comparison run and does not count toward the successful-replicate limit. Preserve an immutable bounded-failure receipt, do not reinterpret the failure as semantic quality, and do not automatically continue with a replacement generation in the same transaction. The bounded transaction stops with `semantic_stability = not_rated`, and a later transaction begins from fresh authority.

### Review and claim scope

Use the existing `ActualModelCrystallizationReview.evidence_run_ids` capability to list every successful run in the tranche. Reviews retain the exact seven CRY2 axes and the `pass` / `fail` / `not_rated` outcomes. No weighted or composite score is introduced.

This rule is separate from `actual-model-replication-rule-v1` in the total cognitive-budget evidence reference. CRY5 does not redefine budget pressure comparisons, directional boundary attribution, provider semantics, crystallization semantics, prompt/schema behavior, or calibration/default policy.

## Evidence artifacts

`write_actual_model_crystallization_evidence(...)` writes one `<run_id>.json` artifact.

Artifact behavior follows the existing actual-model reproducibility rule:

- an identical existing artifact is idempotent;
- the same run ID with different evidence is rejected;
- a repeated model execution that may produce different output must use a distinct `replicate_id` rather than overwrite prior evidence.

This keeps raw model variability auditable instead of hiding it behind last-write-wins persistence.

## Relationship to other authority

This evidence surface is owned by Actual-model Evaluation (#1386).

It consumes but does not redefine:

- crystallization semantics and provider contract (#1260, `docs/contracts/crystallization.md`);
- `OpenAICompatibleCrystallizer` wire/prompt behavior;
- Canonical State and deterministic Validator semantics;
- typed MEMORY temporal/provenance authority;
- ordinary-turn actual-model scenario/evidence contracts;
- deterministic native evaluation registry/counts (#1247);
- cognitive-budget calibration/default policy.

The deterministic `crystallization_integrity` component remains the native contract test of core authority boundaries. Actual-model crystallization evidence instead records how a real replaceable model behaves inside those already-governed boundaries.

## Current limitation

CRY2 is an **evidence contract**, not a target-model verdict. It does not establish that the current crystallizer prompt is product-optimal or that a particular local model reliably improves taxonomy drift, duplicate keys, transient over-persistence, correction handling, temporal nuance, or semantic stability.

Those claims require recorded real-model runs and bounded review using this evidence surface. Prompt/schema changes should follow such evidence rather than being inferred from the existence of the contract itself.
