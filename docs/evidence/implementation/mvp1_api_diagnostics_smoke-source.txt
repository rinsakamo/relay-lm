# MVP-1 API Diagnostics Smoke

This smoke extends the MVP-0 API check to verify runtime diagnostics headers on `/v1/chat/completions`.

It checks that a running RelayLM server returns:

- `x-relaylm-request-id`
- `x-relaylm-mode`

## Run

Start RelayLM in one terminal:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

Run the smoke in another terminal:

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

A `502` chat status is acceptable when the configured backend is not running. The important check is that RelayLM returns a stable response with diagnostics headers.
