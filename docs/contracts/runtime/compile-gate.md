---
relaylm_doc_type: contract
relaylm_authority: current_runtime_profile_compile_apply_and_diagnostics_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - current ProfileCompilePlan or CompileApplyDecision fields change
  - profile compile apply eligibility or mode behavior changes
  - mvp-ctx-apply-0 diagnostics fields or state derivation changes
  - current managed-pipeline compiler ordering or payload handoff changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - target v1 compile-plan/result/decision schemas
  - complete route-authority, fallback, shadow, or blocked taxonomy
  - RelayREL, RelaySCN, RelayEMO, RelayINT, RelayMEM, RelayCTX, or token-budget semantics
  - checkpoint, recovery, scheduler, backend transport, or response finalization
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/compile-and-checkpoint.md
  - ../runtime_compile_artifact_contract.md
  - ../runtime_compile_current_target.md
  - ../../architecture/managed_route_fallback_contract.md
  - ../../architecture/runtime/request-response-pipeline.md
relaylm_verified_by:
  - ../../../scripts/relaylm_compile_decision_dry_run_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime compiler and managed-request maintainers
  - diagnostics, trace, and RelayRUN maintainers
  - context, fallback, authority, and security reviewers
relaylm_authority_level: exact_contract
---
# Runtime Compile Gate Contract

## Authority summary

This contract owns the exact current request-local profile compile planning, apply decision, initial compiled-payload handoff, and `mvp-ctx-apply-0` compile-decision diagnostics used by the managed chat request path.

It deliberately describes the **current** implementation rather than the target Runtime Compile Gate taxonomy.

The current boundary is:

```text
validated route + incoming payload
  -> ProfileCompilePlan
  -> CompileApplyDecision
  -> either unchanged current payload or profile-compiled payload
  -> initial PipelineContext.forwarded_payload
  -> later managed pipeline stages may further mutate forwarded_payload
```

The compile-decision diagnostics artifact is built later from the already-computed plan/decision. It is observability-only and does not itself mutate `PipelineContext` or the backend-bound payload.

## Current versus target

Current implementation has two distinct compile surfaces:

1. the typed `CompileApplyDecision` that controls whether the current profile compiler result is applied;
2. the content-free `mvp-ctx-apply-0` diagnostics artifact that mirrors that decision for request diagnostics and trace.

Current live decision-state construction uses only:

```text
COMPILE_APPLY
COMPILE_DRY_RUN
```

Target concepts such as:

```text
PASS_THROUGH
COMPILE_SHADOW_ONLY
COMPILE_FALLBACK
BLOCKED
```

are not complete current decision states merely because older/target contracts describe them.

In particular, current `pass_through` mode does **not** produce a `PASS_THROUGH` value in `mvp-ctx-apply-0`; it produces a non-applying current compile decision and therefore a `COMPILE_DRY_RUN` diagnostics state.

## Current implementation anchors

The exact current compile-gate behavior is implemented across:

```text
relaylm/profile_plan.py
relaylm/compile_gate.py
relaylm/request_compiler.py
relaylm/managed_chat_pipeline_runtime.py
relaylm/managed_chat_runtime.py
relaylm/diagnostics.py
```

The focused diagnostics smoke is:

```text
scripts/relaylm_compile_decision_dry_run_smoke.py
```

The older contracts:

```text
docs/contracts/runtime_compile_artifact_contract.md
docs/contracts/runtime_compile_current_target.md
```

remain transitional sources for target/current migration context. This transaction does not retire them.

## ProfileCompilePlan

`ProfileCompilePlan` is an immutable current planning object with exactly these fields:

```text
enabled
route_model
character_id
compiled_block_count
compiled_message_count
incoming_message_count
incoming_system_message_count
fallback_reason
```

Current defaults are:

```text
compiled_block_count = 0
compiled_message_count = 0
incoming_message_count = 0
incoming_system_message_count = 0
fallback_reason = null
```

The plan is a dry-run planning result. Constructing it does not mutate the incoming payload.

## Incoming message extraction

`compile_chat_payload_if_enabled` derives the planning input from `payload["messages"]` through the current helper:

- if `messages` is not a list, the extracted list is empty;
- if it is a list, only elements that are dictionaries are retained;
- non-dictionary list elements are ignored by this extraction helper.

