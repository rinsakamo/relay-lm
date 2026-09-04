# RelayLM 2.0 transfer experiment — deterministic R0 contract

This document is the current repository authority for the deterministic R0 surface owned by #2157.

It does not record actual-model evidence and it does not authorize physical execution by itself. The purpose of R0 is narrower:

> **Prove that the transfer experiment can generate matched task/evidence trajectories and isolate cross-task Structure eligibility without hidden information, hidden work, or evaluator authority leaks before an LLM is introduced.**

The upstream experimental hypothesis and physical campaign remain owned by #2157 and #2145. The clean matched-intervention substrate remains owned by #2155.

## Boundary

R0 is deterministic and model-free.

It may create test-only objects for:

- hidden procedural task rules;
- public task packets;
- exact verifier results;
- T0/T1/T2 arm assembly;
- task/evidence identity digests.

Those objects are experiment apparatus, not new persistent cognition.

The canonical cognition used by R0 remains the current #2135 semantic substrate. Projection/resource/intervention mechanics remain the current #2155 harness.

## Procedural task family

R0 uses a small deterministic vector-transformation family only to test experimental integrity.

A hidden rule is a fixed-width permutation plus modular offsets. The exact generator is deterministic from:

```text
seed
+ stable generator labels
+ SHA-256 derivation
```

It does not depend on Python process randomness.

The four evaluator-side relation regimes are:

```text
shared
  source and target use the same hidden rule

null
  target rule is independently derived and differs from source

mismatch
  target rule is a deterministic near-but-wrong variant of source

shift
  early target steps use the source rule;
  later target steps switch to a distinct rule at a predeclared index
```

These regime labels and hidden rule fingerprints are evaluator metadata. They must not appear in model-facing task packets.

## Model-facing packet

Every target step serializes one generic packet:

```json
{
  "instruction": "Infer the transformation from the examples. Return only a JSON integer array.",
  "examples": [
    {"input": [0, 1, 2, 3], "output": [4, 5, 6, 7]}
  ],
  "query": [1, 2, 3, 4]
}
```

The concrete values vary deterministically.

Forbidden model-facing metadata includes:

```text
regime identity
arm identity
hidden rule name/fingerprint
expected answer
shift label/index
source-to-target evaluator mapping
```

The examples themselves are legitimate task Evidence; anti-leakage does not mean hiding information the declared task protocol intentionally supplies.

## Hidden verifier

The verifier parses only a JSON integer array of the declared width and checks it against the evaluator-side hidden transformation.

Verifier output is instrumentation.

```text
verifier says correct
  != Evidence

model response
  != Evidence

score / parse error
  != canonical State
```

No verifier function accepts a semantic store, and deterministic tests assert that verification leaves canonical semantics/provenance unchanged.

## R0 oracle Structure boundary

R0 installs one synthetic source Structure root only to exercise the intervention mechanism:

```text
r0_oracle_source_structure(...)
```

This is deliberately an oracle/mechanism-smoke fixture.

It is **not** evidence that an LLM learned, inferred, or crystallized reusable Structure from source examples. The primary actual-model claim in #2157 still requires a real source-learning path before citable transfer evidence is allowed.

Do not promote an R0 win into learned-transfer evidence.

## Matched arms

All three arms clone the same canonical pre-target snapshot.

```text
T0
  source Structure remains active/auditable
  cross-task projection disabled

T1
  same source Structure
  cross-task projection enabled

T2
  same as T1 before any declared revision
```

At R0 start require identity of:

```text
canonical snapshot
source Structure semantic id
target-local semantic id
public target task digest
target Evidence schedule digest
resource envelope when one is supplied
```

T0/T1 may differ only in the #2155-declared projection surfaces:

```text
allow_cross_task
projected_roots
```

T1/T2 are byte/identity-equivalent before a declared revision.

## Target Evidence schedule

Every target step has a deterministic feedback observation containing only:

```text
query input
observed correct output
```

plus deterministic slot/time/source metadata.

For `shift`, T1 and T2 must receive the exact same post-shift observation identity before any revision policy is allowed to diverge.

An extra observation in one arm changes provenance/canonical digest and must be rejected by matched-arm diffing.

## Resource discipline

R0 consumes #2155 `ResourceLedger` / `ResourceVector`.

A synthetic envelope may account:

```text
calls
input_tokens
output_tokens
latency_units
observation_units
retrieval_units
memory_units
```

R0 asserts both:

- overspending the envelope fails closed;
- an undeclared resource-total difference appears as a contaminated matched-arm surface.

Synthetic units are not physical runtime measurements.

## Deterministic R0 acceptance

R0 is complete only when the repository tests prove:

1. identical seed/regime generates identical hidden/public task family;
2. a different seed changes the public target trajectory;
3. hidden verifier accepts the exact answer and rejects wrong/malformed output;
4. model-facing packets contain no forbidden evaluator metadata;
5. `shared`, `null`, `mismatch`, and `shift` satisfy their predeclared hidden relation;
6. T0/T1/T2 start from identical canonical cognition and task/Evidence identities;
7. T0 preserves source Structure while only cross-task eligibility is disabled;
8. T1/T2 receive identical contradictory shift Evidence identity;
9. hidden extra work exceeds or contaminates the declared resource surface;
10. hidden extra observation contaminates provenance/canonical identity;
11. model response and verifier output remain non-authoritative.

A failure is experiment-design evidence. Do not weaken the matching rules merely to reach R1.

## What R0 does not prove

R0 does not prove:

- transfer exists;
- reusable Structure helps an LLM;
- a model can learn useful Structure;
- revision improves recovery;
- any resource-efficiency claim;
- any Intelligence or General Intelligence claim.

It only earns the right to attempt R1.

## R1 physical boundary

R1 remains a separate bounded actual-model smoke under #2157.

Immediately before any physical model run, reacquire fresh:

```text
v2 commit/tree
experiment runner commit and clean status
model artifact identity/revision/hash
runtime/provider build/config
loaded model identity
tokenizer/chat-template/context limits
sampling/reasoning controls
hardware/GPU/VRAM/NVML where material
output/run identity
```

R0 repository PASS is not a substitute for that host authority.

> **Keep the substrate fixed. Change only eligibility. Then see whether the right prior Structure makes new competence cheaper.**
