# MVP-12 Summary

MVP-12 adds token budget truncation capabilities from helper-level evaluation through gated runtime apply and proxy-level integration smoke.

## Completed scope

- token budget truncation helper
- token budget truncation dry-run diagnostics / trace
- gated runtime truncation apply
- proxy integration smoke with fake OpenAI-compatible backend

## Design intent

MVP-12 enables safe message-shortening when token budget is exceeded before forwarding requests to the backend. The default remains disabled to preserve prior behavior. Runtime apply is only enabled when `token_budget_truncation_enabled=true` and safe conditions are met. System messages and the latest user message are preserved.

## Runtime safety

- default `false` keeps forwarding behavior unchanged
- blocked / unsafe / `over_budget_after=true` does not apply truncation
- malformed-only differences do not trigger apply
- hard rejection / fallback backend switching is not implemented
- message-level deletion only; partial message text truncation is not implemented

## Main validation

- `python scripts/relaylm_token_budget_truncation_smoke.py`
- `python scripts/relaylm_token_budget_truncation_dry_run_smoke.py`
- `python scripts/relaylm_token_budget_truncation_apply_smoke.py`
- `python scripts/relaylm_token_budget_truncation_proxy_smoke.py`
- `python scripts/relaylm_token_memory_dry_run_smoke.py`
- `python scripts/relaylm_token_policy_runtime_gate_smoke.py`
- `python -m compileall relaylm`

## Next phase

- real local-backend manual smoke (LM Studio / llama.cpp / Ollama-compatible)
- operator-facing truncation config documentation
- optional response/diagnostics header review
- future hard rejection / fallback remains a separate MVP
