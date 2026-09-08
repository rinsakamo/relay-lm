# RelayLM 2.0 canonical physical execution preflight

This document is the canonical cross-experiment procedure authority for RelayLM 2.0 physical / actual-model execution setup.

The core rule is:

> **Controller observes and assembles. Host validates and freezes.**

The contract exists to prevent each Local execution prompt from growing its own second implementation of identity freeze, launch admission, durability, retry, or provider-entry semantics.

## Ownership boundary

A physical transaction has three phases.

```text
CONTROLLER_SETUP
  read-only repository / serving / artifact / runtime / hardware observations
  raw identity or typed host-identity assembly
  deterministic shape / mirror checks
  fresh material binding A/B

HOST_ENTERED
  exact repository / static / client / artifact validation
  fresh host-owned live-binding validation
  authoritative host-owned freeze / authorization validation
  durable execution initialization where the host uses durability

EXECUTION_READY
  first provider/model call may begin
```

No external controller may move host-owned work upward into `CONTROLLER_SETUP` merely as an extra safety check.

In particular, for `FrozenExperimentIdentity`-based hosts the controller must not call:

```text
freeze_experiment_identity(...)
FrozenExperimentIdentity.from_live_attestation(...)
DurableQuestionRun.start(...)
```

Those calls belong to the repository host.

## Controller setup

Controller setup is observational and restartable only before the scientific host boundary.

Allowed work includes:

- fresh repository / Issue / open-writer authority;
- exact clean checkout observation;
- native serving-state A/B observations;
- model artifact, tokenizer, template, runtime, backend, process, GPU and capacity anchors;
- construction of the complete raw identity required by the selected host;
- exact key-set checks against repository constants;
- equality of mirrored launch facts such as backend, runtime, admitted context and capacity evidence;
- construction of the host material binding;
- two fresh material-binding observations A/B;
- construction of a fresh empty artifact-root path outside the repository.

For `FrozenExperimentIdentity`-based controllers, use:

```python
from tools.v2_physical_preflight import validate_frozen_identity_controller_setup
```

This validator deliberately cannot freeze identity, create durability, authorize the campaign, or call the provider.

The default maximum number of complete read-only controller establishment cycles is three. A failed cycle is discardable only while:

```text
host invocations = 0
provider / semantic calls = 0
scientific task exposure = 0
scientific artifact population = false
serving treatment was not changed as rescue
```

A new cycle starts from fresh observations. Do not splice evidence from failed cycles.

## Host-owned freeze

Once the experiment host is invoked, the controller does not retry the host.

A `FrozenExperimentIdentity` host owns the authoritative sequence:

```text
host static validation
-> repository / artifact / client validation
-> initial fresh live binding probe
-> material binding validation
-> freeze_experiment_identity(...)
-> DurableQuestionRun.start(...) where applicable
-> first provider call
```

A typed host such as Cognitive Work may use a different identity realization, but preserves the same responsibility boundary:

```text
controller assembles typed identity
-> host validates exact repository / authorization / typed binding
-> host performs final fresh binding check
-> provider call
```

Do not force all experiments into one identity ontology. The invariant is the ownership and ordering of the boundary.

## Exactly-once terminal boundary

For an exactly-once physical owner:

```text
before host invocation failure
  -> EXECUTION_BLOCKED
  -> host invocation = 0
  -> provider / semantic calls = 0

host invocation began but did not complete
  -> experiment-specific INCOMPLETE terminal
  -> no second host invocation

host completed exact declared plan
  -> experiment-specific COMPLETE terminal
```

A host-owned freeze failure after host entry is therefore an incomplete host transaction even when zero provider calls were made. It is not permission to invoke the same host again.

## No treatment rescue

Neither controller setup nor host preflight authorizes changing treatment to obtain a pass.

Do not change after observing failure:

- model artifact or quantization;
- runtime / backend;
- context ceiling;
- reasoning mode;
- prompt / schema / parser;
- scientific seed / task set / call plan;
- retries / fallbacks;
- evaluator/statistics/thresholds.

Read-only controller cycles can recover only from observational/setup instability before host entry.

## Capacity evidence

Capacity is evidence, not a copied number.

Where the selected identity contract contains both top-level capacity evidence and launch-admission capacity evidence, the controller must assemble the same freshly justified value in both places before host invocation. The host remains the authority that freezes the live-attested identity.

## Local execution prompts

Physical prompts should not reproduce this procedure in full. They should instead instruct the Local agent to:

1. read `.ai/skills/physical-execution-preflight/SKILL.md`;
2. follow this canonical contract;
3. supply only experiment-specific scientific identity, host/client, exact call plan, result fields and terminal reconciliation rules.

If a Local prompt conflicts with this document, current repository authority wins.

## Current realizations

Transfer R1 and R2 already use host-owned `freeze_experiment_identity(...)` before provider entry. Cognitive Work hosts use their typed `ExecutionBinding` / host-identity realization and perform host-owned fresh binding checks. Historical completed evidence is not rewritten by this procedure owner.

## Working principles

> **Controller observes and assembles. Host validates and freezes.**

> **Do not implement a second host outside the host.**

> **Explore/restart the controller before host entry; freeze once after host entry.**

> **One frozen transaction means one frozen transaction.**

> **Capacity is evidence, not a number copied from yesterday.**
