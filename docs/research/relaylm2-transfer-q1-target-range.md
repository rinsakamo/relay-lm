# RelayLM 2.0 Q1 Target-Competence Range Qualification

Owner: #2393  
Qualification contract: #2388  
Theory parent: #2145  
Canonical physical procedure: #2363

## Purpose

The terminal #2157 realization showed that a mathematically identifiable target task can still be unusable as a transfer instrument when the actual model sits at floor. Q1 therefore qualifies target-local competence before source acquisition or transfer is purchased.

Q1 asks only:

> Can the frozen model solve the intended target-rule family from target-local evidence at a non-floor, non-ceiling operating point?

It does not measure source acquisition, reusable-Structure benefit, or transfer.

## Stage C — non-citable range calibration

Stage C is one complete frozen transaction:

```text
4 candidates x 4 calibration families x 4 evidence levels = 64 calls
```

Candidate order is frozen:

```text
C0_W2_OFFSET_ONLY
C1_W2_PERMUTATION_OFFSETS
C2_W3_PERMUTATION_OFFSETS
C3_W4_PERMUTATION_OFFSETS
```

All candidates use modulus 10 and evidence levels `(0,1,2,3)`.

Every generated calibration and held-out family is deterministically required to have exactly one hidden rule in the declared hypothesis class after all three visible examples. Model failure therefore cannot be rescued as endpoint underdetermination.

After all 64 calls are durably complete, scan candidates in the frozen order and select the first endpoint in:

```text
0.25 <= endpoint success rate <= 0.75
```

A later candidate with a numerically better endpoint cannot replace the first passing candidate. If none lies in band, terminalize `NO_MEASURABLE_TARGET_RANGE` and do not buy held-out Q1.

Stage C is non-citable calibration and can never satisfy Q1 by itself.

### Why the full ladder completes

`DurableQuestionRun.mark_stopped()` denotes incomplete execution. A planned scientific early stop must not masquerade as execution failure. Stage C therefore completes all 64 frozen calls before applying the first-pass selector.

## Stage Q — citable held-out Q1

Only a successful Stage C selection authorizes Stage Q:

```text
selected candidate x 8 held-out families x 4 evidence levels = 32 calls
```

Calibration and held-out seeds are deterministically disjoint and may not be replaced.

Held-out Q1 uses the frozen endpoint band:

```text
0.25 <= endpoint success rate <= 0.875
```

The upper bound permits 7/8 but rejects an 8/8 ceiling. Stage Q constructs the #2388 `QualificationManifest` and `TargetCompetenceResult`; repository-owned `classify_q1(...)` is the sole gate classifier.

Allowed scientific outcomes:

```text
PASS
FAIL_FLOOR
FAIL_CEILING
INCONCLUSIVE
PROTOCOL_INVALID
```

Q2 and Q3 stay blocked unless held-out Q1 returns `PASS`.

## Declared transformation semantics

The historical #2355 source contract did not define permutation direction. Q1 removes that representation-discovery confound. Model-facing target tasks explicitly declare:

```text
y[i] = (x[permutation[i]] + offsets[i]) mod modulus
```

For C0 the permutation is explicitly identity. For C1-C3 it is an unknown bijection. Offsets are integers inside the modulus.

Thus Q1 measures parameter induction inside a declared rule class, not accidental discovery of the serialization convention.

## Shared future manifest thresholds

Because Q1/Q2/Q3 must later share one #2388 manifest, the inactive downstream thresholds are frozen before Q1 evidence exists:

```text
Q2 minimum families = 8
Q2 exact Structure recovery >= 0.50
Q2 held-out source behavioral competence >= 0.75
Q3 minimum families per regime = 8
Q3 shared gain >= 0.25
Q3 shared-minus-null interaction >= 0.20
```

They have no effect on Q1 but cannot be chosen after Q1 results.

## Package identity

`tools/v2_transfer_q1_target_range.py` owns the ladder, generator, endpoint-identifiability filter, disjoint seed derivation, 64/32 call plans, first-pass selector, explicit rule semantics, variable-width schemas, task-family identity, and #2388 manifest construction.

Seeds are derived from the exact merged package commit supplied as `package_anchor`. Stage C and Stage Q for one realization must use that same package anchor.

`tools/v2_transfer_q1_structured_client.py` consumes the already-qualified strict JSON-Schema mechanism. A call-plan slot is consumed before provider invocation; provider failure is not retried.

## Host-owned physical boundary

`tools/v2_transfer_q1_host.py` follows #2363:

```text
Controller observes and assembles.
Host validates and freezes.
```

The host validates exact repository/static identity, performs the first live binding check, freezes from live launch admission, starts the durable run, and rechecks the material binding before every provider attempt. The controller must not duplicate host freeze or durable initialization.

Complete binding-probe counts are:

```text
Stage C: 1 + 64 = 65
Stage Q: 1 + 32 = 33
```

Stage C records a material model/runtime digest. Stage Q must match it exactly; changing the model/runtime is a new realization.

## Wrong answer vs protocol failure

```text
valid integer array but wrong value
  -> scientific false; continue

invalid JSON / wrong width / non-integer / out-of-range
  -> protocol failure; stop; no later calls
```

No semantic retry, provider retry, fallback, replay, parser repair, schema repair, prompt repair, or seed replacement is legal.

## Anti-tuning

Forbidden:

- changing candidate order or acceptance bands after results;
- adding candidates after calibration and calling it the same Stage C;
- choosing the best observed candidate instead of the first passing candidate;
- reusing calibration seeds in held-out qualification;
- source Structure or evaluator-oracle information in Q1;
- changing model/runtime between Stage C and Stage Q;
- treating Stage C as citable Q1 evidence;
- treating Q1 PASS as transfer evidence.

## Physical ownership

This repository package performs zero real provider/model calls. After merge and post-merge green CI:

1. create a separate exactly-once Stage C physical owner;
2. if Stage C selects a range, create a separate exactly-once Stage Q owner;
3. only held-out Q1 PASS can unblock Q2.

Architecture consequence: **NONE**.

> **Qualify the measurement range before qualifying transfer.**

> **Explore difficulty with a frozen ladder; qualify the selected range on fresh held-out families.**
