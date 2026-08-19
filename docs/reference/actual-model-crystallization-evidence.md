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