This extraction defines the current profile-plan/compiler input surface. It is not a general OpenAI message-validation contract.

## Profile plan construction

`build_profile_compile_plan(...)` currently attempts to:

```text
resolve_profile_files(config, route)
  -> build_profile_blocks(profile_files)
  -> compile_profile_messages_with_system_fallback(blocks, incoming_messages)
```

If either `FileNotFoundError` or `ProfileConfigurationError` is raised by that planning sequence, it returns a disabled plan rather than raising that exception through the compile-plan boundary.

The disabled plan contains:

```text
enabled = false
route_model = route.route_model
character_id = route.character_id
incoming_message_count = len(incoming_messages)
incoming_system_message_count = count(role == "system")
fallback_reason = exception class name
```

Its compile block/message counts remain their zero defaults.

On successful planning, the plan contains:

```text
enabled = true
route_model = route.route_model
character_id = route.character_id
compiled_block_count = len(profile blocks)
compiled_message_count = len(dry-run compiled messages)
incoming_message_count = len(incoming_messages)
incoming_system_message_count = count(role == "system")
fallback_reason = null
```

## Plan logging projection

`ProfileCompilePlan.to_log_dict()` currently uses the dataclass field mapping directly.

The plan carries counts, route model, character ID, enabled state, and a bounded fallback class name. It does not carry rendered prompt/message bodies.

The plan's `compiled_message_count` is a dry-run planning count. It is not proof that those messages were ultimately forwarded to the backend.

## CompileApplyDecision shape

`CompileApplyDecision` is an immutable current object with exactly:

```text
should_apply
mode_applied
profile_compile_ready
reason
```

Its `to_log_dict()` returns the dataclass field mapping.

The object answers one narrow question:

```text
may the current profile-compiler result be applied at this profile compile boundary?
```

It is not the complete target Runtime Compile Gate object and is not the final backend-forward authority after later managed-pipeline stages.

## Exact current apply truth table

`decide_compile_apply(mode_applied, plan)` applies this current order:

### 1. Plan not enabled

```text
should_apply = false
mode_applied = supplied mode
profile_compile_ready = false
reason = plan.fallback_reason or "profile_compile_not_ready"
```

This branch wins before mode-specific handling.

### 2. Enabled plan + `pass_through`

```text
should_apply = false
mode_applied = pass_through
profile_compile_ready = true
reason = pass_through_diagnostics_only
```

The profile compiler is therefore diagnostics-only for this mode.

This rule does not redefine the repository's broader route-authority semantics. It states only that this current profile compile boundary does not apply its compiled payload in `pass_through` mode.

### 3. Enabled plan + `memory_light`

```text
should_apply = true
mode_applied = memory_light
profile_compile_ready = true
reason = memory_light_compile_enabled
```

`memory_light` is the current apply-eligible mode at this specific profile compiler gate when the plan is enabled.

### 4. Enabled plan + any other mode value

```text
should_apply = false
mode_applied = supplied mode
profile_compile_ready = true
reason = compile_apply_not_enabled_for_mode
```

This includes `None` or other current/future mode strings not matched by the two explicit branches above.

## No implicit target-state inference

The current truth table must not be expanded by reading target names into it.

Examples:

```text
mode_applied = pass_through
  != current diagnostics decision_state PASS_THROUGH

should_apply = false
  != current COMPILE_FALLBACK
  != current BLOCKED
  != current shadow apply
```

A non-applying current decision means only that this profile compile result is not applied by `compile_chat_payload_if_enabled`.

## compile_chat_payload_if_enabled entry behavior

`compile_chat_payload_if_enabled(config, route, payload)` begins each call by clearing the request-local compiled-context-block `ContextVar`.

It then:

1. extracts current dictionary messages from the payload;
2. builds the current `ProfileCompilePlan`;
3. computes `CompileApplyDecision` from `route.mode_applied` and the plan;
4. creates a shallow `dict(payload)` copy as the current payload object.

The subsequent behavior depends on `decision.should_apply`.

## Non-applying compile path

When `decision.should_apply` is false, the function returns a `CompiledRequest` with:

```text
payload = shallow dict copy of the incoming payload
plan = current ProfileCompilePlan
decision = current CompileApplyDecision
compiler_used = false
memory_block_used = false
token_memory_dry_run = null
```

