# RelayLM 2.0 Cognitive Work R3 uniform-task physical host

Owner: #2318  
Scientific owner: #2312  
Parent: #2187

## Purpose

This package hard-binds the merged R3 uniform retrieval-only preregistration to one fail-closed structured-output physical host. It is repository qualification only and does not itself authorize a real model run.

Frozen R3 identity:

```text
preregistration commit = 75bba595e66fea695fe4caf50c4c20a71fa4083b
root seed = sha256:ffb09eb916e990bfc4460641f66f877fea4bb4cd47464cc7673409c6ed663a00
preregistration digest = sha256:a7f874b62ec6c386ce2274f09c50a1898383c5859f6f0fde8db88f034485eb1d
version = relaylm2-cognitive-work-r3-uniform-v1
```

The host never derives the R3 suite from a later execution commit.

## Frozen plan

The host requires exactly 16 uniform `RETRIEVAL_BENEFICIAL` tasks and exactly:

```text
16 BASE
16 A2_ALLOCATE
16 BANK:THINK
16 BANK:RETRIEVE
= 64 calls
```

No observation call is legal. The structured-output split is exactly 48 answer-schema and 16 operation-schema calls.

## Policy and statistical immutability

The host consumes the merged R3 preregistration directly. It therefore preserves the R2-tested A0/A1/A2/A3 policies, model-facing messages, strict parsers, resource accounting, exact paired-test lineage, bootstrap implementation, material gain threshold 4, heuristic-oracle gap threshold 2, and alpha 0.05.

Host packaging does not tune the adaptive allocator after R2.

## Physical transaction boundary

A positive physical execution requires a separately supplied `R3UniformExecutionAuthorization` bound to the exact execution repository commit and the frozen R3 preregistration commit. The package never creates authorization for itself.

`R3UniformHostIdentity` additionally binds:

- exact repository commit/tree;
- exact `ExecutionBinding`;
- context 8192;
- no automatic retry;
- no semantic retry;
- the frozen R3 root seed/digest;
- the exact #2302 structured-output transport identity.

Before the artifact transaction begins, the host validates repository cleanliness, repository commit/tree, authorization, and one live physical-binding preflight observation.

## Durable fail-closed evidence

Provider attempts are registered durably before provider invocation. Every attempt records:

- exact plan identity;
- model-facing messages;
- exact schema kind/schema digest/response-format digest/mapping;
- fresh binding observation;
- provider attempt/completion counters.

Each completed response is preserved before semantic parsing. A provider failure, binding drift, plan mismatch, or strict parser/protocol failure leaves the transaction `INCOMPLETE` and does not create `r3-result.json`.

No retry, replay, fallback, fence stripping, embedded JSON recovery, parser relaxation, schema repair, policy repair, or budget repair is permitted.

## Shared operation bank

For each task the host pays once for:

```text
BASE
A2 allocator decision
THINK bank result
RETRIEVE bank result
```

Only after the bank exists does evaluator-side reconstruction derive A0/A1/A2/A3 outcomes. A2 commits its operation before the non-public bank answers are available.

`r3-bank.jsonl` is explicitly evaluator-only and may contain expected answers, hidden regime labels, and bank correctness. Those values are never model-facing input.

## Completion

A host result is written only after:

```text
provider attempts = 64
provider completions = 64
plan cursor = 64
16 complete task banks
16 outcomes for each A0/A1/A2/A3
resource accounting complete
```

The terminal scientific category is produced only by the merged `interpret_r3_uniform(...)` function:

```text
INCONCLUSIVE
NO_USEFUL_WORK_HEADROOM
UNIFORM_NULL_VIOLATION
HEURISTIC_SUFFICIENT_UNIFORM
UNIFORM_NULL_CONSISTENT
```

## Repository fake qualification

Tests exercise a complete 64-call fake transaction with 65 host-side binding probes and exact per-call structured-output mappings, plus fail-closed pressure for authorization, dirty repository, artifact collision, provider failure, binding drift, protocol wrapper drift, and evaluator/packet leakage.

Fake provider evidence is not actual-model evidence.

## Architecture boundary

Architecture consequence remains `NONE`. A later exactly-once physical execution owner is required before #2312 obtains an R3 result.

> Freeze the instrument before spending the null-control seed.

> A null control should be cheaper than the treatment campaign it audits.
