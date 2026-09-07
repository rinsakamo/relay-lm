# RelayLM 2.0 — #2187 R2 Cognitive Work preregistration

This is the repository authority for the R2 heterogeneous same-model Cognitive Work campaign designed by #2279 under parent #2187.

```text
claim_status = R2_PREREGISTERED_DESIGN_ONLY
physical R2 = NOT AUTHORIZED
historical R1 = INCOMPLETE
architecture consequence = NONE
```

The package freezes the experiment before any R2 provider output exists. It does not retry or rewrite R1 and does not authorize a production scheduler.

## Scientific question

Holding physical model/runtime identity, ordinary task information, legal operation surface, hard feasibility constraints, and evaluator target fixed, does adaptive allocation improve attained capability enough to repay its own metareasoning cost compared with fixed and cheap heuristic allocation?

```text
A0 = fixed THINK
A1 = cheap deterministic availability heuristic
A2 = actual-model adaptive allocator; allocator overhead fully charged
A3 = evaluator-only oracle over a quarantined shared operation-result bank
```

A3 is never deployable cognition. Hidden evaluator data, oracle choices, and bank results never enter A0/A1/A2 prompts, State, Structure, Evidence, or another canonical cognitive surface.

## R1 boundary

The first R1 physical transaction completed all eight provider exchanges but remained `INCOMPLETE` because A2 used 572 aggregate input tokens against a synthetic 500-token fixture ceiling. #2278 verified the transcript and classified the only material stop as `SMOKE_ENVELOPE_CALIBRATION_DEFECT`.

R2 therefore does not inherit an outcome-fitted aggregate token ceiling. It separates:

```text
hard feasibility / protocol constraints
  context capacity
  declared provider-call count
  legal operation count
  external-unit bounds
  retry prohibition

measured natural cost
  input tokens
  output tokens
  calls
  retrieval units
  observation units
  allocator overhead
  latency when reliably observable
```

Aggregate input/output tokens are measured, not used as a hard campaign gate. A future token gate would require an independent tokenizer/context derivation frozen before outputs and cannot be selected just above the historical 572.

## Frozen workload

The primary R2 suite is exactly:

```text
5 hidden regimes × 8 tasks = 40 tasks
```

Hidden regime labels are evaluator-only.

### EASY_SATURATED

A small exact arithmetic task whose public prompt contains all required information. Extra work should have little marginal value.

### DEPTH_BENEFICIAL

A deterministic multi-step arithmetic transformation. No external packet exists; one THINK revision may repair a base error.

### RETRIEVAL_BENEFICIAL

A frozen lookup key is public but its mapped value is omitted. One retrieval packet contains the missing record and remains hidden until RETRIEVE is selected.

### OBSERVATION_BENEFICIAL

A current sensor state is omitted from the public prompt. One observation packet exposes the frozen current state and remains hidden until OBSERVE is selected.

### UNCERTAINTY_TRAP

The public evidence is genuinely insufficient, no external packet exists, and the correct bounded answer is `UNKNOWN`. Extra reasoning can waste cost or hallucinate certainty.

A primary task never exposes both retrieval and observation packets.

## Seed and task identity

The concrete suite is derived only after this package merges:

```text
root_seed = SHA256("relaylm2-2187-r2" || exact merged PR commit SHA)
```

Each regime/task RNG is independently derived from `root_seed`, hidden regime, and task index. Deployable task IDs are opaque hashes derived from the same root and do not encode regime name or regime index.

Therefore no seed or task set can be selected after seeing model outputs. A future physical transaction must record the exact merged commit, root seed, generated preregistration digest, and fresh physical binding before its first provider request.

## Deployable information boundary

Before an external operation is selected, deployable messages may contain only:

```text
opaque task_id
public prompt
retrieval_available
observation_available
shared base answer where relevant
legal operation names/descriptions
```

They may not contain:

```text
hidden regime
expected answer as an evaluator field
retrieval packet before RETRIEVE
observation packet before OBSERVE
operation-bank results
A3 choice
ideal operation
```

The expected answer and hidden regime are offline evaluator data only.

## Frozen operation surface

```text
ZERO
  keep the shared base answer; no additional task-work model call

THINK
  one revision call using only already-public information

RETRIEVE
  reveal one frozen retrieval packet, then one revision call

OBSERVE
  reveal one frozen observation packet, then one revision call
```

