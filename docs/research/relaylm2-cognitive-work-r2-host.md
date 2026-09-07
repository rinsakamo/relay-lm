# RelayLM 2.0 — #2187 R2 preregistered physical host

This document is the repository authority for the fail-closed physical host packaged by #2285 for the preregistered Cognitive Work R2 campaign.

The host consumes the merged R2 design from #2279 / PR #2283. It does **not** retune the experiment and does **not** authorize physical execution by existing.

```text
host package = deterministic infrastructure
physical R2  = requires a separate fresh execution authorization
architecture consequence = NONE
production scheduler authority = NONE
```

## Frozen preregistration identity

The task suite remains anchored to the preregistration merge rather than to the later host implementation commit:

```text
preregistration commit
  f8540c959856938331d5db58ae3a2b9825ad5f9b

root seed
  sha256:c7a2b3953b03d51228346ef57937c23b16329b6b659bc7201c00b853f2322e85
```

The execution checkout may move as the host is implemented or later reconciled. The host identity therefore carries two independent repository facts:

```text
current execution repository commit/tree
frozen preregistration commit/root-seed/digest
```

A later execution commit must not silently become a new task seed.

## Separate execution gate

`run_r2_host_campaign(...)` requires an explicit `R2ExecutionAuthorization` supplied by the caller.

The package does not create a positive authorization by itself. The authorization must bind:

```text
authorization id
exact current execution repository commit
frozen preregistration commit
physical_execution_authorized = true
```

A false or stale authorization fails before artifact creation or provider calls.

This is the repository seam for the separate fresh R2 execution reconciliation required by #2285. Unit tests use a clearly test-only authorization with a fake client; that is deterministic host qualification, not physical evidence.

## Exact physical plan

The host imports the merged preregistration and derives its provider authority from `physical_call_plan(...)`.

The campaign is exactly:

```text
40 BASE
40 A2_ALLOCATE
40 BANK:THINK
8 BANK:RETRIEVE
8 BANK:OBSERVE
= 136 provider calls
```

For each task the order is exactly:

```text
BASE
  -> A2_ALLOCATE
  -> BANK:THINK
  -> BANK:RETRIEVE if legal
  -> BANK:OBSERVE if legal
```

A provider call is authorized only when all of these match the next frozen plan entry:

```text
order
task_id
role
operation
```

The contract is therefore stronger than a numeric `calls <= 136` budget. An extra, duplicated, reordered, or differently typed call fails closed.

## Allocator-before-bank boundary

A2 allocates immediately after the shared base completion and before any non-public operation-bank completion for that task exists.

The allocator request comes only from the merged `allocator_messages(...)` surface. It may contain:

```text
opaque task id
public prompt
retrieval / observation availability
shared base answer
legal operation descriptions
```

It may not contain:

```text
hidden regime
expected answer as evaluator metadata
external packet contents
bank results
A3 choice
post-hoc correctness
ideal operation
```

Only after A2's operation has been durably recorded does the host construct the task's non-ZERO bank calls.

## Strict message and output semantics

The host does not reimplement experiment prompts or parsers.

It consumes the merged functions:

```text
answer_messages
allocator_messages
revision_messages
parse_answer
parse_operation
```

Answer calls must return exactly:

```json
{"answer":"..."}
```

Allocator calls must return exactly:

```json
{"operation":"ZERO|THINK|RETRIEVE|OBSERVE"}
```

Duplicate keys, extra keys, empty answers, or illegal operations terminate the transaction as `INCOMPLETE`. There is no semantic retry.

## Physical binding

The host uses the existing #2187 `ExecutionBinding` identity:

```text
model identity
runtime identity
hardware identity
tokenizer identity
chat-template identity
context limit
decoding identity
reasoning identity
```

The R2 context contract remains `8192`.

A genuine caller must provide `live_binding_probe`.

The host requires:

```text
one preflight binding probe
+ one fresh binding probe immediately before every provider attempt
```

Any drift stops before the next provider attempt. The host does not change LM Studio settings, reload a model, switch provider, or continue under a new identity.

## Repository and artifact boundary

Before provider work the host requires:

```text
clean execution checkout
exact expected repository commit
exact expected repository tree
fresh empty artifact root outside the checkout
frozen preregistration identity
retry disabled
```

Repository mismatch and artifact collision fail before provider calls.

The physical run never modifies the source checkout.

## Provider-attempt durability

A provider attempt becomes durable before the client call begins.

