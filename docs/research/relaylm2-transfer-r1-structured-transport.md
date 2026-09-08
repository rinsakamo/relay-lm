# RelayLM 2.0 transfer R1 — structured-output transport

This surface is owned by #2157 and records the model-output transport selected for its bounded non-citable R1 actual-model smoke.

It does **not** change the transfer hypothesis, T0/T1/T2 intervention, task generator, source-learning semantics, verifier, or resource accounting. It changes only how already-required JSON syntax is constrained at the provider boundary.

## Why this transport exists

The historical R1 substrate can parse a strict model-authored source Structure object and strict target integer arrays, but its original OpenAI-compatible client sent only prompt instructions requesting JSON.

Later #2300/#2301 evidence isolated a wrapper-only output-protocol defect under prompt-only JSON, and #2302 qualified provider-side JSON-Schema structured output as the mechanical transport for the same LM Studio / Gemma lineage.

Therefore R1 must not knowingly repeat the weaker measuring instrument.

> **Constrain syntax at the transport; do not teach the parser to guess.**

## Preserved scientific boundary

Unchanged:

```text
source examples
  -> one model-authored reusable Structure hypothesis
  -> ordinary governed commit with source Evidence support
  -> one common pre-target canonical snapshot

T0
  same learned Structure retained canonically
  cross-task projection disabled

T1
  same learned Structure
  cross-task projection enabled

T2
  same as T1 for the R1 smoke
```

The R1 smoke remains non-citable and performs exactly four model calls:

```text
1. source-learning
2. T0 target probe
3. T1 target probe
4. T2 target probe
```

No retry, fallback, replay, parser repair, or semantic repair is introduced by structured transport.

## Qualified transport reuse

R1 reuses the HTTP implementation already qualified by #2302:

```text
tools.v2_cognitive_work_structured_output_qualification
  .OpenAICompatibleStructuredOutputClient
```

The R1 adapter is:

```text
tools.v2_transfer_r1_structured_client
  .OpenAICompatibleR1StructuredClient
```

The adapter does not copy the HTTP implementation. It supplies an explicit response format to the qualified client and converts the returned completion into the existing #2157 `ExperimentCompletion` value.

It adds no temperature, top-p, seed, max-token, reasoning, stop, or tool override. Those physical settings remain frozen separately by the R1 execution identity.

## Frozen schema sequence

Transport version:

```text
relaylm2-transfer-r1-structured-v1
```

Underlying qualified mechanism:

```text
relaylm2-cognitive-work-sopq-v1
```

Call sequence:

```text
source_structure
  -> target_answer
  -> target_answer
  -> target_answer
```

The adapter rejects a fifth call instead of extending the smoke implicitly.

### Source Structure schema

For task modulus `m`, the first completion is constrained to one object with exactly:

```text
permutation
  integer array length 4
  each value 0..3

offsets
  integer array length 4
  each value 0..m-1

modulus
  integer enum [m]
```

`additionalProperties = false`.

The existing #2157 strict parser still verifies the permutation is actually bijective and that the proposal satisfies the declared semantic contract. JSON Schema owns syntax, not semantic authority.

### Target answer schema

Each of the three target completions remains the historical raw representation expected by the verifier:

```text
integer array length 4
items in 0..m-1
```

No wrapper object is introduced, so the scientific prompt/verifier contract is not redefined merely to fit the transport.

## Physical identity

`transport_identity(modulus)` exposes content-derived identities for the later physical owner:

```text
transport_version
qualified_mechanism
modulus
call_sequence
source_schema_name
target_schema_name
source_schema_digest
target_schema_digest
source_response_format_digest
target_response_format_digest
sequence_digest
```

The physical execution owner must include these values inside its `structured_output` binding and require live equality like every other material binding field.

## Failure semantics

The adapter advances its sequence slot before invoking the provider. If that provider/protocol call fails, the surrounding fail-closed R1 host terminates the smoke. The adapter never retries the same slot.

Invalid structured content is still rejected by the existing #2157 parser/verifier. Do not add:

```text
code-fence stripping
prose extraction
embedded JSON recovery
schema fallback
plain-output retry
alternate parser
```

## Evidence boundary

A successful structured R1 smoke establishes only that:

- the model can produce one usable source Structure proposal from source examples;
- the existing governed source-learning path can commit it with grounded source lineage;
- T0/T1/T2 target probes can execute under one frozen physical identity;
- projected Structure is mechanically consumable by the target prompt;
- the strict protocol/verifier remains stable.

It does not establish positive transfer, generality, Intelligence, or architecture value. Those remain R2+ questions under #2157/#2145.

## Architecture consequence

**NONE.**

This is measuring-instrument hardening only. It earns no persistent `Structure` type, scheduler, memory system, or RelayLM 1.0 mutation.

> **Reuse the measuring instrument already qualified.**

Refs #2157 #2145 #2334 #2302 #2301 #2300
