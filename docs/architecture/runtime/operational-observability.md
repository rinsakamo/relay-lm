---
relaylm_doc_type: concept_policy
relaylm_authority: runtime_operational_observability_and_content_minimization_policy
relaylm_status: current
relaylm_volatility: low
relaylm_owner: runtime
relaylm_update_trigger:
  - cross-cutting runtime observability semantics change
  - diagnostic content-minimization or public/private projection policy changes
  - runtime reason, status, lineage, checkpoint, timing, or namespace observability responsibilities change
  - a subsystem begins exposing protected payload content through ordinary diagnostics
relaylm_not_authoritative_for:
  - current repository implementation completion or sequencing
  - exact diagnostic, trace, checkpoint, reason, status, or projection schemas
  - exact metric names, log formats, exporters, storage backends, retention periods, dashboards, or alert thresholds
  - semantic memory, scene, relationship, character, or capability decisions
  - remote telemetry destination authority
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - request-response-pipeline.md
  - conversation-capability-boundary.md
  - ../privacy/protected-source-and-disclosure.md
  - ../privacy/local-first-runtime.md
  - ../context/context-assembly.md
  - ../runtime_operational_requirements.md
  - ../../contracts/runtime_compile_artifact_contract.md
  - ../../contracts/runtime/compile-gate.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime, router, scheduler, memory, context, and adapter maintainers
  - diagnostics, evaluation, operations, and incident-analysis maintainers
  - privacy and security reviewers
relaylm_authority_level: concept
---
# Runtime Operational Observability

## Authority summary

RelayLM should make runtime decisions inspectable without turning diagnostics into a second copy of protected conversation, memory, character, or backend payload content.

The stable posture is:

```text
runtime event or decision
  -> typed bounded state
  -> stable reason/status identifiers where an owner defines them
  -> content-free or content-minimized projection by default
  -> protected payload remains behind its owning boundary
```

This page owns the cross-cutting **meaning and privacy posture of operational observability**. Exact schemas and fields remain with the subsystem or contract that produces each artifact.

## Observability exists to explain behavior, not reproduce payloads

Operational evidence should help answer questions such as:

- which route or component handled the request;
- whether a stage ran, skipped, blocked, degraded, retried, or failed;
- whether a candidate or projection was present;
- whether a mutation or external effect was attempted;
- which bounded reason class explains an outcome;
- whether a checkpoint, queue transition, or recovery state exists;
- whether a request remained within the expected character/user/room/session scope;
- how much bounded work occurred;
- where latency accumulated.

It should not require exposing the semantic body that caused the decision.

The stable distinction is:

```text
explain the transition
  != duplicate the protected input/output
```

## Content-free is the default for generic runtime projections

Generic runtime diagnostics should prefer metadata that can be interpreted without reconstructing protected content.

Useful categories may include:

- schema version;
- component or node identifier;
- route/backend class or approved identifier;
- requested/applied mode;
- state or status enum;
- bounded reason IDs;
- candidate present/absent booleans;
- mutation attempted/applied booleans;
- selected-item counts;
- bounded token/input-size classes or counts;
- queue, retry, lease, or checkpoint state;
- lineage or generation identifiers where allowed;
- timing values;
- scope-presence or namespace-class indicators;
- cancellation/shutdown/fallback classes.

These examples do not create a universal schema. Each exact producer defines its own allowed fields.

## Protected semantic bodies stay behind their owners

Generic operational artifacts should not expose by default:

- raw user or assistant messages;
- backend request or response bodies;
- compiled prompt text;
- character-source bodies;
- SOUL, SELF, REL, GOAL, scene, affect, or relationship prose;
- memory page, evidence, snippet, candidate, or retrieved body content;
- tool payloads containing protected data;
- credentials, tokens, secrets, or secret-bearing URLs;
- arbitrary nested private runtime artifacts;
- full exception text when it can contain content or implementation-sensitive detail.

A subsystem that legitimately needs protected content for execution may retain it in its private/request-local artifact. That does not make the same content eligible for the generic diagnostic projection.

## Public projection and private execution artifact are different responsibilities

Many RelayLM stages need richer private state than they may expose.

The stable pattern is:

