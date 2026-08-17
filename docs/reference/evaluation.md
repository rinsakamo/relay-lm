# RelayLM Native Evaluation

RelayLM evaluation distinguishes visible response quality from State, authority, continuity, and persistence correctness.

```text
response correctness
  != State correctness
  != authority correctness
  != continuity correctness
  != persistence correctness
```

The current repository includes a small native evaluation foundation. It is intentionally not a leaderboard or composite quality score.

## Current command

After installing the package:

```bash
relaylm-eval
```

The command runs the currently registered deterministic native scenarios and prints a machine-readable JSON report. The process exits successfully when every scenario passes and non-zero when the report status is `fail`.

## Report shape

The current report uses `format_version: 1` and suite identity `relaylm-native`.

Conceptually:

```json
{
  "format_version": 1,
  "suite": "relaylm-native",
  "status": "pass",
  "scenarios": [
    {
      "id": "provider_failure_safety",
      "status": "pass",
      "checks": [
        {
          "id": "provider_called_once",
          "boundary": "provider",
          "passed": true,
          "expected": 1,
          "observed": 1
        }
      ],
      "metrics": {
        "provider_calls": 1
      }
    }
  ]
}
```

Each scenario contains explicit invariant checks. A failed check makes its scenario fail, and a failed scenario makes the report fail.

There is deliberately no weighted score, composite ranking, or severity arithmetic in the current format. Boundary violations remain inspectable individually until real failure distributions justify stronger aggregation policy.

## Boundary attribution

Each check carries a short `boundary` label identifying where the invariant is observed. This supports the white-box evaluation direction:

```text
Event / provenance
  -> State
  -> Context selection
  -> provider output
  -> Validator decision
  -> persistence
  -> visible response
```

The current labels are diagnostic metadata, not new runtime authorities.

## Current native scenario

### `provider_failure_safety`

This deterministic scenario creates an isolated synthetic Character Package and runs one ordinary turn against a provider that intentionally fails on its first `generate` call.

It checks independently that:

- the provider failure is actually observed;
- the provider was called exactly once;
- the current User Event remains persisted;
- no Assistant Event is persisted;
- Canonical State remains unchanged.

The report also records bounded counts for provider calls, persisted Events, and persisted State records.

This scenario evaluates an existing RelayLM invariant; it does not alter runtime behavior to make the evaluation pass.

## Deferred evaluation work

Still owned by #1247:

- restart continuity as a native evaluation scenario;
- assistant self-certification prevention;
- correction/remove behavior;
- comparative preference preservation;
- degree-hint integrity;
- Working Context provenance/budget invariants;
- persistence malformed-data safety;
- crystallization quality and Markdown fidelity from #1260;
- relevance/retrieval evaluation from #1267;
- streaming/abort evaluation expansion beyond the existing deterministic contracts;
- future privacy/lifecycle evaluation from #1270;
- response/persona and actual local-model quality measurements;
- external benchmark adapters after current benchmark availability/version suitability is re-verified.

External benchmark names and versions are not frozen by the current native report format.

## Principle

> Evaluate the earliest RelayLM-owned boundary that became incorrect, rather than collapsing every failure into generic memory or response quality.
