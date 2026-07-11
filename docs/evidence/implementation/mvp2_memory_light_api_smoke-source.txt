# MVP-2 Memory-light API Smoke

This step extends the API smoke so RelayLM can verify whether the runtime compiler was used.

## Added header

```text
x-relaylm-compiler-used: true|false
```

## Behavior

- default `config.example.yaml` remains `pass_through`
- pass-through API smoke expects `x-relaylm-compiler-used: false`
- memory-light API smoke can use a temporary config override and expect `x-relaylm-compiler-used: true`

## Pass-through run

Start RelayLM:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

Run:

```bash
python scripts/relaylm_api_smoke.py \
  --base-url http://127.0.0.1:8090 \
  --model relaylm-default \
  --expected-mode pass_through \
  --expected-profile-compile-dry-run true \
  --expected-compiler-used false
```

## Memory-light run

Create a temporary memory-light config:

```bash
cp -f config.example.yaml config.memory_light.yaml
python - <<'PY'
from pathlib import Path
path = Path('config.memory_light.yaml')
text = path.read_text()
text = text.replace('mode: pass_through', 'mode: memory_light', 1)
text = text.replace('    mode: pass_through', '    mode: memory_light', 1)
path.write_text(text)
PY
python -m relaylm.app --config config.memory_light.yaml
```

Run:

```bash
python scripts/relaylm_api_smoke.py \
  --base-url http://127.0.0.1:8090 \
  --model relaylm-default \
  --expected-mode memory_light \
  --expected-profile-compile-dry-run true \
  --expected-compiler-used true
```

A `502` chat status is acceptable when the configured backend is not running.
