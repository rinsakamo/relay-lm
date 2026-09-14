# Persistent WORLD Continuity Benchmark

This document is the repository-facing execution and evidence contract for
Issue #2888.

It is a **pre-1.0 bounded integrated benchmark**. It is not Minecraft product
support, not a new RelayLM Core semantic owner, and not authorization to pull
Post-1.0 capability/presence work into the RelayLM 1.0 product boundary.

## Scientific question

Can an exact RelayLM 1.0 release candidate remain one coherent persistent
subjective cognition while embedded in a changing external WORLD across a hard
process restart, without conflating:

```text
WORLD truth
!= remembered past condition
!= current subjective belief
!= character appraisal
!= narrative presentation

Action proposal
!= authorization
!= execution
!= observed Outcome

model output
!= exogenous evidence
```

Minecraft is only the bounded, inspectable, stateful WORLD fixture.

## Responsibility boundary

```text
Minecraft server/save
  = WORLD authority

WORLD/body adapter
  = observation producer + bounded action mechanics

WORLD fixture operator
  = administrative benchmark mutation authority

benchmark actor runtime
  = reduction, scheduling, causal guards, budgets, lifecycle

RelayLM exact RC
  = persistent subjective cognition

optional presentation
  = non-authoritative
```

The body adapter does not become WORLD authority merely because it reports a
server observation. The operator mutation path is fixture authority, not an
actor capability. RelayLM Core does not own Minecraft ticks, pathfinding,
presentation, audience routing, or a general agent scheduler.

## Zero-Core-change first

The feasibility phase must not change RelayLM Core semantics.

A temporary harness may serialize a WORLD observation through the existing
public text-turn surface to test whether the existing persistence architecture
has useful WORLD continuity. That transport is explicitly lossy:

```text
transport.mode = public_text_turn
transport.preserves_logical_origin = false
```

Such a packet can never claim `provenance_separation = PASS`.

If useful continuity is demonstrated but the public user-message surface is the
only remaining blocker to faithful Event origin, route that finding to a
separate smallest generic runtime-boundary owner. Do not add Minecraft-specific
Event types, State classes, WORLD stores, or prompt branches.

## Benchmark actor and WORLD

Use one actor for v0:

```text
Profile / Character: Rin
WORLD: one small Minecraft Java Edition Home WORLD
```

Use stable harness-local names rather than arbitrary navigation goals, for
example:

```text
home.bed
home.door
home.porch
home.garden
```

Keep the action vocabulary deliberately bounded:

```text
look_at(target_ref)
move_to(known_waypoint)
stop()
interact(target_ref)
```

Exact movement mechanics are benchmark-harness concerns, not Core API
authority. Pathfinding competence is not a qualification axis.

## Observation reduction

Never invoke cognition once per Minecraft tick. Reduce high-frequency state to
meaningful events such as spawn/respawn, health thresholds, named-location
entry, material object-state changes, significant inventory changes,
time/weather milestones, authoritative action results, and explicitly selected
external messages.

Raw movement, camera, block, entity, and tick streams stay local unless a
frozen fixture requires them.

## Golden scenario: Day 1 -> hard stop -> changed WORLD -> Day 2

### Day 1

1. Start from a declared immutable WORLD fixture identity and exact RelayLM
   RC/Profile identity.
2. Capture an authoritative current WORLD fact, for example:

   ```text
   world_id = home-world
   world_epoch = epoch-0
   fact_key = home.door.block
   value = oak_door
   ```

3. Provide the observation to RelayLM through the declared transport.
4. Optionally include one external-message/Echo fixture when social-input
   coexistence is part of the condition.
5. Record RelayLM input/output separately from WORLD evidence.
6. Record one bounded action proposal, deterministic authorization, external
   execution, and authoritative Outcome as separate records.
7. Retain an ordinary RelayLM persistence snapshot for the same subject lineage.

### Hard stop

Stop the declared cognition/body components completely. A citable Qualification
must stop and later restart at least:

```text
relaylm
actor_runtime
body_adapter
```

The Minecraft server may remain alive when it is the cleanest way to preserve
WORLD authority. Do not replay the live client transcript as a hidden
continuity channel.

### Offline WORLD mutation

While the declared cognition/body components are stopped, mutate the same
WORLD fact through explicit fixture/operator authority, for example:

```text
world_id = home-world
fact_key = home.door.block
before: epoch-0 / oak_door
after:  epoch-1 / air
```

