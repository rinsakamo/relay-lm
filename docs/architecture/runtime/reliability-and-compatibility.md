---
relaylm_doc_type: concept_policy
relaylm_authority: runtime_reliability_compatibility_safe_degradation_and_acceptance_policy
relaylm_status: current
relaylm_volatility: low
relaylm_owner: runtime
relaylm_update_trigger:
  - cross-cutting runtime reliability or compatibility posture changes
  - optional-feature failure/degradation rules change
  - supported compatibility-sensitive request/response handling changes conceptually
  - deferred-work failure begins changing already-valid visible response semantics
  - product-level runtime acceptance dimensions change
relaylm_not_authoritative_for:
  - current repository implementation completion or sequencing
  - exact route, fallback, retry, recovery, scheduler, queue, transport, or backend schemas
  - exact supported OpenAI request fields, provider-specific compatibility tables, or frontend integration versions
  - exact latency budgets, test fixtures, thresholds, CI gates, or release criteria
  - semantic scene, intent, memory, character, privacy, or capability decisions
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - request-response-pipeline.md
  - operational-observability.md
  - conversation-capability-boundary.md
  - ../context/context-assembly.md
  - ../performance/perceived-latency.md
  - ../privacy/local-first-runtime.md
  - ../system-overview.md
  - ../runtime_operational_requirements.md
  - ../../contracts/runtime/managed-route-fallback.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime, router, context, memory, scheduler, and adapter maintainers
  - integration, compatibility, evaluation, and operations maintainers
  - product, privacy, and safety reviewers
relaylm_authority_level: concept
---
# Runtime Reliability and Compatibility

## Authority summary

RelayLM should remain usable when optional enrichment or background work fails, but reliability must never be implemented by silently widening authority, changing protocol meaning, or fabricating success.

The stable cross-cutting posture is:

```text
valid request under an accepted route
  -> preserve route and protocol authority
  -> use the strongest supported compatible behavior available
  -> degrade only where the owning contracts permit
  -> otherwise return a bounded blocked/error outcome
```

This page owns that **reliability and compatibility philosophy**. Exact fallback ladders, schemas, retry rules, transport behavior, and implementation-specific support matrices remain with their owners.

## Reliability is not "always return an answer"

A reliable character runtime should continue useful service through ordinary optional failures when it can do so without changing authority or protocol semantics.

Examples may include:

- an optional memory source being unavailable;
- an optional retrieval result timing out;
- a cache miss;
- a non-required presentation adapter being unavailable;
- deferred post-response work failing after the visible response is already valid.

But reliability does not require producing a successful assistant answer after every failure.

A bounded blocked/error result is the correct reliable outcome when continuing would require:

- restoring excluded client authority;
- accepting malformed or untrusted context;
- dropping required tool/structured-output/multimodal state;
- bypassing a persistence or capability gate;
- inventing missing identity or scope;
- changing the selected backend/destination without authority;
- replaying already-emitted visible content unsafely.

The durable rule is:

```text
availability goal
  < authority and protocol correctness
```

## Explicit route authority survives failure

RelayLM may expose route modes with different ownership models.

An explicit delegated/pass-through route and a RelayLM-managed route do not become equivalent just because an optional managed feature failed.

For a managed route, degradation must remain inside the managed authority boundary.

Conceptually:

```text
managed request
  -> full approved managed context
  -> reduced approved managed context where allowed
  -> authority-safe minimal managed context where allowed
  -> blocked/error
```

It must not become:

```text
managed compilation failed
  -> silently restore arbitrary client history
  -> silently become delegated pass-through
```

Exact managed-route fallback semantics are owned by the corresponding runtime contract.

## Optional enrichment must remain optional in failure semantics

Optional context features should not become single points of process failure merely because they add quality when available.

Where policy allows omission, failures in optional enrichment may result in:

- omission;
- a smaller selected context;
- a cache miss;
- a bounded reason/status artifact;
- continuation through the ordinary backend path.

This applies conceptually to optional memory, retrieval, summaries, caches, speculative work, or other enrichment.

The owner of each feature decides whether it is actually optional for a given request.

The runtime must not label a required dependency optional merely to keep serving.

## Required semantic and protocol state cannot be degraded away

Some state is required for a request to remain valid.

Depending on the exact route and integration, required state may include:

- the current validated user input;
- approved character/runtime policy;
- active tool transaction state;
- structured-output constraints;
- multimodal transaction structure;
- exact current instruction provenance;
- scene/intent blocks that prohibit proceeding;
- capability authorization state.

When required state cannot be preserved correctly, the request should stop or fail under its owning contract.

A shorter payload is not automatically a valid fallback.

## Compatibility-sensitive shapes are preserved or explicitly rejected

