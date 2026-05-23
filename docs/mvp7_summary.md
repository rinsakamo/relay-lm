# MVP-7 Summary

MVP-7 adds token-budget-aware memory dry-run support to RelayLM.

## Completed scope

- token estimate helpers
- token memory dry-run helper
- token budget config validation
- token dry-run diagnostics payload
- token dry-run trace metadata capture

## Design intent

MVP-7 intentionally keeps memory-light request behavior unchanged and introduces token-budget handling as a dry-run signal first. This gives operators visibility into estimated selection and assembly outcomes before any future hard enforcement path is enabled.

## Runtime safety

The runtime request path remains compatible with existing profiles and backends. Token-budget logic is isolated to dry-run computation and emitted diagnostics/trace metadata, so failures in this area do not alter normal proxy forwarding behavior.

## Main validation

Primary validation for MVP-7 is smoke-based:

- token-memory dry-run smoke verifies configured assembly behavior and config rejection paths
- token-trace payload smoke verifies `token_memory_dry_run` is preserved in trace metadata and diagnostics logging payloads

## Next phase

Next, RelayLM can build from the diagnostics baseline by adding policy-driven runtime decisions on token-budget signals, plus broader test coverage around profile-level defaults and mixed-character workloads.
