# MVP-1 Runtime Diagnostics Smoke

This smoke check validates RelayLM's request diagnostics contract without starting the server.

It checks that:

- `RequestDiagnostics.to_headers()` emits `x-relaylm-request-id`
- `RequestDiagnostics.to_headers()` emits `x-relaylm-mode` when mode is known
- fallback reason headers are only emitted when present
- `RequestDiagnostics.to_log_dict()` keeps route, backend, character, mode, stream, and compiler fields stable

## Run

```bash
python -m compileall relaylm scripts/relaylm_runtime_diagnostics_smoke.py
python scripts/relaylm_runtime_diagnostics_smoke.py
```

Expected output:

```text
ok diagnostics headers
ok diagnostics log payload
ok fallback header
```

## Purpose

MVP-1 should make routing and runtime behavior observable before RelayLM adds memory or context compilation.

This smoke check fixes the diagnostics contract so later phases can add fields without breaking the current MVP-0 proxy behavior.
