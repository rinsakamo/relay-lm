# MVP-25 Summary

## Completed scope

- Updated `docs/smoke/openwebui_lmstudio_manual_smoke.md` Step 6 into a practical connection decision tree.
- Clarified OpenWebUI host-run Base URL:
  - `http://127.0.0.1:8090/v1`
- Clarified OpenWebUI Docker-run fallback order:
  - try `host.docker.internal`
  - if it fails, use `<WSL_IP>`
- Added WSL IP check command:
  - `hostname -I`
- Added container-side route check command:
  - `docker exec open-webui curl http://<WSL_IP>:8090/v1/models`
- Clarified that RelayLM may need `listen.host: 0.0.0.0` so containers can reach it.
- Added WSL -> Windows LM Studio note:
  - WSL `127.0.0.1` points to WSL itself
  - `WIN_HOST=$(ip route show default | awk '{print $3}')`
  - `curl http://${WIN_HOST}:1234/v1/models`
- Strengthened runbook -> troubleshooting guide path for deeper network/firewall/API-mode cut points.

## Design intent

- Make the manual smoke runbook the first decision entry for "which Base URL should I set now?"
- Keep the troubleshooting doc as the deeper diagnosis path after first-line connection decisions.
- Avoid confusion across host / Docker / WSL / Windows host localhost scopes.

## Runtime safety

- Docs-only summary update.
- No runtime code or smoke script changes.
- No backend forwarding payload contract changes.
- Responsibility boundaries remain explicit across fake-backend smoke, real manual smoke, troubleshooting docs, and local setup guide docs.
- RelaySOUL actual persistence/apply/rollback/persona mutation remains a separate thread and phase.

## Main validation

- `python -m compileall relaylm`
- `git diff --name-only origin/main...HEAD`
- PR #173 is docs-only.
- No Codex review comments to resolve in this MVP-25 summary pass.

## Next phase

- Add further real measurements using the response differentiation prompt set.
- Refine model preset/avatar UX guidance.
- Consider OpenWebUI route examples / screenshots in a separate docs pass.
- Optional (separate MVP): decide whether `/v1/responses` compatibility shim is needed.
- Optional: consolidate local setup guide and troubleshooting docs with a shared decision-index page.
