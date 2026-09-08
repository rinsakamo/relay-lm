# RelayLM 2.0 Cognitive Work R4 shift physical host

Owner: #2325  
Scientific owner: #2321  
Parent: #2187

## Purpose

This repository package hard-binds the merged R4 cue/value relationship-shift preregistration to one fail-closed structured-output physical host. It does not itself authorize a real model run.

Frozen identity:

```text
preregistration commit = af00c6686e6412c0bcfcb09567a609e978f81fe5
root seed = sha256:234f8cf3232d686b2881d1162e6afa814f30bdcf7007453111c5d7b181e6af2c
preregistration digest = sha256:6a0cf44f2cfb003eb065d6a5c53977ee144ed9fa695ae0298062c20f9e6655be
version = relaylm2-cognitive-work-r4-availability-shift-v1
```

The host never derives the R4 suite from a later execution commit.

## Frozen shift

R4 preserves the five R2 semantic regimes and the exact R2-tested A0/A1/A2/A3 policies. It changes only the relation between public availability cues and marginal work value:

```text
retrieval_available = true on every task
observation_available = true on every task
```

Useful packet content remains regime-dependent. The inherited A1 retrieval-first heuristic therefore chooses `RETRIEVE` on all twenty R4 tasks. That is the intended held-out transfer pressure.

## Exact physical plan

Each of twenty balanced tasks pays once for:

```text
BASE
A2_ALLOCATE
BANK:THINK
BANK:RETRIEVE
BANK:OBSERVE
```

Totals:

```text
20 BASE
20 A2_ALLOCATE
20 THINK
20 RETRIEVE
20 OBSERVE
= 100 provider calls
```

Structured transport split:

```text
80 answer-schema
20 operation-schema
```

A normal complete host transaction performs 101 host-side binding probes: one preflight plus one fresh probe before every provider attempt.

## Policy and statistic immutability

The host consumes the merged #2321 preregistration directly and therefore preserves:

```text
A0 = fixed THINK
A1 = retrieval-first heuristic unchanged
A2 = R2-tested model allocator unchanged
A3 = evaluator-only oracle unchanged

material gain = 4
heuristic-oracle gap = 2
alpha = 0.05
bootstrap = 10,000 / 95%
```

The host adds no new scientific category. Only `interpret_r4_shift(...)` may produce the terminal R4 category.

## Physical transaction boundary

A positive run requires a separately supplied `R4ShiftExecutionAuthorization` bound to the exact execution repository commit and frozen R4 preregistration.

`R4ShiftHostIdentity` binds:

- exact repository commit/tree;
- exact `ExecutionBinding`;
- context 8192;
- retry disabled;
- frozen R4 root/digest/version;
- exact #2302 structured-output transport identity.

Repository cleanliness and authorization are validated before an artifact transaction. One live physical-binding preflight is required before durable provider work begins.

## Durable fail-closed evidence

Every provider attempt is registered before invocation with:

- exact plan identity;
- model-facing messages;
- exact schema kind/schema digest/response-format digest/mapping;
- fresh binding observation;
- provider counters.

Every completed response is durably recorded before semantic parsing.

Provider failure, binding drift, call-plan mismatch or strict parser/protocol failure leaves the transaction `INCOMPLETE`; `r4-result.json` is never synthesized for a partial transaction.

No retry, replay, fallback, fence stripping, embedded JSON recovery, parser relaxation, schema repair, policy repair, budget repair or statistic repair is permitted.

## Shared bank and information quarantine

For each task A2 commits its operation immediately after BASE and before any non-public bank result exists. The host then builds the complete THINK/RETRIEVE/OBSERVE bank once.

Only after that bank exists are A0/A1/A2/A3 counterfactual outcomes reconstructed.

`r4-bank.jsonl` is explicitly evaluator-only and may contain:

- hidden regime;
- expected answer;
- bank correctness;
- A3 choice;
- outcome correctness.

None of those fields are model-facing. A RETRIEVE/OBSERVE packet appears only in the request that purchases that operation.

## Completion

A result is legal only after:

```text
provider attempts = 100
provider completions = 100
plan cursor = 100
20 complete banks
20 outcomes each A0/A1/A2/A3
resource accounting complete
```

The result artifact reports:

- global and per-regime correctness;
- A3-A1 shift headroom;
- A2-A1 delta, exact p and 10k bootstrap interval;
- A2-A0 delta;
- A1 RETRIEVE x20 identity;
- A2 and A3 operation counts;
- A2-vs-A3 confusion;
- regret, wasted work and missed useful work;
- physical and per-arm ResourceVectors;
- hard resource/protocol counts;
- frozen R4 interpretation.

## Repository fake qualification

Tests must exercise a complete 100-call synthetic transaction with 101 binding probes and exact 80/20 structured-output transport split, plus fail-closed pressure for:

- authorization;
- dirty repository / artifact collision;
- provider failure;
- binding drift;
- strict protocol wrapper drift;
- evaluator/packet leakage.

Fake evidence is not actual-model evidence.

## Architecture boundary

Architecture consequence remains `NONE`. A separate exactly-once physical owner is required before #2321 gets an actual-model R4 result.

> **Shift the cue, not the policy.**

> **Freeze the instrument before spending the held-out seed.**

> **Metacognition must pay rent.**
