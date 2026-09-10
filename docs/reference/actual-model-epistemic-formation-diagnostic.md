# Actual-model epistemic-formation diagnostic

Owner: Issue #2516. This is an evaluation-only diagnostic. It does not change
production Core, the production cognition wire, the Continuity lifecycle, or
the current Stage R scenario authority.

## Question and scope

The diagnostic asks one question under the current qualified Gemma-4 and
llama.cpp condition with reasoning explicitly OFF: can the model itself form a
source-grounded representation of information or a question that the current
input explicitly leaves not yet known, determined, or answered?

The primary discriminator is only turn 2 of the current Stage R
`continuity-lifecycle-v1` scenario. The scenario text is read from the current
Stage R authority at execution time. Turn 3 is loaded only as part of validating
the authoritative fixture and is never sent to the diagnostic or executed.

This is not a Continuity proposal test and does not ask the model to produce
Continuity candidates or State candidates.

## Model-facing input contract

`build_t2_epistemic_formation_input` uses the repository context compiler with:

1. the authoritative fixture Identity and State;
2. turn 1 as one user-authored, provenance-bearing recent event; and
3. turn 2 as the current user event.

The diagnostic serializer then sends only the compiler-selected prior context
and current Input. It does not send accepted Continuity IR, a model-authored
Pass 1 response, the T2 scenario label, an expected candidate/key/action, an
oracle answer, or turn 3. This keeps the prior referential evidence available
without making the lifecycle representation the object of the test.

The instruction is intentionally general:

> Identify any information or question that the current input itself explicitly
> leaves not yet known, determined, or answered. Use only supplied current input
> and context. Do not infer or invent missing facts.

The native schema has exactly one top-level `items` array. Each item has exactly
`subject_span`, `unknown_evidence_span`, and `source_event_id`. Both spans must
be exact substrings of the current Input content. `source_event_id` must equal
the current Input Event ID. The parser performs only these mechanical checks;
it does not decide whether a span expresses the intended meaning.

## Evidence and review boundary

The final request body is persisted before transport. The raw provider response
is persisted independently before parsing or semantic review. A mechanically
valid output produces a separate mechanical-observation artifact; it does not
produce a semantic verdict.

The later review is zero-generation and uses only:

- the current Input;
- the retained raw structured output;
- the returned subject and evidence spans; and
- the mechanical validation result.

The review artifact follows `EPISTEMIC_FORMATION_REVIEW_SCHEMA` and may record
`FORMATION_PRESENT`, `FORMATION_ABSENT`, or
`TRANSPORT_PROTOCOL_LIMITATION`. `FORMATION_PRESENT` is limited to formation
under the OFF condition; it is not a lifecycle mapping or product-quality
qualification. A transport or protocol failure cannot support either semantic
formation conclusion.

## Physical-owner boundary

Issue #2516 performs no model, provider, server, GPU, LM Studio, Stage R, or
FastCal execution. The future physical owner invokes
`python3 -m tools.v1_stage_r_llama_cpp_epistemic_formation_wsl` once. The
existing llama.cpp transaction owns the fresh roots, exact checkout, operator
llama paths, one server lifecycle, and cleanup. The host performs one T2
diagnostic generation, uses native JSON Schema, sends `reasoning_effort=none`,
and has no semantic retry or fallback. The current llama.cpp admission
condition remains endpoint `http://127.0.0.1:1234/v1`, context 8192, one slot,
and context shift disabled unless fresh authority changes those values.

Any semantic review is performed after the physical transaction from retained
artifacts. The repository transaction itself records zero physical counts.
