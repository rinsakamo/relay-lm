# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM v1 through COGP4.

This contract is owned by #1533 under `cognitive_turn`. Execution topology may vary, while RelayLM's authority rule remains constant:

```text
model cognition -> proposals -> existing deterministic validation/lifecycle -> RelayLM authority
```

## RelayLM 1.0 modes

`CognitionExecutionMode` contains exactly:

```text
single_pass
two_pass
shadow_two_pass
auto
```

`selective_two_pass` and learned extraction gating remain outside RelayLM 1.0.

### `single_pass`

One model generation produces the visible response plus StateCandidate and ContinuityCandidate proposals. Existing ordinary-turn APIs retain this supported baseline.

### `two_pass`

Pass 1 produces only the visible response. Pass 2 produces only immediate State/Continuity proposals. COGP3 implements an explicit response-first path using the same supplied provider object/model resources sequentially.

A valid Pass 1 creates the Assistant Event before Pass 2 completes. Pass 2 receives the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context. It can affect State/Continuity only through the existing deterministic validators and current stale-result guards.

### `shadow_two_pass`

COGP4 implements first-class shadow evidence:

```text
canonical single_pass
  -> normal validation and accepted result

same originating CognitiveInput
+ canonical response
  -> shadow structured extraction
  -> raw proposal evidence only
  -> no canonical State/Continuity change
```

The canonical turn completes independently of shadow completion. Shadow StateCandidate and ContinuityCandidate values are never submitted as a second accepted result.

A shadow failure cannot invalidate the successful canonical response or alter its User Event, Assistant Event, Canonical State, or accepted Continuity. Shadow evidence remains bound to the originating User Event.

Provider-neutral execution identity and shadow-observation semantics are frozen in `docs/contracts/cognition-execution-evidence.md`. #1386 remains the owner of actual-model manifests, artifacts, reviews, cohorts, comparisons, and causal reasoning identity.

### `auto`

`auto` means evidence-backed calibrated profile resolution against actual provider/model/runtime capability. It never means an unknown provider default. #1388 owns canonical profile/default selection and #1446 later carries it through release configuration.

`auto` is unresolved policy, so a completed execution evidence record identifies the mode that actually ran rather than recording `auto` as the execution.

## Pass responsibilities

Pass 1 owns visible conversation quality, persona/identity continuity, current-context coherence, and latency-sensitive tempo.

Pass 2 owns immediate structured proposal extraction, including correction/negation interpretation, canonical class/key reuse, transient-vs-durable discipline, and source preservation.

In canonical `two_pass`, Pass 2 proposals may reach existing deterministic validators after the execution guards succeed. In `shadow_two_pass`, the same proposal shape is evidence-only.

Per-pass reasoning/decoding intent remains defined by `docs/contracts/cognition-pass-execution.md`. COGP chooses no numeric defaults.

## Authority ordering

For canonical and shadow extraction alike:

```text
user/source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The visible assistant response cannot independently establish a user or external fact.

## Canonical two-pass failure and ordering

For canonical `two_pass`, a successful Pass 1 remains a valid conversation when Pass 2 later fails. Failed Pass 2 proposals cause no State or Continuity change. Current extraction outcomes are `committed`, `stale`, and `failed`.

`CognitionExecutionRuntime` is a process-local ordering holder. Pass 2 model inference does not hold the conversation or authority lock. A newer turn advances the execution revision before preparing its input. Final Pass 2 application requires the originating revision/Event and the origin State/Continuity snapshots still match current authority under a short ordering boundary. A mismatch is `stale` and changes nothing.

This does not create a durable State revision or change cross-process persistence rules.

## Shadow failure semantics

For `shadow_two_pass`, canonical `single_pass` is already complete before shadow evidence matters.

```text
shadow completed -> raw proposals observable; canonical result unchanged
shadow failed    -> bounded shadow_pass2_failed; canonical result unchanged
```

Shadow extraction does not advance Continuity lifecycle and does not run proposal acceptance for the purpose of State/Continuity change.

## Streaming

Canonical `two_pass` streaming exposes only Pass 1 response deltas and starts Pass 2 after complete Pass 1 acceptance.

`shadow_two_pass` streaming uses the existing canonical single-pass streaming path. Shadow extraction starts only after the complete canonical result has committed and never produces another visible response.

## Current implementation status

```text
single_pass       implemented baseline
two_pass          implemented response-first path
shadow_two_pass   implemented non-authoritative evidence path
auto              contract frozen; selected profile/default deferred to #1388/#1446
```

None of these facts selects the release default.

## Ownership

COGP / #1533 owns execution topology, pass responsibilities, response-first/failure/stale rules, per-pass execution intent, execution-topology identity, and shadow semantics.

Provider owners retain external wire behavior, capability truth, provider-specific validation, and exact applied request configuration. #1386 owns actual-model evidence methodology/artifacts. #1388 owns profile/default selection. #1446 owns release-config carriage. State, Continuity, Context Compiler, Retrieval, Cognitive Budget, and crystallization retain their existing owners.

## Deferred after COGP4

- #1386 execution-topology carriage and controlled A/B/C evidence (COGP5);
- #1388 calibrated profile/default selection (COGP6);
- #1446 runtime configuration integration (COGP7);
- #1449 release reconciliation (COGP8);
- provider-specific reasoning controls not already supported;
- two simultaneously resident online models;
- StateCandidate/ContinuityCandidate grammar redesign.