The profile compiler does not replace the `messages` field on this branch.

This is an exact current profile-compiler statement. Other request validation, routing, canonicalization, or later pipeline responsibilities remain separately owned.

## Applying compile path

When `decision.should_apply` is true, current code proceeds to build the profile-compiled request.

The current sequence includes:

```text
resolve profile files
  -> build profile blocks
  -> build persona-source budget diagnostics
  -> resolve configured candidate memory selection best-effort
  -> build local seed-memory adapter diagnostics/readiness/conflicts
  -> build token-memory dry-run best-effort
  -> insert selected configured memory block into profile blocks
  -> split incoming system messages from recent messages
  -> append incoming system prompt block to typed compile blocks
  -> render compiled messages
  -> replace payload_dict["messages"]
  -> save typed compiled context blocks in request-local ContextVar
```

This is the current MVP/profile compiler behavior. It does not establish target RelayMEM retrieval authority or target RelayCTX ordering.

## Current configured-memory handling inside the profile compiler

The current applying path may consume the configured candidate-memory selection used by the legacy/current profile compiler.

`_resolve_memory_selection_best_effort(...)`:

- re-raises `MemoryConfigurationError`;
- catches `FileNotFoundError`, `OSError`, `ValueError`, `TypeError`, `yaml.YAMLError`, and `json.JSONDecodeError`;
- on those caught failures returns an empty configured selection and a bounded fallback string of the form `memory_seed_load_error:<ExceptionClass>`.

The resulting configured memory block, when present, is inserted into the profile blocks before rendering.

This behavior is a current compiler input fact only. It does not grant this contract authority over the current Subjective MEM retrieval cutover, RelayMEM reader-family decisions, or later RelayMEM retrieval stage.

## Current token-memory dry-run handling

The applying compiler also builds its current token-memory dry-run from the configured selection.

`MemoryConfigurationError` is re-raised. The current best-effort catch set otherwise includes the same file/I/O/value/type/YAML/JSON decode classes and falls back to an empty `ConfiguredTokenMemoryDryRun`.

This diagnostic planning does not itself apply later token-budget truncation.

## Incoming system-message handling

Current applying profile compilation separates incoming system messages from recent messages, then appends the incoming system instruction material as the current typed system-prompt block before final profile rendering.

That current compiler behavior must not be mistaken for the target managed-route authority model described in newer architecture.

Later authority/canonicalization work may change this ordering and ownership. This contract records current exact behavior only.

## Runtime-private typed block handoff

The applying path stores the compiled typed context blocks in a request-local `ContextVar`.

The current helpers are:

```text
consume_compiled_context_blocks_runtime_private()
restore_compiled_context_blocks_runtime_private(blocks)
```

The consume helper clears the stored value after reading it.

The restore helper exists because compilation may execute on a worker thread and `ContextVar.set()` in the worker's copied context does not propagate automatically into the awaiting request context.

The async managed pipeline therefore captures the blocks on the worker and restores them in the request context before constructing/continuing the typed pipeline handoff.

These typed blocks are content-bearing runtime-private objects and are intentionally not included by `CompiledRequest.to_log_dict()`.

## Current rendering of instruction evidence

When a runtime-private compiled context block has type `CLIENT_INSTRUCTION_EVIDENCE`, current rendering:

1. HTML-escapes its content with `quote=False`;
2. checks the rendered character length against `CLIENT_INSTRUCTION_EVIDENCE_MAX_RENDERED_CHARS`;
3. raises `ValueError("instruction_evidence_oversize")` if the rendered value is too large;
4. otherwise uses the escaped value for final profile rendering.

Other current context-block types return their content unchanged through this helper.

This rendering rule is a current compiler safety detail. It is not a general evidence-retention or disclosure contract.

## CompiledRequest shape

`CompiledRequest` currently carries:

```text
payload
plan
decision
compiler_used
memory_block_used
memory_source
memory_selection_summary
memory_block_assembly
memory_fallback_reason
token_memory_dry_run
stable_prefix_hash
stable_prefix_block_ids
memory_adapter_dry_run
memory_adapter_readiness
memory_adapter_conflicts
context_block_summary
persona_source_budget_diagnostics
```

The object is request-local.

