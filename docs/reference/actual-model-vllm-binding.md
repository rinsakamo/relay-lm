# Actual-model vLLM execution binding

Status: current #1386 binding between the frozen vLLM target, fresh live vLLM/model capability authority, the canonical OpenAI-compatible provider, and citable actual-model evidence.

This reference does not choose cognition semantics or runtime defaults. #1533 defines the two-pass-first Core 1.0 policy; #1386 defines current screening order; #1388 interprets evidence into calibrated values.

## Canonical target

The current frozen vLLM execution target is:

- target: `gemma-4-12b-it-qat-w4a16-google-vllm-v1`;
- repository artifact: `google/gemma-4-12b-it-qat-w4a16-ct@9c79b5e652ae36f02bb07d3ca29124a9d1b009bd`;
- target format: repository snapshot with exact required file sizes/SHA-256 values;
- serving tokenizer and chat-template roles participate in frozen target identity.

Before a run is citable, `verify_actual_model_repository_snapshot(...)` must verify the exact local snapshot.

A mutable model alias, family name or quantization label alone is insufficient evidence identity.

## Runtime / capability authority

The binding consumes `VLLMReasoningCapabilityAttestation`; it does not infer capability from model names, HTTP acceptance or common OpenAI-compatible field names.

The attestation binds applicable facts including:

- vLLM backend/version;
- request and served model identity;
- live `model_root` and `max_model_len` when reported;
- frozen target/repository revision;
- reasoning parser / chat-template thinking controls;
- separately classified OFF and bounded controls;
- protocol acceptance, semantic effect, repeatability and ambiguity facts.

Only controls proven effective for the exact backend/model may be used in causal product-quality evidence.

`low` / `medium` / `high` labels are not substitutes for numeric bounded reasoning unless current provider authority explicitly defines that equivalence.

## Fail-before-generation binding

`bind_vllm_execution_condition(...)` rejects generation when required identity does not agree, including as applicable:

1. frozen target/repository verification;
2. reasoning-capability target/model identity;
3. live `model_root` versus verified snapshot root;
4. live/configured/manifest context capacity;
5. provider-attestation identity;
6. provider request model;
7. manifest provider/adapter/model/tokenizer/decoding/capability/seed identity;
8. explicit cognition pass-request identity;
9. the supported execution path for the selected evidence contract.

Requested reasoning is never promoted to applied capability merely because it was requested.

## Execution reuse

`run_vllm_actual_model_scenario_definition(...)` delegates to the existing #1386 actual-model scenario path after binding succeeds. It does not create a separate evaluation architecture.

```text
#1386 scenario + resolved pass request identity
  -> existing actual-model scenario harness
  -> current single/two-pass Turn path
  -> canonical OpenAI-compatible provider
  -> provider-owned vLLM realization
  -> exact vLLM request
```

A completed condition-bound result can be written as immutable execution evidence. Persistence recomputes the content-derived vLLM `binding_id`, preserves the backend-specific nested and outer execution-ID checks, requires the nested scenario execution to pass the same generic citable admission used by `write_actual_model_execution_result(...)`, and requires the vLLM binding manifest to equal the nested execution plan manifest. The generic admission covers the content-derived plan ID, canonical ordinary/restart run ID, plan/evidence binding, and generic execution ID. Same-ID/different-evidence replacement is rejected; a genuine rerun uses a distinct replicate identity.

## Current Core 1.0 screening order

The current canonical plan is `evaluation/actual_model/screenings/stage-r0-vllm-reference-v2.json`. Format v2 uses semantic condition keys directly:

```text
reference_baseline
  two-pass reference
  Pass 1 = reasoning off
  Pass 2 = reasoning off
  execute first where exact OFF is semantically attested

pass2_reasoning_escalation
  Pass 1 = exactly the same as reference_baseline
  Pass 2 = the already-attested bounded condition
  execute only when #1386 review finds Pass 1 sufficient
  but Pass 2 semantic quality insufficient
```

The frozen historical plan `evaluation/actual_model/screenings/cogp5-vllm-screening-v1.json` retains A/B/C coordinates for immutable compatibility evidence. Those names do not define current plan structure or execution order. The current `reference_baseline` preserves the immutable underlying condition ID `stage-r0-vllm-b-two-pass-off-off`; `pass2_reasoning_escalation` preserves `stage-r0-vllm-c-two-pass-off-bounded16`.

The host can retain technical ability to replay historical evidence. That does not authorize a historical single-pass A condition before the two-pass reference is qualified.

All backend/model evidence runs remain serial. There is no `all` condition and no Cartesian parameter sweep.

## Reasoning escalation boundary

The currently frozen vLLM reasoning proof includes an OFF realization and a bounded realization. Those values are capability/evidence conditions, not release defaults.

Current screening rules are:

- start with `reference_baseline`, the lowest effective exact condition;
- do not add reasoning if its Pass 2 semantic quality is already sufficient;
- if escalation is justified, hold Pass 1 and unrelated Pass 2 decoding controls fixed;
- do not add unsupported or ineffective effort permutations merely for completeness;
- a larger bounded budget requires a new evidence question demonstrating why it is needed.

