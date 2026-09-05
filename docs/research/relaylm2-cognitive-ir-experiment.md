# RelayLM 2.0 Cognitive IR matched-representation experiment

Owning Issue: #2211. Parent reconstruction owner: #2210.

This surface owns the repository-side admission and bounded actual-model protocol
for the LLM-facing Cognitive IR comparison. It does not define a Memory,
Structure, or Crystallization ontology and does not authorize RelayLM 2.0
architecture.

## Question

The experiment asks whether future LLM cognition benefits from a representation
specifically organized as Memory / Structure / crystallized IR after controlling
for cheaper alternatives carrying the same source experience or the same reusable
semantic information.

The primary null remains:

> The target LLM needs useful semantic information, not a dedicated
> Memory/Structure type.

## Representation arms

The comparison declares exactly these arms:

```text
P0_RAW_HISTORY
  source episodes projected directly

P1_RETRIEVAL_ONLY
  episode records remain episode-specific; selected records are exposed

P2_ORDINARY_SUMMARY
  a faithful recap of source episodes without evaluator-supplied reusable rule fields

P3_SEMANTIC_CACHE
  compact reusable semantics without claiming a dedicated Structure type

P4_MEMORY_PLUS_STRUCTURE
  origin handles and reusable response organization are explicitly separated

P5_STRUCTURE_ONLY_RECONSTRUCTABLE
  reusable organization is projected while episode handles remain available only
  through the declared reconstruction path

P6_GENERIC_EQUAL_INFORMATION
  deterministic neutralization of P4 that preserves the same reusable semantic
  distinctions and provenance handles without privileged Memory/Structure/Crystal labels
```

P6 is the strongest type-elimination control. P4 beating raw history or summary
is insufficient to earn a typed IR if P6 matches it at equal or lower total cost.

The S2 P1 fixture currently exposes all source records plus deterministic
selection metadata. It is sufficient to prove retrieval-only representation
transport, but it is **not** a mature target-dependent retrieval baseline. A later
citable comparison that makes retrieval efficacy a primary claim must use a real
predeclared target-dependent selector without leaking evaluator truth.

## R0 deterministic admission

R0 is mechanics-only. It reuses #2157's deterministic generated transfer family
and never makes an actual-model capability claim.

The generated family exposes evaluator-known source-rule semantics. R0 may use
those semantics only as an explicitly quarantined `oracle_upper_bound` fixture to
prove representation integrity. Every R0 arm is marked ineligible for empirical
claims. Model-facing source extraction must instead use the matched learning
budget owned by #2211; evaluator truth cannot be promoted into primary evidence.

R0 proves before any physical model request that all seven arms share source and
target identity, P4 neutralizes deterministically into P6 without semantic loss,
P5 retains reconstruction lineage, raw/retrieval arms do not receive compiled
rule fields, and malformed/information-losing generic forms fail closed.

R0 does **not** prove that an LLM can infer or benefit from a reusable rule, that
a summary/cache is good, that typed IR syntax is behaviorally invariant, or that
any representation deserves architecture authority.

## Typed vs generic semantic identity

P4 and P6 encode one exact reusable semantic payload:

```text
operation
permutation
offsets
modulus
provenance handles
```

P6 is produced only by a deterministic meaning-preserving neutralizer. Both forms
decode to the same canonical semantic payload and therefore the same semantic
digest. This digest is an experiment-integrity device, not a universal
semantic-equivalence oracle for natural language or LLM behavior.

## S2 bounded actual-model smoke

S2 is a **NON_CITABLE** provider/protocol smoke. It replaces the R0 oracle rule
with representations formed only from the same public source observations.

For one family/seed, the physical call schedule is fixed:

```text
formation
  P2 ordinary summary         1 call
  P3 semantic cache           1 call
  P4 reusable-rule extraction 1 call

P0/P1
  direct episode representations
  0 formation calls

P5/P6
  deterministic derivatives of the one P4 learned semantic payload
  0 additional physical formation calls

then
  one target probe for each P0..P6
  7 calls

TOTAL
  10 physical provider calls / family-seed
```

P4 and P6 must not be generated independently. P5 and P6 are deterministic
derivatives of the one P4 formation completion, so representation syntax is not
confounded with independent extraction quality.

### Formation fairness

P2, P3, and P4 receive the same exact model-facing source packet:

```text
modulus
source input/output examples
```

The packet contains no evaluator rule identity, source-rule fingerprint,
`permutation`, or `offsets` fields. Their instructions differ only as the
representation-forming treatment requires.

P2 and P3 are semantic-text controls, not JSON-schema capability tests. Their
non-empty model text is normalized deterministically into the internal
`summary`/`gist` envelope. A model that writes useful recap/gist text without the
requested serialization must not make the entire smoke `INCOMPLETE` merely for
incidental formatting. P4 remains structurally parsed because the explicit
reusable-rule representation is the treatment being instantiated.

P0/P1 pay no semantic-formation call because avoiding compilation is part of
their natural-cost advantage. P4/P5/P6 each carry the counterfactual one-call
formation cost in per-arm accounting even though the physical smoke reuses the
one P4 completion.

### Target fairness

Every arm receives the same public task domain and target packet:

```text
modulus
visible target examples
query
```

This is important: `modulus` is legal public information and must not be present
only inside compiled representations. The target wrapper is identical across
arms except for `prior_context`:

```text
prior_context
  fallible material derived from earlier observations

task
  same public modulus / examples / query
```

Current target examples override stale prior context on conflict. Only
`prior_context` differs across arms; the target task packet and task digest remain
identical.

### What S2 can actually establish

S2 can establish only that:

- each representation can be formed or directly constructed as declared;
- each representation is serialized and projected into a real provider request;
- the provider returns a bounded response under that request;
- P4/P6 semantic identity survives model-authored formation plus deterministic neutralization;
- output parsing/verifying and token accounting work;
- no arm is mechanically broken or silently receiving evaluator truth.

Projection into a provider request is **not proof that model behavior causally
used the representation**. The Issue phrase "every representation is actually
consumed" is interpreted at S2 as transport/projection acceptance, not behavioral
causal dependence. Behavioral consumption requires later intervention/ablation
and belongs to S3 rather than adding extra smoke calls.

### Output and mechanical classification

Target answers use the formal vector-answer contract. Invalid JSON, invalid
shape, or out-of-range values are measured verifier outcomes rather than host
crashes. After all ten calls, classify the smoke mechanically:

```text
any target output has verifier protocol error
  -> OUTPUT_PROTOCOL_DEFECT
  -> S3 blocked

all seven protocol-valid outputs correct
  -> CEILING
  -> S3 blocked

all seven protocol-valid outputs wrong
  -> FLOOR
  -> S3 blocked

mixed correct/wrong, all protocol-valid
  -> MECHANICALLY_DISCRIMINATING
  -> S3 preregistration may begin
```

This prevents malformed output transport from being misreported as a cognitive
floor. None of these S2 classifications is a representation winner verdict.

### S2 cost accounting

Per arm record at minimum:

```text
formation calls
formation input/output tokens
serialized/projected bytes
target calls
target input/output tokens
exact target task digest
formal verifier result
```

The result separately records the physical ten-call count and that P5/P6's
formation cost is the counterfactual shared P4 build cost. Summing arm-level
natural costs must not be mistaken for physical provider-call count.

## Physical host: minimum sufficient harness

S2 is non-citable protocol smoke, not release Qualification. Its host controller
must therefore enforce only predicates needed for causal validity,
reproducibility, or evidence honesty.

Hard requirements are:

```text
exact repository commit/tree + clean checkout
one stable model/backend/runtime identity for the transaction
exact ten-call semantic schedule
retry_policy = automatic_retry:false, semantic_retry:false
same public task across arms
P4/P6 same learned semantic payload
no hidden evaluator truth
terminal stop on material live model-binding drift
repo-external fresh bounded artifact root
truthful NON_CITABLE_S2_SMOKE result
```

Stable facts may be loaded directly from an existing trustworthy local
machine-readable configuration or prepared-environment manifest. They do not
need to be rediscovered through host probing merely because the harness can probe
them.

Per-call live binding is deliberately a declared subset of stable identity. The
default required live field is the loaded `model` identity. A host may add fields
such as backend/runtime when they are independently observable and materially
capable of changing the semantic transaction. Extra observed diagnostic fields
are allowed and do not become acceptance predicates.

The S2 host **does not require** the v1 citable-Qualification
`LiveLaunchAdmissionAttestation`, GPU reservation geometry, capacity-evidence
object, launch-evidence reference, runtime-ownership reference, NVML mechanism,
or a particular process/listener proof. Those may be recorded when material, but
their absence is not an S2 failure.

Operational rule:

```text
freeze semantic/material identity
  !=
freeze every implementation detail

fresh observation only for facts that can actually drift
and materially change the experiment
```

A live-binding failure after the artifact manifest exists is durably recorded as
`INCOMPLETE` with zero or partial provider calls. A repository mismatch/dirty
checkout still fails before a model request. Harness/admission failure is not a
model-performance result.

## Provenance and Grounding boundary

Source handles identify the exact generated source episodes used by all arms.
They are lineage handles only. Model-authored summary/gist/rule is derived
semantics, not new Evidence or Grounding. Neutralization and serialization never
escalate authority. The formal verifier remains evaluator instrumentation unless
a later protocol explicitly exposes a matched feedback occurrence.

## S2 interpretation boundary

S2 is not preregistered citable evidence. A P4 win does not earn a typed IR and a
P6 win does not reject one. Protocol-level defects may be fixed after the smoke;
semantic tuning to rescue a favored arm is prohibited.

If a smoke stops because the harness required an incidental/unavailable host
fact that is not material to the causal comparison, classify that as a
**harness/protocol defect**. Relax/generalize the predicate in a separate fresh
repository transaction before any new smoke. Do not reinterpret it as model
failure and do not silently rescue the same transaction.

## Next gate after S2

Only `MECHANICALLY_DISCRIMINATING` S2 with stable P4/P6 semantic identity may
admit a separately frozen, preregistered S3 semantic-invariance × held-out-reuse
campaign. `OUTPUT_PROTOCOL_DEFECT`, `FLOOR`, `CEILING`, or `INCOMPLETE` blocks S3
and permits only protocol/mechanical diagnosis.

S3 must add the controls that S2 intentionally does not try to prove, including
meaning-preserving surface perturbations versus meaning-changing interventions,
real behavioral-use tests, and a mature target-dependent retrieval-only control
when retrieval efficacy is part of the claim. Arm order should be randomized or
counterbalanced before latency is treated as an outcome.

A later typed-IR claim requires at minimum:

```text
P4 > P6 under held-out behavior/cost
and
semantic intervention effect >> meaning-preserving surface perturbation effect
```

If P6 matches P4, the appropriate result is generic reusable semantics rather
than a dedicated Memory/Structure IR type. If summary or retrieval matches the
reusable representations at lower total cost, crystallization may be reducible
to ordinary retrieval/summary within the declared workload.

## Architecture consequence

**None.**

R0, S2 protocol readiness, and a later non-citable smoke do not change #2132 or
RelayLM 1.0 semantics.