These are experiment operations, not persistent ontology primitives.

## Frozen policies

### A0 — FIXED

```text
always THINK
```

### A1 — CHEAP_HEURISTIC

```text
if retrieval_available:
    RETRIEVE
elif observation_available:
    OBSERVE
else:
    ZERO
```

A1 buys no allocator-model call.

### A2 — ADAPTIVE

A2 buys exactly one allocator-model call per task. It sees only the public task mapping, shared base answer, legal operations, and external-availability booleans. Its allocator calls, tokens, and reliably observed latency are charged to A2.

### A3 — ORACLE

A3 is computed offline after the shared operation-result bank exists. It selects a correct legal outcome if one exists and never invents a success when none exists.

Resource vectors remain heterogeneous. A3 therefore does **not** lexicographically scalarize `ResourceVector` dimensions. Among correct candidates it first removes candidates Pareto-dominated by another correct candidate. If multiple incomparable candidates remain on the Pareto frontier, a preregistered deterministic operation priority resolves the non-scientific tie:

```text
ZERO < THINK < RETRIEVE < OBSERVE
```

This tie-break is only a deterministic oracle-selection convention. It is not a universal resource currency or utility function.

## Shared bank and frozen physical call order

Each task uses one shared base completion plus one physical completion for every legal non-ZERO operation. A0/A1/A2 are then evaluated counterfactually against this same bank, preventing different stochastic draws from masquerading as allocation effects.

The canonical physical order per task is frozen as:

```text
BASE
  → A2_ALLOCATE
  → BANK:THINK
  → BANK:RETRIEVE   if retrieval is available
  → BANK:OBSERVE    if observation is available
```

A2 therefore commits its choice before any non-public bank result exists. A future host must execute this plan exactly; it cannot precompute hidden bank outcomes and merely promise not to expose them.

Physical evaluator cost and counterfactual treatment cost are separate ledgers:

```text
physical cost
  every provider call actually issued for base, A2 decision, and bank construction

treatment cost
  shared base
  + selected operation work
  + A2 allocator overhead for A2 only
```

The shared base cost is charged to every deployable arm.

## Structural resource contract

The frozen suite structurally requires:

```text
40 BASE
40 A2_ALLOCATE
40 BANK:THINK
8 BANK:RETRIEVE
8 BANK:OBSERVE
```

Hence:

```text
operation-bank/base provider-call max = 96
A2 allocator-call max                 = 40
physical provider-call max            = 136
```

No automatic or semantic retry exists.

The common hard counterfactual treatment-call ceiling is derived from the most expensive legal deployable path rather than observed R1 usage:

```text
40 × (base + allocator + at most one selected work call) = 120 calls
```

A0/A1 naturally spend fewer calls; they do not receive free work to equalize spend. Actual spend is part of the result.

Other structural limits:

```text
retrieval units per arm   <= 8
observation units per arm <= 8
context limit             = 8192
aggregate input tokens    = measured, no hard ceiling
aggregate output tokens   = measured, no hard ceiling
automatic retry           = false
semantic retry            = false
```

## Response protocol

Answer calls must return exactly:

```json
{"answer":"..."}
```

Allocator calls must return exactly:

```json
{"operation":"ZERO|THINK|RETRIEVE|OBSERVE"}
```

The repository parser rejects duplicate members, extra keys, empty answers, and operations illegal for that exact task. Provider failure, binding drift, undeclared calls, and retry paths must fail closed in the later physical host.

No LLM judge is required; task answers are exact-evaluator friendly.

## Measurements

Report aggregate and per-regime vectors for at least:

```text
exact task correctness
success count
A2 - A0 paired correctness difference
A2 - A1 paired correctness difference
A3 - A0 oracle headroom
A2 regret vs A3
A1 regret vs A3
model calls
input tokens
output tokens
retrieval units
observation units
allocator-only calls/tokens
latency where reliable
wasted work on EASY_SATURATED / UNCERTAINTY_TRAP
missed useful work on DEPTH / RETRIEVAL / OBSERVATION regimes
operation-selection confusion vs A3
protocol-invalid and hard-failure counts
```

There is no single Intelligence score and no universal scalar resource currency.

## Frozen statistical rules

The task is the paired unit. Exact counts and effect sizes are primary.