#1388 alone decides whether any observed condition becomes part of a release profile.

## Capacity-evidence gate

Historical plans may load without a current capacity artifact for historical inspection, but canonical screening preparation requires valid capacity evidence when the host contract requires it.

`VLLMRuntimeCapacityEvidence` is immutable content-free evidence containing applicable identity such as:

- measurement commit provenance;
- exact frozen target/revision;
- serving tokenizer/chat-template identity;
- vLLM backend/request-model identity;
- observed live `max_model_len`;
- exact scenario-set revision;
- serialized-input counter identity;
- footprint observations keyed by condition/topology/pass/scenario/turn;
- exact resolved pass-request identity `amcpr-<sha256>`;
- total serialized-input/framing counts and count mode;
- independently proved overflow evidence when available.

Current capacity acquisition may additionally carry two optional content-free observations on each reached footprint. `selected_layer_occupancy` records the already-built `CognitiveInput` projection as canonical-State item count, working-context item/character occupancy, retrieved-memory item/character occupancy and event-evidence item/character occupancy. Working-context classification follows the owner projection's user/assistant actor markers; the measurement proxy does not rerun any selector or serialize content. `completion_observation` carries only the provider-supplied `CognitionCompletionMetadata` fields (`finish_reason`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `reasoning_tokens`) for that exact pass. Provider failure leaves the observation null, and missing provider usage stays missing. Historical artifacts without these optional fields remain loadable and retain their original content-addressed identity.

It contains no prompt/message/State/Continuity/MEMORY content, API keys or model output.

The artifact ID is content-addressed and recomputed on load. Conflicting replacement is rejected.

### Reviewed canonical tracked reuse

For the current format-v2 Stage R plan, the repository-tracked `capacity_evidence_id` is itself a reviewed canonical citation. Its measurement `relaylm_commit` remains immutable provenance and does not have to equal a later clean screening checkout merely because the plan key or unrelated repository surfaces moved forward.

That exception is narrow. It applies only when screening consumes the capacity artifact from the repository canonical capacity root selected by the current semantic plan. The checkout itself must still equal the requested current RelayLM commit and be completely clean. Before generation, the host still requires the cited artifact to agree with the current execution on the capacity ID/window, explicit model runner, frozen target/revision/tokenizer/chat template, live backend/request model/`max_model_len`, live serving-tokenizer counter identity, scenario-set revision, and exact selected-condition coverage including pass-request IDs.

The current tracked reference artifact remains reusable because those compatibility identities and its immutable underlying `condition_id` still match `reference_baseline`. Measurement commit is provenance; it is not by itself a semantic compatibility substitute or veto for this reviewed citation.

### External capacity evidence

Caller-supplied `--capacity-evidence-id` / `--capacity-evidence-root` is not a repository-reviewed citation. External evidence therefore remains bound to the exact clean screening checkout by its measurement `relaylm_commit`. A stale external artifact fails before provider preparation even if some other identity fields happen to match.

Fresh external capacity evidence does not need to be committed back into the repository before it can be consumed. Committing an artifact that embeds its own measurement commit would move repository HEAD and create a self-referential authority problem. Acquire it into an external immutable evidence root on the exact clean checkout, keep that checkout unchanged, then cite it in a matching screening invocation:

```text
python -m relaylm.actual_model_host --backend vllm --operation capacity --condition reference_baseline ... --artifact-root "$EVIDENCE_ROOT"
python -m relaylm.actual_model_host --backend vllm --operation screening --condition reference_baseline ... --capacity-evidence-id "$CAPACITY_EVIDENCE_ID" --capacity-evidence-root "$EVIDENCE_ROOT"
```

`--capacity-evidence-id` and `--capacity-evidence-root` are screening-only and must be supplied together. The override replaces only the capacity citation in the in-memory screening plan; it does not rewrite the committed Stage R plan or change target, condition, scenarios, context window, decoding, reasoning or runtime authority.

## Selected-condition coverage

Canonical preparation validates the **selected current condition** against exact capacity coverage.

For Core 1.0 reference qualification:

- `reference_baseline` requires complete exact Pass 1 / Pass 2 coverage for the selected scenarios/turns and its immutable underlying condition ID;
- `pass2_reasoning_escalation` requires its own complete Pass 1 / Pass 2 coverage, including the exact escalated Pass 2 request identity, only after escalation is justified;
- historical single-pass A coverage may remain in old evidence but is not required for current reference qualification.

Missing, stale, duplicate or mismatched selected-condition coverage fails before provider construction/generation.

Do not infer current execution order from the set of coordinates stored in an older capacity artifact.

## Capacity-window validation

A caller-selected candidate window must be strictly greater than the largest required serialized-input footprint for the selected current condition and must not exceed the attested live capacity.

Passing this check proves only that the selected input footprint fits. It does not prove comfortable output headroom and does not select a release context window, output reserve or profile.

#1388 owns that interpretation.

Do not transplant numeric bounds across materially different prompt wires, topologies, tokenizers, model artifacts or runtime renderers without exact evidence.

## Exact serving-tokenizer counting

