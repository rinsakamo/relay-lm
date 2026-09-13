# RelayLM 2.0 — E4-RB1 semantic-role binding decomposition

Repository-binding owner: #2831. Preregistration owner: #2830.
Scientific parent: #2211. Forensic trigger: #2825.

## Purpose

The consumed E4-SR2 panel #2815 did not pass its preregistered measurement
admission gate. Its scientific result remains
`MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND / UNDERDETERMINED` and
must not be rescued or rescored.

The zero-call forensic owner #2825 nevertheless established a useful
measurement-treatment interaction: P4 was exact on all 24 families, while P6
contained 13 valid five-key JSON objects whose first frozen rejection was an
invalid permutation, plus seven additional parse-valid cells with core semantic
mismatches. There was no truncation/output-limit evidence.

E4-RB1 is a fresh prospective mechanism-control experiment that asks a narrower
question:

> Does a bounded consumer pay an accessibility cost for recovering semantic
> roles from opaque equal-information aliases, and after semantic roles are
> explicit in neutral language, is there any residual accessibility difference
> attributable to typed Memory/Structure wrapping?

This is not a formation-quality, downstream-task, Crystallization-efficacy,
durable-correction, ontology, or architecture experiment.

## Ownership

```text
#2211   scientific parent
#2830   prospective preregistration / WHAT
#2831   deterministic zero-GPU repository binding
later physical-adapter owner   guarded materialization + common target binding
later physical owner           exactly-once THIS RUN
```

This owner authorizes no provider/model/GPU/server execution.

## Fresh identities

Exactly 24 future family seed identities use:

```text
label = relaylm2-cognitive-ir-semantic-role-binding-v1
seed_i = uint64_be(SHA256(label + "|family|" + decimal(i))[0:8])
i = 0..23
```

Repository validation proves uniqueness and disjointness from the current
historical #2211 seed lineage, including E4-SR2 and E4-IFQ1 identities.

Only seed identities exist in repository/CI. Exact future family objects may be
materialized only after a later physical layer freezes a validated live
consumer/runtime identity. Unit tests use synthetic non-preregistered fixtures.

## Same-semantics surfaces

All three surfaces derive from one canonical K3 payload and must mechanically
decode back to the same payload before any future model call.

### T — TYPED_MEMORY_STRUCTURE

Reuses the existing historical P4 representation:

```text
memory.origin_refs
structure.operation
structure.permutation
structure.offsets
structure.modulus
```

### R — NEUTRAL_ROLE_EXPLICIT

Keeps neutral outer grouping while exposing semantic role names:

```text
context.provenance_handles
relation.operation
relation.permutation
relation.offsets
relation.modulus
```

It contains no `memory`, `structure`, `crystal`, P4, or treatment label.

### O — NEUTRAL_OPAQUE_ROLE_ALIASES

Reuses the historical P6 equal-information neutralization:

```text
context.refs
relation.kind
relation.a
relation.b
relation.n
```

No O-specific legend or decoder is supplied to the model.

For synthetic fixtures the repository requires:

```text
decode(T) == decode(R) == decode(O) == canonical truth
semantic digest(T) == semantic digest(R) == semantic digest(O)
```

The literal serialized bytes remain distinct.

## Shared model-facing instruction

All three surfaces use the existing arm-symmetric reconstruction instruction.
It names only the required output semantic fields:

```text
operation
permutation
offsets
modulus
provenance_handles
```

It does not name T/R/O, Memory/Structure, context/relation, or any surface-specific
mapping. Only the literal representation bytes differ between conditions.

## Prospective wire/domain split

E4-SR2's historical `strict_parse_valid` combined wire parsing with semantic
domain validation. #2825 showed why that is unsuitable for the next experiment:
a P6 completion could already be one valid five-key JSON object yet fail because
its reconstructed permutation was not bijective.

E4-RB1 therefore separates the stages prospectively.

### `wire_shape_valid` — admission layer

The wire parser requires:

```text
one whole-response JSON value
root object
exact five keys
no duplicate members
no non-finite constants
operation string
permutation exactly four integers
offsets exactly four integers
modulus integer
non-empty provenance_handles array of non-empty strings
no surrounding prose/fence
```

