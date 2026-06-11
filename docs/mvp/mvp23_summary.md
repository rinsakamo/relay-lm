# MVP-23 Summary

## Completed scope

- Added real manual smoke result documentation:
  - `docs/openwebui_lmstudio_manual_smoke_result_2026_05_26.md`
- Confirmed real-environment OpenWebUI -> RelayLM -> LM Studio path as pass.
- Confirmed WSL -> Windows LM Studio connectivity as pass after required local network/firewall adjustments.
- Confirmed RelayLM `/v1/models` as pass.
- Confirmed RelayLM non-stream `POST /v1/chat/completions` as pass.
- Confirmed RelayLM stream `POST /v1/chat/completions` as pass.
- Confirmed OpenWebUI chat to route IDs (including `relaylm-companion`) as pass.
- Confirmed route-specific response differentiation as pass for:
  - `relaylm-companion`
  - `relaylm-work-assistant`
  - `relaylm-code-reviewer`
- Recorded troubleshooting observations in real-run docs:
  - Windows Firewall / local network access adjustments
  - WSL IP usage and environment-dependent addressing
  - Tools/OpenAPI misconfiguration for chat use
  - `/v1/responses` path 404 and Chat Completions correction

## Design intent

- Runtime MVP value check is: route selection from real UI should show profile-driven behavior differences while using the same backend model.
- OpenWebUI owns card-like UX, model selector, and avatar/preset interaction.
- RelayLM owns route/profile/memory/context compile behavior.
- LM Studio owns local OpenAI-compatible inference backend execution.

## Runtime safety

- Docs-only summary update.
- No runtime code or smoke script changes.
- Fake-backend smoke and real manual smoke remain explicitly separated.
- Backend forwarding payload contract remains unchanged.
- RelaySOUL actual persistence/apply/rollback/persona mutation remains separate thread and phase.

## Main validation

- `python -m compileall relaylm`
- `git diff --name-only origin/main...HEAD`
- Real manual smoke result status:
  - `/v1/models`: pass
  - non-stream: pass
  - stream: pass
  - OpenWebUI chat: pass
  - route differentiation: pass

## Next phase

- Add OpenWebUI troubleshooting refinement docs if needed.
- Add more real measurements using the response differentiation prompt set.
- Refine model preset/avatar UX guidance.
- Optional (separate MVP, not implemented here): `/v1/responses` compatibility shim exploration.
- Optional: consolidate local setup guides.
