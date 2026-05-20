# MVP-1 Summary

MVP-1 locks RelayLM's config, routing, and diagnostics contracts after the MVP-0 OpenAI-compatible pass-through proxy.

The purpose is to make RelayLM observable and testable before adding persona compilation, memory, or RAG.

## Completed scope

MVP-1 currently covers:

- config loading smoke
- model route listing
- model route resolution
- unknown model error behavior
- missing backend config error behavior
- runtime diagnostics header contract
- runtime diagnostics log payload contract
- API-level diagnostics headers on `/v1/chat/completions`

## Main validation commands

Run the server-free config/routing smoke:

```bash
python -m compileall relaylm scripts/relaylm_config_routing_smoke.py
python scripts/relaylm_config_routing_smoke.py --config config.example.yaml --model relaylm-default
```

Expected output:

```text
ok list_model_ids
ok resolve_route
ok missing model error
ok missing backend error
```

Run the server-free diagnostics smoke:

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

Run the API diagnostics smoke against a running RelayLM server:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

In another terminal:

```bash
python -m compileall relaylm scripts/relaylm_api_smoke.py
python scripts/relaylm_api_smoke.py --base-url http://127.0.0.1:8090 --model relaylm-default --expected-mode pass_through
```

Expected output includes:

```text
ok healthz
ok models
ok chat diagnostics headers
```

A `502` chat status is acceptable when the configured backend is not running. The important MVP-1 property is that RelayLM returns a stable response with diagnostics headers.

## Contract fixed by MVP-1

### Route contract

`relaylm-default` in `config.example.yaml` should resolve to:

- backend name: `local_backend`
- backend model: `local-model`
- mode: `pass_through`
- character ID: `default`
- cache namespace: `character/default`
- memory namespace: `character/default`

Unknown incoming model names should raise `RouteNotFoundError` and become client-facing invalid request errors.

Routes that exist but point to missing backend config should raise `RouteConfigurationError` and become server-side config errors.

### Diagnostics contract

RelayLM chat responses should expose:

- `x-relaylm-request-id`
- `x-relaylm-mode`

When a fallback reason exists, RelayLM may also expose:

- `x-relaylm-fallback-reason`

The diagnostics log payload should keep route, backend, character, mode, stream, compiler, and fallback fields stable so later phases can add more information without breaking current checks.

## Still out of scope

MVP-1 does not implement:

- SOUL loading
- OUTPUT_POLICY loading
- context compilation
- memory or RAG
- embeddings
- vector stores
- automatic memory writes
- backend KV-cache mutation

## Next phase: MVP-2

MVP-2 should introduce a persona-stable context compiler without memory/RAG.

Recommended first MVP-2 scope:

- character profile config placeholders
- `SOUL.md` loading
- `OUTPUT_POLICY.md` loading
- `common_runtime_policy` loading
- `room_anchor` loading
- incoming system prompt fallback
- compiled system message smoke
- pass-through mode remains unchanged

MVP-2 should preserve the MVP-1 route and diagnostics contracts.
