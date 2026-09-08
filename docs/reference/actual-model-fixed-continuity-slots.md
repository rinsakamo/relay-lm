# Fixed per-kind Continuity decision diagnostic

This reference owns the evaluation-only diagnostic introduced by #2358.

## Purpose

Current Core 1.0 Pass 2 emits direct `state_candidates` and a variable-length `continuity_candidates` list. Repeated LM Studio effective-OFF evidence has shown a fragile `unresolved` omission even after general prompt-only and accepted-context comparison repairs.

This diagnostic asks one narrower question:

> Does making the three existing Continuity kind decisions mechanically explicit remove the omission without changing Continuity semantics?

It does not change the production cognition wire.

## Shadow transport

Pass 1 remains the current production conversation pass.

Pass 2 keeps the production CognitiveInput, Pass 1 response, semantic instructions, decoding, reasoning request, native structured-output transport, State candidate grammar, provenance rules, deterministic Validator, Continuity lifecycle, Stage R scenarios, and scoring.

Only the model-facing Continuity output representation changes for the diagnostic:

```text
state_candidates: [...]
continuity_decisions:
  referent:
    decision: none | emit
    transitions: [ordinary ContinuityCandidate wire items]
  unresolved:
    decision: none | emit
    transitions: [ordinary ContinuityCandidate wire items]
  active_task:
    decision: none | emit
    transitions: [ordinary ContinuityCandidate wire items]
```

All three slots are required exactly once.

`decision = none` requires an empty transition list. `decision = emit` requires at least one transition. Every transition retains the existing `kind`, `key`, `op`, `value`, `sources`, and `epistemic_role` wire grammar, and its kind must match the containing slot.

The representation deliberately retains an array inside each kind slot. It therefore does not reduce current semantics to at most one candidate per kind.

## Translation boundary

The diagnostic provider parses the fixed-slot object and flattens only emitted transitions into the existing production candidate parser. From that point onward, the ordinary typed `ContinuityCandidate`, current Event source validation, deterministic Continuity validation/materialization, execution evidence, boundary evaluation, and Stage R scoring are reused unchanged.

`none` creates no candidate and no authority. The slot object itself is never accepted Continuity and is not persisted into product State or Continuity.

JSON Schema remains mechanical shape control only. It does not become semantic or commit authority.

## Semantic-first execution

The diagnostic reuses the repository-owned LM Studio semantic-first contract:

- stable non-secret model/runtime facts are transaction declarations;
- provider-native/content-free HTTP preflight is zero;
- the first provider request is actual Stage R semantic work;
- production reasoning OFF is requested with `reasoning_effort=none`;
- actual response-side reasoning observations remain required for an effective-OFF claim;
- request/explicit Pass 2 failures remain fail-fast;
- no retry, fallback, restart, reload, model swap, prompt tuning, parser relaxation, reasoning escalation, or FastCal is performed.

The generic OpenAI-compatible cognition capability descriptor is not a native-structured-output admission gate for this diagnostic. That descriptor truthfully reports `structured_output=false` when the generic adapter has no independent native capability attestation source. The fixed-slot transaction instead carries the already-explicit Pass 2 `NATIVE` request and lets the first real semantic extraction request establish whether LM Studio accepts or rejects the strict fixed-slot schema. No extra provider request is added for this capability check.

Each successful Pass 2 also writes a create-once fixed-slot decision observation so the three explicit decisions can be reviewed independently of the flattened candidate result.

## Diagnostic acceptance

The primary discriminating scenario is the current `continuity-lifecycle-v1` authority.

A clean positive result requires:

- T1: referent emits `set`, active_task emits `set`, unresolved explicitly chooses `none`;
- T2: unresolved emits the required `set`, referent and active_task explicitly choose `none`;
- T3: unresolved and active_task emit `resolve`, referent explicitly chooses `none`;
- flattened existing-candidate scoring reaches TP=5 / FP=0 / FN=0;
- current Event provenance remains valid;
- #2280 State non-regression, false-attribution resistance, protocol boundaries, and effective reasoning OFF remain valid.

#2281 referent lexical fidelity is reviewed separately because its qualified lexical-source repair is not part of this diagnostic.

## Interpretation

A positive physical result does not authorize a production wire change. It supplies evidence to #1533 / #2043 for a separate production IR decision, implementation, exact-head qualification, and merged-production requalification.

A negative result stops the hypothesis that variable-list omission is the likely cause. Do not respond by adding fixture-specific slots or benchmark-specific schema branches.

If the provider cannot reliably realize the strict fixed-slot native schema, record that transport/capability limitation without retrying with a weaker schema.

## Scope

This module, its tests, and this reference are evaluation-only. They are deliberately outside the Core semantic qualification identity and must not change the Core semantic fingerprint.
