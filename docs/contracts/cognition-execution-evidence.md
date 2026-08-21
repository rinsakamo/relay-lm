# Cognition Execution Evidence Contract

Status: COGP provider-neutral execution-topology and shadow-observation contract for RelayLM v1, including RelayLM-owned single-pass combined IR and Pass 2 proposal IR structure.

This contract is owned by #1533 under `cognitive_turn`. It defines what ordinary-turn execution topology occurred and how `shadow_two_pass` raw extraction is carried without becoming semantic authority. It does not replace #1386 Actual-model Evaluation identity, artifacts, reviews, cohorts, or comparison methodology.

## Purpose

Actual-model evidence must be able to distinguish:

```text
single_pass
  combined response/proposal IR parsed by RelayLM

two_pass
  Pass 1 conversation
  Pass 2 canonical extraction into RelayLM-owned proposal IR

shadow_two_pass
  canonical single_pass
  + non-authoritative Pass 2 extraction observation
```

without inferring topology from provider request counts or mutable implementation details.

The execution identity is provider-neutral. Provider/model/reasoning/decoding/runtime identity remains owned by provider and #1386 surfaces and is combined later rather than copied into COGP authority.

## Execution evidence identity

`CognitionExecutionEvidenceIdentity` has format version `1` and binds:

- resolved cognition mode;
- buffered or streaming delivery path;
- exact RelayLM semantic output contract identities used by the topology;
- which path is permitted to produce canonical State/Continuity mutation.

Current contract identities are:

```text
single-pass combined output:
  relaylm_cognitive_output:v1

conversation-only output:
  relaylm_conversation_output:v1

RelayLM proposal-IR extraction output:
  relaylm_structured_cognition_output:v1
```

These are **RelayLM execution-contract identities**. `relaylm_cognitive_output:v1` identifies the RelayLM-owned combined response/proposal IR and parser/type-construction boundary. `relaylm_structured_cognition_output:v1` identifies the RelayLM-owned compact proposal IR and parser/type-construction boundary. Neither requires or identifies a provider-native `response_format`, JSON-schema grammar, or equivalent structured-output feature. The names are not claims about an exact model artifact, provider deployment, reasoning setting, decoding configuration, tokenizer, or context window.

### `single_pass`

```text
mode                       single_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          omitted
shadow_output              omitted
canonical_mutation_source  single_pass
```

For canonical `single_pass`, the OpenAI-compatible realization is ordinary provider message content containing the combined RelayLM cognitive IR. RelayLM performs JSON parsing, exact top-level/candidate shape checks, typed `CognitiveOutput` construction, and fail-closed validation before the existing deterministic commit boundary. Provider-native structured-output support is not part of the topology requirement.

### `two_pass`

```text
mode                       two_pass
canonical_output_contract  omitted
conversation_output        relaylm_conversation_output:v1
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              omitted
canonical_mutation_source  pass2
```

For canonical `two_pass`, the extraction contract is realized as plain provider message content that RelayLM parses into the compact proposal IR. Provider-native structured-output support is not part of the topology requirement.

### `shadow_two_pass`

```text
mode                       shadow_two_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              relaylm_structured_cognition_output:v1
canonical_mutation_source  single_pass
```

The canonical side uses the same RelayLM-owned combined-IR boundary as ordinary `single_pass`; the shadow extraction side uses plain provider content plus the same RelayLM-owned proposal-IR parser as canonical `two_pass`. Neither side requires provider-native structured-output enforcement.

`auto` is unresolved policy, not an execution that happened, and therefore cannot be persisted as this evidence identity. A citable run must record the resolved execution mode.

## Shadow observation

`ShadowExtractionEvidence` binds one shadow Pass 2 attempt to:

- the `shadow_two_pass` execution identity;
- the originating RelayLM User Event ID;
- terminal status `completed` or `failed`;
- the raw `CognitionExtractionOutput` only when completed;
- a bounded content-free failure reason only when failed.

The initial bounded failure reason is:

```text
shadow_pass2_failed
```

Raw exception text is not part of the execution evidence contract.

A completed shadow observation preserves the model's raw StateCandidate and ContinuityCandidate proposals after the RelayLM-owned proposal IR has been parsed and converted to typed values. It does **not** contain deterministic acceptance decisions because shadow proposals are deliberately not submitted to State or Continuity validators for mutation.

