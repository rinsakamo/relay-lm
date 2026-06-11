# MVP-1 Config and Routing Smoke

This smoke check validates the first MVP-1 seam without starting the RelayLM server.

It checks that:

- `config.example.yaml` loads successfully
- configured model IDs are listed
- `relaylm-default` resolves to the expected backend route
- unknown model names raise `RouteNotFoundError`
- routes that reference a missing backend raise `RouteConfigurationError`

## Run

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

## Purpose

MVP-0 proved that RelayLM can start and expose the OpenAI-compatible API surface.

This smoke check starts MVP-1 by fixing the route/config contract before adding heavier runtime diagnostics or context compilation.
