# RelayLM 2.0 Cognitive Work — structured-output R2 host

Status: **deterministic/fake-client host qualification only; physical R2 remains unauthorized**.

Owner: #2306. Parent experiment: #2187. Consumes #2304 and #2302.

## Frozen scientific identity

The host is hard-bound to the third preregistration merged by #2305:

```text
preregistration commit = bca9866cab344a9701a859d299af2b18924f6f2e
root seed = sha256:f59a601eedf78eb405691b59d86185c43226a749d9bf523bec20464a392bc495
preregistration digest = sha256:53271a481c2270eebe086a159fa7a8fb8905f7d087386bc0c580e504dcedc18b
```

A later host merge commit cannot change the task suite. `build_preregistration(...)` always consumes the exact frozen preregistration commit above.

The scientific design remains 40 tasks over five hidden regimes and the exact 136-call bank plan. Policies, messages, budgets, oracle, statistics and interpretation are imported from the preregistration rather than copied into the host.

## Frozen structured-output transport

Every provider call is paired with the exact #2302 qualified `response_format`:

```text
BASE        -> answer JSON Schema
A2_ALLOCATE -> operation JSON Schema
BANK:*      -> answer JSON Schema
```

The mapping is derived by `response_format_for_call(plan_entry)` from #2304.

Accepted transport identities include:

```text
qualification version = relaylm2-cognitive-work-sopq-v1
answer schema = sha256:d7f69ea25824f613d0b60198abe050adc66a3bf45d9f2045d1997214a55498e5
operation schema = sha256:acabff40467f48996033a4be6ee02dbfa97755bbfaf45ee1dd94cea5afeb720d
answer response_format = sha256:e7a71f6a15e7cc936df664f19e3729cbffce6562dbebcb5e69e8f9cfd070639b
operation response_format = sha256:a41031db0de0e912ded0fae8e8fb9687507debb6bcc86a286cfa0051de8afa76
```

No prompt-only fallback, `json_object`, fence stripping, embedded JSON recovery, tool-call substitution or dynamic schema repair exists in this host.

## Fail-closed transaction

The host preserves the accepted R2 durability mechanics:

- clean exact repository commit/tree;
- fresh empty artifact root outside the checkout;
- explicit separate execution authorization;
- one preflight binding probe plus one fresh probe before every provider attempt;
- attempt evidence before provider invocation;
- exact plan order and unique call identity;
- `response_format`, schema digest and binding included in request evidence;
- no retry, fallback, replay or parser/schema repair;
- provider failure keeps attempts distinct from completions;
- strict parser failure after a completion keeps the completed response evidence but terminates the run;
- binding drift stops before the affected provider attempt;
- evaluator-only bank evidence remains separate from model-facing request evidence;
- `r2-result.json` is written only after all 136 calls and all reconstruction/resource checks complete.

A complete normal transaction therefore performs 136 provider calls and 137 host binding probes including preflight.

## Scientific reconstruction

After a complete operation bank exists, the host reuses the preregistered functions for A0/A1/A2/A3 reconstruction and resource/statistical interpretation. A2's allocator call is charged; A1 receives no allocator call; ZERO uses only the shared base completion.

A2 allocation is physically obtained before any non-public bank operation result for that task exists. Retrieval and observation packets are projected only in their corresponding bank calls.

## Repository qualification

Repository tests use fake structured-output clients only. They cover:

- exact frozen commit/root/digest;
- full 136-call completion;
- 96 answer-schema and 40 operation-schema calls;
- evaluator/packet quarantine;
- provider failure;
- wrapper/strict-parser failure;
- binding drift;
- dirty repository and artifact collision;
- explicit authorization;
- no 137th call.

No LM Studio/provider/model call is made by this owner.

## What merge does not authorize

```text
physical provider calls = 0
semantic generations = 0
R2 campaign invocations = 0
real physical execution authorization = 0
scientific allocator verdict = NONE
architecture consequence = NONE
v1 mutation = 0
```

A separately owned one-shot physical execution gate is required after this host merges and post-merge CI is green.

> Freeze the instrument into the host before spending the proof seed.

> Change the transport, not the treatment.

> Metacognition must pay rent.
