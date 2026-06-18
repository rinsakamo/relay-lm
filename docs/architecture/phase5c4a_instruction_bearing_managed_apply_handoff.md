# Phase 5-C4a Instruction-Bearing Managed Apply Handoff

## Status

Phase 5-C4a is complete.

Implemented schemas:

- `client_history_exclusion_apply.v1`
- `client_instruction_source.v1`

Instruction-bearing actual apply now requires explicit request-local source provenance through the reserved `relaylm.instruction_evidence` envelope. Role, wording, and message position alone are not provenance.

Selected indices must be bounded, strictly increasing, non-duplicated, in range, refer to `system` or `developer` messages before the current user turn, and match request-local instruction identity candidates. Missing or invalid provenance blocks actual apply.

The completed path:

- excludes prior history and raw instruction objects,
- excludes unselected frontend summaries and memory notes,
- replaces exactly one typed legacy instruction block,
- performs escaping and rendered-size enforcement in the managed renderer,
- preserves the exact current user message and compatible top-level fields,
- removes the reserved RelayLM control envelope before managed forwarding,
- keeps cache lookup optional and read-only,
- blocks active tool transactions,
- requires the exact v1 applied candidate at backend forwarding,
- preserves v0 and pass-through behavior,
- keeps generic diagnostics content-free,
- remains default-off and dry-run-only by default.

Deterministic validation covers provenance selection and rejection, frontend summary exclusion, renderer escaping, JSON and stream backend integration, cache classes, multimodal preservation, fail-closed gates, audit/error surfaces, and existing v0 regressions through `onboarding-config-smoke.yml`.

Deferred work remains cache-hit RelaySCN projection, typed parse/cache write, complete Runtime Compile Gate v1, managed fallback, tool-chain reconstruction, RelaySOUL mutation, Stream Unpack, output-side RelayREF/SCN, and full RelayRUN routing.

Rollback must preserve the v0 no-instruction path and safe defaults.