```text
private execution artifact
  may contain bounded content needed by the owner

public / generic diagnostic projection
  contains only approved operational state
```

A public projection should not become a serialization shortcut for the private object.

When new fields are added, the owner should decide explicitly whether they are:

- required for execution only;
- safe for generic diagnostics;
- safe only under a narrower protected inspection surface;
- not persistable at all.

## Reason identifiers are preferable to raw exception strings

Failures need interpretable classification without making incidental implementation text a contract.

Where a component exposes reasons, prefer bounded identifiers or enums such as conceptual classes for:

- invalid input;
- unavailable dependency;
- policy block;
- unsupported compatibility shape;
- stale or mismatched state;
- retry later;
- cancellation or shutdown;
- internal unexpected failure.

The exact strings belong to the exact owner.

Raw exception messages are unsuitable as a stable cross-cutting interface because they may:

- include protected values;
- change with dependencies or Python versions;
- reveal internal paths or implementation details;
- create accidental compatibility obligations;
- tempt downstream code to parse prose.

An internal exception may be retained under a protected debug boundary when explicitly allowed, while the ordinary projection remains typed and bounded.

## Unknown and malformed diagnostic state fails closed

Diagnostics must not invent a stronger success state when an artifact is malformed, unknown, or from an unsupported schema.

Conceptually:

```text
unknown / malformed diagnostic artifact
  -> unavailable / invalid / unsafe-to-interpret class
  -> no inferred success
```

Observability is evidence about runtime behavior. It must not become a backdoor authority source that changes the behavior being observed.

## Observability never grants semantic or capability authority

A diagnostic artifact may report that a component observed, proposed, selected, attempted, or applied something.

That report does not independently authorize later behavior.

Examples:

```text
memory candidate count > 0
  != permission to persist memory

intent says action requested
  != permission to execute the action

scene identifier present
  != disclosure permission

checkpoint exists
  != proof that resume is supported

cache hit recorded
  != memory eligibility

previous status = success
  != authority to skip current validation
```

Downstream owners use their own current contracts and durable state, not generic diagnostics, as authority.

## Diagnostics do not belong in stable prompt prefixes

Machine evidence, counters, reason IDs, timestamps, run identifiers, and trace metadata are not character context merely because they are available.

The stable separation is:

```text
operational evidence
  -> operations / debugging / evaluation

approved semantic context
  -> backend context under RelayCTX and upstream semantic owners
```

Injecting diagnostics into stable prompt prefixes can damage cache stability, expose implementation details, and allow operational metadata to influence character semantics without an owning policy.

## Scope and identity must not leak through convenient labels

Operational diagnostics often need to distinguish character, user/viewer, room, scene, session, memory, or cache scopes.

A diagnostic may expose an approved identifier or a presence/class indicator when its owner allows it.

But a namespace label remains metadata, not authenticated identity or permission.

When an identifier itself is sensitive, unnecessary, high-cardinality, or externally derived, a safer projection may expose only:

- present/absent;
- matched/mismatched;
- same/different scope;
- bounded class;
- content-free digest or opaque identity under an exact contract.

Exact identity projection belongs to the owner.

## Lineage and generation metadata should be purpose-bounded

Generation, operation, transaction, checkpoint, revision, manifest, or lineage identifiers can be useful for:

- idempotency analysis;
- stale-state detection;
- recovery audit;
- queue/worker correlation;
- exact source/result binding;
- debugging duplicate or out-of-order effects.

They should remain bounded to the purpose that requires them.

A lineage identifier does not grant access to the content behind that lineage.

## Timing is observable without exposing content

Latency and scheduling analysis normally requires timestamps or durations rather than semantic payloads.

Useful timing boundaries may include, where implemented:

- request accepted;
- route resolved;
- context ready;
- backend request started;
- first token or first safe visible output;
- first adapter-ready speech segment;
- queue admitted/claimed/finalized;
- retry-not-before class;
- operation completed.

Exact metric names and clocks belong elsewhere.

The conceptual rule is that performance analysis should not require logging the prompt or response body.

## Counters must remain bounded

Counts are safer than bodies only when they are bounded and meaningful.

A runtime contract may expose counts such as:

