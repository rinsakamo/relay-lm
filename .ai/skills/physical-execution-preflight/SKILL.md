---
schema_version: 1
id: physical-execution-preflight
responsibility: Apply the canonical RelayLM 2.0 host-owned physical execution boundary before an actual-model transaction spends its scientific seed.
mode: execution_preflight
when_to_use:
  - Before any RelayLM 2.0 physical / actual-model host invocation.
  - When a Local execution prompt asks for native serving, model/runtime/hardware binding, capacity evidence, or exactly-once provider execution.
  - When recovering from a read-only controller setup failure before host invocation.
when_not_to_use:
  - To change scientific seeds, tasks, prompts, schemas, statistics, budgets, thresholds, or interpretation.
  - To add a second controller-owned identity freeze or durable-run implementation.
  - To retry or resume an exactly-once host after host invocation has begun.
required_authority:
  - .ai/README.md
  - .ai/agent-contract.yaml
  - docs/reference/development-workflow.md
  - docs/reference/relaylm2-physical-execution-preflight.md
  - The experiment owner's current .ai/authority declaration and canonical surfaces.
authorization:
  repository_writes: prohibited_during_physical_transaction
  provider_calls: only_after_host_entry
---

# Physical execution preflight

This is a repository-native procedure. The canonical semantic/procedure authority is `docs/reference/relaylm2-physical-execution-preflight.md` under owner #2363.

## Invariant

> **Controller observes and assembles. Host validates and freezes.**

Do not implement a second host in Local controller code.

## Procedure

1. Reconstruct fresh repository authority and the selected experiment owner. Treat all handoff SHA/status/model/runtime facts as historical until re-observed.
2. Confirm the physical owner is OPEN/unspent and no competing writer changes the same scientific or execution boundary.
3. Use an isolated exact clean checkout and a fresh external artifact root.
4. Perform read-only native serving A/B observations and collect stable model/runtime/artifact/tokenizer/template/GPU/capacity anchors from appropriate local sources.
5. Assemble the complete raw identity or typed host identity required by the selected repository host.
6. For `FrozenExperimentIdentity`-based hosts, call only the controller validator:

```python
from tools.v2_physical_preflight import validate_frozen_identity_controller_setup
```

Supply the host's material-binding field set plus two fresh material binding observations A/B.
7. Do **not** call `freeze_experiment_identity(...)`, `FrozenExperimentIdentity.from_live_attestation(...)`, or `DurableQuestionRun.start(...)` from the Local controller.
8. Immediately before invocation, reacquire the experiment-specific authority/digests/call plan and verify host invocation/provider/semantic counts remain zero.
9. Invoke the repository-owned experiment host at most once.
10. After host entry, do not retry, replay, reseed, repair, or invoke again. Preserve the host's complete/incomplete result exactly.
11. Reconcile the physical owner and parent owner using the experiment-specific terminal contract.

## Restartable controller setup

At most three complete controller establishment cycles are allowed by default.

A cycle may be discarded only while all are true:

```text
host invocation = 0
provider calls = 0
semantic calls = 0
scientific task exposure = 0
scientific artifact populated = false
serving treatment changed as rescue = false
```

Each new cycle starts from fresh native observations. Never patch one failed cycle by borrowing stale facts from another.

## Frozen-identity controller checks

Before host entry, the controller may verify only deterministic assembly facts:

```text
raw identity field set == repository FROZEN_EXPERIMENT_IDENTITY_FIELDS
launch_admission field set == repository LIVE_LAUNCH_ADMISSION_FIELDS
backend mirrors launch backend
runtime mirrors launch runtime
context capacity mirrors admitted context
capacity evidence mirrors launch capacity evidence
fresh material binding A == proposed binding
fresh material binding B == proposed binding
A == B
```

The host then performs the authoritative live-attested freeze.

## Typed host identities

Some experiment families, including Cognitive Work, use typed `ExecutionBinding`/host identities instead of `FrozenExperimentIdentity`.

Do not translate them into a synthetic frozen identity merely for uniformity. Preserve the same protocol:

```text
controller observes + assembles typed identity
host validates exact repository / authorization / final fresh binding
provider begins only after host validation
```

The common invariant is ownership/order, not one universal identity representation.

## Stop conditions

Before host entry, return the experiment's blocked class when fresh authority, complete identity assembly, capacity evidence, binding A/B, exact checkout, or fresh artifact boundary cannot be established without changing treatment.

After host entry, use the experiment's incomplete class. Do not convert a host-owned freeze failure into a new controller cycle.

## Forbidden rescue

Never change model, quantization, runtime, context, reasoning, prompt, schema, parser, seed, task set, budget, statistics, or retry policy to make preflight pass.

## Handoff rule

Future physical execution prompts should reference this skill rather than reproducing the preflight algorithm. The prompt should contain only experiment-specific identity, call plan, metrics, and reconciliation rules.
