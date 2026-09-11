# RelayLM 2.0 Cognitive IR — shared-floor calibration v2

Owner: #2619. Repository binding: #2620. Scientific owner: #2211.

This is a **NON_CITABLE** successor calibration after #2610 ended `CALIBRATION_INCOMPLETE/CLEANUP_INCOMPLETE` and #2614/#2615 repaired cleanup instrumentation. It does not reinterpret or replay #2610 and does not promote the historical inner K3 result.

## Fresh identity

```text
label = relaylm2-cognitive-ir-shared-floor-calibration-v2
seeds =
  1142504739
  1503134270
  356394414
  1625198782
  1873901982
  2032603824
```

Seeds are deterministically derived as `int.from_bytes(SHA256(label + "|seed|" + index)[0:4], "big") & 0x7fffffff` and must remain disjoint from all historical #2211 calibration/qualification/S2/S3 seeds and relevant issue-number identities.

## Frozen protocol

Everything except label/seeds and repaired cleanup authority is inherited unchanged from #2600 plus #2612:

```text
K4_CURRENT_CLASS
K3_THREE_ACTIVE
K2_TWO_ACTIVE
K1_ONE_ACTIVE
```

The ladder is nested. For a fixed seed, coordinate ranking and nonzero values are fixed; difficulty changes only active count.

Per seed legal calls remain:

```text
A0_EXPLICIT_APPLICATION
FORM_P2
FORM_P3
FORM_P4
TARGET_P0
TARGET_P1
TARGET_P2
TARGET_P3
TARGET_P6
```

`TARGET_P4`, `TARGET_P5`, surface/semantic interventions, option-value, and null/mismatch/shift panels are forbidden from calibration selection.

Admission remains:

```text
A0 = 6/6
P4 formation >= 3/6
P2 hard admission = 6/6
neutral mean in [0.20, 0.80]
at least two of P0/P1/P2/P3/P6 individually in [1/6, 5/6]
```

Accounting remains 54 semantic calls and 108 `/input_tokens` requests per completed difficulty, maximum 216/432. First/hardest admitted difficulty terminates the calibration.

## Executable binding

Dedicated v2 identity modules are used so invoking the fresh calibration cannot silently fall back to the historical v1 seeds:

```text
src/relaylm/v2_cognitive_ir_shared_floor_calibration_v2.py
tools/v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp.py
tools/v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_transaction.py
tools/v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_wsl.py
```

The transaction and WSL adapters reuse the merged historical execution machinery only after binding the v2 runner/module explicitly. The repaired #2615 cleanup implementation remains authoritative: owned process termination is required, followed by bounded listener-release evidence. The old one-shot post-exit bindability decision is not restored.

## Claim boundary

```text
claim = NON_CITABLE_SHARED_TARGET_RANGE_CALIBRATION
citable = false
architecture_consequence = NONE
```

A later successful calibration can only select a difficulty for a separately preregistered R5 scientific campaign using another fresh, disjoint scientific seed set. Calibration completions, learned representations, rules, or family outputs must never be reused as R5 evidence.