`VLLMServingTokenizerCounter` plugs into the existing production serializer rather than rebuilding prompts.

```text
current production pass request
  -> canonical OpenAI-compatible request builder
  -> transport-only fields removed where appropriate
  -> live vLLM /tokenize renderer + frozen serving tokenizer
  -> SerializedInputTokenCount
```

The counter preserves current chat-template controls that affect rendered input and rejects ambiguous/conflicting reasoning-template states rather than guessing.

Generation-only controls that do not affect rendered prompt text are not misrepresented as tokenizer input.

Counter identity records content-free target/tokenizer/template/backend/model/renderer facts without base URL, API key or semantic payload.

A token count does not itself choose usable runtime capacity.

## Fresh live re-attestation

A frozen reasoning proof is not enough by itself for a new actual-model execution. Before each citable run, current backend/model identity is reacquired and matched to the frozen target/proof according to current provider authority.

Version, served-model, snapshot, `model_root`, `max_model_len` or other required identity drift fails before generation.

This is fresh identity re-attestation, not permission to repeat an unconstrained reasoning-parameter search.

## Host orchestration

`src/relaylm/actual_model_vllm_host.py` owns vLLM host preparation/execution binding.

It validates the capacity citation and checkout admission described above, verifies the exact repository snapshot, reacquires live backend/model identity, reconstructs the serving-tokenizer counter identity, validates exact selected-condition coverage, constructs the canonical provider and pass requests, creates the run manifest, and obtains the binding before scenario generation.

The common facade remains:

```text
python -m relaylm.actual_model_host --backend vllm ...
```

One invocation executes exactly one explicitly selected semantic role over the frozen scenarios. Current Core 1.0 authority selects `reference_baseline` first and `pass2_reasoning_escalation` only when justified. Historical single-pass A is not automatically executed.

Generated summaries/evidence must not expose API-key material.

### Preflight/startup and semantic freeze

The launch boundary is implemented by `relaylm.actual_model_vllm_launch_preflight`.
It is an infrastructure gate before any semantic request:

```text
PREFLIGHT
  -> AUTHORITY_READY
  -> ADMISSION
  -> STARTUP_READY
  -> EXECUTION_FROZEN
  -> SEMANTIC_EXECUTION
```

Before `EXECUTION_FROZEN`, the host may make only bounded mechanical corrections
that preserve the declared condition. `negotiate_vllm_launch(...)` derives supported
flags from the live vLLM help surface and omits only an explicitly classified,
non-semantic legacy observability flag; an unsupported model, tokenizer, template,
context, decoding, reasoning or structured-output flag fails closed. The final argv
and omitted flag list are evidence.

vLLM RPC/IPC and temporary paths are created under a fresh native Linux run path.
Drvfs paths such as `/mnt/c/...` are never used for vLLM process IPC; evidence may
remain in a separately selected evidence root. GPU admission consumes fresh free/total
memory and a fresh capacity recheck for the unchanged declared context. A lower GPU
reservation is allowed only when that same condition is re-attested; reducing context,
truncating input, changing model/quantization or changing output semantics is not a
preflight correction.

Authority acquisition accepts only a successful live source consensus. Transport
unavailability or contradictory live sources cannot promote a remembered ref, Issue,
manifest or handoff. The freeze identity records the exact candidate and all
model/runtime/decoding/capacity/hardware/authority inputs. Once frozen, corrections
are rejected and semantic requests can only proceed through the frozen identity.

This module does not own model generation and does not retry or reinterpret semantic
failures. It is the explicit boundary between recoverable startup work and immutable
execution.

## Performance / timing relationship

Provider-call timing and scenario/turn-settle timing may be bound to the same execution as separate evidence axes.

For two-pass reference evidence, distinguish Pass 1 response time from Pass 2 extraction time and total settle time. Timing cannot override semantic grounding or deterministic-authority requirements.

The shared vLLM screening summary projects `failed_provider_call_count` for each completed scenario result from that result's citable timing sidecar. A deterministic-boundary `pass` therefore does not erase an absorbed provider-call failure such as a failed Pass 2 extraction. The count is an operational observation only: zero failed calls is not a product-quality qualification, and a nonzero count does not retroactively invalidate an already-valid Pass 1 response.

If the qualified two-pass path is slow, use this evidence to inform execution-engine tuning before treating single-pass as an optimization candidate.

## Historical evidence handling

Historical A/B/C artifacts, prior capacity artifacts and old numeric probes remain available through Git/evidence history. Current authority should not restate their old planning order.

A historical artifact is citable only for the exact code/wire/capacity/question it measured, except where a current reviewed canonical citation explicitly reuses a compatible immutable artifact under the admission rules above.

## Deliberate boundary

This binding does not:

- select a release mode/default/profile;
- authorize historical single-pass A before two-pass reference qualification;
- add unverified reasoning conditions;
- infer capability from response text;
- redefine State/Continuity semantics;
- require LM Studio and vLLM simultaneously;
- turn capacity/timing observations into a weighted model score.

## Principle

> Bind exact live execution truth, then follow the current two-pass screening authority rather than the historical condition ordering.