The mutation must not be produced by editing RelayLM State/MEMORY and must not
be represented as an actor action.

### Day 2

1. Restart the same intended RelayLM subject lineage and same WORLD fixture
   lineage.
2. Reconstruct ordinary supported cognition without hidden transcript replay.
3. Capture the same fact key from the fresh WORLD epoch.
4. Require the hard-axis adjudication to distinguish Day-1 remembered state
   from Day-2 current observation.
5. Produce fresh RelayLM input/output under a bounded resource budget.

Exact natural-language wording is not scored by the deterministic validator.
Semantic verdicts remain owner adjudications constrained by retained evidence.

## Evidence schema v2

`tools/persistent_world_evidence.py` accepts only schema version 2. Version 1
packets are not silently reinterpreted.

The packet has exact top-level fields:

```text
schema_version
run
identities
transport
budget
counts
records
axes
```

Unknown controlled-schema fields fail closed instead of being discarded before
fingerprinting. Open metadata/payload content that is permitted by the schema
is retained in the normalized packet and therefore remains fingerprint-bound.

### Run class is intrinsic

Every packet declares exactly one run class:

```text
EXPLORATORY_NON_CITABLE
QUALIFICATION
```

Exploratory runs are permanently:

```text
citable = false
qualification_authority = false
execution_frozen = false
```

A Qualification requires:

```text
citable = true
qualification_authority = true
execution_frozen = true
attempt = 1
```

A rehearsal artifact has no schema-level promotion path into Qualification.
Changing the run class/condition creates a different fingerprint and must be a
new physical transaction under fresh authority.

### Frozen identities

A Qualification packet requires non-null identities for:

```text
RelayLM exact artifact
Profile/Cognitive Package
immutable WORLD fixture/baseline
benchmark harness
physical model
governed provider boundary
model runtime/server
hardware/runtime host
Minecraft server artifact/version
body adapter artifact/version
```

Exploratory WORLD-plumbing trials may omit RelayLM/model identities when those
components were genuinely not used, but still require WORLD fixture, harness,
Minecraft server, and body adapter identities.

The top-level WORLD fixture artifact identifies the immutable starting fixture.
Mutable Day-1/Day-2 state is represented by fact-level records and WORLD epochs,
not by pretending a live ticking world directory has one stable hash.

### Producer origin != authority domain

Each record carries both:

```text
provenance.channel
provenance.authority_domain
```

For example:

```text
world_observation:
  channel = world_adapter
  authority_domain = minecraft_server

world_mutation:
  channel = world_fixture_operator
  authority_domain = minecraft_server

model_output:
  channel = relaylm
  authority_domain = relaylm_inference

action_authorization:
  channel = benchmark_harness
  authority_domain = benchmark_policy
```

A string label alone cannot convert endogenous model output into WORLD evidence.

### Causal lineage

Records are strictly sequence ordered. Important linear chains are explicit:

```text
exogenous observation/message OR budgeted benchmark opportunity
  -> relay_input
  -> model_output
  -> action_proposal
  -> action_authorization
  -> action_execution
  -> world_outcome
```

A rejected authorization cannot have an execution child. A PASS action axis
must cite one complete single chain; mixing records from unrelated chains does
not count.

Every cognition input requires new exogenous information or an explicitly
budgeted benchmark opportunity. Model output, persistence commits, and action
proposals cannot recursively create fresh cognition by themselves.

### Restart subject lineage

`persistence_snapshot` and Day-2 `context_reconstruction` identify both the
Profile and one `subject_lineage_id`. If both are present, the lineage must be
identical across the restart.

A Day-2 context reconstruction also declares whether transcript replay occurred.
`no_hidden_transcript_replay = PASS` requires both the packet count and cited
Day-2 reconstruction to say `false`.

### WORLD fact change

`past_present_world_separation = PASS` requires evidence of one exact chain:

```text
Day-1 world_observation(world_id, fact_key, before_value, before_epoch)
  -> offline world_mutation(same world_id/fact_key, before -> after)
  -> Day-2 world_observation(same world_id/fact_key, after_value, after_epoch)
  + Day-2 model_output evidence used by semantic adjudication
```

The mutation must change both declared epoch and fact value.

### Resource evidence

The frozen budget includes at least:

```text
model calls
cognition cycles
actions
reduced events
total tokens
wall-clock milliseconds
```

