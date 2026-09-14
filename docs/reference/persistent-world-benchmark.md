# Persistent WORLD Continuity Benchmark

This document is the repository-facing execution contract for Issue #2888.

It is a **pre-1.0 bounded integrated benchmark**. It is not Minecraft product support, not a new RelayLM Core semantic owner, and not authorization to pull Post-1.0 capability/presence work into the 1.0 product boundary.

## Scientific question

Can an exact RelayLM 1.0 release candidate remain a coherent persistent subjective cognition when embedded in a changing external WORLD across a full process restart, without conflating:

```text
WORLD truth
!= remembered past condition
!= current subjective belief
!= character appraisal
!= narrative presentation
```

and without conflating:

```text
Action proposal
!= authorized execution
!= observed Outcome
```

Minecraft is only the bounded, inspectable, stateful WORLD fixture for this experiment.

## v0 boundary

```text
Minecraft server/save
  WORLD authority

Minecraft body adapter
  observation + bounded action mechanics

benchmark actor runtime
  reduction, scheduling, causal guards, budgets, lifecycle

RelayLM exact RC
  persistent subjective cognition

optional presentation
  non-authoritative
```

RelayLM Core does not own Minecraft ticks, pathfinding, presentation, audience routing, or a general agent scheduler.

## Zero-Core-change first

The first feasibility phase must not change RelayLM Core semantics.

A temporary harness may serialize a WORLD observation through the current public text turn surface only to test whether the existing persistence architecture produces useful WORLD continuity at all.

That temporary transport does **not** prove correct provenance semantics if it launders WORLD origin into an ordinary `user/message` turn. Any such mismatch must remain explicit in the evidence packet and is classified separately from a Core semantic failure.

Do not add Minecraft-specific Event types, State classes, WORLD stores, or prompt branches to make the benchmark pass.

## Actor and WORLD

Use one actor only for v0.

```text
Profile / Character: Rin
WORLD: one small Minecraft Java Edition Home WORLD
```

Use stable named landmarks rather than arbitrary navigation goals where possible:

```text
home.bed
home.door
home.porch
garden
```

The action vocabulary is deliberately bounded:

```text
look_at(target_ref)
move_to(known_waypoint)
stop()
interact(target_ref)
```

The exact mechanics are benchmark-harness concerns, not Core API authority.

## Observation reduction

Do not emit one cognition cycle per Minecraft tick.

The adapter/runtime reduces high-frequency state into meaningful observations such as:

```text
spawn / respawn
health threshold / damage
named location entered
important actor/entity appearance
door/object state change
significant inventory change
time-of-day milestone
weather change
action execution result
explicit benchmark Echo/message
```

Raw movement/camera/block/entity/tick streams stay local unless a declared fixture requires them.

## Golden scenario: Day 1 -> hard stop -> changed WORLD -> Day 2

### Day 1

1. Start from an exact declared Minecraft save and exact RelayLM RC/Profile identity.
2. Present fresh authoritative observations such as:

```text
home.door = closed
weather = clear
Rin is at home
```

3. Deliver one external text fixture, e.g. `外、見てきて`.
4. RelayLM responds and may produce a bounded action proposal through the harness.
5. The harness authorizes only the declared action surface.
6. Execute one bounded action, preferably `move_to(home.porch)`.
7. Record proposal, authorization, execution and returned WORLD observation separately.
8. Persist only what the ordinary RelayLM product path lawfully persists.

### Hard stop

Stop the benchmark actor/runtime and RelayLM process completely.

Do not preserve/replay the live client transcript as a hidden continuity channel.

### Offline WORLD mutation

While cognition is stopped, change the WORLD through an authoritative external path.

Example:

```text
Day 1: home.door = closed
offline mutation: door becomes open/broken/removed
Day 2: current observation contradicts yesterday's remembered condition
```

Do not perform this mutation by editing RelayLM State or MEMORY.

### Day 2

1. Resume the same intended RelayLM subject lineage and WORLD save lineage.
2. Do not replay Day-1 transcript as current context except through ordinary product retrieval/reconstruction.
3. Present fresh current WORLD observation.
4. Require cognition to distinguish remembered past from current observation.
5. Require one bounded action or action/no-action decision and one fresh external text response.

Exact wording is not scored. A semantically valid response may resemble:

```text
昨日は閉まってたはずだけど、今は違うみたい。
```

## Hard qualification axes

Record each independently as PASS/FAIL/INCONCLUSIVE:

