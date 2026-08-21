# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM v1 with RelayLM-owned single-pass combined IR and two-pass proposal IR structure.

This contract is owned by #1533 under `cognitive_turn`. Execution topology may vary, while RelayLM's authority rule remains constant:

```text
model cognition -> RelayLM-owned IR parse/type construction -> proposals -> existing deterministic validation/lifecycle -> RelayLM authority
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

Conversation and proposal generation still share one generation, so the model-facing combined IR remains larger than two-pass Pass 1. The OpenAI-compatible request is ordinary message generation: it does not require provider-native `response_format`, JSON-schema grammar, or equivalent structured-output enforcement. The model returns plain message content containing exactly the RelayLM-owned combined cognitive IR:

```text
utterance
state_candidates
continuity_candidates
```

RelayLM parses the JSON, enforces the exact top-level and candidate shapes, constructs typed `CognitiveOutput`, and fails closed before the existing commit boundary when the IR is malformed or incomplete. Provider-native structured-output support may exist, but it does not own or define canonical `single_pass` structure.

### `two_pass`

Pass 1 produces only the visible response. Pass 2 produces only immediate State/Continuity proposals. COGP implements an explicit response-first path using the same supplied provider object/model resources sequentially.

A valid Pass 1 creates the Assistant Event before Pass 2 completes. Pass 2 receives the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context. It can affect State/Continuity only through the existing deterministic validators and current stale-result guards.

The two passes intentionally have different wire responsibilities:

```text
Pass 1 — conversation
  input: governed conversational context
  output: plain natural-language response content
  no State/Continuity proposal schema
  no JSON wrapper required by RelayLM

Pass 2 — immediate extraction
  input: originating governed turn + Pass 1 response as lower-authority context
  provider output: plain message content containing compact RelayLM proposal IR
  IR keys:
    state_candidates
    continuity_candidates

RelayLM
  owns the proposal IR contract
  parses/validates proposal IR shape
  assembles typed CognitionExtractionOutput deterministically
  runs existing State/Continuity validators and lifecycle authority
```

The model does not author execution IDs, turn binding, provider identity, evidence metadata, commit status, or canonical RelayLM envelopes. Those remain RelayLM-owned deterministic structure.

This responsibility split is semantic rather than provider-specific. Canonical `two_pass` does **not** require provider-native JSON-schema/grammar/structured-output support. The provider transports ordinary message content; RelayLM owns the proposal IR grammar, parsing, type construction, and fail-closed validation. Backend structured-output features may still exist as provider capabilities for other paths, but they do not define the canonical Pass 2 schema or correctness boundary.

### `shadow_two_pass`

COGP implements first-class shadow evidence:

```text
canonical single_pass
  -> plain combined cognitive IR
  -> RelayLM parse/type construction
  -> normal validation and accepted result

same originating CognitiveInput
+ canonical response
  -> shadow plain proposal IR extraction
  -> RelayLM proposal-IR parse/type construction
  -> raw proposal evidence only
  -> no canonical State/Continuity change
```

The canonical turn completes independently of shadow completion. Shadow StateCandidate and ContinuityCandidate values are never submitted as a second accepted result.

A shadow failure cannot invalidate the successful canonical response or alter its User Event, Assistant Event, Canonical State, or accepted Continuity. Shadow evidence remains bound to the originating User Event.

The canonical side uses the same RelayLM-owned combined-IR boundary as ordinary `single_pass`. The shadow extraction pass uses the same RelayLM-owned proposal-IR parsing boundary as canonical `two_pass`. Neither side requires provider-native structured-output enforcement.

Provider-neutral execution identity and shadow-observation semantics are frozen in `docs/contracts/cognition-execution-evidence.md`. #1386 remains the owner of actual-model manifests, artifacts, reviews, cohorts, comparisons, and causal reasoning identity.

### `auto`

`auto` means evidence-backed calibrated profile resolution against actual provider/model/runtime capability. It never means an unknown provider default. #1388 owns canonical profile/default selection and #1446 later carries it through release configuration.

`auto` is unresolved policy, so a completed execution evidence record identifies the mode that actually ran rather than recording `auto` as the execution.

## Pass responsibilities

`single_pass` jointly asks one generation for visible conversation plus immediate semantic proposals. Its model-facing result is the RelayLM-owned combined cognitive IR; RelayLM parses and types that result before any deterministic State/Continuity commit.

Pass 1 in `two_pass` owns visible conversation quality, persona/identity continuity, current-context coherence, and latency-sensitive tempo. Its provider result is natural-language response content, not a RelayLM state/proposal envelope.

Pass 2 owns immediate semantic proposal extraction, including correction/negation interpretation, canonical class/key reuse, transient-vs-durable discipline, and source preservation. Its model-facing result is ordinary provider message content constrained by the compact RelayLM-owned proposal IR contract; provider-native structured-output enforcement is not required.

In canonical `two_pass`, Pass 2 proposals may reach existing deterministic validators after RelayLM parses the IR and the execution guards succeed. In `shadow_two_pass`, the same proposal shape is evidence-only.

Per-pass reasoning/decoding intent remains defined by `docs/contracts/cognition-pass-execution.md`. COGP chooses no numeric defaults.

## Deterministic assembly boundary

RelayLM owns mechanical structure that does not require language understanding.

The model is responsible for semantic interpretation needed to produce the visible utterance and propose candidate meaning. RelayLM is responsible for the combined/proposal IR grammars, deterministic JSON parsing, exact-key checks, type construction, origin/turn binding, validation, normalization already owned by State/Continuity contracts, and evidence/runtime envelopes. Malformed or incomplete IR fails closed before it can mutate State/Continuity. In `two_pass`, such failure does not invalidate an already-delivered valid Pass 1 response.

Do not move multilingual semantic interpretation into language-specific RelayLM parsers merely to reduce model work. Conversely, do not ask the model to reproduce metadata or envelope structure RelayLM can construct without semantic judgment.

In short:

```text
natural language / governed CognitiveInput
  -> model semantic interpretation
  -> ordinary provider message containing RelayLM-owned IR
  -> deterministic RelayLM parse/assembly/validation
  -> canonical response + State/Continuity authority
