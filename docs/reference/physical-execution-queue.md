# RelayLM one-shot llama.cpp physical runner

Status: infrastructure-only execution control owned by #2660. This layer does not
change v1/v2 scientific semantics or interpret experiment results.

## Fixed engine and fixed local Python substrate

The shared physical path is intentionally **llama.cpp-only** and uses one
persistent Python environment for both v1 and v2.

Default local state:

```text
~/.local/share/relaylm/physical/
├── venv/
└── python-environment.json
```

`RELAYLM_PHYSICAL_HOME` may override that root.

The repository policy is `.ai/physical/python_environment_policy.json`. It fixes
the physical bootstrap interpreter to CPython 3.12 and declares the runtime
dependency floor, including `httpx`. The explicit bootstrap command is:

```bash
python3.12 -m tools.relay_physical_env --prepare
```

`--prepare` is idempotent: if the environment already matches its create-once
local manifest it is reused without reinstalling anything. It never upgrades or
repairs a drifted environment. A deliberate replacement requires:

```bash
python3.12 -m tools.relay_physical_env --rebuild
```

The local manifest freezes the exact Python identity and a fingerprint over all
installed distributions. Therefore a later `pip install`, upgrade, removal, or
interpreter change causes preparation/final-preflight failure instead of a
silent runtime change.

RelayLM itself is not installed into this persistent venv. Child processes get
an exact `PYTHONPATH` containing only the selected checkout root and its `src/`
directory, plus `PYTHONNOUSERSITE=1`. This keeps reusable dependencies local
while product/scientific code always comes from the exact isolated checkout.

## Public entrypoint

Use the one-shot runner:

```bash
python -m tools.relay_physical_run --list-targets
python -m tools.relay_physical_run --target <registered-target>
```

For target execution, the runner verifies the persistent environment and
automatically re-execs itself through:

```text
~/.local/share/relaylm/physical/venv/bin/python
```

If the persistent environment does not exist or has drifted, the runner stops
before queue/target invocation and tells the operator to run the explicit
environment preparation/rebuild command. It never performs `pip install` during
a physical transaction.

Target-owned arguments may follow `--`. Every target resolves to:

```text
<persistent physical Python> -m <repository-registered wrapper module> <target args>
```

`tools.physical_execution_queue` is an internal primitive. LocalCodex should not
construct `queue -- <arbitrary child command>` as the normal execution surface.

## Shared resource

The current single-GPU LocalCodex resource key is fixed to:

```text
llama-cpp:local-gpu
```

All v1/v2 LocalCodex physical jobs using the local RTX GPU use that same key.

## One-shot controller lifecycle

```text
PREPARE
  exact clean checkout
  persistent Python environment fingerprint
  exact checkout-only PYTHONPATH
  required distributions
  repository target registry
  fresh protected-branch remote ref
  fresh pushed checkout-branch ref when one exists
       |
       v
QUEUE / SHARED LEASE
  wait for another cooperative RelayLM job
       |
       v
EXTERNAL LLAMA.CPP QUIESCENCE
  wait for llama-server / llama-cli / llama-run / listener
  never kill or reuse
       |
       v
FINAL_PREFLIGHT
  checkout unchanged
  persistent Python executable unchanged
  environment policy unchanged
  installed-distribution fingerprint unchanged
  target module unchanged
  required distributions still present
  protected branch remote ref unchanged
  pushed checkout branch remote ref unchanged
       |
       v
TARGET WRAPPER EXACTLY ONCE
       |
       v
TARGET-OWNED CLEANUP / RESULT
       |
       v
LEASE RELEASE
```

If repository authority or the persistent Python environment changes while the
job waits, the final gate stops before child invocation. Reprepare and requeue.
That is not a scientific retry because target host/provider/semantic counts
remain zero.

Fresh Issue/PR ownership and target-specific authority beyond branch refs remain
part of the LocalCodex preparation procedure.

## Lease semantics

The queue uses POSIX/WSL `flock`. File existence is not ownership.

After acquisition it requires consecutive idle observations. A busy observation
resets the idle counter. The lease file descriptor is inherited by the immediate
child so an outer controller death does not release the lease while that child
is still alive.

The queue does not retry a target after `child_invoked_at` is populated.

## Zero-GPU process smoke

Before a real llama.cpp/GPU smoke, check the OS-level control plane with:

```bash
python -m pytest -q tests/integration/test_physical_execution_queue_process_smoke.py
```

This uses real local processes/sockets but no model/GPU and covers cross-process
`flock`, external `llama-server` waiting, listener quiescence, inherited-lease
survival after controller death, and pre-invoke blocking with zero child starts.

## Receipt and environment evidence

Queue receipts remain infrastructure-only. The public runner also emits:

```text
python
python_environment_manifest
python_environment_policy_sha256
python_environment_fingerprint
```

These identify the reused local execution substrate without putting it in the
repository or mixing it with scientific verdicts.

## LocalCodex prompt shape

The operator-facing instruction stays short:

```text
#<physical-owner> を current authority に従って one-shot physical run。
```

LocalCodex owns the non-exclusive preparation step. It verifies/reuses the
persistent physical environment first; only an absent environment may be
created by the explicit idempotent `--prepare` action. Drift is fail-closed and
requires explicit `--rebuild`, never an in-transaction repair.
