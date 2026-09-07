# RelayLM 2.0 Cognitive Work — R2 structured-output preregistration

Status: **design-only preregistration; no physical execution authorized**.

Owner: #2304. Parent experiment: #2187.

## Why a third R2 identity exists

Two earlier scientific transactions terminated fail-closed at the first task's representation boundary before a complete R2 result existed:

- #2288: numeric JSON answer rejected by the historical string-only parser;
- #2300: the repaired scalar protocol produced one fenced JSON object, classified by #2301 as `WRAPPER_ONLY_PROTOCOL_DEFECT`.

#2302 then qualified provider-side JSON-Schema structured output on deliberately non-R2 prompts: 12/12 whole-response strict JSON, schema validation, RelayLM parser validation and `finish_reason=stop`, with zero wrapper/prose defects, binding drift, retries, fallbacks or repairs.

The next scientific suite therefore changes the measuring transport, not the scientific question.

## Scientific invariance

This preregistration reuses the accepted predecessor's scientific functions and message constructors directly.

Frozen science remains:

```text
5 hidden regimes x 8 tasks = 40 tasks
operations = ZERO / THINK / RETRIEVE / OBSERVE
A0 = fixed THINK
A1 = cheap deterministic heuristic
A2 = actual-model allocator
A3 = offline evaluator oracle
shared operation bank
physical call plan = 136 calls
  40 BASE
  40 A2_ALLOCATE
  40 BANK:THINK
   8 BANK:RETRIEVE
   8 BANK:OBSERVE
resource accounting = predecessor contract
oracle = Pareto frontier then fixed non-scientific operation priority
paired exact tests / paired bootstrap = predecessor contract
material thresholds / interpretation categories = predecessor contract
```

No regime frequency, semantic policy, threshold, oracle rule, expected-answer rule or statistical decision rule is retuned from the incomplete runs.

## Fresh unseen seed

The new root-seed domain is:

```text
relaylm2-2187-r2-structured-output-v3
```

The root seed is derived only from:

```text
new root-seed domain
+
this preregistration's final squash-merge commit SHA
```

The branch/PR head is not seed authority. The concrete root seed and preregistration digest are recorded only after merge.

This guarantees a third suite identity distinct from the original and replacement seed domains.

## Qualified transport identity

The preregistration hard-binds the accepted #2302 protocol evidence:

```text
qualification version = relaylm2-cognitive-work-sopq-v1
answer schema = sha256:d7f69ea25824f613d0b60198abe050adc66a3bf45d9f2045d1997214a55498e5
operation schema = sha256:acabff40467f48996033a4be6ee02dbfa97755bbfaf45ee1dd94cea5afeb720d
answer response_format = sha256:e7a71f6a15e7cc936df664f19e3729cbffce6562dbebcb5e69e8f9cfd070639b
operation response_format = sha256:a41031db0de0e912ded0fae8e8fb9687507debb6bcc86a286cfa0051de8afa76
qualification plan = sha256:e6bc9ddaa46ddd6e44d44fabb40e26ab6850542bf0a26b8908750caff77f88b5
qualification result artifact = sha256:1b0972ed92e6e3a8afad38c43b547877881935c7e7fe2318926677543aba8ed8
qualification identity = sha256:dcd432572adb8716d187dd899a0417ae0ff55ffb56047c53b25ea98e239268de
qualified execution binding = sha256:8cad3e68cf6bfe1c4ea6db3d925569815c3326462fd1c359d2da073f5b8ca9d6
```

Per physical call:

```text
BASE / BANK      -> qualified answer JSON Schema
A2_ALLOCATE      -> qualified operation JSON Schema
```

The exact `response_format` mapping comes from the merged #2302 package. No `json_object` fallback, prompt-only fallback, code-fence stripping, embedded-object recovery or schema substitution is part of this preregistration.

The answer schema constrains representation to a non-empty string-compatible object before RelayLM parsing. This is an instrumentation constraint; expected answers remain evaluator-only.

## Information boundary

The predecessor message constructors are reused unchanged.

Therefore:

- hidden regime and expected answer stay evaluator-only;
- retrieval/observation packets are absent before the corresponding selected external operation;
- A2 sees only public task information, the base answer and declared legal-operation descriptions;
- A3 remains offline and model-invisible.

## Budget and retry boundary

The existing R2 budget remains:

```text
physical provider call max = 136
treatment call ceiling per deployable arm = 120
retrieval units per arm <= 8
observation units per arm <= 8
context limit = 8192
aggregate input-token ceiling = none
aggregate output-token ceiling = none
automatic retry = false
semantic retry = false
```

No historical 500-token smoke envelope is restored.

## What merge does not authorize

Merging #2304 means only that the third scientific identity is preregistered.

It does not authorize:

```text
provider calls
semantic generations
R2 campaign invocation
physical authorization
#2288/#2300 replay or resume
allocator efficacy claim
production scheduler
architecture mutation
v1 mutation
```

After merge, a separate host owner must hard-bind the exact merged preregistration commit/root/digest and the qualified structured-output transport. Only after that host separately merges and passes deterministic qualification may a one-shot physical execution owner exist.

> Change the measuring transport, not the scientific question.

> A fresh proof seed must be born after the measuring instrument is frozen.

> Metacognition must pay rent.
