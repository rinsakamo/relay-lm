# RelayLM 2.0 Cognitive IR matched-representation experiment

Owning Issue: #2211. Parent reconstruction owner: #2210.

This surface owns the repository-side deterministic admission contract for the
LLM-facing Cognitive IR comparison. It does not define a Memory, Structure, or
Crystallization ontology and does not authorize RelayLM 2.0 architecture.

## Question

The experiment asks whether future LLM cognition benefits from a representation
specifically organized as Memory / Structure / crystallized IR after controlling
for cheaper alternatives carrying the same source experience or the same reusable
semantic information.

The primary null remains:

> The target LLM needs useful semantic information, not a dedicated
> Memory/Structure type.

## Representation arms

The first comparison declares exactly these arms:

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
claims. Later model-facing source extraction must use the matched learning budget
owned by #2211; evaluator truth cannot be promoted into primary evidence.

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

## Provenance and Grounding boundary

R0 source handles identify the exact generated source episodes used by all arms.
They are lineage handles only. They do not assert that a derived semantic rule is
new Evidence or Grounding.

Required invariant:

```text
source episode occurrence
  -> may be referenced by a derived representation

derived semantic representation
  != new grounded occurrence

neutralization / serialization
  != authority escalation
```

The later actual-model campaign must preserve the same rule under real
model-authored summary/cache/Structure formation.

## Cost boundary

R0 records exact UTF-8 serialized byte size. It does not estimate tokenizer cost,
reasoning steps, or hidden chain of thought.

S2/S3 later add observable model-facing cost such as:

```text
formation calls/tokens/latency
retrieval/selection work
projected input tokens
model calls/output tokens/latency
revision/invalidation work where tested
```

Natural-cost comparisons charge the actual representation cost. Matched hard
budgets constrain the maximum envelope without adding meaningless filler solely
to equalize token counts.

## Next gate

After R0 repository admission is merged, the next step is a bounded non-citable
S2 actual-model smoke. S2 must replace oracle semantics with fair representation
formation from the same source observations and matched construction budgets.

A later typed-IR claim requires at minimum:

```text
P4 > P6 under held-out behavior/cost
and
semantic intervention effect >> meaning-preserving surface perturbation effect
```

If P6 matches P4, the appropriate result is generic reusable semantics rather
than a dedicated Memory/Structure IR type.

## Architecture consequence

**None.**

A deterministic R0 PASS earns only a clean experiment surface. It does not change
#2132 or RelayLM 1.0 semantics.
