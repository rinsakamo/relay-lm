# RelayLM 2.0 transfer experiment — R0 integrity + R1 actual-model substrate

This document is the current repository authority for the transfer experiment surface owned by #2157.

It records repository-side experiment mechanics. It does **not** record actual-model evidence and does not authorize physical execution from repository state alone.

The upstream experimental hypothesis and physical campaign remain owned by #2157 and #2145. The clean matched-intervention substrate remains owned by #2155, and canonical semantic governance remains owned by #2135.

## R0 — deterministic integrity contract

R0 is deterministic and model-free. Its purpose is narrower than transfer itself:

> **Prove that the transfer experiment can generate matched task/evidence trajectories and isolate cross-task Structure eligibility without hidden information, hidden work, or evaluator authority leaks before an LLM is introduced.**

It may create test-only objects for:

- hidden procedural task rules;
- public task packets;
- exact verifier results;
- T0/T1/T2 arm assembly;
- task/evidence identity digests.

Those objects are experiment apparatus, not new persistent cognition.

The canonical cognition used by R0 remains the current #2135 semantic substrate. Projection/resource/intervention mechanics remain the current #2155 harness.

### Procedural task family

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

### Model-facing packet

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

### Hidden verifier

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

### R0 oracle Structure boundary

R0 installs one synthetic source Structure root only to exercise the intervention mechanism:

```text
r0_oracle_source_structure(...)
```

This is deliberately an oracle/mechanism-smoke fixture.

It is **not** evidence that an LLM learned, inferred, or crystallized reusable Structure from source examples. Do not promote an R0 win into learned-transfer evidence.

### Matched arms

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

### Target Evidence schedule

Every target step has a deterministic feedback observation containing only:

```text
query input
observed correct output
```

plus deterministic slot/time/source metadata.

For `shift`, T1 and T2 must receive the exact same post-shift observation identity before any revision policy is allowed to diverge.

An extra observation in one arm changes provenance/canonical digest and must be rejected by matched-arm diffing.

### Resource discipline

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

### Deterministic R0 acceptance

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

## R1 — bounded actual-model repository substrate

R1 is a **non-citable actual-model smoke**. Its repository substrate establishes a real source-learning path instead of reusing the R0 oracle root.

The source-learning order is fixed as:

```text
source examples
  -> observed Evidence
  -> same physical model proposes a Structure hypothesis
  -> proposal remains endogenous
  -> ordinary #2135 governance with observed-support lineage
  -> committed reusable Structure
  -> establish target-local root
  -> clone the same post-source/post-target-start snapshot into T0/T1/T2
```

The model response itself is not Evidence. The semantic transaction that accepts a proposal records an endogenous `produces` lineage supported by the observed source Evidence records.

### R1 learned Structure representation

For the current formal vector family, the bounded experiment represents the model-authored reusable hypothesis canonically as:

```text
learned_transfer_structure_hypothesis(
  permutation(...),
  offsets(...),
  modulus(...)
)
```

This is an **experiment-specific semantic representation**, not a new RelayLM architecture primitive or a claim that general Structure must use this schema.

The model may produce a wrong but structurally valid hypothesis. RelayLM does not replace it with evaluator truth. That wrong prior is part of the measured cognition and may later produce negative transfer.

Malformed, duplicate-member, non-standard JSON, extra-field, non-bijective, out-of-range, or protocol-modulus-mismatched hypotheses fail closed.

### R1 source prompt boundary

The source-learning model receives only:

- the declared modulus;
- source input/output examples;
- a generic instruction to return the formal hypothesis shape.

It does not receive:

- transfer regime;
- target task data;
- hidden rule fingerprint;
- target rule;
- arm identity;
- evaluator correctness annotations.

### R1 matched target arms

The committed learned Structure remains active in all three arms.

```text
T0
  same canonical learned Structure
  cross-task projection disabled

T1
  same canonical learned Structure
  cross-task projection enabled

T2
  same as T1 before any declared revision
```

The target-local task root is established before cloning the three arms, so the starting canonical snapshot is identical.

Projection is recomputed from the current store after the target-local root exists. Do not reuse the pre-target R0 `ProjectionResult` as a post-mutation cache.

### Model-facing Structure projection

Canonical semantic IDs are not treated as useful LLM context by themselves.

