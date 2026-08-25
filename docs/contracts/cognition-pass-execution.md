# Cognition Pass Execution Contract

Status: current provider-neutral per-pass execution-option contract for RelayLM 1.0.

Owner: #1533 / `cognitive_turn`.

This contract defines per-pass reasoning/decoding intent and pre-generation capability resolution. It chooses no numeric defaults. Core 1.0 is two-pass first; #1388 later resolves the calibrated two-pass profile and #1446 carries it through release configuration.

## Policy intent versus effective request

`CognitionPassPolicy` represents unresolved policy intent.

Reasoning mode is closed to:

```text
auto
off
bounded
```

The current scalar controls are:

```text
temperature
top_p
max_output_tokens
```

A bounded reasoning policy may also carry a positive reasoning budget.

`auto` means profile-owned resolution. It never means “silently inherit an unknown provider default”.

`CognitionPassRequest` is the fully resolved pre-generation form. In that form:

- `reasoning_mode` may be `off`, `bounded`, or explicit omission;
- `reasoning_mode=auto` is invalid;
- a reasoning budget requires `bounded`;
- scalar `None` means explicit omission from the effective provider request;
- provider-neutral validation checks only shape/finiteness/positivity; provider-specific range rules remain provider-owned.

## Core 1.0 pass roles

The qualified release/reference path is `two_pass`:

```text
Pass 1
  visible conversation
  latency-sensitive

Pass 2
  non-authoritative subjective turn-interpretation scaffold
  semantic State/Continuity proposal extraction
  no second visible response
```

Pass 1 and Pass 2 reuse one canonical cognitive prompt prefix through the serialized `CognitiveInput` and diverge only after an explicit pass boundary. The canonical Pass 1 suffix is intentionally minimal: `Respond as this character.` It does not impose a RelayLM-owned visible output format that could conflict with a legitimate user request for JSON, Markdown, code, or another representation.

Pass 1 and Pass 2 may use independently resolved requests after that common cognitive prefix.

Pass 2 reasoning is an escalation mechanism, not an assumed default. Begin from the lowest effective explicit condition proven by the exact backend/model. Increase Pass 2 effort only when #1386 shows semantic need while Pass 1 remains controlled.

Single-pass remains a compatibility/future-optimization surface and is not a Core 1.0 quality-tuning prerequisite.

## Normalized capability view

`CognitionExecutionCapabilities` is a COGP-owned consumer view over facts supplied by the provider/model owner. It does not discover or infer support.

It can represent:

```text
structured_output
streaming
reasoning modes: off / bounded
bounded reasoning-budget control
per-pass decoding/output controls
```

`structured_output` remains a truthful provider capability fact because a backend may expose native JSON-schema/grammar features for other purposes. **Current RelayLM cognition modes do not require that capability merely to carry RelayLM-owned cognition IR.**

Current OpenAI-compatible cognition uses ordinary provider message content and RelayLM-owned parsing/type construction for both:

- single-pass combined cognitive IR; and
- two-pass Pass 2 turn-interpretation scaffold plus proposal IR.

Therefore `structured_output=false` is not by itself a mode-level failure for `single_pass`, `two_pass`, or `shadow_two_pass` under the current cognition contracts.

`streaming=true` is still required when the selected execution path actually requests streaming.

## Provider-facts normalization

`normalize_cognition_execution_capabilities(...)` performs closed-vocabulary normalization only.

Accepted reasoning capability strings are:

```text
off
bounded
```

Accepted COGP decoding-control strings are:

```text
temperature
top_p
max_output_tokens
```

Unknown values, duplicates and `auto` fail closed. Provider-level controls that COGP does not own are not promoted by spelling similarity.

The provider remains authoritative for discovery, attestation and external wire realization.

## Applied / omitted / unsupported

`resolve_pass_request(...)` classifies every requested option as exactly one of:

```text
applied
omitted
unsupported
```

- `applied` — the supplied provider/model capability view declares the requested explicit control;
- `omitted` — the resolved request intentionally carries no explicit value;
- `unsupported` — an explicit value was requested but capability truth does not declare support.

Unsupported is never silently rewritten to omitted.

`CognitionPassResolution.require_supported()` fails before generation when an explicit request is unsupported.

