# Continuity semantic-label invariance diagnostic

This reference owns the evaluation-only diagnostic introduced by #2385. The
current physical carriage is the llama.cpp/llama-server Stage R qualification
path. The existing LM Studio module remains the historical semantic contract;
it is not a fallback for current physical admission.

## Purpose

#2358 made `referent`, `unresolved`, and `active_task` mechanically explicit as fixed slots. Under the current fixed-slot reasoning-OFF treatment, the provider still chose `unresolved = none` on the lifecycle turns that require the canonical `unresolved` set and resolve. The omission therefore survived removal of the variable-list / structural-salience degree of freedom.

This diagnostic asks one narrower question:

> Does changing only the model-facing name of the same Continuity meaning change semantic realization?

It does not change canonical Continuity semantics or the production cognition wire.

## Shadow coordinate

The diagnostic reuses the #2358 fixed-slot transport but substitutes one model-facing coordinate:

```text
canonical kind: unresolved
shadow alias:   open_question
```

The alias denotes the same existing semantic meaning: an explicit open question or unknown value that remains to be resolved. `referent` and `active_task` are unchanged.

The model-facing fixed-slot shape is therefore:

```text
continuity_decisions:
  referent:      {decision: none | emit, transitions: [...]}
  open_question: {decision: none | emit, transitions: [...]}
  active_task:   {decision: none | emit, transitions: [...]}
```

Every emitted transition inside `open_question` must also carry `kind = open_question` on the shadow wire.

## Prompt boundary

The provider first constructs the ordinary #2358 fixed-slot request from current production semantics. It then applies the alias only to RelayLM-generated model-facing Continuity representation:

- static Pass 2 Continuity instructions use `open_question` in place of the canonical `unresolved` coordinate;
- already-accepted projected Continuity records whose canonical kind is `unresolved` are shown to the model with `kind = open_question`;
- current user Input, Pass 1 response, Event Evidence, State, Memory, Knowledge, semantic values, source IDs, and other user/assistant-authored text are not rewritten merely because they contain the English word `unresolved`.

This keeps the intervention at the Cognitive IR coordinate rather than becoming a lexical rewrite of task evidence.

## Canonical translation boundary

After native structured output is received, the diagnostic requires the exact shadow slot set `referent / open_question / active_task`. Before any ordinary deterministic RelayLM authority is invoked, an emitted `open_question` transition is translated losslessly to `kind = unresolved`.

From that point onward the existing fixed-slot parser, canonical `ContinuityCandidate`, Event source validation, deterministic lifecycle handling/materialization, Stage R boundary evaluation, and scorer are reused unchanged.

The shadow alias is never accepted or persisted as product Continuity. JSON Schema controls the diagnostic shape only; it is not semantic authority.

## Current llama.cpp execution

The diagnostic inherits the current llama.cpp physical boundary:

- physical runtime, artifact, server PID/log, native JSON Schema, and exact
  `/v1/chat/completions/input_tokens` accounting are attested by the current
  llama.cpp host;
- the one-command WSL/LocalCodex carriage creates fresh workspace/artifact
  roots and the shared transaction owns one server lifetime and one host;
- Pass 1 uses the unchanged production request; Pass 2 uses the native
  fixed-slot diagnostic request with only the `unresolved` label aliased;
- reasoning OFF is requested as `reasoning_effort=none` and requires
  completion-side evidence;
- the exact input-token counter receives the final aliased request body before
  the provider posts it;
- no retry, fallback, reload, restart, model swap, tuning, schema rescue,
  parser/Validator relaxation, reasoning escalation, LM Studio fallback, or
  FastCal is permitted.

The future owner command is:

```text
python3 -m tools.v1_stage_r_llama_cpp_continuity_label_invariance_wsl
```

It is an owner boundary, not an instruction to execute the diagnostic inside
#2496. #2496 creates that separate physical owner only after repository support
is merged and stops before any server or provider/model call.

Each successful Pass 2 writes a create-once shadow-decision observation preserving the raw `open_question` choice before canonical translation.

## Diagnostic acceptance

The primary discriminator is `continuity-lifecycle-v1`.

A clean positive result requires:

- T1: no spurious `open_question` transition;
- T2: `open_question` emits `set`, which translates to canonical `unresolved set`;
- T3: `open_question` emits `resolve`, which translates to canonical `unresolved resolve`;
- translated canonical scoring reaches `TP=5 / FP=0 / FN=0` with no new churn;
- effective reasoning OFF, #2280 State, false-attribution resistance, protocol/provenance, and deterministic boundaries remain valid.

#2281 lexical behavior remains a separate observation and is not repaired here.

## Interpretation

A clean positive result is evidence that this target model/runtime is sensitive to the model-facing semantic coordinate name. It does not authorize production adoption of `open_question`; #1533/#2043 must separately decide any production IR change and require broader semantic-invariance / held-out qualification.

If the alias still yields `none` or a wrong transition, stop label tuning and move the diagnosis deeper to semantic formation/capability. If the provider cannot realize the strict shadow schema, record that transport/capability limitation without fallback.

## Scope

This module, its tests, and this reference are evaluation-only. They are deliberately outside the Core semantic qualification identity and must not change the Core semantic fingerprint.
