---
relaylm_doc_type: subsystem_architecture
relaylm_authority: perceived_latency_measurement_and_optimization_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: performance
relaylm_update_trigger:
  - request or streaming latency measurement boundaries change
  - first-visible-output or stream-drain semantics change
  - voice/audio timing becomes a measured RelayLM boundary
  - latency optimization introduces a new governed skip, timeout, or degradation decision
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact timing trace schemas, field names, benchmark flags, or storage formats
  - component-specific semantic policy, retry, timeout, or degradation behavior
  - backend/provider SLA, network SLA, TTS engine SLA, or frontend rendering SLA
  - search/ranking/candidate-limit, scheduler, or memory lifecycle design
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../pipeline-responsibilities.md
  - ../runtime/request-response-pipeline.md
  - ../runtime/scheduler.md
  - ../lat1_latency_measurement.md
  - ../lat2_mobile_perceived_latency.md
  - ../voice/streaming-and-tts.md
  - ../../evaluation/mobile-dogfood-observation.md
  - ../../evaluation/lat1-retrieval-scaling.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_related_contracts:
  - ../../contracts/relayrun-checkpoint-and-recovery.md
  - ../../contracts/pipeline_node_result_contract.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime and scheduler maintainers
  - retrieval and context maintainers
  - realtime frontend and voice maintainers
  - performance, evaluation, and operations reviewers
relaylm_authority_level: subsystem
---
# Perceived Latency Architecture

## Purpose

This page is the canonical responsibility map for measuring and reasoning about RelayLM perceived latency.

Perceived latency is not one number. RelayLM separates at least:

```text
request accepted
  -> RelayLM pre-backend work
  -> backend stream open / response wait
  -> first visible chunk
  -> remaining stream drain
  -> optional downstream presentation such as TTS/audio
```

The performance subsystem owns the meaning and safe interpretation of those timing boundaries. It does not own the semantics of the components being measured.

The central invariant is:

```text
measurement
  != optimization authority
  != semantic skip authority
  != SLA
```

A slow measured stage is evidence for investigation, not permission to bypass its owner.

## Current implementation boundary

Current latency instrumentation is split across two completed measurement slices:

- **LAT-1** records per-node RelayRUN timing and a content-free request-path timing summary;
- **LAT-2** records a second content-free stream-final timing observation for streaming responses, including time to first chunk and stream drain.

Both are measurement-only. They did not change search/ranking, candidate limits, timeout behavior, degradation behavior, backend forwarding, SSE payloads, or UI behavior.

Current instrumentation does not constitute a response-time guarantee or service-level objective.

Current TTS/audio/avatar execution is outside RelayLM Core, so end-to-end first-audio timing is not yet a complete RelayLM Core metric. Project Status remains authoritative for exact implementation state.

## Perceived latency is stage-composed

A useful model is:

```text
T_visible ~= T_pre_backend + T_backend_open_and_first_output + T_transport_to_client

T_complete ~= T_visible + T_remaining_stream_drain

T_first_audio ~= T_visible + T_segmentation_ready + T_adapter_delivery + T_tts_first_audio
```

These are conceptual decompositions, not exact formulas guaranteed by every backend/frontend.

The value of the decomposition is responsibility: each measured interval has an owning boundary, and optimization can target the relevant source rather than weakening unrelated semantics.

## Request-path latency and stream latency are different observations

RelayRUN's request-path checkpoint is constructed before streaming body iteration begins.

Therefore a synchronous request-path timing artifact can measure work completed before the response starts, but it cannot truthfully backfill a future first-chunk timestamp that did not yet exist.

LAT-2 preserves this temporal boundary by writing a later stream-final timing record instead of mutating or delaying the earlier checkpoint.

The stable rule is:

```text
an earlier artifact never claims knowledge of a later event
```

If a metric requires observation after streaming begins, it belongs in a later observation path.

## Time to first chunk is not time to first token

Current streaming measurement observes the first body chunk at the outer assembled stream boundary.

That metric is useful for perceived responsiveness, but it must not be mislabeled as model-token latency unless the implementation actually has tokenizer/provider-level evidence.

A body chunk may contain protocol framing or multiple model tokens depending on backend behavior.

Accordingly:

- `first chunk` is an observable transport/runtime event;
- `first token` is a model/tokenization concept;
- `first visible text` may require output-safety interpretation;
- `first audio` belongs even later in the presentation chain.

These terms must remain distinct in architecture, reports, and optimization claims.

## Backend open and stream drain measure different costs

For a streaming request, opening the backend stream and draining it are separate timing regions.

Backend-open timing ends when status/headers establish the stream. Stream-drain timing ends only when the assembled body iterator completes, errors, or closes.

