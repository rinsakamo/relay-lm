# MVP-21 Summary

## Completed scope

- Documented `OpenWebUI -> RelayLM -> LM Studio` as the standard MVP UI/backend path.
- Kept Open-LLM-VTuber positioned as an optional frontend / example integration.
- Standardized abstract route IDs for OpenWebUI model preset/model ID mapping:
  - `relaylm-companion`
  - `relaylm-work-assistant`
  - `relaylm-code-reviewer`
- Added abstract example profiles and memory seeds for route-specific persona/memory shaping.
- Added copy-ready config for immediate local setup:
  - `examples/config/openwebui_lmstudio.yaml`
- Added config-only local smoke coverage:
  - `scripts/relaylm_openwebui_lmstudio_config_smoke.py`
- Added fake-backend proxy-path local smoke coverage:
  - `scripts/relaylm_openwebui_lmstudio_proxy_smoke.py`

## Design intent

- Use OpenWebUI model preset/avatar as a card-like UI for route selection.
- Keep RelayLM responsible for route resolution and persona/profile/memory/context compile binding.
- Keep LM Studio responsible for local OpenAI-compatible inference execution.
- Allow differentiated behavior from the same backend model through route/profile/memory configuration.

## Runtime safety

- Runtime behavior changes are not required; scope is docs/examples/smoke consolidation.
- Real LM Studio connection remains manual smoke scope.
- Fake-backend proxy smoke does not connect to a real backend.
- RelaySOUL actual persistence/apply/rollback/persona mutation remains unimplemented.
- Backend forwarding payload contract remains unchanged.

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_openwebui_lmstudio_config_smoke.py`
- `python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py`
- `python scripts/relaylm_config_routing_smoke.py`
- `python scripts/relaylm_profile_compile_dry_run_smoke.py`

## Next phase

- Real LM Studio manual smoke in target environments.
- OpenWebUI model preset/avatar setup verification checklist.
- Route-specific response differentiation check with shared backend model.
- Optional manual smoke result template and troubleshooting refinement.
- Later: RelaySOUL actual persistence/apply integration behind explicit safety gates.