Its `payload` may contain the content-bearing compiled backend candidate. That payload is not included in `to_log_dict()`.

## CompiledRequest log projection

`CompiledRequest.to_log_dict()` emits compiler/memory/token/context diagnostics plus `plan.to_log_dict()` and `decision.to_log_dict()`.

It does not emit:

- the `payload` field;
- the rendered `messages` list;
- the runtime-private compiled context-block tuple.

Individual nested diagnostic objects use their separately owned current projections.

## Initial PipelineContext handoff

The current managed pipeline runs profile compilation near initialization, off the request event-loop thread through `asyncio.to_thread`.

After compilation, `_initialize_pipeline` constructs `PipelineContext` with:

```text
original_payload = original validated payload
forwarded_payload = dict(compiled.payload)
```

This is the initial forwarded-payload state for the managed pipeline.

It is **not** necessarily the final backend-forwarded payload.

## Current compiler ordering

Current profile compilation occurs before the later managed semantic/runtime stages that include:

```text
RelayREL
RelaySCN
RelayEMO
RelayINT
RelayMEM retrieval
RelayMEM runtime CTX/snippet injection
RelayCTX short-term injection
Token-budget truncation
```

Those later stages operate through `PipelineContext` and may replace/mutate the request-local `forwarded_payload` under their own contracts.

Therefore:

```text
CompileApplyDecision.should_apply
  -> controls current profile compiler application
  != final proof of backend payload identity
```

The final backend-forward boundary belongs to the managed request/response pipeline and adapter ownership, not this exact profile compile contract.

## Evidence capture occurs after initial compilation

In the current managed initialization sequence, the profile compile and initial `PipelineContext` construction happen before governed evidence capture for the current user input.

This ordering is a current implementation fact. The compile gate does not thereby gain authority over evidence admission, evidence persistence, or current Subjective MEM retrieval.

## Current compile diagnostics artifact

`build_compile_decision_dry_run(...)` builds the current content-free diagnostics object.

Its default schema is exactly:

```text
mvp-ctx-apply-0
```

The exact returned keys are:

```text
schema_version
decision_id
plan_id
result_id
decision_state
apply_compiled_messages
diagnostics_only
fallback_reason
blocking_reasons
selected_route
selected_mode
backend
character_id
compiled_message_count
omitted_block_ids
token_budget_status
```

The object contains no `messages` or `prompt` field.

## Diagnostics builder normalization

Current `build_compile_decision_dry_run` normalizes inputs as follows:

- `blocking_reasons=None` -> empty list;
- `omitted_block_ids=None` -> empty list;
- list entries are converted with `str(...)`;
- `compiled_message_count` is retained only when it is a non-negative integer, otherwise `None`;
- a non-string `decision_state` becomes `COMPILE_DRY_RUN`;
- a non-boolean `apply_compiled_messages` becomes `false`;
- a non-boolean `diagnostics_only` becomes `true`.

Other scalar identifier/route/backend/fallback/token-status arguments are passed through as supplied by the current caller.

The helper is intended to be fail-safe for missing/unknown values and does not perform prompt inspection.

## Current diagnostics defaults

Direct calls to the diagnostics builder default to:

```text
decision_state = COMPILE_DRY_RUN
apply_compiled_messages = false
diagnostics_only = true
schema_version = mvp-ctx-apply-0
```

These defaults are current diagnostics defaults, not a complete state machine.

## Managed-request diagnostics derivation

The current managed runtime builds its compile diagnostics from the already-created `CompiledRequest`.

It derives:

```text
compiled_message_count = plan.compiled_message_count if plan.enabled else null
apply_compiled_messages = (decision.should_apply is true)
```

When apply is true:

```text
decision_state = COMPILE_APPLY
diagnostics_only = false
fallback_reason = null
blocking_reasons = []
```

When apply is false:

```text
decision_state = COMPILE_DRY_RUN
diagnostics_only = true
fallback_reason = plan.fallback_reason or decision.reason
blocking_reasons = [decision.reason, optional distinct plan.fallback_reason]
```

The blocking-reason list preserves that exact current order and avoids adding the plan fallback twice when it equals the decision reason.

## Current request-derived IDs

The current managed runtime builds diagnostics IDs from `request_id` exactly as:

```text
<request_id>:compile-decision-dry-run
<request_id>:compile-plan
<request_id>:compile-result
```

These are request-local diagnostics identifiers. They are not durable memory IDs or proof that a separately materialized plan/result object exists under a target v1 schema.

## Current diagnostics route fields

The managed runtime supplies:

```text
selected_route = route.route_model
selected_mode = route.mode_applied
backend = route.backend_name
character_id = route.character_id
omitted_block_ids = []
token_budget_status = null
```

for the current `mvp-ctx-apply-0` artifact.

The current diagnostics artifact therefore does not currently encode a complete route-authority class, forwarded-payload source class, fallback class, compatibility result, or target blocked-state taxonomy.

## Diagnostics artifact is not a pipeline mutation

`_build_compile_decision_dry_run_artifact(...)` is pure diagnostics construction.

Current code explicitly does not:

- call `run_stage` for this helper;
- add a node timing for this artifact;
- touch `PipelineContext`;
- change the backend-bound payload;
- change the already-computed compile decision.

Its result is passed into request diagnostics assembly.

## RequestDiagnostics and trace

The current artifact is stored at:

```text
RequestDiagnostics.compile_decision_dry_run
```

`RequestDiagnostics.to_log_dict()` therefore includes it in generic diagnostics output.

When trace is enabled, current trace handling can persist the content-free diagnostics object with the request trace.

The focused smoke verifies that:

- the artifact is present in `RequestDiagnostics.to_log_dict()`;
- trace output contains `compile_decision_dry_run` when tracing is enabled;
- disabling trace leaves trace writing disabled.

Trace inclusion does not make the artifact a semantic decision owner.

## Content-free boundary

The current compile-decision diagnostics may expose bounded identifiers, route/mode/backend/character identifiers, state booleans, counts, block IDs, token-budget status, and bounded reason strings/classes supplied by the current builder.

It must not be interpreted as permission to copy runtime-private content into the artifact.

Current focused coverage explicitly checks that the diagnostics object does not contain top-level `messages` or `prompt` values.

The runtime-private `CompiledRequest.payload` and typed context-block contents remain outside this artifact.

## Current pass-through meaning at this gate

At this profile compiler boundary:

```text
plan enabled + mode_applied == pass_through
  -> should_apply = false
  -> profile_compile_ready = true
  -> reason = pass_through_diagnostics_only
  -> managed diagnostics derivation => COMPILE_DRY_RUN
```

This contract does not redefine the broader explicit delegated `pass_through` route behavior owned by routing/request-response architecture.

It only states that the current profile compiler result is not applied by this helper on that mode.

## Current memory_light meaning at this gate

At this profile compiler boundary:

```text
plan enabled + mode_applied == memory_light
  -> should_apply = true
  -> profile_compile_ready = true
  -> reason = memory_light_compile_enabled
  -> profile compiler replaces payload messages
  -> managed diagnostics derivation => COMPILE_APPLY
```

Later pipeline stages may still change the forwarded payload after this point.

`COMPILE_APPLY` therefore means the current profile compiler was applied, not that no later CTX/retrieval/token-budget mutation occurred.

## Disabled-plan behavior

When profile planning is disabled because the current planning catch set handled a profile file/configuration error:

```text
CompileApplyDecision.should_apply = false
profile_compile_ready = false
```

`compile_chat_payload_if_enabled` returns the shallow payload copy without profile-message replacement.

The current managed diagnostics becomes `COMPILE_DRY_RUN` with a fallback reason derived from the plan fallback or decision reason.

This contract does not upgrade that current behavior into the target managed fallback/fail-closed model.

## No current complete fallback taxonomy

The current profile compile boundary does not implement the full target distinction among:

```text
managed reduced fallback
shadow-only compile
blocked compile
explicit forwarded-payload-source class
route-authority class
```

Those are future/adjacent migration responsibilities.

Consumers must inspect current code/schema and the actual managed pipeline state instead of inferring target guarantees from target contract names.

## No current final-forward source field

`mvp-ctx-apply-0` does not include a `forwarded_payload_source` field.

Because later managed pipeline stages can mutate `PipelineContext.forwarded_payload`, the compile diagnostics artifact is not sufficient to reconstruct the final backend-forward payload source.

Any future canonical source typing must be introduced by an explicitly reviewed contract/runtime change.