A low stream-open time does not prove a low first-visible-chunk time, and a fast first chunk does not prove a short total response duration.

Performance reporting should preserve the distinction rather than collapsing all streaming behavior into one backend latency number.

## The outer stream observer measures the assembled delivery path

Current LAT-2 timing wraps the fully assembled stream immediately before it becomes the response body iterator.

This placement means its first-chunk and drain observations include the effects of upstream stream wrappers already applied in the request path.

That is appropriate for perceived runtime latency because the user cannot receive a chunk until the assembled path yields it.

The observer remains measurement-only:

- it does not buffer chunks for performance analysis;
- it does not reorder chunks;
- it does not decode content;
- it does not delay a chunk to improve timing precision;
- it re-raises upstream errors rather than replacing them.

Measurement overhead must not become a new response transformation.

## Per-node timing is diagnostic, not semantic authority

Per-node timing can identify where current request-path time is spent, including relationship, scene, affect, intent, retrieval, context injection, token-budget, and backend-forward stages when those stages are active and timed.

Timing data may answer:

- which stage dominates pre-backend overhead;
- whether retrieval cost changes with store shape;
- whether optional stages are material to latency;
- whether backend time dominates local processing.

Timing data cannot answer by itself:

- whether a semantic stage is unnecessary;
- whether a safety check can be removed;
- whether a memory candidate limit should change;
- whether a timeout is acceptable;
- whether a degraded answer is semantically safe.

Those decisions require the owning architecture and evidence.

## Untimed is not zero

A missing timing value means the interval was not measured under the relevant instrumentation boundary.

It does not mean the stage consumed zero time.

Examples include:

- a stage disabled or skipped by its existing behavior;
- an event occurring after the earlier checkpoint was built;
- an external frontend/TTS interval outside RelayLM Core;
- a measurement path disabled because tracing is off.

Reports and dashboards must preserve null/unknown semantics instead of silently coercing them to zero.

## Content-free timing is a hard boundary

Latency telemetry does not need prompt, response, memory, scene, relationship, or internal candidate content.

Default timing artifacts therefore remain content-free and use only bounded values such as:

- durations;
- timestamps where explicitly governed;
- counts;
- booleans;
- fixed status/reason identifiers;
- schema/version identifiers;
- request correlation identity already allowed by the trace boundary.

Timing diagnostics must not contain:

- prompt or response text;
- memory bodies;
- scene/relationship content;
- raw exceptions or free-form error messages;
- backend payload bodies;
- SSE body content;
- TTS text/audio content;
- reversible content-derived fingerprints.

Performance observability must not become a shadow transcript store.

## Error timing remains content-free

A stream may finish normally, be closed, be cancelled, or fail upstream.

The timing layer may record a bounded error classification needed to interpret incomplete drain timing, but it does not log raw exception text or inspect content to invent more specific classifications.

If the observation layer cannot distinguish two causes without additional authority or content inspection, the metric stays coarse rather than guessing.

Measurement fidelity never justifies expanding the content exposure surface silently.

## Trace-disabled behavior remains cheap

When tracing/measurement is disabled, RelayLM should avoid unnecessary per-chunk observability work where the current design allows it.

Performance instrumentation must not impose a mandatory heavy observation path on deployments that have not enabled that observability.

Conversely, disabling trace does not change semantic behavior or waive safety checks. It changes measurement availability only.

## Offline benchmarks and live timings answer different questions

Offline synthetic benchmarks isolate bounded algorithmic/scaling behavior under controlled fixtures.

Live request timings observe the real assembled runtime under current configuration and backend conditions.

Neither substitutes for the other.

An offline retrieval benchmark can characterize local retrieval scaling without backend/network noise. A live timing trace can show whether retrieval is significant in an actual request.

Benchmark fixtures must remain isolated from production stores and must not become memory publication authority.

## Bench results are evidence, not automatic tuning commands

Observed p50/p95 or scaling plateaus can justify investigation and later bounded design work.

They do not automatically authorize:

- a larger or smaller candidate limit;
- ANN/vector-store adoption;
- bypassing lexical or structured filtering;
- disabling a semantic stage;
- a new timeout;
- degraded-mode activation;
- Secondary MEM fallback;
- scheduler priority changes.

Each such change is a separate responsibility-bearing transaction with its own safety and quality evidence.

## Latency optimization must preserve authority boundaries

The preferred optimization order is to remove avoidable work inside an owner's safe contract before removing the owner itself.

Examples of generally safer optimization classes include:

