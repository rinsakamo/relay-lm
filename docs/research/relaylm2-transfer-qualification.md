# RelayLM 2.0 Transfer Precondition Qualification

Owner: #2388  
Theory parent: #2145  
Historical failed realization: #2157 / #2355 / #2376  
Canonical physical procedure: #2363

## Purpose

A learned-Structure transfer experiment is not informative if any of these are false:

1. the model can solve the target task from target-local evidence;
2. the model can acquire the reusable source representation;
3. projecting a correct reusable representation can actually move target behavior.

The #2157 realization reached a complete R2 transaction but failed before transfer itself was measurable: source acquisition was 0/16 and every target curve remained at floor. The remedy is not to retry that campaign. The remedy is to qualify its prerequisites independently before buying another transfer interaction.

> **Qualify the learner and the task before testing transfer between them.**

## Qualification manifest

`tools/v2_transfer_qualification.py` defines one manifest shared by all three gates.

The manifest binds:

```text
qualification version
model/runtime identity digest
task-family identity digest
explicit source-representation semantics
source-representation semantics digest
target evidence levels
predeclared gate thresholds
```

Threshold values are not globally hard-coded by this owner. A future physical qualification must choose them before its model calls and bind them through the manifest digest.

The source representation is not allowed to be only a field schema. Its executable semantics must be present as text and content-addressed by the manifest. For the historical vector-rule realization, an adequate convention is of the form:

```text
y[i] = (x[permutation[i]] + offsets[i]) mod modulus
```

A different future task family may use a different explicit executable convention.

## Q1 — TARGET_COMPETENCE

Q1 isolates target-local capability.

```text
Structure origin = NONE
source reuse = absent
oracle = absent
target-local evidence = present at preregistered levels
```

The result records one success count for every preregistered target-evidence level, plus an endpoint count that must equal the final curve entry. The curve length must exactly match the manifest's evidence-level sequence; a missing or shortened curve is `PROTOCOL_INVALID` rather than sufficient endpoint evidence.

`PASS` requires:

- exact manifest identity;
- protocol-valid and complete evidence;
- a complete adaptation curve over every preregistered evidence level;
- zero seed replacement;
- enough families for the preregistered minimum;
- endpoint success rate at or above the preregistered floor threshold;
- endpoint success rate at or below the preregistered ceiling threshold.

Outcomes below/above the range are `FAIL_FLOOR` / `FAIL_CEILING`.

This does not prove transfer. It proves only that the target task occupies a measurable operating range for the frozen model/runtime while preserving the full adaptation curve needed by later transfer design.

## Q2 — SOURCE_ACQUISITION

Q2 isolates acquisition of reusable Structure from source observations.

```text
Structure origin = MODEL_LEARNED
oracle truth used = false
```

It reports two distinct quantities:

```text
exact Structure recovery
held-out source-task behavioral competence
```

`PASS` requires both to meet their separately preregistered rates. A structurally valid JSON object is not enough. A model that predicts source behavior but uses a different factorization can therefore be diagnosed separately from one that fails the source task itself.

Any evaluator/oracle truth entering Q2 is `PROTOCOL_INVALID` rather than a better acquisition score.

## Q3 — ORACLE_PROJECTION_UPPER_BOUND

Q3 isolates the projection mechanism with a deliberately privileged oracle Structure.

```text
Structure origin = EVALUATOR_ORACLE
scientific role = mechanism upper bound only
```

Matched shared and null regimes compare:

```text
baseline target success
vs
oracle-Structure-projected target success
```

The executable helper computes:

```text
shared_gain = oracle_shared - baseline_shared
null_gain   = oracle_null   - baseline_null
interaction = shared_gain - null_gain
```

`PASS` requires both a preregistered minimum shared gain and a preregistered minimum shared-minus-null interaction. It also requires matched target packets, zero detected target-rule leakage, zero seed replacement, and complete protocol-valid evidence.

An oracle-only win is not learned-transfer evidence and has Architecture consequence = NONE.

## Origins are part of the type

The three gates intentionally use mutually exclusive origins:

```text
Q1 -> NONE
Q2 -> MODEL_LEARNED
Q3 -> EVALUATOR_ORACLE
```

The validator rejects origin substitution. This prevents an oracle Structure from silently satisfying the learned-acquisition gate.

## One manifest, three evidence products

`qualify_for_transfer(...)` issues a `TransferQualificationCertificate` only when:

```text
Q1 == PASS
Q2 == PASS
Q3 == PASS
```

under the exact same manifest digest.

The three gates must cite three distinct evidence products. A future transfer preregistration can consume the certificate as a machine-checkable prerequisite instead of inferring readiness from prose or from a previous full campaign.

## Physical execution boundary

This owner packages only the repository contract. It performs no provider/model call.

Any Q1, Q2, or Q3 physical run is a separate exactly-once Issue and must consume the canonical physical procedure owned by #2363:

```text
.ai/skills/physical-execution-preflight/SKILL.md
docs/reference/relaylm2-physical-execution-preflight.md
```

Do not implement a second controller-side freeze.

## Gate order

The default order is deliberately asymmetric:

```text
Q1 TARGET_COMPETENCE
  -> Q2 SOURCE_ACQUISITION
  -> Q3 ORACLE_PROJECTION_UPPER_BOUND
  -> new learned-transfer preregistration
```

A floor-saturated Q1 blocks spending model calls on downstream gates unless a separately justified repository-only analysis is being performed.

## Failure interpretation

```text
Q1 FAIL_FLOOR
  target task is below the useful measurement range

Q1 FAIL_CEILING
  target task is above the useful measurement range

Q2 FAIL_ACQUISITION
  the learner does not reliably acquire the declared reusable representation

Q3 FAIL_MECHANISM
  even correct reusable Structure does not create the required relation-specific target effect

PROTOCOL_INVALID
  do not reinterpret as scientific failure

INCONCLUSIVE
  do not promote to PASS by narrative
```

A failed gate may motivate a genuinely new experiment design. It never authorizes retrying a completed predecessor as though its seed were unspent.

## Non-goals

- no reopening #2157;
- no rescore of #2355;
- no R3-R6 continuation;
- no automatic model substitution;
- no tuning seeds until a gate passes;
- no oracle-to-learned provenance collapse;
- no architecture promotion;
- no RelayLM 1.0 mutation.

## Working principles

> **Before measuring transfer, prove there is something to transfer, somewhere useful to transfer it, and a mechanism capable of moving it.**

> **Structured output validity is not semantic competence.**

> **Oracle mechanism evidence and learned acquisition evidence are different scientific objects.**

> **A full interaction experiment is downstream of its measurement prerequisites.**
