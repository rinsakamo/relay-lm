# MVP-20 Summary

## Completed scope

- Established `OpenWebUI -> RelayLM -> LM Studio` as the standard MVP UI/backend path.
- Kept Open-LLM-VTuber as an optional frontend/example integration path.
- Standardized abstract route IDs for OpenWebUI model preset/model ID mapping:
  - `relaylm-companion`
  - `relaylm-work-assistant`
  - `relaylm-code-reviewer`
- Added abstract example profiles and memory seeds for the three route personas.
- Added copy-ready config for the standard MVP route/profile setup:
  - `examples/config/openwebui_lmstudio.yaml`
- Added config-only local smoke:
  - `scripts/relaylm_openwebui_lmstudio_config_smoke.py`
- Added fake-backend proxy-path local smoke:
  - `scripts/relaylm_openwebui_lmstudio_proxy_smoke.py`

## Design intent

- Treat OpenWebUI model preset/avatar as card-like UI for route selection and UX.
- Keep RelayLM responsible for route resolution, persona/profile binding, memory context assembly, and context compile behavior.
- Keep LM Studio responsible for local OpenAI-compatible inference execution.
- Allow the same backend model to present differentiated behavior by route/profile/memory configuration.

## Runtime safety

- MVP-20 completion is centered on docs/examples/smoke hardening; no runtime behavior expansion is required.
- Real LM Studio verification remains manual smoke scope.
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
- Route-specific response differentiation check under shared backend model.
- Optional manual smoke result template and troubleshooting refinement.
- Later: RelaySOUL actual persistence/apply integration behind explicit safety gates.
