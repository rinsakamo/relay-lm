# Actual-model vLLM capability probe

Status: repository-owned provider-free execution capsule for current `actual_model_evaluation` vLLM capability-surface acquisition.

This surface exists so an external controller does not have to recreate the mechanics or result semantics of `vllm serve --help=all` from Issue prose.

## Scope

`relaylm.actual_model_vllm_capability_probe.probe_vllm_capability_surface(...)` owns exactly one direct capability probe:

```text
<exact-vllm-executable> serve --help=all
```

It owns:

- exact command-shape validation;
- direct subprocess execution with `shell=False`;
- process-local explicit environment overlay without mutating the caller environment;
- bounded timeout and cleanup of the probe child only;
- non-zero / timeout / spawn / empty-help classification;
- current `discover_vllm_supported_flags(...)` parsing after successful non-empty help;
- content-free result identity;
- optional create-once atomic receipt persistence and strict reload.

It does **not** own:

- which exploratory environment candidate should be tried;
- model/provider server launch;
- endpoint or listener allocation;
- GPU admission;
- profiler/final runtime launch;
- reference or semantic evidence;
- Stage R, Crystallization, MemConflict, benchmark questions, or release calibration.

## Authority boundary

The caller may choose an exploratory process-local environment candidate only from authority appropriate to its transaction. The probe capsule does not promote that candidate into product/runtime authority.

Historical LAB3 procedure hints may suggest a later candidate. They do not authorize one. A candidate's scientific or operational legitimacy remains outside this execution capsule.

Conversely, once a candidate is selected, the controller must not hand-roll subprocess execution, timeout cleanup, output interpretation, or supported-flag parsing. Those mechanics belong to this repository-owned surface.

This is the same authority direction as `actual-model-vllm-qualification-launcher.md`:

> the controller sequences current inputs; repository-owned primitives decide and classify their owned predicates.

## Environment privacy

The child inherits the current process environment and receives only the explicit caller delta as an overlay. The probe never mutates `os.environ`.

Durable result data records only sorted explicit environment **key names** and their key-list digest. Environment values are not serialized or hashed into the receipt. This avoids turning credentials or opaque host values into durable evidence while still showing which environment roles the trial changed.

## Result classes

Exactly one status is returned:

```text
CAPABILITY_READY
NONZERO_EXIT
EMPTY_HELP
TIMEOUT
SPAWN_ERROR
```

These are mechanical probe observations only. None is model-quality or semantic evidence.

`CAPABILITY_READY` requires:

- direct command exit `0`;
- non-empty stdout help surface;
- at least one option parsed by current `discover_vllm_supported_flags(...)`.

A failure remains a failure of this exact candidate invocation. It does not authorize switching model/runtime, installing packages, inventing environment settings, or classifying the product as semantically failed.

## Device discovery

`vllm serve --help=all` is not assumed to be hardware-inert. Upstream parser construction may perform platform/device discovery before printing help. Therefore `provider launches = 0` must not be reinterpreted as `CUDA/NVML/device interaction = 0`.

The probe still does not reserve or launch a provider/listener runtime. Any LAB3 or Qualification using it must independently preserve current foreign-resource and physical-isolation rules.

## Receipt

`write_vllm_capability_probe_receipt(...)` writes exactly one `vllm-capability-probe.json` into an existing caller-selected artifact directory using create-once + atomic replace semantics.

The receipt contains only content-free metadata:

- command and digest;
- explicit environment key names and digest;
- exit/failure class;
- stdout/stderr byte counts and digests;
- help digest;
- supported flags and digest;
- timeout/cleanup status;
- content-derived receipt id.

Raw stdout/stderr and environment values are not persisted by this surface.

## LAB3 consumption

A later #2219 rehearsal may use this capsule repeatedly for bounded named mechanical candidates. The LAB3 controller may decide **which already-justified candidate to ask the capsule to execute**; it may not replace the capsule's command validation, process mechanics, timeout cleanup, result classification, or receipt semantics.

A successful rehearsal changes only procedure knowledge and remains `EXPLORATORY_NON_CITABLE` / `qualification_authority=false`. A later citable Qualification reacquires fresh authority and consumes the repository-owned capability surface again; it does not cite the LAB3 result as current physical authority.
