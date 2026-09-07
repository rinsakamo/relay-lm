# RelayLM 2.0 — #2211 pre-S2 calibration forensic

This surface defines the bounded **zero-provider forensic** applied only after a
completed `NON_CITABLE_S2_CALIBRATION` transaction.

It exists to answer a narrower question than calibration admission:

> Given the frozen calibration cases and the already-recorded visible structured
> completions, where did application, rule formation, or end-to-end use fail?

The forensic does **not** rerun the model, change thresholds, select an S2
representation arm, or create architecture authority.

## Inputs

The forensic consumes one completed calibration artifact root containing:

- `calibration-result.json`;
- `request-evidence.jsonl`.

`calibration-result.json` preserves the frozen coordinates and pass/fail booleans.
`request-evidence.jsonl` preserves the 72 visible structured responses as
`instrumentation_only` evidence. The deterministic calibration generator in
`src/relaylm/v2_cognitive_ir_calibration.py` reconstructs the true rule, examples,
query, and expected answer for every seed/difficulty cell.

No provider, LM Studio, GPU, or network access is required or permitted by the
forensic implementation.

## Integrity checks

Before analysis the forensic fails closed unless:

- the source claim remains `NON_CITABLE_S2_CALIBRATION` / `citable=false`;
- the frozen seed, difficulty, and probe sets are unchanged;
- the source provider-call count is exactly 72;
- all 24 calibration cells are present exactly once;
- all 72 request-evidence records occur in the frozen call order;
- every evidence record is `instrumentation_only` and has non-empty visible content;
- all evidence records belong to at most one run id / identity fingerprint;
- recomputing the result booleans from visible evidence exactly matches
  `calibration-result.json`.

A mismatch is an artifact-integrity failure, not a model result.

## Descriptive failure geometry

For each seed × difficulty cell the report reconstructs:

- true permutation, offsets, modulus, query, and expected answer;
- C0 application answer and answer Hamming distance;
- C1 inferred rule and permutation/offset Hamming distance;
- C2 inferred rule, answer, and both deltas;
- structural case features:
  - moved permutation positions;
  - permutation cycle lengths;
  - non-zero offset count and offset sum;
  - query wrap-around count;
  - example count and total example wrap-around count.

The report emits descriptive flags only:

- `APPLICATION_FAILURE`;
- `FORMATION_FAILURE`;
- `END_TO_END_RULE_FAILURE`;
- `END_TO_END_ANSWER_FAILURE`;
- `FORMATION_GAIN_WITH_QUERY_CANDIDATE` when C1 is wrong but the C2 rule is exact;
- `FORMATION_LOSS_WITH_QUERY_CANDIDATE` when C1 is exact but the C2 rule is wrong;
- `ANSWER_CORRECT_UNDER_WRONG_RULE`;
- `RULE_CORRECT_ANSWER_WRONG`;
- `FULL_CELL_SUCCESS`.

The `*_WITH_QUERY_CANDIDATE` labels are deliberately non-causal. The original
calibration did not randomize query presence within the same provider sample, so
the forensic may identify a pattern but may not claim that the query caused the
change.

## Cross-difficulty diagnostics

The report keeps the original admission thresholds intact and expresses them as
integer count margins for the six frozen seeds. It also reports:

- difficulties with C0 application floor (`0/6`);
- later predeclared difficulty positions whose C0 count is greater than an
  earlier position (`application_nonmonotonic_pairs`);
- cells showing candidate C1→C2 rule-formation gain or loss.

A non-monotonic pair does not prove a general capability ordering. It only shows
that this completed calibration does not empirically realize a monotone C0
application curve under the predeclared ordering.

## Interpretation boundary

Every forensic report is forced to:

```text
claim_status             = NON_CITABLE_S2_CALIBRATION_FORENSIC
citable                  = false
provider_calls_added     = 0
causal_effect_claims     = false
threshold_retuning       = unauthorized
S2 authorization         = false
architecture consequence = NONE
```

In particular:

- a near miss does not permit post-hoc threshold relaxation;
- a C1/C2 pattern does not establish a task-conditioning effect;
- a D0/D1 inversion does not justify renaming or reordering the frozen v1
  calibration after seeing the result;
- a forensic report cannot unblock S2 by itself.

Its legitimate use is to design a **separate, preregistered calibration-v2** on
new independent cases after the failure geometry is understood.

## Invocation

Run against the historical artifact **read-only** and write any report outside
that artifact root:

```bash
python -m tools.v2_cognitive_ir_calibration_forensic \
  --artifact-root /tmp/<completed-calibration-root> \
  --output /tmp/relaylm-2211-calibration-forensic.json
```

Omit `--output` to print canonical JSON to stdout. The output path is opened
exclusively and is never allowed to overwrite an existing report.

The source artifact is not modified.
