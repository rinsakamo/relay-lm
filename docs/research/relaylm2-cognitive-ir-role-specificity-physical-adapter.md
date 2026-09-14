# RelayLM 2.0 — E4-RS1 common physical adapter

Owner: #2889. Scientific parent: #2211. Preregistration: #2883.
Repository binding: #2884.

This is a zero-GPU binding owner. It consumes the frozen F/C/O E4-RS1
science unchanged and connects it to protected-v2 common physical generation
`relay-common-physical-g2`. It authorizes no THIS-RUN execution.

## Target

```text
target   = v2:semantic-role-specificity
engine   = llama.cpp
resource = llama-cpp:local-gpu
branch   = v2
module   = tools.v2_cognitive_ir_role_specificity_llama_cpp_wsl
required distributions = [httpx]
```

The common generation certificate/aggregate is not modified. Only one row is
added to the llama.cpp target registry.

## Frozen material boundary

Official #2883 family objects do not exist during import, docs, tests, CI, or
common-runner discovery. A scientific family can be generated only from the
exact preregistered `(index, seed)` and a validated `FrozenConsumerIdentity`.
The transaction establishes that identity only after owned live runtime
binding and exactly two successful non-scientific strict `/input_tokens`
preflight requests.

```text
queue / quiescence / final gate
-> owned llama.cpp runtime
-> live binding
-> 2/2 non-scientific strict input-counter preflight
-> FrozenConsumerIdentity
-> official family materialization
-> F/C/O same-semantics equality
-> semantic calls
```

Synthetic paths reject all official preregistered seeds.

## Scientific envelope

```text
families = 24
surfaces = F / C / O
semantic calls = 72
scientific /input_tokens = 144
non-scientific preflight = 2
context = 8192
slots = 1
context shift = false
max output = 256
temperature = 0
reasoning = none/off
seed = omitted/null
stream = false
semantic parallelism = 1
strict native json_schema = true
```

F is the successful function-descriptive nonlexical E4-LX1 vocabulary. C is
readable category/type naming without role-function semantics. O is opaque
`q0..q4`. The repository owner #2884 remains authoritative for exact field
names, field order, forbidden role terms, instruction, wire schema, scorer,
admission and statistics.

`wire_shape_valid` is admission. `semantic_domain_valid` is a scientific
outcome and may be false on an admitted panel.

## Inference

Exactly two confirmatory contrasts exist:

```text
H1 F vs C  role-function specificity
H2 C vs O  generic lexical/category transparency
```

Both use same-family two-sided exact paired McNemar/sign tests, with Holm
across exactly H1/H2 at familywise alpha .05. F-vs-O is descriptive only. No
equivalence margin exists.

## Failure discipline

The two pre-material counter requests are non-scientific. Scientific spend
begins with the first scientific `/input_tokens` attempt or semantic provider
POST attempt. Once spend begins, any incomplete/admission/runtime failure
terminalizes as
`MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND`; partial evidence is
preserved and there is no retry, replay, reseed, fallback, hidden repair,
judge, alternate backend, or completion run.

A live binding check precedes every semantic provider attempt and one final
binding check closes the panel.

## Ownership boundary

```text
PHYSICAL_EXECUTION_AUTHORIZED = False
THIS_RUN = not owned here
provider/model/GPU/server execution in CI = 0
v1/main/primary checkout mutations = 0
architecture_consequence = NONE
```

After this owner is merged, reconciled and closed, a separate exactly-once
physical owner may authorize one common-runner invocation on Local Codex.

Refs #2211 #2883 #2884 #2889 #2871 #2857 #2799.
