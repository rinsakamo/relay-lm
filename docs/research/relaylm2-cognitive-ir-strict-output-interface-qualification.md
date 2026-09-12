# RelayLM 2.0 — E4-IFQ1 strict-output interface qualification

Repository-binding owner: #2744. Preregistration owner: #2742. Scientific parent: #2211.
Forensic trigger: #2736. Common physical HOW: #2660.

## Purpose

#2736 established that the consumed #2732 semantic-reconstruction panel was
fully censored by a shared output-format failure before the frozen parser could
reach root/schema/domain validation. All 32 completions used fenced JSON while
the scientific parser required one bare JSON value.

E4-IFQ1 therefore asks only whether one already-supported native structured
output interface can remove that measurement floor on fresh **non-treatment**
material.

This repository binding is deterministic and zero-GPU. It does not execute the
qualification and does not compare P4 with P6.

## Ownership

```text
#2211  scientific parent
#2736  immutable forensic trigger
#2742  preregistration / scientific WHAT
#2744  repository binding / deterministic mechanics
#2660  common physical HOW
future physical-adapter owner  runtime materialization + common target binding
future physical owner          exactly-once THIS RUN
```

`PHYSICAL_EXECUTION_AUTHORIZED` is false in this binding.

## Frozen non-treatment design

Exactly 18 future case identities are derived from:

```text
label = relaylm2-cognitive-ir-semantic-reconstruction-interface-qualification-v1
seed_i = uint64_be(SHA256(label + "|case|" + decimal(i))[0:8])
i = 0..17
```

The repository validates identity derivation, uniqueness, and disjointness from
the historical #2211 seed lineage. It does **not** instantiate the exact 18
future payload objects. A later physical-adapter owner may materialize those
objects only after live consumer/runtime identity has been frozen.

Repository/CI tests use synthetic non-preregistered payloads only.

## Neutral model-facing material

The eventual runtime payload has exactly the visible fields:

```text
operation
permutation
offsets
modulus
provenance_handles
```

It is a neutral K3-shaped reference object used only for output-interface
qualification. It is not a P4 or P6 representation and must not contain
Memory/Structure/generic-treatment surfaces.

The request asks the model to copy the values already visible in one
`REFERENCE_PAYLOAD` into the output object. This tests strict format compliance
plus trivial visible-value carriage, not latent semantic reconstruction.

## One candidate interface

There is exactly one interface and no ladder:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "relaylm2_e4_ifq1_reference_payload_v1",
    "strict": true,
    "schema": "<mechanical five-field schema>"
  }
}
```

The schema constrains only mechanical shape/domain. It contains no per-case
answer values, no exact permutation/offset/provenance values, and no treatment
decoder.

The current direct llama.cpp S3 transport already supports this native
`json_schema` shape. The physical adapter must reuse that transport capability
rather than inventing a second structured-output mechanism.

## Resource envelope

The later physical execution is frozen to:

```text
context                 8192
max output tokens       256
temperature             0
reasoning               none/off
request seed            null / omitted
semantic parallelism    1
stream                   false
semantic completions    18
/input_tokens requests  36
```

The 36 input-token requests are inherited from the exact direct llama.cpp
accounting contract: each semantic call counts the full request plus empty
message framing.

Retries, replay, reseed, fallback, hidden repair, and model judge are all zero.

## Deterministic parsing and scoring

The binding requires one strict whole-response JSON object, rejects duplicate
members and non-finite constants, requires exactly the five declared keys, and
applies the bounded K3-shaped field/domain checks.

Per case it reports:

```text
strict_parse_valid
visible_payload_copy_exact
failure_reason / field-domain diagnostic
```

`visible_payload_copy_exact` compares output only with the values explicitly
present in the same neutral request. No hidden evaluator truth is involved.

No historical #2732 output is imported or rescored.

## Admission

A completed future panel earns `STRICT_OUTPUT_INTERFACE_QUALIFIED` only if:

```text
strict_parse_valid             18/18
visible_payload_copy_exact     >= 17/18
provider completions           18/18
/input_tokens                  36/36
all rescue counters            0
truncation/output-limit fails  0
identity/accounting gates      PASS
```

A completed panel that misses a gate is
`STRICT_OUTPUT_INTERFACE_FAILED`. A post-spend incomplete panel is
`QUALIFICATION_INCOMPLETE`. A pre-spend capability/binding stop is
`PRE_WRAPPER_MECHANICAL_BLOCKED`.

Every outcome remains:

```text
citable_for_representation_claim = false
architecture_consequence = NONE
```

## Interpretation boundary

Even a PASS establishes only that this common output surface is non-floor for
fresh later design. It does not establish:

```text
P4 == P6
P4 != P6
consumer semantic accessibility
semantic reconstruction
Memory/Structure efficacy or ontology
G2 eligibility
#2188 eligibility
architecture authority
```

A PASS may license only a new prospective semantic-reconstruction accessibility
preregistration with fresh identities and the same qualified arm-symmetric
output interface.

A FAIL must not be rescued by plain-text fallback, fence stripping, a second
schema, threshold relaxation, or reuse of the same 18 cases.

## Repository boundary

This owner contains only:

- seed identity and collision-fence mechanics;
- one mechanical native response schema;
- neutral request construction;
- strict parser / visible-copy scoring;
- exact accounting and outcome classification;
- synthetic-only deterministic tests.

It contains no official 18-case material generator, no llama.cpp transaction,
no WSL launcher, no common target registration, and no provider/model/GPU call.

Refs #2211 #2660 #2732 #2736 #2742 #2744.
