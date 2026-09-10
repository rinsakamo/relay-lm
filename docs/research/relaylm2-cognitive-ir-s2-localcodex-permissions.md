# RelayLM 2.0 Cognitive IR — LocalCodex physical permission boundary

This document is the operator-permission contract for the current #2211 selected-S2 WSL llama.cpp physical path.

It does not redefine the S2 experiment, the P0-P6 arms, the selected seed/regime, the ten-call plan, the llama.cpp runtime condition, or the #2363 host boundary.

## Why this surface exists

Historical physical owners established three distinct pre-host environment failures without spending selected S2:

- #2436: the target WSL shell had `python3` but no `python` compatibility alias;
- #2440: the LocalCodex sandbox exposed the operator home read-only, so the original lifecycle lock path under `$HOME/.cache` could not be opened;
- #2445: after writable state was moved to repo-external temporary storage, the lifecycle lock was acquired successfully but the inner transaction stopped before server launch with `PermissionError: [Errno 1] Operation not permitted` while entering the local socket/port-ownership boundary.

All three remain infrastructure evidence only. None reached selected-S2 host entry or made a semantic provider/model call.

## Required LocalCodex execution capability

The physical transaction necessarily owns a local `llama-server` process bound to:

```text
127.0.0.1:1234
```

Therefore the LocalCodex execution context used for the exactly-once wrapper command MUST permit, before the wrapper is consumed:

- local TCP socket creation;
- bind/listen/connect on localhost for the transaction-owned server and management probes;
- execution/read access to the declared local llama.cpp source/binary;
- read access to the canonical GGUF artifact;
- the required local GPU/runtime access;
- repo-external temporary writable state used by the WSL envelope.

A default sandbox that denies local socket creation/binding is not an admissible physical execution context for this path. Moving files to a writable directory cannot repair that capability boundary because every descendant server process inherits the execution sandbox.

This requirement is about localhost physical-laboratory access. It does not authorize arbitrary Internet access, a different provider, or LM Studio fallback.

## Current command

The repository-owned LocalCodex/WSL command remains:

```text
python3 -m tools.v2_cognitive_ir_s2_selected_llama_cpp_wsl
```

The wrapper still owns only the writable LocalCodex envelope. It invokes the existing inner transaction once, which in turn owns exactly one possible llama-server lifetime and at most one selected-S2 host invocation.

Do not replace this command with a hand-built llama-server sequence.

## Pre-invocation permission gate

A fresh physical owner must establish the required LocalCodex host/local-binding permission **before** consuming the wrapper invocation.

Acceptable operator states include a LocalCodex execution mode or managed policy that explicitly permits the required localhost binding and local runtime accesses, or an explicitly approved unsandboxed/full-access execution of the one bounded physical wrapper command.

If the required permission cannot be established, stop before wrapper invocation and report a mechanical operator-environment block. Do not consume another selected-S2 physical transaction merely to rediscover the same sandbox denial.

Do not use a semantic Chat Completions request as a permission probe.

## Scientific invariants unchanged

The permission boundary changes no scientific treatment. The current selected-S2 path still requires:

```text
endpoint             = http://127.0.0.1:1234/v1
context              = 8192
parallel slots       = 1
context shift        = disabled
reasoning_effort     = none
semantic calls       = exactly 10 if completed
semantic retries     = 0
fallbacks            = 0
LM Studio contacts   = 0
claim                = NON_CITABLE_S2_SMOKE
citable              = false
architecture effect  = NONE
S3 executed          = NO
```

The transaction-owned server launch remains `-ngl 999 -c 8192 -np 1 --no-context-shift` with one unique one-lifetime log.

A mechanically discriminating S2 may only route to a separately preregistered S3 owner; it is not itself an IR winner or architecture authorization.

## Historical preservation

Do not rewrite or rerun #2436, #2440, or #2445. Their zero-host/zero-semantic results remain immutable historical pre-host infrastructure evidence.

Any subsequent physical attempt requires a new current-authority physical owner, fresh exact `v2` checkout, fresh #2211/#2363 authority, and the permission gate above.
