# RelayLM 2.0 Cognitive Work — R2 replacement physical host

Owner: #2292  
Parent experiment: #2187  
Replacement preregistration: #2290 / #2291  
Historical original host: #2285 / #2286  
Historical physical R2: #2288 = `R2_INCOMPLETE`

## Role

This package binds the repaired R2 answer protocol to a separate physical-host identity without modifying the historical #2286 host.

Frozen replacement scientific authority:

```text
preregistration commit = 6a85ef75241baf65ebf1044ebbb3583e123063d7
root seed = sha256:a4610e491d2ff5358d65a468d91163097608faf2dd223903300c24339207cdfd
answer protocol = canonical-string-or-integer-v2
```

The original frozen authority remains:

```text
preregistration commit = f8540c959856938331d5db58ae3a2b9825ad5f9b
host = tools/v2_cognitive_work_r2_host.py
answer protocol = STRING_ONLY
historical physical result = #2288 R2_INCOMPLETE
```

The replacement host is not a generic multi-version runner and does not authorize physical execution by itself.

## Reused mechanics

The replacement host deliberately reuses the proven fail-closed machinery from the historical host for:

```text
repository attestation
fresh external artifact root
exact call-plan cursor
pre-attempt live binding
provider attempt/completion durability
request evidence
shared operation-bank accounting
resource validation
statistics/result construction
INCOMPLETE semantics
```

The historical private mechanics are used as an explicit implementation seam so their behavior does not have to be independently reimplemented or silently generalized.

## Version-specific surface

The replacement host changes only:

```text
hard-bound preregistration commit/root seed
answer/revision messages
answer scalar parser
manifest/result claim identity
answer-protocol version identity
```

Allocator messages, operations, policy functions, oracle semantics, resource rules, statistical rules and interpretation thresholds remain inherited from the frozen R2 scientific design.

## Exact plan

```text
40 BASE
40 A2_ALLOCATE
40 BANK:THINK
8 BANK:RETRIEVE
8 BANK:OBSERVE
= 136 calls
```

Every provider attempt remains authorized by exact task id, role, operation and order. A2 allocation is completed before the corresponding non-public operation-bank results are generated.

## Answer transport

Accepted scalar representations:

```json
{"answer":"87"}
{"answer":87}
```

Both canonicalize to evaluator text `87` without access to expected-answer truth.

Bool, float, null, containers, empty strings, duplicate/extra keys and non-standard JSON constants remain invalid.

## Physical execution boundary

Packaging/CI uses fake clients only.

```text
provider calls = 0
semantic generations = 0
replacement physical campaign = 0
```

A future real campaign requires a new one-shot execution owner, fresh repository authority, fresh LM Studio/model/runtime/tokenizer/template/reasoning/decoding/hardware identity, a fresh external artifact root, and a positive replacement-specific execution authorization.

The historical #2288 transaction must never be resumed or retried.

## Scientific consequence

```text
scientific allocator verdict = NONE
production scheduler authority = NONE
architecture consequence = NONE
```

> Version the measuring instrument; do not rewrite the failed measurement.
