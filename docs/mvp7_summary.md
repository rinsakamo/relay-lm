# MVP-7 Summary

MVP-7 adds token-budget-aware memory dry-run support to RelayLM.

Completed scope:

- token estimate helpers
- token memory dry-run helper
- token budget config validation
- token dry-run diagnostics payload
- token dry-run trace metadata capture

MVP-7 keeps the existing memory-light runtime path unchanged and records token-budget behavior as diagnostics first.