A future profile-owned fallback must be explicit and auditable; it cannot be invented by the adapter or Turn layer.

## Mode-level capability gate

`require_mode_capabilities(...)` checks only actual mode-level prerequisites.

Current rules:

- `auto` must already be resolved before generation;
- provider-native `structured_output` is **not** required by the current RelayLM-owned cognition IR paths;
- a streaming request requires declared streaming support;
- explicit unsupported pass options are handled by `resolve_pass_request(...).require_supported()`.

Capability declaration proves only that a request can be represented. It does not prove product quality; #1386 owns observed actual-model quality.

## RelayLM-owned Pass 2 scaffold and proposal IR

Canonical OpenAI-compatible Pass 2 is:

```text
ordinary provider chat/message generation
  -> plain content containing turn_interpretation + proposal IR
  -> RelayLM JSON parse
  -> exact top-level and turn_interpretation shape checks
  -> non-authoritative turn_interpretation is not promoted into State/Continuity authority
  -> typed StateCandidate / ContinuityCandidate construction
  -> existing deterministic validation/lifecycle
```

The top-level IR contains exactly:

```text
turn_interpretation
state_candidates
continuity_candidates
```

`turn_interpretation` is an explicit cognitive scaffold. It is generated before candidates in this order:

```text
user_meaning
change_signals
self_meaning
assistant_effects
unresolved
continuity_signals
state_candidates
continuity_candidates
```

Every interpretation field is an array of strings. Empty arrays are normal. Blank or whitespace-only string members carry no semantic meaning in this non-authoritative scaffold and are treated as absent/no-op items before scaffold acceptance. Missing fields, additional fields, non-array fields, or non-string array members fail closed. Non-blank semantic strings are not trimmed, rewritten, promoted into authority, or used as a substitute for candidate/source validation.

The fields mean:

- `user_meaning` — what this character understands the user to mean through Identity, accepted State and supplied context; it is not merely a literal utterance summary;
- `change_signals` — meaningful change relative to accepted current understanding, including correction, revocation, supersession, strengthening, weakening or new meaning;
- `self_meaning` — what the interpreted meaning means to the character itself, including personal, emotional, relational, self-belief, self-goal or self-condition implications;
- `assistant_effects` — meanings introduced by the Pass 1 response that may matter to continuation, such as questions, proposals, commitments or deliberately unfinished interaction;
- `unresolved` — meanings that should not yet be decided because evidence is ambiguous, incomplete or underspecified;
- `continuity_signals` — meanings worth carrying across upcoming turns for coherent interaction.

The scaffold is not accepted State, Continuity, Memory, evidence authority, or deterministic validation input merely because the model emitted it. It structures generation and provides raw model-output evidence for diagnosis. Candidate parsing, source semantics, validation and commit remain the existing authority boundary.

Interpretation is not State. Pass 2 proposes State only when an adequately grounded and sufficiently resolved meaning represents a meaningful durable change in accepted current understanding. An item in `unresolved` does not by itself require `Continuity(kind=unresolved)`; Continuity is proposed only when carrying the meaning across upcoming turns materially improves coherence.

The current experiment preserves model-authored candidate `sources` and the existing Event-ID source rules. Deterministic source reconstruction is not introduced as part of this prompt/scaffold change so actual-model regressions remain causally attributable.

Provider-native `response_format`, JSON Schema, grammar or constrained decoding is not required to define or enforce this semantic boundary. The OpenAI-compatible Pass 2 suffix carries a compact RelayLM-owned field glossary, candidate wire grammar and exact top-level example as ordinary prompt content rather than embedding the full JSON Schema. RelayLM remains authoritative for JSON parsing, exact scaffold/candidate shape checks and type construction after generation.

Malformed JSON, extra/missing keys, invalid interpretation shape, invalid candidate shapes or invalid typed values fail closed in RelayLM and produce no proposal commit.

## RelayLM-owned single-pass combined IR

The optional/compatibility single-pass path uses ordinary provider content containing exactly:

```text
utterance
state_candidates
continuity_candidates
```

RelayLM owns parsing and typed construction here as well. The existence of a combined JSON object does not make provider-native structured output a semantic prerequisite.

## Semantic/mechanical split

The model owns language-dependent semantic judgment. RelayLM owns deterministic structure and authority mechanics.

