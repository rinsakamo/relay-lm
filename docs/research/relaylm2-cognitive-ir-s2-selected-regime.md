# RelayLM 2.0 Cognitive IR S2 — selected-regime preregistration

Status: **PREREGISTERED / NO S2 MODEL CALLS YET**. Owner: #2211.

This document freezes the task family for the next fresh NON_CITABLE S2 P0–P6 transaction after the completed factorized calibration-v2 selected `V2_IDENTITY_OFFSET_NO_WRAP`.

It does not reinterpret calibration-v1, tune an admission threshold, change P0–P6 semantics, choose a winning representation, authorize S3, or mutate architecture authority.

## Calibration admission anchor

The completed calibration-v2 transaction is historical admission evidence only:

```text
repository commit:
  ff89c5cb20bb4089ad52ea4a2d1992e64e5c5ea9

run id:
  calv2-8eb503b4598857c6768cdc67948e5f42e4dac76b4e268e43b0ee009320966ee0

identity fingerprint:
  sha256:21a9b484df100f616386f55165f5aec5f71de2235f40d9b0e44ff00b96cce310
```

Frozen completed counts:

| regime | C0 application | C1 formation | C2 joint | admitted |
| --- | ---: | ---: | ---: | --- |
| `V2_SINGLE_SWAP_ZERO_OFFSET` | 6/6 | 6/6 | 5/6 | no |
| `V2_IDENTITY_OFFSET_NO_WRAP` | 6/6 | 5/6 | 4/6 | **yes** |
| `V2_IDENTITY_OFFSET_WRAP` | 6/6 | 2/6 | 1/6 | no |
| `V2_SINGLE_SWAP_OFFSET_NO_WRAP` | 2/6 | 0/6 | 0/6 | no |

The original calibration-v2 selector and unchanged thresholds mechanically replay `V2_IDENTITY_OFFSET_NO_WRAP` as the selected regime. The S2 preregistration does not weaken `C0=6/6`, `C1=3..5/6`, or `C2=2..4/6`.

The calibration receipt is not current physical authority. Every later S2 execution must reacquire repository/model/runtime/provider authority fresh.

## Fresh S2 family

Calibration cases cannot become S2 evidence. The next S2 family therefore uses an independent deterministic label and seed:

```text
label = relaylm2-cognitive-ir-s2-selected-regime-v1
seed  = 1399709667
```

The seed is disjoint from:

- historical S2 seed `2211`;
- all calibration-v1 seeds;
- all calibration-v2 seeds.

The hidden shared source/target rule is frozen as:

```text
modulus     = 10
permutation = [0, 1, 2, 3]
offsets     = [3, 2, 1, 1]
```

This is exactly the selected factor class: identity permutation, nonzero offsets, no wrap in the observed source examples or the executed target query.

The compatibility-level `TransferFamily.regime` remains `shared` because source and target use the same rule. `shared` is not a replacement name for the calibrated factor; `V2_IDENTITY_OFFSET_NO_WRAP` remains the task-selection authority.

## Source formation packet

Exactly four fresh source examples are generated from the new S2 seed. They contain only public input/output observations plus modulus when passed to formation. The hidden permutation/offset values are not inserted into P2/P3/P4 formation messages.

The four source examples are mechanically checked against the full public legal class:

```text
all 4! source-index permutations
× arbitrary modulo-10 offsets
```

and exactly one candidate rule fits all four. Thus S2 formation does not depend on an undisclosed prior that the permutation is identity.

All four source inputs satisfy zero wrap coordinates under the hidden rule.

## Target probe

The next S2 smoke freezes:

```text
step_index       = 0
examples_visible = 0
query            = [6, 5, 6, 8]
expected output  = [9, 7, 7, 9]
```

The target query also has zero wrap coordinates. Target examples are generated and retained in the family identity but none are projected into the executed target prompt because `examples_visible=0`.

This keeps the actual P0–P6 question focused on whether the representation formed from the source observations is usable on the matched future task. It does not let current target examples wash out representation differences.

## Representation protocol is unchanged

The existing #2211 S2 representation contract remains authoritative:

```text
formation:
  P2 ordinary summary        1 model call
  P3 semantic cache/gist     1 model call
  P4 reusable rule           1 model call

P5/P6:
  deterministic derivatives of the exact P4 learned payload

probe:
  P0..P6                     7 model calls

physical total               10 model calls
```

In particular:

- P0/P1 remain direct source-history/retrieval controls;
- P2/P3 are independently model-formed from the exact same source packet;
- P4 is model-formed from that same source packet;
- P5 and P6 do not receive independent extraction calls;
- P4/P6 must retain deterministic equal-information semantic identity;
- all arms share source history, target task, and provenance identity;
- evaluator-hidden rule identity remains evaluator instrumentation rather than model Evidence;
- formation/projection/target cost accounting remains visible.

No P0–P6 representation definition is changed by selecting the task regime.

## Scientific boundary

Repository preregistration performs:

```text
provider calls = 0
LM Studio calls = 0
GPU calls = 0
P0-P6 executions = 0
```

Current status:

```text
selected task regime = V2_IDENTITY_OFFSET_NO_WRAP
S2 task family       = PREREGISTERED
S2 physical result   = NONE
S3                   = BLOCKED
architecture         = NONE
```

The next physical transaction must be fresh, fail closed, and NON_CITABLE. It must not reuse calibration outputs as S2 responses or current physical proof-state authority.

A future completed S2 may only classify the bounded smoke as protocol defect / floor / ceiling / mechanically discriminating under its frozen contract. Only a mechanically discriminating S2 may make a separate S3 preregistration eligible. It cannot itself establish Memory/Structure ontology or a production architecture.

## Execution handoff

Before physical S2 execution, package or verify a current host entrypoint that:

- constructs this exact selected family from `generate_selected_s2_family()`;
- freezes `step_index=0`, `examples_visible=0`, and the ten-call order;
- uses fresh repository/native/provider binding;
- uses the currently qualified visible-output/reasoning-off transport rather than reviving historical hidden-reasoning behavior;
- rejects retry, task repair, seed replacement, or arm-specific transport changes;
- records failed provider attempts as physical work.

That host work is a separate repository transaction. This preregistration deliberately freezes the scientific family before the next physical execution surface is adapted.
