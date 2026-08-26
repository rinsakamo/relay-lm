# Cognition Pass Execution Contract

Status: current provider-neutral per-pass execution-option contract for RelayLM 1.0.

Owner: #1533 / `cognitive_turn`.

This contract defines per-pass reasoning/decoding intent, Pass 2 structured-output transport selection, and pre-generation capability resolution. It chooses no numeric defaults. Core 1.0 is two-pass first; #1388 later resolves the calibrated two-pass profile and #1446 carries it through release configuration.

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
- provider-neutral validation checks only shape/finiteness/positivity; provider-specific range rules remain provider-owned;
- Pass 2 may additionally carry `structured_output_mode=plain|native|auto`;
- `structured_output_mode` is invalid on Pass 1 because Pass 1 owns unconstrained visible conversation, not extraction IR.

For Pass 2 structured-output transport:

```text
plain
  ordinary provider message content containing RelayLM-owned JSON IR

native
  OpenAI-compatible response_format=json_schema for the RelayLM extraction wire

auto
  native only when affirmative provider capability truth is available;
  otherwise plain
```

Omitting `structured_output_mode` preserves the established `plain` behavior. Explicit `native` never silently falls back to `plain`; if the selected provider rejects the native request, generation fails closed through the provider boundary.

## Core 1.0 pass roles

The qualified release/reference path is `two_pass`:

```text
Pass 1
  visible conversation
  latency-sensitive

Pass 2
  direct semantic State/Continuity proposal extraction
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

`structured_output` is a truthful provider capability fact. It is not a prerequisite for the `two_pass` topology because Pass 2 always has a `plain` transport. It becomes relevant when `structured_output_mode=auto` decides whether provider-native JSON Schema may be used without guessing.

Current single-pass cognition continues to use ordinary provider message content and RelayLM-owned parsing/type construction. Current two-pass Pass 2 may use either ordinary provider message content or native JSON Schema constrained output; both converge on the same RelayLM parser, typed candidate construction, deterministic validation and authority boundary.

Therefore `structured_output=false` is not by itself a mode-level failure for `single_pass`, `two_pass`, or `shadow_two_pass`. It causes Pass 2 `auto` selection to remain `plain`; explicit `native` is an operator request and any provider rejection is surfaced rather than silently rewritten.

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

Unknown values, duplicates and reasoning `auto` fail closed. Provider-level controls that COGP does not own are not promoted by spelling similarity.

The provider remains authoritative for discovery, attestation and external wire realization.

## Applied / omitted / unsupported

`resolve_pass_request(...)` classifies reasoning and scalar decoding/output options as exactly one of:

```text
applied
omitted
unsupported
```

- `applied` — the supplied provider/model capability view declares the requested explicit control;
- `omitted` — the resolved request intentionally carries no explicit value;
- `unsupported` — an explicit value was requested but capability truth does not declare support.

Unsupported is never silently rewritten to omitted.

`CognitionPassResolution.require_supported()` fails before generation when an explicit reasoning/decoding/output request is unsupported.

Pass 2 structured-output transport has separate semantics: `plain` is always representable by the current OpenAI-compatible adapter; `auto` consults affirmative structured-output capability truth and otherwise chooses `plain`; explicit `native` emits the native wire exactly and lets provider rejection fail closed.

A future profile-owned fallback must be explicit and auditable; it cannot be invented by the adapter or Turn layer.

## Mode-level capability gate

`require_mode_capabilities(...)` checks only actual topology-level prerequisites.

Current rules:

- cognition topology `auto` must already be resolved before generation;
- provider-native `structured_output` is not required by the `two_pass` topology because Pass 2 has a plain transport;
- a streaming request requires declared streaming support;
- explicit unsupported reasoning/decoding/output pass options are handled by `resolve_pass_request(...).require_supported()`;
- Pass 2 structured-output selection is handled at the extraction transport boundary, not by pretending it is a topology requirement.

Capability declaration proves only that a request can be represented. It does not prove product quality; #1386 owns observed actual-model quality.

## RelayLM-owned Pass 2 direct proposal IR

Canonical OpenAI-compatible Pass 2 has one semantic prompt contract and two selectable transport paths:

```text
shared CognitiveInput + Pass 1 response + semantic State/Continuity guidance
  -> plain
       ordinary provider chat/message JSON generation
     OR
     native
       response_format=json_schema constrained generation
  -> RelayLM JSON parse
  -> exact top-level candidate-collection shape checks
  -> typed StateCandidate / ContinuityCandidate construction
  -> source validation
  -> existing deterministic validation/lifecycle
