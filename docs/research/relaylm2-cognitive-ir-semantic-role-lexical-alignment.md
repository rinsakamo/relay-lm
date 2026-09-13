# RelayLM 2.0 — E4-LX1 lexical alignment × semantic role

Repository-binding owner: #2848. Preregistration owner: #2847.
Scientific parent: #2211. Triggering admitted physical result: #2837.

## Purpose

E4-RB1 #2837 produced one admitted same-semantics accessibility panel:

```text
T typed Memory/Structure       24/24 full exact
R neutral role-explicit        24/24 full exact
O neutral opaque aliases        6/24 full exact
```

The preregistered R-vs-O contrast survived Holm correction; the typed-vs-R
contrast did not. This is bounded consumer-accessibility evidence only.
It does not establish a Memory/Structure ontology, formation efficacy,
general transfer, or architecture value.

One confound remains. E4-RB1's R input used the exact output-role key tokens:
`operation`, `permutation`, `offsets`, `modulus`, and `provenance_handles`.
A bounded model may therefore have benefited from literal input-output key
alignment rather than, or in addition to, semantic-role information.

E4-LX1 isolates that residual confound before the role-accessibility result is
credited as semantic invariance.

## Ownership

```text
#2211   scientific parent
#2847   prospective preregistration / WHAT
#2848   deterministic zero-GPU repository binding
later physical-adapter owner   guarded official materialization + target
later physical owner           exactly-once THIS RUN
```

This owner authorizes no provider/model/GPU/server execution.

## Fresh identities

Exactly 24 future family seed identities use:

```text
label = relaylm2-cognitive-ir-semantic-role-lexical-alignment-v1
seed_i = uint64_be(SHA256(label + "|family|" + decimal(i))[0:8])
i = 0..23
```

Repository validation fixes the exact #2847 values, proves uniqueness, and
rejects overlap with the current historical #2211 seed lineage inherited
through E4-RB1, E4-SR2, and IFQ1.

Only seed identities exist here. Exact official family objects may be
materialized only after a later physical layer has frozen and validated a live
`FrozenConsumerIdentity`. Unit tests use synthetic non-preregistered fixtures.

## Same-semantics neutral surfaces

All three surfaces derive deterministically from one canonical K3 payload and
must decode to that exact payload before any future semantic call.

### E — NEUTRAL_ROLE_EXACT_LEXEMES

E reuses the E4-RB1 role-explicit neutral representation:

```text
context.provenance_handles
relation.operation
relation.permutation
relation.offsets
relation.modulus
```

These names intentionally match the required output-role lexemes.

### D — NEUTRAL_ROLE_DESCRIPTIVE_NONLEXICAL

D preserves semantic role descriptiveness while removing exact output-key
overlap:

```text
context.source_handles
relation.transform_kind
relation.index_reordering
relation.additive_shifts
relation.modular_divisor
```

Evaluator-side decoding is frozen as:

```text
source_handles      -> provenance_handles
transform_kind      -> operation
index_reordering    -> permutation
additive_shifts     -> offsets
modular_divisor     -> modulus
```

The model never receives this map as a legend. The semantic value
`affine_permutation` is unchanged because E4-LX1 manipulates key-role lexemes,
not answer values.

### O — NEUTRAL_OPAQUE_ROLE_ALIASES

O reuses the E4-RB1 opaque neutral representation:

```text
context.refs
relation.kind
relation.a
relation.b
relation.n
```

No D-specific or O-specific decoding legend is model-visible.

For every synthetic fixture:

```text
decode(E) == decode(D) == decode(O) == canonical truth
semantic digest(E) == semantic digest(D) == semantic digest(O)
```

Literal serialized surfaces remain distinct.

## Shared consumer instruction

All surfaces reuse the exact E4-RB1 reconstruction instruction. It may name
only the required output fields:

```text
operation
permutation
offsets
modulus
provenance_handles
```

