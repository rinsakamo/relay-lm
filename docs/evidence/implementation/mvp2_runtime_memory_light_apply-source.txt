# MVP-2 Runtime Memory-light Apply

This step connects the memory-light profile compilation helper to `/v1/chat/completions`.

## Behavior

- `pass_through` keeps the original request payload unchanged.
- `memory_light` can forward compiled profile messages when the profile compile plan is ready.
- `stream=true` and `stream=false` both use the same forwarded payload selection.
- profile compile diagnostics headers remain available.

## Safety boundary

The default `config.example.yaml` still uses `pass_through`, so the default API smoke keeps validating the unchanged pass-through path.

The memory-light apply contract is validated by the server-free helper smoke.

## Run

Server-free helper smoke:

```bash
python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py
```

Pass-through API smoke:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

In another terminal:

```bash
python -m compileall relaylm scripts/relaylm_api_smoke.py
python scripts/relaylm_api_smoke.py --base-url http://127.0.0.1:8090 --model relaylm-default --expected-mode pass_through --expected-profile-compile-dry-run true
```

Expected output includes:

```text
ok pass-through payload unchanged
ok memory-light payload compiled
ok profile compile dry-run header
```

A `502` chat status is acceptable when the configured backend is not running.