```

The top-level IR contains exactly:

```text
state_candidates
continuity_candidates
```

There is no model-authored intermediate `turn_interpretation` authority or canonical scaffold between the semantic prompt and the candidate collections. Pass 2 performs language-dependent interpretation as part of direct projection into State/Continuity proposals, while the semantic prompt continues to require grounded, sufficiently resolved, meaningful durable State changes and bounded Continuity.

A candidate is still only a proposal. It does not become accepted State, Continuity, Memory, evidence authority, or deterministic validation input merely because the model emitted it. Candidate parsing, source semantics, validation and commit remain the existing authority boundary.

### Structure versus semantics

The transport schema and the semantic prompt have different responsibilities.

Provider-native JSON Schema may constrain mechanical facts such as:

- exact top-level members;
- object/array/string/null shape;
- State `op=set|remove`;
- Continuity `kind`, `op`, and `epistemic_role` enum values;
- required candidate fields and source-array shape.

It does **not** decide semantic representation such as whether “I like coffee” is a durable preference, which stable State key should represent a meaning, whether a correction warrants `remove`, or whether ambiguous meaning deserves Continuity.

The Pass 2 prompt therefore retains short semantic definitions and bounded canonical State examples. Those examples use the originating turn's real Event ID so source grammar is realistic, but they are representation examples only: the model must never copy their keys, values or claims unless the current evidence supports that exact meaning. Existing class/key vocabulary is preferred over synonymous reinvention.

The current contract preserves model-authored candidate `sources` and the existing Event-ID source rules. Deterministic source reconstruction is not introduced as part of this change.

### Plain transport

`structured_output_mode=plain` carries a compact RelayLM-owned candidate wire grammar, semantic guidance, bounded canonical examples and exact top-level example as ordinary prompt content. No `response_format` is sent.

This is also the behavior when the Pass 2 structured-output field is omitted, preserving the established plain transport selection.

### Native transport

`structured_output_mode=native` sends OpenAI-compatible:

```text
response_format.type = json_schema
response_format.json_schema.strict = true
```

with the current direct two-collection extraction wire schema. Pass 1 never receives this field.

Native constrained decoding is an additional structural guard, not a transfer of semantic or commit authority to the provider. The returned content still passes through the same RelayLM JSON parser, exact-shape checks, typed candidate construction, source checks and deterministic State/Continuity lifecycle.

`structured_output_mode=auto` selects this path only when the provider capability view affirmatively declares structured output. Absence of capability evidence selects `plain`; compatibility alone is not treated as evidence.

Malformed JSON, extra/missing top-level keys, invalid candidate shapes or invalid typed values that reach RelayLM still fail closed and produce no proposal commit.

## RelayLM-owned single-pass combined IR

The optional/compatibility single-pass path uses ordinary provider content containing exactly:

```text
utterance
state_candidates
continuity_candidates
```

RelayLM owns parsing and typed construction here as well. Pass 2 native structured-output selection does not alter this single-pass contract.

## Semantic/mechanical split

The model owns language-dependent semantic judgment. RelayLM owns deterministic structure and authority mechanics.

Do not move correction, negation, uncertainty, transient/durable interpretation, source attribution or other free-form multilingual semantics into language-specific deterministic parsers.

Do not ask the model to author mechanical metadata that RelayLM can construct deterministically. Existing candidate-source carriage is deliberately preserved and may be revisited only as a separately attributable change if actual-model evidence warrants it.

## Relationship to provider controls

Provider owners own:

- external request fields/endpoints;
- capability discovery/attestation;
- provider-specific value/range validation;
- exact applied reasoning/decoding carriage;
- native structured-output request realization;
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
  -> structured-output transport selection
  -> generate_extraction
  -> RelayLM direct proposal-IR parse and candidate type construction
```

Buffered and streaming two-pass paths must carry equivalent resolved Pass 1 semantics. Pass 2 extraction remains buffered. A runtime that silently drops configured Pass 1 reasoning/decoding controls or Pass 2 extraction controls is not compliant.

When no pass request is supplied, no layer may strengthen reasoning merely because the call is Pass 2, and Pass 2 structured-output transport remains the established plain path.

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

A citable two-pass run requires the exact Pass 1/Pass 2 request identity, including the Pass 2 structured-output transport selection, plus the current RelayLM common-prefix prompt/direct-IR/parser contract revision and exact provider/model capability evidence.

## Ownership

#1533 owns:

- per-pass provider-neutral reasoning/decoding intent;
- Pass 2 `plain|native|auto` structured-output transport semantics;
- `auto` versus effective omission semantics;
- normalized capability vocabulary;
- applied/omitted/unsupported classification for reasoning/decoding/output controls;
- fail-closed explicit unsupported behavior;
- current mode-level capability requirements;
- the canonical common cognitive prefix and pass-specific cognition responsibilities;
- the direct Pass 2 State/Continuity proposal-IR ownership boundary;
- content-free per-pass completion-observation carriage through canonical two-pass outputs and diagnostics.

#1386 owns actual-model evidence. #1388 owns calibrated profile/default selection. #1446 owns release config and operator provenance. Provider owners retain external wire and truthful capability authority.

## Non-goals

- numeric defaults;
- profile selection;
- provider-specific fallback tables;
- language-specific semantic parsers;
- direct model mutation of State/Continuity;
- making provider-native structured output a topology-level prerequisite;
- silently falling back from explicit `native` to `plain`;
- deterministic Event-ID reconstruction as part of this change;
- single-pass prompt optimization as a Core 1.0 gate.

## Principle

> Use constrained decoding for mechanical structure when explicitly selected and supported; project semantic proposals directly and keep authority in RelayLM.
