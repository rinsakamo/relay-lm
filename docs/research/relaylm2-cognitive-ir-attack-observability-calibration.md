# RelayLM 2.0 Cognitive IR — R6D attack observability calibration

Owner: #2669  
Preregistration: #2667  
Scientific owner: #2211

## Purpose

R5 completed citable execution but every arm was `0/6` on canonical
`F_NULL`, `F_MISMATCH`, and `F_SHIFT` while canonical target probes exposed
zero target examples. This calibration does **not** test Memory/Structure
efficacy. It tests whether the changed target law is minimally observable to
a source-blind model when equal target-world evidence is supplied.

The only calibrated knob is:

```text
target_examples_visible = 1 -> 2 -> 3
```

Source/rule geometry remains `K3_THREE_ACTIVE`.

## Treatment-blind diagnostic

`A_ATTACK_TARGET_ONLY` receives only:

- the formal vector task instruction;
- the declared number of current target-law examples;
- the current target query;
- public task metadata such as modulus.

It receives no source history, no P0-P6 representation, no learned semantic
material, and no prior R5 output.

For SHIFT the diagnostic targets the first post-shift step.

## Frozen identity

```text
schema = relaylm2-cognitive-ir-s3-r6d-d2-observability-cal-v1
label  = relaylm2-cognitive-ir-s3-r6d-attack-observability-cal-v1
regimes = null -> mismatch -> shift
seeds/regime = 6
candidate order = 1 -> 2 -> 3 visible target examples
admission = >=5/6 correct in each regime
claim = NON_CITABLE_ATTACK_OBSERVABILITY_CALIBRATION
citable = false
architecture_consequence = NONE
```

Exact seed values and collision fences live in
`relaylm.v2_cognitive_ir_attack_observability_calibration`.

## Accounting

One candidate is exactly 18 semantic calls. The current llama.cpp transport
performs two exact `/input_tokens` requests per semantic call, therefore one
candidate is 36 token-count requests and the three-candidate maximum is:

```text
54 semantic calls
108 /input_tokens requests
```

The first qualifying visibility is selected and later candidates are not run.

## Terminal outcomes

```text
ATTACK_OBSERVABILITY_QUALIFIED
NO_OBSERVABLE_ATTACK_TARGET_RANGE
CALIBRATION_INCOMPLETE
PRE_WRAPPER_MECHANICAL_BLOCKED
```

All are non-citable and have `architecture_consequence = NONE`.

A successful calibration only supplies a routing value for a **separate**
future citable attack preregistration using fresh seeds. It does not authorize
P0-P6 scientific interpretation, #2188 correction/invalidation, or an
architecture change.

## Physical route

Repository binding provides:

```text
python3 -m tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp_wsl
```

The route reuses the existing listener-safe shared-floor transaction lifecycle
and canonical local llama.cpp treatment. A physical execution requires a
separate exactly-once owner and fresh physical authority.
