# RelayLM 2.0 — Semantic Reconstruction Probe

Repository-binding owner: #2722. Preregistration owner: #2709. Scientific parent: #2211. Theory reverse-import owner: #2668.

## Purpose

This is the zero-GPU repository binding for the Relay Theory discriminator that
separates:

```text
A. semantic sufficiency
from
B. bounded consumer accessibility
```

It consumes the scientific contract preregistered by #2709 without redefining
it. It does not test realized use (C) or operational efficacy (D), does not rerun
the full #2211 campaign, and does not authorize architecture mutation.

The causal question is:

> Holding one canonical semantic payload fixed by construction, can one frozen
> finite LLM consumer reconstruct that payload equally from the existing P4
> `MEMORY_PLUS_STRUCTURE` and P6 `GENERIC_EQUAL_INFORMATION` serializations
> under one predeclared, arm-symmetric, resource-accounted, non-oracular
> interface?

## Ownership boundary

```text
#2660 common physical infrastructure = HOW
#2211 / #2709 experiment contract    = WHAT / preregistration
#2722                                = zero-GPU repository binding
future exactly-once physical owner   = THIS RUN
#2668 theory reverse import          = completed result -> scoped Level-D only
```

This binding owns no provider, localhost server, GPU/NVML lifecycle, llama.cpp
process lifecycle, or scientific artifact writer. `PHYSICAL_EXECUTION_AUTHORIZED`
is false.

## Mechanism-control construction

This experiment deliberately removes formation quality as a variable. The
scoring-side evaluator starts from the canonical K3 semantic payload and builds:

```text
P4_MEMORY_PLUS_STRUCTURE
  memory.origin_refs
  structure.operation
  structure.permutation
  structure.offsets
  structure.modulus

P6_GENERIC_EQUAL_INFORMATION
  context.refs
  relation.kind
  relation.a
  relation.b
  relation.n
```

P6 is produced only through the existing `neutralize_typed_payload` path.
Before any model call, the existing canonical decoder and semantic digest must
prove exact P4/P6 semantic equality.

The scored semantic payload is exactly:

```text
operation
permutation
offsets
modulus
provenance_handles
```

The canonical truth and canonical decoder remain scoring-side only. Decoding
P4/P6 into a common canonical form before model exposure is forbidden because
that would place the decoder in the interface and destroy the discriminator.

This oracle mechanism control is not evidence for Crystallization formation,
Memory/Structure ontology, Structure transfer, realized use, or general
cognitive efficacy.

## Access interface

Both arms receive the same system instruction and one user message containing
only the literal serialized representation bytes. The interface is frozen as:

```text
predeclared
arm-symmetric except representation bytes
resource-accounted
non-oracular
reusable across all families
no family-specific hint
no representation-specific helper
no target answer
no evaluator decoder output
no free target-aware preprocessing
```

The completion must be one JSON object containing exactly the five scored
fields. Parsing is deterministic and strict: no missing/extra members,
duplicate JSON members, non-finite constants, semantic repair, model judge, or
arm-specific normalization.

## Fresh-family seed contract

Exactly 16 future K3 families are identified by:

```text
label = relaylm2-cognitive-ir-semantic-reconstruction-v1
seed_i = uint64_be(
  SHA256(label + "|family|" + decimal(i))[0:8]
)
i = 0..15
```

The repository binding verifies exact derivation, uniqueness, and disjointness
from the current historical #2211 seed lineage, including the later G1
certificate-qualification seeds now present on v2.

The binding also verifies the inherited K3 geometry:

```text
difficulty = K3_THREE_ACTIVE
active coordinates = 3
vector width = 4
modulus = 10
source examples = 4
target steps = 4
shift index = 2
```

The exact 16 scientific family objects are intentionally not generated here.
They may be instantiated only after the later exactly-once physical owner has
freshly frozen the consumer/model/runtime identity. Unit-test fixtures in this
binding are synthetic contract fixtures and are not scientific evidence.

## Call and resource contract

Exactly:

```text
16 families x 2 arms = 32 semantic completions
one completion per arm/family
semantic retry = 0
replay = 0
reseed = 0
fallback = 0
hidden repair call = 0
judge/model grading call = 0
```

Frozen scientific envelope:

```text
context limit = 8192
max output tokens = 256
temperature = 0
reasoning = none/off
request seed = null
parallel semantic slots = 1
```

The later physical owner must freeze the exact model artifact/hash,
tokenizer/chat template, runtime/provider build, GPU/material identity,
transport, launch parameters, fresh v2 SHA/tree, and empty artifact destination
before scientific spend. If the qualified runtime cannot implement this
envelope without changing scientific meaning, execution must stop before spend.

## Outcomes and costs

Primary endpoint:

```text
full_payload_exact
```

Preregistered diagnostics only:

```text
core_rule_exact
provenance_exact
parse_valid
```

Observable cost vector:

```text
input_tokens
output_tokens
model_calls
wall_clock_seconds
representation_bytes
representation_tokens
```

Each scientific arm/family cell must account for exactly one model call.

## Paired inference

Pair P4 and P6 within each of the same 16 semantic families and report:

```text
both correct
P4 only
P6 only
both wrong
raw paired accuracy difference
```

Primary test:

```text
two-sided exact binomial / exact McNemar sign test
conditioned on discordant pairs
alpha = 0.05
```

Six discordant pairs all in one direction give two-sided exact `p = 0.03125`.
No equivalence margin is preregistered.

Terminal interpretation:

```text
V0
INVALID_BEFORE_PHYSICAL_EXECUTION

V1
CONSUMER_ACCESSIBILITY_DIFFERENCE_DETECTED_WITHIN_DECLARED_SCOPE
+ SIGNIFICANT_PAIRED_EXACT_TEST

V2
NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION
+ UNDERDETERMINED

V3
PROTOCOL_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND
+ UNDERDETERMINED
```

`p >= 0.05` is not equivalence. Every verdict has
`architecture_consequence = NONE`.

## Grand Null and forbidden inference

Any observed difference is first explained through ordinary bounded consumer
and interface factors such as serialization, tokenization, ordering/locality,
context position, projection/retrieval interface, attention allocation, decoder
complexity, finite model capacity, resource budget, formation/projection cost,
and runtime/sampling.

Never infer automatically:

```text
A -> B
B -> C
C -> D
semantic equality -> equal finite-consumer cost
reconstruction difference -> Memory/Structure primitive
reconstruction difference -> dedicated IR type
reconstruction difference -> realized downstream use
reconstruction difference -> operational efficacy
non-significance -> equivalence
```

A completed physical result may be reverse-imported to #2668 only as a scoped
Level-D empirical result with treatment, held-fixed coordinates, raw paired
outcomes/statistics, costs, Grand Null, forbidden inference, architecture
consequence, and theory pressure. No direct Time/Cosmology export is earned.

Refs #2211 #2660 #2668 #2674 #2677 #2691 #2693 #2695 #2701 #2704 #2709 #2722.
