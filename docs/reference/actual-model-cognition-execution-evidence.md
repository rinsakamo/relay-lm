# Actual-model cognition execution evidence

Status: #1386 COGP5 execution-topology and resolved per-pass request evidence bridge for RelayLM v1.

This reference extends the existing Actual-model Evaluation foundation so ordinary-turn cognition topology and fully resolved per-pass generation requests can participate in reproducible evidence without replacing historical evidence or creating another evaluation architecture.

## Historical evidence remains immutable

Historical `ActualModelRunManifest` serialization remains unchanged when the newer optional fields are absent.

When `cognition_execution` is absent, no cognition-execution key is emitted. When `cognition_pass_requests` is absent, no per-pass request key is emitted. Historical manifests therefore preserve their existing run identity.

Reasoning-attested LM Studio ordinary-turn runs may additionally use the derived `ActualModelReasoningRunManifest`; only those runs emit the existing model-environment `reasoning_environment` identity.

New cognition-policy evidence supplies an explicit COGP `CognitionExecutionEvidenceIdentity`. That topology identity participates in the run hash, so `single_pass`, `two_pass`, and `shadow_two_pass` cannot accidentally share a run identity solely because model/provider/scenario fields are otherwise equal.

The topology execution path must equal the manifest `execution_path`. A buffered/streaming mismatch fails before model execution.

## Resolved per-pass request identity

`ActualModelCognitionPassRequests` records the exact fully resolved `CognitionPassRequest` values supplied to an actual-model run. It is evidence identity, not policy resolution and not provider-wire authority.

The supported shapes in this bounded bridge are:

```text
single_pass:
  single_pass = CognitionPassRequest

two_pass:
  pass1 = CognitionPassRequest
  pass2 = CognitionPassRequest
```

Each recorded request preserves the exact provider-neutral fields:

```text
reasoning_mode
reasoning_budget
temperature
top_p
max_output_tokens
```

The request has already passed the COGP policy-resolution boundary: unresolved `auto` is not legal in `CognitionPassRequest`.

The request identity is optional for backward compatibility. When present it participates in `ActualModelRunManifest.to_mapping()` and therefore in `stable_actual_model_run_id(...)`. Changing Pass 2 from `off` to `bounded(64)`, for example, cannot alias to the same run ID.

Topology and request shape must agree. A single-pass topology cannot carry Pass 1/Pass 2 requests, and a two-pass topology cannot carry a single-pass request. `shadow_two_pass` request evidence is not implemented by this transaction and fails closed.

The current bridge intentionally supports only buffered execution. Streaming request evidence fails closed rather than claiming a request was carried through a Turn streaming path that is not part of the first COGP5 screening transaction.

## Execution-aware scenario harness

`run_actual_model_scenario(...)` resolves execution topology from the manifest and forwards any recorded fully resolved request through the existing ordinary-turn runtime.

### Legacy or explicit `single_pass`

Without `cognition_pass_requests`, the existing ordinary-turn harness remains unchanged.

With explicit request evidence, the buffered path is:

```text
ActualModelRunManifest.cognition_pass_requests.single_pass
  -> run_actual_model_scenario
  -> run_user_turn(..., pass_request=...)
  -> canonical provider
```

The recording wrapper forwards the keyword only when a request is actually present, preserving historical generic providers that implement only the old no-request signature.

### `two_pass`

The harness executes the merged COGP3 response-first runtime and may carry independent resolved requests:

```text
pass1 request
  -> run_user_turn_two_pass
  -> generate_conversation

pass2 request
  -> originating-turn-bound extraction
  -> generate_extraction
```

The per-turn execution observation still records Pass 2 terminal status (`committed`, `stale`, or `failed`), bounded failure reason, and raw valid Pass 2 proposals when produced.

Pass 1 response becomes `raw_model.response`; proposal arrays come from the actual Pass 2 structured output. Deterministic State/Continuity fields remain owned solely by the existing validators.

The harness awaits canonical Pass 2 before advancing the semantic scenario turn so the next turn observes the accepted canonical State/Continuity result.

### `shadow_two_pass`

The merged COGP4 shadow evidence path remains available for topology-only evidence, but this transaction does not attach resolved per-pass request evidence to it. A manifest attempting to combine shadow topology with `cognition_pass_requests` fails closed.

## Raw model versus deterministic authority

