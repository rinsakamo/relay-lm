# E4-SR2 strict semantic reconstruction — physical adapter

Authority owner: #2774. Scientific parent: #2211. Prospective preregistration: #2768. Deterministic repository binding: #2769. Strict-output interface precedent: #2748. Historical P4/P6 physical precedent: #2723. Common physical generation authority: #2750.

This surface makes the prospective E4-SR2 P4-vs-P6 accessibility experiment executable through the shared llama.cpp runner. It owns only the zero-GPU adapter. It does **not** authorize THIS RUN, provider/model/GPU/server execution, architecture mutation, or a new Memory/Structure primitive.

## Frozen scientific envelope

The adapter consumes #2768/#2769 unchanged:

```text
families                       24
arms                           P4_MEMORY_PLUS_STRUCTURE / P6_GENERIC_EQUAL_INFORMATION
canonical semantic equality    24/24
semantic completions           48
scientific /input_tokens       96
mechanical pre-material counts exactly 2 non-scientific /input_tokens requests
interface                      native response_format json_schema strict=true
context                        8192
max output tokens              256
temperature                    0
reasoning                      none/off
request seed                   omitted/null
semantic slots                 1
stream                         false
primary endpoint               full_payload_exact
strict_parse_valid admission   48/48
paired inference               two-sided exact sign/McNemar, alpha=0.05
retry/replay/reseed/fallback/hidden repair/judge = 0
architecture_consequence       NONE
```

No P0/P1/P2/P3/P5 arm, formation-quality call, target-task probe, G2/#2188 strengthening, or architecture claim is introduced here.

## Material boundary

Exact #2768 family objects do not exist merely because this module is imported, tested, listed as a common target, inspected with `--help`, queued, or mechanically preflighted.

The canonical order is:

```text
fresh clean exact protected-v2 checkout
 -> common target dispatch and persistent-Python preflight
 -> queue/resource lease and external-runtime quiescence
 -> llama.cpp executable/model/runtime preflight
 -> one owned llama.cpp launch
 -> live health/models/props/slots binding
 -> synthetic strict-response-format /input_tokens preflight (2 non-scientific)
 -> immutable validated FrozenConsumerIdentity
 -> ONLY THEN materialize one exact preregistered family at a time
 -> derive P4/P6 through the existing #2709 mechanism-control path
 -> require equal canonical semantic digest before admitting the pair
 -> 48 sequential strict-json-schema semantic calls
 -> 96 scientific /input_tokens requests
 -> #2769 strict scoring, paired table, exact inference, admission/classification
 -> final live binding check
 -> persist manifest/result/receipt/raw cell evidence
```

The official family generator requires both a validated `FrozenConsumerIdentity` and the exact #2768 `(index, seed)` relation. The synthetic helper rejects every one of the 24 preregistered E4-SR2 seeds. It uses only separate synthetic seeds for CI.

`prepare_mechanism_control()` remains the semantic-equality authority. It derives typed P4 and neutralized P6 from the same canonical payload, requires identical semantic digests and decoded canonical truth, and requires the literal serialized surfaces to remain different. The physical adapter does not add a second evaluator or arm-specific decoder.

## Common generation and target binding

The adapter is bound to the protected-v2 common physical generation present when #2774 was qualified:

```text
generation_id = relay-common-physical-g1
aggregate      = sha256:5cc6444f473a748d56de7da7d5a56e564a7e29d919e00b6afcfd01a7fcd4edd5
```

Before entering the WSL transaction, the wrapper uses `tools.physical_common_generation.verify_checkout()` to verify the current checkout bytes against that certificate and verifies the branch-local target registry entry. This does not add the registry to common-generation identity; `.ai/physical/llama_cpp_targets.json` remains branch-local carriage outside the g1 aggregate.

Exactly one target is registered:

```text
v2:semantic-reconstruction-strict
  branch = v2
  module = tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp_wsl
  required_distributions = [httpx]
```

The canonical operator surface is therefore:

```bash
python3.12 -m tools.relay_physical_run --target v2:semantic-reconstruction-strict
```

The common runner, not this document, remains authority for clean-checkout, protected-base ancestry, fresh remote refs, persistent environment identity, resource serialization, and final pre-invoke checks.

## Strict llama.cpp transport and accounting

Each scientific cell calls #2769 `build_reconstruction_messages()` and carries the exact #2769 `response_format()`. The inherited no-retry llama.cpp transport enforces:

- one declared call-plan entry at a time;
- `stream=false`;
- `temperature=0`;
- `max_tokens=256`;
- top-level `reasoning_effort=none`;
- no request seed;
- exactly one response choice;
- `finish_reason=stop`;
- no visible/nonzero reasoning content;
- exact prompt-token agreement with llama.cpp `/input_tokens` accounting.

The exact input counter spends two non-generative `/input_tokens` requests for each semantic generation: full serialized request plus empty-content framing. Thus a completed E4-SR2 panel has 48 semantic completions and exactly 96 scientific count requests. The synthetic structured counter preflight is a separate 2-request non-scientific ledger before any exact family material exists.

Each persisted cell carries family/seed/arm identity, semantic digest, canonical truth used only by deterministic scoring, literal serialized representation, representation bytes, raw completion, strict score, input/output token counts, wall time, response id, and validated stop finish reason. Representation token count remains null unless independently exact rather than estimated.

## Failure semantics

Before exact materialization, any unprovable repository/common-generation/registry/runtime/model/context/slot/context-shift/reasoning/strict-schema/counter condition blocks execution.

After any scientific `/input_tokens` request attempt or semantic provider request attempt has begun, completed cells and observable ledgers are retained. A counter failure between `/input_tokens` accounting and the provider POST is therefore already scientific spend, even when `provider_attempts == 0`. There is no retry, replay, reseed, fallback, hidden repair, or model judge. Any measurement gate failure after scientific spend is classified by #2769 as:

```text
MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND
```

A failed or partial transaction cannot be completed by a second invocation under the same future exactly-once physical owner.

## CI and physical execution boundary

Repository CI uses synthetic-only payload factories and fake HTTP clients. It performs zero provider/model/GPU/llama-server work. Tests prove guarded materialization, 24/48/96 accounting, 2/2 pre-material counter freeze, exact native schema/envelope, P4/P6 semantic pairing, count-only and provider-attempt terminal failure semantics, common-generation pinning, and common-target routing.

#2774 itself authorizes no physical run. Only after this adapter is merged, protected-v2 post-merge CI is GREEN, reconciliation and the #2211 handoff are persisted/read back, and a fresh duplicate-owner search is clear may a separate exactly-once physical owner authorize one canonical common-runner invocation.

Architecture consequence: **NONE**.
