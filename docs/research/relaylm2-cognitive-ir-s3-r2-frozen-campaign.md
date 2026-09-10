# RelayLM 2.0 Cognitive IR — frozen replacement S3-R2 campaign

Scientific owner: #2211. Replacement preregistration owner: #2491. Repository binding owner: #2492. Physical procedure owner: #2363.

This document records the clean replacement campaign after historical #2478 ended `S3_INCOMPLETE / citable=false` and #2485/#2487 repaired the listener-release false negative. It does not reinterpret or tune from partial #2478 scientific outcomes.

Canonical preregistration:

```text
schema  relaylm2-cognitive-ir-s3-prereg-v2
label   relaylm2-cognitive-ir-s3-semantic-invariance-v2
SHA256  d3e19d59c2c6481178b942d462e4fca0a1ace02ed8deea1ae3c22f68c59f2166
```

The historical #2461/#2478 campaign remains represented by `relaylm2-cognitive-ir-s3-prereg-v1` and is not rewritten or replayed.

## Fresh families, unchanged science

Only the campaign identity and generated families change. The frozen replacement seeds are:

```text
shared    900332946 4686252 1045955583
null      2143918802 448647733 1569754577
mismatch  1206244949 1165112526 1584962688
shift     236371850 1062068690 225652850
```

They are derived from the replacement label by SHA-256 and are disjoint from calibration-v1, calibration-v2, selected S2, issue-number seed 2211, and all historical #2461 S3 seeds.

Everything else remains frozen exactly as #2461: modulus 10, vector width 4, identity permutation, nonzero offsets in 1..3, four source examples, four target steps, `shift_index=2`, zero target examples visible, no-wrap generation, all seven P0..P6 arms, one P2/P3/P4 formation each, deterministic P5/P6 from the exact P4 formation, and exact P4/P6 canonical semantic equality.

The meaning-preserving surface panel remains:

```text
S1_ROLE_LABEL_NEUTRAL
S2_KEY_RENAME_REORDER
S3_LOSSLESS_LIST_PROSE_SERIALIZATION
S4_PROMPT_PARAPHRASE_FORMAT
```

The meaning-changing intervention panel remains:

```text
M1_RULE_OFFSET_FLIP
M2_EXCEPTION_CHANGE
M3_SCOPE_CHANGE
M4_RELATION_REPLACE
```

Each semantic intervention is probed as `STALE_ORIGINAL` versus `UPDATED_INTERVENED`. The option-value query remains the smallest source-example index whose input vector has maximum coordinate sum, with smallest-index tie break.

## Exact campaign ledger

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

Shard order is fixed `shared -> null -> mismatch -> shift`. The campaign stops on the first non-completed shard. No shard retry, replay, reseed, alternate family, model swap, context change, provider fallback, LM Studio fallback, or skip-forward is permitted.

The primary semantic-invariance discriminator is unchanged:

```text
surface_perturbation_effect <= 0.15
semantic_intervention_effect >= 0.20
semantic_intervention_effect - surface_perturbation_effect >= 0.15
```

All #2211 Grand Null and kill/weaken criteria remain live. Architecture consequence remains `NONE` regardless of result.

## Executable binding

The historical `relaylm.v2_cognitive_ir_s3` module remains the immutable #2461/#2478 campaign under ordinary import. `relaylm.v2_cognitive_ir_s3_r2` owns the replacement identity, seed derivation, collision audit, and scientific-shape guard. It activates the replacement only inside the dedicated fresh child process.

The current WSL command remains:

```text
python3 -m tools.v2_cognitive_ir_s3_llama_cpp_wsl
```

The WSL wrapper now launches:

```text
tools.v2_cognitive_ir_s3_r2_llama_cpp_transaction
```

That child activates #2491 before the shared transaction module binds its preregistration identity, then delegates through the listener-safe envelope from #2487. The shared S3 implementation therefore retains the exact panels, accounting, runtime/material checks, and no-retry semantics while receiving only the fresh preregistration identity and families.

## Physical/runtime boundary

A later physical owner must freshly reattest the exact clean v2 implementation and local material before the first semantic call. Intended runtime class remains loopback llama.cpp at `http://127.0.0.1:1234/v1`, context 8192, one slot, context shift disabled, `reasoning_effort=none`, temperature 0, request seed null, max output 512, timeout at least 1800 seconds, and launch class `-ngl 999 -c 8192 -np 1 --no-context-shift -lv 4 --log-prefix --log-timestamps`.

Every planned shard owns one server lifetime and unique log. The listener-safe lifecycle check observes actual loopback listener absence rather than immediate fresh-bind availability. Runtime/material drift, process loss, exact-input mismatch, lineage/equality failure, cleanup failure, undeclared call, or any incomplete shard fails closed and prevents later shards.

A result is citable within this same-model scope only when all four fresh shards complete under one frozen implementation/runtime/material contract with the exact 498/996 ledger and all mechanical checks. Otherwise it is `S3_INCOMPLETE / citable=false` and any later attempt requires another wholly new preregistration.

No model/provider/GPU call is authorized by this repository-binding document.