For every declared call, `request-evidence.jsonl` records an `ATTEMPT_REGISTERED` record containing the exact plan identity, messages, binding observation, and current counters.

If the provider succeeds, a second `COMPLETED` record stores the response content/id and token accounting.

If the provider fails:

```text
provider_attempts > provider_completions
status = INCOMPLETE
failure remains visible
no retry
```

A completed provider response that later fails strict JSON parsing is also retained as a completed physical response. Protocol invalidity does not rewrite physical history.

## Shared bank

For each task, evaluator-only `r2-bank.jsonl` records:

```text
shared base completion
THINK result
RETRIEVE result if legal
OBSERVE result if legal
A2 allocator decision and allocator cost
A3 offline oracle choice
A0/A1/A2/A3 counterfactual outcomes
```

The expected answer and hidden regime may exist in this quarantined evaluator artifact. They are never copied into deployable requests.

All arms use the same physical base and operation bank. There are no arm-specific redraws.

## Resource accounting

Physical campaign cost counts every real base, allocator, and bank completion.

Counterfactual treatment cost is reconstructed separately:

```text
A0 / A1
  shared base + selected operation

A2
  shared base + allocator call + selected operation

A3
  evaluator-only shared base + oracle-selected operation
```

The merged R2 structural contract remains:

```text
physical provider calls = 136
counterfactual treatment calls per deployable arm <= 120
retrieval units <= 8
observation units <= 8
context limit = 8192
aggregate input tokens = measured; no hard campaign ceiling
aggregate output tokens = measured; no hard campaign ceiling
automatic retry = false
semantic retry = false
```

The host does not restore the historical R1 `500` token ceiling or fit another threshold around `572`.

Resource dimensions remain a vector. The host does not invent a universal scalar cost.

## Durable artifacts

A started transaction writes:

```text
run-manifest.json
run-state.json
request-evidence.jsonl
r2-bank.jsonl
```

`r2-result.json` exists only after:

```text
all 136 plan entries completed
provider attempts = provider completions = 136
all 40 task banks reconstructed
all four arm vectors contain 40 outcomes
structural treatment resource constraints pass
strict protocol remains valid
```

On first material failure:

```text
status = INCOMPLETE
prior evidence remains
r2-result.json is absent
```

## Result derivation

The complete result reuses the merged preregistration statistics and interpretation logic:

```text
interpret_r2
paired_bootstrap_interval
```

It reports at least:

```text
A0/A1/A2/A3 correctness vectors
aggregate and per-regime correctness
A2-A0 / A2-A1 effects and exact p-values
A3-A0 oracle headroom
paired 10,000-resample bootstrap intervals
per-arm ResourceVectors
physical ResourceVector
A2 selection confusion vs A3
wasted / missed adaptive work counts
frozen interpretation category
```

The allowed interpretation categories remain:

```text
NO_ORACLE_HEADROOM
HEURISTIC_SUFFICIENT
ALLOCATOR_FAILURE
ADAPTIVE_SIGNAL
INCONCLUSIVE
```

A complete R2 result can be a constituent scientific result when run under a separately valid physical authorization. It still does not define Intelligence or authorize a production scheduler.

## Deterministic qualification

Repository tests use only a fake `ExperimentClient` and synthetic `ExecutionBinding` probes.

The main positive fixture executes the entire 136-entry plan and verifies:

```text
136 attempts / 136 completions
137 binding probes including preflight
40 shared bank records
no undeclared 137th call
A2 overhead charged
A1 no allocator call
ZERO no task-work call
external packets only in their corresponding BANK request
result recomputable from raw bank evidence
```

Negative fixtures prove:

```text
provider failure remains an attempt and stops without retry
strict parser failure preserves the completed response and yields INCOMPLETE
mid-run binding drift stops before the next provider attempt
false execution authorization stops before artifacts/calls
repository mismatch stops before calls
artifact collision stops before calls
```

These tests perform zero physical provider/model calls.

## Scientific boundary

Merging the host establishes only:

> **The preregistered R2 transaction has a deterministic fail-closed physical execution surface.**

It does not establish:

```text
R2 result
adaptive allocator value
production scheduler value
Attention primitive
Intelligence mechanism or score
architecture promotion
```

A separate fresh execution gate must reacquire repository, model, runtime, tokenizer/template, reasoning/decoding, hardware, artifact-root, and live-binding authority before one physical campaign transaction may be attempted.

> **Freeze the claim before buying the evidence.**

> **The allocator chooses before the oracle bank exists.**

> **Count failed work; do not retry reality away.**