The existing #1386 separation is unchanged.

Raw model evidence records what the model proposed. Deterministic evidence records only what RelayLM validators accepted or rejected. A Pass 2 provider failure with no valid structured output records no fabricated proposal output and never reuses a previous turn's extraction.

Per-pass request identity contains no prompt, model response, State, Continuity, Event, or MEMORY content.

## Total Cognitive Budget boundary

The pre-existing #1386 single-pass total Cognitive Budget bridge returns `CognitiveBudgetDiagnostics` from the ordinary Turn runtime.

The current resolved-request bridge does not combine explicit `cognition_pass_requests` with total `CognitiveBudgetRuntimeConfig`. Such a manifest fails closed. Likewise, the topology-aware path does not fabricate equivalent total-budget diagnostics for two-pass/shadow execution.

Legacy explicit MEMORY/Event budgets may still be carried through the already-owned Turn preparation path when used without total Cognitive Budget evidence.

## Restart boundary

Restart evidence has a separate execution bridge. That bridge does not yet forward the new resolved per-pass request identity across its pre/post-restart ordinary-turn executions.

Therefore a restart scenario combined with `cognition_pass_requests` fails during scenario planning before workspace mutation or model generation. The run must not retain the request in its manifest while silently executing without it.

## Provider application remains separate authority

Recording a `CognitionPassRequest` proves only what RelayLM requested at the provider-neutral boundary. It does not by itself prove that a backend applied a wire control or that the control was semantically effective.

Provider owners remain authoritative for exact request serialization and applied configuration. In current v1 authority, the configured-vLLM reasoning path already has deterministic attested realization from #1545/#1558:

```text
RelayLM off
  -> reasoning_effort = none

RelayLM bounded(N)
  -> thinking_token_budget = N
  -> chat_template_kwargs.enable_thinking = true
```

The canonical Turn/provider carriage merged in #1561 can carry those fully resolved requests to that realizer. Unsupported or ambiguous controls fail closed before generation; no low/medium/high effort label is substituted for a numeric bounded budget.

This #1386 transaction composes the same resolved request into run identity and the scenario harness. It does not duplicate provider capability discovery or backend serialization.

## LM Studio environment evidence remains distinct

Existing LM Studio host-runner formats and `ActualModelReasoningEnvironmentIdentity` remain historical/current evidence for the LM Studio model-wide environment where used.

A model-wide LM Studio default is not equivalent to a per-pass RelayLM `bounded(N)` request. The exact LM Studio model previously demonstrated only binary native `off/on` behavior; it must not be treated as providing vLLM-style bounded reasoning merely because both backends serve a related model family.

## Current vLLM COGP5 boundary

The repository now contains these prerequisites:

- frozen canonical vLLM repository-snapshot target identity;
- configured-vLLM reasoning capability attestation;
- provider-owned exact `off` and `bounded(N)` realization;
- ordinary/two-pass Turn carriage for fully resolved requests;
- #1386 execution-topology identity;
- #1386 resolved per-pass request identity and buffered scenario-harness carriage.

What is still missing is the host-side binding that validates the live vLLM server/model against the frozen repository-snapshot target and constructs the matching provider plus applied reasoning capability for an actual evidence run.

Accordingly, this transaction does **not** constitute actual-model product evidence and does not freeze a numeric default.

The intended first screening after that host binding is deliberately small:

```text
A: single_pass
   request = off

B: two_pass
   Pass 1 = off
   Pass 2 = off

C: two_pass
   Pass 1 = off
   Pass 2 = bounded(small explicit budget)
```

Only if C demonstrates a meaningful product/budget difference should a larger bounded budget be added. Unsupported/ineffective parameter permutations are not part of this screening.

LM Studio and vLLM evidence runs remain serial backend executions; simultaneous backend availability is not required.

## Ownership

#1533 / COGP owns execution-topology semantics, provider-neutral per-pass request semantics, capability vocabulary normalization, and request resolution.

#1386 owns:

- manifest/run identity composition;
- raw/deterministic execution evidence;
- scenario execution/review/cohort methodology;
- controlled supported-condition evidence;
- host-side evidence binding;
- exact resolved-request evidence carriage into the actual-model harness.

Provider owners retain actual request capability, backend serialization, and applied configuration truth. #1388 remains the sole owner of evidence-backed profile/default selection.