For A2 vs A0 and A2 vs A1:

```text
one-sided exact paired sign/binomial test on discordant outcomes
alpha = 0.05
```

The direction is frozen because the preregistered hypotheses are `A2 > A0` and `A2 > A1`.

Also report a paired bootstrap interval for accuracy difference:

```text
10,000 resamples
95% interval
bootstrap RNG deterministically derived from frozen campaign identity
```

No test, threshold, or favorable regime subset may be selected after results.

## Frozen interpretation categories

A material task gain is frozen at 4/40. A1 is treated as essentially at the oracle accuracy frontier when `A3 - A1 <= 2/40`.

Oracle headroom is measured against A0 fixed allocation, preserving three distinct questions:

```text
A3 - A0
  does allocation have useful headroom at all?

A3 - A1
  does the cheap heuristic already capture that headroom?

A2 vs A0/A1
  does the adaptive allocator capture enough headroom to justify itself?
```

### INCONCLUSIVE

Any incomplete resource accounting, hard-constraint violation, or protocol-invalid result blocks a positive scientific category.

### NO_ORACLE_HEADROOM

```text
A3 - A0 < 4 tasks
```

The campaign does not expose enough allocation headroom to evaluate adaptive metareasoning meaningfully.

### ADAPTIVE_SIGNAL

All must hold:

```text
A2 - A0 >= 4 tasks
A2 - A1 >= 4 tasks
one-sided paired p(A2 > A0) <= 0.05
one-sided paired p(A2 > A1) <= 0.05
resource accounting complete
hard violations = 0
protocol invalid = 0
```

This remains only an R2 constituent signal and does not authorize production scheduling.

### HEURISTIC_SUFFICIENT

Oracle headroom over A0 is material, A2 does not meet `ADAPTIVE_SIGNAL`, and:

```text
A3 - A1 <= 2 tasks
```

The cheap heuristic captures essentially all observed accuracy headroom.

### ALLOCATOR_FAILURE

Oracle headroom over A0 is material, neither `ADAPTIVE_SIGNAL` nor `HEURISTIC_SUFFICIENT` holds, and A2 fails to capture enough available headroom under the frozen rules.

## Deterministic admission before physical work

Tests must establish before any physical R2 authorization:

```text
40 unique tasks; exactly 8 per hidden regime
suite deterministic from immutable merged-commit identity
opaque task IDs do not encode regime
same generated suite used by all arms
hidden regime absent from deployable messages
expected answer absent as a deployable field
retrieval packet hidden until RETRIEVE
observation packet hidden until OBSERVE
A3/bank data absent from deployable messages
A0/A1 deterministic
A2 allocation occurs before non-public bank generation
A2 allocator overhead charged
A1 has no allocator call
ZERO has no task-work call
shared base charged to every arm
strict JSON rejects duplicate/extra fields and illegal operations
A3 uses Pareto dominance, not hidden scalarization
A3 tie-break deterministic on incomparable frontier candidates
136-call physical maximum structurally derived
120-call common treatment ceiling structurally derived
aggregate token ceilings absent
```

The later physical host must additionally prove exact repository/binding identity, truthful provider-attempt accounting, and absence of retry/fallback paths.

## Physical identity boundary

A later separately authorized R2 host should preserve the already-qualified #2187 physical lineage unless current authority requires otherwise. Every physical transaction must nevertheless reacquire fresh repository, model, runtime, hardware, tokenizer, template, context, decoding, reasoning, endpoint, and artifact authority.

Historical R0.5/R1 values are anchors only. No model, reasoning mode, sampling setting, prompt, generator, seed, policy, threshold, or budget rule may change because R1 or later R2 outputs suggest a favorable choice.

## Next gate

#2279 is complete only after this preregistration module, tests, authority declaration, and this document merge into `v2`.

After merge:

```text
repository-side R2 preregistration = complete
physical R2 execution = still NOT AUTHORIZED
```

A separate fresh reconciliation must package and review a fail-closed R2 physical host before any R2 provider request.

> **Metacognition must pay rent.**

> **Oracle headroom tells us whether allocation matters; A2 tells us whether our allocator matters.**

> **Do not give the adaptive arm free information and call it intelligence.**

> **Do not fit tomorrow's scientific budget to yesterday's overflow.**