- candidates considered;
- memories selected;
- queue entries scanned;
- retries attempted;
- reasons emitted;
- output segments produced.

Unbounded collections or arbitrary nested lists can recreate sensitive or unstable runtime state even without literal prose.

Each producer should define bounds appropriate to its artifact.

## Persisted diagnostics require a stronger decision than ephemeral inspection

A request-local in-memory observation and a durable log record are not the same privacy surface.

Persistence increases:

- retention duration;
- discoverability;
- correlation capability;
- exposure during support or backup;
- the consequences of accidental content inclusion.

Therefore:

```text
safe to inspect request-locally
  != automatically safe to persist
```

Exact persistence, retention, rotation, deletion, and storage authorities remain outside this concept.

## Local-first destination posture composes with content minimization

`privacy/local-first-runtime.md` owns the destination/scope posture for RelayLM-owned operational data.

This page owns what generic operational observability should contain.

The two are independent requirements:

```text
content-free diagnostic
  != permission to upload remotely

local diagnostic
  != permission to include protected content
```

A future remote telemetry feature therefore needs both explicit destination authority and an exact content contract.

## Protected-source disclosure remains authoritative

`privacy/protected-source-and-disclosure.md` owns whether protected semantic content may be used or disclosed for a purpose and audience.

Operational observability must not create a broad exception such as "debug mode may log everything."

If a protected inspection mode is needed, it requires an explicit bounded authority that defines:

- who/what may access it;
- what content is included;
- why it is required;
- how long it persists;
- how ordinary content-free mode is restored.

This concept does not create that mode.

## Checkpoints are evidence, not automatic recovery capability

A checkpoint or durable transition record can prove that a stage reached a known state.

It does not by itself prove that:

- all required state can be reconstructed;
- replay is safe;
- the operation is idempotent;
- a stale lease may be recovered;
- a user-visible response may be replayed;
- a mutation may be retried.

Recovery, replay, and scheduler contracts define those permissions.

Observability should report the checkpoint state without overstating capability.

## Deferred work must not contaminate the already valid visible response

When background queueing, candidate extraction, durable finalization, or maintenance fails after a valid visible response, diagnostics should preserve that separation.

Conceptually:

```text
visible response succeeded
  + deferred maintenance failed
  -> report deferred failure separately
  -> do not rewrite historical response status as semantic failure
```

Exact status composition belongs to the owning handoff/queue/finalization contracts.

## Adapter diagnostics remain transport metadata

Backend, TTS, avatar, renderer, or other external adapters may expose transport or availability state.

That state should not become character truth.

For example:

- TTS unavailable does not mean the character decided not to speak;
- backend timeout does not create a durable memory fact;
- transport retry count does not belong in SOUL or SELF;
- a renderer error does not authorize semantic regeneration.

Operational state stays operational unless a semantic owner explicitly consumes a bounded result for its own purpose.

## Evaluation may consume diagnostics without changing their authority

Evaluation and dogfood tooling can use content-free operational evidence to compare:

- latency;
- fallback frequency;
- retry behavior;
- queue health;
- candidate admission rates;
- schema/version distribution;
- block/clarification frequency;
- resource or stage utilization.

Evaluation consumption does not upgrade the diagnostic into runtime authority, and evaluation-specific protected samples belong to their own storage/disclosure boundary.

## Avoid a universal global diagnostic object

RelayLM is composed of bounded owners with separate schemas and lifecycles.

A single unrestricted object that accumulates every subsystem's private state would undermine those boundaries.

Cross-cutting observability should instead compose bounded projections:

```text
component-private state
  -> component-approved diagnostic projection
  -> optional request/run correlation layer
```

Correlation should not require merging protected payloads.

## Stable operational posture

The cross-cutting invariants are:

```text
observability explains behavior; it does not reproduce payloads
content-free by default
private execution artifact != public diagnostic projection
stable reason IDs > raw exception prose
unknown diagnostic state != inferred success
diagnostic evidence != semantic or capability authority
machine diagnostics != backend prompt context
local storage != permission for protected content
content-free != permission for remote telemetry
checkpoint present != recovery supported
adapter state != character truth
```

Exact schemas remain with the owners that produce them.