When the learned source root is projection-eligible, R1 reconstructs the experiment-specific hypothesis from the committed canonical semantic expression and serializes that meaning to the model. It does not read the evaluator's hidden source rule or a side-car copy of model output.

T0 receives the same target task packet with `reusable_structure = null`; T1/T2 receive the same target packet plus the same reconstructed learned hypothesis before revision.

The model-facing instruction explicitly treats reusable Structure as a **fallible prior**, not truth. Supplied target Evidence may override it.

### Starting-capability probe

R1 supports a zero-target-example probe:

```text
examples_visible = 0
```

This allows the campaign to distinguish:

- target-local/raw starting capability;
- immediate effect of projected learned Structure;
- later adaptation after target Evidence is exposed.

The target task packet and task digest remain identical across matched arms for the same step/evidence count. Only the declared reusable-Structure eligibility differs.

### Provider boundary and accounting

The bounded R1 adapter uses OpenAI-compatible Chat Completions without importing RelayLM 1.x cognitive-turn semantics.

It requires:

- exactly one returned choice;
- successful `stop` finish when a finish reason is present;
- non-empty assistant content;
- provider-reported prompt/input token usage;
- provider-reported completion/output token usage.

Missing or malformed usage fails closed rather than being silently counted as zero. Calls and token counts become experiment resource instrumentation; they do not mutate canonical cognition.

A target probe snapshots canonical cognition/provenance before the model request and verifies that request, response parsing, and hidden scoring do not change either surface.

### What R1 repository readiness does not prove

Repository GREEN for R1 does not prove:

- that any physical model can infer the source hypothesis reliably;
- that projected Structure helps;
- that transfer exists;
- that the task protocol is not floor/ceiling saturated for a selected model;
- that revision improves shift recovery;
- any citable transfer effect;
- any Intelligence or General Intelligence claim.

R1 physical smoke remains necessary.

## Physical execution boundary

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

### R1 host admission

The R1 host runner reuses the existing `external_qualification` frozen-identity and durable-run substrate. It does not define a second manifest/resume format.

Before the first model request it must:

1. deep-snapshot the proposed experiment identity before invoking any live probe, so caller mutation cannot alter the later frozen contract;
2. observe the local repository commit/tree and require a clean checkout;
3. require the fresh durable artifact root to resolve **outside** that checkout, so the runner cannot dirty its own frozen repository while generating evidence;
4. obtain a **live** physical binding covering model, artifact, tokenizer, template, backend, runtime, decoding, reasoning, structured-output mode, context capacity, hardware, and launch/admission facts;
5. compare every material binding field with the snapshotted proposed identity;
6. freeze the identity against the live launch/admission attestation;
7. derive the per-call expected physical binding from that frozen identity and create the fresh empty durable artifact root, which writes `run-manifest.json` before any model request.

The host execution order is fixed:

```text
source-learning
  -> T0
  -> T1
  -> T2
```

One client is used across the four calls. The full physical binding is reacquired and compared immediately before every call. Binding drift fails closed before the request. The per-call expectation comes from the already frozen identity; later mutation of the caller's original identity object cannot change it.

The physical probes are authority boundaries, not convenience inputs. A local execution wrapper must derive repository state from the current checkout and physical binding from the current loaded runtime/model/hardware. It must **not** satisfy a probe by copying values back out of the proposed manifest or a historical handoff.

Provider or model-protocol failure stops the run and persists instrumentation. Automatic retry, semantic retry, alternate-model fallback, and silent decoding/protocol mutation are forbidden. The current R1 entrypoint starts fresh only; it does not reinterpret the generic durable infrastructure's exact-resume capability as permission to regenerate source learning.

Raw requests, model responses, token counts, verifier results, binding checks, and failures are instrumentation-only. They do not become canonical Evidence merely because they are durably persisted.

A completed host run reports only:

```text
NON_CITABLE_R1_SMOKE
```

Completion means that the bounded physical wiring executed under one frozen identity. It is not a citable transfer effect and does not authorize R2 conclusions.

Repository CI is not a substitute for host authority. Actual GPU/vLLM/LM Studio execution must preserve the exact host/model/runtime identity and record failures rather than silently changing protocol or decoding until the experiment wins.

> **Keep the substrate fixed. Change only eligibility. Then see whether the right prior Structure makes new competence cheaper.**