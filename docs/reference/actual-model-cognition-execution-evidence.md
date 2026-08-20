# Actual-model cognition execution evidence

Status: #1386 COGP5 execution-topology evidence bridge for RelayLM v1.

This reference extends the existing Actual-model Evaluation foundation so ordinary-turn cognition topology can participate in reproducible evidence without replacing historical evidence or creating another evaluation architecture.

## Historical evidence remains immutable

`ActualModelRunManifest.cognition_execution` is optional.

When it is absent, the manifest serializes exactly the historical #1386 shape: no `cognition_execution` key is added. Because `stable_actual_model_run_id(...)` hashes that mapping plus the unchanged scenario definition, historical manifests preserve their existing run identity.

New cognition-policy evidence supplies an explicit COGP `CognitionExecutionEvidenceIdentity`. That identity then participates in the run hash, so a `single_pass`, `two_pass`, or `shadow_two_pass` execution cannot accidentally share a run identity solely because model/provider/scenario fields are otherwise equal.

The COGP execution identity delivery path must equal the manifest `execution_path`. A buffered/streaming mismatch fails before model execution.

## Execution-aware scenario harness

`run_actual_model_scenario(...)` resolves execution topology from the manifest.

### Legacy or explicit `single_pass`

The existing ordinary-turn harness remains unchanged:

```text
CognitiveOutput
  response
  StateCandidate[]
  ContinuityCandidate[]
        |
        +--> raw_model evidence
        |
        +--> existing deterministic Turn decisions/result
```

An explicit single-pass COGP identity changes run identity because it is a new controlled execution condition. A historical manifest without the field remains historical authority.

### `two_pass`

The harness executes the merged COGP3 response-first runtime:

```text
Pass 1 response
        |
        +--> raw_model.response

Pass 2 raw proposals
        |
        +--> raw_model State/Continuity proposals
        +--> cognition_execution.pass2_raw
        |
        +--> existing deterministic State/Continuity result
```

The per-turn execution observation records:

- `mode = two_pass`;
- Pass 2 terminal status: `committed`, `stale`, or `failed`;
- bounded Pass 2 failure reason when failed;
- raw valid Pass 2 proposal output when one was actually produced.

The recorder is turn-scoped: a later Pass 2 failure cannot reuse an earlier turn's recorded extraction as though it belonged to the failed turn.

The harness awaits canonical Pass 2 before advancing the semantic scenario turn. This preserves the actual canonical State/Continuity result as the next turn's accepted input rather than evaluating later turns against intentionally stale canonical authority.

### `shadow_two_pass`

The harness executes the merged COGP4 shadow path:

```text
canonical single_pass
  -> raw_model + deterministic result

shadow extraction
  -> cognition_execution.shadow_raw only
  -> no canonical mutation
```

A conflicting shadow proposal remains visible as model behavior without changing the canonical `raw_model` or deterministic result.

Shadow failure is separately observable and cannot convert the successful canonical turn into a failed turn.

## Raw model versus deterministic authority

The existing #1386 separation is preserved.

For canonical `two_pass`, `raw_model.response` comes from Pass 1 while `raw_model` proposal arrays come from the actual Pass 2 structured output. Deterministic State/Continuity fields come only from the existing validators and their resulting authority.

For `shadow_two_pass`, canonical `raw_model` remains the single-pass output. Shadow proposals are stored only under the execution observation and are never represented as deterministic acceptance decisions.

A Pass 2 provider failure with no valid structured output records empty raw proposal arrays for that turn and no `pass2_raw`. It never reuses a previous turn's raw extraction.

## Total Cognitive Budget boundary

The pre-existing #1386 single-pass total Cognitive Budget bridge returns `CognitiveBudgetDiagnostics` from the ordinary Turn runtime.

The current topology-aware path does not fabricate equivalent diagnostics for the new two-pass/shadow paths. Therefore an evidence run that combines a non-single execution topology with an explicit `CognitiveBudgetRuntimeConfig` fails explicitly until a bounded follow-up bridge exists.

This keeps missing measurements distinct from zero/normal measurements and avoids claiming that a two-generation execution satisfied the current one-generation total-budget evidence contract.

