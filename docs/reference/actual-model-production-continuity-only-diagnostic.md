# Production-context Continuity-only extraction diagnostic

This reference defines the repository support for RelayLM 1.0 Issue #2624, a bounded evaluation-only discriminator under #2616 / #2043.

It does **not** change ordinary-turn product semantics and does **not** authorize a physical run by itself.

## Question

The diagnostic tests whether simultaneous new-State extraction and Continuity extraction, or their combined native output schema, contributes materially to the remaining Stage R Continuity lifecycle omission.

Established evidence already shows:

- T2 unknown/open-question semantic formation is present;
- isolated projection of that formed meaning can produce a canonical `unresolved` Continuity set;
- full production extraction with the retained formed observation can still emit no Continuity candidate.

The next discriminator therefore removes one responsibility only.

```text
ordinary production Pass 2
  -> State proposal work
  -> Continuity proposal work
  -> state_candidates + continuity_candidates

Continuity-only diagnostic Pass 2
  -> Continuity proposal work
  -> continuity_candidates
```

Accepted State remains present in `CognitiveInput`. The diagnostic removes only proposal of **new** durable State from this Pass 2 request.

## Canonical factorization

The OpenAI-compatible two-pass provider owns the canonical extraction projection components.

Production and diagnostic requests share:

- `COMMON_SYSTEM_INSTRUCTION`;
- exact serialized `CognitiveInput`;
- exact Pass 1 response framing;
- canonical Continuity rules and examples;
- model, decoding and reasoning fields;
- native structured-output transport;
- current Event source binding.

Production additionally composes the canonical State extraction component and the combined schema. The diagnostic composes only the canonical Continuity component and a strict schema whose sole property is `continuity_candidates`.

The Continuity-only candidate collection schema is deep-derived from the canonical production Continuity collection schema. It is not a copied independent wire contract.

The default production builder remains `ExtractionProjectionMode.PRODUCTION`. Its model-facing prompt and request identity are a behavior-preservation invariant. Source-byte changes to provider qualification inputs may still mechanically advance the Core fingerprint and must be measured from exact-head repository verification rather than guessed.

## Retained formation overlay

The diagnostic reuses the existing production retained-formation overlay contract from #2593 / #2611.

The retained observation contains exactly:

```text
subject_span
unknown_evidence_span
source_event_id
```

The historical source ID is validated against the current Stage R semantic revision, both spans must remain exact substrings of the authoritative T2 input, and `source_event_id` is rebound to the run-local current T2 Event before any model-facing request is built.

The overlay supplies no expected `kind`, `key`, `op`, `value`, scorer label, oracle answer, fixture key, or target Continuity transition.

## Request construction order

Repository support constructs the diagnostic deterministically in this order:

1. build the ordinary production T2 extraction request through the canonical production builder;
2. bind and apply the existing retained formed-observation overlay, producing the production+overlay baseline;
3. build a fresh Continuity-only request through the same canonical builder using `ExtractionProjectionMode.CONTINUITY_ONLY`;
4. apply the exact same retained overlay payload;
5. validate a non-model-facing diff receipt proving the held-fixed fields and intended responsibility removal;
6. after a future physical owner sends the diagnostic request, parse its output through the unchanged canonical candidate parser and source-validation contract.

No production request is transformed by prompt substring deletion, regex surgery, monkeypatching, runtime component replacement, hidden fallback, or an ad-hoc bridge.

## Diff receipt

The repository builder records content-free structural assertions and canonical request-body SHA-256 values for:

- ordinary production request;
- production request with retained overlay;
- Continuity-only request;
- Continuity-only request with retained overlay.

The receipt must establish:

- same system instruction;
- same CognitiveInput and Pass 1 framing;
- same canonical Continuity component;
- same retained overlay;
- same non-projection request fields;
- State extraction component present in production and absent from the diagnostic;
- production schema properties = `state_candidates`, `continuity_candidates`;
- diagnostic schema properties = `continuity_candidates` only.

The intended removed model-facing responsibilities are exactly:

```text
state_extraction_instruction
state_candidates_output_schema
```

## Parser and provenance

A valid diagnostic response has exactly this top-level shape:

```json
{"continuity_candidates": []}
```

Candidate records are parsed by the ordinary canonical candidate parser with an empty State candidate collection. The resulting `CognitionExtractionOutput` then passes the unchanged canonical source-in-CognitiveInput validation.

Invented source Event IDs, extra top-level fields, malformed candidate records, stale retained-source identity, or retained spans that no longer occur in current T2 fail closed.

## Repository-only scope

Issue #2624 performs zero real model/provider/server generations. Unit tests use deterministic synthetic inputs and fakes only.

After this support is merged and current `v1` / Core identity is known, a **separate fresh physical owner** may authorize exactly one bounded diagnostic transaction. Its intended semantic-generation ceiling is:

```text
T1 production Pass1                 1
T1 production Pass2                 1
T2 production Pass1                 1
T2 Continuity-only retained Pass2   1
-------------------------------------
maximum                              4
```

T1 production Pass2 must commit before T2. Formation regeneration, T3, retry, replay, reseed, fallback, FastCal, and LM Studio contact are outside this diagnostic.

## Interpretation

A protocol-valid T2 Continuity-only request that emits the semantically correct unresolved set strongly supports State/Continuity co-extraction or combined-schema interference as a material factor. It does not by itself authorize a permanent production multi-call split.

A protocol-valid request that still omits or materially misprojects the unresolved meaning means removing State extraction responsibility is insufficient. The investigation then moves to the remaining lifecycle-context, multi-kind, Pass1-conditioning, or full-input-volume factors.

An invalid protocol, provenance, retained binding, or T1 production parity provides no causal inference.
