# E5-RA1 role-accessibility-controlled downstream-use physical adapter

Owner: #2904. Scientific parent: #2211. Preregistration: #2899. Repository binding: #2900.

This adapter is a **zero-GPU binding only**. It authorizes no THIS-RUN physical execution. `PHYSICAL_EXECUTION_AUTHORIZED` remains false in the scientific owner and architecture consequence remains `NONE`.

## Frozen experiment

The physical campaign preserves exactly 24 fresh F_SHARED K3 families. Each family uses one shared model-formed P4 learned-rule completion followed by three matched downstream probes:

1. `TYPED_MEMORY_STRUCTURE`
2. `GENERIC_ROLE_FUNCTIONAL`
3. `LEGACY_GENERIC_ROLE_NEUTRAL`

The exact per-family call order is `FORM_P4 -> T -> G -> L`, for 96 semantic provider calls and 192 scientific `/input_tokens` requests. T/G/L are deterministic projections of the same learned rule and public-source provenance. Their decoded semantics and provenance must be identical before any downstream target call.

H1 is T versus G. H2 is G versus L. Holm-Bonferroni covers exactly those two confirmatory contrasts. T versus L is descriptive only. No equivalence margin exists; non-rejection is not equivalence.

## Runtime binding

The adapter reuses the established S3-R5 llama.cpp rule/vector interface:

- context 8192;
- one slot and one semantic request at a time;
- context shift disabled;
- max output tokens 1024;
- temperature 0;
- reasoning none/off;
- request seed omitted/null;
- stream false;
- strict `json_schema` reusable-rule response for formation;
- strict `json_schema` integer-vector response for downstream probes;
- exactly two `/input_tokens` requests per semantic call.

The earlier E4 `FrozenConsumerIdentity` is intentionally not reused because it freezes a 256-token ceiling. E5-R5 instead owns an immutable E5-specific identity with the same repository/runtime/material fields but a 1024-token output ceiling. Historical E4 code is unchanged.

## Material boundary

Official #2899 family objects remain unmaterialized during import, docs, tests, CI, and help. A live transaction must first acquire the common resource, establish owned llama.cpp/model/GPU/listener identity, pass live binding, complete exactly two non-scientific synthetic strict input-counter requests, and freeze the E5-specific consumer identity. Only then may the exact `(index, seed)` official family be generated.

Synthetic helpers reject every preregistered #2899 seed. Tests use disjoint synthetic seeds only.

## Failure semantics

A wrong but transport-valid target vector is a scientific incorrect outcome, not a repair trigger. Any failure after the first scientific count or semantic POST preserves partial evidence and terminalizes as `MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND`. Retry, replay, reseed, fallback, hidden repair, model judge, and alternate backend/model/interface are all zero.

## Common runner target

The single registered target is:

```text
target   = v2:role-accessible-generic
branch   = v2
module   = tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_wsl
resource = llama-cpp:local-gpu
required distributions = [httpx]
```

The WSL wrapper verifies `relay-common-physical-g2` and its aggregate identity before delegating to the established common lifecycle. `.ai/physical/common_generation.json` and all certified common-generation bytes are unchanged by this owner.
