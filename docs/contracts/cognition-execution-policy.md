# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM v1 through COGP2.

This contract is owned by #1533 and is part of the existing `cognitive_turn` semantic owner. It replaces the former architectural assumption that one ordinary turn must always contain exactly one semantic model generation. The current runtime remains the implemented `single_pass` baseline until COGP3 adds the two-pass runtime path.

Execution topology never changes RelayLM semantic authority:

```text
model output
  -> proposal
  -> existing deterministic State / Continuity validation and lifecycle
  -> RelayLM authority
```

A second pass, a larger model, or a larger reasoning budget never grants direct State or Continuity authority.

## Closed RelayLM 1.0 mode vocabulary

`CognitionExecutionMode` contains exactly:

```text
single_pass
two_pass
shadow_two_pass
auto
```

`selective_two_pass` and learned extraction gating are not RelayLM 1.0 modes.

### `single_pass`

One model generation produces the visible response plus StateCandidate and ContinuityCandidate proposals. This is the current implemented ordinary-turn behavior and remains a supported baseline even after two-pass support exists.

### `two_pass`

Pass 1 owns the visible conversational response. Pass 2 owns immediate structured State/Continuity proposal extraction. Pass 2 remains proposal-producing cognition and uses the existing deterministic authority boundary.

The response is **response-first**: a successful Pass 1 response is semantically valid independently of whether Pass 2 later completes successfully.

### `shadow_two_pass`

Canonical behavior remains the normal `single_pass` result and its existing validation/commit path. An additional Pass 2 extraction is evidence-only and must not mutate Canonical State or accepted Continuity.

Shadow output is not a second State authority.

### `auto`

`auto` means resolution through an evidence-backed calibrated cognition profile against actual provider/model/runtime capability. It does not mean “omit the field and inherit a hidden provider default,” and it is not a hard-coded vendor/model-name table.

# Pass responsibility boundary

## Pass 1 — conversation

Pass 1 is responsible for:

- visible natural-language response;
- persona / identity continuity;
- current-context coherence;
- latency-sensitive conversational tempo.

In `two_pass`, Pass 1 is not required to produce StateCandidate or ContinuityCandidate proposals.

## Pass 2 — immediate structured cognition

Pass 2 is responsible for proposals for:

- StateCandidate extraction;
- ContinuityCandidate extraction;
- correction / negation / supersession interpretation;
- exact canonical class/key reuse where supported by current authority;
- transient-vs-durable discipline;
- provenance/source preservation.

Pass 1 and Pass 2 now have provider-neutral reasoning/decoding intent semantics under `docs/contracts/cognition-pass-execution.md`. Those types distinguish policy-owned `auto` from a fully resolved generation request, classify effective values as applied/omitted/unsupported, and fail closed on explicit unsupported behavior. COGP2 chooses no numeric default and does not add provider-specific reasoning wire fields.

# Evidence and authority ordering

Pass 2 may consume the current governed User Event, relevant accepted Canonical State, accepted Continuity, allowed State classes/relevant exact keys, and the Pass 1 response as interpretive context.

The authority order is:

```text
user/source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The Pass 1 response cannot self-certify a user or external fact. For example, if the user says only that they have recently been drinking coffee and Pass 1 paraphrases that as liking coffee, that assistant paraphrase alone cannot authorize `user.preference/coffee = likes`.

Existing source-role/provenance, StateCandidate validation, and Continuity validation rules remain unchanged.

# RelayLM 1.0 online resource boundary

The initial supported two-pass topology reuses the **same already-loaded online model sequentially**:

```text
same loaded model
  Pass 1
    -> Pass 2
```

RelayLM 1.0 does not require two online model artifacts to remain resident simultaneously. This is an execution-topology boundary, not a provider-specific model-loading API contract.

Off-turn crystallization remains separately governed by #1260 and may use a different/larger/offloaded model without changing this ordinary-turn contract.

# Pass 2 failure semantics

For `two_pass`:

```text
Pass 1 = success
Pass 2 = failure / timeout / malformed structured output
```

means:

```text
visible response remains valid/deliverable
failed Pass 2 proposals do not commit
partial State mutation = prohibited
partial Continuity mutation = prohibited
original governed Event evidence remains preserved
failure may be observed only through bounded/content-free diagnostics or evidence
```

A post-response extraction failure does not retroactively convert a valid conversation response into a failed conversation turn.

Later off-turn crystallization may re-interpret retained Event evidence through its separately governed proposal/validation path.

# Turn ordering and stale-result invariants

Two-pass completion may overlap later user input. RelayLM 1.0 therefore requires:

- every Pass 2 result is bound to its originating turn/User Event identity;
- a late extraction result must not overwrite newer accepted State/Continuity as though it were current merely because it finished later;
- commit ordering/revision checks are deterministic;
- Turn N+1 Pass 1 should not ordinarily block only because Turn N Pass 2 is pending;
- recent governed Events / Working Context may bridge temporary structured-extraction staleness;
- any join/wait policy must be explicit rather than an accidental lock.

COGP1 freezes these invariants. COGP3 owns the runtime mechanism and executable race/failure tests that realize them.

# Current implementation status after COGP2

```text
single_pass       implemented baseline
two_pass          execution + per-pass policy contracts frozen; runtime deferred to COGP3
shadow_two_pass   semantic contract frozen; evidence carriage deferred to COGP4
auto              semantic/policy contract frozen; profile resolution/default deferred to #1388/#1446
```

The existing ordinary-turn functions continue to execute the current single-pass path until COGP3 changes runtime assembly. The provider-neutral capability view in COGP2 does not by itself assert that any concrete provider supports reasoning, reasoning budgets, or `max_output_tokens`; provider owners remain the source of those facts.

# Ownership boundaries

COGP / #1533 owns:

- available cognition execution modes;
- Pass 1 / Pass 2 responsibility split;
- response-first semantics;
- same-loaded-model initial 1.0 topology;
- Pass 2 failure semantics;
- turn-bound ordering/stale-result invariants;
- provider-neutral per-pass execution intent;
- `auto` versus effective omission semantics;
- applied/omitted/unsupported capability-resolution outcomes.

#1386 owns controlled actual-model evidence for execution modes.

#1388 owns evidence-backed profile/default selection and provenance.

#1446 owns runtime-config schema carriage, precedence, direct operator overrides, runtime assembly, and effective-config reporting.

Provider owners retain provider wire, capability discovery/declaration, provider-specific validation, and exact applied request configuration.

State, Continuity, Context Compiler, Retrieval, Cognitive Budget, and crystallization owners retain their existing semantic authority.

# Current deferred work

Not yet implemented by COGP1/COGP2:

- two-pass generation/orchestration;
- provider-specific per-pass reasoning/output-control carriage where unsupported today;
- response/Pass-2 asynchronous scheduling;
- stale-result revision machinery;
- shadow evidence artifacts;
- actual-model A/B/C execution;
- calibrated default/profile selection;
- release runtime-config fields;
- a second resident online model;
- StateCandidate or ContinuityCandidate grammar changes;
- direct model mutation of State or Continuity.
