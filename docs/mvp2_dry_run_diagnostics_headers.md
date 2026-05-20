# MVP-2 Dry-run Diagnostics Headers

This step connects profile compile dry-run planning to `/v1/chat/completions` diagnostics headers.

The request payload forwarded to the backend is not changed. Pass-through runtime behavior remains unchanged.

## Added headers

RelayLM may now emit:

```text
x-relaylm-profile-compile-dry-run: true|false
x-relaylm-profile-compile-fallback-reason: <reason>
```

The header indicates whether RelayLM could build a profile compile plan for the current route and incoming messages.

## Behavior

- `compiler_used` remains false.
- request payload mutation is still disabled.
- profile compile dry-run runs before forwarding.
- backend errors still return stable RelayLM diagnostics headers.

## Run

Start RelayLM:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

Run the API smoke in another terminal:

```bash
python -m compileall relaylm scripts/relaylm_api_smoke.py
python scripts/relaylm_api_smoke.py --base-url http://127.0.0.1:8090 --model relaylm-default --expected-mode pass_through --expected-profile-compile-dry-run true
```

Expected output includes:

```text
ok healthz
ok models
ok chat diagnostics headers
ok profile compile dry-run header
```

A `502` chat status is acceptable when the configured backend is not running.
