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

## R0 deterministic admission

R0 is mechanics-only. It reuses #2157's deterministic generated transfer family
and never makes an actual-model capability claim.

The generated family exposes evaluator-known source-rule semantics. R0 may use
those semantics only as an explicitly quarantined `oracle_upper_bound` fixture to
prove representation integrity. Every R0 arm is marked ineligible for empirical
claims. Model-facing source extraction must instead use the matched learning
budget owned by #2211; evaluator truth cannot be promoted into primary evidence.

R0 proves the following before any physical model request:

1. all seven arms share the exact source-history identity;
2. all seven arms share the exact public target-task identity;
3. all seven arms preserve the same source provenance handles;
4. P4 deterministically neutralizes into P6 without semantic loss;
5. P6 contains no privileged `memory`, `structure`, or `crystal` role labels;
6. semantically irrelevant object ordering and neutral key substitution preserve
   the canonical semantic digest;
7. changing a real reusable-rule component changes the semantic digest;
8. P5 retains an out-of-band reconstruction path while not projecting episode
   handles directly;
9. P0/P1 preserve episode records without receiving compiled rule fields;
10. the deterministic P2 fixture remains an episode recap rather than an oracle
    rule dump;
11. serialized byte size is recorded as representation cost rather than forced
    equal through filler.

R0 does **not** prove:

- that an LLM can infer a useful reusable rule;
- that a summary or semantic cache is good;
- that P4/P5/P6 change model behavior;
- that typed IR syntax is semantically invariant for a real model;
- that crystallization reduces Cognitive Work;
- that any representation deserves architecture authority.

## Typed vs generic semantic identity

R0 defines one exact reversible semantic payload for the deterministic upper-bound
fixture:

```text
operation
permutation
offsets
modulus
provenance handles
```

P4 serializes this payload using explicit Memory/Structure roles. P6 is produced
only by a deterministic meaning-preserving neutralizer:

```text
P4 typed payload
  -> validate exact fields and values
  -> remove privileged role labels
  -> neutral relation/context keys
  -> P6 generic payload
```

Both forms decode to the same canonical semantic payload and therefore the same
semantic digest. If any field is dropped, malformed, or changed, R0 fails closed.

This digest is an experiment-integrity device, not a universal semantic-equivalence
oracle for natural language or LLM behavior.

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

This deliberately separates two questions:

```text
semantic compilation efficacy
  source episodes -> a reusable semantic quotient

representation-type efficacy
  same learned quotient as typed P4 vs neutralized P6
```

P4 and P6 **must not** be generated independently. They share one exact learned
semantic payload, and P6 is produced only by deterministic neutralization. P5 is
derived from that same learned rule while keeping episode provenance available
only through its reconstruction handles.

### Formation fairness

P2, P3, and P4 receive the same exact model-facing source packet:

```text
modulus
source input/output examples
```

The packet contains no evaluator rule identity, source-rule fingerprint,
`permutation`, or `offsets` fields. Their system instructions differ only as the
representation-forming treatment requires:

```text
P2
  strong faithful concise recap; may preserve supported recurring patterns

P3
  compact future-reusable semantic gist; may infer supported regularity

P4
  explicit reusable vector-rule hypothesis
```

All three use the same physical model/runtime during a smoke and one maximum
formation call each. The provider-reported input/output token costs are charged.

P0/P1 pay no semantic-formation call because avoiding compilation is part of their
natural-cost advantage. P4/P5/P6 each carry the counterfactual one-call formation
cost in per-arm accounting even though the paired smoke physically reuses the one
P4 completion to isolate representation syntax.

### Target fairness

Every representation is placed under the same neutral target wrapper:

```text
prior_context
  fallible material derived from earlier observations

task
  same target examples/query
```

The wrapper does not tell the model that a particular arm is preferred. Target
examples explicitly override stale prior context on conflict. Only
`prior_context` differs across arms; the target task packet and task digest remain
identical.

The first bounded smoke may use zero or a small number of visible target examples
to avoid ceiling saturation. Exact vector verification remains evaluator-side.
A wrong answer is a measured model result, not new Evidence.

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

The physical smoke also records the fixed provider-call count. No hidden
chain-of-thought steps are estimated.

P5/P6 sharing the physical P4 formation completion does not make their build cost
zero. Their arm-level natural cost remains the cost required to produce the
learned semantic payload they consume.

### S2 interpretation boundary

S2 can establish only that:

- all representation protocols can be formed/serialized/projected;
- the model/provider can consume the bounded task protocol;
- P4/P6 semantic identity survives real model-authored formation followed by
  deterministic neutralization;
- output parsing/verifying and token accounting work;
- no arm is mechanically broken, context-overflowing, or silently receiving
  evaluator truth.

S2 is not preregistered citable evidence. A P4 win in S2 does not earn a typed IR,
and a P6 win does not yet reject one. Protocol-level defects may be fixed after
the smoke; semantic tuning to rescue a favored arm is prohibited.

## Provenance and Grounding boundary

Source handles identify the exact generated source episodes used by all arms.
They are lineage handles only. They do not assert that a derived semantic rule is
new Evidence or Grounding.

Required invariant:

```text
source episode occurrence
  -> may be referenced by a derived representation

derived semantic representation
  != new grounded occurrence

model-authored summary/gist/rule
  != Evidence

neutralization / serialization
  != authority escalation
```

The formal verifier remains evaluator instrumentation unless a later protocol
explicitly exposes a feedback occurrence identically across matched arms.

## Cost boundary

Natural-cost comparisons charge actual representation formation, projection, and
model costs. Matched hard budgets constrain the maximum envelope without adding
meaningless filler solely to equalize token counts.

Later S3/S4 work may add:

```text
retrieval/selection latency
wall-clock request latency
revision/invalidation work
storage lifecycle cost
resource-pressure variants
```

but S2 stays bounded to protocol viability.

## Next gate after S2

Only after a bounded physical S2 smoke succeeds should #2211 freeze a
preregistered S3 semantic-invariance × held-out-reuse campaign.

A later typed-IR claim requires at minimum:

```text
P4 > P6 under held-out behavior/cost
and
semantic intervention effect >> meaning-preserving surface perturbation effect
```

If P6 matches P4, the appropriate result is generic reusable semantics rather
than a dedicated Memory/Structure IR type.

If P2 or retrieval matches the reusable representations at lower total cost, the
appropriate result may be crystallization reducible to ordinary
retrieval/summary within that declared workload.

## Architecture consequence

**None.**

R0 PASS and S2 protocol readiness earn only a clean experiment surface. A later
non-citable smoke also does not change #2132 or RelayLM 1.0 semantics.