OpenAI-compatible transport is a compatibility boundary, not merely a JSON container.

Requests may contain shapes whose meaning cannot safely survive casual repacking, such as:

- tool calls and tool results;
- structured-output requirements;
- multimodal parts;
- provider-specific transaction state;
- streaming semantics;
- fields whose ordering or identity matters to an active protocol.

The cross-cutting rule is:

```text
understood + supported
  -> preserve according to the owning adapter/runtime contract

not safely supported
  -> explicit preflight block/error
  -> no silent flattening or semantic rewrite
```

This page does not declare which shapes are currently implemented.

## Compatible transport errors are valid product outcomes

Backend, routing, or transport failure must not be hidden by fabricating semantic success.

When forwarding cannot continue, the runtime may return the compatible error representation defined by its transport/integration boundary.

The stable invariant is:

```text
backend failed
  != assistant successfully answered
```

Likewise, a checkpoint or diagnostic entry saying a stage started does not justify reporting a completed response.

## Already emitted visible output is a special reliability boundary

Streaming creates state outside the server as soon as safe visible content is emitted.

After that point, recovery must respect what the user/frontend may already have received.

Cross-cutting constraints include:

- do not duplicate already emitted chunks;
- do not replay the entire answer unless an exact recovery contract permits it;
- do not expose incomplete internal/sentinel/update material;
- do not rewrite earlier visible content merely to make a later stage appear successful;
- preserve content-free evidence of the partial outcome where an owner defines it.

Exact stream suppression and recovery algorithms remain with their contracts.

## Deferred work is not part of visible-response success unless explicitly coupled

RelayLM may perform queueing, candidate extraction, durable finalization, indexing, summaries, or other work after the visible response boundary.

When the visible response was already valid, later deferred failure should normally remain a separate operational outcome.

Conceptually:

```text
visible response success
  + deferred maintenance failure
  -> response remains historically valid
  -> maintenance failure is observable separately
```

This protects user-visible reliability from background subsystems while preserving truthful operational state.

It does not excuse failed durable work; retries and recovery remain governed by the owning queue/worker/finalization contracts.

## Reliability must preserve idempotency boundaries

Retries, reconnection, scheduler rounds, and recovery can create duplicate-effect risk.

The cross-cutting reliability posture is that a retry must not infer idempotency merely because the previous attempt ended ambiguously.

Separate effects may have separate idempotency identities, for example:

- request dispatch;
- queue transition;
- durable memory write;
- lifecycle mutation;
- user-visible transport emission.

An idempotency guarantee in one layer does not automatically cover another.

Exact keys and replay rules belong to the exact contracts.

## Failure must not broaden privacy scope or destination

Reliability fallback is subordinate to local-first privacy and protected-source policy.

Unsafe reliability shortcuts include:

- using a global store after a scoped store fails;
- reading another character/user namespace after a miss;
- sending data to a different remote provider without route authority;
- enabling remote telemetry when local diagnostics fail;
- exposing protected bodies because typed diagnostics were unavailable.

A reliable failure can be a narrower result, a miss, or an explicit error.

It does not require a broader destination or data scope.

## Failure must not create mutation authority

A runtime should not mutate durable state merely to make a request appear recovered.

Examples of invalid fallback include:

- writing a guessed memory because retrieval failed;
- changing SOUL/SELF/REL/GOAL to repair an inconsistent response;
- applying a held candidate because the preferred path was unavailable;
- converting an untrusted repaired context into trusted durable state;
- deleting stale state outside its lifecycle contract.

Reliability coordinates existing authorities; it does not create them.

## Observability is part of reliable operation

A bounded failure is more useful when operators can distinguish its class without exposing protected content.

Operational evidence should make it possible to tell, under the producing contracts, whether a stage:

- ran or skipped;
- succeeded, blocked, failed, or requested retry;
- used a fallback/degraded path;
- attempted a mutation;
- emitted visible output;
- queued or finalized deferred work.

`operational-observability.md` owns the cross-cutting diagnostic privacy posture.

This reliability page only requires that failure/degradation not be concealed as success.

## Product acceptance is multi-dimensional

Runtime acceptance cannot be reduced to "unit tests pass" or "the server returned 200."

A mature RelayLM slice should be judged across the dimensions relevant to that responsibility.

Cross-cutting dimensions include:

- compatibility;
- authority preservation;
- character/context integrity;
- memory/persistence governance where involved;
- visible/internal separation;
- latency responsiveness;
- recovery and idempotency;
- privacy/isolation;
- operational observability.

This list defines review dimensions, not a universal score or release gate.

Exact acceptance tests and thresholds remain with implementation/evaluation owners.

## Compatibility acceptance

Compatibility review asks whether a supported frontend or caller can use RelayLM without hidden protocol changes.