```

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

A provider-native structured-output failure is not a required failure class for canonical `two_pass`: the provider may return HTTP-successful plain content, after which RelayLM itself decides whether the proposal IR is valid. Parse/type/validation failure remains bounded Pass 2 failure and cannot invalidate the already-delivered Pass 1 response.

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

Canonical `two_pass` streaming exposes Pass 1 provider content deltas directly as visible response deltas and starts Pass 2 after complete Pass 1 acceptance. It does not buffer a JSON `utterance` envelope merely to recover the same visible text.

Canonical `single_pass` streaming incrementally decodes visible `utterance` content from the combined IR stream but does not commit until the complete combined IR has passed RelayLM parsing/type construction and existing deterministic validation. `shadow_two_pass` streaming uses this canonical single-pass streaming path. Shadow extraction starts only after the complete canonical result has committed and never produces another visible response.

## Capacity relationship

Execution capacity and semantic reasoning effort are separate controls.

`effective_context_window` is calibrated by #1388 from exact model/provider/runtime evidence and is not a reasoning budget. Fixed single-pass, Pass 1, and Pass 2 prompt/wire overhead should be measured separately so #1267 can consume derived per-path input budgets rather than inventing its own context capacity.

Both the single-pass combined wire and the two-pass extraction wire now rely on RelayLM-owned plain-content IR instructions rather than provider-native response-schema carriage. This does not itself choose an effective context window, Context Compiler budget, output reserve, or reasoning budget. #1386 must remeasure exact serialized footprints after these semantic changes before historical capacity measurements are used for revised screening.

## Current implementation status

```text
single_pass       implemented one-generation baseline; combined IR structure parsed/enforced by RelayLM
two_pass          implemented response-first path; Pass 2 proposal IR parsed/enforced by RelayLM
shadow_two_pass   implemented non-authoritative evidence path; both model-facing IR boundaries are RelayLM-owned
auto              contract frozen; selected profile/default deferred to #1388/#1446
```

None of these facts selects the release default.

## Ownership

COGP / #1533 owns execution topology, pass responsibilities, response-first/failure/stale rules, per-pass execution intent, execution-topology identity, shadow semantics, the RelayLM combined cognitive IR for `single_pass`, the compact proposal IR for Pass 2, and the semantic boundary between model proposal meaning and RelayLM deterministic assembly.

Provider owners retain external wire transport, capability truth, provider-specific reasoning/decoding validation, and exact applied request configuration. Provider-native structured-output capability does not own or define either canonical cognition IR. #1386 owns actual-model evidence methodology/artifacts. #1388 owns effective-context and profile/default calibration. #1446 owns release-config carriage. State, Continuity, Context Compiler, Retrieval, Cognitive Budget, and crystallization retain their existing owners.

## Deferred

- fresh exact fixed prompt/token footprint measurement under #1386 evidence after RelayLM-owned single-pass and Pass 2 structure changes;
- #1388 effective-context and per-pass reserve/input-budget calibration;
- revised #1386 controlled topology/reasoning evidence after capacity prerequisites are citable;
- #1388 calibrated profile/default selection;
- #1446 runtime configuration integration;
- #1449 release reconciliation;
- two simultaneously resident online models;
- semantic StateCandidate/ContinuityCandidate grammar redesign.
