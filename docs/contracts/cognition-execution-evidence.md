# Cognition Execution Evidence Contract

Status: current provider-neutral execution-topology and shadow-observation contract for RelayLM 1.0.

Owner: #1533 / `cognitive_turn`.

This contract identifies what execution topology actually ran and which output path was permitted to mutate State/Continuity. #1386 owns actual-model run/review/cohort/comparison methodology and product-quality evidence.

## Core 1.0 evidence role

Core 1.0 is two-pass first.

Execution evidence must distinguish:

```text
two_pass
  Pass 1 conversation
  Pass 2 canonical semantic extraction

single_pass
  combined response/proposal IR
  compatibility / future optimization evidence

shadow_two_pass
  canonical single_pass
  + non-authoritative Pass 2 observation
```

The existence of all three identities does not make them equal Core 1.0 release candidates. Current product role is defined by `docs/contracts/cognition-execution-policy.md`.

## Execution evidence identity

`CognitionExecutionEvidenceIdentity` format version `1` binds:

- resolved cognition mode;
- buffered or streaming delivery path;
- exact RelayLM output-contract identities used by that topology;
- the only path permitted to produce canonical State/Continuity mutation.

Current contract identities are:

```text
single-pass combined output
  relaylm_cognitive_output:v1

conversation-only output
  relaylm_conversation_output:v1

Pass 2 proposal-IR output
  relaylm_structured_cognition_output:v1
```

These are RelayLM contract identities, not provider-native JSON-schema identities.

Neither `relaylm_cognitive_output:v1` nor `relaylm_structured_cognition_output:v1` requires provider-native `response_format`, JSON Schema, grammar or constrained decoding. Provider/model/reasoning/decoding/runtime identity is supplied separately by the owning provider and #1386 evidence surfaces.

### `two_pass`

```text
mode                       two_pass
canonical_output_contract  omitted
conversation_output        relaylm_conversation_output:v1
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              omitted
canonical_mutation_source  pass2
```

Pass 1 is the visible conversation. Pass 2 is ordinary provider message content containing the RelayLM-owned compact proposal IR, parsed and typed by RelayLM before deterministic State/Continuity validation.

For Core 1.0 this is the reference/release topology that #1386 qualifies first.

### `single_pass`

```text
mode                       single_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          omitted
shadow_output              omitted
canonical_mutation_source  single_pass
```

The provider returns ordinary message content containing the RelayLM-owned combined cognitive IR. RelayLM parses exact top-level/candidate shape and constructs `CognitiveOutput` before the deterministic commit boundary.

For Core 1.0 this identity remains available for compatibility and later optimization evidence. Its presence does not make single-pass quality tuning a release prerequisite.

### `shadow_two_pass`

```text
mode                       shadow_two_pass
canonical_output_contract  relaylm_cognitive_output:v1
conversation_output        omitted
extraction_output          relaylm_structured_cognition_output:v1
shadow_output              relaylm_structured_cognition_output:v1
canonical_mutation_source  single_pass
```

The canonical side is single-pass. The shadow extraction uses the same RelayLM-owned proposal-IR contract as canonical two-pass Pass 2, but its proposals are evidence-only and never submitted as a second accepted result.

`auto` is unresolved policy and therefore cannot be recorded as an execution that happened. Evidence records the resolved mode.

## Two-pass reference evidence

For current Core 1.0 qualification, #1386 combines this topology identity with exact evidence for:

```text
RelayLM commit / contract revision
provider / backend / deployment
exact model artifact / tokenizer
Pass 1 resolved request
Pass 2 resolved request
effective context capacity
scenario / fixture / replicate
raw Pass 1 response
raw Pass 2 proposal output
deterministic State / Continuity decisions
product-quality review
timing/resource evidence where captured
```

The first qualification target is the current two-pass baseline. A Pass 2 reasoning escalation is citable only when exact provider/model capability evidence proves the applied control and the controlled comparison holds Pass 1 fixed.

Single-pass comparison is not required before the two-pass reference is qualified.

## Authority ordering in extraction evidence

For canonical and shadow Pass 2:

```text
user / source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The Pass 1/canonical assistant response is interpretive context only. It cannot self-certify a user or external fact or become a provenance source merely because the model said it.

A citable product-quality review may classify assistant-to-user contamination even when the proposal IR is syntactically valid.

## Canonical two-pass failure evidence

A valid Pass 1 response remains valid when Pass 2 later fails, is malformed, or becomes stale.

Evidence must preserve the distinction:

```text
Pass 1 completed + Pass 2 committed
Pass 1 completed + Pass 2 failed
Pass 1 completed + Pass 2 stale
```

A failed/stale Pass 2 causes no State/Continuity mutation from that extraction.

## Shadow observation

`ShadowExtractionEvidence` binds one evidence-only Pass 2 attempt to:

- `shadow_two_pass` execution identity;
- originating User Event ID;
- terminal status `completed` or `failed`;
- raw typed `CognitionExtractionOutput` only when completed;
- bounded content-free failure reason only when failed.

The initial failure reason remains:

```text
shadow_pass2_failed
```

Raw exception text is not part of the stable evidence contract.

Shadow extraction never advances Continuity lifecycle or mutates State/Continuity.

## Same-model boundary

Canonical two-pass and shadow evidence may reuse the same supplied provider/model object sequentially. Execution identity does not imply two concurrently resident online model artifacts.

Provider-native structured-output capability is not part of the topology requirement for the current RelayLM cognition IR paths.

## Performance evidence

Timing/resource observations are separate evidence axes. They do not change canonical mutation authority and must not be collapsed into a weighted score that can override grounding or deterministic correctness.

For two-pass evidence, preserve distinctions between:

- first-visible latency when actually observed;
- Pass 1 response-complete time;
- Pass 2 provider/extraction time;
- total scenario/turn-settle time.

A later single-pass optimization comparison must use the qualified two-pass reference and record both quality regression and performance/resource benefit.

## Historical evidence

Existing immutable artifacts remain valid for the exact code/wire/question they measured. Historical A/B/C naming or old topology-first plans do not define current Core 1.0 execution order.

Do not restate old ordering as current authority merely because an artifact remains loadable.

Prior serialized-input footprints are historical whenever prompt/IR/provider framing/tokenizer/runtime changes alter exact tokenization or execution identity.

## Ownership

#1533 owns:

- resolved topology identity;
- RelayLM pass/output contract identities;
- canonical mutation-source identity;
- shadow non-authoritative semantics.

#1386 owns:

- actual-model manifest/run/review/cohort/comparison schemas;
- provider/model/runtime/fixture/replicate evidence identity;
- two-pass reference qualification methodology;
- Pass 2 escalation comparisons when justified;
- later optional single-pass optimization comparisons;
- quality/timing/token/resource observations.

#1388 owns calibrated Core 1.0 profile/default selection. #1446 owns release-config/operator carriage. Provider owners retain capability truth and exact applied external request configuration.

## Non-goals

This contract does not:

- choose numeric defaults;
- choose a topology winner for Core 1.0;
- make single-pass quality tuning a release prerequisite;
- validate/commit shadow proposals;
- replace #1386 evidence artifacts;
- infer reasoning state from topology identity;
- require provider-native structured output;
- require a second concurrently resident online model.

## Principle

> Evidence identity says what ran. Current release policy says which path must be qualified first.