## Semantic non-authority

This compile gate does not own or recompute:

- current relationship state;
- current scene classification/policy;
- current affect modulation;
- current intent decision;
- current Subjective MEM retrieval authority;
- RelayMEM retrieval ranking;
- RelayCTX working-state semantics;
- short-term CTX extraction/assembly/injection semantics;
- final token-budget truncation semantics;
- backend transport or response finalization.

It consumes only the inputs current code gives it and hands an initial payload into the wider managed pipeline.

## Persistence non-authority

Current plan, apply decision, and compiled request are request-local runtime objects.

The content-free compile-decision diagnostics may appear in trace when tracing is enabled.

The compile gate itself does not persist:

- prompt/message bodies;
- RelayMEM records;
- RelayCTX working state;
- RelaySOUL artifacts;
- scene/relationship/affect state;
- checkpoint envelopes;
- Character Workspace sources.

Checkpoint persistence is a separate runtime contract family.

## Failure and exception boundary

Current profile-plan construction handles only its documented `FileNotFoundError` and `ProfileConfigurationError` cases as disabled plans.

Current configured-memory/token helper paths have their own documented best-effort catch sets, with `MemoryConfigurationError` re-raised.

Other unexpected exceptions are not converted by this contract into a synthetic `BLOCKED` state.

The current exact contract therefore must not claim a broader fail-closed taxonomy than the implementation provides.

## Stable invariants

- `ProfileCompilePlan` construction is dry-run with respect to the incoming payload.
- Plan file/configuration failures handled by the current catch set produce an `enabled=false` plan with a bounded exception-class fallback reason.
- `CompileApplyDecision` has exactly four fields and controls only current profile-compiler application.
- A disabled plan never applies the current profile compiler regardless of mode.
- An enabled `pass_through` plan is diagnostics-only at this profile compile boundary.
- An enabled `memory_light` plan is the current apply-eligible profile compile case.
- Other enabled modes do not apply the current profile compiler.
- A non-applying current compile path returns a shallow payload copy without replacing `messages`.
- An applying current path replaces `payload["messages"]` with current profile-compiled messages and carries typed blocks request-locally.
- Runtime-private compiled payload/messages/typed blocks are omitted from generic `CompiledRequest.to_log_dict()`.
- The current managed compile diagnostics schema is `mvp-ctx-apply-0`.
- Current managed diagnostics derive only `COMPILE_APPLY` or `COMPILE_DRY_RUN` from `decision.should_apply`.
- The compile diagnostics artifact is content-free diagnostics construction and does not mutate `PipelineContext` or backend payload.
- Current profile compilation occurs before later REL/SCN/EMO/INT/MEM/CTX/token-budget managed stages.
- `COMPILE_APPLY` is not proof of final backend payload identity because later stages may replace `PipelineContext.forwarded_payload`.
- Current diagnostics do not implement the complete target route-authority/fallback/shadow/blocked taxonomy.
- Current compile objects do not persist semantic state or checkpoint content.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- the target `relaylm.compile_plan_projection.v1`, `relaylm.compile_result_projection.v1`, or `relaylm.compile_decision_projection.v1` schemas;
- a current `PASS_THROUGH`, `COMPILE_SHADOW_ONLY`, `COMPILE_FALLBACK`, or `BLOCKED` implementation where none exists;
- target canonical compiler ordering after SCN/INT/MEM/CTX selection;
- managed minimal-fallback construction;
- route-authority or forwarded-payload-source typing not present in the current artifact;
- current-boundary changes to client instruction/history authority;
- RelayMEM retrieval-family selection or R5 authority;
- RelayCTX repack semantics;
- checkpoint/recovery persistence;
- scheduler behavior;
- backend transport/response finalization;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related architecture and transitional contracts

- [Runtime Compile and Checkpoint Architecture](../../architecture/runtime/compile-and-checkpoint.md)
- [Request / Response Pipeline](../../architecture/runtime/request-response-pipeline.md)
- [Managed-Route Fallback Authority](../../architecture/managed_route_fallback_contract.md)
- [Runtime Compile Artifact Contract — transitional target vocabulary](../runtime_compile_artifact_contract.md)
- [Runtime Compile Current / Target Boundary — transitional migration boundary](../runtime_compile_current_target.md)
