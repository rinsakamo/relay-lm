# MVP-10 Summary

MVP-10 adds operator-facing documentation for token policy shadow configuration and diagnostics.

## Completed scope

- operator-facing token policy profile examples
- global memory token policy shadow setting example
- character-level override examples
- `token_policy_decision` diagnostics / trace examples

## Design intent

MVP-10 clarifies how operators should read global and character-level token policy shadow settings. It also explains how to interpret shadow-only diagnostics before hard enforcement is introduced.

## Runtime safety

- runtime code is unchanged
- proxy forwarding behavior is unchanged
- token policy remains diagnostics / trace only
- hard fallback / rejection / truncation are not implemented

## Main validation

- `python -m compileall relaylm`
- docs-only diff confirmation

## Next phase

- gated runtime evaluation smoke
- operator-facing policy readiness checks
- hard enforcement evaluation in a separate MVP