Legacy explicit MEMORY/Event budgets may still be carried through the already-owned COGP Turn preparation path when used without total Cognitive Budget evidence.

## Reasoning / Thinking capability boundary

Topology observability does **not** make a requested reasoning configuration executable or citable by itself.

The provider-owned contract now explicitly records that the current canonical OpenAI-compatible Chat Completions adapter carries `temperature`, `top_p`, and `seed`, but does not carry or attest a per-request reasoning/thinking mode, reasoning effort, or bounded reasoning budget.

Accordingly, current COGP5 evidence must not:

- invent `reasoning_effort`;
- assume a provider field exists because another OpenAI-compatible endpoint supports it;
- treat a model-wide LM Studio default as a distinct Pass 2 override when no such override is applied;
- infer Thinking OFF/ON from output style;
- claim bounded reasoning when the provider cannot attest a bounded control.

For the current canonical provider capability class:

```text
per-request reasoning modes      = unsupported
bounded reasoning budget         = unsupported
per-pass reasoning override      = unavailable
```

A model-wide or host-wide LM Studio reasoning default may be separately observed and attested as execution-environment identity. Such an attestation may make A/B reproducible under the same effective environment, but it does not become a Pass-2-only request control.

Therefore the supported comparison boundary is:

```text
A = explicit single_pass
B = explicit two_pass under the same actually attested provider/model reasoning environment as A
C = unsupported for the current canonical provider: bounded Pass 2 reasoning is not executed
```

If the environment itself truthfully attests reasoning OFF, B may be described as running under an OFF environment, but that must not be represented as though RelayLM applied a distinct Pass 2 override.

The CRY reasoning identity work demonstrates the reproducibility principle but remains CRY-specific authority. Ordinary-turn evidence must consume an ordinary-turn host/evidence binding rather than copy CRY fields blindly.

## Canonical LM Studio host topology binding

The canonical #1386 LM Studio host runner has a strict topology-aware condition format dedicated to cognition execution evidence.

`format_version: 4` adds exactly one execution-policy declaration:

```json
{
  "cognition_execution": {
    "mode": "single_pass | two_pass | shadow_two_pass"
  }
}
```

The host runner resolves that mode through the already-owned `CognitionExecutionEvidenceIdentity` constructors using the same explicit buffered/streaming `execution_path`. `auto` is unresolved policy and is rejected as evidence identity.

For explicit `single_pass`, host preparation retains the canonical `OpenAICompatibleProvider`. For `two_pass` and `shadow_two_pass`, it selects the already-implemented `OpenAICompatibleTwoPassProvider`, which uses the same OpenAI-compatible Chat Completions transport and the same provider-owned decoding configuration while exposing the conversation/extraction methods required by the COGP runtime.

The resolved execution identity is placed directly in `ActualModelRunManifest.cognition_execution`. Host metadata therefore cannot claim a two-pass condition while executing the legacy single-pass provider path.

Format v4 retains the existing explicit MEMORY/Event budget shape and deliberately cannot carry the format-v3 total Cognitive Budget identity. That separation preserves the existing fail-closed rule for non-single topology plus total-budget evidence.

This host binding closes topology carriage only. It does not itself attest the current LM Studio model-wide reasoning default and does not create a synthetic run for unsupported bounded Pass 2 reasoning. Those are separate evidence responsibilities.

## Current COGP5 boundary

The provider-neutral topology bridge and the canonical LM Studio host topology carriage are implemented.

Actual target-model A/B evidence still requires a fresh ordinary-turn host reasoning-environment attestation so both runs can cite the same effective model/provider reasoning state. Condition C remains unsupported for the current canonical provider capability class and must be represented as unsupported/not executed rather than as a fabricated generation.

Therefore this stage does **not** change #1388 calibration/default authority.

## Ownership

#1533 / COGP owns the meaning of execution topology and its provider-neutral topology identity.

#1386 owns:

- manifest/run identity composition;
- raw/deterministic execution evidence;
- scenario execution/review/cohort methodology;
- controlled supported-condition evidence;
- host-side evidence binding and unsupported-condition evidence.

Provider owners retain actual request capability and applied configuration truth. #1388 remains the sole owner of profile/default selection.
