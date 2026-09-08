# RelayLM 2.0 — Transfer R2 hard-bound host

Status: repository-only physical-host packaging for #2343 / #2157.

This surface packages the already-preregistered shared/null R2 campaign from #2341. It does not change the scientific design and performs no real provider/model execution during repository qualification.

## Frozen scientific authority

The host is permanently bound to:

```text
preregistration commit = aeb8f8d477ba46650cb2f3d97b7154b69366431c
preregistration digest = sha256:1323fadd94e18d073c07629dd3ce2d2ec9735eea583d5bdfb49606aeec099cf6
call-plan digest = sha256:0890dbaf7d99821592f771225b38af42aa024351d48283f11069980709393d70
transport identity digest = sha256:c78e50b122a447b1d7ee10afc6a0a702b0c83bc59ca84508e8ac11963f0b8376
families = 16 = 8 shared + 8 null
provider calls = 208
```

Concrete seeds are derived only by the merged preregistration code. The host contains no second mutable seed table.

## Exact execution order

For each family, in preregistered family order:

```text
source-learning
T0 / examples_visible 0,1,2,3
T1 / examples_visible 0,1,2,3
T2 / examples_visible 0,1,2,3
```

This gives 13 calls per family and 208 calls total. `R2PlanStructuredClient` consumes the exact preregistered schema plan. A normal complete host transaction performs 209 host-side physical-binding probes: one preflight plus one immediately before every provider call.

No automatic retry, semantic retry, fallback, replay, reseed, arm repair, or post-result semantic repair exists.

## Reused cognitive mechanism

The host does not invent new transfer semantics. It reuses:

- `run_source_learning(...)`;
- `prepare_r1_arms(...)`;
- `run_target_probe(...)`.

One source Structure is learned and governed per family. T0 keeps it canonical but ineligible for cross-task projection. T1 and T2 receive the same projected learned Structure in R2. A wrong but valid learned Structure remains part of the result; evaluator truth never repairs it.

Target probes are read-only over canonical cognition and provenance.

## Protocol boundary

A model response has two distinct failure meanings:

1. **well-formed in-schema answer, but wrong value** — scientific `correct=false`;
2. **invalid JSON/shape/range or malformed source Structure** — protocol failure.

The second class stops the campaign immediately. It must never be rewritten as a scientific false answer. This distinction is enforced by the R2 host even though the provider transport is already JSON-Schema constrained.

## Durable boundary

The host reuses `FrozenExperimentIdentity` and `DurableQuestionRun`.

Before each provider attempt:

1. the exact durable question is marked in-flight;
2. a fresh material live-binding probe is read;
3. the probe is compared with the deeply frozen expected binding.

After provider completion, raw model exchange and token usage are appended before the semantic result is committed. Binding/provider/protocol failure marks the durable run `INCOMPLETE`, writes failure evidence, stops immediately, and leaves `r2-result.json` absent.

Only a complete 208/208 run may reconstruct all 16 family outcomes, invoke the merged `analyze_r2(...)`, write `r2-result.json`, and become citable under claim `R2_SHARED_NULL_PREREGISTERED_PHYSICAL_RESULT`.

## Reconstruction invariants

Complete reconstruction requires:

- durable result order equals the 208-call preregistered plan;
- family index/regime/seed match each plan entry;
- one source result per family;
- four T0, four T1, and four T2 target results per family;
- committed target results have no protocol error;
- every durable result accounts for exactly one provider call;
- total physical calls reconstruct to exactly 208.

The scientific category is produced only by the frozen #2341 `analyze_r2(...)` implementation.

## Anti-leak boundary

Evaluator-only regime labels, hidden rules, expected answers, verification outcomes, and durable question metadata are instrumentation. They are not inserted into semantic model messages.

At each matched evidence level:

- T0/T1/T2 task packets and task digests are identical;
- T0 has no reusable Structure in its model-facing payload;
- T1 and T2 have identical reusable Structure payloads.

## Repository fake qualification

`tests/unit/test_v2_transfer_r2_host.py` mechanically checks:

- exact complete 208-call campaign;
- 209 host-side binding probes;
- 16 source schemas and 192 target schemas;
- complete result reconstruction and frozen analysis;
- fail-closed interior provider failure;
- fail-closed target protocol/shape drift;
- binding drift before the affected provider call;
- dirty/wrong repository rejection;
- occupied artifact rejection;
- scientific identity/plan/retry mutation rejection;
- deep freezing against caller mutation after preflight begins;
- no result artifact on incomplete execution.

These are fake provider calls only. Repository packaging adds zero real physical/provider/model calls.

## Interpretation boundary

Even a future `TRANSFER_SIGNAL` from this host would be one R2 constituent result under one generated task family and one physical model/runtime. It does not promote Structure to an ontology or production primitive and does not modify RelayLM v1 semantics.

R3 mismatch, R4 shift/revision, R5 resource pressure, and R6 held-out generator families remain separate maturity gates.

> Freeze science first; package the instrument second; spend the seed last.
