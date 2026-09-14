# RelayLM 2.0 — E4-RS1 role-function specificity × lexical transparency

Repository-binding owner: #2884. Preregistration owner: #2883.
Scientific parent: #2211. Triggering admitted physical result: #2871.

## Purpose

E4-LX1 #2871 admitted one same-semantics panel:

```text
E exact required-role lexemes        24/24 full exact
D descriptive nonlexical roles       24/24 full exact
O opaque aliases                      1/24 full exact

H1 E vs D  Holm p = 1.0                 non-reject
H2 D vs O  Holm p = 4.76837158203125e-7 reject
```

That result rules out literal required-output-key overlap as a sufficient
explanation for the earlier role-explicit advantage. It does not establish
E=D equivalence because E and D were both at ceiling.

A residual confound remains: D's names (`index_reordering`,
`additive_shifts`, `modular_divisor`, etc.) are strongly function-specific.
D > O can therefore reflect either semantic role-function information or
generic readable/category labeling. E4-RS1 separates those components.

## Ownership

```text
#2211   scientific parent
#2883   prospective preregistration / WHAT
#2884   deterministic zero-GPU repository binding
later physical-adapter owner   guarded official materialization + target
later physical owner           exactly-once THIS RUN
```

This owner authorizes no provider/model/GPU/server execution and does not
register a common physical target.

## Fresh seed identities

Exactly 24 future family seed identities use:

```text
label = relaylm2-cognitive-ir-role-specificity-v1
seed_i = uint64_be(SHA256(label + "|family|" + decimal(i))[0:8])
i = 0..23
```

Repository validation fixes the exact #2883 values, proves uniqueness, and
rejects overlap with the repository-declared historical #2211 lineage,
including E4-LX1 and its predecessors.

Only seed identities exist here. Exact official family objects may be
materialized only after a later physical layer freezes a validated live
consumer/runtime identity. Unit tests use synthetic non-preregistered payloads.

## Same-semantics surfaces

All surfaces preserve identical `context` / `relation` grouping, the same
semantic-slot order, canonical payload, and provenance meaning. None reuses a
required output key as a whole input field name.

### F — ROLE_FUNCTION_DESCRIPTIVE_NONLEXICAL

F reuses the successful E4-LX1 D vocabulary exactly:

```text
context.source_handles
relation.transform_kind
relation.index_reordering
relation.additive_shifts
relation.modular_divisor
```

### C — CATEGORY_DESCRIPTIVE_ROLE_NEUTRAL

C exposes only readable broad category/type labels:

```text
context.text_list
relation.text_value
relation.integer_list_one
relation.integer_list_two
relation.integer_value
```

The labels deliberately avoid role-functional terms such as permutation,
offset, modulus, provenance, source, transform, reorder, shift, add, wrap, or
base. They identify stable readable slots, not target roles.

### O — OPAQUE_ROLE_ALIASES

O uses stable opaque aliases:

```text
context.q0
relation.q1
relation.q2
relation.q3
relation.q4
```

No arm-specific decoder legend is model-visible.

For every synthetic fixture:

```text
decode(F) == decode(C) == decode(O) == canonical truth
semantic digest(F) == semantic digest(C) == semantic digest(O)
```

Literal serialized surfaces remain distinct. JSON insertion order is
preserved so semantic-slot position is held fixed across F/C/O.

## Shared consumer interface

All surfaces reuse the E4-LX1 reconstruction instruction and strict wire-only
JSON schema. The instruction may name only required output fields:

```text
operation
permutation
offsets
modulus
provenance_handles
```

It never exposes F/C/O treatment identity or evaluator mappings.

`wire_shape_valid` is the admission gate. Semantic correctness remains a
scientific outcome, including:

```text
semantic_domain_valid
full_payload_exact
core_rule_exact
provenance_exact
```

A shape-valid non-bijective permutation remains wire-valid but scientifically
wrong.

## Resource and spend envelope

```text
families                    24
surfaces                     3
semantic completions        72
scientific /input_tokens   144
pre-material counter          2 non-scientific, if retained
context                    8192
max output tokens           256
temperature                   0
reasoning              none/off
request seed       null / omitted
semantic parallelism          1
stream                     false
```

Retry, replay, reseed, fallback, hidden repair, and model judge remain zero.

## Confirmatory questions

Exactly two paired confirmatory tests are exposed.

### H1 — role-function specificity

```text
F ROLE_FUNCTION_DESCRIPTIVE_NONLEXICAL
vs
C CATEGORY_DESCRIPTIVE_ROLE_NEUTRAL
```

This asks whether function-specific semantic-role labels change
`full_payload_exact` when both arms are readable and neither copies required
output-key lexemes.

### H2 — generic lexical/category transparency

```text
C CATEGORY_DESCRIPTIVE_ROLE_NEUTRAL
vs
O OPAQUE_ROLE_ALIASES
```

This asks whether readable generic slot/category labels change accessibility
without supplying role-function semantics.

F-vs-O is descriptive only and receives no third confirmatory p-value.

For H1/H2 use same-family paired tables and a two-sided exact
McNemar/binomial-sign test. Holm-Bonferroni applies across exactly H1/H2 at
familywise alpha 0.05. No equivalence margin exists; non-rejection is not
equivalence.

## Terminal classes

```text
ROLE_FUNCTION_SPECIFICITY_DIFFERENCE_DETECTED
GENERIC_LEXICAL_TRANSPARENCY_DIFFERENCE_DETECTED
MULTIPLE_ROLE_ACCESSIBILITY_COMPONENTS_DETECTED
NO_DECLARED_ROLE_SPECIFICITY_GAP_DETECTED_AT_THIS_RESOLUTION
MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND
INVALID_BEFORE_PHYSICAL_EXECUTION
```

Every terminal class retains:

```text
architecture_consequence = NONE
```

## Repository boundary

This owner binds only the fresh seed identities, deterministic F/C/O
surfaces, same-semantics decoding, shared consumer interface, wire/domain
measurement split, 72/144 accounting, H1/H2 paired statistics, Holm
correction, terminal classifications, and zero-rescue semantics.

It contains no official future family generator, llama.cpp transport,
transaction/WSL wrapper, common target, or physical run. It may not replay
#2871 or infer Memory/Structure ontology, Crystallization formation efficacy,
general transfer, G2/#2188 success, equivalence, or architecture value.

Working principle:

> If readable labels help, distinguish "the model can parse this slot" from
> "the model understands this slot's semantic role."

Refs #2211 #2883 #2884 #2871 #2847 #2848 #2857 #2193 #2173.
