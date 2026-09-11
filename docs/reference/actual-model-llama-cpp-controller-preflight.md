# v1 llama.cpp controller preflight

Status: canonical restartable controller-setup procedure for RelayLM 1.0 llama.cpp / llama-server physical owners before a repository one-shot wrapper is consumed.

The governing split is:

```text
CONTROLLER_SETUP
  fresh authority + exact checkout
  repo-external Python environment
  runtime dependency/import closure
  localhost/runtime/material observations
  no scientific wrapper/host/provider call

ONE_SHOT_CONSUMED
  repository-owned WSL wrapper begins
  -> inner transaction
  -> owned llama-server / citable host as declared by that owner
```

> Prepare and prove the interpreter before spending the experiment.

This adopts the already-proven v1 #2458 controller pattern and the cross-line controller/host ordering used by RelayLM 2.0 #2363/#2498. It does not import RelayLM 2.0 scientific identity semantics into v1.

## Why this gate exists

#2521 consumed its wrapper once with a base `python3` that did not contain the declared RelayLM runtime dependency `httpx`. The child stopped at module import before transaction `main()`, server startup, host entry or generation. That result is infrastructure-invalid and scientifically empty.

A missing Python dependency must therefore be discovered while the controller is still restartable, not by spending the one-shot transaction.

## Restartable controller setup

Before any v1 llama.cpp one-shot wrapper, LocalCodex or another physical controller must establish the execution environment outside the repository.

A suitable fresh environment is:

```bash
CONTROLLER_ROOT="$(mktemp -d /tmp/relaylm-v1-llama-controller-XXXXXX)"
VENV="$CONTROLLER_ROOT/venv"
python3 -m venv "$VENV"
"$VENV/bin/python3" -m pip install "$REPO_ROOT"
```

An existing repo-external virtual environment may be reused only after fresh validation against the current exact checkout. It must not be treated as authority merely because it worked for an older transaction.

Package download/build activity, if needed, belongs only to restartable `CONTROLLER_SETUP`. It is not allowed after the one-shot wrapper has been consumed. Controller setup must not mutate tracked repository state or change the scientific treatment.

The exact checkout source is then placed first for the preflight and the later wrapper invocation:

```bash
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
```

Run the repository preflight with the **same interpreter** that will later invoke the wrapper:

```bash
"$VENV/bin/python3" -m tools.v1_llama_cpp_controller_preflight \
  --repo-root "$REPO_ROOT" \
  --expected-head "$EXPECTED_HEAD" \
  --expected-tree "$EXPECTED_TREE" \
  --inner-module "$INNER_MODULE" \
  --wrapper-module "$WRAPPER_MODULE"
```

The helper is non-generative. It validates:

- current `project.requires-python` against the selected interpreter;
- a repo-external virtual environment rather than the base interpreter;
- exact clean checkout HEAD/tree against fresh controller authority;
- an installed RelayLM distribution and current `httpx` distribution;
- `python -m pip check` under the selected interpreter;
- exact checkout `src` as the imported RelayLM source;
- selected wrapper existence in the exact checkout;
- exact selected inner transaction import without calling `main()`.

A successful result is `classification=READY`, has `wrapper_consumed=false`, and emits `one_shot_command` beginning with the same `sys.executable` that performed the preflight.

A failure is `PRE_WRAPPER_RUNTIME_BLOCKED` with:

```text
wrapper_consumed = false
server_calls = 0
host_calls = 0
provider_calls = 0
semantic_calls = 0
```

Such controller setup may be discarded and freshly re-established because the scientific one-shot has not begun. Do not splice partial observations from different controller environments.

## Opaque wrapper arguments

Some diagnostic wrappers require explicit controller-supplied artifact paths or other owner-specific arguments. The generic controller preflight may carry those arguments without interpreting them by placing `--wrapper-args` last and supplying the remaining wrapper command tail verbatim:

```bash
"$VENV/bin/python3" -m tools.v1_llama_cpp_controller_preflight \
  --repo-root "$REPO_ROOT" \
  --expected-head "$EXPECTED_HEAD" \
  --expected-tree "$EXPECTED_TREE" \
  --inner-module "$INNER_MODULE" \
  --wrapper-module "$WRAPPER_MODULE" \
  --wrapper-args \
  --owner-specific-option "$OWNER_SPECIFIC_VALUE"
```

`--wrapper-args` consumes the remainder of the preflight command line. The controller validates only that the values are safe argument strings and appends them to the emitted `one_shot_command`; it does not read files, infer semantic meaning, or validate owner-specific scientific content. The selected wrapper/host remains responsible for its own arguments and fail-closed semantics.

Omitting `--wrapper-args` preserves the historical ordinary Stage R command exactly.

## Same-interpreter handoff

After preflight is `READY`, do not switch back to an ambient/system `python3`.

Invoke the selected repository wrapper using the exact preflight interpreter, for example:

```bash
"$VENV/bin/python3" -m tools.v1_stage_r_llama_cpp_wsl
```

or, for the #2516 epistemic-formation physical successor:

```bash
"$VENV/bin/python3" -m tools.v1_stage_r_llama_cpp_epistemic_formation_wsl
```

The preflight `one_shot_command` is the canonical interpreter/module pair, including any explicitly supplied opaque wrapper arguments, for that controller cycle.

The wrapper still owns its existing fresh runtime HOME and passes its same `sys.executable` to the inner transaction. Workspace and artifact roots remain **transaction-owned and nonexistent before inner invocation**; controller setup must not pre-create them.

## Other pre-wrapper observations

Python readiness is necessary but not sufficient. The physical owner must also freshly establish, without generation, the current repository/GitHub authority and whatever localhost/runtime/material checks its current llama.cpp owner requires, including as applicable:

- Full Access / equivalent localhost permission;
- free `127.0.0.1:1234` without killing or reusing another listener;
- real operator HOME before child-HOME rewriting;
- llama.cpp root/server revision/version/build;
- canonical GGUF existence/readability/hash;
- GPU/runtime visibility;
- repo-external temporary-state writability.

These observations remain controller setup. They do not authorize a semantic retry or treatment change.

## Exactly-once boundary

Once the repository one-shot wrapper is invoked, the current physical owner is consumed according to its own accounting contract.

After that point there is no second wrapper/inner/host invocation for the same owner, including when the terminal result is infrastructure-invalid before provider generation. Do not repair the venv, switch interpreter, replay, restart, reseed, fall back, or manually rescue the server/host inside the spent owner.

A later attempt requires a new fresh physical owner after the infrastructure cause is reconciled.

## Non-goals

This controller gate does not change:

- production Core or cognition semantics;
- Stage R prompts, scenarios, oracle or scorer;
- model, quantization, context, slots or reasoning treatment;
- native structured-output semantics;
- llama-server process ownership/cleanup;
- retry/replay/fallback policy;
- LM Studio or FastCal routing.

It is an execution-readiness boundary only.

## Working principles

> Controller setup is restartable only before the one-shot boundary.

> Prove the exact interpreter, exact checkout and import closure together.

> Use the same interpreter to spend the one-shot.