## Non-authoritative invariant

`shadow_two_pass` means:

```text
canonical single-pass plain combined IR
  -> RelayLM parse/type construction
  -> existing State / Continuity validation
  -> canonical mutation as normal

same originating CognitiveInput
+ canonical response
  -> shadow extraction plain content
  -> RelayLM proposal-IR parse/type construction
  -> raw evidence only
  -> NO State validation for mutation
  -> NO Continuity validation for mutation
  -> NO canonical mutation
```

Shadow output never becomes a second State or Continuity authority, even if its proposal appears more semantically convincing than the canonical single-pass proposal.

The Pass 1/canonical response supplied to shadow extraction remains interpretive context only. Existing source-role authority still applies; the response cannot self-certify a user or external fact.

## Failure semantics

Shadow failure occurs after the canonical single-pass turn has already completed. Therefore:

```text
canonical response          remains valid
User Event                  remains preserved
Assistant Event             remains preserved
canonical State             remains exactly canonical single-pass result
accepted Continuity         remains exactly canonical single-pass result
shadow raw proposal output  absent on failure
```

A shadow failure cannot turn a successful canonical turn into a failed turn. Invalid or incomplete plain Pass 2 proposal IR is one bounded cause of shadow failure; provider-native structured-output failure is not required for this extraction path.

## Same-model boundary

`run_user_turn_shadow_two_pass(...)` and its streaming counterpart use one supplied provider object that supports both the canonical single-pass generation and extraction generation.

The OpenAI-compatible COGP provider extension inherits the canonical adapter and therefore can run:

```text
same adapter object / client / request model
  plain canonical relaylm_cognitive_output content
    -> RelayLM combined-IR parse/type construction
    -> plain shadow extraction message
    -> RelayLM relaylm_structured_cognition_output:v1 parse/type construction
```

The two contract identities do not imply provider-native response schemas. This is an execution-topology capability, not a claim that multiple concurrent provider requests are resident as separate model artifacts.

## Relationship to #1386

COGP intentionally does not replace `ActualModelRunManifest` or the existing actual-model evidence artifact system.

#1386 remains the owner that combines, at minimum:

```text
COGP execution evidence identity
+ exact RelayLM commit
+ provider / deployment identity
+ exact model artifact / tokenizer
+ effective context capacity
+ applied decoding configuration
+ reasoning/thinking identity when causally compared
+ scenario / fixture / replicate identity
```

before an A/B/C result is citable.

Both current model-facing structure prompts differ materially from their historical provider-native schema-carriage realizations. Prior exact single-pass and Pass-2 serialized-input footprints remain historical for those exact old wires. #1386 must reacquire current fixed prompt/wire footprint evidence before revised topology screening cites capacity assumptions.

In particular, COGP topology identity alone is insufficient to claim that reasoning was actually OFF or ON. Provider/reasoning capability evidence must establish the exact applied control before causal comparison.

## Ownership boundaries

COGP / #1533 owns:

- resolved execution-topology identity;
- RelayLM pass/output contract identity;
- canonical-mutation-source identity;
- the RelayLM-owned combined cognitive IR identity for `single_pass`;
- the RelayLM-owned proposal-IR identity for canonical/shadow extraction;
- non-authoritative shadow runtime semantics;
- raw shadow extraction observation and bounded failure status.

#1386 owns:

- actual-model manifest/artifact schema;
- provider/model/runtime/fixture/replicate evidence identity;
- controlled A/B/C methodology;
- review/cohort/comparison artifacts;
- latency/token/resource observations used as product evidence.

Provider owners retain capability truth and exact applied external request configuration. Provider-native structured-output support is not the owner of either RelayLM cognition IR. #1388 retains profile/default selection. #1446 retains operator config carriage.

## Non-goals

This contract does not:

- select a release default;
- change single-pass semantic meaning or deterministic commit ownership;
- validate or commit shadow proposals;
- replace #1386 manifests or scenario evidence;
- claim reasoning-on/off causality;
- choose numeric decoding or reasoning settings;
- create a second resident model requirement;
- make backend JSON-schema/grammar support a semantic prerequisite for canonical cognition.
