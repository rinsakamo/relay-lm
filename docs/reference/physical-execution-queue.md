# RelayLM one-shot llama.cpp physical runner

Status: infrastructure-only execution control owned by #2660 and hardened by
#2760. This layer does not change v1/v2 scientific semantics or interpret
experiment results.

## Fixed engine and policy-addressed local Python substrate

The shared physical path is intentionally **llama.cpp-only**. v1 and v2 may
evolve asynchronously, so the persistent Python substrate is selected by the
exact repository policy identity rather than by branch name or one mutable
global venv.

Default local state:

```text
~/.local/share/relaylm/physical/
├── environments/
│   └── <python-policy-sha256>/
│       ├── current.json
│       └── instances/
│           ├── <immutable-instance-id>/
│           │   ├── venv/
│           │   └── python-environment.json
│           └── ...
└── locks/
    └── python-env-<python-policy-sha256>.lock
```

`RELAYLM_PHYSICAL_HOME` may override the root.

The repository policy is `.ai/physical/python_environment_policy.json`. It fixes
the physical bootstrap interpreter to CPython 3.12 and declares the runtime
dependency floor, including `httpx`. Two branches carrying the same policy hash
may reuse the same selected local instance; branches carrying different policy
hashes coexist in different namespaces.

The explicit bootstrap command is:

```bash
python3.12 -m tools.relay_physical_env --prepare
```

`--prepare` is idempotent for the current policy: if the selected immutable
instance still matches its create-once manifest, it is reused without
reinstalling anything. Creation for the same policy is cross-process serialized
by a policy-specific `flock`.

A drifted selected instance is fail-closed. Deliberate replacement requires:

```bash
python3.12 -m tools.relay_physical_env --rebuild
```

`--rebuild` is **non-destructive**. It creates and verifies a fresh immutable
instance, then atomically switches `current.json` for future runs. The previous
instance is retained, so an already-started process that froze the old exact
interpreter is not broken by directory deletion. Automatic garbage collection
of old instances is intentionally outside the physical transaction path.

The local instance manifest freezes the exact Python identity and a fingerprint
over all installed distributions. Therefore a later `pip install`, upgrade,
removal, or interpreter change causes preparation/final-preflight failure
instead of a silent runtime change. The policy requirement list may use version
floors; the exact realized environment is the local manifest/fingerprint, not
the policy text alone.

RelayLM itself is not installed into a persistent venv. Child processes get an
exact `PYTHONPATH` containing only the selected checkout root and its `src/`
directory, plus `PYTHONNOUSERSITE=1`. This keeps reusable dependencies local
while product/scientific code always comes from the exact isolated checkout.

## Public entrypoint

Use CPython 3.12 as the pre-reexec operator entrypoint:

```bash
python3.12 -m tools.relay_physical_run --list-targets
python3.12 -m tools.relay_physical_run --target <registered-target>
```

This is deliberate. Do not assume a generic `python` alias exists on the host.
The runner verifies the selected policy-addressed environment and automatically
re-execs itself through that instance's exact interpreter.

If the selected environment does not exist or has drifted, the runner stops
before queue/target invocation and tells the operator to run the explicit
environment preparation/rebuild command. It never performs `pip install` during
a physical transaction.

Target-owned arguments may follow `--`. Every target resolves to:

```text
<selected persistent physical Python> -m <repository-registered wrapper module> <target args>
```

`tools.physical_execution_queue` is an internal primitive. LocalCodex should not
construct `queue -- <arbitrary child command>` as the normal execution surface.

## Target registry and branch carriage

The branch-local target registry is:

```text
.ai/physical/llama_cpp_targets.json
```

It is carriage data, not branch-neutral generation identity. v1 and v2 are
expected to register different targets.

The common runner nevertheless fails closed on the registry contract before
using it:

```text
schema_version = 1
engine = llama.cpp
resource_key = llama-cpp:local-gpu
```

