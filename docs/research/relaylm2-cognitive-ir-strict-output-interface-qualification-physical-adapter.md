# E4-IFQ1 strict-output interface qualification — physical adapter

Authority owner: #2748. Scientific parent: #2211. Preregistration: #2742. Deterministic repository contract: #2744. Common physical execution HOW: #2660.

This surface makes the prospective **NON_CITABLE, non-treatment** strict-output qualification executable through the shared llama.cpp runner. It does not authorize THIS RUN and does not test P4/P6, Memory/Structure efficacy, G2, #2188, or architecture.

## Frozen scientific envelope

The adapter consumes the #2742/#2744 contract unchanged:

```text
cases                         18
semantic completions          18
scientific /input_tokens      36
interface                     one native json_schema, strict=true
context                       8192
max output tokens             256
temperature                   0
reasoning                     none/off
request seed                  omitted/null
semantic slots                1
stream                         false
strict_parse_valid gate       18/18
visible_payload_copy_exact    >=17/18
retry/replay/reseed/fallback/repair/judge = 0
citable_for_representation_claim = false
architecture_consequence      NONE
```

The JSON Schema controls only mechanical shape/domain. Per-case answers are not encoded in it.

## Material boundary

Repository import, test discovery, `--help`, common-target resolution, and mechanical preflight must not instantiate the exact preregistered 18 payload objects.

The official order is:

```text
fresh clean exact protected-v2 checkout
 -> common #2660 target dispatch
 -> executable/model/runtime preflight
 -> one owned llama.cpp launch
 -> live health/models/props/slots freeze
 -> synthetic structured /input_tokens preflight (2 non-scientific requests)
 -> immutable FrozenConsumerIdentity
 -> ONLY THEN materialize exact 18 neutral payloads
 -> 18 sequential native-json-schema semantic calls
 -> 36 scientific /input_tokens requests
 -> deterministic #2744 strict parsing + visible-copy scoring
 -> final live binding check
 -> immutable result/manifest/receipt
```

The official generator requires both a validated `FrozenConsumerIdentity` and the exact preregistered `(index, seed)` relation. The synthetic test helper rejects every preregistered IFQ1 seed.

Neutral case material contains only:

```text
operation = affine_permutation
permutation = deterministic permutation of 0..3
offsets = four values with exactly three nonzero values in 1..3
modulus = 10
provenance_handles = deterministic opaque strings
```

It contains no P4/P6 serialization, Memory/Structure treatment label, or hidden semantic decoder.

## Native llama.cpp transport

The direct adapter reuses the existing no-retry S3 llama.cpp client and exact input accounting. Each scientific request carries the exact #2744 `response_format()` and frozen decoding envelope. Input accounting remains two non-generative `/input_tokens` requests per semantic call.

Before scientific materialization, the transaction sends only a **synthetic** input-token counter request pair carrying the same strict response format. This is mechanical capability/accounting evidence, not a model generation and not part of the 36 scientific requests.

## Common target

After #2748 is merged, the public target is:

```bash
python -m tools.relay_physical_run --target v2:strict-output-interface-qualification
```

The common registry routes to the dedicated WSL wrapper, then transaction layer. Operators must not call the material generator, direct scientific runner, llama-server, or localhost endpoints manually.

A later separate exactly-once physical owner must authorize one invocation. #2748 itself authorizes zero provider/model/GPU execution.

## Failure and interpretation

Before semantic spend, inability to prove the required repository/runtime/interface envelope is a mechanical block. After semantic spend begins, protocol/runtime failure preserves completed evidence and yields `QUALIFICATION_INCOMPLETE`; there is no rescue or second interface in the same transaction.

A clean PASS can establish only that the strict output interface is usable for this bounded neutral carriage test. It cannot establish P4/P6 accessibility, semantic reconstruction, Memory/Structure type value, native-output cognitive efficacy, Grounding, G2, #2188, or architecture mutation.

Architecture consequence: **NONE**.
