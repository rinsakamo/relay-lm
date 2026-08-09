---
relaylm_doc_type: contract
relaylm_authority: managed_route_fallback_current_target_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - route mode or route-authority semantics change
  - managed payload fallback stages or fail-closed behavior change
  - client-history exclusion backend-forward gating changes
  - compile-gate fallback or blocked-state projections change
  - PipelineContext backend-bound payload/source tracking changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - profile compile plan or CompileApplyDecision field definitions
  - client-history exclusion candidate/provenance schemas
  - backend HTTP transport or response finalization
  - RelayRUN checkpoint schema or scheduler behavior
  - R5/R6 Primary MEM retirement or cutover authority
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/compile-and-checkpoint.md
  - ../../architecture/runtime/request-response-pipeline.md
  - ../../architecture/client_history_authority_contract.md
  - ../../architecture/client_history_exclusion_apply_forward_gate.md
  - ../../architecture/managed_route_fallback_contract.md
relaylm_related_contracts:
  - compile-gate.md
  - ../runtime_compile_current_target.md
relaylm_verified_by:
  - ../../../scripts/relaylm_compile_decision_dry_run_smoke.py
  - ../../../scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
  - ../../../scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - managed request routing and compiler maintainers
  - PipelineContext, backend adapter, and RelayRUN maintainers
  - client-history exclusion and compatibility maintainers
  - security, privacy, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Managed Route Fallback Contract

## Authority summary

This contract owns the stable route-authority invariant and the exact current/target interpretation of fallback for RelayLM chat routes.

The central rule is:

```text
route authority does not change because managed compilation or reconstruction fails
```

An explicit `pass_through` route delegates backend-context authority to the client. A managed route does not become pass-through as an error-recovery mechanism.

The target managed fallback ladder is:

```text
full RelayLM-managed payload
  -> reduced RelayLM-managed payload
  -> minimal RelayLM-managed payload
  -> fail closed
```

The complete ladder is not yet one current runtime state machine. Current code implements only portions of the boundary described below. Target labels must not be inferred from current non-applying compiler decisions.

## Route classes

The current configuration mode type contains exactly:

```text
pass_through
memory_light
memory_full
```

`resolve_route(...)` resolves the effective mode as:

```text
route.mode when explicitly configured
otherwise config.mode
```

and currently places that same resolved value in `ResolvedRoute.mode_applied`.

For this contract:

```text
explicit pass-through route
  = mode_applied == pass_through

managed route
  = mode_applied != pass_through
```

This classification describes context authority. It does not imply that every target managed fallback tier is implemented for every current managed mode.

## Explicit pass-through authority

For an explicit `pass_through` route:

- the client remains authoritative for compatible backend-bound context;
- the profile compiler is diagnostics-only at its current compile gate when its plan is enabled;
- managed client-history exclusion backend blocking is exempt;
- backend payload construction preserves the supplied payload fields apart from the backend-model replacement performed by the adapter;
- the reserved RelayLM control-envelope stripping used on managed routes is not applied by `build_backend_payload(...)`.

A pass-through request is therefore not a managed fallback tier. It is a separately selected route authority.

## Managed-route authority invariant

For a managed route:

```text
compiler/reconstruction failure
  != permission to restore client authority
  != permission to switch mode_applied to pass_through
  != permission to restore previously excluded history
```

Any implemented managed fallback must stay within RelayLM-owned payload construction. If no authorized managed payload can be constructed, the terminal target outcome is fail closed.

This invariant applies independently of whether a specific current feature gate is enabled.

## Current profile-compile boundary

The exact current profile compile mechanics are owned by [Runtime Compile Gate](compile-gate.md). This contract records only the route/fallback interpretation required to prevent accidental authority escalation.

Current `CompileApplyDecision` behavior includes:

```text
plan disabled
  -> should_apply = false

plan enabled + pass_through
  -> should_apply = false

plan enabled + memory_light
  -> should_apply = true

plan enabled + any other mode, including memory_full
  -> should_apply = false
```

A false `should_apply` result is not, by itself, a managed fallback state.

In particular:

```text
should_apply = false
  != PASS_THROUGH
  != COMPILE_FALLBACK
  != BLOCKED
  != reduced managed payload
  != minimal managed payload
```

When the current profile compiler does not apply, `compile_chat_payload_if_enabled(...)` returns a shallow dictionary copy of the incoming payload. That behavior is an exact current implementation fact, not proof that the target managed fallback ladder has completed successfully.

## Current managed history-exclusion gate

Current client-history exclusion is an independently gated managed reconstruction boundary.

Its safe defaults remain:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
```

When actual apply is explicitly requested:

```text
client_history_exclusion_apply_enabled == true
and
client_history_exclusion_apply_dry_run_only == false
and
mode_applied != pass_through
```

backend forwarding is allowed only when the request-local exclusion result is exactly applicable.

A missing, blocked, failed, or otherwise non-applicable result blocks backend forward. The previous client history is not restored as fallback.

Pass-through routes are exempt because client context authority was selected before the failure; the exemption must not be used to reclassify a managed request after failure.

## PipelineContext boundary

`PipelineContext` carries two distinct request-local payload concepts:

```text
original_payload
  = exact incoming request retained for request-local validation/evidence work

forwarded_payload
  = current backend-bound payload owned by the managed pipeline
