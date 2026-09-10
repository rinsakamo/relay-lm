# RelayLM 2.0 Cognitive IR — frozen S3-R3 campaign

Scientific owner: #2211. Protocol-repair owner: #2517. Repository binding owner: #2518. Physical procedure owner: #2363.

S3-R3 is the clean preregistered successor to historical S3-R2. #2498 remains immutable `S3_INCOMPLETE / citable=false`; #2515 established `MAX_OUTPUT_CEILING_CONFIRMED` for `shift:2:225652850:form-p2` at exactly 512 generated tokens with 7516 context tokens remaining. S3-R3 uses that mechanical fact only. It does not tune from partial scientific outcomes.

Canonical preregistration:

```text
schema  relaylm2-cognitive-ir-s3-prereg-v3
label   relaylm2-cognitive-ir-s3-semantic-invariance-v3
SHA256  a0b137f023c260eb9da479f5722708f6cf6f955198e4234203753831e9278ed1
```

Fresh deterministic seeds:

```text
shared    410645929 1746379332 553311797
null      37598355 516261911 867582011
mismatch  970643640 1824424633 1573930240
shift     1371833688 1071883363 1464302864
```

They are derived from the R3 label by SHA-256 and must remain disjoint from S3-v1, S3-R2, selected S2, issue-number sentinels, and both calibration seed sets.

## Only protocol repair

The only non-identity protocol change from S3-R2 is a uniform output ceiling:

```text
max_output_tokens: 512 -> 1024
```

The 1024 allowance applies to every semantic call, not only P2 or shift. Actual output tokens remain charged. `finish_reason != stop` remains a terminal fail-closed condition and never authorizes retry.

Everything scientific remains frozen: four ordered regimes `shared -> null -> mismatch -> shift`; three families per regime; P0..P6; one P2/P3/P4 formation with deterministic P5/P6 from the exact P4 formation; exact P4/P6 semantic equality; the four meaning-preserving surface perturbations; the four stale-vs-updated semantic interventions; option-value/query-family-shift pressure; and discriminator thresholds `0.15 / 0.20 / 0.15`.

Exact ledger:

```text
shared    123 semantic calls
null      123 semantic calls
mismatch  123 semantic calls
shift     129 semantic calls
--------------------------------
total     498 semantic Chat Completions
          996 exact /input_tokens requests
          4 managed server lifetimes/logs
```

No retry, replay, reseed, alternate family, prompt repair, model/provider swap, context change, fallback, LM Studio contact, or skip-forward is permitted. Architecture consequence remains `NONE` regardless of result.

## Runtime binding

The operator command remains:

```text
python3 -m tools.v2_cognitive_ir_s3_llama_cpp_wsl
```

The WSL launcher routes to `tools.v2_cognitive_ir_s3_r3_llama_cpp_transaction`. The child activates the fresh R3 identity before the shared transaction binds campaign constants, substitutes the dedicated R3 transport, and sets the shared transaction's runtime identity/output budget to 1024. Historical S3/S3-R2 constants and ordinary imports remain unchanged.

Intended physical runtime remains loopback llama.cpp at `http://127.0.0.1:1234/v1`, context 8192, one slot, context shift disabled, `reasoning_effort=none`, temperature 0, request seed null, timeout at least 1800 seconds, and launch class `-ngl 999 -c 8192 -np 1 --no-context-shift -lv 4 --log-prefix --log-timestamps`.

## Non-stop observability

The dedicated R3 transport records instrumentation-only metadata before rejecting a non-`stop` completion when the provider envelope exposes it: question id, finish reason, prompt/completion/reasoning token counts, reasoning-field status, and generated-content character/byte counts plus SHA-256. Raw generated content is not persisted by this diagnostic path. The response is still not counted as a provider completion.

No model/provider/GPU execution is authorized by this repository-binding document. A physical owner may be created only after exact-head and post-merge CI are green.
