# Production-context unresolved-only diagnostic

Status: deterministic repository support for #2672. This document does not authorize physical execution.

This diagnostic follows #2664, which showed that removing new-State projection responsibility did not restore the formed T2 `unresolved` meaning. The next factor cut asks whether simultaneous Continuity-kind decision work itself suppresses the proposal.

## Held fixed

The diagnostic preserves:

- the authoritative Stage-R T1/T2 inputs;
- ordinary production T1 execution and accepted T1 Continuity entering T2;
- full T2 CognitiveInput, including accepted lifecycle context;
- the actual production T2 Pass 1 response;
- the retained three-field formed observation and run-local Event rebound;
- decoding, explicit reasoning OFF, native structured output and transport fields;
- canonical Continuity candidate wire shape, source validation and epistemic-role validation.

## Factor cut

The existing Continuity-only projection still decides all three Continuity kinds:

```text
referent + unresolved + active_task
```

The unresolved-only diagnostic removes only the model-facing responsibility to decide/project `referent` and `active_task` in T2 Pass 2:

```text
unresolved
```

The native JSON Schema is deliberately **not** narrowed to `kind=unresolved`. It uses the exact same `continuity_candidates` item schema as Continuity-only extraction, so the experiment changes prompt responsibility rather than adding a schema enum hint. Canonical parsing/source validation runs first; diagnostic validation then fails closed if any returned candidate has a non-`unresolved` kind.

## Canonical composition

`src/relaylm/providers/openai_compatible_extraction_projection.py` owns structured Continuity instruction fragments. Existing production and Continuity-only modes render the complete fragment sequence. `UNRESOLVED_ONLY` renders only canonical common + unresolved fragments.

No substring deletion, copied production prompt, monkeypatch, runtime replacement, hidden fallback or alternate provider path is permitted.

The existing production suffix has a fixed regression hash. Existing production and Continuity-only request assembly remain canonical and are not rewritten for the diagnostic.

## Request evidence

The repository diagnostic retains deterministic hashes for:

1. production baseline;
2. production + retained overlay;
3. Continuity-only baseline;
4. Continuity-only + retained overlay;
5. unresolved-only baseline;
6. unresolved-only + retained overlay;
7. an explicit non-model-facing factor-delta receipt.

The retained overlay remains exactly:

```text
subject_span
unknown_evidence_span
source_event_id
```

No expected Continuity kind/key/op/value, scorer label or answer hint may be added.

## Later physical interpretation

Only a separately owned fresh one-shot physical transaction may generate evidence.

```text
valid unresolved-only T2 emits the formed unresolved meaning
  -> strongly supports multi-kind Continuity decision competition

valid unresolved-only T2 still emits [] / materially misprojects
  -> multi-kind projection responsibility is not sufficient
  -> next isolate accepted lifecycle context vs Pass1/full-input burden

invalid parity / provenance / schema / transport
  -> no causal inference
```

A positive discriminator does not authorize a permanent production split or an unresolved-specific product shortcut. #1388 FastCal remains blocked until qualified production evidence satisfies its own gate.

> Keep the context; remove only the competing Continuity decisions.