```

Managed payload replacement is explicit and records the mutating step through `replace_forwarded_payload(...)`.

The existence of `original_payload` is not fallback authority. A managed failure must not copy `original_payload` back into `forwarded_payload` merely to keep a request moving.

Current source tracking is limited to the mutating-step record and the subsystem-specific result artifacts. The target fallback ladder may require stronger typed source/tier tracking; this contract does not pretend that tracking already exists.

## Backend-forward boundary

Immediately before backend transport, current adapter code enforces the active client-history exclusion gate.

For managed routes, `build_backend_payload(...)` strips the reserved RelayLM control envelope before assigning the backend model.

For pass-through routes, the adapter retains the client-owned payload shape and assigns the backend model.

The backend adapter does not own permission to invent a new fallback tier or to change route authority.

## Target managed fallback ladder

The target ordering remains exactly:

```text
1. full RelayLM-managed payload
2. reduced RelayLM-managed payload
3. minimal RelayLM-managed payload
4. fail closed
```

The ordering is monotonic toward less optional context, never toward less RelayLM authority.

### Full managed payload

A full managed payload is the normal RelayLM-constructed backend payload after all enabled required managed gates succeed.

Its exact component set is owned by the relevant compiler, context, memory, instruction, and runtime contracts. This contract owns only its position as the first managed attempt.

### Reduced managed payload

A reduced managed payload may omit optional RelayLM-managed context that is explicitly classified as safe to omit.

It must not:

- restore prior client user/assistant history that a managed exclusion boundary removed;
- promote frontend summaries or memory notes into authoritative context;
- weaken route or safety policy;
- silently reuse a failed full-payload candidate;
- bypass a gate whose failure is classified as terminal.

No current generic `reduced` state should be claimed unless an owning implementation and exact artifact contract define it.

### Minimal managed payload

A minimal managed payload is the smallest explicitly authorized RelayLM-owned request that still preserves the required current-turn and server-authority invariants.

It must not be synthesized by treating the incoming message array as trusted history.

Its exact required fields, source bindings, and eligibility are target work until separately implemented and contracted.

### Fail closed

Fail closed is the terminal managed outcome when no authorized managed payload tier is available.

Fail closed means:

```text
no backend request using restored client history
no automatic switch to pass_through
no hidden retry with weaker authority
no reuse of a blocked managed candidate as if successful
```

The public error and diagnostics projection remain owned by their runtime/error contracts. This contract owns only the authority outcome.

## Forbidden fallback forms

The following are forbidden as managed fallback behavior:

1. changing `mode_applied` to `pass_through` after a managed compile or reconstruction failure;
2. restoring `PipelineContext.original_payload` after managed history exclusion has applied or has become mandatory;
3. forwarding excluded prior client history because a later managed stage fails;
4. treating `CompileApplyDecision.should_apply == false` as permission to downgrade route authority;
5. using diagnostic, dry-run, shadow, or preflight artifacts as backend-forward permission unless their owning contract explicitly authorizes that effect;
6. inventing a reduced/minimal tier without a separately validated implementation boundary;
7. representing a blocked managed request as a successful fallback in RelayRUN or diagnostics.

## Current/target state interpretation

Current runtime has partial pieces of the target policy but not one complete fallback taxonomy.

Current implemented pieces include:

- explicit pass-through versus non-pass-through route classification;
- current profile compile apply/non-apply behavior;
- request-local `original_payload` versus `forwarded_payload` separation;
- explicit managed payload replacement reasons;
- managed client-history exclusion apply with a backend-forward fail-closed gate when actual apply is enabled;
- managed control-envelope stripping at backend payload construction.

Not established as one current exact fallback state machine:

- typed `full | reduced | minimal | blocked` managed-tier state;
- generic reduced-payload construction;
- generic minimal-payload construction;
- a complete compile-gate fallback/blocked diagnostics taxonomy;
- complete typed PipelineContext fallback-source tracking;
- complete RelayRUN fallback-tier routing/projection.

Consumers must therefore inspect the actual forwarded payload, route mode, current compile-decision fields, client-history exclusion result, payload-replacement reason, and separately owned diagnostics rather than inferring an unimplemented target state.

## Migration coupling

A transaction that implements or materially changes the complete managed fallback ladder must treat the affected authority surfaces as one coordinated migration boundary.

At minimum, the change must account for:

- route-authority typing and resolution;
- managed client-history exclusion and reconstruction;
- reduced/minimal payload construction;
- compile-gate fallback/blocked projections;
- PipelineContext payload/source tracking;
- RelayRUN routing or runtime-artifact projection where affected;
- backend-forward compatibility checks;
- exact smokes for success, downgrade prevention, and fail-closed behavior.

This coupling requirement does not authorize one oversized implementation transaction. It means the architecture/authority migration must not leave an interval in which a failure can regain client context authority.

## Diagnostics and privacy

Fallback diagnostics must remain content-free unless a separately authoritative runtime-private contract explicitly owns content-bearing data.

Persisted or public fallback evidence should describe bounded state such as:

```text
route class
managed tier/state when implemented
apply/blocked status
bounded reason identifiers
payload replacement source/step
```

It must not persist raw messages, prompt bodies, private instruction evidence, or excluded client history merely to explain why fallback occurred.

## Legacy source provenance

This canonical contract was extracted from the stable responsibility in:

```text
docs/architecture/managed_route_fallback_contract.md
```

That source established the enduring rules that explicit pass-through is client-authority selection, managed failure does not change route authority, excluded history is not restored, and target fallback proceeds full -> reduced -> minimal -> fail closed.

The legacy file remains in place as migration/source provenance until a separately authorized documentation-retirement transaction classifies its consumers and disposition. It is not authorization to retire or rewrite that source in this transaction.

## Non-ownership

This contract does not redefine:

- exact `ProfileCompilePlan` or `CompileApplyDecision` fields;
- exact client instruction or history-exclusion schemas;
- RelayREL/RelaySCN/RelayEMO/RelayINT/RelayMEM/RelayCTX semantics;
- backend HTTP request/stream transport;
- response finalization, TTS transport, scheduler operation, or durable memory cutover;
- repository-wide completion status.

Those responsibilities remain with their owning architecture/contracts and current status authority.