A future registry schema or resource identity must therefore be an explicit
common-runtime change rather than silently changing repository declarations
without changing executed behavior.

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
  selected policy-addressed Python instance + fingerprint
  exact checkout-only PYTHONPATH
  required distributions
  fail-closed branch-local target registry
  fresh protected-branch remote ref
  fresh pushed checkout-branch ref when one exists
       |
       v
QUEUE / SHARED LEASE
  wait for another cooperative RelayLM job
       |
       v
EXTERNAL LLAMA.CPP QUIESCENCE
  wait for llama-server / llama-cli / llama-run
  require exact target listener address to be bindable
  never kill or reuse
       |
       v
FINAL_PREFLIGHT
  checkout unchanged
  selected persistent Python executable unchanged
  environment policy unchanged
  installed-distribution fingerprint unchanged
  target module unchanged
  required distributions still present
  protected branch remote ref unchanged
  pushed checkout branch remote ref unchanged
       |
       v
INVOCATION-BOUNDARY EXTERNAL CHECK
  recheck external process / target-facing bindability
  if busy appeared during final preflight:
    return to quiescence
    rerun final preflight
    do not invoke child
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

The listener criterion is target-facing **bindability**, not merely successful
TCP connection. A port can have no accepting listener and still be unavailable
to the target because of local socket lifecycle state.

If repository authority or the selected persistent Python environment changes
while the job waits, the final gate stops before child invocation. Reprepare and
requeue. That is not a scientific retry because target host/provider/semantic
counts remain zero.

A non-destructive `--rebuild` may atomically select a newer instance after a run
has frozen an older one. Before target invocation the final gate conservatively
blocks if selection changed. After the final gate, the old immutable instance
still exists, so pointer movement does not delete the interpreter underneath an
already-invoked child.

Fresh Issue/PR ownership and target-specific authority beyond branch refs remain
part of the LocalCodex preparation procedure.

## Lease semantics

The queue uses POSIX/WSL `flock`. File existence is not ownership.

After acquisition it requires consecutive idle observations. A busy observation
resets the idle counter. The lease file descriptor is inherited by the immediate
child so an outer controller death does not release the lease while that child
is still alive.

After the potentially slow final authority/environment gate, the queue performs
one more external process/port check. If the target address became unavailable,
it does not invoke the child; it returns to the external-runtime wait, regains
stable quiescence, and repeats final preflight.

An arbitrary non-cooperating process can still race after the controller's last
observation. The target retains its own listener check as defense in depth; the
common controller does not claim atomic ownership that the OS lifecycle does not
provide.

The queue does not retry a target after `child_invoked_at` is populated.

## Zero-GPU process smoke

Before a real llama.cpp/GPU smoke, check the OS-level control plane with:

```bash
python3.12 -m pytest -q tests/integration/test_physical_execution_queue_process_smoke.py
```

This uses real local processes/sockets but no model/GPU and covers cross-process
`flock`, external `llama-server` waiting, target-facing port quiescence,
inherited-lease survival after controller death, and pre-invoke blocking with
zero child starts.

## Receipt and environment evidence

Queue receipts remain infrastructure-only. The public runner also emits:

```text
python
python_environment_manifest
python_environment_policy_sha256
python_environment_fingerprint
```

The manifest path identifies the exact immutable selected instance. These fields
identify the reusable local execution substrate without putting it in the
repository or mixing it with scientific verdicts.

## LocalCodex prompt shape

The operator-facing instruction stays short:

```text
#<physical-owner> を current authority に従って one-shot physical run。
```

LocalCodex owns the non-exclusive preparation step. It verifies/reuses the
policy-addressed persistent physical environment first; an absent policy
namespace may be created by the explicit idempotent `--prepare` action. Drift is
fail-closed and requires deliberate `--rebuild`, never an in-transaction repair.

Repository/common-runner improvements must not absorb target-specific science,
exactly-once spend state, retry legality, or causal interpretation.
