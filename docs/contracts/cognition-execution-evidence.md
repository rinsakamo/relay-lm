# Cognition Execution Evidence Contract

Status: COGP4 provider-neutral execution-topology and shadow-observation contract for RelayLM v1.

This contract is owned by #1533 under `cognitive_turn`. It defines what ordinary-turn execution topology occurred and how `shadow_two_pass` raw extraction is carried without becoming semantic authority. It does not replace #1386 Actual-model Evaluation identity, artifacts, reviews, cohorts, or comparison methodology.

## Purpose

Actual-model evidence must be able to distinguish:

```text
single_pass

two_pass
  Pass 1 conversation
  Pass 2 canonical structured extraction

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
single-pass output:
  relaylm_cognitive_output:v1

conversation-only output:
  relaylm_conversation_output:v1

structured extraction output:
  relaylm_structured_cognition_output:v1
```

These are RelayLM execution-contract identities. They are not claims about an exact model artifact, provider deployment, reasoning setting, decoding configuration, tokenizer, or context window.

### `single_pass`

```text
mode                       single_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          omitted
shadow_output              omitted
canonical_mutation_source  single_pass
```

### `two_pass`

```text
mode                       two_pass
canonical_output_contract  omitted
conversation_output        relaylm_conversation_output:v1
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              omitted
canonical_mutation_source  pass2
```

### `shadow_two_pass`

```text
mode                       shadow_two_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              relaylm_structured_cognition_output:v1
canonical_mutation_source  single_pass
```

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

A completed shadow observation preserves the model's raw StateCandidate and ContinuityCandidate proposals. It does **not** contain deterministic acceptance decisions because shadow proposals are deliberately not submitted to State or Continuity validators.

## Non-authoritative invariant

`shadow_two_pass` means:

```text
canonical single-pass CognitiveOutput
  -> existing State / Continuity validation
  -> canonical mutation as normal

same originating CognitiveInput
+ canonical response
  -> shadow extraction
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

A shadow failure cannot turn a successful canonical turn into a failed turn.

## Same-model boundary

`run_user_turn_shadow_two_pass(...)` and its streaming counterpart use one supplied provider object that supports both the canonical single-pass generation and extraction generation.

The OpenAI-compatible COGP3 provider extension inherits the canonical adapter and therefore can run:

```text
same adapter object / client / request model
  canonical relaylm_cognitive_output
    -> shadow relaylm_structured_cognition_output
```

This is an execution-topology capability. It does not claim that multiple concurrent provider requests are resident as separate model artifacts.

## Relationship to #1386

COGP4 intentionally does not modify `ActualModelRunManifest` or the existing actual-model evidence artifact format.

#1386 remains the owner that must later combine, at minimum:

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

In particular, COGP topology identity alone is insufficient to claim that reasoning was actually OFF or ON. #1532/CRY reasoning attestation is design precedent only; CRY-specific LM Studio evidence fields are not copied here.

## Ownership boundaries

COGP / #1533 owns:

- resolved execution-topology identity;
- RelayLM pass/output contract identity;
- canonical-mutation-source identity;
- non-authoritative shadow runtime semantics;
- raw shadow extraction observation and bounded failure status.

#1386 owns:

- actual-model manifest/artifact schema;
- provider/model/runtime/fixture/replicate evidence identity;
- controlled A/B/C methodology;
- review/cohort/comparison artifacts;
- latency/token/resource observations used as product evidence.

Provider owners retain capability truth and exact applied external request configuration. #1388 retains profile/default selection. #1446 retains operator config carriage.

## COGP4 non-goals

COGP4 does not:

- select a release default;
- change canonical `single_pass` behavior;
- validate or commit shadow proposals;
- modify #1386 manifests or scenario evidence;
- claim reasoning-on/off causality;
- choose numeric decoding or reasoning settings;
- create a second resident model requirement.