Do not move correction, negation, uncertainty, transient/durable interpretation, source attribution or other free-form multilingual semantics into language-specific deterministic parsers.

Do not ask the model to author mechanical metadata that RelayLM can construct deterministically. Existing candidate-source carriage is deliberately preserved for the current controlled prompt experiment and may be revisited only as a separately attributable change if actual-model evidence warrants it.

## Relationship to provider controls

Provider owners own:

- external request fields/endpoints;
- capability discovery/attestation;
- provider-specific value/range validation;
- exact applied reasoning/decoding carriage;
- transport of ordinary cognition message content.

COGP uses provider-neutral intent only.

Existing provider-level controls such as `seed` remain provider-owned unless COGP separately promotes them into its vocabulary.

## Resolved-request carriage

The two-pass path carries independently resolved requests:

```text
pass1_request
  -> run_user_turn_two_pass
  -> generate_conversation
  -> visible response

pass2_request
  -> originating-turn-bound extraction
  -> generate_extraction
  -> RelayLM scaffold/proposal-IR parse and candidate type construction
```

Buffered and streaming two-pass paths must carry equivalent resolved pass semantics. A streaming implementation that silently drops Pass 1 or Pass 2 controls is not compliant.

When no pass request is supplied, no layer may strengthen reasoning merely because the call is Pass 2.

## Content-free completion observation

A successful cognition pass may carry provider-supplied completion facts separately from semantic model content through `CognitionCompletionMetadata`.

The provider-neutral observation can retain only facts that the actual provider response supplied and RelayLM observed for that exact pass:

```text
finish_reason
prompt_tokens
completion_tokens
total_tokens
reasoning_tokens
```

These fields are optional observations, not request controls and not semantic authority. Missing provider data remains missing. RelayLM must not reconstruct a missing value from response text length, tokenizer re-tokenization, context remainder, configured output/reasoning budgets, another pass, or a later request.

For buffered OpenAI-compatible Pass 1 and Pass 2, valid response-envelope usage may be copied into the typed pass output. For the current streaming Pass 1 contract, `finish_reason` may be retained when present in an admitted SSE choice; token usage is left missing unless the supported stream protocol actually exposes and admits it. No usage value is invented from the stream body.

`TwoPassTurnResult` carries the admitted Pass 1 completion observation, and `TwoPassExtractionResult` carries the Pass 2 observation once a typed Pass 2 output exists, including stale or later deterministic-failure dispositions. A failure before a valid provider Pass 2 output has no completion observation.

Completion observation does not change request serialization, generation, retries, response-first ordering, State/Continuity validation, stale-result semantics, or commit authority. #1386 may bind these content-free facts into immutable actual-model evidence in a separate owner transaction.

## Reproducibility

Materially output-affecting configuration must remain distinguishable in evidence as applied, omitted or unsupported.

A citable two-pass run requires the exact Pass 1/Pass 2 request identity plus the current RelayLM common-prefix prompt/scaffold/IR/parser contract revision and exact provider/model capability evidence.

## Ownership

#1533 owns:

- per-pass provider-neutral reasoning/decoding intent;
- `auto` versus effective omission semantics;
- normalized capability vocabulary;
- applied/omitted/unsupported classification;
- fail-closed explicit unsupported behavior;
- current mode-level capability requirements;
- the canonical common cognitive prefix and pass-specific cognition responsibilities;
- the non-authoritative six-field Pass 2 turn-interpretation scaffold;
- the RelayLM Pass 2 proposal-IR ownership boundary;
- content-free per-pass completion-observation carriage through canonical two-pass outputs and diagnostics.

#1386 owns actual-model evidence. #1388 owns calibrated profile/default selection. #1446 owns release config and operator provenance. Provider owners retain external wire and truthful capability authority.

## Non-goals

- numeric defaults;
- profile selection;
- provider-specific fallback tables;
- language-specific semantic parsers;
- direct model mutation of State/Continuity;
- provider-native structured-output requirements for current cognition modes;
- deterministic Event-ID reconstruction as part of this prompt experiment;
- single-pass prompt optimization as a Core 1.0 gate.

## Principle

> Resolve only real capability requirements. Do not mistake JSON inside RelayLM-owned ordinary message content for a provider-native structured-output dependency.