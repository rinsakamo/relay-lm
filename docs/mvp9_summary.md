# MVP-9 Summary

MVP-9 extends token policy shadow diagnostics with character-level isolation for mixed workloads.

## Completed scope

- character-level token policy shadow override
- effective token policy setting resolution
- `shadow_source` diagnostics
- mixed-character token policy smoke

## Design intent

MVP-9 separates token policy shadow behavior safely per character/profile context. It keeps global defaults and character-level overrides compatible while preventing setting leakage across mixed-character request sequences.

## Runtime safety

- proxy forwarding behavior is unchanged
- hard enforcement / fallback / rejection / truncation remain unimplemented
- `enforcement_enabled` remains `false`
- token policy output remains diagnostics / trace only

## Main validation

Primary MVP-9 validation is smoke and compile checks:

- `python scripts/relaylm_token_memory_dry_run_smoke.py`
- `python scripts/relaylm_token_trace_payload_smoke.py`
- `python scripts/relaylm_token_policy_signal_smoke.py`
- `python scripts/relaylm_mixed_character_token_policy_smoke.py`
- `python -m compileall relaylm scripts/relaylm_mixed_character_token_policy_smoke.py`

## Next phase

- operator-facing profile defaults
- broader mixed workload validation
- future gated runtime evaluation
- hard enforcement evaluation in a separate MVP
