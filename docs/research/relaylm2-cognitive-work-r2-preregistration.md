# RelayLM 2.0 — #2187 R2 Cognitive Work preregistration

This document is the repository authority for the R2 heterogeneous actual-model campaign design owned by #2187 and packaged by #2279.

R2 is not physically authorized by this document. The package freezes the experiment before any R2 provider output exists.

```text
claim_status = R2_PREREGISTERED_DESIGN_ONLY
physical R2  = NOT AUTHORIZED
R1 status    = INCOMPLETE, preserved historically
architecture consequence = NONE
```

## Scientific question

Holding one physical model/runtime identity, ordinary task information, legal operation surface, hard feasibility constraints, and evaluator target fixed, does an adaptive allocator improve attained capability enough to justify its own metareasoning overhead compared with fixed and cheap heuristic allocation?

The arms are:

```text
A0 — fixed THINK
A1 — cheap deterministic availability heuristic
A2 — actual-model adaptive allocator; allocator cost fully charged
A3 — evaluator-only oracle over the frozen operation-result bank
```

A3 is not deployable cognition. Its information never enters A0/A1/A2 messages, State, Structure, Evidence, or another canonical cognitive surface.

## Why R2 does not inherit the R1 token ceiling

The first R1 physical transaction completed all eight provider exchanges but remained `INCOMPLETE` because A2 consumed 572 aggregate input tokens against a synthetic 500-token fixture ceiling. #2278 verified that this was the only material stop and classified it as `SMOKE_ENVELOPE_CALIBRATION_DEFECT`.

R2 therefore separates:

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

There is no aggregate input- or output-token feasibility ceiling in the R2 preregistration. Tokens remain measured resource dimensions. A later hard token ceiling would require a new independent tokenizer/context derivation frozen before outputs; it may not be selected just above the historical 572.

## Frozen workload

R2 contains exactly:

```text
5 hidden regimes × 8 tasks = 40 tasks
```

The regimes are evaluator-only labels.

### EASY_SATURATED

The public prompt contains all information needed for a small exact arithmetic answer. Extra work is expected to have little marginal value.

### DEPTH_BENEFICIAL

The public prompt contains a multi-step deterministic arithmetic transformation. No external packet is available. A second revision pass can repair a base error without receiving new information.

### RETRIEVAL_BENEFICIAL

The public prompt names a frozen lookup key but omits the mapped value. One retrieval packet contains the missing record. The packet is hidden until `RETRIEVE` is selected.

### OBSERVATION_BENEFICIAL

The answer depends on a frozen current sensor state omitted from the public prompt. One observation packet exposes that state. The packet is hidden until `OBSERVE` is selected.

### UNCERTAINTY_TRAP

The answer is not knowable from the public prompt and no external packet is available. The evaluator answer is `UNKNOWN`; additional unconstrained reasoning can waste work or hallucinate certainty.

A primary task never exposes both retrieval and observation packets.

## Seed and task freeze

The merged commit containing this preregistration package supplies the immutable seed identity:

```text
root_seed = SHA256("relaylm2-2187-r2" || exact merged PR commit SHA)
```

The generator then derives each regime/task RNG independently from `root_seed`, regime name, and task index.

This deliberately prevents selecting a convenient seed after model outputs. The concrete 40-task suite becomes computable only from the immutable merged package identity.

Changing the merged commit changes the generated suite and preregistration digest. A physical campaign must record the exact merged commit, root seed, generated task digest, and physical binding before its first model call.

## Deployable information boundary

Before an external operation is selected, a deployable arm may receive only:

```text
task_id
public prompt
retrieval_available
observation_available
base answer where the policy acts after the base call
legal operation names/descriptions
```

It may not receive:

```text
hidden regime
expected answer
retrieval packet before RETRIEVE
observation packet before OBSERVE
operation-bank results
A3 choice
ideal operation
```

The evaluator answer and hidden regime are offline scoring data only.

## Operation surface

R2 freezes the smallest surface needed for heterogeneous value-of-computation curves:

```text
ZERO
  keep the shared base answer; no additional task-work model call

THINK
  one revision call using only already-public information

RETRIEVE
  reveal the frozen retrieval packet, then one revision call

OBSERVE
  reveal the frozen observation packet, then one revision call
```

`RETRIEVE` and `OBSERVE` are experiment operations, not persistent ontology primitives.

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

A1 has no allocator-model call.

### A2 — ADAPTIVE

A2 buys exactly one allocator-model call per task. Its allocator sees the public task mapping, shared base answer, legal operations, and external-availability booleans. It chooses one legal operation.

The allocator call, input/output tokens, and reliably observed latency are charged to A2. No evaluator data or packet content is legal allocator input.

### A3 — ORACLE

After the operation-result bank exists, A3 chooses a correct legal operation when one exists. Ties prefer the lowest extra `ResourceVector`, then the frozen operation priority:

```text
ZERO < THINK < RETRIEVE < OBSERVE
```

If no legal result is correct, A3 records `oracle_no_headroom=true` rather than inventing success.

## Shared operation-result bank

Every task has one physical base completion and one physical completion for each legal non-ZERO operation. Those completions form a frozen evaluator/instrumentation bank.

A0/A1/A2 are evaluated counterfactually from the same bank. This prevents different stochastic completion draws from masquerading as allocator quality.

The bank must not leak into A2. A physical host should order each task so A2's allocator choice is obtained from the base answer before any non-public bank result can become policy input. Bank results may be generated before or after that decision only if deterministic tests prove they are quarantined from the allocator request; the canonical physical host should prefer the clearer base → allocator → bank sequence.

