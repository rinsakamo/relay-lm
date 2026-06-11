# MVP-26 Summary

## Completed scope

- Added request-local CompileDecision diagnostics wiring for Runtime CTX Apply milestones from PR #178 and PR #179.
- Added `RequestDiagnostics.compile_decision_dry_run` and `build_compile_decision_dry_run(...)` as the baseline diagnostics schema helper.
- Propagated `compile_decision_dry_run` into trace metadata.
- Wired CompileDecision diagnostics generation into `/v1/chat/completions` request path.
- Ensured `compiled_message_count` uses plan-derived count (`compiled_request.plan.compiled_message_count`) rather than forwarded input message count.
- Aligned diagnostics apply-state with actual request decision (`compiled_request.decision.should_apply`):
  - apply path: `COMPILE_APPLY`, `apply_compiled_messages=true`, `diagnostics_only=false`
  - non-apply path: `COMPILE_DRY_RUN`, `apply_compiled_messages=false`, `diagnostics_only=true`
- Verified in fake-backend proxy smoke that compile decision metadata is not injected into backend payload.
- Verified CompileDecision diagnostics object does not include prompt text, full messages, or message content fields.

## Design intent

- Runtime CTX Apply should first stabilize diagnostics/trace/artifact boundaries before expanding apply policy surface.
- CompileDecision is the request-local boundary for observing what was applied (or not applied).
- Diagnostics must remain consistent with actual forwarding/apply state.
- RelaySOUL approval/persistence artifacts remain a later-phase integration.

## Runtime safety

- Docs-only summary update.
- No runtime behavior change.
- No backend forwarding payload behavior change.
- No actual CTX apply behavior change.
- No compiled-messages apply behavior change.
- `/v1/responses` compatibility shim remains unimplemented.
- CompileDecision diagnostics object excludes full prompt text/full messages/content.
- Trace writing remains best-effort.
- No hard rejection behavior introduced.

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_compile_decision_dry_run_smoke.py`
- `python scripts/relaylm_compile_decision_request_path_smoke.py`
- `python scripts/relaylm_profile_compile_dry_run_smoke.py`
- `python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py`
- `git diff --name-only origin/main...HEAD`
- PR #179 review follow-up items completed:
  - plan-derived `compiled_message_count`
  - diagnostics apply-state alignment with actual apply decision

## Next phase

- Add CompileDecision ID helper/naming convention.
- Add `token_budget_status` diagnostics wiring from compile pipeline outputs.
- Add `omitted_block_ids` diagnostics wiring from compile pipeline outputs.
- Add trace metadata size guards/allowlist policy.
- Add CTX Apply Gate dry-run path with explicit operator-facing decision surface.
- Integrate RelaySOUL approval artifact linkage in a later phase.
