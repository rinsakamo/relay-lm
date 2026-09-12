# RelayLM one-shot llama.cpp physical runner

Status: infrastructure-only execution control owned by #2660. This layer does not
change v1/v2 scientific semantics or interpret experiment results.

## Fixed engine

The shared physical path is intentionally **llama.cpp-only**.

There is no engine/provider abstraction in this controller. LM Studio and vLLM
remain historical or target-specific evidence where already recorded, but they
are not selectable backends of the common runner.

The current single-GPU LocalCodex resource key is fixed to:

```text
llama-cpp:local-gpu
```

All v1/v2 LocalCodex physical jobs using the local RTX GPU must use that same key.

## Public entrypoint

Use the one-shot runner:

```bash
python -m tools.relay_physical_run --list-targets
python -m tools.relay_physical_run --target <registered-target>
```

Target-owned arguments may follow `--`. The public runner never accepts an
arbitrary executable; every target resolves to:

```text
<current exact Python> -m <repository-registered wrapper module> <target args>
```

`tools.physical_execution_queue` is an internal primitive. LocalCodex should not
construct `queue -- <arbitrary child command>` as the normal execution surface.

## One-shot controller lifecycle

```text
PREPARE
  exact clean checkout
  exact interpreter
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
  interpreter unchanged
  target module unchanged
  required distributions still present
  protected branch remote ref unchanged
  pushed checkout branch ref unchanged
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

If the protected branch or pushed execution branch advances while the job waits,
the final gate stops before child invocation. Reprepare and requeue. That is not a
scientific retry because target host/provider/semantic counts remain zero.

Fresh Issue/PR ownership and any target-specific authority beyond branch refs are
still part of the LocalCodex preparation procedure. The target wrapper/host
retains its existing scientific freeze, call ceilings, artifact and cleanup
contract.

## Lease semantics

The queue uses POSIX/WSL `flock`. File existence is not ownership.

After acquisition it requires consecutive idle observations. A busy observation
resets the idle counter. The lease file descriptor is deliberately inherited by
the immediate child process so an outer controller death does not release the
lease while that child is still alive.

The queue does not retry a target after `child_invoked_at` is populated.

## Receipt

The infrastructure receipt separates execution state from lease state.

Important fields include:

```text
state
lease_state
queued_at
lease_acquired_at
quiescent_at
pre_invoke_gate_started_at
pre_invoke_gate_passed_at
child_invoked_at
child_exit_code
released_at
```

Terminal execution states include `CHILD_EXITED`, `PRE_INVOKE_BLOCKED`, and
`CONTROLLER_ERROR`. `lease_state=RELEASED` records resource release separately.

The receipt never synthesizes PASS, SEMANTIC_FAIL, qualification, benchmark, or
product verdicts.

## LocalCodex prompt shape

The operator-facing instruction should stay short. Example:

```text
#2667 を current authority に従って one-shot physical run。
llama.cpp 共通 runner を使い、他の llama.cpp/GPU 利用中なら終了まで待つ。
pre-invoke で authority が古くなっていたら scientific transaction を消費せず停止。
host entry 後は retry/replay/rescue せず evidence をそのまま保存・報告。
```

LocalCodex resolves the registered target and repository-owned scientific
procedure from current authority; the operator does not hand-build Python,
server, port, model, HOME, lock, or wrapper argv.