Deterministically derivable counts are cross-checked against retained records.
A resource-budget PASS also requires a retained `resource_receipt` whose
fingerprinted payload matches the packet counts. This does not magically
authenticate the physical runtime; the physical owner must independently
retain the referenced runtime/log receipt.

## Hard qualification axes

Record each independently as `PASS`, `FAIL`, or `INCONCLUSIVE`:

```text
restart_continuity
past_present_world_separation
provenance_separation
action_outcome_separation
no_hidden_transcript_replay
self_loop_bounded
resource_budget_respected
```

The validator constrains what evidence may support PASS; it does **not** infer
natural-language semantic correctness from prose.

A packet is reported as `qualification_eligible=true` only when it is a
`QUALIFICATION` packet and all hard axes are PASS. This is an evidence-structure
eligibility result, not an automatic release decision.

## Structural validation is not artifact authentication

The deterministic validator proves only that the declared packet is
well-formed, fingerprinted, causally admissible, internally consistent, and
meets the hard-axis evidence-shape rules.

It does **not** by itself prove that:

- a supplied hash really came from the claimed external server/runtime;
- a Minecraft observation was physically truthful;
- a model response semantically expressed the claimed distinction;
- a resource receipt was generated by the claimed process;
- an operator did not omit an unrecorded external channel.

Therefore citable Qualification additionally requires the physical owner to
capture and independently verify the external artifacts/receipts referenced by
the packet, under the owner's fresh execution-freeze contract. Narrative prose
alone is never evidence.

## Negative/adversarial fixtures

At minimum retain deterministic or physical negatives for:

- false narrated action success;
- stale remembered WORLD vs fresh contradictory observation;
- endogenous text relabelled as WORLD evidence;
- event flood / one-call-per-tick pressure;
- hidden transcript replay;
- cross-chain action evidence mixing;
- resource/count under-reporting;
- rehearsal-to-Qualification run-class laundering.

## Baselines and Echo

The core WORLD-continuity qualification does not require an audience/Echo input.
An Echo fixture may be added when testing coexistence of social input and WORLD
input; it must not become a confounding blocker for the core WORLD invariant.

Matched B0/B1/B2 baselines are required before making a comparative claim such
as “RelayLM is better than transcript-only/stateless continuity.” They are not
required merely to determine whether RelayLM itself preserves the hard WORLD
invariants.

## Verdict classes and defect routing

Human/scientific reconciliation may classify the result as:

```text
QUALIFIED
QUALIFIED_WITH_HARNESS_LIMITATION
RUNTIME_BOUNDARY_DEFECT_DETECTED
CORE_SEMANTIC_DEFECT_DETECTED
POST_1_0_CAPABILITY_REQUIRED
INCONCLUSIVE
```

Do not map Minecraft navigation/server failure to a Core defect. Do not map a
deliberately deferred governed capability to a 1.0 semantic defect. If the
current user-message-only ingress is the demonstrated generic blocker, create a
small generic runtime-boundary owner. If existing State/MEMORY/Continuity
semantics themselves create false WORLD truth or break supported restart
continuity, route to the current semantic owner and recycle the RC when the
release gate requires it.

## Physical execution discipline

Repository preparation spends zero Minecraft/model transaction. Actual
execution requires a fresh dedicated physical owner. The later owner reacquires
and freezes current repository/RC/package identity, WORLD fixture, Minecraft
server/body adapter, model/provider/runtime/hardware, budgets, ports/listeners,
process ownership, and the exact evidence schema immediately before execution.

Reuse current shared RelayLM physical-control surfaces where they actually own
the resource. Do not imply that the llama.cpp GPU queue owns Minecraft/Java/Node
process semantics; those processes need their own explicit owner-scoped
lifecycle and cleanup.

For unknown Minecraft mechanics, use LAB3 rehearsal first. Exploratory output
remains non-citable forever; after the procedure is known and cleaned up, prove
it once again under a separate fresh Qualification owner.

## References

- #2888 — Persistent WORLD benchmark owner
- #2894 — deterministic benchmark/evidence owner
- #2896 — non-citable Minecraft LAB3 rehearsal owner
- #1449 — RelayLM 1.0 release-readiness integration gate
- #1972 — external-cognition/WORLD-feedback roadmap
- #1242 — governed capability/action authority
- #2660 / #2690 lineage — shared physical execution control plane