It does not identify E/D/O or expose any input-to-output mapping rule. Only the
literal representation bytes differ across conditions.

## Strict wire/domain split

E4-LX1 preserves the prospective E4-RB1 measurement split.

`wire_shape_valid` is admission-only. It checks one exact five-key JSON object,
basic field types, vector widths, duplicate/nonfinite rejection, and absence of
surrounding prose.

Semantic correctness remains a measured outcome:

```text
semantic_domain_valid
full_payload_exact
core_rule_exact
provenance_exact
first deterministic mismatch/domain failure
```

A shape-valid non-bijective permutation is therefore wire-valid but
scientifically wrong.

The response interface remains native strict JSON schema:

```text
response_format.type = json_schema
json_schema.strict = true
```

The schema is wire/shape-only. It must not encode expected answer values,
permutation bijection, treatment identity, or evaluator decoding truth.

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

## Measurement admission

Inferential analysis is allowed only if:

```text
E/D/O canonical semantic equality   24/24
provider attempts/completions       72/72
wire_shape_valid                    72/72
scientific /input_tokens          144/144
preflight, when implemented           2/2
truncation/output-limit failures       0
identity/provenance/accounting       PASS
all rescue counters                     0
```

`semantic_domain_valid` is deliberately not an admission gate.

## Confirmatory questions

Exactly two paired confirmatory tests are exposed.

### H1 — literal lexical-alignment effect

```text
E NEUTRAL_ROLE_EXACT_LEXEMES
vs
D NEUTRAL_ROLE_DESCRIPTIVE_NONLEXICAL
```

This tests whether exact reuse of output-key lexemes changes
`full_payload_exact` after role meaning remains explicit.

### H2 — role descriptiveness without exact overlap

```text
D NEUTRAL_ROLE_DESCRIPTIVE_NONLEXICAL
vs
O NEUTRAL_OPAQUE_ROLE_ALIASES
```

This tests whether descriptive role names still change accessibility after exact
output-key overlap is removed.

E-vs-O is descriptive only and receives no third confirmatory p-value.

For H1 and H2, report same-family paired tables, raw paired accuracy
difference, and a two-sided exact McNemar/binomial-sign p-value. Apply
Holm-Bonferroni across exactly H1 and H2 at familywise alpha 0.05.

No equivalence margin exists. Non-rejection is not equivalence or sufficiency.

## Terminal classes

```text
LEXICAL_FORM_ACCESSIBILITY_DIFFERENCE_DETECTED
ROLE_DESCRIPTION_ACCESSIBILITY_DIFFERENCE_DETECTED
MULTIPLE_LEXICAL_ROLE_ACCESSIBILITY_DIFFERENCES_DETECTED
NO_DECLARED_LEXICAL_ROLE_GAP_DETECTED_AT_THIS_RESOLUTION
MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND
INVALID_BEFORE_PHYSICAL_EXECUTION
```

Every terminal class retains:

```text
architecture_consequence = NONE
```

## Repository boundary

This owner binds only seed identities, the three deterministic neutral
surfaces, same-semantics decoding, the shared consumer instruction, E4-RB1's
wire/domain scorer and shape-only schema, 72/144 accounting, H1/H2 paired
statistics, Holm correction, terminal classification, and zero-rescue
semantics.

It contains no official future family generator, llama.cpp transport,
transaction/WSL wrapper, common target, or physical run.

Never use this owner to replay/rescore #2837, tune D names from #2837 raw
completions, add D/O mapping hints, infer equivalence from non-rejection,
infer Memory/Structure ontology, infer Crystallization formation efficacy, or
mutate architecture.

Working principles:

> If role-explicit representation wins, remove exact-key copying before
> crediting semantic roles.

> Same meaning should survive a change of names; otherwise the representation
> may be a prompt surface, not an IR.

Refs #2211 #2193 #2173 #2837 #2847 #2848.