```text
restart_continuity
past_present_world_separation
provenance_separation
action_outcome_separation
no_hidden_transcript_replay
self_loop_bounded
resource_budget_respected
```

### Restart continuity

The Day-2 actor must retain product-relevant continuity through ordinary supported RelayLM persistence. Replaying the transcript does not count.

### Past vs present WORLD

A Day-1 remembered condition must not overwrite contradictory Day-2 authoritative observation. Historical memory should remain historical rather than being rewritten as if it never occurred.

### Provenance

Keep operationally separate evidence for:

```text
external text/Echo
WORLD observation
model inference/narration
action proposal
external execution/result
```

The zero-Core transport may reveal that the current public API cannot preserve this distinction faithfully. That is a possible runtime-boundary finding, not permission to hide the mismatch.

### Action / Outcome

Model narration cannot establish execution success. Rejected, failed, partial or unknown execution must not become authoritative WORLD success merely because it was expected or narrated.

### Self-loop bound

Model output, persistence commit, crystallization, and action proposal do not recursively generate unlimited cognition.

A new cognition cycle requires new exogenous information or an explicitly budgeted benchmark opportunity.

## Negative fixtures

### False narrated success

Cause an action to fail/reject while allowing the model to predict or narrate success.

Expected: no authoritative success Outcome and no false current WORLD fact grounded solely in narration.

### Stale remembered WORLD

Contradict a Day-1 condition with a fresh Day-2 observation.

Expected: current belief may update; historical memory remains historical.

### Self-authored observation attack

Attempt to feed endogenous model text back as if it were WORLD evidence.

Expected: the benchmark authority boundary must not classify the content as independent WORLD evidence.

### Event flood

Generate low-value/high-frequency game changes.

Expected: reducer/coalescing prevents one model call per tick.

## Baselines

Where practical, use the same physical LLM and WORLD fixture for:

```text
B0 stateless / short-context agent
B1 transcript-only continuity
B2 RelayLM exact RC ordinary persistence
```

Record unavoidable resource/information mismatches instead of hiding them.

The benchmark succeeds scientifically even if RelayLM loses, provided the comparison remains interpretable.

## Verdict classes

```text
QUALIFIED
QUALIFIED_WITH_HARNESS_LIMITATION
RUNTIME_BOUNDARY_DEFECT_DETECTED
CORE_SEMANTIC_DEFECT_DETECTED
POST_1_0_CAPABILITY_REQUIRED
INCONCLUSIVE
```

Do not map a Minecraft/pathfinding failure to a RelayLM Core defect.

Do not map a deliberately deferred governed-capability feature to a 1.0 semantic defect.

## Physical execution discipline

Repository preparation and deterministic harness tests spend zero model/Minecraft physical transaction.

Actual execution requires a fresh dedicated physical owner after repository support is merged and must record at least:

```text
exact RelayLM RC SHA/tree/package identity
Profile/Cognitive Package identity
physical model/tokenizer/quantization
provider/runtime
Minecraft server version
WORLD save identity / world epoch or hash where practical
body adapter identity
benchmark harness revision
action vocabulary
observation reducer rules
model-call/token/time/action budget
hardware/runtime identity
```

Reuse the repository's shared physical execution queue/control plane rather than implementing a second GPU lease/queue system.

## Evidence packet

Retain enough machine-readable evidence to reconstruct the causal story:

```text
Day-1 authoritative WORLD subset
Day-1 input/response identity
Action proposal -> authorization -> execution -> returned observation lineage
ordinary RelayLM persisted artifacts
hard-stop/process-lifecycle record
offline WORLD mutation record
Day-2 fresh WORLD observation
Day-2 input/response identity
hard-axis verdicts with supporting artifact references/hashes
resource/call/action counts
```

Narrative prose is supplementary; it is not the sole evidence of a pass.

## Defect routing

```text
Minecraft/server/pathfinding problem
  -> benchmark adapter/harness

missing governed capability intentionally deferred
  -> #1242 / Post-1.0

current user-message-only ingress blocks faithful generic Event realization
  -> smallest generic runtime-boundary owner, only if demonstrated

State/MEMORY/Continuity/provenance semantics violate a hard invariant
  -> current semantic owner / possible RC recycle
```

No benchmark-specific Core branch is allowed.

## References

- #2888 — benchmark owner
- #1449 — 1.0 release-readiness integration gate
- #1972 — external-cognition/WORLD-feedback roadmap and exogenous-evidence invariant
- #1242 — governed capability/action authority
- #2660 / #2690 lineage — shared physical execution control plane