- eliminating duplicate computation;
- avoiding unnecessary I/O;
- using already-approved cached immutable projections where their freshness contract allows it;
- reducing serialization/diagnostic overhead;
- moving non-user-blocking work to an already-governed deferred path;
- improving algorithms without changing semantic outputs or authority;
- overlapping independent work only when dependencies and failure behavior remain explicit.

An optimization becomes an architecture change when it alters what is selected, skipped, delayed, persisted, or exposed.

## No latency win may weaken safety/privacy

A lower first-chunk time is not an acceptable optimization if it bypasses or races ahead of a required authority gate.

Latency work must not:

- expose internal RelayCTX candidate material;
- use private context before scene/disclosure gates complete;
- restore excluded client instruction/history authority;
- bypass current memory retrieval ownership;
- convert a dry-run or target-only result into actual apply;
- skip required validation because it is slow;
- speak output before the visible/internal safety boundary approves it;
- write durable state synchronously merely to avoid later reconstruction.

Safety and authority correctness are constraints on optimization, not optional dimensions in a latency tradeoff.

## Degradation requires an owning policy

Graceful degradation can reduce latency under load or uncertainty, but the performance subsystem does not invent degradation semantics.

A component may be skipped, reduced, or replaced only when its owning contract explicitly defines that behavior and the resulting authority remains safe.

The performance layer may provide evidence that a degradation path is worth designing or evaluating.

It does not convert a slow stage into an optional stage by measurement alone.

## Timeout choice is semantic when it changes output

A timeout is not merely a performance constant when expiration changes which evidence, memory, scene, tool, or response path is used.

Such a timeout belongs to the owner of the affected behavior, with performance evidence as an input.

Performance architecture may define measurement expectations around timeouts, but it does not own their semantic fallback.

A timeout failure must not create cross-family authority transfer.

## Scheduler priority is related but separate

The scheduler may influence when work executes, concurrency, and resource contention.

Performance observations can identify queueing or contention worth investigating.

The performance subsystem does not assign scheduler priority simply from elapsed time.

Scheduler changes must preserve ordering dependencies, single-writer constraints where applicable, bounded concurrency, and fail-closed behavior.

## Streaming can improve perceived latency without reducing total work

Streaming is valuable because the user can receive safe visible output before the entire response completes.

This can lower perceived latency even if total backend generation time is unchanged.

That benefit depends on preserving chunk-forwarding behavior and avoiding unnecessary buffering.

However, the first chunk must still pass all required output-safety boundaries. Perceived-latency optimization cannot justify emitting unsafe or semantically internal content earlier.

## Voice adds another perceived-latency chain

For realtime speech use, text first-chunk latency is only part of the experience.

A future complete measurement may distinguish:

```text
request start
  -> first safe visible text
  -> first speech-ready segment
  -> adapter delivery
  -> TTS synthesis start
  -> first playable audio
  -> playback completion
```

Current RelayLM Core owns only the upstream preparation boundary and does not execute TTS/audio.

Therefore current timing must not fabricate first-audio metrics from segmentation or transport-envelope readiness.

When concrete adapter execution ships, its timing needs a separately governed observation boundary with the same content-free discipline.

## Mobile perceived latency includes external factors

Mobile dogfooding may include latency outside RelayLM Core, such as:

- Wi-Fi/cellular transport;
- reverse proxy or tunnel overhead;
- browser/app rendering;
- frontend buffering;
- device scheduling;
- TTS provider/network latency;
- audio playback setup.

RelayLM traces can explain only the intervals they actually observe.

A user-visible delay must not automatically be attributed to RelayLM request-path work without correlated measurement.

## Correlation does not require content

Performance records can correlate phases of one request using an already-governed opaque request identity.

This permits comparison of early request timing and later stream-final timing without copying prompt/response content into the telemetry surface.

New correlation identifiers should not be introduced casually when an existing request identity already serves the purpose.

Correlation scope must remain bounded to the observability need.

## Measurement precision must be honest

Durations should use a monotonic clock where elapsed-time correctness matters.

Wall-clock timestamps can support event correlation when governed, but clock adjustments must not corrupt duration calculations.

Rounding, sampling, integer conversion, and trace-write timing should be described by the owning implementation when they materially affect interpretation.

Architecture-level claims should avoid precision that the measurement boundary cannot support.

## Performance regressions need comparable evidence

A useful regression comparison controls enough variables to make the result interpretable.

Depending on the question, that may include:

- same scenario/query set;
- same backend/model class;
- same route/profile and feature gates;
- same dataset/store shape;
- same warm/cold-cache assumptions;
- repeated runs rather than a single sample;
- p50/p95 or another explicitly stated distribution summary.

A single slow request can be an incident signal, but it is weak evidence for an architectural optimization by itself.

