# MVP-13 Summary

## Completed scope

- `SCENE_STATE.md` / `scene_state` naming alignment across RelayLM profile compile paths
- deprecated `room_state` alias compatibility preserved for existing configs
- content-free `context_block_summary` diagnostics for compiled context blocks
- content-free `persona_source_budget_diagnostics` for persona source budget pressure
- content-free `relaysoul_runtime_feedback_summary` for RelaySOUL-facing runtime feedback aggregation

## Design intent

MVP-13 organizes RelaySOUL-facing RelayLM runtime diagnostics into machine-readable artifacts that support persona patch-candidate, calibration, and revision decisions.

- RelaySOUL can consume RelayLM runtime feedback signals as structured diagnostics when evaluating persona changes.
- Persona source budget pressure is observable directly from RelayLM compile outputs before patch application.
- `scene_state` remains a dynamic suffix block and is intentionally excluded from stable prefix hash targets.
- RelaySOUL decisions should use both user preference examples and RelayLM runtime diagnostics.

## Runtime safety

- diagnostics-only changes
- pass-through behavior unchanged
- backend forwarding payload unchanged
- no hard rejection
- no fallback backend switching
- no runtime memory selection behavior change
- no request scope application to `ResolvedRoute` / memory selection
- no persona/memory content in diagnostics summaries

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_profile_compile_smoke.py`
- `python scripts/relaylm_context_block_summary_smoke.py`
- `python scripts/relaylm_persona_source_budget_smoke.py`
- `python scripts/relaylm_relaysoul_runtime_feedback_smoke.py`
- `python scripts/relaylm_stable_prefix_hash_smoke.py`
- `python scripts/relaylm_memory_light_apply_smoke.py`
- `python scripts/relaylm_memory_adapter_dry_run_smoke.py`
- `python scripts/relaylm_memory_adapter_shadow_scope_smoke.py`
- `python scripts/relaylm_memory_adapter_shadow_delta_smoke.py`
- `python scripts/relaylm_scope_resolution_smoke.py`
- `python scripts/relaylm_request_scope_identity_smoke.py`
- `python scripts/relaylm_token_budget_truncation_proxy_smoke.py`
- `python scripts/relaylm_token_memory_dry_run_smoke.py`

## Next phase

- RelaySOUL patch-candidate dry-run contract
- persona revision metadata / rollback summary contract
- optional docs for RelaySOUL runtime feedback fields
- future hard rejection / fallback remains a separate MVP