Physical evaluator cost and counterfactual treatment cost are separate ledgers:

```text
physical cost
  every provider request actually issued to construct the bank and A2 decisions

treatment cost
  shared base + the arm-selected operation
  + A2 allocator overhead for A2 only
```

The shared base cost is charged to every deployable arm.

## Structural resource budget

The exact 40-task suite contains:

```text
40 base completions
40 THINK bank completions
8 RETRIEVE bank completions
8 OBSERVE bank completions
40 A2 allocator completions
```

Therefore:

```text
operation-bank provider-call max = 96
A2 allocator-call max            = 40
physical provider-call max       = 136
```

No automatic or semantic retry exists.

For counterfactual treatment accounting, the common hard call ceiling is derived from the most expensive legal deployable path:

```text
40 tasks × (base + allocator + one selected work call) = 120 calls
```

A0 and A1 do not receive free calls merely because their natural spend is lower. Actual spend is reported and is part of the result.

External-unit ceilings are also structural:

```text
retrieval units per arm   <= 8
observation units per arm <= 8
context limit             = 8192
aggregate input tokens    = measured, no frozen ceiling
aggregate output tokens   = measured, no frozen ceiling
```

## Response protocol

Tasks use evaluator-friendly exact answers; no LLM judge is needed.

Answer calls return exactly:

```json
{"answer":"..."}
```

Allocator calls return exactly:

```json
{"operation":"ZERO|THINK|RETRIEVE|OBSERVE"}
```

Duplicate keys, extra keys, invalid operations, provider failure, binding drift, undeclared calls, and retries fail closed. There is no semantic retry.

## Primary measurements

Report aggregate and per-regime vectors for:

```text
exact task correctness
success count
A2 - A0 paired correctness difference
A2 - A1 paired correctness difference
A3 headroom over A0/A1
A2 regret vs A3
best cheap-baseline regret vs A3
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

There is no universal scalar resource currency and no Intelligence score.

## Frozen statistical rules

The task is the paired unit.

Primary reporting uses exact counts and effect sizes. For A2 vs A0 and A2 vs A1, use:

```text
one-sided exact paired sign/binomial test on discordant outcomes
alpha = 0.05
```

The directional test is frozen because the preregistered hypotheses are `A2 > A0` and `A2 > A1`.

Also report a paired bootstrap interval for accuracy difference using:

```text
10,000 resamples
95% interval
bootstrap RNG derived deterministically from the frozen campaign identity
```

No statistical method or favorable regime subset may be chosen after results.

## Frozen interpretation categories

A material task gain is frozen at 4/40 tasks. A1 is considered essentially at the oracle accuracy frontier when its gap to A3 is at most 2/40 tasks.

### INCONCLUSIVE

Any incomplete resource accounting, hard-constraint violation, or protocol-invalid result prevents a positive scientific category.

### NO_ORACLE_HEADROOM

```text
A3 - max(A0, A1) < 4 tasks
```

Allocation does not have enough observed headroom for this R2 campaign to test the metareasoner meaningfully.

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

This is only an R2 constituent signal; it does not authorize a production scheduler.

### HEURISTIC_SUFFICIENT

Oracle headroom is material, A2 does not meet `ADAPTIVE_SIGNAL`, and:

```text
A3 - A1 <= 2 tasks
```

The cheap heuristic captures essentially all observed accuracy headroom.

### ALLOCATOR_FAILURE

Oracle headroom is material, neither `ADAPTIVE_SIGNAL` nor `HEURISTIC_SUFFICIENT` holds, and A2 fails to capture the available headroom strongly enough under the frozen rules.

## Required anti-cheat tests

Before any physical R2 authorization, deterministic tests must prove:

```text
40 unique tasks; 8 per hidden regime
suite is deterministic from the merged commit identity
same generated suite is used by all arms
hidden regime absent from deployable messages
expected answer absent as a deployable field
retrieval packet hidden until RETRIEVE
observation packet hidden until OBSERVE
A3 data absent from deployable messages
A0/A1 policies are deterministic
A2 allocator overhead is charged
A1 has no allocator call
ZERO has no task-work call
shared base is charged to every arm
A3 tie-break is deterministic
136-call physical maximum is structurally derived
120-call common treatment ceiling is structurally derived
aggregate token ceilings are absent
provider attempts cannot disappear in the later physical host
retry/fallback paths are absent in the later physical host
```

The preregistration module does not perform provider calls and does not authorize a physical host by itself.

## Physical identity boundary

A later separately authorized R2 host should preserve the already-qualified #2187 physical lineage unless current authority requires otherwise, but every host execution must reacquire fresh repository/model/runtime/hardware/tokenizer/template/context/decoding/reasoning authority.

Historical R0.5/R1 binding values are anchors, not current authority.

No model, reasoning mode, sampling setting, prompt, task generator, seed, policy, threshold, or budget rule may be changed because the R1 transcript or later R2 outputs suggest a favorable choice.

## Next gate

Completion of #2279 requires the generator, policies, bank semantics, budgets, decision rules, documentation, and deterministic anti-leak tests to merge into `v2`.

After that merge:

```text
repository-side R2 preregistration = complete
physical R2 execution              = still NOT AUTHORIZED
```

A separate fresh reconciliation must inspect the exact merged package and package a fail-closed physical host before any R2 provider request.

> **Metacognition must pay rent.**

> **Oracle headroom tells us whether allocation matters; A2 tells us whether our allocator matters.**

> **Do not give the adaptive arm free information and call it intelligence.**

> **Do not fit tomorrow's scientific budget to yesterday's overflow.**
