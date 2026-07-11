# MVP-2 Profile Compile Dry-run

This step adds dry-run planning for profile compilation without mutating `/v1/chat/completions` payloads.

The purpose is to make RelayLM able to report whether persona profile compilation is possible for a route before enabling real request rewriting.

## Added pieces

- `ProfileCompilePlan`
- `build_profile_compile_plan()`
- server-free dry-run smoke

## Plan fields

The dry-run plan records:

- whether compilation is enabled
- route model
- character ID
- compiled block count
- compiled message count
- incoming message count
- incoming system message count
- fallback reason, when compilation cannot be planned

## Run

```bash
python -m compileall relaylm scripts/relaylm_profile_compile_dry_run_smoke.py
python scripts/relaylm_profile_compile_dry_run_smoke.py
```

Expected output:

```text
ok profile compile dry-run plan
ok profile compile plan log payload
ok profile compile fallback plan
```

## Runtime behavior

This step does not connect compilation to FastAPI and does not change pass-through behavior.

Future PRs can use this plan to add diagnostics-only runtime visibility before enabling payload rewriting in a gated mode.
