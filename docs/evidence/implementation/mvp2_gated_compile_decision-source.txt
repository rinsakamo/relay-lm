# MVP-2 Gated Compile Decision

This step adds the first explicit gate for applying compiled profile messages.

It does not rewrite `/v1/chat/completions` payloads yet.

## Rule

```text
pass_through -> diagnostics only
memory_light -> compile apply eligible when dry-run plan is ready
memory_full -> not enabled yet
```

This keeps MVP-0 pass-through safe while preparing a narrow gate for the first persona-stable context application path.

## Added pieces

- `CompileApplyDecision`
- `decide_compile_apply()`
- server-free compile gate smoke

## Run

```bash
python -m compileall relaylm scripts/relaylm_compile_gate_smoke.py
python scripts/relaylm_compile_gate_smoke.py
```

Expected output:

```text
ok pass-through diagnostics-only decision
ok memory-light compile apply decision
ok fallback compile decision
ok compile decision log payload
```

## Out of scope

This step does not add:

- actual payload rewriting
- FastAPI integration for applying compiled messages
- memory or RAG
