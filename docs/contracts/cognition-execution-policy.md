# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM v1 through COGP3.

This contract is owned by #1533 under the existing `cognitive_turn` semantic owner. Ordinary-turn execution topology is configurable policy; State/Continuity authority remains unchanged.

```text
model cognition
  -> response / proposals
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

One model generation produces the visible response plus StateCandidate and ContinuityCandidate proposals. The existing ordinary-turn APIs retain this implemented baseline.

### `two_pass`

Pass 1 produces only the visible conversational response. Pass 2 produces only immediate State/Continuity proposals. COGP3 implements this as an explicit response-first runtime path.

Pass 1 success creates the Assistant Event before Pass 2 completes. The returned two-pass turn therefore contains the already-valid visible response plus an independently completing extraction task.

Pass 2 receives the originating `CognitiveInput` and the Pass 1 response. The response is interpretive context only; its text is not source evidence and cannot self-certify user or external facts.

The initial OpenAI-compatible implementation reuses one constructed provider object, its existing client, configured request model, endpoint, and provider-owned explicit decoding configuration for Pass 1 then Pass 2. It does not require a second resident online model.

### `shadow_two_pass`

Canonical behavior remains `single_pass`; an additional Pass 2 result is evidence-only and cannot mutate State or accepted Continuity. COGP4 owns this still-deferred evidence carriage.

### `auto`

`auto` means evidence-backed calibrated profile resolution against actual provider/model/runtime capability. It never means silently inheriting an unknown provider default. #1388 owns the canonical profile/default decision; #1446 later carries it through release configuration.

## Pass responsibility boundary

### Pass 1 — conversation

Pass 1 owns:

- visible natural-language response;
- persona / identity continuity;
- current-context coherence;
- latency-sensitive conversational tempo.

It does not produce StateCandidate or ContinuityCandidate proposals in `two_pass` mode.

### Pass 2 — immediate structured cognition

Pass 2 owns proposals for:

- StateCandidate extraction;
- ContinuityCandidate extraction;
- correction / negation / supersession interpretation;
- exact canonical class/key reuse where supported by current authority;
- transient-vs-durable discipline;
- provenance/source preservation.

The provider-neutral per-pass reasoning/decoding intent contract remains `docs/contracts/cognition-pass-execution.md`. COGP3 does not choose numeric defaults or invent unsupported reasoning controls.

## Evidence and authority ordering

The authority order is:

```text
user/source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

For example, if the user says only that they have recently been drinking coffee and Pass 1 paraphrases that as liking coffee, the assistant paraphrase alone cannot authorize `user.preference/coffee = likes`.

Existing source-role/provenance, StateCandidate validation, and Continuity validation rules are reused unchanged.

## Response-first failure semantics

For `two_pass`:

```text
Pass 1 = success
Pass 2 = failure / malformed output / provider error
```

means:

```text
visible response remains valid
User Event remains preserved
Assistant Event remains preserved
failed Pass 2 proposals commit nothing
partial State mutation is prohibited
partial Continuity mutation is prohibited
failure is reported by bounded/content-free extraction status
```

The current COGP3 result statuses are:

```text
committed
stale
failed
```

`failed` may include bounded reasons such as `pass2_failed` or `continuity_runtime_required`. Raw exception text and semantic payload are not promoted into the result contract.

A Pass 2 output that includes Continuity proposals without an explicit Continuity runtime fails before any State mutation, so a missing Continuity runtime cannot create a partial cross-channel commit.

## Turn ordering and stale-result prevention

`CognitionExecutionRuntime` is a process-local ordering holder for the explicit two-pass path. It is not State or Continuity authority.

The runtime uses two deliberately different lock scopes:

- a conversation lock serializes Pass 1 preparation/generation so ordinary user turns keep deterministic Event ordering;
- a short authority lock serializes only new-turn reservation/binding and the final Pass 2 stale-check/validation/commit boundary.

Pass 2 model inference runs outside both locks after Pass 1 returns. Therefore Turn N+1 Pass 1 does not wait merely because Turn N Pass 2 is still reasoning.

When a newer turn enters the two-pass runtime, it advances the process-local execution revision before preparing its input. Older pending extraction is thereby stale before the newer turn can become current.

A Pass 2 result may commit only while the short authority lock proves all of the following together:

- its execution revision is still the latest revision;
- its originating User Event is still the latest bound two-pass turn;
- persisted Canonical State still equals the origin State snapshot;
- accepted Continuity still equals the origin Continuity snapshot when a runtime is present.

Only after those checks do the existing State and Continuity validators run and any mutations apply. The stale check and mutation therefore cannot be interleaved with a newer two-pass turn reservation inside this runtime.

If any guard fails, the result is `stale` and performs no State/Continuity mutation. Working Context and retained Events remain available to bridge the temporary extraction gap.

This process-local guard does not create a new durable State revision scheme or change the persistence owner's cross-process concurrency guarantees.

## Streaming

The explicit two-pass streaming path streams only the Pass 1 `utterance`. The complete Pass 1 structured conversation result must still validate before the Assistant Event is created and Pass 2 is scheduled.

Pass 2 starts only after Pass 1 completion; it does not stream a second user-visible response.

## Current implementation status after COGP3

```text
single_pass       implemented baseline
two_pass          implemented explicit response-first runtime path
shadow_two_pass   semantic contract frozen; evidence carriage deferred to COGP4
auto              semantic/policy contract frozen; default/profile deferred to #1388/#1446
```

COGP3 does not yet make `two_pass` the release default or expose a release-config selector. Those are later owner transactions.

## Ownership boundaries

COGP / #1533 owns execution topology, pass responsibility, response-first semantics, turn ordering, stale-result rules, and provider-neutral per-pass intent.

Provider owners retain external request/response transport semantics, capability truth, provider-specific validation, and exact applied request configuration. The COGP3 OpenAI-compatible two-pass extension reuses the canonical adapter machinery rather than redefining State/Continuity candidate grammar.

#1386 owns controlled actual-model evidence. #1388 owns evidence-backed profile/default selection. #1446 owns release config carriage and effective-config provenance. State, Continuity, Context Compiler, Retrieval, Cognitive Budget, and crystallization owners retain their existing semantic authority.

## Deferred after COGP3

- shadow evidence carriage and execution identity (COGP4);
- actual-model A/B/C comparison (#1386 / COGP5);
- calibrated default/profile selection (#1388 / COGP6);
- release runtime-config integration (#1446 / COGP7);
- provider-specific per-request reasoning controls not already supported;
- a second resident online model;
- StateCandidate or ContinuityCandidate grammar redesign;
- direct model mutation of State or Continuity.
