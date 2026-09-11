# Actual-model semantic-to-Continuity projection diagnostic

## Purpose

This evaluation-only diagnostic separates semantic formation from projection into RelayLM Continuity IR.

It exists because #2529 established that, under the qualified Gemma-4 / llama.cpp explicit reasoning-OFF condition, the model can identify a source-grounded question that the current input explicitly leaves not yet known. The next question is narrower:

> If that formed meaning is held fixed and supplied as empirical evidence, can the model map it into the existing canonical Continuity candidate grammar?

The diagnostic is not a production prompt proposal and does not change RelayLM cognition semantics.

## Boundary

The probe receives only:

- the current input Event;
- one or more previously formed `EpistemicFormationItem` observations;
- each observation's exact `subject_span`, `unknown_evidence_span`, and `source_event_id`.

Before request construction, RelayLM requires every observation to be grounded in the current Event: the source ID must match and both spans must be exact current-input substrings.

The probe deliberately omits:

- State extraction;
- the Pass 1 response;
- open-ended discovery of additional meanings;
- fixed-slot three-kind scanning;
- fixture-specific expected keys, operations, values, or oracle answers.

The observation is explicitly described as an empirical model-reported observation rather than authoritative truth.

## Projection contract

The target of the experiment is the real existing Continuity IR. The model-facing instruction therefore exposes the canonical generic meanings of:

- `referent`;
- `unresolved`;
- `active_task`;
- `set` and `resolve`;
- `user_assertion`, `assistant_inference`, and `assistant_commitment`.

This is intentional. Unlike the formation probe, this experiment is specifically testing the mapping into those coordinates.

The native JSON Schema has exactly one top-level field:

```json
{"continuity_candidates": []}
```

Its array schema is a deep copy of the current production `WIRE_SCHEMA.properties.continuity_candidates`. No shadow or renamed IR is introduced.

Parsed candidates reuse the existing provider candidate parser. The diagnostic additionally fails closed if any candidate cites a source other than the current input Event.

## Interpretation

A later separately owned physical run is interpreted only after retained raw evidence is reviewed without another generation:

```text
canonical projection present
  -> reject P1 semantic-to-IR inability
  -> support P2 production multiplexing/interference

canonical projection absent or materially wrong
  -> support P1 semantic-to-IR projection failure

native transport/protocol invalid
  -> no P1/P2 semantic inference
```

A successful projection is not itself a production fix. It only demonstrates that the model can perform the mapping when formation is supplied and production multiplexing is removed.

## Retained-formation rule

The physical experiment must not regenerate the #2529 formation observation merely to feed this probe. A future physical owner must bind its supplied observation to retained #2529 evidence and preserve artifact identity/provenance in its evidence capsule.

Repository tests use synthetic observations; fixture-specific #2529 answer content is not embedded in the diagnostic implementation.

## Physical ordering

Repository preparation performs zero provider/model calls and zero GPU execution.

Do not create or consume the projection physical owner until:

1. the projection diagnostic support is merged; and
2. #2541's generic llama.cpp host-summary contract defect is merged and reconciled.

The physical owner then gets exactly one generation under fresh authority and the current qualified llama.cpp reasoning-OFF carriage unless a later owner intentionally changes that treatment.

## Non-goals

This diagnostic does not change:

- production Pass 1 or Pass 2 prompts;
- production `CognitiveInput` serialization;
- State semantics;
- Continuity ontology, validator, materializer, lifecycle, oracle, or scorer;
- reasoning defaults;
- model, quantization, context window, or provider defaults;
- FastCal;
- PR #2441.

## Principle

> Hold formation fixed; vary only the projection boundary.
