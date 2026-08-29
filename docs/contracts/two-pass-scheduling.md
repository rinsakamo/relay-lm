# Two-pass response-first scheduling contract

Status: Core 1.0 provider-generation scheduling boundary owned by #1533 / #1978.

This contract defines only how response-first Pass 1 / Pass 2 work is ordered when a newer user turn arrives. Pass semantics, State/Continuity validation and provider wire details remain in their existing owners.

## Response-first remains the product contract

A successful Pass 1 response is committed and may be returned before Pass 2 finishes:

```text
turn N Pass 1
  -> visible response committed
  -> turn-bound Pass 2 scheduled
  -> response may return while Pass 2 remains pending
```

Pass 2 failure, cancellation or staleness never retracts an already-valid Pass 1 response.

## Supersession and single-flight local provider work

A newly admitted user turn semantically supersedes every still-pending extraction from an older cognition execution revision.

Before the newer turn begins provider generation, RelayLM:

1. advances the execution revision so older extraction results can no longer be current;
2. cancels every still-pending older local Pass 2 task;
3. joins those cancelled tasks so their local provider request coroutines have terminated;
4. only then prepares and starts the newer turn's Pass 1 provider generation.

Conceptually:

```text
old Pass 2 pending
      |
new turn admitted
      -> old revision becomes stale
      -> cancel + join old Pass 2 local task
      -> new Pass 1 provider request may start
```

This prevents RelayLM itself from accumulating overlapping obsolete Pass 2 requests merely because response-first execution backgrounds extraction.

The guarantee is a RelayLM local-request scheduling guarantee. A remote backend may have its own cancellation/disconnect implementation and physical scheduler. #1446 must not infer a stronger GPU-sequence guarantee than the configured backend/launcher can actually enforce. Physical OOM/KV sizing may additionally constrain backend concurrency (for example, a managed runtime sequence limit) before claiming a one-sequence physical allocation.

## Cancelled extraction disposition

Cancellation caused by a newer execution revision is reported through the existing semantic disposition as:

```text
TwoPassExtractionStatus.STALE
```

It is not a provider failure and carries no candidate decisions or authority mutation.

Cancellation for another reason while the extraction is still the current revision remains normal asyncio cancellation and is not silently reclassified as stale. This preserves process shutdown/caller cancellation semantics.

## Authority safety

A superseded/cancelled Pass 2:

- never commits State;
- never commits Continuity;
- never changes the newer turn's authority;
- leaves the older turn's already-persisted user and assistant Events intact;
- may retain only completion metadata that was already validly obtained before the stale boundary.

The existing revision/State/Continuity stale checks remain in force even after the proactive cancellation boundary. Cancellation is a resource/scheduling optimization plus a stronger no-overlap invariant, not a replacement for deterministic authority validation.

## Buffered / streaming parity

Buffered and streaming Pass 1 use the same supersession sequence:

```text
reserve newer revision
-> cancel + join obsolete Pass 2
-> begin newer Pass 1 provider generation
```

Streaming therefore does not gain a second concurrency policy.

## Relationship to Calibration and runtime allocation

#1388 may treat this contract as evidence that RelayLM does not intentionally keep obsolete Pass 2 local provider requests alive across newer turns.

It does not by itself prove physical GPU concurrency equals one. #1446 owns translation from calibrated cognitive demand to a physical runtime allocation and must bind any physical sequence/concurrency limit truthfully to the managed backend before reclaiming KV VRAM on that assumption.

## Non-goals

- waiting for every Pass 2 before returning Pass 1;
- group-chat or multi-agent scheduling;
- throughput optimization;
- changing Pass 2 semantic output;
- changing stale State/Continuity validation;
- choosing FastCal numeric values;
- defining backend-specific GPU scheduler behavior.

## Principle

> Return Pass 1 promptly, but do not spend provider work on an extraction that a newer turn has already made non-authoritative.