It deliberately does **not** require a bijective permutation, correct offsets,
correct modulus value, or canonical semantic equality.

### semantic/domain scoring — scientific outcome

After a valid wire shape, deterministic scoring records:

```text
semantic_domain_valid
full_payload_exact
core_rule_exact
provenance_exact
first deterministic semantic/domain failure or field mismatch
```

Thus `[0,0,0,0]` in the permutation field is wire-valid but a scientifically
wrong semantic reconstruction. This rule applies only to fresh E4-RB1 material
and does not alter #2815.

## Strict structured-output mechanism

E4-RB1 retains the already-qualified native mechanism:

```text
response_format.type = json_schema
json_schema.strict = true
```

Its owner-local schema is intentionally wire/shape-only. In particular it does
not carry IFQ1's `uniqueItems`, integer value bounds, per-family constants,
answer-valued enums, treatment identity, or an input-surface decoder. This
prevents provider-side schema enforcement from hiding the semantic-domain errors
that E4-RB1 is designed to measure.

## Resource and spend envelope

```text
families                    24
surfaces                     3
semantic completions        72
scientific /input_tokens   144
optional pre-material counter 2 non-scientific requests
context                    8192
max output tokens           256
temperature                   0
reasoning              none/off
request seed       null / omitted
semantic parallelism          1
stream                     false
```

All retry/replay/reseed/fallback/hidden-repair/judge counts remain zero.

## Measurement admission

Inferential analysis is allowed only if:

```text
T/R/O canonical semantic equality   24/24
provider attempts/completions       72/72
wire_shape_valid                    72/72
scientific /input_tokens          144/144
truncation/output-limit failures       0
identity/provenance/accounting       PASS
all rescue counters                     0
```

`semantic_domain_valid` is intentionally not an admission gate; it is a measured
outcome.

## Confirmatory questions

Exactly two paired confirmatory tests are preregistered.

### H1 — role-binding cost

```text
R NEUTRAL_ROLE_EXPLICIT
vs
O NEUTRAL_OPAQUE_ROLE_ALIASES
```

### H2 — typed-wrapper residual

```text
T TYPED_MEMORY_STRUCTURE
vs
R NEUTRAL_ROLE_EXPLICIT
```

T-vs-O may be reported descriptively but is not a third confirmatory test.

For H1 and H2, pair exact same-family `full_payload_exact` outcomes and report
`both_correct`, `left_only`, `right_only`, `both_wrong`, raw accuracy
difference, and two-sided exact McNemar/binomial-sign p-value. Holm-Bonferroni
controls familywise alpha 0.05 across exactly H1 and H2.

No equivalence margin exists. Failure to reject is not equivalence.

## Terminal classes

```text
ROLE_BINDING_ACCESSIBILITY_DIFFERENCE_DETECTED
TYPED_WRAPPER_ACCESSIBILITY_DIFFERENCE_DETECTED
MULTIPLE_SURFACE_ACCESSIBILITY_DIFFERENCES_DETECTED
NO_DECLARED_SURFACE_GAP_DETECTED_AT_THIS_RESOLUTION
MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND
INVALID_BEFORE_PHYSICAL_EXECUTION
```

A detected difference is scoped only to the exact consumer/interface/resource
frame. Every terminal class retains:

```text
architecture_consequence = NONE
```

## Repository boundary

This owner binds only seed identities, the three deterministic representation
surfaces, same-semantics decoding, shared prompt, wire/domain split, shape-only
strict schema, 72/144 accounting, paired H1/H2 statistics, Holm correction,
terminal classification, and no-rescue semantics.

It contains no official future family generator, llama.cpp transport,
transaction/WSL wrapper, common target, or physical run.

Never use this owner to rescore #2815, tune prompts from #2815 raw outputs, add
an O-specific decoder, infer Memory/Structure ontology, infer Crystallization
formation efficacy, authorize G2/#2188, or mutate architecture.

Working principle:

> If equal information becomes hard only after semantic roles are renamed
> opaquely, test the role-binding cost before crediting the ontology.

Refs #2211 #2758 #2768 #2769 #2815 #2825 #2830 #2831.