Questions include:

- does model/route resolution remain predictable;
- are supported streaming and non-streaming semantics preserved;
- are required fields and transaction shapes retained;
- are unsupported compatibility-sensitive shapes blocked explicitly;
- does a managed route preserve its authority model during degradation;
- does an explicit delegated route remain distinguishable from managed execution.

A feature that improves persona quality but silently breaks protocol compatibility is not complete.

## Character and context acceptance

Character/context review asks whether operational degradation preserves the hierarchy of semantic owners.

Questions include:

- is the latest validated request retained;
- are approved durable character anchors still authoritative;
- can memory/retrieval evidence override identity after a fallback;
- are excluded client instructions/history accidentally restored;
- are internal artifacts or diagnostics exposed to the model/user;
- is a missing semantic decision being guessed by the wrong layer.

The exact semantic answers belong to character/context/scene/intent/memory owners.

## Memory and persistence acceptance

Where a slice touches durable memory or state, review asks whether failure can cause unauthorized writes or resurrection.

Questions include:

- does read-only retrieval stay read-only;
- can low-confidence/held/blocked candidates become active during fallback;
- are lifecycle mutations gated and idempotent;
- can a forgotten/hidden item reappear through a fallback reader;
- does deferred persistence failure remain distinguishable from visible-response success;
- does another subsystem accidentally acquire memory-write authority.

Exact lifecycle semantics remain with memory contracts.

## Latency acceptance

Reliability includes responding soon enough for the intended interaction profile.

Review may distinguish:

- request overhead;
- backend first token;
- first safe visible output;
- first adapter-ready speech segment;
- deferred post-response work.

Optional heavy work should not block first response merely because it may improve later state, unless the current request explicitly requires that work.

Exact latency targets remain with performance architecture/evaluation.

## Recovery acceptance

Recovery review asks whether interrupted or repeated execution remains coherent.

Questions include:

- can a retry duplicate visible output;
- can a retry duplicate a durable effect;
- is a checkpoint being mistaken for resume support;
- can stale state be recovered only through its owning transition;
- does a repaired context still require confirmation where specified;
- are safe blocked/error outcomes observable.

The exact recovery mechanism remains with RelayRUN, scheduler, queue, worker, storage, or lifecycle owners as applicable.

## Reliability should be compositional

RelayLM has many bounded owners. Reliability should arise from their contracts composing correctly rather than from a universal catch-all exception handler that rewrites state.

A healthy composition looks like:

```text
component validates its input
  -> component emits bounded typed result
  -> caller interprets result under its own contract
  -> optional failure degrades only where allowed
  -> required failure stops safely
```

This makes failures local enough to reason about and prevents one generic recovery layer from becoming a hidden semantic authority.

## Do not use broad exception recovery as semantic policy

Catching an unexpected exception may be necessary at a process/transport boundary to avoid crashing a server.

But the fallback chosen after that catch must still follow current authority.

An exception handler must not infer:

- which memory is safe to use;
- which client history is trusted;
- which character source should apply;
- whether a capability may execute;
- whether a durable mutation should be retried;
- whether a different backend/provider is allowed.

Those decisions remain typed responsibilities.

## Defaults should be conservative at new authority boundaries

New authority-changing features should not rely on hidden default-on behavior merely because the legacy path is inconvenient.

Where the owning implementation plan requires staged rollout, dry-run/default-off behavior can be part of safe convergence.

This concept does not define a universal configuration triple. It establishes the product principle that reliability experiments must not silently become authority changes.

## Historical mode ladders are not current authority rules

Older RelayLM design material described broad mode degradation such as:

```text
memory_full -> memory_light -> pass_through
```

Such descriptions are useful product history but cannot override current route authority.

A mode name does not itself authorize a fallback transition.

Current exact routing/fallback contracts determine whether a specific transition is allowed.

## Reliability and quality are related but distinct

A response can be technically reliable but poor character interaction, and a character-rich response can be operationally unreliable.

`character/interaction-quality.md` owns character-experience semantics.

This page owns the operational expectation that the runtime:

- preserves valid protocol behavior;
- does not hide failure as semantic success;
- degrades without widening authority;
- isolates deferred failure;
- remains observable and testable.

Both dimensions matter to the product.

## Stable reliability invariants

```text
reliability != always answer
managed failure != implicit pass-through
degradation != authority widening
unsupported protocol shape != flatten to text
backend failure != fabricated assistant success
already emitted output != safe to replay automatically
deferred failure != retroactive visible-response failure
checkpoint != resume permission
retry != automatic idempotency
fallback != privacy scope widening
failure != mutation authority
observability != semantic authority
historical mode ladder != current fallback contract
```

Exact behavior remains with the owners that implement each boundary.