## Targets and budgets must be explicit, not inferred

This page does not invent a universal latency SLA or hard target.

If RelayLM adopts targets such as maximum pre-backend overhead, first-visible-chunk budgets, or first-audio goals, they must be recorded explicitly with:

- the measured boundary;
- the environment/profile;
- percentile/statistic;
- acceptable sample method;
- exclusions/unknowns;
- what action is authorized when the target is missed.

A dashboard threshold is not automatically an authority to skip work.

## Stable optimization decision flow

```text
measure a named boundary
  -> reproduce / characterize
  -> identify owning stage or external interval
  -> determine whether the issue is algorithmic, I/O, orchestration, backend, network, or presentation
  -> propose one bounded optimization under the owner's invariants
  -> validate semantic/safety equivalence or explicitly govern changed behavior
  -> re-measure the same boundary
```

This flow prevents latency work from becoming an unbounded excuse to alter unrelated semantics.

## Current measurement map

Conceptually, current instrumentation supports:

| Boundary | Current observation | Interpretation |
|---|---|---|
| RelayLM pre-backend nodes | LAT-1 per-node durations | request-path stage diagnostics |
| aggregate pre-backend overhead | LAT-1 timing summary | completed non-backend timed work |
| retrieval stage | LAT-1 retrieval duration + offline scaling bench | local retrieval cost/scaling evidence |
| backend stream open | LAT-1/LAT-2 carried observation | headers/stream-open latency, not stream completion |
| first assembled stream chunk | LAT-2 | runtime perceived first-chunk timing |
| stream completion | LAT-2 drain timing | full assembled stream drain |
| stream chunk count | LAT-2 | transport chunk count, not token count |
| first safe visible text | partially approximated by assembled safe stream boundary | must not be mislabeled beyond actual observation |
| first speech-ready segment | no canonical end-to-end timing claim yet | voice preparation can exist without execution timing |
| first audio/playback | external/not currently measured by RelayLM Core | requires future adapter observation |

Exact field names and schemas remain in the implementation handoffs/contracts rather than this architecture page.

## Stable invariants

- Perceived latency is a chain of named intervals, not one undifferentiated number.
- Measurement does not grant optimization, skip, timeout, or degradation authority.
- An earlier artifact never claims a later timing event.
- First chunk, first token, first safe visible text, and first audio are distinct concepts.
- Backend stream open, first chunk, and stream drain are distinct measurements.
- Missing/untimed values remain unknown/null rather than zero.
- Timing telemetry is content-free and never becomes a transcript or semantic store.
- Observability errors use bounded reason classes rather than raw exception/content leakage.
- Measurement wrappers do not buffer, reorder, decode, or delay content merely to improve telemetry.
- Offline benchmarks and live timings serve different purposes and neither is automatic tuning authority.
- Optimization preserves semantic, safety, privacy, and current-boundary ownership.
- Degradation and timeouts require the affected component's explicit policy.
- Scheduler decisions remain scheduler authority.
- Streaming may improve perceived latency without changing total generation time.
- Current RelayLM Core does not fabricate TTS/audio latency that it cannot observe.
- External network/frontend/device latency is not attributed to RelayLM without measurement.
- Correlation uses bounded opaque identity rather than content.
- Latency targets/SLOs must be explicit; none are inferred from current telemetry.
- Every optimization is re-measured against the same named boundary.

## Non-goals

This architecture does not define:

- an SLA/SLO or universal millisecond target;
- exact timing trace fields or schemas;
- exact benchmark CLI/query/store fixture definitions;
- search ranking, candidate limits, ANN/vector adoption, or retrieval semantics;
- component-specific timeout values;
- degradation ladders or skip policies;
- scheduler priorities or concurrency limits;
- backend/provider performance guarantees;
- network/tunnel/browser/mobile-device timing implementation;
- TTS provider/audio/avatar timing implementation;
- semantic response generation or output rewriting;
- durable performance telemetry retention policy beyond existing observability authority;
- repository-level implementation sequencing.

## Related architecture

- [RelayLM Pipeline Responsibilities](../pipeline-responsibilities.md)
- [Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [Runtime Scheduler](../runtime/scheduler.md)
- [LAT-1 Latency Measurement](../lat1_latency_measurement.md)
- [LAT-2 Mobile Perceived Latency](../lat2_mobile_perceived_latency.md)
- [Voice Streaming and TTS](../voice/streaming-and-tts.md)
- [Mobile Dogfood Observation](../../evaluation/mobile-dogfood-observation.md)
- [LAT-1 Retrieval Scaling](../../evaluation/lat1-retrieval-scaling.md)
